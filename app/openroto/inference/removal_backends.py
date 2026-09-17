from __future__ import annotations

import json
import os
import signal
import subprocess
import time
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


def _local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "OpenRoto"


def backend_root(backend_id: str) -> Path:
    spec = REMOVAL_BACKENDS[backend_id]
    explicit = os.environ.get(spec.root_env, "") if spec.root_env else ""
    if explicit:
        return Path(explicit).expanduser()
    return _local_root() / "RemovalBackends" / backend_id / "repo"


def backend_python(backend_id: str) -> Path:
    spec = REMOVAL_BACKENDS[backend_id]
    explicit = os.environ.get(spec.python_env, "") if spec.python_env else ""
    if explicit:
        return Path(explicit).expanduser()
    base = _local_root() / "RemovalBackends" / backend_id / "venv"
    return base / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def backend_status(backend_id: str) -> dict[str, object]:
    spec = REMOVAL_BACKENDS[backend_id]
    if backend_id == "temporal":
        return {
            **asdict(spec),
            "available": True,
            "installed": True,
            "managed_installable": False,
            "status": "Built in",
            "root": "",
            "python": "",
        }

    root = backend_root(backend_id)
    python = backend_python(backend_id)
    marker = root / ("tool/video_inpainting.py" if backend_id == "fgt" else "predict_SVOR.py")
    installed = python.is_file() and marker.is_file()
    explicit = bool(os.environ.get(spec.root_env, "") or os.environ.get(spec.python_env, ""))
    managed_installable = not explicit

    if installed:
        status = "Ready"
    elif explicit and not root.exists():
        status = "Configured path missing"
    elif explicit and not marker.is_file():
        status = "Repository incomplete"
    elif explicit:
        status = "Python environment missing"
    elif root.exists() or python.exists():
        status = "Repair on first use"
    else:
        status = "Downloads on first use"

    return {
        **asdict(spec),
        # The UI uses `available` to decide whether a backend can be selected.
        # Managed backends are available even before installation because the
        # first inference operation installs them automatically.
        "available": installed or managed_installable,
        "installed": installed,
        "managed_installable": managed_installable,
        "status": status,
        "root": str(root),
        "python": str(python),
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
    if not bool(status.get("installed", False)) and bool(status.get("managed_installable", False)):
        from openroto.inference.removal_install import install_removal_backend

        install_removal_backend(backend_id, progress=progress, cancelled=cancelled)
        status = backend_status(backend_id)

    if not bool(status.get("installed", False)):
        spec = REMOVAL_BACKENDS[backend_id]
        raise RuntimeError(
            f"{spec.display_name} is not configured. Install its local sidecar environment "
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
