from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.free_agent import (
    AGENT_PROTOCOL_VERSION,
    existing_session_ids,
    write_agent_heartbeat,
)


class FreeAgentGuardTests(unittest.TestCase):
    def test_existing_published_sessions_are_seeded_as_seen(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "old-session-1").mkdir()
            (root / "old-session-2").mkdir()
            (root / ".claiming-session").mkdir()
            (root / "not-a-session.txt").write_text("x", encoding="utf-8")

            self.assertEqual(
                {"old-session-1", "old-session-2"},
                existing_session_ids(root),
            )

    def test_agent_heartbeat_identifies_protocol_and_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            heartbeat = Path(temporary) / "heartbeat.json"
            written = write_agent_heartbeat(heartbeat)
            payload = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual("free-v3", AGENT_PROTOCOL_VERSION)
            self.assertEqual(AGENT_PROTOCOL_VERSION, payload["protocol"])
            self.assertEqual(Path(sys.executable).resolve(), Path(payload["executable"]))
            self.assertGreater(int(payload["pid"]), 0)
            self.assertGreater(float(payload["timestamp"]), 0.0)

    def test_dev_install_requires_verified_current_agent(self):
        script = (ROOT / "scripts" / "install-dev.ps1").read_text(encoding="utf-8")
        self.assertIn('$agentProtocol = "free-v3"', script)
        self.assertIn("free-agent-heartbeat.json", script)
        self.assertIn("Verified current OpenRoto Free agent protocol", script)
        self.assertIn("OpenRoto Free agent verification failed", script)
        self.assertIn("Get-FileHash", script)
        self.assertIn("Installed and verified Resolve launcher", script)

    def test_main_uses_guarded_free_agent(self):
        main = (ROOT / "app" / "openroto" / "main.py").read_text(encoding="utf-8")
        self.assertIn("from openroto.free_agent import FreeSessionAgent", main)
        self.assertNotIn(
            "from openroto.free_handoff import FreeHandoffController, FreeSessionAgent",
            main,
        )


if __name__ == "__main__":
    unittest.main()
