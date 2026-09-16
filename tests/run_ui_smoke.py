"""Manual/offscreen QML smoke test; exits non-zero when the window cannot load."""

from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.core.manifest import write_manifest
from openroto.core.models import SessionManifest, SessionState
from openroto.main import main


def serve_once(server: socket.socket) -> None:
    connection, _ = server.accept()
    with connection:
        stream = connection.makefile("rwb")
        line = stream.readline()
        message = json.loads(line)
        assert message["type"] == "hello"
        stream.write(b'{"type":"ready"}\n')
        stream.flush()
        while stream.readline():
            pass


def run() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["OPENROTO_SMOKE_EXIT_MS"] = "1200"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        frames = root / "frames"
        matte = root / "matte"
        frames.mkdir()
        matte.mkdir()
        Image.new("RGB", (640, 360), "#24314a").save(frames / "00000000.png")
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        thread = threading.Thread(target=serve_once, args=(server,), daemon=True)
        thread.start()
        manifest = SessionManifest(
            session_id="smoke-session-0001",
            token="smoke-token-0000000000000000000000000000",
            bridge_host="127.0.0.1",
            bridge_port=server.getsockname()[1],
            project_id="project",
            project_name="Project",
            timeline_id="timeline",
            timeline_name="Timeline",
            clip_id="clip",
            clip_name="UI smoke clip",
            track_index=1,
            record_start=0,
            record_end=1,
            source_start=0,
            source_end=1,
            fps=24,
            width=640,
            height=360,
            frames_dir=str(frames.resolve()),
            matte_dir=str(matte.resolve()),
            snapshot_path=str((root / "snapshot.drt").resolve()),
            state=SessionState.READY,
        )
        manifest_path = root / "session.json"
        write_manifest(manifest_path, manifest)
        try:
            return main(["openroto", "--session", str(manifest_path)])
        finally:
            server.close()


if __name__ == "__main__":
    raise SystemExit(run())
