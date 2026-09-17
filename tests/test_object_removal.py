from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.inference.removal import RemovalEngine, RemovalSettings
from openroto.inference.removal_backends import backend_status
from openroto.inference.removal_comp import fusion_removal_comp_text
from openroto.inference.removal_runners.svor_runner import _svor_video_length


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

    def test_external_backend_is_composited_only_inside_mask(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frames = root / "frames"
            masks = root / "masks"
            output = root / "removed"
            frames.mkdir()
            masks.mkdir()
            source = np.zeros((8, 8, 3), dtype=np.uint8)
            source[:] = (10, 20, 30)
            Image.fromarray(source).save(frames / "00000000.png")
            mask = np.zeros((8, 8), dtype=np.uint8)
            mask[3:5, 3:5] = 255
            Image.fromarray(mask).save(masks / "mask_00000000.png")

            def fake_backend(_backend_id, **kwargs):
                destination = Path(kwargs["output_dir"])
                destination.mkdir(parents=True, exist_ok=True)
                generated = np.zeros((8, 8, 3), dtype=np.uint8)
                generated[:] = (240, 240, 240)
                Image.fromarray(generated).save(destination / "removed_00000000.png")
                return destination

            engine = RemovalEngine(frames, masks)
            with mock.patch("openroto.inference.removal.run_external_backend", fake_backend):
                engine.remove(
                    1,
                    output,
                    RemovalSettings(padding=0, feather=0, backend="fgt"),
                    fps=24.0,
                )

            with Image.open(output / "removed_00000000.png") as image:
                result = np.asarray(image.convert("RGB"))
            self.assertTupleEqual((10, 20, 30), tuple(result[0, 0]))
            self.assertTupleEqual((240, 240, 240), tuple(result[3, 3]))

    def test_builtin_backend_is_always_available(self):
        status = backend_status("temporal")
        self.assertTrue(status["available"])
        self.assertTrue(status["ready"])
        self.assertEqual("Built in", status["status"])

    def test_managed_fgt_can_be_downloaded_on_windows(self):
        with tempfile.TemporaryDirectory() as temporary:
            environment = {
                "LOCALAPPDATA": temporary,
                "OPENROTO_FGT_ROOT": "",
                "OPENROTO_FGT_PYTHON": "",
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                status = backend_status("fgt")
        self.assertFalse(status["ready"])
        self.assertEqual(os.name == "nt", status["installable"])
        if os.name == "nt":
            self.assertEqual("Download on first use", status["status"])

    def test_managed_fgt_ready_state_checks_runtime_dependencies_and_weights(self):
        with tempfile.TemporaryDirectory() as temporary:
            environment = {
                "LOCALAPPDATA": temporary,
                "OPENROTO_FGT_ROOT": "",
                "OPENROTO_FGT_PYTHON": "",
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                base = Path(temporary) / "OpenRoto" / "RemovalBackends" / "fgt"
                root = base / "repo"
                required = [
                    root / "tool" / "video_inpainting.py",
                    root / "FGT" / "checkpoint" / "fgt.pth.tar",
                    root / "FGT" / "checkpoint" / "FGT_config.yaml",
                    root / "LAFC" / "checkpoint" / "lafc.pth.tar",
                    root / "LAFC" / "checkpoint" / "LAFC_config.yaml",
                    root / "LAFC" / "flowCheckPoint" / "raft-things.pth",
                    base / "python" / ("python.exe" if os.name == "nt" else "bin/python"),
                ]
                for path in required:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"test")
                (base / ".openroto-dependencies").write_text(
                    "openroto-fgt-win-v1\n", encoding="utf-8"
                )
                status = backend_status("fgt")
        self.assertTrue(status["ready"])
        self.assertTrue(status["available"])
        self.assertEqual("Ready", status["status"])

    def test_svor_rounds_clip_length_up_to_wan_temporal_grid(self):
        self.assertEqual(1, _svor_video_length(1))
        self.assertEqual(5, _svor_video_length(2))
        self.assertEqual(5, _svor_video_length(5))
        self.assertEqual(9, _svor_video_length(6))
        self.assertEqual(81, _svor_video_length(81))
        self.assertEqual(85, _svor_video_length(82))

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
        self.assertIn("fgt_runner.py", build)
        self.assertIn("svor_runner.py", build)
        self.assertIn('text: "Remove"', qml)
        self.assertIn('model: ["Temporal Fill", "FGT++", "SVOR"]', qml)
        self.assertIn("backendInfo.available", qml)
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
        self.assertIn("fps=self._app.manifest.fps", controller)
        self.assertIn('status.get("installable")', controller)

    def test_fgt_runner_uses_upstream_tool_working_directory(self):
        runner = (
            ROOT / "app" / "openroto" / "inference" / "removal_runners" / "fgt_runner.py"
        ).read_text(encoding="utf-8")
        self.assertIn('tool_dir = root / "tool"', runner)
        self.assertIn("cwd=str(tool_dir)", runner)

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
