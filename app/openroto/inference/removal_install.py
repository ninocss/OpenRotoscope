from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from openroto.inference.removal_backends import REMOVAL_BACKENDS, backend_status

InstallProgress = Callable[[float, str], None]
CancelCallback = Callable[[], bool]

_PYTHON_VERSION = "3.10.11"
_FGT_COMMIT = "b6b01e3fc82931e050cf4d7062f3879f70677bad"
_SVOR_COMMIT = "df1fe23248c46477aea665c0f116fff91184f26d"

_FGT_PACKAGES = (
    "torch==1.13.1",
    "torchvision==0.14.1",
    "numpy==1.23.5",
    "scipy==1.9.3",
    "scikit-image==0.19.3",
    "Pillow==9.5.0",
    "PyYAML==6.0.1",
    "imageio==2.31.6",
    "imageio-ffmpeg==0.4.9",
    "opencv-python==4.8.1.78",
    "cvbase==0.5.5",
    "tensorboardX==2.6.2.2",
)

_SVOR_PACKAGES = (
    "einops",
    "safetensors",
    "numpy<2",
    "scipy",
    "scikit-image",
    "opencv-python",
    "omegaconf",
    "decord",
    "imageio[ffmpeg]",
    "dataclasses-json",
    "accelerate>=0.25.0",
    "diffusers==0.31.0",
    "transformers==4.46.2",
    "sentencepiece",
    "protobuf",
)


def _local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "OpenRoto"


def _managed_root(backend_id: str) -> Path:
    return _local_root() / "RemovalBackends" / backend_id


def _check_cancelled(cancelled: CancelCallback | None) -> None:
    if cancelled is not None and cancelled():
        raise InterruptedError("Removal backend installation was cancelled")


def _report(progress: InstallProgress | None, fraction: float, message: str) -> None:
    if progress is not None:
        progress(max(0.0, min(1.0, fraction)), message)


def _download_file(
    url: str,
    destination: Path,
    *,
    progress: InstallProgress | None,
    start: float,
    end: float,
    label: str,
    cancelled: CancelCallback | None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "OpenRoto/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        received = 0
        while True:
            _check_cancelled(cancelled)
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            received += len(chunk)
            if total > 0:
                fraction = start + (end - start) * min(1.0, received / total)
                _report(progress, fraction, label)
    _report(progress, end, label)


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    destination_resolved = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination_resolved):
                raise RuntimeError(f"Unsafe path in downloaded archive: {member.filename}")
        bundle.extractall(destination)


def _download_source(
    backend_id: str,
    destination: Path,
    *,
    progress: InstallProgress | None,
    cancelled: CancelCallback | None,
) -> None:
    if backend_id == "fgt":
        url = f"https://github.com/hitachinsk/FGT/archive/{_FGT_COMMIT}.zip"
    else:
        url = f"https://github.com/xiaomi-research/svor/archive/{_SVOR_COMMIT}.zip"

    with tempfile.TemporaryDirectory(prefix=f"openroto-{backend_id}-source-") as temp_dir:
        temp = Path(temp_dir)
        archive = temp / "source.zip"
        extracted = temp / "extracted"
        _download_file(
            url,
            archive,
            progress=progress,
            start=0.02,
            end=0.08,
            label=f"Downloading {REMOVAL_BACKENDS[backend_id].display_name} source",
            cancelled=cancelled,
        )
        _safe_extract_zip(archive, extracted)
        roots = [path for path in extracted.iterdir() if path.is_dir()]
        if len(roots) != 1:
            raise RuntimeError(f"Unexpected {backend_id} source archive layout")
        shutil.copytree(roots[0], destination, dirs_exist_ok=True)


def _terminate_process_tree(process: subprocess.Popen[object]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            process.kill()


def _run_command(
    command: list[str],
    *,
    cwd: Path | None,
    log_path: Path,
    cancelled: CancelCallback | None,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write("\n$ " + " ".join(command) + "\n")
        log.flush()
        process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd is not None else None,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        while process.poll() is None:
            if cancelled is not None and cancelled():
                _terminate_process_tree(process)
                raise InterruptedError("Removal backend installation was cancelled")
            time.sleep(0.20)

    if process.returncode != 0:
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        tail = "\n".join(lines[-20:]).strip()
        detail = f"\n{tail}" if tail else ""
        raise RuntimeError(f"Command failed with exit code {process.returncode}:{detail}")


def _prepare_windows_python(
    staging: Path,
    *,
    progress: InstallProgress | None,
    log_path: Path,
    cancelled: CancelCallback | None,
) -> Path:
    bootstrap = staging / "bootstrap-python"
    bootstrap.mkdir(parents=True, exist_ok=True)
    archive = staging / "python-embed.zip"
    url = (
        f"https://www.python.org/ftp/python/{_PYTHON_VERSION}/"
        f"python-{_PYTHON_VERSION}-embed-amd64.zip"
    )
    _download_file(
        url,
        archive,
        progress=progress,
        start=0.09,
        end=0.13,
        label="Downloading isolated Python 3.10 runtime",
        cancelled=cancelled,
    )
    _safe_extract_zip(archive, bootstrap)
    archive.unlink(missing_ok=True)

    pth_files = list(bootstrap.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError("Downloaded Python runtime is missing its path configuration")
    pth = pth_files[0]
    lines = pth.read_text(encoding="utf-8").splitlines()
    normalized: list[str] = []
    has_site_packages = False
    has_import_site = False
    for line in lines:
        stripped = line.strip()
        if stripped == "#import site":
            normalized.append("import site")
            has_import_site = True
        else:
            normalized.append(line)
            if stripped.lower() == r"lib\site-packages".lower():
                has_site_packages = True
            if stripped == "import site":
                has_import_site = True
    if not has_site_packages:
        normalized.append(r"Lib\site-packages")
    if not has_import_site:
        normalized.append("import site")
    pth.write_text("\n".join(normalized) + "\n", encoding="utf-8")

    bootstrap_python = bootstrap / "python.exe"
    get_pip = staging / "get-pip.py"
    _download_file(
        "https://bootstrap.pypa.io/get-pip.py",
        get_pip,
        progress=progress,
        start=0.13,
        end=0.14,
        label="Preparing sidecar package manager",
        cancelled=cancelled,
    )
    _run_command(
        [str(bootstrap_python), str(get_pip), "--disable-pip-version-check"],
        cwd=staging,
        log_path=log_path,
        cancelled=cancelled,
    )
    _run_command(
        [
            str(bootstrap_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "virtualenv>=20.26,<21",
        ],
        cwd=staging,
        log_path=log_path,
        cancelled=cancelled,
    )
    venv = staging / "venv"
    _run_command(
        [str(bootstrap_python), "-m", "virtualenv", str(venv)],
        cwd=staging,
        log_path=log_path,
        cancelled=cancelled,
    )
    python = venv / "Scripts" / "python.exe"
    if not python.is_file():
        raise RuntimeError("Could not create the isolated Python environment")
    shutil.rmtree(bootstrap, ignore_errors=True)
    get_pip.unlink(missing_ok=True)
    _report(progress, 0.18, "Isolated Python environment ready")
    return python


def _prepare_posix_python(
    staging: Path,
    *,
    progress: InstallProgress | None,
    log_path: Path,
    cancelled: CancelCallback | None,
) -> Path:
    candidates = [
        os.environ.get("OPENROTO_SIDECAR_PYTHON", ""),
        shutil.which("python3.10") or "",
    ]
    if sys.version_info[:2] == (3, 10):
        candidates.append(sys.executable)
    base_python = next((value for value in candidates if value and Path(value).is_file()), "")
    if not base_python:
        raise RuntimeError(
            "Automatic FGT/SVOR setup requires Python 3.10 on this platform. "
            "Set OPENROTO_SIDECAR_PYTHON to a Python 3.10 executable."
        )
    venv = staging / "venv"
    _run_command(
        [base_python, "-m", "venv", str(venv)],
        cwd=staging,
        log_path=log_path,
        cancelled=cancelled,
    )
    python = venv / "bin" / "python"
    if not python.is_file():
        raise RuntimeError("Could not create the isolated Python environment")
    _report(progress, 0.18, "Isolated Python environment ready")
    return python


def _prepare_python(
    staging: Path,
    *,
    progress: InstallProgress | None,
    log_path: Path,
    cancelled: CancelCallback | None,
) -> Path:
    if os.name == "nt":
        return _prepare_windows_python(
            staging, progress=progress, log_path=log_path, cancelled=cancelled
        )
    return _prepare_posix_python(
        staging, progress=progress, log_path=log_path, cancelled=cancelled
    )


def _pip_install(
    python: Path,
    packages: tuple[str, ...],
    *,
    cwd: Path,
    log_path: Path,
    cancelled: CancelCallback | None,
    extra: tuple[str, ...] = (),
) -> None:
    _run_command(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            *extra,
            *packages,
        ],
        cwd=cwd,
        log_path=log_path,
        cancelled=cancelled,
    )


def _install_fgt_dependencies(
    python: Path,
    repo: Path,
    *,
    progress: InstallProgress | None,
    log_path: Path,
    cancelled: CancelCallback | None,
) -> None:
    _report(progress, 0.20, "Installing FGT++ dependencies")
    _pip_install(
        python,
        _FGT_PACKAGES,
        cwd=repo,
        log_path=log_path,
        cancelled=cancelled,
    )
    _report(progress, 0.55, "FGT++ dependencies ready")


def _install_svor_dependencies(
    python: Path,
    repo: Path,
    *,
    progress: InstallProgress | None,
    log_path: Path,
    cancelled: CancelCallback | None,
) -> None:
    _report(progress, 0.20, "Installing SVOR PyTorch runtime")
    _pip_install(
        python,
        ("torch==2.7.0", "torchvision==0.22.0", "torchaudio==2.7.0"),
        cwd=repo,
        log_path=log_path,
        cancelled=cancelled,
        extra=("--index-url", "https://download.pytorch.org/whl/cu126"),
    )
    _report(progress, 0.42, "Installing SVOR inference dependencies")
    _pip_install(
        python,
        _SVOR_PACKAGES,
        cwd=repo,
        log_path=log_path,
        cancelled=cancelled,
    )
    _report(progress, 0.58, "SVOR dependencies ready")


def _snapshot_download(*, repo_id: str, local_dir: Path, allow_patterns: list[str] | None = None) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as error:
        raise RuntimeError("The Hugging Face model manager is not installed.") from error
    local_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(local_dir),
        allow_patterns=allow_patterns,
    )


def _copy_required(source: Path, destination: Path, names: tuple[str, ...]) -> None:
    match: Path | None = None
    lowered = {name.lower() for name in names}
    for candidate in source.rglob("*"):
        if candidate.is_file() and candidate.name.lower() in lowered:
            match = candidate
            break
    if match is None:
        raise RuntimeError(f"Downloaded model is missing {names[0]}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(match, destination)


def _install_fgt_weights(
    repo: Path,
    *,
    progress: InstallProgress | None,
    cancelled: CancelCallback | None,
) -> None:
    _check_cancelled(cancelled)
    _report(progress, 0.58, "Downloading FGT++ model weights")
    weights = repo.parent / "fgt-weights"
    _snapshot_download(
        repo_id="hitachinsk/FGT",
        local_dir=weights,
        allow_patterns=[
            "fgt.pth.tar",
            "lafc.pth.tar",
            "lafc_single.pth.tar",
            "FGT_config.yaml",
            "LAFC_config.yaml",
            "LAFC_single_config.yaml",
            "fgt_config.yaml",
            "lafc_config.yaml",
            "lafc_single_config.yaml",
        ],
    )
    _check_cancelled(cancelled)
    _copy_required(weights, repo / "FGT" / "checkpoint" / "fgt.pth.tar", ("fgt.pth.tar",))
    _copy_required(weights, repo / "LAFC" / "checkpoint" / "lafc.pth.tar", ("lafc.pth.tar",))
    _copy_required(
        weights,
        repo / "FGT" / "flowCheckPoint" / "lafc_single.pth.tar",
        ("lafc_single.pth.tar",),
    )
    _copy_required(
        weights,
        repo / "FGT" / "checkpoint" / "config.yaml",
        ("FGT_config.yaml", "fgt_config.yaml"),
    )
    _copy_required(
        weights,
        repo / "LAFC" / "checkpoint" / "config.yaml",
        ("LAFC_config.yaml", "lafc_config.yaml"),
    )
    _copy_required(
        weights,
        repo / "FGT" / "flowCheckPoint" / "config.yaml",
        ("LAFC_single_config.yaml", "lafc_single_config.yaml"),
    )
    shutil.rmtree(weights, ignore_errors=True)
    _report(progress, 0.92, "FGT++ model weights ready")


def _install_svor_weights(
    repo: Path,
    *,
    progress: InstallProgress | None,
    cancelled: CancelCallback | None,
) -> None:
    _check_cancelled(cancelled)
    models = repo / "models"
    _report(progress, 0.58, "Downloading SVOR LoRA weights")
    _snapshot_download(
        repo_id="HigherHu/SVOR",
        local_dir=models,
        allow_patterns=["remove_model_stage1.safetensors", "remove_model_stage2.safetensors"],
    )
    _check_cancelled(cancelled)
    _report(progress, 0.70, "Downloading Wan2.1-VACE-1.3B")
    _snapshot_download(
        repo_id="Wan-AI/Wan2.1-VACE-1.3B",
        local_dir=models / "Wan2.1-VACE-1.3B",
    )
    _check_cancelled(cancelled)
    for required in (
        models / "remove_model_stage1.safetensors",
        models / "remove_model_stage2.safetensors",
        models / "Wan2.1-VACE-1.3B" / "config.json",
    ):
        if not required.exists():
            raise RuntimeError(f"SVOR model download is incomplete: {required.name} is missing")
    _report(progress, 0.94, "SVOR model weights ready")


def install_removal_backend(
    backend_id: str,
    *,
    progress: InstallProgress | None = None,
    cancelled: CancelCallback | None = None,
) -> Path:
    if backend_id not in {"fgt", "svor"}:
        raise ValueError(f"Unsupported managed removal backend: {backend_id}")

    status = backend_status(backend_id)
    if bool(status["available"]):
        _report(progress, 1.0, f"{status['display_name']} is already installed")
        return _managed_root(backend_id)

    spec = REMOVAL_BACKENDS[backend_id]
    if os.environ.get(spec.root_env, "") or os.environ.get(spec.python_env, ""):
        raise RuntimeError(
            f"{spec.display_name} has an explicit environment override. Fix or unset "
            f"{spec.root_env}/{spec.python_env} before using OpenRoto's managed installer."
        )

    base = _local_root() / "RemovalBackends"
    base.mkdir(parents=True, exist_ok=True)
    final_root = _managed_root(backend_id)
    staging = base / f".{backend_id}-install"
    failure_log = base / f"{backend_id}-install.log"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=False)
    log_path = staging / "install.log"

    try:
        _check_cancelled(cancelled)
        _report(progress, 0.01, f"Preparing {spec.display_name}")
        repo = staging / "repo"
        _download_source(
            backend_id,
            repo,
            progress=progress,
            cancelled=cancelled,
        )
        python = _prepare_python(
            staging,
            progress=progress,
            log_path=log_path,
            cancelled=cancelled,
        )
        if backend_id == "fgt":
            _install_fgt_dependencies(
                python,
                repo,
                progress=progress,
                log_path=log_path,
                cancelled=cancelled,
            )
            _install_fgt_weights(repo, progress=progress, cancelled=cancelled)
        else:
            _install_svor_dependencies(
                python,
                repo,
                progress=progress,
                log_path=log_path,
                cancelled=cancelled,
            )
            _install_svor_weights(repo, progress=progress, cancelled=cancelled)

        marker = staging / ".openroto-managed.json"
        marker.write_text(
            json.dumps(
                {
                    "backend": backend_id,
                    "python": _PYTHON_VERSION,
                    "source_commit": _FGT_COMMIT if backend_id == "fgt" else _SVOR_COMMIT,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        _check_cancelled(cancelled)
        shutil.rmtree(final_root, ignore_errors=True)
        staging.replace(final_root)
        failure_log.unlink(missing_ok=True)

        ready = backend_status(backend_id)
        if not bool(ready["available"]):
            raise RuntimeError(
                f"{spec.display_name} installation finished but OpenRoto cannot find its runtime."
            )
        _report(progress, 1.0, f"{spec.display_name} installed")
        return final_root
    except Exception:
        try:
            if log_path.is_file():
                shutil.copy2(log_path, failure_log)
        except OSError:
            pass
        shutil.rmtree(staging, ignore_errors=True)
        raise


def remove_managed_removal_backend(backend_id: str) -> None:
    if backend_id not in {"fgt", "svor"}:
        raise ValueError(f"Unsupported managed removal backend: {backend_id}")
    spec = REMOVAL_BACKENDS[backend_id]
    if os.environ.get(spec.root_env, "") or os.environ.get(spec.python_env, ""):
        raise RuntimeError(f"Refusing to remove externally configured {spec.display_name}")
    shutil.rmtree(_managed_root(backend_id), ignore_errors=True)
