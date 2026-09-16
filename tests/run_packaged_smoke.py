"""Smoke-test the packaged OpenRoto executable with a synthetic Resolve session."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import threading
from pathlib import Path

from PIL import Image


def serve_once(server: socket.socket) -> None:
    connection, _ = server.accept()
    with connection:
        stream = connection.makefile("rwb")
        line = stream.readline()
        message = json.loads(line)
        assert message["type"] == "hello"
        assert message["protocol"] == 1
        stream.write(b'{"type":"ready","session_id":"smoke-session-0001"}\n')
        stream.flush()
        while stream.readline():
            pass


def run(executable: Path) -> int:
    executable = executable.resolve(strict=True)
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

        manifest = {
            "session_id": "smoke-session-0001",
            "token": "smoke-token-0000000000000000000000000000",
            "bridge_host": "127.0.0.1",
            "bridge_port": server.getsockname()[1],
            "project_id": "project",
            "project_name": "Project",
            "timeline_id": "timeline",
            "timeline_name": "Timeline",
            "clip_id": "clip",
            "clip_name": "Packaged smoke clip",
            "track_index": 1,
            "record_start": 0,
            "record_end": 1,
            "source_start": 0,
            "source_end": 1,
            "fps": 24.0,
            "width": 640,
            "height": 360,
            "frames_dir": str(frames.resolve()),
            "matte_dir": str(matte.resolve()),
            "snapshot_path": str((root / "snapshot.drt").resolve()),
            "state": "ready",
            "frame_pattern": "%08d.png",
            "matte_pattern": "matte_%08d.png",
            "schema_version": 1,
            "linked_item_ids": [],
        }
        manifest_path = root / "session.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["OPENROTO_SMOKE_EXIT_MS"] = "1500"
        try:
            completed = subprocess.run(
                [str(executable), "--session", str(manifest_path)],
                env=env,
                timeout=30,
                check=False,
            )
        finally:
            server.close()

        if completed.returncode != 0:
            raise SystemExit(f"Packaged OpenRoto exited with code {completed.returncode}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    return run(args.executable)


if __name__ == "__main__":
    raise SystemExit(main())
