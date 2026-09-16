from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from PySide6.QtCore import Property, QTimer, QUrl, Signal, Slot

from openroto.free_handoff import FreeHandoffController
from openroto.inference.removal import RemovalEngine, RemovalSettings
from openroto.inference.removal_comp import fusion_removal_comp_text
from openroto.ui.controller import ApplicationController


_REMOVAL_TIMING_LABELS = (
    ("removal_prepare", "Prepare"),
    ("removal_inpaint", "Inpaint"),
)


class ObjectRemovalMixin:
    workflowChanged = Signal()
    removalChanged = Signal()
    removalTimingsChanged = Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._workflow_mode = "rotoscope"
        self._viewer_mode = "mask"
        self._removal_settings = RemovalSettings()
        self._removal_dir = Path(self.manifest.matte_dir) / "removed"
        self._removal_ready = False
        self._removal_revision = 0
        self._removal_timings: dict[str, float | None] = {
            key: None for key, _label in _REMOVAL_TIMING_LABELS
        }
        self._removal_engine = RemovalEngine(self.manifest.frames_dir, self._raw_dir)
        self._removal_engine.set_timing_callback(
            lambda key, ms: self.workerTiming.emit(key, ms)
        )
        self.workerTiming.connect(self._set_removal_timing)

    @Property(str, notify=workflowChanged)
    def workflowMode(self) -> str:
        return self._workflow_mode

    @Property(str, notify=workflowChanged)
    def viewerMode(self) -> str:
        return self._viewer_mode

    @Property(bool, notify=removalChanged)
    def removalReady(self) -> bool:
        return self._removal_ready

    @Property(int, notify=removalChanged)
    def removalPadding(self) -> int:
        return self._removal_settings.padding

    @Property(float, notify=removalChanged)
    def removalFeather(self) -> float:
        return self._removal_settings.feather

    @Property(int, notify=removalChanged)
    def removalTemporalRadius(self) -> int:
        return self._removal_settings.temporal_radius

    @Property(QUrl, notify=removalChanged)
    def currentRemovalUrl(self) -> QUrl:
        path = self._removal_dir / f"removed_{self.currentFrame:08d}.png"
        if not path.is_file():
            return QUrl()
        url = QUrl.fromLocalFile(str(path))
        url.setQuery(f"v={self._removal_revision}")
        return url

    @Property("QVariantList", notify=removalTimingsChanged)
    def removalTimings(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for key, label in _REMOVAL_TIMING_LABELS:
            value = self._removal_timings[key]
            rows.append(
                {
                    "key": key,
                    "label": label,
                    "measured": value is not None,
                    "value": "—" if value is None else f"{value:,.1f} ms",
                }
            )
        return rows

    @Slot(str)
    def setWorkflowMode(self, value: str) -> None:
        if value not in {"rotoscope", "remove"} or value == self._workflow_mode:
            return
        self._workflow_mode = value
        self._viewer_mode = "mask" if value == "rotoscope" else (
            "removed" if self._removal_ready else "mask"
        )
        self.workflowChanged.emit()

    @Slot(str)
    def setViewerMode(self, value: str) -> None:
        if value not in {"original", "mask", "removed"}:
            return
        if value == "removed" and not self._removal_ready:
            return
        if value != self._viewer_mode:
            self._viewer_mode = value
            self.workflowChanged.emit()

    @Slot(int)
    def setRemovalPadding(self, value: int) -> None:
        value = max(0, min(32, int(value)))
        if value != self._removal_settings.padding:
            self._removal_settings.padding = value
            self._invalidate_removal()

    @Slot(float)
    def setRemovalFeather(self, value: float) -> None:
        value = max(0.0, min(24.0, float(value)))
        if value != self._removal_settings.feather:
            self._removal_settings.feather = value
            self._invalidate_removal()

    @Slot(int)
    def setRemovalTemporalRadius(self, value: int) -> None:
        value = max(1, min(60, int(value)))
        if value != self._removal_settings.temporal_radius:
            self._removal_settings.temporal_radius = value
            self._invalidate_removal()

    @Slot()
    def previewRemoval(self) -> None:
        if self.busy or not self.hasPrompts:
            return
        self._run_async("Removing object", self._prepare_removal)

    @Slot()
    def renderAndApply(self) -> None:  # noqa: N802 - QML API
        if self._workflow_mode == "rotoscope":
            super().renderAndApply()
            return
        if self.busy or not self.hasPrompts or not self.bridgeConnected:
            return
        self._run_async("Remove & Apply", self._remove_and_apply)

    @Slot()
    def cancel(self) -> None:
        self._removal_engine.cancel()
        super().cancel()

    def _mark_tracking_dirty(self) -> None:
        self._invalidate_removal()
        super()._mark_tracking_dirty()

    def _prepare_removal(self) -> None:
        if self.trackingDirty:
            self._track()
        self._removal_engine.remove(
            self.manifest.frame_count,
            self._removal_dir,
            self._removal_settings,
            self._worker_progress,
        )
        self._removal_ready = True
        self._removal_revision += 1
        self._viewer_mode = "removed"
        self.removalChanged.emit()
        self.workflowChanged.emit()

    def _remove_and_apply(self) -> None:
        if not self._removal_ready or self.trackingDirty:
            self._prepare_removal()
        self._apply_removal()

    def _apply_removal(self) -> None:
        self._bridge.send(
            "apply",
            session_id=self.manifest.session_id,
            mode="remove",
            removal_dir=str(self._removal_dir),
            removal_pattern="removed_%08d.png",
            frame_count=self.manifest.frame_count,
        )
        self._set_progress_from_worker(1.0, "Waiting for Resolve", "Applying removed-object result")

    @Slot(str, float)
    def _set_removal_timing(self, key: str, elapsed_ms: float) -> None:
        if key not in self._removal_timings:
            return
        self._removal_timings[key] = max(0.0, float(elapsed_ms))
        self.removalTimingsChanged.emit()

    def _invalidate_removal(self) -> None:
        if not hasattr(self, "_removal_ready"):
            return
        changed = self._removal_ready
        self._removal_ready = False
        if self._viewer_mode == "removed":
            self._viewer_mode = "mask"
            self.workflowChanged.emit()
        if changed:
            self.removalChanged.emit()


class WorkflowController(ObjectRemovalMixin, ApplicationController):
    pass


class FreeWorkflowController(ObjectRemovalMixin, FreeHandoffController):
    def _apply_removal(self) -> None:
        comp_path = Path(self.manifest.matte_dir) / "OpenRoto.comp"
        comp_path.write_text(
            fusion_removal_comp_text(
                self._removal_dir / "removed_00000000.png",
                self.manifest.frame_count,
            ),
            encoding="utf-8",
        )

        for stale in (self._applied_ack_path, self._failed_ack_path):
            stale.unlink(missing_ok=True)
        self._send_control("apply")
        self._apply_requested = True
        self._worker_progress(0.98, "Applying in DaVinci Resolve")

        deadline = time.monotonic() + self.APPLY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self._cancel.is_set():
                self._send_control("cancel")
                raise InterruptedError("Applying was cancelled")
            if self._failed_ack_path.is_file():
                raise RuntimeError(
                    "DaVinci Resolve could not apply the object-removal result. "
                    "The safety snapshot was kept in the session folder."
                )
            if self._applied_ack_path.is_file():
                self._handoff_applied = True
                self._worker_progress(1.0, "Applied in DaVinci Resolve")
                return
            time.sleep(0.20)
        raise RuntimeError(
            "DaVinci Resolve did not confirm the object-removal apply step within two minutes."
        )

    def _finish_operation(self, status: str, detail: str) -> None:
        if status == "Ready" and self._handoff_applied:
            self._busy = False
            self._completed = True
            self._progress = 1.0
            self._status = "Applied in DaVinci Resolve"
            self._detail = "OpenRoto will close automatically."
            self.busyChanged.emit()
            self.progressChanged.emit()
            self.statusChanged.emit()
            self.maskChanged.emit()
            QTimer.singleShot(250, self.closeRequested.emit)
            return
        super()._finish_operation(status, detail)
