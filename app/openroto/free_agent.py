from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from openroto.free_handoff import FreeSessionAgent as _BaseFreeSessionAgent
from openroto.free_handoff import free_sessions_root

AGENT_PROTOCOL_VERSION = "free-v3"
_HEARTBEAT_INTERVAL_SECONDS = 5.0


def _local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "OpenRoto"


def agent_heartbeat_path(root: Path | None = None) -> Path:
    base = _local_root() if root is None else Path(root)
    return base / "free-agent-heartbeat.json"


def existing_session_ids(root: Path | None = None) -> set[str]:
    """Return published session ids that must never be claimed again.

    Fusion Loader nodes may keep referencing files in these folders after
    OpenRoto closes. A stale FreeExchange export with the same id therefore
    must be ignored rather than retried forever or allowed to overwrite it.
    """
    sessions = free_sessions_root() if root is None else Path(root)
    try:
        return {
            path.name
            for path in sessions.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        }
    except OSError:
        return set()


def write_agent_heartbeat(path: Path | None = None) -> Path:
    """Publish proof that the process owning the Free-agent mutex is current."""

    destination = agent_heartbeat_path() if path is None else Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    executable = Path(sys.executable)
    try:
        executable = executable.resolve()
    except OSError:
        pass
    payload = {
        "protocol": AGENT_PROTOCOL_VERSION,
        "pid": os.getpid(),
        "executable": str(executable),
        "timestamp": time.time(),
    }
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(temporary, destination)
    return destination


class FreeSessionAgent(_BaseFreeSessionAgent):
    """Free agent that remembers sessions and publishes a verified heartbeat."""

    def __init__(self) -> None:
        self._last_heartbeat = 0.0
        super().__init__()
        if self.is_primary:
            # super() schedules its first poll for the next event-loop turn, so
            # seeding _seen here happens before any exchange files are inspected.
            self._seen.update(existing_session_ids())
            self._publish_heartbeat(force=True)

    def poll(self) -> None:
        if self.is_primary:
            self._publish_heartbeat()
        super().poll()

    def _publish_heartbeat(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_heartbeat < _HEARTBEAT_INTERVAL_SECONDS:
            return
        try:
            write_agent_heartbeat()
            self._last_heartbeat = now
        except Exception:
            # A heartbeat is diagnostic/installation verification only. Failure
            # to write it must never stop an otherwise functional handoff poll.
            pass
