"""Render the active QML UI at a requested logical size and DPI scale.

Each invocation runs in a fresh process because Qt's DPI scale is fixed when
QApplication is created. The test intentionally uses the real controllers and
active ObjectRemovalMain.qml chain, but does not perform inference.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--scale", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("rotoscope", "remove"), default="rotoscope")
    parser.add_argument("--theme", choices=("system", "light", "dark"), default="system")
    parser.add_argument("--settings", action="store_true")
    parser.add_argument(
        "--force-size",
        action="store_true",
        help="Temporarily ignore the app minimum size for unsupported-size probes.",
    )
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Show the performance overlay so its compact centering is captured too.",
    )
    parser.add_argument(
        "--drawer",
        action="store_true",
        help="Open the compact controls drawer before capturing the window.",
    )
    return parser.parse_args()


ARGS = parse_args()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = str(ARGS.scale)
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PIL import Image
from PySide6.QtCore import QMetaObject, QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication
from shiboken6 import getCppPointer, wrapInstance

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.core.models import SessionManifest, SessionState
from openroto.ui.controller import ApplicationController
from openroto.ui.model_manager import ModelManager
from openroto.ui.removal_controller import RemovalController


def serve_once(server: socket.socket) -> None:
    connection, _ = server.accept()
    with connection:
        stream = connection.makefile("rwb")
        message = json.loads(stream.readline())
        assert message["type"] == "hello"
        stream.write(b'{"type":"ready"}\n')
        stream.flush()
        while stream.readline():
            pass


def build_manifest(root: Path, port: int) -> SessionManifest:
    frames = root / "frames"
    matte = root / "matte"
    frames.mkdir()
    matte.mkdir()
    Image.new("RGB", (1920, 1080), "#24314a").save(frames / "00000000.png")
    return SessionManifest(
        session_id="layout-smoke-session",
        token="layout-smoke-token-000000000000000000000",
        bridge_host="127.0.0.1",
        bridge_port=port,
        project_id="project",
        project_name="Layout validation project",
        timeline_id="timeline",
        timeline_name="Layout validation timeline",
        clip_id="clip",
        clip_name="Long layout validation clip name for clipping checks",
        track_index=1,
        record_start=0,
        record_end=1,
        source_start=0,
        source_end=1,
        fps=24,
        width=1920,
        height=1080,
        frames_dir=str(frames.resolve()),
        matte_dir=str(matte.resolve()),
        snapshot_path=str((root / "snapshot.drt").resolve()),
        state=SessionState.READY,
    )


def run() -> int:
    app = QApplication(["openroto-layout-smoke"])
    app.setApplicationName("OpenRoto Layout Smoke")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        thread = threading.Thread(target=serve_once, args=(server,), daemon=True)
        thread.start()

        controller = ApplicationController(build_manifest(root, server.getsockname()[1]))
        removal_controller = RemovalController(controller)
        model_manager = ModelManager(controller)
        engine = QQmlApplicationEngine()
        try:
            engine.setInitialProperties(
                {
                    "appController": controller,
                    "modelManager": model_manager,
                    "removalController": removal_controller,
                }
            )
            qml_path = ROOT / "app" / "openroto" / "ui" / "ObjectRemovalMain.qml"
            engine.load(QUrl.fromLocalFile(str(qml_path)))
            if not engine.rootObjects():
                return 4

            window = engine.rootObjects()[0]
            quick_window = wrapInstance(getCppPointer(window)[0], QQuickWindow)
            window.setProperty("themeMode", ARGS.theme)
            removal_controller.setWorkflowMode(ARGS.mode)
            if ARGS.performance:
                model_manager.setPerformanceStatsVisible(True)

            declared_minimum = [int(window.minimumWidth()), int(window.minimumHeight())]
            if ARGS.force_size:
                window.setMinimumWidth(0)
                window.setMinimumHeight(0)
            window.setWidth(ARGS.width)
            window.setHeight(ARGS.height)
            window.show()
            app.processEvents()

            compact_mode = bool(window.property("compactMode"))
            if ARGS.width < 1120 and not compact_mode:
                raise AssertionError("Compact mode did not activate below 1120 logical pixels")
            if ARGS.width >= 1120 and compact_mode:
                raise AssertionError("Compact mode stayed active at or above 1120 logical pixels")

            if ARGS.drawer:
                if not compact_mode:
                    raise AssertionError("Drawer capture requested outside compact mode")
                if not QMetaObject.invokeMethod(window, "openCompactControls"):
                    raise RuntimeError("Could not open compact controls drawer")
            if ARGS.settings:
                signal = getattr(window, "settingsRequested", None)
                if signal is not None and hasattr(signal, "emit"):
                    signal.emit()
                elif not QMetaObject.invokeMethod(window, "settingsRequested"):
                    raise RuntimeError("Could not open the Settings popup")

            result = {"ok": False}

            def capture() -> None:
                try:
                    actual_width = int(window.width())
                    actual_height = int(window.height())
                    effective_minimum = [int(window.minimumWidth()), int(window.minimumHeight())]
                    image = quick_window.grabWindow()
                    if image.isNull():
                        raise RuntimeError("QQuickWindow.grabWindow() returned a null image")
                    ARGS.output.parent.mkdir(parents=True, exist_ok=True)
                    if not image.save(str(ARGS.output)):
                        raise RuntimeError(f"Could not save {ARGS.output}")

                    expected_pixel_width = round(ARGS.width * ARGS.scale)
                    expected_pixel_height = round(ARGS.height * ARGS.scale)
                    print(
                        json.dumps(
                            {
                                "requested": [ARGS.width, ARGS.height],
                                "actual": [actual_width, actual_height],
                                "declared_minimum": declared_minimum,
                                "effective_minimum": effective_minimum,
                                "forced_size": ARGS.force_size,
                                "compact_mode": compact_mode,
                                "drawer": ARGS.drawer,
                                "scale": ARGS.scale,
                                "expected_pixels": [expected_pixel_width, expected_pixel_height],
                                "image_pixels": [image.width(), image.height()],
                                "mode": ARGS.mode,
                                "theme": ARGS.theme,
                                "settings": ARGS.settings,
                                "performance": ARGS.performance,
                                "output": str(ARGS.output),
                            },
                            sort_keys=True,
                        )
                    )
                    if not ARGS.force_size and (
                        actual_width < declared_minimum[0] or actual_height < declared_minimum[1]
                    ):
                        raise AssertionError("Window rendered below its declared minimum size")
                    if actual_width != ARGS.width or actual_height != ARGS.height:
                        raise AssertionError(
                            f"Requested {ARGS.width}x{ARGS.height}, got {actual_width}x{actual_height}"
                        )
                    if image.width() != expected_pixel_width or image.height() != expected_pixel_height:
                        raise AssertionError(
                            "High-DPI render size mismatch: expected "
                            f"{expected_pixel_width}x{expected_pixel_height}, got "
                            f"{image.width()}x{image.height()}"
                        )
                    result["ok"] = True
                finally:
                    app.quit()

            QTimer.singleShot(500, capture)
            exit_code = app.exec()
            return exit_code if exit_code else (0 if result["ok"] else 5)
        finally:
            removal_controller.close()
            model_manager.close()
            controller.closeSession()
            server.close()


if __name__ == "__main__":
    raise SystemExit(run())
