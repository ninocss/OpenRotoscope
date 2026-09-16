from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image


def _peak_vram_for_pid(pid: int) -> float | None:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    peak: float | None = None
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            if int(parts[0]) == pid:
                value = float(parts[1])
                peak = value if peak is None else max(peak, value)
        except ValueError:
            continue
    return peak


def _padded_video_length(frame_count: int) -> int:
    if frame_count <= 1:
        return 1
    return int(math.ceil((frame_count - 1) / 4.0) * 4 + 1)


def _sample_size(vram_gb: float, width: int, height: int) -> str:
    if vram_gb >= 32:
        max_h, max_w = 720, 1280
    else:
        max_h, max_w = 480, 832
    if height > width:
        max_h, max_w = max_w, max_h
    return f"{min(height, max_h)},{min(width, max_w)}"


def _write_input_video(frame_paths: list[Path], destination: Path, fps: float) -> None:
    frames = []
    for path in frame_paths:
        with Image.open(path) as image:
            frames.append(np.asarray(image.convert("RGB"), dtype=np.uint8))
    imageio.mimwrite(destination, frames, fps=max(1.0, fps), codec="libx264", quality=9)


def _write_mask_video(mask_paths: list[Path], destination: Path, fps: float) -> None:
    frames = []
    for path in mask_paths:
        with Image.open(path) as image:
            mask = np.asarray(image.convert("L"), dtype=np.uint8)
        frames.append(np.repeat(mask[..., None], 3, axis=2))
    imageio.mimwrite(destination, frames, fps=max(1.0, fps), codec="libx264", quality=10)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()

    request = json.loads(args.request.read_text(encoding="utf-8"))
    source = Path(request["source_dir"]).resolve()
    frame_paths = [Path(value) for value in request["frame_paths"]]
    mask_paths = [Path(value) for value in request["mask_paths"]]
    output = Path(request["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if len(frame_paths) != len(mask_paths) or not frame_paths:
        raise RuntimeError("SVOR sidecar received mismatched or empty frame/mask input")

    predictor = source / "predict_SVOR.py"
    if not predictor.is_file():
        raise FileNotFoundError(f"SVOR predictor was not found at {predictor}")

    work = output.parent / ".svor-work"
    shutil.rmtree(work, ignore_errors=True)
    results = work / "results"
    work.mkdir(parents=True)
    results.mkdir(parents=True)
    input_video = work / "openroto_input.mp4"
    input_mask = work / "openroto_mask.mp4"
    fps = float(request.get("fps", 24.0))
    _write_input_video(frame_paths, input_video, fps)
    _write_mask_video(mask_paths, input_mask, fps)

    vram_gb = float(request.get("vram_gb", 0.0))
    memory_mode = "model_full_load" if vram_gb >= 32 else "model_cpu_offload"
    sample_size = _sample_size(vram_gb, int(request["width"]), int(request["height"]))
    video_length = _padded_video_length(len(frame_paths))

    command = [
        os.fspath(Path(os.sys.executable)),
        os.fspath(predictor),
        "--input_video",
        os.fspath(input_video),
        "--input_mask_video",
        os.fspath(input_mask),
        "--video_length",
        str(video_length),
        "--fps",
        str(max(1, int(round(fps)))),
        "--sample_size",
        sample_size,
        "--num_inference_steps",
        "20",
        "--gpu_memory_mode",
        memory_mode,
        "--save_dir",
        os.fspath(results),
    ]

    started = time.perf_counter_ns()
    process = subprocess.Popen(command, cwd=os.fspath(source))
    peak_vram: float | None = None
    while process.poll() is None:
        sample = _peak_vram_for_pid(process.pid)
        if sample is not None:
            peak_vram = sample if peak_vram is None else max(peak_vram, sample)
        time.sleep(0.20)
    if process.returncode != 0:
        raise RuntimeError(f"SVOR upstream process exited with code {process.returncode}")

    result_video = results / "openroto_input.mp4"
    if not result_video.is_file():
        candidates = sorted(results.glob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError("SVOR completed without writing an output video")
        result_video = candidates[0]

    reader = imageio.get_reader(result_video)
    try:
        decoded = 0
        for index, frame in enumerate(reader):
            if index >= len(frame_paths):
                break
            Image.fromarray(frame).convert("RGB").save(
                output / f"backend_{index:08d}.png", compress_level=1
            )
            decoded += 1
    finally:
        reader.close()
    if decoded != len(frame_paths):
        raise RuntimeError(f"SVOR returned {decoded} frames; expected {len(frame_paths)}")

    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
    args.result.write_text(
        json.dumps(
            {
                "backend": "svor",
                "elapsed_ms": elapsed_ms,
                "peak_vram_mb": peak_vram,
                "frame_count": len(frame_paths),
                "sample_size": sample_size,
                "gpu_memory_mode": memory_mode,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
