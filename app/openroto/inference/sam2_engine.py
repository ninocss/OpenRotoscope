from __future__ import annotations

import contextlib
import gc
import threading
from collections.abc import Callable
from pathlib import Path

import numpy as np

from openroto.core.models import ModelPreset, PointPrompt, TrackingDirection
from openroto.inference.catalog import MODEL_CATALOG
from openroto.inference.matte import save_raw_mask

ProgressCallback = Callable[[float, str], None]


class InferenceUnavailableError(RuntimeError):
    pass


class Sam2Engine:
    """Lazy SAM2.1 video predictor with on-disk masks for long sessions."""

    def __init__(self, frames_dir: str | Path, raw_masks_dir: str | Path) -> None:
        self.frames_dir = Path(frames_dir)
        self.raw_masks_dir = Path(raw_masks_dir)
        self.raw_masks_dir.mkdir(parents=True, exist_ok=True)
        self._preset: ModelPreset | None = None
        self._predictor = None
        self._state = None
        self._torch = None
        self._lock = threading.RLock()
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def reset_cancel(self) -> None:
        self._cancelled.clear()

    def load(self, preset: ModelPreset, progress: ProgressCallback | None = None) -> None:
        with self._lock:
            if self._preset == preset and self._predictor is not None and self._state is not None:
                return
            if progress:
                progress(0.02, f"Loading {MODEL_CATALOG[preset].display_name} model")
            try:
                import torch
                from sam2.sam2_video_predictor import SAM2VideoPredictor
            except ImportError as error:
                raise InferenceUnavailableError(
                    "SAM2 is not installed. Run OpenRoto Setup, then restart the app."
                ) from error

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._predictor = None
            self._state = None
            self._preset = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            try:
                predictor = SAM2VideoPredictor.from_pretrained(
                    MODEL_CATALOG[preset].repository, device=device
                )
            except Exception as error:
                raise InferenceUnavailableError(
                    f"Could not load {MODEL_CATALOG[preset].display_name}: {error}"
                ) from error
            if progress:
                progress(0.62, "Preparing video frames")
            frame_count = sum(
                1
                for path in self.frames_dir.iterdir()
                if path.suffix.lower() in {".png", ".jpg", ".jpeg"}
            )
            if frame_count == 0:
                raise InferenceUnavailableError("Resolve did not export any readable video frames.")
            try:
                state = predictor.init_state(
                    video_path=str(self.frames_dir),
                    offload_video_to_cpu=True,
                    offload_state_to_cpu=frame_count > 600,
                    async_loading_frames=frame_count > 120,
                )
            except Exception as error:
                raise InferenceUnavailableError(
                    f"Could not prepare the exported frames: {error}"
                ) from error
            self._predictor = predictor
            self._state = state
            self._torch = torch
            self._preset = preset
            if progress:
                progress(1.0, "Model ready")

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
        assert self._predictor is not None and self._state is not None
        coordinates = np.array([[point.x, point.y] for point in points], dtype=np.float32)
        frame_path = self._frame_path(frame)
        from PIL import Image

        with Image.open(frame_path) as image:
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
        mask = self._tensor_mask(logits[0])
        destination = self.raw_masks_dir / f"mask_{frame:08d}.png"
        return save_raw_mask(mask, destination)

    def track(
        self,
        prompts: dict[int, tuple[PointPrompt, ...]],
        frame_count: int,
        preset: ModelPreset,
        direction: TrackingDirection,
        progress: ProgressCallback | None = None,
    ) -> None:
        if not prompts:
            raise ValueError("Place at least one positive point before tracking")
        if frame_count <= 0:
            raise ValueError("The clip has no frames to track")
        if any(frame < 0 or frame >= frame_count for frame in prompts):
            raise ValueError("A prompt references a frame outside the clip")
        self.reset_cancel()
        self.load(preset, progress)
        assert self._predictor is not None and self._state is not None
        self._predictor.reset_state(self._state)
        for stale_mask in self.raw_masks_dir.glob("mask_*.png"):
            stale_mask.unlink(missing_ok=True)

        for frame, points in sorted(prompts.items()):
            if self._cancelled.is_set():
                raise InterruptedError("Tracking was cancelled")
            if not any(point.label.value == "positive" for point in points):
                raise ValueError(f"Frame {frame + 1} has no positive point")
            self.segment_frame(frame, points, preset, reset_cancel=False)

        seed = min(prompts)
        completed: set[int] = set(prompts)
        passes: list[tuple[bool, int]] = []
        if direction in {TrackingDirection.BOTH, TrackingDirection.FORWARD}:
            passes.append((False, seed))
        if direction in {TrackingDirection.BOTH, TrackingDirection.BACKWARD}:
            passes.append((True, max(prompts)))

        for reverse, start_frame in passes:
            with self._inference_context():
                iterator = self._predictor.propagate_in_video(
                    self._state, start_frame_idx=start_frame, reverse=reverse
                )
                for frame_index, object_ids, logits in iterator:
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
                    if progress:
                        progress(
                            len(completed) / frame_count,
                            f"Tracking frame {frame_index + 1}/{frame_count}",
                        )

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
            empty.save(destination, optimize=True)

    def _frame_path(self, frame: int) -> Path:
        candidates = (
            self.frames_dir / f"{frame:08d}.png",
            self.frames_dir / f"{frame:08d}.jpg",
            self.frames_dir / f"frame_{frame:08d}.png",
            self.frames_dir / f"frame_{frame + 1:08d}.png",
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
