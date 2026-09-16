from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from PIL import Image

from openroto.inference.sam2_engine import InferenceUnavailableError, Sam2Engine


class Sam2FrameStagingTests(unittest.TestCase):
    def test_png_sequence_is_staged_as_numeric_jpegs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = root / "frames"
            masks = root / "masks"
            frames.mkdir()
            for index in range(3):
                Image.new("RGBA", (12, 8), (index * 50, 20, 30, 255)).save(
                    frames / f"{index:08d}.png"
                )

            engine = Sam2Engine(frames, masks)
            staged, frame_count = engine._prepare_predictor_frames()

            self.assertEqual(3, frame_count)
            self.assertEqual(frames / ".sam2-jpeg", staged)
            self.assertEqual(
                ["00000000.jpg", "00000001.jpg", "00000002.jpg"],
                sorted(path.name for path in staged.glob("*.jpg")),
            )
            with Image.open(staged / "00000000.jpg") as image:
                self.assertEqual("RGB", image.mode)
                self.assertEqual((12, 8), image.size)

    def test_staging_reuses_current_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = root / "frames"
            masks = root / "masks"
            frames.mkdir()
            Image.new("RGB", (8, 8), "black").save(frames / "00000000.png")

            engine = Sam2Engine(frames, masks)
            staged, _ = engine._prepare_predictor_frames()
            cached = staged / "00000000.jpg"
            first_mtime = cached.stat().st_mtime_ns
            staged_again, _ = engine._prepare_predictor_frames()

            self.assertEqual(staged, staged_again)
            self.assertEqual(first_mtime, cached.stat().st_mtime_ns)

    def test_staging_rejects_empty_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = root / "frames"
            masks = root / "masks"
            frames.mkdir()
            engine = Sam2Engine(frames, masks)

            with self.assertRaisesRegex(InferenceUnavailableError, "did not export"):
                engine._prepare_predictor_frames()


if __name__ == "__main__":
    unittest.main()
