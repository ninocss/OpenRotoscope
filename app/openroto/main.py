from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMessageBox

from openroto.core.manifest import read_manifest
from openroto.free_handoff import FreeHandoffController, FreeSessionAgent, ensure_free_agent
from openroto.ui.controller import ApplicationController
from openroto.ui.mica import apply_mica


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
            "On Resolve Free, OpenRoto opens automatically after the clip export. "
            "When the matte is ready, choose Workspace › Scripts › OpenRoto Apply.",
        )
        return 2
    try:
        manifest = read_manifest(arguments.session)
    except Exception as error:
        QMessageBox.critical(None, "OpenRoto could not start", str(error))
        return 3

    engine = QQmlApplicationEngine()
    controller = (
        FreeHandoffController(manifest) if arguments.handoff else ApplicationController(manifest)
    )
    engine.setInitialProperties({"appController": controller})
    qml_path = Path(__file__).with_name("ui") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        controller.closeSession()
        return 4

    window = engine.rootObjects()[0]

    def configure_window() -> None:
        apply_mica(int(window.winId()), controller.darkMode)

    QTimer.singleShot(0, configure_window)
    controller.themeChanged.connect(configure_window)
    controller.closeRequested.connect(window.close)
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
