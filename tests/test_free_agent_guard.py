from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.free_agent import existing_session_ids


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

    def test_main_uses_guarded_free_agent(self):
        main = (ROOT / "app" / "openroto" / "main.py").read_text(encoding="utf-8")
        self.assertIn("from openroto.free_agent import FreeSessionAgent", main)
        self.assertNotIn(
            "from openroto.free_handoff import FreeHandoffController, FreeSessionAgent",
            main,
        )


if __name__ == "__main__":
    unittest.main()
