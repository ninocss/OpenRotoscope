from __future__ import annotations

from pathlib import Path

from openroto.free_handoff import FreeSessionAgent as _BaseFreeSessionAgent
from openroto.free_handoff import free_sessions_root


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


class FreeSessionAgent(_BaseFreeSessionAgent):
    """Free agent that remembers sessions already published on disk."""

    def __init__(self) -> None:
        super().__init__()
        if self.is_primary:
            # super() schedules its first poll for the next event-loop turn, so
            # seeding _seen here happens before any exchange files are inspected.
            self._seen.update(existing_session_ids())
