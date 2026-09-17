from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.inference.sam2_engine import Sam2Engine
from openroto.ui.controller import ApplicationController


class EditorUxContractTests(unittest.TestCase):
    def test_frame_navigation_never_renders_preview_synchronously(self):
        source = inspect.getsource(ApplicationController.setFrame)
        self.assertNotIn("_refresh_preview", source)
        self.assertIn("_schedule_preview_refresh", source)
        self.assertIn("_queue_viewer_prefetch", source)

    def test_tracking_publishes_frames_progressively(self):
        source = inspect.getsource(Sam2Engine.track)
        self.assertIn("frame_ready", source)
        self.assertIn("frame_ready(frame_index)", source)

    def test_viewer_retains_frames_and_has_playback_prefetch(self):
        qml = (ROOT / "app/openroto/ui/PolishedMain.qml").read_text(encoding="utf-8")
        self.assertGreaterEqual(qml.count("retainWhileLoading: true"), 2)
        self.assertIn("id: playbackTimer", qml)
        self.assertIn("frameUrlAt(window.appController.currentFrame + 1)", qml)
        self.assertNotIn("blurEnabled: true", qml)
        self.assertIn('sequence: "Space"', qml)

    def test_preview_processing_is_debounced_and_backgrounded(self):
        source = inspect.getsource(ApplicationController)
        self.assertIn("setInterval(120)", source)
        self.assertIn("_preview_executor.submit", source)
        self.assertIn("_preview_versions", source)
        self.assertIn("_viewer_executor.submit", source)


if __name__ == "__main__":
    unittest.main()
