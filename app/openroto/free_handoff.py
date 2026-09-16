from __future__ import annotations

import ctypes
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from openroto.core.manifest import write_manifest
from openroto.core.models import SessionManifest, SessionState
from openroto.inference.matte import render_matte_sequence
from openroto.ui.controller import ApplicationController

APP_NAME = "OpenRoto"
FREE_EXPORT_RE = re.compile(
    r"^(?P<prefix>OpenRotoFree_(?P<session>[A-Za-z0-9-]+)_n(?P<count>\d+)_w(?P<width>\d+)_h(?P<height>\d+)_f(?P<fps>\d+))"
)


def _local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME


def free_exchange_root() -> Path:
    return _local_root() / "FreeExchange"


def free_sessions_root() -> Path:
    return _local_root() / "Sessions"


def _agent_log(message: str) -> None:
    try:
        root = _local_root()
        root.mkdir(parents=True, exist_ok=True)
        with (root / "free-agent.log").open("a", encoding="utf-8") as stream:
            stream.write(time.strftime("%Y-%m-%d %H:%M:%S ") + message + "\n")
    except Exception:
        pass


def _self_command(*arguments: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *arguments]
    return [sys.executable, "-m", "openroto", *arguments]


def ensure_free_agent() -> None:
    creation_flags = 0
    if os.name == "nt":
        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | 0x00000008
    try:
        subprocess.Popen(
            _self_command("--free-agent"),
            cwd=str(Path(sys.executable).parent),
            creationflags=creation_flags,
            close_fds=True,
        )
    except Exception as error:
        _agent_log(f"could not start free agent: {error}")


def _acquire_agent_mutex():
    if os.name != "nt":
        return object()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.CreateMutexW(None, False, "Local\\OpenRotoFreeAgent")
    if not handle:
        return None
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return None
    return (kernel32, handle)


def _natural_key(path: Path):
    return [int(value) if value.isdigit() else value.lower() for value in re.split(r"(\d+)", path.name)]


def _fusion_comp_text(mask_path: Path, frame_count: int, width: int, height: int) -> str:
    filename = str(mask_path).replace("\\", "\\\\").replace('"', '\\"')
    last = max(0, frame_count - 1)
    return f'''Composition {{
    CurrentTime = 0,
    RenderRange = {{ 0, {last} }},
    GlobalRange = {{ 0, {last} }},
    Tools = ordered() {{
        MediaIn1 = MediaIn {{
            Extent_Set = true,
            ViewInfo = OperatorInfo {{ Pos = {{ 0, 0 }} }},
        }},
        OpenRotoMask = Loader {{
            Clips = {{
                Clip {{
                    ID = "Clip1",
                    Filename = "{filename}",
                    FormatID = "PNGFormat",
                    StartFrame = 0,
                    Length = {frame_count},
                    LengthSetManually = true,
                    TrimIn = 0,
                    TrimOut = {last},
                    ExtendFirst = 0,
                    ExtendLast = 0,
                    Loop = 0,
                    AspectMode = 0,
                    Depth = 0,
                    TimeCode = 0,
                    GlobalStart = 0,
                    GlobalEnd = {last}
                }}
            }},
            Inputs = {{ Clip = Input {{ Value = FuID {{ "Clip1" }} }} }},
            ViewInfo = OperatorInfo {{ Pos = {{ 0, 110 }} }},
        }},
        Transparent = Background {{
            Inputs = {{
                GlobalOut = Input {{ Value = {last} }},
                Width = Input {{ Value = {width} }},
                Height = Input {{ Value = {height} }},
                TopLeftAlpha = Input {{ Value = 0 }},
            }},
            ViewInfo = OperatorInfo {{ Pos = {{ 110, -55 }} }},
        }},
        ApplyOpenRotoMask = Merge {{
            Inputs = {{
                Background = Input {{ SourceOp = "Transparent", Source = "Output" }} }},
                Foreground = Input {{ SourceOp = "MediaIn1", Source = "Output" }} }},
                EffectMask = Input {{ SourceOp = "OpenRotoMask", Source = "Output" }} }},
                PerformDepthMerge = Input {{ Value = 0 }},
            }},
            ViewInfo = OperatorInfo {{ Pos = {{ 220, 0 }} }},
        }},
        MediaOut1 = MediaOut {{
            Inputs = {{ Input = Input {{ SourceOp = "ApplyOpenRotoMask", Source = "Output" }} }},
            ViewInfo = OperatorInfo {{ Pos = {{ 330, 0 }} }},
        }}
    }}
}}
'''


class FreeSessionAgent(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._mutex = _acquire_agent_mutex()
        self.is_primary = self._mutex is not None
        self._seen: set[str] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(650)
        self._timer.timeout.connect(self.poll)
        if self.is_primary:
            free_exchange_root().mkdir(parents=True, exist_ok=True)
            free_sessions_root().mkdir(parents=True, exist_ok=True)
            _agent_log("free agent started")
            self._timer.start()
            QTimer.singleShot(0, self.poll)

    def poll(self) -> None:
        try:
            groups: dict[str, tuple[re.Match[str], list[Path]]] = {}
            for path in free_exchange_root().iterdir():
                if not path.is_file() or path.suffix.lower() != ".png":
                    continue
                match = FREE_EXPORT_RE.match(path.name)
                if match is None:
                    continue
                session_id = match.group("session")
                previous = groups.get(session_id)
                if previous is None:
                    groups[session_id] = (match, [path])
                else:
                    previous[1].append(path)
            for session_id, (match, paths) in groups.items():
                if session_id in self._seen:
                    continue
                expected = int(match.group("count"))
                if len(paths) < expected:
                    continue
                newest = max(path.stat().st_mtime for path in paths)
                if time.time() - newest < 0.75:
                    continue
                self._seen.add(session_id)
                self._claim_session(match, sorted(paths, key=_natural_key)[:expected])
        except Exception as error:
            _agent_log(f"poll failed: {type(error).__name__}: {error}")

    def _claim_session(self, match: re.Match[str], exported: list[Path]) -> None:
        session_id = match.group("session")
        count = int(match.group("count"))
        width = int(match.group("width"))
        height = int(match.group("height"))
        fps = int(match.group("fps")) / 1000.0
        session_root = free_sessions_root() / session_id
        if session_root.exists():
            shutil.rmtree(session_root, ignore_errors=True)
        frames_dir = session_root / "frames"
        matte_dir = session_root / "matte"
        frames_dir.mkdir(parents=True, exist_ok=False)
        matte_dir.mkdir(parents=True, exist_ok=True)

        for index, source in enumerate(exported):
            shutil.move(str(source), frames_dir / f"{index:08d}.png")

        snapshot = session_root / "backup.drt"
        exchange_snapshot = free_exchange_root() / f"OpenRotoFree_{session_id}.drt"
        if exchange_snapshot.is_file():
            shutil.copy2(exchange_snapshot, snapshot)
        else:
            snapshot.touch()

        manifest = SessionManifest(
            session_id=session_id,
            token=secrets.token_urlsafe(32),
            bridge_host="127.0.0.1",
            bridge_port=1,
            project_id=f"free-project-{session_id}",
            project_name="DaVinci Resolve Free",
            timeline_id=f"free-timeline-{session_id}",
            timeline_name="Resolve timeline",
            clip_id=f"free-clip-{session_id}",
            clip_name="Resolve clip",
            track_index=1,
            record_start=0,
            record_end=count,
            source_start=0,
            source_end=count,
            fps=fps,
            width=width,
            height=height,
            frames_dir=str(frames_dir.resolve()),
            matte_dir=str(matte_dir.resolve()),
            snapshot_path=str(snapshot.resolve()),
            state=SessionState.READY,
        )
        manifest_path = session_root / "session.json"
        write_manifest(manifest_path, manifest)
        _agent_log(f"claimed free session {session_id} with {count} frames")
        self._launch_ui(manifest_path)

    def _launch_ui(self, manifest_path: Path) -> None:
        try:
            subprocess.Popen(
                _self_command("--session", str(manifest_path), "--handoff"),
                cwd=str(Path(sys.executable).parent),
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        except Exception as error:
            _agent_log(f"could not open free session UI: {error}")


class FreeHandoffController(ApplicationController):
    def __init__(self, manifest: SessionManifest) -> None:
        self._handoff_ready = False
        super().__init__(manifest)
        # The handoff does not use Resolve's Python socket bridge. Mark the
        # integration as available so the existing QML keeps the Apply action enabled.
        self._bridge_connected = True
        self._bridge_failed = False
        self._status = "Ready to select a subject"
        self._detail = "DaVinci Resolve Free handoff is active."
        self.connectionChanged.emit()
        self.statusChanged.emit()

    def renderAndApply(self) -> None:  # noqa: N802 - Qt slot name is part of the QML API
        if self._busy or not self._points.all():
            return
        self._run_async("Rendering matte", self._render_for_handoff)

    def _render_for_handoff(self) -> None:
        missing = [
            index
            for index in range(self.manifest.frame_count)
            if not self._raw_path(index).exists()
        ]
        if missing or self._tracking_dirty:
            self._track()
        if self._final_dir.exists():
            if self._final_dir.is_symlink() or self._final_dir.resolve().parent != Path(
                self.manifest.matte_dir
            ).resolve():
                raise RuntimeError("Refusing to replace an unsafe matte output folder")
            shutil.rmtree(self._final_dir)
        render_matte_sequence(
            self._raw_dir,
            self._final_dir,
            self.manifest.frame_count,
            self._matte_settings,
            progress=self._worker_progress,
            cancelled=self._cancel.is_set,
        )
        if self._cancel.is_set():
            raise InterruptedError("Rendering was cancelled")

        comp_path = Path(self.manifest.matte_dir) / "OpenRoto.comp"
        comp_path.write_text(
            _fusion_comp_text(
                self._final_dir / "matte_00000000.png",
                self.manifest.frame_count,
                self.manifest.width,
                self.manifest.height,
            ),
            encoding="utf-8",
        )
        ready = Path(self.manifest.matte_dir) / "READY_TO_APPLY"
        ready.write_text(json.dumps({"session_id": self.manifest.session_id}), encoding="utf-8")
        self._handoff_ready = True
        self._status = "Waiting for Resolve"
        self._detail = "Workspace › Scripts › OpenRoto Apply"

    def _finish_operation(self, status: str, detail: str) -> None:
        if status == "Ready" and self._handoff_ready:
            self._busy = False
            self._bridge_connected = False
            self._progress = 1.0
            self._status = "Matte ready for DaVinci Resolve"
            self._detail = "In Resolve choose Workspace › Scripts › OpenRoto Apply."
            self.busyChanged.emit()
            self.connectionChanged.emit()
            self.progressChanged.emit()
            self.statusChanged.emit()
            self.maskChanged.emit()
            return
        super()._finish_operation(status, detail)
