from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from PIL import Image, ImageDraw

from openroto.inference.removal import RemovalEngine, RemovalSettings
from openroto.inference.removal_backends import REMOVAL_BACKENDS, backend_status


def gpu_memory_used_mb() -> int | None:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode != 0:
            return None
        values = [int(line.strip()) for line in result.stdout.splitlines() if line.strip()]
        return sum(values) if values else None
    except Exception:
        return None


class VramMonitor:
    def __init__(self) -> None:
        self.baseline = gpu_memory_used_mb()
        self.peak = self.baseline
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="OpenRotoVramMonitor", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> int | None:
        self._stop.set()
        self._thread.join(timeout=2)
        if self.baseline is None or self.peak is None:
            return None
        return max(0, self.peak - self.baseline)

    def _run(self) -> None:
        while not self._stop.wait(0.20):
            value = gpu_memory_used_mb()
            if value is not None and (self.peak is None or value > self.peak):
                self.peak = value


def contact_sheet(output_dir: Path, frame_count: int, destination: Path) -> None:
    if frame_count <= 0:
        return
    sample_count = min(6, frame_count)
    indices = sorted({round(i * (frame_count - 1) / max(1, sample_count - 1)) for i in range(sample_count)})
    thumbs: list[tuple[int, Image.Image]] = []
    for index in indices:
        path = output_dir / f"removed_{index:08d}.png"
        if not path.is_file():
            continue
        with Image.open(path) as image:
            thumb = image.convert("RGB")
            thumb.thumbnail((320, 180), Image.Resampling.LANCZOS)
            thumbs.append((index, thumb.copy()))
    if not thumbs:
        return
    width = max(image.width for _, image in thumbs)
    height = max(image.height for _, image in thumbs) + 24
    sheet = Image.new("RGB", (width * len(thumbs), height), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for column, (index, image) in enumerate(thumbs):
        x = column * width + (width - image.width) // 2
        sheet.paste(image, (x, 0))
        draw.text((column * width + 8, height - 20), f"Frame {index + 1}", fill=(230, 230, 230))
    sheet.save(destination, compress_level=1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark OpenRoto object-removal backends")
    parser.add_argument("--frames-dir", type=Path, required=True)
    parser.add_argument("--masks-dir", type=Path, required=True)
    parser.add_argument("--frame-count", type=int, required=True)
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--backends", default="temporal,fgt,svor")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmark-removal")
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--feather", type=float, default=2.0)
    parser.add_argument("--temporal-radius", type=int, default=12)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    requested = [value.strip() for value in args.backends.split(",") if value.strip()]
    results: list[dict[str, object]] = []

    for backend_id in requested:
        if backend_id not in REMOVAL_BACKENDS:
            print(f"Skipping unknown backend: {backend_id}")
            continue
        status = backend_status(backend_id)
        row: dict[str, object] = {
            "backend": backend_id,
            "name": status["display_name"],
            "license": status["license"],
            "quality_class": status["quality"],
            "speed_class": status["speed"],
            "vram_guidance": status["vram"],
            "available": bool(status["available"]),
        }
        if not status["available"]:
            row["status"] = "skipped"
            row["reason"] = status["status"]
            results.append(row)
            print(f"{status['display_name']}: skipped ({status['status']})")
            continue

        output = args.output_dir / backend_id
        engine = RemovalEngine(args.frames_dir, args.masks_dir)
        settings = RemovalSettings(
            padding=args.padding,
            feather=args.feather,
            temporal_radius=args.temporal_radius,
            backend=backend_id,
        )
        timings: dict[str, float] = {}
        engine.set_timing_callback(lambda key, ms, values=timings: values.__setitem__(key, ms))
        monitor = VramMonitor()
        monitor.start()
        started = time.perf_counter_ns()
        try:
            engine.remove(
                args.frame_count,
                output,
                settings,
                progress=lambda fraction, message: print(
                    f"[{status['display_name']}] {fraction * 100:5.1f}% {message}",
                    flush=True,
                ),
                fps=args.fps,
            )
            elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
            peak_delta = monitor.stop()
            row.update(
                {
                    "status": "ok",
                    "elapsed_ms": round(elapsed_ms, 2),
                    "effective_fps": round(args.frame_count / max(elapsed_ms / 1000.0, 1e-9), 3),
                    "peak_vram_delta_mb_approx": peak_delta,
                    "timings_ms": {key: round(value, 2) for key, value in timings.items()},
                    "output_dir": str(output.resolve()),
                }
            )
            sheet = args.output_dir / f"{backend_id}-contact-sheet.png"
            contact_sheet(output, args.frame_count, sheet)
            row["contact_sheet"] = str(sheet.resolve())
            print(
                f"{status['display_name']}: {elapsed_ms / 1000.0:.2f}s, "
                f"{row['effective_fps']} fps, peak VRAM Δ {peak_delta if peak_delta is not None else 'n/a'} MB"
            )
        except Exception as error:
            peak_delta = monitor.stop()
            row.update(
                {
                    "status": "failed",
                    "error": f"{type(error).__name__}: {error}",
                    "peak_vram_delta_mb_approx": peak_delta,
                }
            )
            print(f"{status['display_name']}: FAILED: {error}")
        results.append(row)

    payload = {
        "frames_dir": str(args.frames_dir.resolve()),
        "masks_dir": str(args.masks_dir.resolve()),
        "frame_count": args.frame_count,
        "fps": args.fps,
        "note": "Peak VRAM is an approximate total-GPU delta sampled with nvidia-smi; visual quality must be judged from the generated sequences/contact sheets.",
        "results": results,
    }
    result_path = args.output_dir / "benchmark.json"
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Benchmark written to {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
