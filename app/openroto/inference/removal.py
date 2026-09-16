from __future__ import annotations

import shutil
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageFilter

from openroto.inference.removal_backends import run_external_backend

ProgressCallback = Callable[[float, str], None]
TimingCallback = Callable[[str, float], None]


@dataclass(slots=True)
class RemovalSettings:
    padding: int = 8
    feather: float = 2.0
    temporal_radius: int = 12
    backend: str = "temporal"

    def validate(self) -> None:
        if not 0 <= self.padding <= 32:
            raise ValueError("padding must be between 0 and 32 pixels")
        if not 0.0 <= self.feather <= 24.0:
            raise ValueError("feather must be between 0 and 24 pixels")
        if not 1 <= self.temporal_radius <= 60:
            raise ValueError("temporal_radius must be between 1 and 60 frames")
        if self.backend not in {"temporal", "fgt", "svor"}:
            raise ValueError(f"unsupported removal backend: {self.backend}")


class RemovalEngine:
    """Video object removal with built-in and optional isolated model backends."""

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
        *,
        fps: float = 24.0,
    ) -> Path:
        settings.validate()
        if frame_count <= 0:
            raise ValueError("The clip has no frames to remove from")
        self.reset_cancel()
        self._load_frame.cache_clear()
        self._load_mask.cache_clear()

        destination = Path(output_dir)
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=False)

        started = time.perf_counter_ns()
        self._load_frame(0)
        self._load_mask(0, settings.padding)
        self._report("removal_prepare", started)
        if progress:
            progress(0.10, "Preparing removal frames")

        try:
            if settings.backend == "temporal":
                self._remove_temporal(frame_count, destination, settings, progress)
            else:
                self._remove_external(frame_count, destination, settings, fps, progress)
        finally:
            self._load_frame.cache_clear()
            self._load_mask.cache_clear()

        if progress:
            progress(1.0, "Removal ready")
        return destination

    def _remove_temporal(
        self,
        frame_count: int,
        destination: Path,
        settings: RemovalSettings,
        progress: ProgressCallback | None,
    ) -> None:
        started = time.perf_counter_ns()
        for index in range(frame_count):
            if self._cancelled.is_set():
                raise InterruptedError("Object removal was cancelled")
            target = self._load_frame(index)
            mask = self._load_mask(index, settings.padding)
            result = self._fill_frame(
                index,
                frame_count,
                settings.padding,
                settings.temporal_radius,
            )
            composite = self._masked_composite(target, result, mask, settings.feather)
            Image.fromarray(composite, mode="RGB").save(
                destination / f"removed_{index:08d}.png", compress_level=1
            )
            if progress:
                fraction = (index + 1) / frame_count
                progress(
                    0.10 + 0.88 * fraction,
                    f"Removing object {index + 1}/{frame_count}",
                )
        self._report("removal_inpaint", started)

    def _remove_external(
        self,
        frame_count: int,
        destination: Path,
        settings: RemovalSettings,
        fps: float,
        progress: ProgressCallback | None,
    ) -> None:
        generated = destination.parent / f".{settings.backend}-generated"
        backend_masks = destination.parent / f".{settings.backend}-masks"
        shutil.rmtree(generated, ignore_errors=True)
        shutil.rmtree(backend_masks, ignore_errors=True)
        backend_masks.mkdir(parents=True, exist_ok=False)
        try:
            for index in range(frame_count):
                if self._cancelled.is_set():
                    raise InterruptedError("Object removal was cancelled")
                padded = self._load_mask(index, settings.padding) * 255
                Image.fromarray(padded.astype(np.uint8), mode="L").save(
                    backend_masks / f"mask_{index:08d}.png", compress_level=1
                )
            run_external_backend(
                settings.backend,
                frames_dir=self.frames_dir,
                masks_dir=backend_masks,
                output_dir=generated,
                frame_count=frame_count,
                fps=fps,
                padding=settings.padding,
                feather=settings.feather,
                temporal_radius=settings.temporal_radius,
                progress=progress,
                timing=self._timing_callback,
                cancelled=self._cancelled.is_set,
            )
            for index in range(frame_count):
                if self._cancelled.is_set():
                    raise InterruptedError("Object removal was cancelled")
                generated_path = generated / f"removed_{index:08d}.png"
                if not generated_path.is_file():
                    raise RuntimeError(
                        f"The {settings.backend} backend did not return frame {index + 1}."
                    )
                target = self._load_frame(index)
                with Image.open(generated_path) as image:
                    model_result = np.asarray(image.convert("RGB"), dtype=np.uint8)
                if model_result.shape != target.shape:
                    model_result = np.asarray(
                        Image.fromarray(model_result, mode="RGB").resize(
                            (target.shape[1], target.shape[0]), Image.Resampling.LANCZOS
                        ),
                        dtype=np.uint8,
                    )
                mask = self._load_mask(index, settings.padding)
                composite = self._masked_composite(target, model_result, mask, settings.feather)
                Image.fromarray(composite, mode="RGB").save(
                    destination / f"removed_{index:08d}.png", compress_level=1
                )
                if progress:
                    progress(
                        0.92 + 0.07 * ((index + 1) / frame_count),
                        f"Finalizing {index + 1}/{frame_count}",
                    )
        finally:
            shutil.rmtree(generated, ignore_errors=True)
            shutil.rmtree(backend_masks, ignore_errors=True)

    @staticmethod
    def _masked_composite(
        target: np.ndarray,
        replacement: np.ndarray,
        mask: np.ndarray,
        feather: float,
    ) -> np.ndarray:
        alpha = mask.astype(np.float32)
        if feather > 0:
            feathered = Image.fromarray((alpha * 255).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(radius=feather)
            )
            alpha = np.asarray(feathered, dtype=np.float32) / 255.0
        alpha = alpha[..., None]
        return (
            target.astype(np.float32) * (1.0 - alpha)
            + replacement.astype(np.float32) * alpha
        ).clip(0, 255).astype(np.uint8)

    def _fill_frame(
        self,
        index: int,
        frame_count: int,
        padding: int,
        radius: int,
    ) -> np.ndarray:
        target = self._load_frame(index)
        hole = self._load_mask(index, padding).astype(bool)
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
            if after < frame_count:
                order.append(after)

        step = max(1, frame_count // 12)
        order.extend(i for i in range(0, frame_count, step) if i != index)

        seen: set[int] = set()
        for candidate_index in order:
            if candidate_index in seen or not unresolved.any():
                continue
            if self._cancelled.is_set():
                raise InterruptedError("Object removal was cancelled")
            seen.add(candidate_index)
            candidate_mask = self._load_mask(candidate_index, padding).astype(bool)
            available = unresolved & ~candidate_mask
            if not available.any():
                continue
            candidate = self._load_frame(candidate_index)
            result[available] = candidate[available]
            unresolved[available] = False

        if unresolved.any():
            blurred = np.asarray(
                Image.fromarray(target, mode="RGB").filter(ImageFilter.GaussianBlur(radius=18)),
                dtype=np.uint8,
            )
            result[unresolved] = blurred[unresolved]
        return result

    @lru_cache(maxsize=8)
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

    @lru_cache(maxsize=48)
    def _load_mask(self, index: int, padding: int) -> np.ndarray:
        path = self.masks_dir / f"mask_{index:08d}.png"
        if not path.is_file():
            raise FileNotFoundError(f"Tracked mask {index + 1} is missing")
        with Image.open(path) as image:
            mask = image.convert("L")
            if padding > 0:
                kernel = min(65, padding * 2 + 1)
                mask = mask.filter(ImageFilter.MaxFilter(kernel))
            return (np.asarray(mask, dtype=np.uint8) > 0).astype(np.uint8)

    def _report(self, key: str, started_ns: int) -> None:
        if self._timing_callback is not None:
            self._timing_callback(key, (time.perf_counter_ns() - started_ns) / 1_000_000.0)
