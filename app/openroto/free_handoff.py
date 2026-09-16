from __future__ import annotations

import contextlib
import ctypes
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
    return [
        int(value) if value.isdigit() else value.lower()
        for value in re.split(r"(\d+)", path.name)
    ]


def fusion_comp_text(mask_path: Path, frame_count: int, width: int, height: int) -> str:
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
                Background = Input {{ SourceOp = "Transparent", Source = "Output" }},
                Foreground = Input {{ SourceOp = "MediaIn1", Source = "Output" }},
                EffectMask = Input {{ SourceOp = "OpenRotoMask", Source = "Output" }},
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

                exchange_snapshot = free_exchange_root() / f"OpenRotoFree_{session_id}.drt"
                if not exchange_snapshot.is_file() or exchange_snapshot.stat().st_size <= 0:
                    continue

                newest = max(
                    [path.stat().st_mtime for path in paths]
                    + [exchange_snapshot.stat().st_mtime]
                )
                if time.time() - newest < 0.75:
                    continue

                try:
                    self._claim_session(match, sorted(paths, key=_natural_key)[:expected])
                except Exception as error:
                    # Do not mark the session as seen. A transient file lock or an
                    # agent/UI startup race must be retried on the next poll.
                    _agent_log(
                        f"claim failed for free session {session_id}: "
                        f"{type(error).__name__}: {error}"
                    )
                    continue
                self._seen.add(session_id)
        except Exception as error:
            _agent_log(f"poll failed: {type(error).__name__}: {error}")

    def _claim_session(self, match: re.Match[str], exported: list[Path]) -> None:
        session_id = match.group("session")
        count = int(match.group("count"))
        width = int(match.group("width"))
        height = int(match.group("height"))
        fps = int(match.group("fps")) / 1000.0
        session_root = free_sessions_root() / session_id
        staging_root = free_sessions_root() / f".{session_id}.claiming"
        exchange_snapshot = free_exchange_root() / f"OpenRotoFree_{session_id}.drt"

        if len(exported) != count:
            raise RuntimeError(
                f"Resolve exported {len(exported)} frames, expected {count}"
            )
        if not exchange_snapshot.is_file() or exchange_snapshot.stat().st_size <= 0:
            raise RuntimeError("Resolve safety snapshot is not ready yet")
        if session_root.exists():
            # Never overwrite an old applied session. Fusion Loader nodes can keep
            # referencing these files long after OpenRoto has closed.
            raise RuntimeError(
                f"session folder already exists: {session_root}. Start OpenRoto again "
                "to obtain a fresh Resolve Free session id."
            )

        shutil.rmtree(staging_root, ignore_errors=True)
        frames_dir = staging_root / "frames"
        matte_dir = staging_root / "matte"
        frames_dir.mkdir(parents=True, exist_ok=False)
        matte_dir.mkdir(parents=True, exist_ok=True)

        try:
            for index, source in enumerate(exported):
                if not source.is_file() or source.stat().st_size <= 0:
                    raise RuntimeError(f"Exported frame {index + 1} is not ready")
                shutil.copy2(source, frames_dir / f"{index:08d}.png")

            snapshot = staging_root / "backup.drt"
            shutil.copy2(exchange_snapshot, snapshot)
            if snapshot.stat().st_size <= 0:
                raise RuntimeError("Copied Resolve safety snapshot is empty")

            # The manifest points at the final path. Rename the complete staging
            # directory atomically before launching the UI.
            final_frames = session_root / "frames"
            final_matte = session_root / "matte"
            final_snapshot = session_root / "backup.drt"
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
                frames_dir=str(final_frames.resolve()),
                matte_dir=str(final_matte.resolve()),
                snapshot_path=str(final_snapshot.resolve()),
                state=SessionState.READY,
            )
            manifest_path = staging_root / "session.json"
            write_manifest(manifest_path, manifest)

            os.replace(staging_root, session_root)
            final_manifest = session_root / "session.json"
            _agent_log(f"claimed free session {session_id} with {count} frames")
            self._launch_ui(final_manifest)

            # Only remove the exchange copies after the complete session is in its
            # final location and the UI process was started successfully.
            for source in exported:
                with contextlib.suppress(OSError):
                    source.unlink()
            with contextlib.suppress(OSError):
                exchange_snapshot.unlink()
        except Exception:
            shutil.rmtree(staging_root, ignore_errors=True)
            # If the staging directory was already renamed but UI startup failed,
            # remove only this not-yet-applied session. Exchange sources are still
            # present, so the next poll can retry safely.
            if session_root.exists():
                shutil.rmtree(session_root, ignore_errors=True)
            raise

    def _launch_ui(self, manifest_path: Path) -> None:
        subprocess.Popen(
            _self_command("--session", str(manifest_path), "--handoff"),
            cwd=str(Path(sys.executable).parent),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )


class FreeHandoffController(ApplicationController):
    APPLY_TIMEOUT_SECONDS = 120.0

    def __init__(self, manifest: SessionManifest) -> None:
        self._handoff_applied = False
        self._apply_requested = False
        super().__init__(manifest)
        # Port 1 is intentionally unreachable for handoff manifests. The base
        # controller catches that connection error; the filesystem handoff then
        # presents itself as the active integration to the existing QML.
        self._bridge_connected = True
        self._bridge_failed = False
        self._status = "Ready to select a subject"
        self._detail = "DaVinci Resolve Free handoff is active."
        self.connectionChanged.emit()
        self.statusChanged.emit()

    @property
    def _control_path(self) -> Path:
        return Path(self.manifest.matte_dir) / "CONTROL.lua"

    @property
    def _applied_ack_path(self) -> Path:
        return Path(self.manifest.matte_dir) / "APPLIED.drt"

    @property
    def _failed_ack_path(self) -> Path:
        return Path(self.manifest.matte_dir) / "APPLY_FAILED.drt"

    def _send_control(self, action: str) -> None:
        token = f"openroto-free-{action}:{self.manifest.session_id}"
        path = self._control_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(f'return "{token}"\n', encoding="utf-8")
        os.replace(temporary, path)

    def renderAndApply(self) -> None:  # noqa: N802 - Qt slot name is part of the QML API
        if self._busy or not self._points.all():
            return
        self._run_async("Render & Apply", self._render_for_handoff)

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
            fusion_comp_text(
                self._final_dir / "matte_00000000.png",
                self.manifest.frame_count,
                self.manifest.width,
                self.manifest.height,
            ),
            encoding="utf-8",
        )

        for stale in (self._applied_ack_path, self._failed_ack_path):
            stale.unlink(missing_ok=True)
        self._send_control("apply")
        self._apply_requested = True
        self._set_progress_from_worker(
            0.98, "Waiting for Resolve", "Applying the matte in DaVinci Resolve Free"
        )

        deadline = time.monotonic() + self.APPLY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self._cancel.is_set():
                self._send_control("cancel")
                raise InterruptedError("Applying was cancelled")
            if self._failed_ack_path.is_file():
                raise RuntimeError(
                    "DaVinci Resolve could not apply the OpenRoto matte. "
                    "The safety snapshot was kept in the session folder."
                )
            if self._applied_ack_path.is_file():
                self._handoff_applied = True
                self._worker_progress(1.0, "Applied in DaVinci Resolve")
                return
            time.sleep(0.20)

        raise RuntimeError(
            "DaVinci Resolve did not confirm the OpenRoto apply step within two minutes."
        )

    def _finish_operation(self, status: str, detail: str) -> None:
        if status == "Ready" and self._handoff_applied:
            self._busy = False
            self._completed = True
            self._progress = 1.0
            self._status = "Applied in DaVinci Resolve"
            self._detail = "OpenRoto will close automatically."
            self.busyChanged.emit()
            self.progressChanged.emit()
            self.statusChanged.emit()
            self.maskChanged.emit()
            QTimer.singleShot(250, self.closeRequested.emit)
            return
        super()._finish_operation(status, detail)

    def closeSession(self) -> None:  # noqa: N802 - mirrors the base Qt-facing lifecycle
        if not self._handoff_applied:
            try:
                self._send_control("cancel")
            except Exception:
                pass
        super().closeSession()
