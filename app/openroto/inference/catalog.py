from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openroto.core.models import ModelPreset


@dataclass(frozen=True, slots=True)
class ModelSpec:
    preset: ModelPreset
    display_name: str
    repository: str
    approximate_download_mb: int
    minimum_vram_gb: int
    description: str


MODEL_CATALOG: dict[ModelPreset, ModelSpec] = {
    ModelPreset.FAST: ModelSpec(
        preset=ModelPreset.FAST,
        display_name="Fast",
        repository="facebook/sam2.1-hiera-tiny",
        approximate_download_mb=156,
        minimum_vram_gb=4,
        description="Lowest latency for previews and straightforward shots.",
    ),
    ModelPreset.BALANCED: ModelSpec(
        preset=ModelPreset.BALANCED,
        display_name="Balanced",
        repository="facebook/sam2.1-hiera-base-plus",
        approximate_download_mb=323,
        minimum_vram_gb=6,
        description="The recommended quality and speed balance.",
    ),
    ModelPreset.HIGH: ModelSpec(
        preset=ModelPreset.HIGH,
        display_name="High",
        repository="facebook/sam2.1-hiera-large",
        approximate_download_mb=898,
        minimum_vram_gb=10,
        description="Best detail retention for difficult motion and edges.",
    ),
}


def model_cache_dir(root: Path, preset: ModelPreset) -> Path:
    return root / preset.value

