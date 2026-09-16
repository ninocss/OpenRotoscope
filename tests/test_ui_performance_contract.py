from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))


class UiResponsivenessContractTests(unittest.TestCase):
    def test_polished_ui_is_packaged_and_loaded(self):
        main = (ROOT / "app" / "openroto" / "main.py").read_text(encoding="utf-8")
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        qml = (ROOT / "app" / "openroto" / "ui" / "PolishedMain.qml").read_text(
            encoding="utf-8"
        )

        self.assertIn('"PolishedMain.qml"', main)
        self.assertIn("PolishedMain.qml", build)
        self.assertIn("component CenteredTip", qml)
        self.assertIn("component SubjectMarker", qml)
        self.assertNotIn('text: pointItem.modelData.positive ? "+"', qml)

    def test_session_masks_use_fast_lossless_png_writes(self):
        matte = (ROOT / "app" / "openroto" / "inference" / "matte.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("compress_level=1", matte)
        self.assertIn("compress_level=2", matte)
        self.assertNotIn("optimize=True", matte)


if __name__ == "__main__":
    unittest.main()
