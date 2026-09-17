"""Exercise compact-mode touch targets, keyboard focus, tab order and Escape behavior."""

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
    parser.add_argument("--mode", choices=("rotoscope", "remove"), required=True)
    return parser.parse_args()


ARGS = parse_args()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PIL import Image
from PySide6.QtCore import QMetaObject, QObject, QPointF, QSettings, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import getCppPointer, wrapInstance

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.core.models import SessionManifest, SessionState
from openroto.ui.controller import ApplicationController
from openroto.ui.model_manager import ModelManager
from openroto.ui.removal_controller import RemovalController

MIN_TOUCH = 44.0


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
        session_id="accessibility-smoke-session",
        token="accessibility-smoke-token-00000000000000",
        bridge_host="127.0.0.1",
        bridge_port=port,
        project_id="project",
        project_name="Accessibility validation project",
        timeline_id="timeline",
        timeline_name="Accessibility validation timeline",
        clip_id="clip",
        clip_name="Accessibility validation clip",
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


def wait(app: QApplication, ms: int = 80) -> None:
    app.processEvents()
    QTest.qWait(ms)
    app.processEvents()


def bool_property(obj: QObject, name: str) -> bool:
    value = obj.property(name)
    return bool(value) if value is not None else False


def control_for_focus(obj: QObject | None) -> QObject | None:
    current = obj
    while current is not None:
        if current.property("compactTouchMode") is not None:
            return current
        current = current.parent()
    return None


def descriptor(control: QObject) -> str:
    parts: list[str] = []
    for name in ("text", "toolTip", "displayText"):
        value = control.property(name)
        if isinstance(value, str) and value and value not in parts:
            parts.append(value)
    return " | ".join(parts) if parts else control.metaObject().className()


def focused_descriptor(app: QApplication) -> str:
    control = control_for_focus(app.focusObject())
    return descriptor(control) if control is not None else "<non-control>"


def item_rect(item: QQuickItem) -> tuple[float, float, float, float]:
    point = item.mapToScene(QPointF(0, 0))
    return float(point.x()), float(point.y()), float(item.width()), float(item.height())


def intersects_window(rect: tuple[float, float, float, float], width: float, height: float) -> bool:
    x, y, w, h = rect
    return x + w > 0 and y + h > 0 and x < width and y < height


def visible_compact_controls(window: QObject) -> list[QQuickItem]:
    controls: list[QQuickItem] = []
    width = float(window.property("width"))
    height = float(window.property("height"))
    for obj in window.findChildren(QObject):
        if not isinstance(obj, QQuickItem):
            continue
        if obj.property("compactTouchMode") is None:
            continue
        if not bool_property(obj, "compactTouchMode"):
            continue
        if not bool_property(obj, "visible") or not bool_property(obj, "enabled"):
            continue
        rect = item_rect(obj)
        if intersects_window(rect, width, height):
            controls.append(obj)
    return controls


def assert_touch_targets(window: QObject, surface: str) -> list[str]:
    controls = visible_compact_controls(window)
    if not controls:
        raise AssertionError(f"{surface}: no visible compact controls found")
    failures: list[str] = []
    labels: list[str] = []
    for control in controls:
        label = descriptor(control)
        labels.append(label)
        _, _, width, height = item_rect(control)
        if width + 0.01 < MIN_TOUCH or height + 0.01 < MIN_TOUCH:
            failures.append(f"{label}: {width:.1f}x{height:.1f}")
    if failures:
        raise AssertionError(f"{surface}: touch targets below {MIN_TOUCH:.0f}px: " + "; ".join(failures))
    return labels


def tab_sequence(app: QApplication, window: QQuickWindow, count: int) -> list[str]:
    sequence: list[str] = []
    for _ in range(count):
        QTest.keyClick(window, Qt.Key_Tab)
        wait(app, 30)
        control = control_for_focus(app.focusObject())
        if control is None:
            sequence.append("<non-control>")
            continue
        if not bool_property(control, "visualFocus"):
            raise AssertionError(f"Focused control lacks visualFocus: {descriptor(control)}")
        sequence.append(descriptor(control))
    return sequence


def first_index(sequence: list[str], value: str) -> int:
    for index, item in enumerate(sequence):
        if value in item:
            return index
    raise AssertionError(f"Tab sequence never reached {value!r}: {sequence}")


def assert_base_tab_order(sequence: list[str]) -> None:
    roto = first_index(sequence, "Rotoscope")
    remove = first_index(sequence, "Remove")
    controls = first_index(sequence, "Open controls")
    settings = first_index(sequence, "Settings")
    viewer_reset = first_index(sequence, "Reset viewer")
    if not (roto < remove < controls < settings < viewer_reset):
        raise AssertionError(f"Unexpected compact tab order: {sequence}")


def assert_overlay_focus(sequence: list[str], forbidden: tuple[str, ...], surface: str) -> None:
    actual = [entry for entry in sequence if entry != "<non-control>"]
    if len(actual) < 3:
        raise AssertionError(f"{surface}: too few focusable controls reached: {sequence}")
    for entry in actual:
        if any(token in entry for token in forbidden):
            raise AssertionError(f"{surface}: focus escaped to background control {entry!r}: {sequence}")


def run() -> int:
    app = QApplication(["openroto-accessibility-smoke"])
    app.setApplicationName("OpenRoto Accessibility Smoke")
    QSettings("OpenRoto", "OpenRoto").clear()

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
            removal_controller.setWorkflowMode(ARGS.mode)
            window.setWidth(ARGS.width)
            window.setHeight(ARGS.height)
            window.show()
            wait(app, 200)

            if not bool(window.property("compactMode")):
                raise AssertionError("Accessibility smoke requires compact mode")

            base_touch = assert_touch_targets(window, "base")
            base_tabs = tab_sequence(app, quick_window, 24)
            assert_base_tab_order(base_tabs)

            if not QMetaObject.invokeMethod(window, "openCompactControls"):
                raise RuntimeError("Could not open compact controls drawer")
            wait(app, 160)
            drawer_touch = assert_touch_targets(window, "drawer")
            drawer_tabs = tab_sequence(app, quick_window, 16)
            assert_overlay_focus(
                drawer_tabs,
                ("Open controls", "Settings", "Reset viewer", "Previous frame", "Next frame"),
                "drawer",
            )
            QTest.keyClick(quick_window, Qt.Key_Escape)
            wait(app, 120)
            drawer_escape_focus = focused_descriptor(app)
            if "Open controls" not in drawer_escape_focus:
                raise AssertionError(
                    "Escape did not close the compact drawer and return focus to its trigger: "
                    + drawer_escape_focus
                )

            settings_signal = getattr(window, "settingsRequested", None)
            if settings_signal is not None and hasattr(settings_signal, "emit"):
                settings_signal.emit()
            elif not QMetaObject.invokeMethod(window, "settingsRequested"):
                raise RuntimeError("Could not open Settings")
            wait(app, 160)
            settings_touch = assert_touch_targets(window, "settings")
            settings_tabs = tab_sequence(app, quick_window, 12)
            assert_overlay_focus(
                settings_tabs,
                ("Open controls", "Reset viewer", "Previous frame", "Next frame"),
                "settings",
            )
            system = first_index(settings_tabs, "System")
            light = first_index(settings_tabs, "Light")
            dark = first_index(settings_tabs, "Dark")
            if not (system < light < dark):
                raise AssertionError(f"Unexpected Settings tab order: {settings_tabs}")
            QTest.keyClick(quick_window, Qt.Key_Escape)
            wait(app, 120)
            after_settings_escape = tab_sequence(app, quick_window, 8)
            if not any(
                any(token in entry for token in ("Open controls", "Settings", "Reset viewer"))
                for entry in after_settings_escape
            ):
                raise AssertionError(
                    "Escape did not return keyboard navigation to the main compact UI: "
                    f"{after_settings_escape}"
                )
            if any(
                any(token in entry for token in ("System", "Light", "Dark"))
                for entry in after_settings_escape
            ):
                raise AssertionError(
                    "Settings remained in the tab order after Escape: "
                    f"{after_settings_escape}"
                )

            print(
                json.dumps(
                    {
                        "size": [ARGS.width, ARGS.height],
                        "mode": ARGS.mode,
                        "minimum_touch": MIN_TOUCH,
                        "base_touch_controls": len(base_touch),
                        "drawer_touch_controls": len(drawer_touch),
                        "settings_touch_controls": len(settings_touch),
                        "base_tab_sequence": base_tabs,
                        "drawer_tab_sequence": drawer_tabs,
                        "settings_tab_sequence": settings_tabs,
                        "drawer_escape_focus": drawer_escape_focus,
                        "after_settings_escape": after_settings_escape,
                        "escape_drawer": True,
                        "escape_settings": True,
                    },
                    sort_keys=True,
                )
            )
            return 0
        finally:
            removal_controller.close()
            model_manager.close()
            controller.closeSession()
            server.close()


if __name__ == "__main__":
    raise SystemExit(run())
