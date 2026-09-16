from __future__ import annotations

import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageFilter

ProgressCallback = Callable[[float, str], None]
TimingCallback = Callable[[str, float], None]


@dataclass(slots=True)
class RemovalSettings:
    padding: int = 8
    feather: float = 2.0
    temporal_radius: int = 12

    def validate(self) -> None:
        if not 0 <= self.padding <= 32:
            raise ValueError("padding must be between 0 and 32 pixels")
        if not 0.0 <= self.feather <= 24.0:
            raise ValueError("feather must be between 0 and 24 pixels")
        if not 1 <= self.temporal_radius <= 60:
            raise ValueError("temporal_radius must be between 1 and 60 frames")


class RemovalEngine:
    """Local temporally-aware object removal.

    The default backend reconstructs masked pixels from the nearest temporal frame
    where that pixel is visible, then falls back to a spatially blurred estimate
    for pixels that remain occluded throughout the clip. The interface is kept
    backend-neutral so a learned video-inpainting backend can replace the fill
    stage without changing UI or Resolve integration.
    """

    def __init__(self, frames_dir: str | Path, masks_dir: str | Path) -> None:
        self.frames_dir = Path(frames_dir)
        self.masks_dir = Path(masks_dir)
        self._cancelled = threading.Event()
        self._timing_callback: TimingCallback | None = None

    def set_timing_callback(self, callback: TimingCallback | None) -> None:
        self._timing_callback = callback

    def cancel(self) -> None:
        self._cancelled.set()

    def reset_cancel(self) -> None:
        self._cancelled.clear()

    def remove(
        self,
        frame_count: int,
        output_dir: str | Path,
        settings: RemovalSettings,
        progress: ProgressCallback | None = None,
    ) -> Path:
        settings.validate()
        self.reset_cancel()
        destination = Path(output_dir)
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=False)

        started = time.perf_counter_ns()
        frames = [self._load_frame(index) for index in range(frame_count)]
        masks = [self._load_mask(index, settings.padding) for index in range(frame_count)]
        self._report("removal_prepare", started)
        if progress:
            progress(0.10, "Preparing removal frames")

        started = time.perf_counter_ns()
        for index in range(frame_count):
            if self._cancelled.is_set():
                raise InterruptedError("Object removal was cancelled")
            result = self._fill_frame(index, frames, masks, settings.temporal_radius)
            alpha = masks[index].astype(np.float32)
            if settings.feather > 0:
                feathered = Image.fromarray((alpha * 255).astype(np.uint8)).filter(
                    ImageFilter.GaussianBlur(radius=settings.feather)
                )
                alpha = np.asarray(feathered, dtype=np.float32) / 255.0
            alpha = alpha[..., None]
            composite = (
                frames[index].astype(np.float32) * (1.0 - alpha)
                + result.astype(np.float32) * alpha
            ).clip(0, 255).astype(np.uint8)
            Image.fromarray(composite, mode="RGB").save(
                destination / f"removed_{index:08d}.png", compress_level=1
            )
            if progress:
                progress(0.10 + 0.88 * ((index + 1) / frame_count), f"Removing object {index + 1}/{frame_count}")
        self._report("removal_inpaint", started)
        if progress:
            progress(1.0, "Removal ready")
        return destination

    def _fill_frame(
        self,
        index: int,
        frames: list[np.ndarray],
        masks: list[np.ndarray],
        radius: int,
    ) -> np.ndarray:
        target = frames[index]
        hole = masks[index].astype(bool)
        if not hole.any():
            return target.copy()

        result = target.copy()
        unresolved = hole.copy()
        order: list[int] = []
        for distance in range(1, radius + 1):
            before = index - distance
            after = index + distance
            if before >= 0:
                order.append(before)
            if after < len(frames):
                order.append(after)
        # Sparse global references help when the object stays put for many nearby frames.
        step = max(1, len(frames) // 12)
        order.extend(i for i in range(0, len(frames), step) if i != index)

        seen: set[int] = set()
        for candidate_index in order:
            if candidate_index in seen or not unresolved.any():
                continue
            seen.add(candidate_index)
            available = unresolved & ~masks[candidate_index].astype(bool)
            result[available] = frames[candidate_index][available]
            unresolved[available] = False

        if unresolved.any():
            blurred = np.asarray(
                Image.fromarray(target, mode="RGB").filter(ImageFilter.GaussianBlur(radius=18)),
                dtype=np.uint8,
            )
            result[unresolved] = blurred[unresolved]
        return result

    def _load_frame(self, index: int) -> np.ndarray:
        candidates = (
            self.frames_dir / f"{index:08d}.png",
            self.frames_dir / f"frame_{index:08d}.png",
            self.frames_dir / f"frame_{index + 1:08d}.png",
        )
        for path in candidates:
            if path.is_file():
                with Image.open(path) as image:
                    return np.asarray(image.convert("RGB"), dtype=np.uint8)
        raise FileNotFoundError(f"Exported frame {index + 1} is missing")

    def _load_mask(self, index: int, padding: int) -> np.ndarray:
        path = self.masks_dir / f"mask_{index:08d}.png"
        if not path.is_file():
            raise FileNotFoundError(f"Tracked mask {index + 1} is missing")
        with Image.open(path) as image:
            mask = image.convert("L")
            if padding > 0:
                # MaxFilter requires an odd kernel size. Cap it to keep the filter practical.
                kernel = min(65, padding * 2 + 1)
                mask = mask.filter(ImageFilter.MaxFilter(kernel))
            return (np.asarray(mask, dtype=np.uint8) > 0).astype(np.uint8)

    def _report(self, key: str, started_ns: int) -> None:
        if self._timing_callback is not None:
            self._timing_callback(key, (time.perf_counter_ns() - started_ns) / 1_000_000.0)
