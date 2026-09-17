from __future__ import annotations

import contextlib
import gc
import os
import shutil
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from openroto.core.models import ModelPreset, PointPrompt, TrackingDirection
from openroto.inference.catalog import MODEL_CATALOG
from openroto.inference.matte import save_raw_mask

ProgressCallback = Callable[[float, str], None]
TimingCallback = Callable[[str, float], None]
FrameReadyCallback = Callable[[int], None]


class InferenceUnavailableError(RuntimeError):
    pass


class Sam2Engine:
    """SAM2.1 predictor optimized for fast interactive prompts and video tracking."""

    def __init__(self, frames_dir: str | Path, raw_masks_dir: str | Path) -> None:
        self.frames_dir = Path(frames_dir)
        self.raw_masks_dir = Path(raw_masks_dir)
        self.raw_masks_dir.mkdir(parents=True, exist_ok=True)
        self._preset: ModelPreset | None = None
        self._predictor = None
        self._image_predictor = None
        self._state = None
        self._image_frame: int | None = None
        self._image_size: tuple[int, int] | None = None
        self._torch = None
        self._lock = threading.RLock()
        self._cancelled = threading.Event()
        self._timing_callback: TimingCallback | None = None

    def set_timing_callback(self, callback: TimingCallback | None) -> None:
        self._timing_callback = callback

    def _report_timing(self, key: str, started_ns: int) -> float:
        elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000.0
        callback = self._timing_callback
        if callback is not None:
            callback(key, elapsed_ms)
        return elapsed_ms

    def cancel(self) -> None:
        self._cancelled.set()

    def reset_cancel(self) -> None:
        self._cancelled.clear()

    def load(self, preset: ModelPreset, progress: ProgressCallback | None = None) -> None:
        """Load model weights only.

        Video-frame staging and ``init_state`` are intentionally deferred until
        tracking. A click selection only needs SAM2's image predictor and should
        not pay the cost of preparing an entire clip.
        """

        with self._lock:
            if self._preset == preset and self._predictor is not None:
                return
            if progress:
                progress(0.03, f"Loading {MODEL_CATALOG[preset].display_name} model")
            try:
                import torch
                from sam2.sam2_image_predictor import SAM2ImagePredictor
                from sam2.sam2_video_predictor import SAM2VideoPredictor
            except ImportError as error:
                raise InferenceUnavailableError(
                    "SAM2 is not installed. Run OpenRoto Setup, then restart the app."
                ) from error

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._predictor = None
            self._image_predictor = None
            self._state = None
            self._image_frame = None
            self._image_size = None
            self._preset = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                try:
                    properties = torch.cuda.get_device_properties(torch.cuda.current_device())
                    if properties.major >= 8:
                        torch.backends.cuda.matmul.allow_tf32 = True
                        torch.backends.cudnn.allow_tf32 = True
                except Exception:
                    pass
            started_ns = time.perf_counter_ns()
            try:
                predictor = SAM2VideoPredictor.from_pretrained(
                    MODEL_CATALOG[preset].repository, device=device
                )
                image_predictor = SAM2ImagePredictor(predictor)
            except Exception as error:
                raise InferenceUnavailableError(
                    f"Could not load {MODEL_CATALOG[preset].display_name}: {error}"
                ) from error
            finally:
                self._report_timing("model_load", started_ns)

            self._predictor = predictor
            self._image_predictor = image_predictor
            self._torch = torch
            self._preset = preset
            if progress:
                progress(0.28, "Model loaded")

    def prewarm_frame(self, frame: int, preset: ModelPreset) -> None:
        """Warm installed weights and the first image embedding without UI work."""

        try:
            self.load(preset)
            with self._lock:
                self._set_image_frame(frame)
        except Exception:
            # Prewarming is opportunistic. The interactive operation will report
            # a concrete error if loading actually fails when the user clicks.
            return

    def segment_frame(
        self,
        frame: int,
        points: tuple[PointPrompt, ...],
        preset: ModelPreset,
        progress: ProgressCallback | None = None,
        *,
        reset_cancel: bool = True,
    ) -> Path:
        if not points or not any(point.label.value == "positive" for point in points):
            raise ValueError("Place at least one positive point on the frame")
        if reset_cancel:
            self.reset_cancel()
        self.load(preset, progress)

        with self._lock:
            assert self._image_predictor is not None
            if progress:
                progress(0.36, f"Preparing frame {frame + 1}")
            width, height = self._set_image_frame(frame)
            coordinates = np.array([[point.x, point.y] for point in points], dtype=np.float32)
            coordinates[:, 0] *= width
            coordinates[:, 1] *= height
            labels = np.array(
                [1 if point.label.value == "positive" else 0 for point in points],
                dtype=np.int32,
            )
            if progress:
                progress(0.72, "Creating selection")
            started_ns = time.perf_counter_ns()
            try:
                with self._inference_context():
                    masks, _, _ = self._image_predictor.predict(
                        point_coords=coordinates,
                        point_labels=labels,
                        multimask_output=False,
                        normalize_coords=True,
                    )
            finally:
                self._report_timing("predict", started_ns)
            mask = np.asarray(masks[0], dtype=np.uint8)
            destination = self.raw_masks_dir / f"mask_{frame:08d}.png"
            result = save_raw_mask(mask, destination)
            if progress:
                progress(1.0, "Selection ready")
            return result

    def track(
        self,
        prompts: dict[int, tuple[PointPrompt, ...]],
        frame_count: int,
        preset: ModelPreset,
        direction: TrackingDirection,
        progress: ProgressCallback | None = None,
        *,
        frame_ready: FrameReadyCallback | None = None,
    ) -> None:
        if not prompts:
            raise ValueError("Place at least one positive point before tracking")
        if frame_count <= 0:
            raise ValueError("The clip has no frames to track")
        if any(frame < 0 or frame >= frame_count for frame in prompts):
            raise ValueError("A prompt references a frame outside the clip")
        self.reset_cancel()
        self.load(preset, progress)

        with self._lock:
            self._ensure_video_state(progress)
            assert self._predictor is not None and self._state is not None
            self._predictor.reset_state(self._state)
            for stale_mask in self.raw_masks_dir.glob("mask_*.png"):
                stale_mask.unlink(missing_ok=True)

            completed: set[int] = set()
            for frame, points in sorted(prompts.items()):
                if self._cancelled.is_set():
                    raise InterruptedError("Tracking was cancelled")
                if not any(point.label.value == "positive" for point in points):
                    raise ValueError(f"Frame {frame + 1} has no positive point")

                if hasattr(self._predictor, "add_new_points_or_box"):
                    logits = self._add_video_prompt(frame, points)
                    save_raw_mask(
                        self._tensor_mask(logits[0]),
                        self.raw_masks_dir / f"mask_{frame:08d}.png",
                    )
                else:
                    # Keep lightweight/custom predictor doubles usable. Real
                    # SAM2 video predictors always take the fast branch above.
                    self.segment_frame(frame, points, preset, reset_cancel=False)
                completed.add(frame)
                if frame_ready is not None:
                    frame_ready(frame)

            seed = min(prompts)
            passes: list[tuple[bool, int]] = []
            if direction in {TrackingDirection.BOTH, TrackingDirection.FORWARD}:
                passes.append((False, seed))
            if direction in {TrackingDirection.BOTH, TrackingDirection.BACKWARD}:
                passes.append((True, max(prompts)))

            propagate_ns = 0
            for reverse, start_frame in passes:
                with self._inference_context():
                    iterator = iter(
                        self._predictor.propagate_in_video(
                            self._state, start_frame_idx=start_frame, reverse=reverse
                        )
                    )
                    while True:
                        started_ns = time.perf_counter_ns()
                        try:
                            frame_index, object_ids, logits = next(iterator)
                        except StopIteration:
                            propagate_ns += time.perf_counter_ns() - started_ns
                            break
                        propagate_ns += time.perf_counter_ns() - started_ns
                        if self._cancelled.is_set():
                            raise InterruptedError("Tracking was cancelled")
                        frame_index = int(frame_index)
                        if not 0 <= frame_index < frame_count or not len(object_ids):
                            continue
                        save_raw_mask(
                            self._tensor_mask(logits[0]),
                            self.raw_masks_dir / f"mask_{frame_index:08d}.png",
                        )
                        completed.add(frame_index)
                        if frame_ready is not None:
                            frame_ready(frame_index)
                        if progress:
                            fraction = len(completed) / frame_count
                            progress(
                                min(1.0, 0.42 + 0.58 * fraction),
                                f"Tracking frame {frame_index + 1}/{frame_count}",
                            )
            if propagate_ns:
                callback = self._timing_callback
                if callback is not None:
                    callback("propagate", propagate_ns / 1_000_000.0)

            if direction == TrackingDirection.FORWARD:
                self._fill_untracked(0, seed, seed)
            elif direction == TrackingDirection.BACKWARD:
                self._fill_untracked(max(prompts) + 1, frame_count, max(prompts))

            missing = [
                frame
                for frame in range(frame_count)
                if not (self.raw_masks_dir / f"mask_{frame:08d}.png").is_file()
            ]
            if missing:
                raise InferenceUnavailableError(
                    f"Tracking did not produce a mask for frame {missing[0] + 1}."
                )

    def _set_image_frame(self, frame: int) -> tuple[int, int]:
        if self._image_frame == frame and self._image_size is not None:
            return self._image_size
        assert self._image_predictor is not None
        from PIL import Image

        frame_path = self._frame_path(frame)
        with Image.open(frame_path) as source:
            image = source.convert("RGB")
            size = image.size
            started_ns = time.perf_counter_ns()
            try:
                with self._inference_context():
                    self._image_predictor.set_image(image)
            finally:
                self._report_timing("image_embedding", started_ns)
        self._image_frame = frame
        self._image_size = size
        return size

    def _ensure_video_state(self, progress: ProgressCallback | None = None) -> None:
        if self._state is not None:
            return
        assert self._predictor is not None
        if progress:
            progress(0.06, "Preparing tracking frames")
        try:
            predictor_frames_dir, frame_count = self._prepare_predictor_frames(progress)
        except Exception as error:
            raise InferenceUnavailableError(
                f"Could not prepare the exported frames for SAM2: {error}"
            ) from error
        if progress:
            progress(0.30, "Initializing video tracking")
        started_ns = time.perf_counter_ns()
        try:
            self._state = self._predictor.init_state(
                video_path=str(predictor_frames_dir),
                offload_video_to_cpu=frame_count > 48,
                offload_state_to_cpu=frame_count > 600,
                async_loading_frames=frame_count > 120,
            )
        except Exception as error:
            raise InferenceUnavailableError(
                f"Could not prepare the exported frames: {error}"
            ) from error
        finally:
            self._report_timing("init_state", started_ns)
        if progress:
            progress(0.42, "Tracking ready")

    def _add_video_prompt(self, frame: int, points: tuple[PointPrompt, ...]):
        assert self._predictor is not None and self._state is not None
        from PIL import Image

        coordinates = np.array([[point.x, point.y] for point in points], dtype=np.float32)
        with Image.open(self._frame_path(frame)) as image:
            coordinates[:, 0] *= image.width
            coordinates[:, 1] *= image.height
        labels = np.array(
            [1 if point.label.value == "positive" else 0 for point in points],
            dtype=np.int32,
        )
        with self._inference_context():
            _, _, logits = self._predictor.add_new_points_or_box(
                inference_state=self._state,
                frame_idx=frame,
                obj_id=1,
                points=coordinates,
                labels=labels,
                clear_old_points=True,
                normalize_coords=True,
            )
        return logits

    def _prepare_predictor_frames(
        self, progress: ProgressCallback | None = None
    ) -> tuple[Path, int]:
        """Stage Resolve frames into SAM2's required numeric JPEG layout."""

        source_frames = sorted(
            (
                path
                for path in self.frames_dir.iterdir()
                if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
            ),
            key=lambda path: path.name.lower(),
        )
        frame_count = len(source_frames)
        if frame_count == 0:
            raise InferenceUnavailableError("Resolve did not export any readable video frames.")

        cache_dir = self.frames_dir / ".sam2-jpeg"
        expected = [cache_dir / f"{index:08d}.jpg" for index in range(frame_count)]
        cache_is_current = cache_dir.is_dir() and all(
            destination.is_file()
            and destination.stat().st_mtime_ns >= source.stat().st_mtime_ns
            for source, destination in zip(source_frames, expected, strict=True)
        )
        if cache_is_current:
            return cache_dir, frame_count

        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=False)

        from PIL import Image

        def encode(item: tuple[int, Path]) -> None:
            index, source = item
            if self._cancelled.is_set():
                raise InterruptedError("Preparing video frames was cancelled")
            destination = cache_dir / f"{index:08d}.jpg"
            with Image.open(source) as image:
                image.convert("RGB").save(
                    destination,
                    format="JPEG",
                    quality=93,
                    subsampling=0,
                    optimize=False,
                )

        workers = min(4, max(1, os.cpu_count() or 1))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="OpenRotoFrames") as executor:
            futures = [executor.submit(encode, item) for item in enumerate(source_frames)]
            for index, future in enumerate(futures):
                future.result()
                if progress and (index == frame_count - 1 or index % 16 == 0):
                    fraction = (index + 1) / frame_count
                    progress(
                        0.08 + 0.18 * fraction,
                        f"Preparing tracking frame {index + 1}/{frame_count}",
                    )

        return cache_dir, frame_count

    def _fill_untracked(self, start: int, end: int, source_frame: int) -> None:
        """Direction-only tracking produces transparent frames outside its pass."""
        source = self.raw_masks_dir / f"mask_{source_frame:08d}.png"
        if not source.exists():
            return
        from PIL import Image

        with Image.open(source) as image:
            empty = Image.new("L", image.size, 0)
        for frame in range(start, end):
            destination = self.raw_masks_dir / f"mask_{frame:08d}.png"
            empty.save(destination, compress_level=1)

    def _frame_path(self, frame: int) -> Path:
        candidates = (
            self.frames_dir / f"{frame:08d}.png",
            self.frames_dir / f"{frame:08d}.jpg",
            self.frames_dir / f"{frame:08d}.jpeg",
            self.frames_dir / f"frame_{frame:08d}.png",
            self.frames_dir / f"frame_{frame + 1:08d}.png",
            self.frames_dir / f"frame_{frame:08d}.jpg",
            self.frames_dir / f"frame_{frame + 1:08d}.jpg",
        )
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"Exported frame {frame + 1} is missing")

    def _inference_context(self):
        assert self._torch is not None
        stack = contextlib.ExitStack()
        stack.enter_context(self._torch.inference_mode())
        if self._torch.cuda.is_available():
            stack.enter_context(self._torch.autocast("cuda", dtype=self._torch.bfloat16))
        return stack

    @staticmethod
    def _tensor_mask(logit) -> np.ndarray:
        mask = (logit > 0.0).detach().to("cpu").numpy()
        return np.squeeze(mask).astype(np.uint8)
