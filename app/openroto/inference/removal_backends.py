from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageFilter

ProgressCallback = Callable[[float, str], None]


@dataclass(frozen=True, slots=True)
class RemovalBackendSpec:
    id: str
    display_name: str
    quality: str
    speed: str
    vram: str
    license: str
    description: str
    setup_script: str | None = None
    runner_script: str | None = None
    approximate_download: str = ""


BACKENDS: dict[str, RemovalBackendSpec] = {
    "temporal": RemovalBackendSpec(
        id="temporal",
        display_name="Temporal Fill",
        quality="Preview",
        speed="Fast",
        vram="No extra GPU VRAM",
        license="OpenRoto",
        description="Built-in temporal pixel reconstruction. Best when the hidden background is visible in nearby frames.",
    ),
    "fgt": RemovalBackendSpec(
        id="fgt",
        display_name="FGT",
        quality="Balanced",
        speed="Medium",
        vram="Upstream does not publish a fixed VRAM requirement",
        license="MIT",
        description="Flow-Guided Transformer video inpainting using the official FGT code and pretrained weights in an isolated runtime.",
        setup_script="setup_fgt.ps1",
        runner_script="fgt_runner.py",
        approximate_download="~2–3 GB runtime + 0.2 GB model weights",
    ),
    "svor": RemovalBackendSpec(
        id="svor",
        display_name="SVOR",
        quality="High",
        speed="Slow",
        vram="~24 GB with model offload; ~33 GB full load",
        license="Apache-2.0",
        description="Stable Video Object Removal diffusion backend for difficult motion, mask defects, shadows and reflections.",
        setup_script="setup_svor.ps1",
        runner_script="svor_runner.py",
        approximate_download="Large: Wan2.1-VACE-1.3B + ~1.1 GB SVOR LoRAs + runtime",
    ),
}


@dataclass(slots=True)
class BackendRunResult:
    backend_id: str
    elapsed_ms: float
    peak_vram_mb: float | None
    frame_count: int

    @property
    def ms_per_frame(self) -> float:
        return self.elapsed_ms / max(1, self.frame_count)


def _local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "OpenRoto"


def backend_home() -> Path:
    return _local_root() / "RemovalBackends"


def backend_root(backend_id: str) -> Path:
    if backend_id not in BACKENDS or backend_id == "temporal":
        raise ValueError(f"Unknown external removal backend: {backend_id}")
    return backend_home() / backend_id


def support_root() -> Path:
    return Path(__file__).resolve().parent.parent / "removal_backends"


def backend_manifest_path(backend_id: str) -> Path:
    return backend_root(backend_id) / "backend.json"


def backend_is_installed(backend_id: str) -> bool:
    if backend_id == "temporal":
        return True
    try:
        manifest = _load_manifest(backend_id)
    except Exception:
        return False
    return (
        Path(manifest["python"]).is_file()
        and Path(manifest["runner"]).is_file()
        and Path(manifest["source"]).is_dir()
    )


def backend_rows(selected: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for spec in BACKENDS.values():
        installed = backend_is_installed(spec.id)
        rows.append(
            {
                "id": spec.id,
                "name": spec.display_name,
                "quality": spec.quality,
                "speed": spec.speed,
                "vram": spec.vram,
                "license": spec.license,
                "description": spec.description,
                "download": spec.approximate_download,
                "installed": installed,
                "selected": selected == spec.id,
                "status": "Built in" if spec.id == "temporal" else "Installed" if installed else "Not installed",
            }
        )
    return rows


def setup_backend(backend_id: str, progress: ProgressCallback | None = None) -> None:
    spec = BACKENDS.get(backend_id)
    if spec is None or spec.id == "temporal" or spec.setup_script is None or spec.runner_script is None:
        raise ValueError(f"Backend {backend_id!r} does not require setup")
    if os.name != "nt":
        raise RuntimeError("OpenRoto removal backend setup currently supports Windows only")

    script = support_root() / spec.setup_script
    runner = support_root() / spec.runner_script
    if not script.is_file() or not runner.is_file():
        raise FileNotFoundError("OpenRoto backend support files are missing from this build")

    destination = backend_root(backend_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if progress:
        progress(0.05, f"Setting up {spec.display_name}")

    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Destination",
        str(destination),
        "-RunnerSource",
        str(runner),
    ]
    completed = subprocess.run(
        command,
        cwd=str(destination.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log_path = destination.parent / f"{backend_id}-setup.log"
    log_path.write_text(
        (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else ""),
        encoding="utf-8",
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "backend setup failed").strip()
        raise RuntimeError(f"{spec.display_name} setup failed: {detail[-1200:]}")
    if not backend_is_installed(backend_id):
        raise RuntimeError(f"{spec.display_name} setup completed without a usable backend manifest")
    if progress:
        progress(1.0, f"{spec.display_name} installed")


def remove_backend(backend_id: str) -> None:
    if backend_id == "temporal":
        return
    root = backend_root(backend_id)
    home = backend_home().resolve()
    if root.resolve().parent != home:
        raise RuntimeError("Refusing to remove an unsafe backend folder")
    shutil.rmtree(root, ignore_errors=False)


def _load_manifest(backend_id: str) -> dict[str, str]:
    path = backend_manifest_path(backend_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    if str(data.get("id")) != backend_id:
        raise ValueError("Removal backend manifest id does not match its folder")
    for key in ("python", "runner", "source"):
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"Removal backend manifest is missing {key}")
    return {str(key): str(value) for key, value in data.items()}


def _frame_path(frames_dir: Path, index: int) -> Path:
    candidates = (
        frames_dir / f"{index:08d}.png",
        frames_dir / f"frame_{index:08d}.png",
        frames_dir / f"frame_{index + 1:08d}.png",
        frames_dir / f"{index:08d}.jpg",
        frames_dir / f"{index:08d}.jpeg",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Exported frame {index + 1} is missing")


def _padded_mask(mask_path: Path, padding: int, feather: float, size: tuple[int, int]) -> Image.Image:
    with Image.open(mask_path) as image:
        mask = image.convert("L")
        if mask.size != size:
            mask = mask.resize(size, Image.Resampling.NEAREST)
        if padding > 0:
            mask = mask.filter(ImageFilter.MaxFilter(min(65, padding * 2 + 1)))
        if feather > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
        return mask.copy()


class ExternalRemovalBackend:
    """Runs learned video-inpainting backends outside the PyInstaller process.

    Each backend owns an isolated Python environment and upstream checkout under
    LOCALAPPDATA. The sidecar contract is JSON-in/JSON-out so incompatible torch
    versions cannot contaminate OpenRoto's SAM2 runtime.
    """

    def __init__(self, backend_id: str) -> None:
        if backend_id not in {"fgt", "svor"}:
            raise ValueError(f"Unsupported learned removal backend: {backend_id}")
        self.backend_id = backend_id
        self._cancelled = threading.Event()
        self._process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancelled.set()
        process = self._process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def reset_cancel(self) -> None:
        self._cancelled.clear()

    def remove(
        self,
        frames_dir: str | Path,
        masks_dir: str | Path,
        indices: Iterable[int],
        output_dir: str | Path,
        *,
        width: int,
        height: int,
        fps: float,
        padding: int,
        feather: float,
        vram_gb: float,
        progress: ProgressCallback | None = None,
    ) -> BackendRunResult:
        self.reset_cancel()
        manifest = _load_manifest(self.backend_id)
        index_list = [int(value) for value in indices]
        if not index_list:
            raise ValueError("The removal backend received no video frames")

        frames_root = Path(frames_dir)
        masks_root = Path(masks_dir)
        destination = Path(output_dir)
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=False)
        raw_output = destination.parent / f".{destination.name}-{self.backend_id}-raw"
        shutil.rmtree(raw_output, ignore_errors=True)
        raw_output.mkdir(parents=True, exist_ok=False)

        token = uuid.uuid4().hex
        request_path = destination.parent / f".{self.backend_id}-{token}-request.json"
        result_path = destination.parent / f".{self.backend_id}-{token}-result.json"
        log_path = destination.parent / f".{self.backend_id}-{token}.log"
        frame_paths = [_frame_path(frames_root, index) for index in index_list]
        mask_paths = [masks_root / f"mask_{index:08d}.png" for index in index_list]
        missing_masks = [index_list[i] for i, path in enumerate(mask_paths) if not path.is_file()]
        if missing_masks:
            raise FileNotFoundError(f"Tracked mask {missing_masks[0] + 1} is missing")

        request = {
            "backend_id": self.backend_id,
            "source_dir": manifest["source"],
            "frame_paths": [str(path.resolve()) for path in frame_paths],
            "mask_paths": [str(path.resolve()) for path in mask_paths],
            "output_dir": str(raw_output.resolve()),
            "width": int(width),
            "height": int(height),
            "fps": float(fps),
            "vram_gb": float(vram_gb),
        }
        request_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
        started = time.perf_counter_ns()
        try:
            if progress:
                progress(0.12, f"Running {BACKENDS[self.backend_id].display_name}")
            with log_path.open("w", encoding="utf-8", errors="replace") as log:
                creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
                self._process = subprocess.Popen(
                    [manifest["python"], manifest["runner"], "--request", str(request_path), "--result", str(result_path)],
                    cwd=manifest["source"],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=creation_flags,
                )
                while self._process.poll() is None:
                    if self._cancelled.is_set():
                        self.cancel()
                        raise InterruptedError("Object removal was cancelled")
                    time.sleep(0.20)
                code = self._process.returncode
            self._process = None
            if code != 0:
                detail = log_path.read_text(encoding="utf-8", errors="replace")[-1800:]
                raise RuntimeError(f"{BACKENDS[self.backend_id].display_name} failed: {detail.strip()}")
            if not result_path.is_file():
                raise RuntimeError("Removal backend exited without a result report")
            result_data = json.loads(result_path.read_text(encoding="utf-8"))
            raw_paths = [raw_output / f"backend_{i:08d}.png" for i in range(len(index_list))]
            missing = [i for i, path in enumerate(raw_paths) if not path.is_file()]
            if missing:
                raise RuntimeError(f"Removal backend output is incomplete at frame {missing[0] + 1}")

            if progress:
                progress(0.92, "Compositing removal result")
            for sequence_index, original_index in enumerate(index_list):
                if self._cancelled.is_set():
                    raise InterruptedError("Object removal was cancelled")
                original_path = frame_paths[sequence_index]
                mask_path = mask_paths[sequence_index]
                with Image.open(original_path) as original_image, Image.open(raw_paths[sequence_index]) as generated_image:
                    original = original_image.convert("RGB")
                    generated = generated_image.convert("RGB")
                    if generated.size != original.size:
                        generated = generated.resize(original.size, Image.Resampling.LANCZOS)
                    mask = _padded_mask(mask_path, padding, feather, original.size)
                    composite = Image.composite(generated, original, mask)
                    composite.save(destination / f"removed_{sequence_index:08d}.png", compress_level=1)
                if progress:
                    progress(0.92 + 0.07 * ((sequence_index + 1) / len(index_list)), "Compositing removal result")

            elapsed_ms = float(result_data.get("elapsed_ms") or 0.0)
            if elapsed_ms <= 0:
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
            peak_raw = result_data.get("peak_vram_mb")
            peak_vram = float(peak_raw) if peak_raw is not None else None
            if progress:
                progress(1.0, "Removal ready")
            return BackendRunResult(self.backend_id, elapsed_ms, peak_vram, len(index_list))
        finally:
            self._process = None
            request_path.unlink(missing_ok=True)
            result_path.unlink(missing_ok=True)
            shutil.rmtree(raw_output, ignore_errors=True)
