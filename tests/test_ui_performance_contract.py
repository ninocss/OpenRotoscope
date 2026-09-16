from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))


class UiResponsivenessContractTests(unittest.TestCase):
    def test_polished_ui_timing_overlay_and_removal_shell_are_packaged_and_loaded(self):
        main = (ROOT / "app" / "openroto" / "main.py").read_text(encoding="utf-8")
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        polished = (ROOT / "app" / "openroto" / "ui" / "PolishedMain.qml").read_text(
            encoding="utf-8"
        )
        timed = (ROOT / "app" / "openroto" / "ui" / "TimedMain.qml").read_text(
            encoding="utf-8"
        )
        removal = (ROOT / "app" / "openroto" / "ui" / "ObjectRemovalMain.qml").read_text(
            encoding="utf-8"
        )
        removal_models = (
            ROOT / "app" / "openroto" / "ui" / "RemovalModelsMain.qml"
        ).read_text(encoding="utf-8")
        model_manager = (ROOT / "app" / "openroto" / "ui" / "model_manager.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('"RemovalModelsMain.qml"', main)
        self.assertIn("PolishedMain.qml", build)
        self.assertIn("TimedMain.qml", build)
        self.assertIn("ObjectRemovalMain.qml", build)
        self.assertIn("RemovalModelsMain.qml", build)
        self.assertIn("openroto\\removal_backends", build)
        self.assertIn("component CenteredTip", polished)
        self.assertIn("component SubjectMarker", polished)
        self.assertNotIn('text: pointItem.modelData.positive ? "+"', polished)
        self.assertIn("window.appController.performanceTimings", timed)
        self.assertIn("last measurement · milliseconds", timed)
        self.assertIn("window.modelManager.performanceStatsVisible", timed)
        self.assertIn('text: "Performance statistics"', timed)
        self.assertIn("setPerformanceStatsVisible", timed)
        self.assertIn('QSettings("OpenRoto", "OpenRoto")', model_manager)
        self.assertIn('"showPerformanceStats"', model_manager)
        self.assertIn("def setPerformanceStatsVisible", model_manager)
        self.assertIn("TimedMain {", removal)
        self.assertIn('text: "Rotoscope"', removal)
        self.assertIn('text: "Remove"', removal)
        self.assertIn("ObjectRemovalMain {", removal_models)
        self.assertIn("Object Removal Models", removal_models)
        self.assertIn("Benchmark 17 frames", removal_models)

    def test_session_masks_use_fast_lossless_png_writes(self):
        matte = (ROOT / "app" / "openroto" / "inference" / "matte.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("compress_level=1", matte)
        self.assertIn("compress_level=2", matte)
        self.assertNotIn("optimize=True", matte)


if __name__ == "__main__":
    unittest.main()
