from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from openroto.inference.removal_backends import (
    BACKENDS,
    ExternalRemovalBackend,
    backend_is_installed,
    backend_rows,
)


class RemovalBackendTests(unittest.TestCase):
    def test_catalog_keeps_permissive_learned_backends_separate_from_temporal(self):
        self.assertEqual("OpenRoto", BACKENDS["temporal"].license)
        self.assertEqual("MIT", BACKENDS["fgt"].license)
        self.assertEqual("Apache-2.0", BACKENDS["svor"].license)
        self.assertIn("24 GB", BACKENDS["svor"].vram)
        rows = backend_rows("temporal")
        self.assertEqual(["temporal", "fgt", "svor"], [row["id"] for row in rows])
        self.assertTrue(rows[0]["installed"])

    def test_external_backend_json_contract_composites_only_inside_mask(self):
        old_local = os.environ.get("LOCALAPPDATA")
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                os.environ["LOCALAPPDATA"] = str(root)
                frames = root / "frames"
                masks = root / "masks"
                output = root / "output"
                frames.mkdir()
                masks.mkdir()

                first = np.zeros((6, 6, 3), dtype=np.uint8)
                first[:] = (10, 20, 30)
                second = np.zeros((6, 6, 3), dtype=np.uint8)
                second[:] = (40, 50, 60)
                Image.fromarray(first).save(frames / "00000000.png")
                Image.fromarray(second).save(frames / "00000001.png")
                mask = np.zeros((6, 6), dtype=np.uint8)
                mask[2:4, 2:4] = 255
                Image.fromarray(mask).save(masks / "mask_00000000.png")
                Image.fromarray(mask).save(masks / "mask_00000001.png")

                backend = root / "OpenRoto" / "RemovalBackends" / "fgt"
                source = backend / "source"
                source.mkdir(parents=True)
                runner = backend / "fake_runner.py"
                runner.write_text(
                    """
import argparse, json
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser(); p.add_argument('--request'); p.add_argument('--result'); a=p.parse_args()
r=json.loads(Path(a.request).read_text(encoding='utf-8')); out=Path(r['output_dir']); out.mkdir(parents=True, exist_ok=True)
for i, path in enumerate(r['frame_paths']):
    with Image.open(path) as im:
        Image.new('RGB', im.size, (200, 210, 220)).save(out / f'backend_{i:08d}.png')
Path(a.result).write_text(json.dumps({'elapsed_ms': 25.0, 'peak_vram_mb': 512.0}), encoding='utf-8')
""".strip()
                    + "\n",
                    encoding="utf-8",
                )
                (backend / "backend.json").write_text(
                    json.dumps(
                        {
                            "id": "fgt",
                            "python": sys.executable,
                            "runner": str(runner),
                            "source": str(source),
                        }
                    ),
                    encoding="utf-8",
                )

                self.assertTrue(backend_is_installed("fgt"))
                result = ExternalRemovalBackend("fgt").remove(
                    frames,
                    masks,
                    [0, 1],
                    output,
                    width=6,
                    height=6,
                    fps=24.0,
                    padding=0,
                    feather=0,
                    vram_gb=8.0,
                )
                self.assertEqual(25.0, result.elapsed_ms)
                self.assertEqual(512.0, result.peak_vram_mb)
                with Image.open(output / "removed_00000000.png") as image:
                    pixels = np.asarray(image.convert("RGB"))
                self.assertTupleEqual((10, 20, 30), tuple(pixels[0, 0]))
                self.assertTupleEqual((200, 210, 220), tuple(pixels[2, 2]))
        finally:
            if old_local is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = old_local

    def test_setup_scripts_use_isolated_runtimes_and_official_sources(self):
        fgt = (ROOT / "app" / "openroto" / "removal_backends" / "setup_fgt.ps1").read_text(
            encoding="utf-8"
        )
        svor = (ROOT / "app" / "openroto" / "removal_backends" / "setup_svor.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("uv venv", fgt)
        self.assertIn("--python 3.8", fgt)
        self.assertIn("hitachinsk/FGT", fgt)
        self.assertIn("princeton", "princeton-vl/RAFT")
        self.assertIn("uv venv", svor)
        self.assertIn("--python 3.10", svor)
        self.assertIn("xiaomi-research/svor", svor)
        self.assertIn("Wan-AI/Wan2.1-VACE-1.3B", svor)
        self.assertIn("HigherHu/SVOR", svor)

    def test_advanced_controller_benchmarks_same_17_frame_window(self):
        controller = (
            ROOT / "app" / "openroto" / "ui" / "removal_backend_controller.py"
        ).read_text(encoding="utf-8")
        self.assertIn("sample_count = min(17, frame_count)", controller)
        self.assertIn("for spec in BACKENDS.values()", controller)
        self.assertIn("ExternalRemovalBackend(spec.id)", controller)
        self.assertIn("peak_vram", controller)
        self.assertIn("openBenchmarkFolder", controller)


if __name__ == "__main__":
    unittest.main()
