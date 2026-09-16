from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ComputeDevice:
    backend: str
    name: str
    vram_gb: float
    available: bool
    detail: str = ""

    @property
    def display_name(self) -> str:
        if self.backend == "cuda":
            return f"CUDA · {self.name} · {self.vram_gb:.0f} GB"
        return self.name


def detect_compute_device() -> ComputeDevice:
    try:
        import torch
    except ImportError:
        return ComputeDevice(
            backend="unavailable",
            name="Inference runtime not installed",
            vram_gb=0,
            available=False,
            detail="Run OpenRoto Setup to install PyTorch and SAM2.",
        )

    try:
        if torch.cuda.is_available():
            index = torch.cuda.current_device()
            properties = torch.cuda.get_device_properties(index)
            return ComputeDevice(
                backend="cuda",
                name=properties.name,
                vram_gb=properties.total_memory / (1024**3),
                available=True,
                detail=f"CUDA {torch.version.cuda or 'runtime'}",
            )
    except Exception as error:
        return ComputeDevice(
            backend="unavailable",
            name="CUDA unavailable",
            vram_gb=0,
            available=False,
            detail=f"The NVIDIA runtime could not start: {error}",
        )

    return ComputeDevice(
        backend="cpu",
        name="CPU fallback",
        vram_gb=0,
        available=True,
        detail="No compatible NVIDIA CUDA device was detected. Tracking will be slow.",
    )
