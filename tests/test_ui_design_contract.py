from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "app" / "openroto" / "ui"


class UiDesignContractTests(unittest.TestCase):
    def test_shared_design_primitives_are_packaged(self):
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        components = [
            "RotoTheme.qml",
            "GlassPanel.qml",
            "RotoButton.qml",
            "RotoSlider.qml",
            "RotoComboBox.qml",
            "RotoSwitch.qml",
            "StatusPill.qml",
        ]
        for component in components:
            self.assertTrue((UI / component).exists(), component)
            self.assertIn(component, build)

    def test_active_ui_uses_shared_theme_and_close_guard(self):
        polished = (UI / "PolishedMain.qml").read_text(encoding="utf-8")
        timed = (UI / "TimedMain.qml").read_text(encoding="utf-8")
        removal = (UI / "ObjectRemovalMain.qml").read_text(encoding="utf-8")

        self.assertIn("RotoTheme {", polished)
        self.assertIn('property string themeMode: "system"', polished)
        self.assertIn("customSidePanelComponent", polished)
        self.assertIn("workflowSwitcherComponent", polished)
        self.assertIn("blurEnabled: true", polished)
        self.assertIn("id: closeGuard", polished)
        self.assertIn('"Close when finished"', polished)
        self.assertIn('text: "Appearance"', timed)
        self.assertIn('"Light"', timed)
        self.assertIn('"Dark"', timed)
        self.assertIn("customSidePanelComponent:", removal)
        self.assertIn("viewerFrameSource:", removal)
        self.assertIn("RotoSlider", removal)
        self.assertIn("RotoComboBox", removal)


if __name__ == "__main__":
    unittest.main()
