from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from openroto.free_handoff import FREE_EXPORT_RE, FreeSessionAgent, fusion_comp_text


class _ClaimAgent:
    _claim_session = FreeSessionAgent._claim_session

    def __init__(self, *, fail_launch: bool = False) -> None:
        self.fail_launch = fail_launch
        self.launched: Path | None = None

    def _launch_ui(self, manifest_path: Path) -> None:
        if self.fail_launch:
            raise OSError("simulated UI launch failure")
        self.launched = manifest_path


class FreeHandoffTests(unittest.TestCase):
    def test_free_export_filename_contract(self):
        match = FREE_EXPORT_RE.match(
            "OpenRotoFree_clipABC-7_n42_w1920_h1080_f25000_00000000.png"
        )
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual("clipABC-7", match.group("session"))
        self.assertEqual(42, int(match.group("count")))
        self.assertEqual(1920, int(match.group("width")))
        self.assertEqual(1080, int(match.group("height")))
        self.assertEqual(25000, int(match.group("fps")))

    def test_free_comp_points_loader_at_final_matte_sequence(self):
        with tempfile.TemporaryDirectory() as temporary:
            first_mask = Path(temporary) / "matte" / "final" / "matte_00000000.png"
            text = fusion_comp_text(first_mask, frame_count=12, width=1280, height=720)
        self.assertIn("Composition {", text)
        self.assertIn("OpenRotoMask = Loader", text)
        self.assertIn(str(first_mask).replace("\\", "\\\\"), text)
        self.assertIn("Length = 12", text)
        self.assertIn("GlobalEnd = 11", text)
        self.assertIn("Width = Input { Value = 1280 }", text)
        self.assertIn("Height = Input { Value = 720 }", text)
        self.assertIn(
            'EffectMask = Input { SourceOp = "OpenRotoMask", Source = "Output" }', text
        )

    def _make_export(self, root: Path):
        exchange = root / "exchange"
        sessions = root / "sessions"
        exchange.mkdir()
        sessions.mkdir()
        names = [
            "OpenRotoFree_clipABC-7_n2_w32_h18_f24000_00000000.png",
            "OpenRotoFree_clipABC-7_n2_w32_h18_f24000_00000001.png",
        ]
        paths = []
        for index, name in enumerate(names):
            path = exchange / name
            Image.new("RGB", (32, 18), (index * 30, 20, 10)).save(path)
            paths.append(path)
        snapshot = exchange / "OpenRotoFree_clipABC-7.drt"
        snapshot.write_text("resolve snapshot", encoding="utf-8")
        match = FREE_EXPORT_RE.match(names[0])
        assert match is not None
        return exchange, sessions, match, paths, snapshot

    def test_claim_is_transactional_and_removes_exchange_only_after_ui_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exchange, sessions, match, paths, snapshot = self._make_export(root)
            agent = _ClaimAgent()
            with (
                mock.patch("openroto.free_handoff.free_exchange_root", return_value=exchange),
                mock.patch("openroto.free_handoff.free_sessions_root", return_value=sessions),
            ):
                agent._claim_session(match, paths)

            session = sessions / "clipABC-7"
            self.assertEqual(session / "session.json", agent.launched)
            self.assertTrue((session / "frames" / "00000000.png").is_file())
            self.assertTrue((session / "frames" / "00000001.png").is_file())
            self.assertTrue((session / "backup.drt").is_file())
            self.assertFalse(snapshot.exists())
            self.assertTrue(all(not path.exists() for path in paths))
            self.assertFalse((sessions / ".clipABC-7.claiming").exists())

    def test_failed_ui_launch_keeps_exchange_for_retry_and_removes_partial_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exchange, sessions, match, paths, snapshot = self._make_export(root)
            agent = _ClaimAgent(fail_launch=True)
            with (
                mock.patch("openroto.free_handoff.free_exchange_root", return_value=exchange),
                mock.patch("openroto.free_handoff.free_sessions_root", return_value=sessions),
            ):
                with self.assertRaises(OSError):
                    agent._claim_session(match, paths)

            self.assertTrue(snapshot.is_file())
            self.assertTrue(all(path.is_file() for path in paths))
            self.assertFalse((sessions / "clipABC-7").exists())
            self.assertFalse((sessions / ".clipABC-7.claiming").exists())

    def test_claim_refuses_to_overwrite_assets_from_an_existing_applied_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exchange, sessions, match, paths, snapshot = self._make_export(root)
            existing = sessions / "clipABC-7"
            existing.mkdir()
            sentinel = existing / "old-loader-asset.png"
            sentinel.write_bytes(b"keep")
            agent = _ClaimAgent()
            with (
                mock.patch("openroto.free_handoff.free_exchange_root", return_value=exchange),
                mock.patch("openroto.free_handoff.free_sessions_root", return_value=sessions),
            ):
                with self.assertRaisesRegex(RuntimeError, "session folder already exists"):
                    agent._claim_session(match, paths)

            self.assertEqual(b"keep", sentinel.read_bytes())
            self.assertTrue(snapshot.is_file())
            self.assertTrue(all(path.is_file() for path in paths))

    def test_free_apply_uses_protected_waiting_state(self):
        source = Path(__file__).resolve().parents[1] / "app" / "openroto" / "free_handoff.py"
        text = source.read_text(encoding="utf-8")
        self.assertIn('0.98, "Waiting for Resolve", "Applying the matte in DaVinci Resolve Free"', text)
        self.assertNotIn('_worker_progress(0.98, "Applying in DaVinci Resolve")', text)


if __name__ == "__main__":
    unittest.main()
