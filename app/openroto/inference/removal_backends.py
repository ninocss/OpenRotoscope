from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
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
    download_size: str


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
        download_size="Built in",
    ),
    "fgt": RemovalBackendSpec(
        id="fgt",
        display_name="FGT++",
        description="Flow-guided transformer video inpainting. OpenRoto can install its isolated runtime and pretrained weights automatically.",
        quality="Balanced",
        speed="Medium",
        vram="GPU dependent",
        license="MIT",
        source_url="https://github.com/hitachinsk/FGT",
        python_env="OPENROTO_FGT_PYTHON",
        root_env="OPENROTO_FGT_ROOT",
        download_size="About 2 GB including runtime",
    ),
    "svor": RemovalBackendSpec(
        id="svor",
        display_name="SVOR",
        description="Diffusion video object removal for difficult motion, shadows and imperfect masks. OpenRoto can install the code, runtime and model weights automatically.",
        quality="High",
        speed="Slow",
        vram="~33 GB / ~24 GB with CPU offload",
        license="Apache-2.0",
        source_url="https://github.com/xiaomi-research/svor",
        python_env="OPENROTO_SVOR_PYTHON",
        root_env="OPENROTO_SVOR_ROOT",
        download_size="Several GB including Wan2.1-VACE-1.3B",
    ),
}

_SOURCE_ARCHIVES = {
    "fgt": "https://github.com/hitachinsk/FGT/archive/refs/heads/master.zip",
    "svor": "https://github.com/xiaomi-research/svor/archive/refs/heads/main.zip",
}

_PYTHON_RUNTIMES = {
    "fgt": ("3.9.13", "python39._pth"),
    "svor": ("3.10.11", "python310._pth"),
}


def _local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "OpenRoto"


def _backend_base(backend_id: str) -> Path:
    return _local_root() / "RemovalBackends" / backend_id


def _managed_root(backend_id: str) -> Path:
    return _backend_base(backend_id) / "repo"


def _managed_python(backend_id: str) -> Path:
    if os.name == "nt":
        return _backend_base(backend_id) / "runtime" / "python.exe"
    return _backend_base(backend_id) / "runtime" / "bin" / "python"


def _has_external_override(backend_id: str) -> bool:
    spec = REMOVAL_BACKENDS[backend_id]
    return bool(os.environ.get(spec.root_env, "") or os.environ.get(spec.python_env, ""))


def backend_root(backend_id: str) -> Path:
    spec = REMOVAL_BACKENDS[backend_id]
    explicit = os.environ.get(spec.root_env, "") if spec.root_env else ""
    if explicit:
        return Path(explicit).expanduser()
    return _managed_root(backend_id)


def backend_python(backend_id: str) -> Path:
    spec = REMOVAL_BACKENDS[backend_id]
    explicit = os.environ.get(spec.python_env, "") if spec.python_env else ""
    if explicit:
        return Path(explicit).expanduser()
    return _managed_python(backend_id)


def _weights_ready(backend_id: str, root: Path) -> bool:
    if backend_id == "fgt":
        required = (
            root / "FGT" / "checkpoint" / "fgt.pth.tar",
            root / "FGT" / "checkpoint" / "config.yaml",
            root / "LAFC" / "checkpoint" / "lafc.pth.tar",
            root / "LAFC" / "checkpoint" / "config.yaml",
            root / "FGT" / "flowCheckPoint" / "lafc_single.pth.tar",
            root / "FGT" / "flowCheckPoint" / "config.yaml",
        )
        return all(path.is_file() for path in required)
    if backend_id == "svor":
        models = root / "models"
        wan = models / "Wan2.1-VACE-1.3B"
        return (
            (models / "remove_model_stage1.safetensors").is_file()
            and (models / "remove_model_stage2.safetensors").is_file()
            and wan.is_dir()
            and any(wan.iterdir())
        )
    return True


def backend_status(backend_id: str) -> dict[str, object]:
    spec = REMOVAL_BACKENDS[backend_id]
    if backend_id == "temporal":
        return {
            **asdict(spec),
            "available": True,
            "status": "Built in",
            "root": "",
            "python": "",
            "managed": True,
            "can_manage": False,
            "install_root": "",
        }

    root = backend_root(backend_id)
    python = backend_python(backend_id)
    marker = root / ("tool/video_inpainting.py" if backend_id == "fgt" else "predict_SVOR.py")
    weights_ready = _weights_ready(backend_id, root) if marker.is_file() else False
    available = python.is_file() and marker.is_file() and weights_ready
    external = _has_external_override(backend_id)
    if available:
        status = "Ready (external)" if external else "Ready"
    elif not root.exists():
        status = "Not installed"
    elif not marker.is_file():
        status = "Repository incomplete"
    elif not python.is_file():
        status = "Python runtime missing"
    elif not weights_ready:
        status = "Model weights missing"
    else:
        status = "Incomplete"
    return {
        **asdict(spec),
        "available": available,
        "status": status,
        "root": str(root),
        "python": str(python),
        "managed": not external,
        "can_manage": not external,
        "install_root": str(_backend_base(backend_id)),
    }


def _download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "OpenRoto/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as stream:
        shutil.copyfileobj(response, stream)


def _extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"Unsafe path in downloaded archive: {member.filename}")
        bundle.extractall(destination)


def _download_source(backend_id: str, destination: Path, work: Path) -> None:
    archive = work / f"{backend_id}-source.zip"
    extracted = work / f"{backend_id}-source"
    _download_file(_SOURCE_ARCHIVES[backend_id], archive)
    _extract_zip(archive, extracted)
    candidates = [path for path in extracted.iterdir() if path.is_dir()]
    if len(candidates) != 1:
        raise RuntimeError(f"Could not identify the {backend_id} source directory")
    shutil.move(str(candidates[0]), str(destination))


def _run_checked(command: list[str], *, cwd: Path | None = None) -> None:
    process = subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )
    if process.returncode == 0:
        return
    tail = "\n".join(process.stdout.splitlines()[-20:]).strip()
    raise RuntimeError(
        f"Backend setup command failed with exit code {process.returncode}: {' '.join(command[:4])}"
        + (f"\n{tail}" if tail else "")
    )


def _prepare_embedded_python(backend_id: str, destination: Path, work: Path) -> Path:
    if os.name != "nt":
        raise RuntimeError(
            "Automatic FGT/SVOR installation is currently supported on Windows. "
            "On other platforms configure the backend with the OPENROTO_*_ROOT and OPENROTO_*_PYTHON variables."
        )
    version, pth_name = _PYTHON_RUNTIMES[backend_id]
    archive = work / f"python-{version}.zip"
    _download_file(
        f"https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip",
        archive,
    )
    _extract_zip(archive, destination)
    pth = destination / pth_name
    if not pth.is_file():
        raise RuntimeError(f"Downloaded Python {version} runtime is missing {pth_name}")
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
            has_import_site = has_import_site or stripped == "import site"
        if stripped.replace("/", "\\").lower() == "lib\\site-packages":
            has_site_packages = True
    if not has_site_packages:
        normalized.append(r"Lib\site-packages")
    if not has_import_site:
        normalized.append("import site")
    pth.write_text("\n".join(normalized) + "\n", encoding="utf-8")

    python = destination / "python.exe"
    get_pip = work / "get-pip.py"
    _download_file("https://bootstrap.pypa.io/get-pip.py", get_pip)
    _run_checked([str(python), str(get_pip), "--disable-pip-version-check"])
    _run_checked(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ]
    )
    return python


def _pip(python: Path, *arguments: str, cwd: Path | None = None) -> None:
    _run_checked(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", *arguments],
        cwd=cwd,
    )


def _install_fgt_dependencies(python: Path) -> None:
    if shutil.which("nvidia-smi"):
        _pip(
            python,
            "torch==1.10.1+cu113",
            "torchvision==0.11.2+cu113",
            "-f",
            "https://download.pytorch.org/whl/torch_stable.html",
        )
    else:
        _pip(python, "torch==1.10.1", "torchvision==0.11.2")
    _pip(
        python,
        "cvbase==0.5.5",
        "imageio==2.31.6",
        "imageio-ffmpeg==0.4.9",
        "matplotlib==3.7.5",
        "numpy==1.22.4",
        "opencv-python==4.8.1.78",
        "Pillow==9.5.0",
        "PyYAML==6.0.1",
        "scikit-image==0.19.3",
        "scipy==1.9.3",
        "tensorboardX==2.6.2.2",
    )


def _install_svor_dependencies(python: Path, root: Path) -> None:
    torch_index = (
        "https://download.pytorch.org/whl/cu126"
        if shutil.which("nvidia-smi")
        else "https://download.pytorch.org/whl/cpu"
    )
    _pip(
        python,
        "torch==2.7.0",
        "torchvision==0.22.0",
        "torchaudio==2.7.0",
        "--index-url",
        torch_index,
    )
    _pip(python, "-r", str(root / "requirements.txt"), cwd=root)


def _install_fgt_weights(root: Path, work: Path) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as error:
        raise RuntimeError("The Hugging Face model manager is not installed.") from error

    downloaded = work / "fgt-weights"
    snapshot_download(
        repo_id="hitachinsk/FGT",
        local_dir=str(downloaded),
        allow_patterns=["*.pth.tar", "*.yaml"],
    )
    copies = (
        ("fgt.pth.tar", root / "FGT" / "checkpoint" / "fgt.pth.tar"),
        ("FGT_config.yaml", root / "FGT" / "checkpoint" / "config.yaml"),
        ("lafc.pth.tar", root / "LAFC" / "checkpoint" / "lafc.pth.tar"),
        ("LAFC_config.yaml", root / "LAFC" / "checkpoint" / "config.yaml"),
        ("lafc_single.pth.tar", root / "FGT" / "flowCheckPoint" / "lafc_single.pth.tar"),
        ("LAFC_single_config.yaml", root / "FGT" / "flowCheckPoint" / "config.yaml"),
    )
    for source_name, destination in copies:
        source = downloaded / source_name
        if not source.is_file():
            raise RuntimeError(f"FGT model repository is missing {source_name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _install_svor_weights(root: Path) -> None:
    try:
        from huggingface_hub import hf_hub_download, snapshot_download
    except ImportError as error:
        raise RuntimeError("The Hugging Face model manager is not installed.") from error

    models = root / "models"
    models.mkdir(parents=True, exist_ok=True)
    for filename in ("remove_model_stage1.safetensors", "remove_model_stage2.safetensors"):
        hf_hub_download(repo_id="HigherHu/SVOR", filename=filename, local_dir=str(models))
    snapshot_download(
        repo_id="Wan-AI/Wan2.1-VACE-1.3B",
        local_dir=str(models / "Wan2.1-VACE-1.3B"),
    )


def install_backend(backend_id: str) -> None:
    if backend_id not in {"fgt", "svor"}:
        raise ValueError(f"Unsupported managed removal backend: {backend_id}")
    if _has_external_override(backend_id):
        spec = REMOVAL_BACKENDS[backend_id]
        raise RuntimeError(
            f"{spec.display_name} uses external paths from {spec.root_env}/{spec.python_env}. "
            "Unset those variables before using OpenRoto's automatic installer."
        )

    base = _backend_base(backend_id)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / ".installing"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    staged_root = staging / "repo"
    staged_runtime = staging / "runtime"
    try:
        _download_source(backend_id, staged_root, staging)
        python = _prepare_embedded_python(backend_id, staged_runtime, staging)
        if backend_id == "fgt":
            _install_fgt_dependencies(python)
            _install_fgt_weights(staged_root, staging)
        else:
            _install_svor_dependencies(python, staged_root)
            _install_svor_weights(staged_root)

        if not _weights_ready(backend_id, staged_root):
            raise RuntimeError(f"{REMOVAL_BACKENDS[backend_id].display_name} model download is incomplete")

        final_root = _managed_root(backend_id)
        final_runtime = _backend_base(backend_id) / "runtime"
        shutil.rmtree(final_root, ignore_errors=True)
        shutil.rmtree(final_runtime, ignore_errors=True)
        shutil.move(str(staged_root), str(final_root))
        shutil.move(str(staged_runtime), str(final_runtime))
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    status = backend_status(backend_id)
    if not status["available"]:
        raise RuntimeError(
            f"{REMOVAL_BACKENDS[backend_id].display_name} installation finished but is incomplete: {status['status']}"
        )


def remove_backend(backend_id: str) -> None:
    if backend_id not in {"fgt", "svor"}:
        raise ValueError(f"Unsupported managed removal backend: {backend_id}")
    if _has_external_override(backend_id):
        raise RuntimeError("OpenRoto will not remove an externally configured backend.")
    shutil.rmtree(_backend_base(backend_id), ignore_errors=True)


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
    if not status["available"]:
        spec = REMOVAL_BACKENDS[backend_id]
        raise RuntimeError(
            f"{spec.display_name} is not ready ({status['status']}). Install it in OpenRoto Settings "
            f"or set {spec.python_env} and {spec.root_env}."
        )

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
        progress(0.12, f"Starting {REMOVAL_BACKENDS[backend_id].display_name}")
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
                progress(0.15, f"{REMOVAL_BACKENDS[backend_id].display_name} is processing")
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
        progress(1.0, f"{REMOVAL_BACKENDS[backend_id].display_name} removal ready")
    return destination
