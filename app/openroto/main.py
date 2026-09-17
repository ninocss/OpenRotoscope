from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMessageBox

from openroto.core.manifest import read_manifest
from openroto.core.models import ModelPreset
from openroto.free_agent import FreeSessionAgent
from openroto.free_handoff import FreeHandoffController, ensure_free_agent
from openroto.inference.catalog import MODEL_CATALOG
from openroto.inference.model_cache import model_is_installed
from openroto.ui.controller import ApplicationController
from openroto.ui.mica import apply_mica
from openroto.ui.model_manager import ModelManager
from openroto.ui.removal_controller import RemovalController


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenRoto for DaVinci Resolve")
    parser.add_argument("--session", type=Path, help="Resolve session manifest")
    parser.add_argument(
        "--handoff",
        action="store_true",
        help="Use the filesystem handoff used by DaVinci Resolve Free 21.1+",
    )
    parser.add_argument(
        "--free-agent",
        action="store_true",
        help="Watch for frame exports from DaVinci Resolve Free",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    local_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    os.environ.setdefault("HF_HOME", str(local_data / "OpenRoto" / "Models"))
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    app = QApplication(argv or sys.argv)
    app.setApplicationName("OpenRoto")
    app.setOrganizationName("OpenRoto")
    app.setApplicationVersion("0.1.0")
    icon_path = Path(__file__).with_name("ui") / "openroto.svg"
    app.setWindowIcon(QIcon(str(icon_path)))

    arguments = build_parser().parse_args((argv or sys.argv)[1:])
    if arguments.free_agent:
        agent = FreeSessionAgent()
        if not agent.is_primary:
            return 0
        return app.exec()

    if arguments.session is None:
        ensure_free_agent()
        QMessageBox.information(
            None,
            "Open OpenRoto from DaVinci Resolve",
            "OpenRoto is ready for DaVinci Resolve Free and Studio.\n\n"
            "Place the playhead over a video clip, then choose\n\n"
            "Workspace  ›  Scripts  ›  OpenRoto\n\n"
            "Use Rotoscope to isolate a subject or Remove to reconstruct the background.",
        )
        return 2
    try:
        manifest = read_manifest(arguments.session)
    except Exception as error:
        QMessageBox.critical(None, "OpenRoto could not start", str(error))
        return 3

    engine = QQmlApplicationEngine()
    controller = FreeHandoffController(manifest) if arguments.handoff else ApplicationController(manifest)
    removal_controller = RemovalController(controller)
    model_manager = ModelManager(controller)
    model_manager.changed.connect(removal_controller.refreshBackends)
    engine.setInitialProperties(
        {
            "appController": controller,
            "modelManager": model_manager,
            "removalController": removal_controller,
        }
    )
    qml_path = Path(__file__).with_name("ui") / "ObjectRemovalMain.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        removal_controller.close()
        model_manager.close()
        controller.closeSession()
        return 4

    window = engine.rootObjects()[0]

    def configure_window() -> None:
        apply_mica(int(window.winId()), controller.darkMode)

    def prewarm_initial_selection() -> None:
        """Hide installed-model startup cost behind the time spent viewing the clip."""
        try:
            preset = ModelPreset(controller.modelPreset)
            if not model_is_installed(MODEL_CATALOG[preset]):
                return
            controller._engine.prewarm_frame(controller.currentFrame, preset)
        except Exception:
            pass

    QTimer.singleShot(0, configure_window)
    QTimer.singleShot(
        180,
        lambda: threading.Thread(
            target=prewarm_initial_selection,
            name="OpenRotoPrewarm",
            daemon=True,
        ).start(),
    )
    controller.themeChanged.connect(configure_window)
    controller.closeRequested.connect(window.close)
    app.aboutToQuit.connect(removal_controller.close)
    app.aboutToQuit.connect(model_manager.close)
    app.aboutToQuit.connect(controller.closeSession)
    smoke_exit_ms = os.environ.get("OPENROTO_SMOKE_EXIT_MS")
    smoke_screenshot = os.environ.get("OPENROTO_SMOKE_SCREENSHOT")
    if smoke_screenshot:
        QTimer.singleShot(
            500,
            lambda: window.screen().grabWindow(int(window.winId())).save(smoke_screenshot),
        )
    if smoke_exit_ms:
        QTimer.singleShot(max(1, int(smoke_exit_ms)), app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
