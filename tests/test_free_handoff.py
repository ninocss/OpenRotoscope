from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openroto.free_handoff import FREE_EXPORT_RE, fusion_comp_text


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


if __name__ == "__main__":
    unittest.main()
