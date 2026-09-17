from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

ProgressCallback = Callable[[float, str], None]
TimingCallback = Callable[[str, float], None]


@dataclass(frozen=True, slots=True)
class RemovalBackendSpec:
    id: str
    display_name: str
    description: str
    quality: str
    speed: str
    vram: str
    license: str
    source_url: str
    python_env: str
    root_env: str


REMOVAL_BACKENDS: dict[str, RemovalBackendSpec] = {
    "temporal": RemovalBackendSpec(
        id="temporal",
        display_name="Temporal Fill",
        description="Fast local reconstruction from visible pixels in nearby frames.",
        quality="Preview",
        speed="Fast",
        vram="No extra VRAM",
        license="OpenRoto",
        source_url="",
        python_env="",
        root_env="",
    ),
    "fgt": RemovalBackendSpec(
        id="fgt",
        display_name="FGT++",
        description="Flow-guided transformer video inpainting. Runs in an isolated local environment.",
        quality="Balanced",
        speed="Medium",
        vram="GPU dependent",
        license="MIT",
        source_url="https://github.com/hitachinsk/FGT",
        python_env="OPENROTO_FGT_PYTHON",
        root_env="OPENROTO_FGT_ROOT",
    ),
    "svor": RemovalBackendSpec(
        id="svor",
        display_name="SVOR",
        description="Diffusion video object removal for difficult motion, shadows and imperfect masks.",
        quality="High",
        speed="Slow",
        vram="~33 GB / ~24 GB with CPU offload",
        license="Apache-2.0",
        source_url="https://github.com/xiaomi-research/svor",
        python_env="OPENROTO_SVOR_PYTHON",
        root_env="OPENROTO_SVOR_ROOT",
    ),
}

_SOURCE_ARCHIVES = {
    "fgt": (
        "https://codeload.github.com/hitachinsk/FGT/zip/b6b01e3fc82931e050cf4d7062f3879f70677bad",
        "b6b01e3fc82931e050cf4d7062f3879f70677bad",
    ),
    "svor": (
        "https://codeload.github.com/xiaomi-research/svor/zip/df1fe23248c46477aea665c0f116fff91184f26d",
        "df1fe23248c46477aea665c0f116fff91184f26d",
    ),
}

_PYTHON_RUNTIMES = {
    "fgt": ("3.8.10", "3.8"),
    "svor": ("3.10.11", "3.10"),
}

_DEPENDENCY_REVISION = {
    "fgt": "openroto-fgt-win-v1",
    "svor": "openroto-svor-win-v1",
}

_FGT_PACKAGES = (
    "numpy==1.22.4",
    "scipy==1.7.3",
    "scikit-image==0.19.3",
    "matplotlib==3.5.3",
    "Pillow==9.2.0",
    "PyYAML==6.0.1",
    "tensorboardX==2.5.1",
    "imageio==2.19.5",
    "imageio-ffmpeg==0.4.9",
    "opencv-python-headless==4.7.0.72",
    "cvbase==0.5.5",
)


def _local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "OpenRoto"


def _backend_base(backend_id: str) -> Path:
    return _local_root() / "RemovalBackends" / backend_id


def _uses_managed_backend(backend_id: str) -> bool:
    spec = REMOVAL_BACKENDS[backend_id]
    return not bool(os.environ.get(spec.root_env, "") or os.environ.get(spec.python_env, ""))


def backend_root(backend_id: str) -> Path:
    spec = REMOVAL_BACKENDS[backend_id]
    explicit = os.environ.get(spec.root_env, "") if spec.root_env else ""
    if explicit:
        return Path(explicit).expanduser()
    return _backend_base(backend_id) / "repo"


def backend_python(backend_id: str) -> Path:
    spec = REMOVAL_BACKENDS[backend_id]
    explicit = os.environ.get(spec.python_env, "") if spec.python_env else ""
    if explicit:
        return Path(explicit).expanduser()
    base = _backend_base(backend_id)
    managed = base / "python" / ("python.exe" if os.name == "nt" else "bin/python")
    if managed.is_file():
        return managed
    legacy = base / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if legacy.is_file():
        return legacy
    return managed


def _source_marker(backend_id: str) -> Path:
    return backend_root(backend_id) / ".openroto-source.json"


def _dependency_marker(backend_id: str) -> Path:
    return _backend_base(backend_id) / ".openroto-dependencies"


def _required_backend_paths(backend_id: str) -> list[Path]:
    root = backend_root(backend_id)
    if backend_id == "fgt":
        return [
            root / "tool" / "video_inpainting.py",
            root / "FGT" / "checkpoint" / "fgt.pth.tar",
            root / "FGT" / "checkpoint" / "FGT_config.yaml",
            root / "LAFC" / "checkpoint" / "lafc.pth.tar",
            root / "LAFC" / "checkpoint" / "LAFC_config.yaml",
            root / "LAFC" / "flowCheckPoint" / "raft-things.pth",
        ]
    if backend_id == "svor":
        return [
            root / "predict_SVOR.py",
            root / "models" / "remove_model_stage1.safetensors",
            root / "models" / "remove_model_stage2.safetensors",
            root / "models" / "Wan2.1-VACE-1.3B" / "config.json",
        ]
    return []


def backend_status(backend_id: str) -> dict[str, object]:
    spec = REMOVAL_BACKENDS[backend_id]
    if backend_id == "temporal":
        return {
            **asdict(spec),
            "available": True,
            "ready": True,
            "installable": False,
            "status": "Built in",
            "root": "",
            "python": "",
            "missing": [],
        }

    root = backend_root(backend_id)
    python = backend_python(backend_id)
    managed = _uses_managed_backend(backend_id)
    required = _required_backend_paths(backend_id)
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    dependencies_ready = True
    if managed:
        marker = _dependency_marker(backend_id)
        dependencies_ready = marker.is_file() and marker.read_text(
            encoding="utf-8", errors="replace"
        ).strip() == _DEPENDENCY_REVISION[backend_id]
    ready = python.is_file() and not missing and dependencies_ready
    installable = managed and os.name == "nt"

    if ready:
        status = "Ready"
    elif not managed:
        if not root.exists():
            status = "Configured repository missing"
        elif not python.is_file():
            status = "Configured Python missing"
        elif missing:
            status = "Configured backend incomplete"
        else:
            status = "Configured environment incomplete"
    elif os.name != "nt":
        status = "Automatic setup currently requires Windows"
    elif not root.exists() and not python.is_file():
        status = "Download on first use"
    elif not python.is_file():
        status = "Python runtime incomplete — retry to repair"
    elif missing:
        status = "Model files incomplete — retry to repair"
    elif not dependencies_ready:
        status = "Dependencies incomplete — retry to repair"
    else:
        status = "Not ready"

    return {
        **asdict(spec),
        # Existing QML treats `available` as "the action can be started". A
        # managed backend is therefore available before its first use, while
        # `ready` still reports whether all local files are already installed.
        "available": ready or installable,
        "ready": ready,
        "installable": installable,
        "status": status,
        "root": str(root),
        "python": str(python),
        "missing": missing,
    }


def _runner_script(backend_id: str) -> Path:
    filename = "fgt_runner.py" if backend_id == "fgt" else "svor_runner.py"
    return Path(__file__).with_name("removal_runners") / filename


def _terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except Exception:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except Exception:
            process.kill()


def _progress(callback: ProgressCallback | None, fraction: float, text: str) -> None:
    if callback:
        callback(fraction, text)


def _check_cancelled(cancelled: Callable[[], bool] | None) -> None:
    if cancelled and cancelled():
        raise InterruptedError("Object-removal backend setup was cancelled")


def _ensure_managed_base(backend_id: str) -> Path:
    base = _backend_base(backend_id)
    if base.exists() and base.is_symlink():
        raise RuntimeError(f"Refusing to install into symlinked backend folder: {base}")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _download_file(
    url: str,
    destination: Path,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "OpenRoto/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as stream:
            while True:
                _check_cancelled(cancelled)
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                stream.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def _safe_extract_zip(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for item in archive.infolist():
            resolved = (destination / item.filename).resolve()
            if resolved != target and target not in resolved.parents:
                raise RuntimeError(f"Unsafe path in downloaded archive: {item.filename}")
        archive.extractall(destination)


def _install_source(
    backend_id: str,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    root = backend_root(backend_id)
    archive_url, revision = _SOURCE_ARCHIVES[backend_id]
    marker = _source_marker(backend_id)
    expected_entry = root / ("tool/video_inpainting.py" if backend_id == "fgt" else "predict_SVOR.py")
    if marker.is_file() and expected_entry.is_file():
        try:
            metadata = json.loads(marker.read_text(encoding="utf-8"))
        except Exception:
            metadata = {}
        if metadata.get("revision") == revision:
            return

    base = _ensure_managed_base(backend_id)
    if root.exists() and root.is_symlink():
        raise RuntimeError(f"Refusing to replace symlinked backend repository: {root}")
    with tempfile.TemporaryDirectory(prefix="source-", dir=base) as temporary:
        temporary_path = Path(temporary)
        archive_path = temporary_path / "source.zip"
        extracted = temporary_path / "extracted"
        _download_file(archive_url, archive_path, cancelled=cancelled)
        _safe_extract_zip(archive_path, extracted)
        children = [path for path in extracted.iterdir() if path.is_dir()]
        if len(children) != 1:
            raise RuntimeError(f"Downloaded {REMOVAL_BACKENDS[backend_id].display_name} archive is invalid")
        if root.exists():
            shutil.rmtree(root)
        shutil.move(str(children[0]), str(root))
    marker.write_text(json.dumps({"revision": revision}, indent=2), encoding="utf-8")


def _enable_embedded_site(runtime: Path) -> None:
    pth_files = sorted(runtime.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError("Downloaded Python runtime is missing its ._pth configuration")
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
            if stripped == "import site":
                has_import_site = True
            if stripped.replace("/", "\\").lower() == "lib\\site-packages":
                has_site_packages = True
    if not has_site_packages:
        normalized.append("Lib\\site-packages")
    if not has_import_site:
        normalized.append("import site")
    pth.write_text("\n".join(normalized) + "\n", encoding="utf-8")
    (runtime / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)


def _run_command(
    command: list[str],
    *,
    cwd: Path | None,
    log_path: Path,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if os.name == "nt":
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", errors="replace") as log_stream:
        process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
        while process.poll() is None:
            if cancelled and cancelled():
                _terminate_process_tree(process)
                raise InterruptedError("Object-removal backend setup was cancelled")
            time.sleep(0.25)
    if process.returncode != 0:
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        tail = "\n".join(lines[-20:]).strip()
        raise RuntimeError(
            f"Backend setup command failed with exit code {process.returncode}"
            + (f":\n{tail}" if tail else "")
        )


def _ensure_python_runtime(
    backend_id: str,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    if os.name != "nt":
        raise RuntimeError("Automatic removal-backend setup currently supports Windows only")
    base = _ensure_managed_base(backend_id)
    runtime = base / "python"
    python = runtime / "python.exe"
    log_path = base / "install.log"
    if python.is_file():
        probe = subprocess.run(
            [str(python), "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if probe.returncode == 0:
            return python

    if runtime.exists() and runtime.is_symlink():
        raise RuntimeError(f"Refusing to replace symlinked Python runtime: {runtime}")
    shutil.rmtree(runtime, ignore_errors=True)
    runtime.mkdir(parents=True, exist_ok=True)
    full_version, minor_version = _PYTHON_RUNTIMES[backend_id]
    with tempfile.TemporaryDirectory(prefix="python-", dir=base) as temporary:
        temporary_path = Path(temporary)
        archive_path = temporary_path / "python.zip"
        runtime_url = (
            f"https://www.python.org/ftp/python/{full_version}/"
            f"python-{full_version}-embed-amd64.zip"
        )
        _download_file(runtime_url, archive_path, cancelled=cancelled)
        _safe_extract_zip(archive_path, runtime)
        _enable_embedded_site(runtime)
        get_pip = temporary_path / "get-pip.py"
        _download_file(
            f"https://bootstrap.pypa.io/pip/{minor_version}/get-pip.py",
            get_pip,
            cancelled=cancelled,
        )
        _run_command(
            [str(python), str(get_pip), "--disable-pip-version-check"],
            cwd=runtime,
            log_path=log_path,
            cancelled=cancelled,
        )
    return python


def _install_dependencies(
    backend_id: str,
    python: Path,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    base = _ensure_managed_base(backend_id)
    marker = _dependency_marker(backend_id)
    revision = _DEPENDENCY_REVISION[backend_id]
    if marker.is_file() and marker.read_text(encoding="utf-8", errors="replace").strip() == revision:
        return
    log_path = base / "install.log"
    if backend_id == "fgt":
        _run_command(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "torch==1.10.1+cu113",
                "torchvision==0.11.2+cu113",
                "--index-url",
                "https://download.pytorch.org/whl/cu113",
            ],
            cwd=backend_root(backend_id),
            log_path=log_path,
            cancelled=cancelled,
        )
        _run_command(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                *_FGT_PACKAGES,
            ],
            cwd=backend_root(backend_id),
            log_path=log_path,
            cancelled=cancelled,
        )
    else:
        _run_command(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "torch==2.7.0",
                "torchvision==0.22.0",
                "torchaudio==2.7.0",
                "xformers==0.0.30",
                "--index-url",
                "https://download.pytorch.org/whl/cu126",
            ],
            cwd=backend_root(backend_id),
            log_path=log_path,
            cancelled=cancelled,
        )
        requirements = backend_root(backend_id) / "requirements.txt"
        if not requirements.is_file():
            raise RuntimeError("SVOR requirements.txt is missing")
        _run_command(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(requirements),
            ],
            cwd=backend_root(backend_id),
            log_path=log_path,
            cancelled=cancelled,
        )
    marker.write_text(revision + "\n", encoding="utf-8")


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


def _install_weights(backend_id: str) -> None:
    root = backend_root(backend_id)
    if backend_id == "fgt":
        base = _ensure_managed_base(backend_id)
        staging = base / "weights"
        _snapshot_download(
            repo_id="hitachinsk/FGT",
            local_dir=staging,
            allow_patterns=[
                "fgt.pth.tar",
                "lafc.pth.tar",
                "FGT_config.yaml",
                "LAFC_config.yaml",
            ],
        )
        fgt_target = root / "FGT" / "checkpoint"
        lafc_target = root / "LAFC" / "checkpoint"
        shutil.rmtree(fgt_target, ignore_errors=True)
        shutil.rmtree(lafc_target, ignore_errors=True)
        fgt_target.mkdir(parents=True, exist_ok=True)
        lafc_target.mkdir(parents=True, exist_ok=True)
        for source_name, destination in (
            ("fgt.pth.tar", fgt_target / "fgt.pth.tar"),
            ("FGT_config.yaml", fgt_target / "FGT_config.yaml"),
            ("lafc.pth.tar", lafc_target / "lafc.pth.tar"),
            ("LAFC_config.yaml", lafc_target / "LAFC_config.yaml"),
        ):
            source = staging / source_name
            if not source.is_file():
                raise RuntimeError(f"FGT model download is missing {source_name}")
            shutil.copy2(source, destination)
        shutil.rmtree(staging, ignore_errors=True)
    else:
        models = root / "models"
        _snapshot_download(
            repo_id="HigherHu/SVOR",
            local_dir=models,
            allow_patterns=[
                "remove_model_stage1.safetensors",
                "remove_model_stage2.safetensors",
            ],
        )
        _snapshot_download(
            repo_id="Wan-AI/Wan2.1-VACE-1.3B",
            local_dir=models / "Wan2.1-VACE-1.3B",
        )


def install_backend(
    backend_id: str,
    *,
    progress: ProgressCallback | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, object]:
    if backend_id not in {"fgt", "svor"}:
        raise ValueError(f"Unsupported installable backend: {backend_id}")
    if not _uses_managed_backend(backend_id):
        spec = REMOVAL_BACKENDS[backend_id]
        raise RuntimeError(
            f"{spec.display_name} uses explicit {spec.root_env}/{spec.python_env} overrides. "
            "OpenRoto will not modify that environment automatically."
        )
    if os.name != "nt":
        raise RuntimeError("Automatic removal-backend setup currently supports Windows only")

    spec = REMOVAL_BACKENDS[backend_id]
    _ensure_managed_base(backend_id)
    (_backend_base(backend_id) / "install.log").write_text("", encoding="utf-8")
    _check_cancelled(cancelled)
    _progress(progress, 0.12, f"Downloading {spec.display_name} source")
    _install_source(backend_id, cancelled=cancelled)
    _check_cancelled(cancelled)
    _progress(progress, 0.14, f"Preparing {spec.display_name} Python runtime")
    python = _ensure_python_runtime(backend_id, cancelled=cancelled)
    _check_cancelled(cancelled)
    _progress(progress, 0.16, f"Installing {spec.display_name} dependencies")
    _install_dependencies(backend_id, python, cancelled=cancelled)
    _check_cancelled(cancelled)
    if backend_id == "svor":
        _progress(progress, 0.18, "Downloading SVOR and Wan2.1 model weights")
    else:
        _progress(progress, 0.18, "Downloading FGT++ model weights")
    _install_weights(backend_id)
    status = backend_status(backend_id)
    if not bool(status["ready"]):
        missing = ", ".join(status.get("missing", []))
        raise RuntimeError(
            f"{spec.display_name} setup finished but is incomplete"
            + (f": {missing}" if missing else "")
        )
    _progress(progress, 0.20, f"{spec.display_name} is ready")
    return status


def run_external_backend(
    backend_id: str,
    *,
    frames_dir: str | Path,
    masks_dir: str | Path,
    output_dir: str | Path,
    frame_count: int,
    fps: float,
    padding: int,
    feather: float,
    temporal_radius: int,
    progress: ProgressCallback | None = None,
    timing: TimingCallback | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    if backend_id not in {"fgt", "svor"}:
        raise ValueError(f"Unsupported external removal backend: {backend_id}")
    status = backend_status(backend_id)
    if not bool(status["ready"]):
        if bool(status.get("installable")):
            status = install_backend(backend_id, progress=progress, cancelled=cancelled)
        else:
            spec = REMOVAL_BACKENDS[backend_id]
            raise RuntimeError(
                f"{spec.display_name} is not configured: {status['status']}. "
                f"Set {spec.python_env} and {spec.root_env} to a working sidecar environment."
            )
    if not bool(status["ready"]):
        raise RuntimeError(f"{REMOVAL_BACKENDS[backend_id].display_name} is not ready")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    job_path = destination.parent / f".{backend_id}-job.json"
    result_path = destination.parent / f".{backend_id}-result.json"
    log_path = destination.parent / f".{backend_id}-backend.log"
    job = {
        "backend": backend_id,
        "backend_root": str(backend_root(backend_id).resolve()),
        "frames_dir": str(Path(frames_dir).resolve()),
        "masks_dir": str(Path(masks_dir).resolve()),
        "output_dir": str(destination.resolve()),
        "frame_count": int(frame_count),
        "fps": float(fps),
        "padding": int(padding),
        "feather": float(feather),
        "temporal_radius": int(temporal_radius),
        "result_json": str(result_path.resolve()),
    }
    job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    result_path.unlink(missing_ok=True)

    runner = _runner_script(backend_id)
    if not runner.is_file():
        raise RuntimeError(f"OpenRoto backend runner is missing: {runner}")

    if progress:
        progress(0.22, f"Starting {REMOVAL_BACKENDS[backend_id].display_name}")
    started = time.perf_counter_ns()
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if os.name == "nt":
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    with log_path.open("w", encoding="utf-8", errors="replace") as log_stream:
        process = subprocess.Popen(
            [str(backend_python(backend_id)), str(runner), "--job", str(job_path)],
            cwd=str(backend_root(backend_id)),
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
        while process.poll() is None:
            if cancelled and cancelled():
                _terminate_process_tree(process)
                raise InterruptedError("Object removal was cancelled")
            if progress:
                progress(0.30, f"{REMOVAL_BACKENDS[backend_id].display_name} is processing")
            time.sleep(0.20)

    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
    if timing:
        timing("removal_inpaint", elapsed_ms)
    if process.returncode != 0:
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        tail = "\n".join(lines[-12:]).strip()
        raise RuntimeError(
            f"{REMOVAL_BACKENDS[backend_id].display_name} failed with exit code {process.returncode}"
            + (f":\n{tail}" if tail else "")
        )

    if result_path.is_file():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as error:
            raise RuntimeError(f"Could not read {backend_id} result metadata: {error}") from error
        if result.get("error"):
            raise RuntimeError(str(result["error"]))

    missing = [
        index
        for index in range(frame_count)
        if not (destination / f"removed_{index:08d}.png").is_file()
    ]
    if missing:
        raise RuntimeError(
            f"{REMOVAL_BACKENDS[backend_id].display_name} did not produce frame {missing[0] + 1}."
        )
    if progress:
        progress(0.90, f"{REMOVAL_BACKENDS[backend_id].display_name} removal ready")
    return destination
