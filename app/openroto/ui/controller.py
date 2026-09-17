from __future__ import annotations

import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    Property,
    QObject,
    QSettings,
    QTimer,
    QUrl,
    Signal,
    Slot,
)

from openroto.core.ipc import BridgeClient
from openroto.core.models import (
    MatteSettings,
    ModelPreset,
    PointLabel,
    PointPrompt,
    SessionManifest,
    TrackingDirection,
)
from openroto.core.point_store import PointStore
from openroto.inference.device import ComputeDevice, detect_compute_device
from openroto.inference.matte import render_matte_sequence, render_preview
from openroto.inference.sam2_engine import Sam2Engine
from openroto.ui.mica import reduced_motion_enabled, system_uses_dark_mode


_TIMING_LABELS = (
    ("model_load", "Model Load"),
    ("image_embedding", "Image Embedding"),
    ("predict", "Predict"),
    ("preview", "Preview"),
    ("init_state", "Init State"),
    ("propagate", "Propagate"),
)


class ApplicationController(QObject):
    changed = Signal()
    pointsChanged = Signal()
    frameChanged = Signal()
    maskChanged = Signal()
    progressChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()
    trackingStateChanged = Signal()
    connectionChanged = Signal()
    themeChanged = Signal()
    timingsChanged = Signal()
    bridgeMessage = Signal("QVariantMap")
    workerProgress = Signal(float, str, str)
    workerTiming = Signal(str, float)
    workerMaskReady = Signal(int)
    previewRendered = Signal(int, int)
    viewerFrameReady = Signal(int)
    operationFinished = Signal(str, str)
    closeRequested = Signal()

    def __init__(self, manifest: SessionManifest) -> None:
        super().__init__()
        self.manifest = manifest
        self._settings = QSettings("OpenRoto", "OpenRoto")
        saved_preset = self._settings.value("modelPreset", ModelPreset.BALANCED.value)
        try:
            self._model_preset = ModelPreset(str(saved_preset))
        except ValueError:
            self._model_preset = ModelPreset.BALANCED
        self._direction = TrackingDirection.BOTH
        self._matte_settings = MatteSettings()
        self._points = PointStore()
        self._current_frame = 0
        self._mask_revision = 0
        self._progress = 0.0
        self._status = "Ready to select a subject"
        self._detail = "Left-click the subject. Right-click to exclude an area."
        self._busy = False
        self._tracking_dirty = True
        self._closed = False
        self._completed = False
        self._bridge_failed = False
        self._close_when_idle = False
        self._bridge_connected = False
        self._dark_mode = system_uses_dark_mode()
        self._reduced_motion = reduced_motion_enabled()
        self._cancel = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="OpenRoto")
        self._preview_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="OpenRotoPreview"
        )
        self._viewer_executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="OpenRotoViewer"
        )
        self._preview_settings_revision = 0
        self._preview_versions: dict[int, int] = {}
        self._viewer_pending: set[int] = set()
        self._raw_dir = Path(manifest.matte_dir) / "raw"
        self._final_dir = Path(manifest.matte_dir) / "final"
        self._preview_dir = Path(manifest.matte_dir) / "preview"
        self._viewer_dir = Path(manifest.matte_dir) / "viewer"
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        self._preview_dir.mkdir(parents=True, exist_ok=True)
        self._viewer_dir.mkdir(parents=True, exist_ok=True)
        self._timings: dict[str, float | None] = {key: None for key, _label in _TIMING_LABELS}
        self._engine = Sam2Engine(manifest.frames_dir, self._raw_dir)
        self._engine.set_timing_callback(lambda key, ms: self.workerTiming.emit(key, ms))
        self._device: ComputeDevice = detect_compute_device()
        self._bridge = BridgeClient(
            manifest.bridge_host,
            manifest.bridge_port,
            manifest.token,
            on_message=lambda message: self.bridgeMessage.emit(message),
            on_disconnect=lambda reason: self.bridgeMessage.emit(
                {"type": "disconnected", "message": reason}
            ),
        )
        self.bridgeMessage.connect(self._on_bridge_message)
        self.workerProgress.connect(self._set_progress_from_worker)
        self.workerTiming.connect(self._set_timing_from_worker)
        self.workerMaskReady.connect(self._on_worker_mask_ready)
        self.previewRendered.connect(self._on_preview_rendered)
        self.viewerFrameReady.connect(self._on_viewer_frame_ready)
        self.operationFinished.connect(self._finish_operation)
        try:
            self._bridge.connect()
            self._bridge_connected = True
        except Exception as error:
            self._status = "Resolve connection unavailable"
            self._detail = str(error)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self._queue_current_preview)
        self._theme_timer = QTimer(self)
        self._theme_timer.setInterval(1000)
        self._theme_timer.timeout.connect(self._refresh_theme)
        self._theme_timer.start()
        QTimer.singleShot(0, lambda: self._queue_viewer_prefetch(self._current_frame))

    @Property(str, constant=True)
    def clipName(self) -> str:
        return self.manifest.clip_name

    @Property(str, constant=True)
    def clipMeta(self) -> str:
        return (
            f"{self.manifest.width} × {self.manifest.height}  ·  "
            f"{self.manifest.fps:g} fps  ·  {self.manifest.frame_count} frames"
        )

    @Property(int, notify=frameChanged)
    def currentFrame(self) -> int:
        return self._current_frame

    @Property(int, constant=True)
    def frameCount(self) -> int:
        return self.manifest.frame_count

    @Property(str, notify=frameChanged)
    def frameLabel(self) -> str:
        return f"{self._current_frame + 1} / {self.manifest.frame_count}"

    @Property(float, constant=True)
    def clipFps(self) -> float:
        return float(self.manifest.fps)

    @Property(QUrl, notify=frameChanged)
    def currentFrameUrl(self) -> QUrl:
        return self._viewer_frame_url(self._current_frame)

    @Slot(int, result=QUrl)
    def frameUrlAt(self, frame: int) -> QUrl:
        bounded = max(0, min(int(frame), self.manifest.frame_count - 1))
        return self._viewer_frame_url(bounded)

    @Property(QUrl, notify=maskChanged)
    def currentMaskUrl(self) -> QUrl:
        frame = self._current_frame
        preview = self._preview_path(frame)
        if (
            self._preview_versions.get(frame) == self._preview_settings_revision
            and preview.exists()
        ):
            path = preview
        else:
            path = self._raw_path(frame)
        if not path.exists():
            return QUrl()
        url = QUrl.fromLocalFile(str(path))
        url.setQuery(f"v={self._mask_revision}")
        return url

    @Property("QVariantList", notify=pointsChanged)
    def points(self) -> list[dict[str, Any]]:
        return [
            {"x": point.x, "y": point.y, "positive": point.label == PointLabel.POSITIVE}
            for point in self._points.for_frame(self._current_frame)
        ]

    @Property("QVariantList", notify=timingsChanged)
    def performanceTimings(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key, label in _TIMING_LABELS:
            value = self._timings[key]
            rows.append(
                {
                    "key": key,
                    "label": label,
                    "measured": value is not None,
                    "ms": -1.0 if value is None else value,
                    "value": "—" if value is None else f"{value:,.1f} ms",
                }
            )
        return rows

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        return self._progress

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(str, notify=statusChanged)
    def detail(self) -> str:
        return self._detail

    @Property(str, notify=changed)
    def modelPreset(self) -> str:
        return self._model_preset.value

    @Property(str, notify=changed)
    def trackingDirection(self) -> str:
        return self._direction.value

    @Property(str, constant=True)
    def computeDevice(self) -> str:
        return self._device.display_name

    @Property(str, constant=True)
    def computeBadge(self) -> str:
        if self._device.backend == "cuda":
            return f"CUDA · {self._device.vram_gb:.0f} GB"
        return self._device.name

    @Property(str, constant=True)
    def computeDetail(self) -> str:
        return self._device.detail

    @Property(float, notify=changed)
    def overlayOpacity(self) -> float:
        return self._matte_settings.overlay_opacity

    @Property(int, notify=changed)
    def expandContract(self) -> int:
        return self._matte_settings.expand_contract

    @Property(float, notify=changed)
    def feather(self) -> float:
        return self._matte_settings.feather

    @Property(bool, notify=changed)
    def invert(self) -> bool:
        return self._matte_settings.invert

    @Property(bool, notify=themeChanged)
    def darkMode(self) -> bool:
        return self._dark_mode

    @Property(bool, constant=True)
    def reducedMotion(self) -> bool:
        return self._reduced_motion

    @Property(bool, notify=pointsChanged)
    def canUndo(self) -> bool:
        return self._points.can_undo

    @Property(bool, notify=pointsChanged)
    def canRedo(self) -> bool:
        return self._points.can_redo

    @Property(bool, notify=pointsChanged)
    def hasPrompts(self) -> bool:
        return bool(self._points.all())

    @Property(int, notify=pointsChanged)
    def promptCount(self) -> int:
        return len(self._points.all())

    @Property(bool, notify=trackingStateChanged)
    def trackingDirty(self) -> bool:
        return self._tracking_dirty

    @Property(bool, notify=trackingStateChanged)
    def trackingReady(self) -> bool:
        return bool(self._points.all()) and not self._tracking_dirty

    @Property(bool, notify=connectionChanged)
    def bridgeConnected(self) -> bool:
        return self._bridge_connected

    @Slot(int)
    def setFrame(self, frame: int) -> None:
        bounded = max(0, min(int(frame), self.manifest.frame_count - 1))
        if bounded == self._current_frame:
            return
        self._current_frame = bounded
        self.frameChanged.emit()
        self.pointsChanged.emit()
        self.maskChanged.emit()
        self._schedule_preview_refresh()
        self._queue_viewer_prefetch(bounded)

    @Slot(float, float, bool)
    def addPoint(self, x: float, y: float, positive: bool) -> None:
        if self._busy or not (0 <= x <= 1 and 0 <= y <= 1):
            return
        self._points.add(
            PointPrompt(
                frame=self._current_frame,
                x=x,
                y=y,
                label=PointLabel.POSITIVE if positive else PointLabel.NEGATIVE,
            )
        )
        self._mark_tracking_dirty()
        self.pointsChanged.emit()
        current_points = self._points.for_frame(self._current_frame)
        if any(point.label == PointLabel.POSITIVE for point in current_points):
            self._run_async("Creating mask", self._segment_current_frame)
        else:
            self._status = "Add a positive point"
            self._detail = "Right-click exclusions need a left-click subject point on this frame."
            self.statusChanged.emit()

    @Slot()
    def undo(self) -> None:
        if self._busy:
            return
        point = self._points.undo()
        if point is None:
            return
        self._show_history_frame(point.frame)
        self._mark_tracking_dirty()
        self.pointsChanged.emit()
        self._rerun_or_clear_current()

    @Slot()
    def redo(self) -> None:
        if self._busy:
            return
        point = self._points.redo()
        if point is None:
            return
        self._show_history_frame(point.frame)
        self._mark_tracking_dirty()
        self.pointsChanged.emit()
        self._rerun_or_clear_current()

    @Slot()
    def clearFrame(self) -> None:
        if self._busy:
            return
        self._points.clear_frame(self._current_frame)
        self._mark_tracking_dirty()
        self._raw_path(self._current_frame).unlink(missing_ok=True)
        self._preview_path(self._current_frame).unlink(missing_ok=True)
        self._preview_versions.pop(self._current_frame, None)
        self.pointsChanged.emit()
        self.maskChanged.emit()

    @Slot(str)
    def setModelPreset(self, value: str) -> None:
        try:
            preset = ModelPreset(value)
        except ValueError:
            return
        if preset != self._model_preset:
            self._model_preset = preset
            self._settings.setValue("modelPreset", value)
            self._mark_tracking_dirty()
            self._reset_timings()
            self.changed.emit()

    @Slot(str)
    def setTrackingDirection(self, value: str) -> None:
        try:
            direction = TrackingDirection(value)
        except ValueError:
            return
        if direction != self._direction:
            self._direction = direction
            self._mark_tracking_dirty()
            self.changed.emit()

    @Slot(float)
    def setOverlayOpacity(self, value: float) -> None:
        self._matte_settings.overlay_opacity = max(0.0, min(1.0, float(value)))
        self.changed.emit()

    @Slot(int)
    def setExpandContract(self, value: int) -> None:
        self._matte_settings.expand_contract = max(-32, min(32, int(value)))
        self.changed.emit()
        self._invalidate_preview_settings()

    @Slot(float)
    def setFeather(self, value: float) -> None:
        self._matte_settings.feather = max(0.0, min(64.0, float(value)))
        self.changed.emit()
        self._invalidate_preview_settings()

    @Slot(bool)
    def setInvert(self, value: bool) -> None:
        self._matte_settings.invert = bool(value)
        self.changed.emit()
        self._invalidate_preview_settings()

    @Slot()
    def track(self) -> None:
        if self._busy or not self._points.all():
            return
        self._run_async("Tracking subject", self._track)

    @Slot()
    def renderAndApply(self) -> None:
        if self._busy or not self._points.all() or not self._bridge_connected:
            return
        self._run_async("Rendering matte", self._render_and_apply)

    @Slot()
    def cancel(self) -> None:
        self._cancel.set()
        self._engine.cancel()
        self._status = "Cancelling…"
        self.statusChanged.emit()

    @Slot()
    def closeSession(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._cancel.set()
        self._engine.cancel()
        self._theme_timer.stop()
        self._preview_timer.stop()
        try:
            if self._bridge.connected and not self._completed:
                self._bridge.send("cancel", reason="window_closed")
        finally:
            self._bridge.close()
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._preview_executor.shutdown(wait=False, cancel_futures=True)
            self._viewer_executor.shutdown(wait=False, cancel_futures=True)

    @Slot(result=bool)
    def requestClose(self) -> bool:
        if self._completed or not self._busy:
            return True
        if self._status == "Waiting for Resolve":
            self._detail = "Resolve is applying the matte. The window will close when it finishes."
            self.statusChanged.emit()
            return False
        self._close_when_idle = True
        self.cancel()
        return False

    def _segment_current_frame(self) -> None:
        frame = self._current_frame
        points = self._points.for_frame(frame)
        if not points:
            return
        self._engine.segment_frame(frame, points, self._model_preset, self._worker_progress)
        self.workerMaskReady.emit(frame)

    def _track(self) -> None:
        self._engine.track(
            self._points.by_frame(),
            self.manifest.frame_count,
            self._model_preset,
            self._direction,
            self._worker_progress,
            frame_ready=self.workerMaskReady.emit,
        )
        self._tracking_dirty = False
        self.trackingStateChanged.emit()

    def _render_and_apply(self) -> None:
        missing = [
            index
            for index in range(self.manifest.frame_count)
            if not self._raw_path(index).exists()
        ]
        if missing or self._tracking_dirty:
            self._track()
        if self._final_dir.exists():
            if self._final_dir.is_symlink() or self._final_dir.resolve().parent != Path(
                self.manifest.matte_dir
            ).resolve():
                raise RuntimeError("Refusing to replace an unsafe matte output folder")
            shutil.rmtree(self._final_dir)
        render_matte_sequence(
            self._raw_dir,
            self._final_dir,
            self.manifest.frame_count,
            self._matte_settings,
            progress=self._worker_progress,
            cancelled=self._cancel.is_set,
        )
        if self._cancel.is_set():
            raise InterruptedError("Rendering was cancelled")
        self._bridge.send(
            "apply",
            session_id=self.manifest.session_id,
            matte_dir=str(self._final_dir),
            matte_pattern="matte_%08d.png",
            frame_count=self.manifest.frame_count,
        )
        self._set_progress_from_worker(1.0, "Waiting for Resolve", "Applying the matte")

    def _rerun_or_clear_current(self) -> None:
        if self._points.for_frame(self._current_frame):
            self._run_async("Updating mask", self._segment_current_frame)
        else:
            self._raw_path(self._current_frame).unlink(missing_ok=True)
            self._preview_path(self._current_frame).unlink(missing_ok=True)
            self.maskChanged.emit()

    def _run_async(self, title: str, operation) -> None:
        self._cancel.clear()
        self._busy = True
        self._progress = 0.0
        self._status = title
        self._detail = ""
        self.busyChanged.emit()
        self.progressChanged.emit()
        self.statusChanged.emit()
        future = self._executor.submit(operation)

        def completed(task) -> None:
            try:
                task.result()
            except InterruptedError as error:
                self.operationFinished.emit("Cancelled", str(error))
            except Exception as error:
                self.operationFinished.emit("Something went wrong", str(error))
            else:
                self.operationFinished.emit("Ready", "")

        future.add_done_callback(completed)

    def _finish_operation(self, status: str, detail: str) -> None:
        if status == "Ready" and self._status == "Waiting for Resolve":
            return
        if status == "Ready":
            if self._tracking_dirty:
                status = "Prompt updated"
                detail = "Add corrections on difficult frames, then track the whole clip."
            else:
                status = "Tracking ready"
                detail = "Review the result or render the matte back to Resolve."
        self._busy = False
        self._status = status
        self._detail = detail
        self.busyChanged.emit()
        self.statusChanged.emit()
        self.progressChanged.emit()
        self.maskChanged.emit()
        if self._close_when_idle:
            self._close_when_idle = False
            QTimer.singleShot(0, self.closeRequested.emit)

    def _worker_progress(self, value: float, message: str) -> None:
        self.workerProgress.emit(value, message, "")

    def _set_progress_from_worker(self, value: float, status: str, detail: str) -> None:
        self._progress = max(0.0, min(1.0, value))
        self._status = status
        if detail:
            self._detail = detail
        self.progressChanged.emit()
        self.statusChanged.emit()

    @Slot(str, float)
    def _set_timing_from_worker(self, key: str, elapsed_ms: float) -> None:
        if key not in self._timings:
            return
        self._timings[key] = max(0.0, float(elapsed_ms))
        self.timingsChanged.emit()

    def _reset_timings(self) -> None:
        for key in self._timings:
            self._timings[key] = None
        self.timingsChanged.emit()

    @Slot("QVariantMap")
    def _on_bridge_message(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        if message_type == "progress":
            self._progress = float(message.get("progress", self._progress))
            self._status = str(message.get("message", self._status))
            self._detail = str(message.get("detail", ""))
            self.progressChanged.emit()
            self.statusChanged.emit()
        elif message_type == "completed":
            self._completed = True
            self._bridge_connected = False
            self._busy = False
            self._progress = 1.0
            self._status = "Applied in DaVinci Resolve"
            self._detail = "The source remains available inside the OpenRoto compound clip."
            self.busyChanged.emit()
            self.connectionChanged.emit()
            self.progressChanged.emit()
            self.statusChanged.emit()
            QTimer.singleShot(1100, self.closeRequested.emit)
        elif message_type == "error":
            self._bridge_failed = True
            self._bridge_connected = False
            self._busy = False
            self._status = "Resolve could not apply the matte"
            self._detail = str(message.get("message", "Unknown Resolve error"))
            self.busyChanged.emit()
            self.connectionChanged.emit()
            self.statusChanged.emit()
        elif (
            message_type == "disconnected"
            and not self._completed
            and not self._bridge_failed
            and not self._closed
        ):
            self._busy = False
            self._bridge_connected = False
            self._status = "Resolve connection lost"
            self._detail = str(message.get("message", "Reconnect by starting a new session."))
            self.busyChanged.emit()
            self.connectionChanged.emit()
            self.statusChanged.emit()

    def _invalidate_preview_settings(self) -> None:
        self._preview_settings_revision += 1
        self._preview_versions.clear()
        self._mask_revision += 1
        self.maskChanged.emit()
        self._schedule_preview_refresh()

    def _schedule_preview_refresh(self) -> None:
        if self._closed or not self._raw_path(self._current_frame).exists():
            return
        self._preview_timer.start()

    @Slot()
    def _queue_current_preview(self) -> None:
        if self._closed:
            return
        frame = self._current_frame
        raw = self._raw_path(frame)
        if not raw.exists():
            return
        revision = self._preview_settings_revision
        settings = MatteSettings(
            invert=self._matte_settings.invert,
            expand_contract=self._matte_settings.expand_contract,
            feather=self._matte_settings.feather,
            overlay_opacity=self._matte_settings.overlay_opacity,
        )
        self._preview_executor.submit(self._render_preview_job, frame, revision, settings)

    def _render_preview_job(
        self, frame: int, revision: int, settings: MatteSettings
    ) -> None:
        raw = self._raw_path(frame)
        if not raw.exists():
            return
        started_ns = time.perf_counter_ns()
        try:
            render_preview(raw, self._preview_path(frame), settings)
        except (FileNotFoundError, OSError):
            return
        finally:
            self.workerTiming.emit(
                "preview", (time.perf_counter_ns() - started_ns) / 1_000_000.0
            )
        self.previewRendered.emit(frame, revision)

    @Slot(int, int)
    def _on_preview_rendered(self, frame: int, revision: int) -> None:
        if revision != self._preview_settings_revision:
            return
        if not self._preview_path(frame).exists():
            return
        self._preview_versions[frame] = revision
        if frame == self._current_frame:
            self._mask_revision += 1
            self.maskChanged.emit()

    @Slot(int)
    def _on_worker_mask_ready(self, frame: int) -> None:
        self._preview_versions.pop(frame, None)
        if frame != self._current_frame:
            return
        self._mask_revision += 1
        self.maskChanged.emit()
        self._schedule_preview_refresh()

    def _viewer_frame_url(self, frame: int) -> QUrl:
        proxy = self._viewer_path(frame)
        path = proxy if proxy.exists() else self._frame_path(frame)
        return QUrl.fromLocalFile(str(path))

    def _queue_viewer_prefetch(self, center: int) -> None:
        if self._closed:
            return
        for frame in (center, center + 1, center + 2, center - 1):
            if not 0 <= frame < self.manifest.frame_count:
                continue
            if self._viewer_path(frame).exists() or frame in self._viewer_pending:
                continue
            self._viewer_pending.add(frame)
            self._viewer_executor.submit(self._build_viewer_proxy, frame)

    def _build_viewer_proxy(self, frame: int) -> None:
        try:
            from PIL import Image

            source = self._frame_path(frame)
            destination = self._viewer_path(frame)
            with Image.open(source) as loaded:
                if loaded.width <= 1920 and loaded.height <= 1080:
                    return
                image = loaded.convert("RGB")
                image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                temporary = destination.with_suffix(".tmp.jpg")
                image.save(
                    temporary,
                    format="JPEG",
                    quality=91,
                    subsampling=0,
                    optimize=False,
                )
                os.replace(temporary, destination)
        except (FileNotFoundError, OSError):
            return
        finally:
            self.viewerFrameReady.emit(frame)

    @Slot(int)
    def _on_viewer_frame_ready(self, frame: int) -> None:
        self._viewer_pending.discard(frame)

    def _frame_path(self, frame: int) -> Path:
        root = Path(self.manifest.frames_dir)
        numeric = root / f"{frame:08d}.png"
        zero_based = root / f"frame_{frame:08d}.png"
        one_based = root / f"frame_{frame + 1:08d}.png"
        if numeric.exists():
            return numeric
        return zero_based if zero_based.exists() else one_based

    def _raw_path(self, frame: int) -> Path:
        return self._raw_dir / f"mask_{frame:08d}.png"

    def _preview_path(self, frame: int) -> Path:
        return self._preview_dir / f"preview_{frame:08d}.png"

    def _viewer_path(self, frame: int) -> Path:
        return self._viewer_dir / f"frame_{frame:08d}.jpg"

    def _refresh_theme(self) -> None:
        dark = system_uses_dark_mode()
        if dark != self._dark_mode:
            self._dark_mode = dark
            self.themeChanged.emit()

    def _mark_tracking_dirty(self) -> None:
        if not self._tracking_dirty:
            self._tracking_dirty = True
            self.trackingStateChanged.emit()

    def _show_history_frame(self, frame: int) -> None:
        if frame == self._current_frame:
            return
        self._current_frame = frame
        self.frameChanged.emit()
        self.maskChanged.emit()
