from __future__ import annotations

import ctypes
import os
import sys
import time
import traceback
from pathlib import Path

APP_NAME = "OpenRoto"
_STREAM_HANDLE = None


def _log_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root / "app.log"


def _console_log_path() -> Path:
    return _log_path().with_name("console.log")


def _ensure_standard_streams() -> None:
    """Give console-oriented libraries a writable stream in --windowed builds.

    PyInstaller's Windows ``--windowed`` bootloader intentionally sets
    ``sys.stdout`` and ``sys.stderr`` to ``None``. Hugging Face/tqdm and a few
    dependencies used while SAM2 models are loaded expect a file-like object
    and call ``.write()`` unconditionally. Route missing streams to a small
    persistent log instead of letting model loading crash with a NoneType error.
    """

    global _STREAM_HANDLE
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        if _STREAM_HANDLE is None:
            _STREAM_HANDLE = _console_log_path().open(
                "a", encoding="utf-8", buffering=1, errors="backslashreplace"
            )
            _STREAM_HANDLE.write(
                time.strftime("\n%Y-%m-%d %H:%M:%S ")
                + "=== windowed stdio redirected ===\n"
            )
        if sys.stdout is None:
            sys.stdout = _STREAM_HANDLE
        if sys.stderr is None:
            sys.stderr = _STREAM_HANDLE
    except Exception:
        # Last-resort writable streams. The model loader needs a file-like
        # object even if the normal OpenRoto log directory is unavailable.
        fallback = open(os.devnull, "w", encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = fallback
        if sys.stderr is None:
            sys.stderr = fallback


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
    _ensure_standard_streams()
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
