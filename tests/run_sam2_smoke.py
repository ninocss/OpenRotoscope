"""Optional real-model CUDA smoke test for a local SAM2 checkout/checkpoint."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import torch
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.core.models import ModelPreset, PointLabel, PointPrompt, TrackingDirection
from openroto.inference.sam2_engine import Sam2Engine


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sam2-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--config", default="configs/sam2.1/sam2.1_hiera_b+.yaml")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    sys.path.insert(0, str(arguments.sam2_root.resolve()))
    from sam2.build_sam import build_sam2_video_predictor

    if not torch.cuda.is_available():
        raise RuntimeError("This smoke test requires CUDA")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        frames = root / "frames"
        raw = root / "raw"
        frames.mkdir()
        for index, offset in enumerate((0, 22, 44)):
            image = Image.new("RGB", (512, 320), "#d9e1ec")
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((150 + offset, 70, 290 + offset, 260), 34, fill="#365fa8")
            image.save(frames / f"{index:08d}.png")
        predictor = build_sam2_video_predictor(
            arguments.config,
            str(arguments.checkpoint.resolve()),
            device="cuda",
        )
        engine = Sam2Engine(frames, raw)
        engine._predictor = predictor
        engine._torch = torch
        engine._preset = ModelPreset.BALANCED
        engine._state = predictor.init_state(
            str(frames), offload_video_to_cpu=True, async_loading_frames=True
        )
        prompt = PointPrompt(0, 220 / 512, 160 / 320, PointLabel.POSITIVE)
        engine.track(
            {0: (prompt,)},
            frame_count=3,
            preset=ModelPreset.BALANCED,
            direction=TrackingDirection.BOTH,
        )
        outputs = sorted(raw.glob("mask_*.png"))
        if len(outputs) != 3:
            raise AssertionError(f"Expected 3 masks, found {len(outputs)}")
        if any(Image.open(path).getbbox() is None for path in outputs):
            raise AssertionError("SAM2 produced an empty mask")
    print("SAM2 CUDA smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

