from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from openroto.free_handoff import FreeHandoffController
from openroto.inference.removal import RemovalEngine, RemovalSettings
from openroto.inference.removal_comp import fusion_removal_comp_text
from openroto.ui.controller import ApplicationController

_REMOVAL_TIMING_LABELS = (
    ("removal_prepare", "Prepare"),
    ("removal_inpaint", "Inpaint"),
)


class RemovalController(QObject):
    """Object-removal workflow layered on the stable rotoscope controller."""

    changed = Signal()
    timingsChanged = Signal()

    def __init__(self, app_controller: ApplicationController) -> None:
        super().__init__(app_controller)
        self._app = app_controller
        self._workflow_mode = "rotoscope"
        self._viewer_mode = "mask"
        self._settings = RemovalSettings()
        self._output_dir = Path(app_controller.manifest.matte_dir) / "removed"
        self._ready = False
        self._revision = 0
        self._timings: dict[str, float | None] = {
            key: None for key, _label in _REMOVAL_TIMING_LABELS
        }
        self._engine = RemovalEngine(app_controller.manifest.frames_dir, app_controller._raw_dir)
        self._engine.set_timing_callback(self._set_timing)

        # Frame navigation emits pointsChanged in the rotoscope controller, so do
        # not use that signal as a removal invalidation trigger. trackingStateChanged
        # is emitted when a real prompt/model edit makes a previously tracked mask dirty.
        app_controller.trackingStateChanged.connect(self._on_tracking_state_changed)
        app_controller.changed.connect(self._on_app_changed)
        app_controller.frameChanged.connect(self.changed.emit)
        app_controller.operationFinished.connect(self._on_operation_finished)

    @Property(str, notify=changed)
    def workflowMode(self) -> str:
        return self._workflow_mode

    @Property(str, notify=changed)
    def viewerMode(self) -> str:
        return self._viewer_mode

    @Property(bool, notify=changed)
    def ready(self) -> bool:
        return self._ready

    @Property(int, notify=changed)
    def padding(self) -> int:
        return self._settings.padding

    @Property(float, notify=changed)
    def feather(self) -> float:
        return self._settings.feather

    @Property(int, notify=changed)
    def temporalRadius(self) -> int:
        return self._settings.temporal_radius

    @Property(QUrl, notify=changed)
    def currentRemovalUrl(self) -> QUrl:
        path = self._output_dir / f"removed_{self._app.currentFrame:08d}.png"
        if not path.is_file():
            return QUrl()
        url = QUrl.fromLocalFile(str(path))
        url.setQuery(f"v={self._revision}")
        return url

    @Property("QVariantList", notify=timingsChanged)
    def timings(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for key, label in _REMOVAL_TIMING_LABELS:
            value = self._timings[key]
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
            "removed" if self._ready else "mask"
        )
        self.changed.emit()

    @Slot(str)
    def setViewerMode(self, value: str) -> None:
        if value not in {"original", "mask", "removed"}:
            return
        if value == "removed" and not self._ready:
            return
        if value != self._viewer_mode:
            self._viewer_mode = value
            self.changed.emit()

    @Slot(int)
    def setPadding(self, value: int) -> None:
        value = max(0, min(32, int(value)))
        if value != self._settings.padding:
            self._settings.padding = value
            self._invalidate()
            self.changed.emit()

    @Slot(float)
    def setFeather(self, value: float) -> None:
        value = max(0.0, min(24.0, float(value)))
        if value != self._settings.feather:
            self._settings.feather = value
            self._invalidate()
            self.changed.emit()

    @Slot(int)
    def setTemporalRadius(self, value: int) -> None:
        value = max(1, min(60, int(value)))
        if value != self._settings.temporal_radius:
            self._settings.temporal_radius = value
            self._invalidate()
            self.changed.emit()

    @Slot()
    def preview(self) -> None:
        if self._app.busy or not self._app.hasPrompts:
            return
        self._app._run_async("Removing object", self._prepare)

    @Slot()
    def removeAndApply(self) -> None:
        if self._app.busy or not self._app.hasPrompts or not self._app.bridgeConnected:
            return
        self._app._run_async("Remove & Apply", self._remove_and_apply)

    @Slot()
    def cancel(self) -> None:
        self._engine.cancel()
        self._app.cancel()

    def close(self) -> None:
        self._engine.cancel()

    def _prepare(self) -> None:
        if self._app.trackingDirty:
            self._app._track()
        self._engine.remove(
            self._app.manifest.frame_count,
            self._output_dir,
            self._settings,
            self._app._worker_progress,
        )
        self._ready = True
        self._revision += 1
        self._viewer_mode = "removed"
        self.changed.emit()

    def _remove_and_apply(self) -> None:
        if not self._ready or self._app.trackingDirty:
            self._prepare()
        if isinstance(self._app, FreeHandoffController):
            self._apply_free()
        else:
            self._apply_studio()

    def _apply_studio(self) -> None:
        self._app._bridge.send(
            "apply",
            session_id=self._app.manifest.session_id,
            mode="remove",
            removal_dir=str(self._output_dir),
            removal_pattern="removed_%08d.png",
            frame_count=self._app.manifest.frame_count,
        )
        self._app._set_progress_from_worker(
            1.0, "Waiting for Resolve", "Applying removed-object result"
        )

    def _apply_free(self) -> None:
        app = self._app
        assert isinstance(app, FreeHandoffController)
        comp_path = Path(app.manifest.matte_dir) / "OpenRoto.comp"
        comp_path.write_text(
            fusion_removal_comp_text(
                self._output_dir / "removed_00000000.png",
                app.manifest.frame_count,
            ),
            encoding="utf-8",
        )
        for stale in (app._applied_ack_path, app._failed_ack_path):
            stale.unlink(missing_ok=True)
        app._send_control("apply")
        app._apply_requested = True
        app._worker_progress(0.98, "Applying in DaVinci Resolve")

        deadline = time.monotonic() + app.APPLY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if app._cancel.is_set():
                app._send_control("cancel")
                raise InterruptedError("Applying was cancelled")
            if app._failed_ack_path.is_file():
                raise RuntimeError(
                    "DaVinci Resolve could not apply the object-removal result. "
                    "The safety snapshot was kept in the session folder."
                )
            if app._applied_ack_path.is_file():
                app._handoff_applied = True
                app._worker_progress(1.0, "Applied in DaVinci Resolve")
                return
            time.sleep(0.20)
        raise RuntimeError(
            "DaVinci Resolve did not confirm the object-removal apply step within two minutes."
        )

    def _on_tracking_state_changed(self) -> None:
        if self._app.trackingDirty:
            self._invalidate()

    def _on_app_changed(self) -> None:
        if self._app.trackingDirty:
            self._invalidate()

    @Slot(str, str)
    def _on_operation_finished(self, status: str, detail: str) -> None:
        # This slot runs after ApplicationController's own completion slot because
        # it is connected later. Give removal previews their workflow-specific
        # final status without interfering with Resolve's apply/waiting state.
        if (
            status == "Ready"
            and self._workflow_mode == "remove"
            and self._ready
            and self._app.status not in {"Waiting for Resolve", "Applied in DaVinci Resolve"}
        ):
            self._app._status = "Removal ready"
            self._app._detail = "Review Original, Mask and Removed, or apply the result to Resolve."
            self._app.statusChanged.emit()

    def _set_timing(self, key: str, elapsed_ms: float) -> None:
        if key not in self._timings:
            return
        self._timings[key] = max(0.0, float(elapsed_ms))
        self.timingsChanged.emit()

    def _invalidate(self) -> None:
        was_ready = self._ready
        self._ready = False
        if self._viewer_mode == "removed":
            self._viewer_mode = "mask"
        if was_ready:
            self.changed.emit()
