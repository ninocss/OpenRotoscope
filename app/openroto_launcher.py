from __future__ import annotations

import ctypes
import os
import sys
import time
import traceback
from pathlib import Path

APP_NAME = "OpenRoto"


def _log_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root / "app.log"


def _log(message: str) -> None:
    try:
        with _log_path().open("a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + message + "\n")
    except Exception:
        pass


def _show_error(text: str) -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.user32.MessageBoxW(None, text, f"{APP_NAME} — Startup error", 0x10)
    except Exception:
        pass


def main() -> int:
    _log("=== packaged app launcher started ===")
    _log(f"argv={sys.argv!r}")
    _log(f"executable={sys.executable!r}")
    _log(f"python={sys.version!r}")
    _log(f"frozen={getattr(sys, 'frozen', False)!r}")
    _log(f"cwd={os.getcwd()!r}")
    try:
        from openroto.main import main as application_main

        result = int(application_main())
        _log(f"application exited normally with code {result}")
        return result
    except BaseException as error:
        detail = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        _log("unhandled startup exception:\n" + detail)
        _show_error(
            "OpenRoto could not start.\n\n"
            f"{error}\n\n"
            "Details were written to %LOCALAPPDATA%\\OpenRoto\\app.log"
        )
        return 90


if __name__ == "__main__":
    raise SystemExit(main())
