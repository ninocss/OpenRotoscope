from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot

from openroto.core.models import ModelPreset
from openroto.inference.catalog import MODEL_CATALOG
from openroto.inference.model_cache import download_model, model_home, model_is_installed, remove_model
from openroto.inference.removal_backends import (
    backend_status,
    install_backend,
    remove_backend,
)


class ModelManager(QObject):
    changed = Signal()
    busyChanged = Signal()
    operationFinished = Signal(str, str, str)
    backendOperationFinished = Signal(str, str, str)

    def __init__(self, controller: QObject) -> None:
        super().__init__(controller)
        self._controller = controller
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="OpenRotoModels")
        self._busy_preset: ModelPreset | None = None
        self._busy_backend: str | None = None
        self._busy_action = ""
        self._last_error = ""
        self._settings = QSettings("OpenRoto", "OpenRoto")
        saved_stats = self._settings.value("showPerformanceStats", False)
        if isinstance(saved_stats, bool):
            self._performance_stats_visible = saved_stats
        else:
            self._performance_stats_visible = str(saved_stats).strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        if hasattr(controller, "changed"):
            controller.changed.connect(self.changed.emit)
        self.operationFinished.connect(self._finish_operation)
        self.backendOperationFinished.connect(self._finish_backend_operation)

    @Property("QVariantList", notify=changed)
    def models(self) -> list[dict[str, object]]:
        selected = str(getattr(self._controller, "modelPreset", ModelPreset.BALANCED.value))
        rows: list[dict[str, object]] = []
        for preset in ModelPreset:
            spec = MODEL_CATALOG[preset]
            installed = model_is_installed(spec)
            is_busy = self._busy_preset == preset
            if is_busy:
                status = "Downloading…" if self._busy_action == "download" else "Removing…"
            elif installed:
                status = "Installed"
            else:
                status = "Not installed"
            rows.append(
                {
                    "id": preset.value,
                    "name": spec.display_name,
                    "repository": spec.repository,
                    "description": spec.description,
                    "downloadMb": spec.approximate_download_mb,
                    "minimumVramGb": spec.minimum_vram_gb,
                    "installed": installed,
                    "selected": selected == preset.value,
                    "busy": is_busy,
                    "status": status,
                }
            )
        return rows

    @Property("QVariantList", notify=changed)
    def removalBackends(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for value in ("temporal", "fgt", "svor"):
            row = backend_status(value)
            is_busy = self._busy_backend == value
            row["busy"] = is_busy
            if is_busy:
                row["status"] = "Installing…" if self._busy_action == "install" else "Removing…"
            rows.append(row)
        return rows

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy_preset is not None or self._busy_backend is not None

    @Property(bool, notify=changed)
    def performanceStatsVisible(self) -> bool:
        return self._performance_stats_visible

    @Property(str, notify=changed)
    def lastError(self) -> str:
        return self._last_error

    @Property(str, constant=True)
    def cachePath(self) -> str:
        return str(model_home())

    @Slot(bool)
    def setPerformanceStatsVisible(self, visible: bool) -> None:
        next_value = bool(visible)
        if next_value == self._performance_stats_visible:
            return
        self._performance_stats_visible = next_value
        self._settings.setValue("showPerformanceStats", next_value)
        self.changed.emit()

    @Slot(str)
    def setDefaultModel(self, value: str) -> None:
        if self.busy:
            return
        self._controller.setModelPreset(value)
        self._last_error = ""
        self.changed.emit()

    @Slot(str)
    def downloadModel(self, value: str) -> None:
        self._start_model(value, "download")

    @Slot(str)
    def removeModel(self, value: str) -> None:
        self._start_model(value, "remove")

    @Slot(str)
    def installRemovalBackend(self, value: str) -> None:
        self._start_backend(value, "install")

    @Slot(str)
    def removeRemovalBackend(self, value: str) -> None:
        self._start_backend(value, "remove")

    @Slot()
    def refresh(self) -> None:
        self.changed.emit()

    @Slot()
    def clearError(self) -> None:
        if self._last_error:
            self._last_error = ""
            self.changed.emit()

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _start_model(self, value: str, action: str) -> None:
        if self.busy or bool(getattr(self._controller, "busy", False)):
            return
        try:
            preset = ModelPreset(value)
        except ValueError:
            return
        spec = MODEL_CATALOG[preset]
        self._busy_preset = preset
        self._busy_action = action
        self._last_error = ""
        self.busyChanged.emit()
        self.changed.emit()

        def operation() -> None:
            if action == "download":
                download_model(spec)
            else:
                remove_model(spec)

        future = self._executor.submit(operation)

        def completed(task) -> None:
            error = ""
            try:
                task.result()
            except Exception as exception:
                error = str(exception)
            self.operationFinished.emit(preset.value, action, error)

        future.add_done_callback(completed)

    def _start_backend(self, value: str, action: str) -> None:
        if self.busy or bool(getattr(self._controller, "busy", False)):
            return
        if value not in {"fgt", "svor"}:
            return
        status = backend_status(value)
        if not bool(status.get("can_manage", False)):
            self._last_error = (
                f"{status['display_name']} is configured through environment variables and cannot be managed by OpenRoto."
            )
            self.changed.emit()
            return
        self._busy_backend = value
        self._busy_action = action
        self._last_error = ""
        self.busyChanged.emit()
        self.changed.emit()

        def operation() -> None:
            if action == "install":
                install_backend(value)
            else:
                remove_backend(value)

        future = self._executor.submit(operation)

        def completed(task) -> None:
            error = ""
            try:
                task.result()
            except Exception as exception:
                error = str(exception)
            self.backendOperationFinished.emit(value, action, error)

        future.add_done_callback(completed)

    @Slot(str, str, str)
    def _finish_operation(self, preset_value: str, action: str, error: str) -> None:
        self._busy_preset = None
        self._busy_action = ""
        self._last_error = error
        self.busyChanged.emit()
        self.changed.emit()

    @Slot(str, str, str)
    def _finish_backend_operation(self, backend_id: str, action: str, error: str) -> None:
        self._busy_backend = None
        self._busy_action = ""
        self._last_error = error
        self.busyChanged.emit()
        self.changed.emit()
