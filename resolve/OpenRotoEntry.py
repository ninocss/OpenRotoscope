"""Diagnostic bootstrap executed by Resolve as OpenRoto.py3."""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

APP_NAME = "OpenRoto"


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


def _run() -> None:
    _prepare_environment()
    entry_path = _entry_path()
    _write("=== Resolve Python bootstrap entered ===")
    _write(f"entry_path={str(entry_path)!r}")
    _write(f"python={sys.version!r}")
    _write(f"executable={sys.executable!r}")
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
        sys.stdout = console
        sys.stderr = console
        try:
            source = bridge_path.read_text(encoding="utf-8")
            code = compile(source, str(bridge_path), "exec")
            bridge_globals = globals()
            bridge_globals["__file__"] = str(bridge_path)
            exec(code, bridge_globals, bridge_globals)
            _write("bridge source returned")
        finally:
            sys.stdout = previous_stdout
            sys.stderr = previous_stderr


try:
    _run()
except BaseException as error:
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
