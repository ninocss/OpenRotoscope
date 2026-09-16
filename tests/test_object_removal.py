from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.inference.removal import RemovalEngine, RemovalSettings
from openroto.inference.removal_comp import fusion_removal_comp_text


class ObjectRemovalTests(unittest.TestCase):
    def test_temporal_fill_uses_background_from_visible_neighbor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frames = root / "frames"
            masks = root / "masks"
            output = root / "removed"
            frames.mkdir()
            masks.mkdir()

            first = np.zeros((8, 8, 3), dtype=np.uint8)
            first[:] = (20, 30, 40)
            first[3:5, 3:5] = (240, 20, 20)
            second = np.zeros((8, 8, 3), dtype=np.uint8)
            second[:] = (80, 120, 160)
            Image.fromarray(first).save(frames / "00000000.png")
            Image.fromarray(second).save(frames / "00000001.png")

            mask0 = np.zeros((8, 8), dtype=np.uint8)
            mask0[3:5, 3:5] = 255
            Image.fromarray(mask0).save(masks / "mask_00000000.png")
            Image.fromarray(np.zeros((8, 8), dtype=np.uint8)).save(
                masks / "mask_00000001.png"
            )

            engine = RemovalEngine(frames, masks)
            engine.remove(
                2,
                output,
                RemovalSettings(padding=0, feather=0, temporal_radius=2),
            )

            with Image.open(output / "removed_00000000.png") as image:
                result = np.asarray(image.convert("RGB"))
            self.assertTupleEqual((80, 120, 160), tuple(result[3, 3]))
            self.assertTupleEqual((20, 30, 40), tuple(result[0, 0]))

    def test_removal_comp_uses_rgb_sequence_as_media_out(self):
        text = fusion_removal_comp_text(Path(r"C:\OpenRoto\removed_00000000.png"), 12)
        self.assertIn("OpenRotoRemoval = Loader", text)
        self.assertIn('SourceOp = "OpenRotoRemoval"', text)
        self.assertIn("Length = 12", text)

    def test_object_removal_ui_is_loaded_and_packaged(self):
        main = (ROOT / "app" / "openroto" / "main.py").read_text(encoding="utf-8")
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        qml = (ROOT / "app" / "openroto" / "ui" / "ObjectRemovalMain.qml").read_text(
            encoding="utf-8"
        )
        self.assertIn('"ObjectRemovalMain.qml"', main)
        self.assertIn("ObjectRemovalMain.qml", build)
        self.assertIn('text: "Remove"', qml)
        self.assertIn("Track, Remove & Apply", qml)
        self.assertIn("currentRemovalUrl", qml)
        self.assertIn('text: window.appController.status === "Waiting for Resolve"', qml)
        self.assertIn("window.removalController.cancel()", qml)

    def test_removal_forces_full_both_direction_tracking_before_rendering(self):
        controller = (
            ROOT / "app" / "openroto" / "ui" / "removal_controller.py"
        ).read_text(encoding="utf-8")
        self.assertIn('if self._app.trackingDirection != "both":', controller)
        self.assertIn('self._app.setTrackingDirection("both")', controller)
        self.assertIn("if self._app.trackingDirty or self._missing_masks():", controller)
        self.assertIn("Object tracking is incomplete at frame", controller)

    def test_free_removal_validates_sequence_before_signalling_resolve(self):
        controller = (
            ROOT / "app" / "openroto" / "ui" / "removal_controller.py"
        ).read_text(encoding="utf-8")
        self.assertIn("self._validate_output()", controller)
        self.assertIn('0.98, "Waiting for Resolve", "Applying the removed-object result"', controller)
        self.assertIn('app._send_control("apply")', controller)
        self.assertLess(
            controller.index("self._validate_output()", controller.index("def _apply_free")),
            controller.index('app._send_control("apply")'),
        )


if __name__ == "__main__":
    unittest.main()
