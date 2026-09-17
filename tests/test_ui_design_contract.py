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

    def test_active_ui_uses_shared_theme_close_guard_and_compact_mode(self):
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
        self.assertIn("minimumWidth: 900", polished)
        self.assertIn("minimumHeight: 480", polished)
        self.assertIn("compactMode: window.width < 1120", polished)
        self.assertIn("id: controlsDrawer", polished)
        self.assertIn("openCompactControls", polished)
        self.assertIn('"Subject · LMB"', polished)
        self.assertIn('"Exclude · RMB"', polished)
        self.assertIn('toolTip: "Open controls"', polished)
        self.assertIn("window.compactMode ? window.width", timed)
        self.assertIn('text: "Appearance"', timed)
        self.assertIn('"Light"', timed)
        self.assertIn('"Dark"', timed)
        self.assertIn("customSidePanelComponent:", removal)
        self.assertIn("viewerFrameSource:", removal)
        self.assertIn("window.compactMode ? 196 : 236", removal)
        self.assertIn("RotoSlider", removal)
        self.assertIn("RotoComboBox", removal)

    def test_shared_primitives_remain_safe_on_windows_and_fallback_renderers(self):
        theme = (UI / "RotoTheme.qml").read_text(encoding="utf-8")
        glass = (UI / "GlassPanel.qml").read_text(encoding="utf-8")
        status = (UI / "StatusPill.qml").read_text(encoding="utf-8")

        self.assertIn('fontFamily: "Segoe UI"', theme)
        self.assertIn('displayFontFamily: "Segoe UI"', theme)
        self.assertIn('monoFontFamily: "Consolas"', theme)
        self.assertNotIn("layer.enabled", glass)
        self.assertNotIn("layer.effect", glass)
        self.assertIn("maximumLabelWidth", status)
        self.assertIn("property bool compact", status)
        self.assertIn("compact ? 28", status)
        self.assertIn("Text.ElideRight", status)


if __name__ == "__main__":
    unittest.main()
