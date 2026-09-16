"""Diagnostic bootstrap executed by Resolve as OpenRoto.py3."""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

APP_NAME = "OpenRoto"
STATUS_KEY = "OpenRoto.BootstrapStatus"


def _fusion_host():
    return globals().get("fusion") or globals().get("fu") or globals().get("app")


def _set_status(value: str) -> None:
    """Expose bootstrap state to the sandboxed Lua launcher without file I/O."""
    try:
        host = _fusion_host()
        if host is not None:
            host.SetData(STATUS_KEY, str(value))
    except Exception:
        pass


def _root() -> Path:
    path = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(message: str) -> None:
    try:
        with (_root() / "bridge-bootstrap.log").open("a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + message + "\n")
    except Exception:
        pass


def _entry_path() -> Path:
    current = globals().get("__file__")
    if current:
        return Path(str(current)).resolve()
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return (
        appdata
        / "Blackmagic Design"
        / "DaVinci Resolve"
        / "Support"
        / "OpenRoto"
        / "OpenRoto.py3"
    )


def _prepare_environment() -> None:
    # The installer's Resolve-specific Python home also tells us where the app
    # lives, including when the user chose a non-default installation folder.
    runtime_home = os.environ.get("FUSION_Python3_Home")
    if runtime_home:
        candidate = Path(runtime_home).resolve().parent / "OpenRoto.exe"
        if candidate.is_file():
            os.environ.setdefault("OPENROTO_APP", str(candidate))

    program_data = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
    resolve_api = (
        program_data
        / "Blackmagic Design"
        / "DaVinci Resolve"
        / "Support"
        / "Developer"
        / "Scripting"
    )
    modules = resolve_api / "Modules"
    resolve_lib = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / (
        "Blackmagic Design/DaVinci Resolve/fusionscript.dll"
    )
    os.environ.setdefault("RESOLVE_SCRIPT_API", str(resolve_api))
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", str(resolve_lib))
    if modules.is_dir() and str(modules) not in sys.path:
        sys.path.append(str(modules))


def _bridge_trace(filename: str):
    def trace(frame, event, arg):
        if frame.f_code.co_filename == filename:
            name = frame.f_code.co_name
            line = frame.f_lineno
            if event == "call":
                _write(f"bridge CALL {name} line={line}")
            elif event == "return":
                _write(f"bridge RETURN {name} line={line}")
            elif event == "exception":
                exc_type, exc_value, _ = arg
                _write(
                    f"bridge EXCEPTION {name} line={line}: "
                    f"{getattr(exc_type, '__name__', exc_type)}: {exc_value}"
                )
        return trace

    return trace


def _run() -> None:
    _set_status("entered")
    _write("=== Resolve Python bootstrap entered ===")
    _write(f"python={sys.version!r}")
    _write(f"executable={sys.executable!r}")

    # Resolve/Fusion's Windows scripting bridge is not reliable with Python
    # 3.12+, and some Resolve-side modules still depend on APIs removed there.
    # OpenRoto ships a private 3.10 runtime specifically for this in-process
    # bridge. Fail loudly if Resolve ignored FUSION_Python3_Home and loaded a
    # different interpreter instead of silently doing nothing.
    if sys.version_info >= (3, 12):
        raise RuntimeError(
            "DaVinci Resolve loaded Python "
            f"{sys.version_info.major}.{sys.version_info.minor}, but OpenRoto's "
            "Resolve bridge requires Python 3.10/3.11. Reinstall the newest "
            "OpenRoto build and fully restart Resolve."
        )

    _prepare_environment()
    entry_path = _entry_path()
    _write(f"entry_path={str(entry_path)!r}")
    _write(f"prefix={sys.prefix!r}; base_prefix={getattr(sys, 'base_prefix', None)!r}")
    _write(f"cwd={os.getcwd()!r}")
    _write(f"FUSION_Python3_Home={os.environ.get('FUSION_Python3_Home')!r}")
    _write(f"PYTHONHOME={os.environ.get('PYTHONHOME')!r}")
    _write(f"OPENROTO_APP={os.environ.get('OPENROTO_APP')!r}")
    _write(f"RESOLVE_SCRIPT_API={os.environ.get('RESOLVE_SCRIPT_API')!r}")
    _write(f"RESOLVE_SCRIPT_LIB={os.environ.get('RESOLVE_SCRIPT_LIB')!r}")
    _write(
        "resolve globals: "
        f"resolve={globals().get('resolve') is not None}, "
        f"app={globals().get('app') is not None}, "
        f"fusion={globals().get('fusion') is not None}, "
        f"fu={globals().get('fu') is not None}"
    )
    _write("sys.path=" + repr(sys.path))

    bridge_path = entry_path.with_name("OpenRotoBridge.py")
    _write(f"bridge_path={str(bridge_path)!r}; exists={bridge_path.is_file()}")
    if not bridge_path.is_file():
        raise FileNotFoundError(f"OpenRoto bridge source is missing: {bridge_path}")

    console_path = _root() / "bridge-console.log"
    with console_path.open("a", encoding="utf-8", buffering=1) as console:
        previous_stdout, previous_stderr = sys.stdout, sys.stderr
        previous_trace = sys.gettrace()
        sys.stdout = console
        sys.stderr = console
        sys.settrace(_bridge_trace(str(bridge_path)))
        try:
            source = bridge_path.read_text(encoding="utf-8")
            code = compile(source, str(bridge_path), "exec")
            bridge_globals = globals()
            bridge_globals["__file__"] = str(bridge_path)
            _set_status("bridge-running")
            exec(code, bridge_globals, bridge_globals)
            _write("bridge source returned")
            _set_status("bridge-returned")
        finally:
            sys.settrace(previous_trace)
            sys.stdout = previous_stdout
            sys.stderr = previous_stderr


try:
    _run()
except BaseException as error:
    _set_status(f"failed:{type(error).__name__}:{error}")
    detail = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    _write("bootstrap failure:\n" + detail)
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            f"OpenRoto could not start its Resolve bridge.\n\n{error}\n\n"
            "See %LOCALAPPDATA%\\OpenRoto\\bridge-bootstrap.log",
            "OpenRoto — Resolve bridge error",
            0x10,
        )
    except Exception:
        pass
    raise
