from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from openroto.core.models import MatteSettings


def save_raw_mask(mask: np.ndarray, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = np.asarray(mask)
    if normalized.dtype == np.bool_:
        normalized = normalized.astype(np.uint8) * 255
    elif normalized.dtype == np.uint8:
        if normalized.size and int(normalized.max()) <= 1:
            normalized = normalized * 255
    else:
        normalized = np.clip(normalized, 0, 1)
        normalized = (normalized * 255).astype(np.uint8)
    # These masks are session working files. PNG optimization is lossless but
    # surprisingly expensive when SAM2 writes dozens/hundreds of frames, so use
    # a low compression level for much lower interactive/tracking latency.
    Image.fromarray(normalized, mode="L").save(path, compress_level=1)
    return path


def process_mask(
    source: str | Path, destination: str | Path, settings: MatteSettings
) -> Path:
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as loaded:
        alpha = loaded.convert("L")
        amount = settings.expand_contract
        if amount:
            kernel = min(65, abs(amount) * 2 + 1)
            alpha = alpha.filter(
                ImageFilter.MaxFilter(kernel) if amount > 0 else ImageFilter.MinFilter(kernel)
            )
        if settings.feather > 0:
            alpha = alpha.filter(ImageFilter.GaussianBlur(settings.feather))
        if settings.invert:
            alpha = ImageOps.invert(alpha)
        white = Image.new("RGB", alpha.size, "white")
        white.putalpha(alpha)
        # Final/preview files remain lossless; low PNG compression trades a
        # little temporary disk space for substantially faster UI and export.
        white.save(destination_path, compress_level=2)
    return destination_path


def render_matte_sequence(
    raw_dir: str | Path,
    final_dir: str | Path,
    frame_count: int,
    settings: MatteSettings,
    progress=None,
    cancelled=None,
) -> list[Path]:
    raw_root = Path(raw_dir)
    final_root = Path(final_dir)
    results: list[Path] = []
    for index in range(frame_count):
        if cancelled is not None and cancelled():
            raise InterruptedError("Matte rendering was cancelled")
        source = raw_root / f"mask_{index:08d}.png"
        if not source.exists():
            raise FileNotFoundError(f"Mask is missing for frame {index + 1}")
        destination = final_root / f"matte_{index:08d}.png"
        results.append(process_mask(source, destination, settings))
        if progress is not None:
            progress((index + 1) / frame_count, f"Rendering matte {index + 1}/{frame_count}")
    return results


def render_preview(
    source: str | Path, destination: str | Path, settings: MatteSettings
) -> Path:
    """Render a white-alpha preview that QML can tint without re-running SAM2."""
    return process_mask(source, destination, settings)
