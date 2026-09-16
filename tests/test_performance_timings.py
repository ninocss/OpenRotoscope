from __future__ import annotations

import contextlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image
from PySide6.QtCore import QCoreApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.core.models import (
    ModelPreset,
    PointLabel,
    PointPrompt,
    SessionManifest,
    SessionState,
)
from openroto.inference.sam2_engine import Sam2Engine
from openroto.ui.controller import ApplicationController


class FakeBridge:
    connected = True

    def connect(self):
        return None

    def send(self, *_args, **_kwargs):
        return None

    def close(self):
        self.connected = False


def make_manifest(root: Path) -> SessionManifest:
    frames = root / "frames"
    matte = root / "matte"
    frames.mkdir()
    matte.mkdir()
    Image.new("RGB", (16, 12), "black").save(frames / "00000000.png")
    return SessionManifest(
        session_id="timing-session-0001",
        token="timing-token-00000000000000000000000000000000",
        bridge_host="127.0.0.1",
        bridge_port=41414,
        project_id="project",
        project_name="Project",
        timeline_id="timeline",
        timeline_name="Timeline",
        clip_id="clip",
        clip_name="Timing clip",
        track_index=1,
        record_start=0,
        record_end=1,
        source_start=0,
        source_end=1,
        fps=24,
        width=16,
        height=12,
        frames_dir=str(frames.resolve()),
        matte_dir=str(matte.resolve()),
        snapshot_path=str((root / "backup.drt").resolve()),
        state=SessionState.READY,
    )


class TimingInstrumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QCoreApplication.instance() or QCoreApplication([])

    def test_controller_exposes_all_requested_timing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = make_manifest(Path(directory))
            with patch("openroto.ui.controller.BridgeClient", return_value=FakeBridge()):
                controller = ApplicationController(manifest)
            rows = {row["key"]: row for row in controller.performanceTimings}
            self.assertEqual(
                {
                    "model_load",
                    "image_embedding",
                    "predict",
                    "preview",
                    "init_state",
                    "propagate",
                },
                set(rows),
            )
            self.assertTrue(all(row["value"] == "—" for row in rows.values()))

            controller._set_timing_from_worker("predict", 12.345)
            rows = {row["key"]: row for row in controller.performanceTimings}
            self.assertTrue(rows["predict"]["measured"])
            self.assertEqual("12.3 ms", rows["predict"]["value"])
            controller.closeSession()

    def test_image_selection_reports_embedding_and_predict_timings(self):
        class FakeImagePredictor:
            def set_image(self, _image):
                return None

            def predict(self, **_kwargs):
                return np.ones((1, 12, 16), dtype=np.uint8), None, None

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = root / "frames"
            masks = root / "masks"
            frames.mkdir()
            Image.new("RGB", (16, 12), "black").save(frames / "00000000.png")
            engine = Sam2Engine(frames, masks)
            engine._preset = ModelPreset.BALANCED
            engine._predictor = object()
            engine._image_predictor = FakeImagePredictor()
            engine._torch = object()
            engine._inference_context = contextlib.nullcontext
            measured: dict[str, float] = {}
            engine.set_timing_callback(lambda key, value: measured.__setitem__(key, value))

            engine.segment_frame(
                0,
                (PointPrompt(0, 0.5, 0.5, PointLabel.POSITIVE),),
                ModelPreset.BALANCED,
            )

            self.assertIn("image_embedding", measured)
            self.assertIn("predict", measured)
            self.assertGreaterEqual(measured["image_embedding"], 0.0)
            self.assertGreaterEqual(measured["predict"], 0.0)
            self.assertTrue((masks / "mask_00000000.png").is_file())


if __name__ == "__main__":
    unittest.main()
