from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from PySide6.QtCore import Property, Signal, Slot

from openroto.inference.removal import RemovalEngine
from openroto.inference.removal_backends import (
    BACKENDS,
    ExternalRemovalBackend,
    backend_is_installed,
    backend_rows,
    remove_backend,
    setup_backend,
)
from openroto.ui.removal_controller import RemovalController


class AdvancedRemovalController(RemovalController):
    """Removal workflow with optional isolated learned-inpainting backends."""

    backendChanged = Signal()
    benchmarkChanged = Signal()

    def __init__(self, app_controller) -> None:
        super().__init__(app_controller)
        saved = str(app_controller._settings.value("removalBackend", "temporal"))
        self._backend_id = saved if saved in BACKENDS and backend_is_installed(saved) else "temporal"
        self._backend_error = ""
        self._benchmark_results: list[dict[str, object]] = []
        self._active_external: ExternalRemovalBackend | None = None
        self._benchmark_root = Path(app_controller.manifest.matte_dir) / "benchmark"

    @Property(str, notify=backendChanged)
    def backendId(self) -> str:
        return self._backend_id

    @Property(str, notify=backendChanged)
    def backendName(self) -> str:
        return BACKENDS[self._backend_id].display_name

    @Property(str, notify=backendChanged)
    def backendError(self) -> str:
        return self._backend_error

    @Property("QVariantList", notify=backendChanged)
    def backends(self) -> list[dict[str, object]]:
        return backend_rows(self._backend_id)

    @Property("QVariantList", notify=benchmarkChanged)
    def benchmarkResults(self) -> list[dict[str, object]]:
        return self._benchmark_results

    @Property(str, constant=True)
    def benchmarkFolder(self) -> str:
        return str(self._benchmark_root)

    @Slot(str)
    def setBackend(self, value: str) -> None:
        if value not in BACKENDS:
            return
        if not backend_is_installed(value):
            self._backend_error = f"{BACKENDS[value].display_name} is not installed yet."
            self.backendChanged.emit()
            return
        if value != self._backend_id:
            self._backend_id = value
            self._app._settings.setValue("removalBackend", value)
            self._backend_error = ""
            self._invalidate()
            self.backendChanged.emit()

    @Slot(str)
    def setupBackend(self, value: str) -> None:
        if value not in {"fgt", "svor"} or self._app.busy:
            return
        name = BACKENDS[value].display_name

        def operation() -> None:
            try:
                setup_backend(value, self._app._worker_progress)
            except Exception as error:
                self._backend_error = str(error)
                self.backendChanged.emit()
                raise
            self._backend_error = ""
            self._backend_id = value
            self._app._settings.setValue("removalBackend", value)
            self.backendChanged.emit()

        self._app._run_async(f"Installing {name}", operation)

    @Slot(str)
    def removeBackend(self, value: str) -> None:
        if value not in {"fgt", "svor"} or self._app.busy or not backend_is_installed(value):
            return
        name = BACKENDS[value].display_name
        if self._backend_id == value:
            self._backend_id = "temporal"
            self._app._settings.setValue("removalBackend", "temporal")
            self._invalidate()
            self.backendChanged.emit()

        def operation() -> None:
            remove_backend(value)
            self._backend_error = ""
            self.backendChanged.emit()

        self._app._run_async(f"Removing {name}", operation)

    @Slot()
    def refreshBackends(self) -> None:
        if not backend_is_installed(self._backend_id):
            self._backend_id = "temporal"
            self._app._settings.setValue("removalBackend", "temporal")
        self.backendChanged.emit()

    @Slot()
    def benchmarkBackends(self) -> None:
        if self._app.busy or not self._app.hasPrompts:
            return
        self._app._run_async("Benchmarking removal", self._benchmark)

    @Slot()
    def openBenchmarkFolder(self) -> None:
        self._benchmark_root.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(self._benchmark_root)  # type: ignore[attr-defined]

    @Slot()
    def cancel(self) -> None:
        external = self._active_external
        if external is not None:
            external.cancel()
        super().cancel()

    def close(self) -> None:
        external = self._active_external
        if external is not None:
            external.cancel()
        super().close()

    def _prepare(self) -> None:
        self._ensure_full_tracking()
        self._validate_output_parent()
        if self._backend_id == "temporal":
            self._engine.remove(
                self._app.manifest.frame_count,
                self._output_dir,
                self._settings,
                self._app._worker_progress,
            )
        else:
            if not backend_is_installed(self._backend_id):
                raise RuntimeError(
                    f"{BACKENDS[self._backend_id].display_name} is not installed. Open Removal Models in Settings."
                )
            external = ExternalRemovalBackend(self._backend_id)
            self._active_external = external
            try:
                result = external.remove(
                    self._app.manifest.frames_dir,
                    self._app._raw_dir,
                    range(self._app.manifest.frame_count),
                    self._output_dir,
                    width=self._app.manifest.width,
                    height=self._app.manifest.height,
                    fps=self._app.manifest.fps,
                    padding=self._settings.padding,
                    feather=self._settings.feather,
                    vram_gb=self._app._device.vram_gb,
                    progress=self._app._worker_progress,
                )
                self._set_timing("removal_inpaint", result.elapsed_ms)
            finally:
                self._active_external = None
        self._validate_output()
        self._ready = True
        self._revision += 1
        self._viewer_mode = "removed"
        self.changed.emit()

    def _benchmark(self) -> None:
        self._ensure_full_tracking()
        frame_count = self._app.manifest.frame_count
        sample_count = min(17, frame_count)
        start = max(0, min(self._app.currentFrame - sample_count // 2, frame_count - sample_count))
        source_indices = list(range(start, start + sample_count))

        shutil.rmtree(self._benchmark_root, ignore_errors=True)
        frames = self._benchmark_root / "input" / "frames"
        masks = self._benchmark_root / "input" / "masks"
        frames.mkdir(parents=True, exist_ok=True)
        masks.mkdir(parents=True, exist_ok=True)
        for sequence_index, source_index in enumerate(source_indices):
            frame_source = self._app._frame_path(source_index)
            frame_target = frames / f"{sequence_index:08d}{frame_source.suffix.lower()}"
            try:
                os.link(frame_source, frame_target)
            except OSError:
                shutil.copy2(frame_source, frame_target)
            mask_source = self._app._raw_path(source_index)
            mask_target = masks / f"mask_{sequence_index:08d}.png"
            try:
                os.link(mask_source, mask_target)
            except OSError:
                shutil.copy2(mask_source, mask_target)

        rows: list[dict[str, object]] = []
        installed = [spec for spec in BACKENDS.values() if backend_is_installed(spec.id)]
        total = max(1, len(installed))
        for ordinal, spec in enumerate(installed):
            if self._app._cancel.is_set():
                raise InterruptedError("Removal benchmark was cancelled")
            output = self._benchmark_root / spec.id
            self._app._worker_progress(ordinal / total, f"Benchmarking {spec.display_name}")
            try:
                if spec.id == "temporal":
                    engine = RemovalEngine(frames, masks)
                    started = time.perf_counter_ns()
                    engine.remove(sample_count, output, self._settings)
                    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
                    peak_vram: float | None = 0.0
                else:
                    external = ExternalRemovalBackend(spec.id)
                    self._active_external = external
                    try:
                        result = external.remove(
                            frames,
                            masks,
                            range(sample_count),
                            output,
                            width=self._app.manifest.width,
                            height=self._app.manifest.height,
                            fps=self._app.manifest.fps,
                            padding=self._settings.padding,
                            feather=self._settings.feather,
                            vram_gb=self._app._device.vram_gb,
                        )
                    finally:
                        self._active_external = None
                    elapsed_ms = result.elapsed_ms
                    peak_vram = result.peak_vram_mb
                rows.append(
                    {
                        "id": spec.id,
                        "name": spec.display_name,
                        "status": "Complete",
                        "elapsed": f"{elapsed_ms / 1000.0:,.2f} s",
                        "perFrame": f"{elapsed_ms / sample_count:,.1f} ms/frame",
                        "vram": "n/a" if peak_vram is None else f"{peak_vram / 1024.0:,.1f} GB",
                        "path": str(output),
                    }
                )
            except Exception as error:
                rows.append(
                    {
                        "id": spec.id,
                        "name": spec.display_name,
                        "status": "Failed",
                        "elapsed": "—",
                        "perFrame": "—",
                        "vram": "—",
                        "path": str(output),
                        "error": str(error),
                    }
                )
            self._benchmark_results = list(rows)
            self.benchmarkChanged.emit()

        self._benchmark_results = rows
        self.benchmarkChanged.emit()
        self._app._worker_progress(1.0, f"Benchmark complete · {sample_count} frames")
