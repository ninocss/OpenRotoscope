from __future__ import annotations

import contextlib
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "resolve"))

import numpy as np
import OpenRoto as resolve_bridge
from openroto.core.ipc import BridgeClient
from openroto.core.manifest import read_manifest, write_manifest
from openroto.core.models import (
    MatteSettings,
    ModelPreset,
    PointLabel,
    PointPrompt,
    SessionManifest,
    SessionState,
    TrackingDirection,
)
from openroto.core.point_store import PointStore
from openroto.core.timecode import parse_rate
from openroto.inference.matte import process_mask, save_raw_mask
from openroto.inference.sam2_engine import InferenceUnavailableError, Sam2Engine
from openroto.ui.controller import ApplicationController
from PIL import Image
from PySide6.QtCore import QCoreApplication


def make_manifest(root: Path) -> SessionManifest:
    return SessionManifest(
        session_id="a" * 32,
        token="b" * 40,
        bridge_host="127.0.0.1",
        bridge_port=41414,
        project_id="project",
        project_name="Project",
        timeline_id="timeline",
        timeline_name="Timeline",
        clip_id="clip",
        clip_name="Clip",
        track_index=1,
        record_start=100,
        record_end=124,
        source_start=0,
        source_end=24,
        fps=24,
        width=1920,
        height=1080,
        frames_dir=str((root / "frames").resolve()),
        matte_dir=str((root / "matte").resolve()),
        snapshot_path=str((root / "backup.drt").resolve()),
        state=SessionState.READY,
    )


class ManifestTests(unittest.TestCase):
    def test_manifest_round_trip_and_frame_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "session.json"
            original = make_manifest(root)
            write_manifest(path, original)
            loaded = read_manifest(path)
            self.assertEqual(24, loaded.frame_count)
            self.assertEqual(ModelPreset.BALANCED.value, "balanced")
            self.assertEqual(original.to_dict(), loaded.to_dict())

    def test_manifest_rejects_non_loopback_bridge(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = make_manifest(Path(directory))
            manifest.bridge_host = "192.168.1.10"
            with self.assertRaisesRegex(ValueError, "loopback"):
                manifest.validate()

    def test_manifest_rejects_paths_from_different_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = make_manifest(root)
            manifest.matte_dir = str((root / "other" / "matte").resolve())
            with self.assertRaisesRegex(ValueError, "share one session folder"):
                manifest.validate()


class PointStoreTests(unittest.TestCase):
    def test_undo_redo_and_frame_grouping(self):
        store = PointStore()
        positive = PointPrompt(0, 0.25, 0.5, PointLabel.POSITIVE)
        negative = PointPrompt(3, 0.75, 0.5, PointLabel.NEGATIVE)
        store.add(positive)
        store.add(negative)
        self.assertEqual((negative,), store.for_frame(3))
        self.assertEqual(negative, store.undo())
        self.assertEqual(negative, store.redo())
        self.assertEqual({0, 3}, set(store.by_frame()))

    def test_point_coordinates_are_normalized(self):
        with self.assertRaisesRegex(ValueError, "normalized"):
            PointPrompt(0, 2, 0.5, PointLabel.POSITIVE)


class BridgeClientTests(unittest.TestCase):
    def test_unexpected_disconnect_is_reported(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        disconnected = threading.Event()
        reasons = []

        def close_after_hello():
            connection, _address = server.accept()
            with connection:
                connection.makefile("rb").readline()
            server.close()

        threading.Thread(target=close_after_hello, daemon=True).start()
        client = BridgeClient(
            "127.0.0.1",
            server.getsockname()[1],
            "token",
            on_disconnect=lambda reason: (reasons.append(reason), disconnected.set()),
        )
        client.connect()
        self.assertTrue(disconnected.wait(2), "disconnect callback was not invoked")
        self.assertIn("Resolve", reasons[0])


class TimecodeTests(unittest.TestCase):
    def test_broadcast_rates_are_exact(self):
        self.assertEqual((30000, 1001), parse_rate(29.97).as_integer_ratio())
        self.assertEqual((60000, 1001), parse_rate("59.94").as_integer_ratio())


class ResolveBridgeTests(unittest.TestCase):
    def test_resolve_instance_reuses_internal_app_connection_for_free(self):
        expected = object()

        class InternalApp:
            @staticmethod
            def GetResolve():
                return expected

        with patch.dict(
            resolve_bridge.__dict__, {"resolve": None, "app": InternalApp()}, clear=False
        ):
            self.assertIs(expected, resolve_bridge._resolve_instance())

    def test_fusion_graph_uses_mask_as_merge_effect_mask(self):
        text = resolve_bridge._fusion_comp_text(
            Path(r"C:\OpenRoto\matte_00000000.png"), 24, 1920, 1080
        )
        self.assertIn('EffectMask = Input { SourceOp = "OpenRotoMask"', text)
        self.assertIn("GlobalRange = { 0, 23 }", text)
        self.assertIn("Width = Input { Value = 1920 }", text)

    def test_safe_name_removes_reserved_characters(self):
        self.assertEqual("clip_bad_name", resolve_bridge._safe_name("clip<bad:name"))

    def test_png_renderer_uses_format_extension_for_resolve_api(self):
        class Project:
            def GetRenderFormats(self):
                return {"QuickTime": "mov", "PNG": "png"}

            def GetRenderCodecs(self, extension):
                return {"RGB 8-bit": "RGB8"} if extension == "png" else {}

        format_id, codec_id, extension = resolve_bridge._pick_image_sequence_codec(Project())
        self.assertEqual(("png", "RGB8", "png"), (format_id, codec_id, extension))

    def test_incomplete_matte_is_rejected_before_timeline_mutation(self):
        class Timeline:
            compound_calls = 0

            def GetUniqueId(self):
                return "timeline"

            def CreateCompoundClip(self, *_args):
                self.compound_calls += 1
                return None

        class Project:
            def __init__(self, timeline):
                self.timeline = timeline

            def GetCurrentTimeline(self):
                return self.timeline

        class Target:
            def GetUniqueId(self):
                return "clip"

            def GetStart(self):
                return 0

            def GetEnd(self):
                return 2

        with tempfile.TemporaryDirectory() as directory:
            timeline = Timeline()
            manifest = {
                "timeline_id": "timeline",
                "clip_id": "clip",
                "record_start": 0,
                "record_end": 2,
                "matte_dir": directory,
                "width": 8,
                "height": 8,
                "clip_name": "Clip",
            }
            with self.assertRaisesRegex(resolve_bridge.OpenRotoError, "incomplete"):
                resolve_bridge._apply_matte(
                    Project(timeline), timeline, Target(), manifest, Path(directory)
                )
            self.assertEqual(0, timeline.compound_calls)


class MatteTests(unittest.TestCase):
    def test_processed_matte_uses_mask_as_alpha(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = np.zeros((9, 9), dtype=np.uint8)
            raw[4, 4] = 1
            source = save_raw_mask(raw, root / "raw.png")
            output = process_mask(
                source,
                root / "matte.png",
                MatteSettings(expand_contract=1, feather=0, invert=False),
            )
            with Image.open(output) as image:
                self.assertEqual("RGBA", image.mode)
                alpha = np.asarray(image.getchannel("A"))
            self.assertEqual(255, int(alpha[4, 4]))
            self.assertGreater(int(np.count_nonzero(alpha)), 1)


class TrackingRegressionTests(unittest.TestCase):
    def test_direction_fill_overwrites_stale_masks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = root / "frames"
            masks = root / "masks"
            frames.mkdir()
            masks.mkdir()
            Image.new("L", (8, 8), 255).save(masks / "mask_00000001.png")
            Image.new("L", (8, 8), 255).save(masks / "mask_00000000.png")
            engine = Sam2Engine(frames, masks)
            engine._fill_untracked(0, 1, 1)
            with Image.open(masks / "mask_00000000.png") as image:
                self.assertEqual(0, int(np.asarray(image).max()))

    def test_tracking_resets_state_and_rejects_incomplete_output(self):
        class Predictor:
            reset_calls = 0

            def reset_state(self, _state):
                self.reset_calls += 1

            def propagate_in_video(self, *_args, **_kwargs):
                return iter(())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = root / "frames"
            masks = root / "masks"
            frames.mkdir()
            masks.mkdir()
            for index in range(3):
                Image.new("RGB", (8, 8), "black").save(frames / f"{index:08d}.png")
            engine = Sam2Engine(frames, masks)
            predictor = Predictor()
            engine._preset = ModelPreset.BALANCED
            engine._predictor = predictor
            engine._state = object()
            engine._torch = object()
            engine._inference_context = contextlib.nullcontext

            def segment(frame, *_args, **_kwargs):
                return save_raw_mask(
                    np.ones((8, 8), dtype=np.uint8), masks / f"mask_{frame:08d}.png"
                )

            engine.segment_frame = segment
            prompts = {1: (PointPrompt(1, 0.5, 0.5, PointLabel.POSITIVE),)}
            with self.assertRaisesRegex(InferenceUnavailableError, "frame 1"):
                engine.track(
                    prompts,
                    3,
                    ModelPreset.BALANCED,
                    TrackingDirection.BOTH,
                )
            self.assertEqual(1, predictor.reset_calls)


class ControllerRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QCoreApplication.instance() or QCoreApplication([])

    def _controller(self, root: Path, frame_count: int = 4):
        manifest = make_manifest(root)
        manifest.record_start = 0
        manifest.record_end = frame_count
        manifest.width = 8
        manifest.height = 8
        Path(manifest.frames_dir).mkdir(parents=True)
        Path(manifest.matte_dir).mkdir(parents=True)

        class FakeBridge:
            connected = True

            def __init__(self):
                self.messages = []

            def connect(self):
                return None

            def send(self, message_type, **payload):
                self.messages.append((message_type, payload))

            def close(self):
                self.connected = False

        bridge = FakeBridge()
        with patch("openroto.ui.controller.BridgeClient", return_value=bridge):
            controller = ApplicationController(manifest)
        return controller, bridge

    def test_undo_navigates_to_the_affected_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            controller, _bridge = self._controller(Path(directory))
            controller._points.add(PointPrompt(0, 0.2, 0.2, PointLabel.POSITIVE))
            controller._points.add(PointPrompt(3, 0.4, 0.4, PointLabel.POSITIVE))
            controller.undo()
            self.assertEqual(3, controller.currentFrame)
            self.assertEqual(1, controller.promptCount)
            controller.closeSession()
            controller.deleteLater()
            self.qt_app.processEvents()

    def test_render_retracks_when_prompts_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            controller, bridge = self._controller(Path(directory), frame_count=2)
            controller._points.add(PointPrompt(0, 0.2, 0.2, PointLabel.POSITIVE))
            for index in range(2):
                save_raw_mask(
                    np.ones((8, 8), dtype=np.uint8), controller._raw_path(index)
                )
            calls = []

            def mark_tracked():
                calls.append(True)
                controller._tracking_dirty = False

            controller._track = mark_tracked
            controller._render_and_apply()
            self.assertEqual([True], calls)
            self.assertEqual("apply", bridge.messages[0][0])
            controller.closeSession()
            controller.deleteLater()
            self.qt_app.processEvents()

    def test_negative_first_point_waits_for_positive_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            controller, _bridge = self._controller(Path(directory))
            controller.addPoint(0.25, 0.5, False)
            self.assertFalse(controller.busy)
            self.assertEqual("Add a positive point", controller.status)
            self.assertEqual(1, controller.promptCount)
            controller.closeSession()
            controller.deleteLater()
            self.qt_app.processEvents()

    def test_close_during_work_cancels_before_closing(self):
        with tempfile.TemporaryDirectory() as directory:
            controller, _bridge = self._controller(Path(directory))
            closed = []
            controller.closeRequested.connect(lambda: closed.append(True))
            controller._busy = True
            controller._status = "Tracking subject"
            self.assertFalse(controller.requestClose())
            self.assertTrue(controller._cancel.is_set())
            controller._finish_operation("Cancelled", "Tracking was cancelled")
            self.qt_app.processEvents()
            self.assertEqual([True], closed)
            controller.closeSession()
            controller.deleteLater()
            self.qt_app.processEvents()



if __name__ == "__main__":
    unittest.main()
