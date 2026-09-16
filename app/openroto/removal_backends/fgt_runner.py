from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import imageio.v2 as imageio
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


def _link_or_copy(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _target_size(width: int, height: int, max_dimension: int = 432) -> tuple[int, int]:
    scale = min(1.0, max_dimension / max(width, height))
    target_w = max(64, int(round(width * scale / 8.0)) * 8)
    target_h = max(64, int(round(height * scale / 8.0)) * 8)
    return target_w, target_h


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
        raise RuntimeError("FGT sidecar received mismatched or empty frame/mask input")
    tool = source / "tool" / "video_inpainting.py"
    if not tool.is_file():
        raise FileNotFoundError(f"FGT tool was not found at {tool}")

    work = output.parent / ".fgt-work"
    shutil.rmtree(work, ignore_errors=True)
    frames = work / "frames"
    masks = work / "masks"
    result_dir = work / "result"
    frames.mkdir(parents=True)
    masks.mkdir(parents=True)
    result_dir.mkdir(parents=True)

    for index, (frame, mask) in enumerate(zip(frame_paths, mask_paths)):
        if not frame.is_file() or not mask.is_file():
            raise FileNotFoundError(f"FGT input frame/mask {index + 1} is missing")
        _link_or_copy(frame, frames / f"{index:05d}{frame.suffix.lower()}")
        _link_or_copy(mask, masks / f"{index:05d}.png")

    target_w, target_h = _target_size(int(request["width"]), int(request["height"]))
    command = [
        os.fspath(Path(os.sys.executable)),
        os.fspath(tool),
        "--path",
        os.fspath(frames),
        "--path_mask",
        os.fspath(masks),
        "--outroot",
        os.fspath(result_dir),
        "--raft_model",
        os.fspath(source / "LAFC" / "flowCheckPoint" / "raft-things.pth"),
        "--lafc_ckpts",
        os.fspath(source / "LAFC" / "checkpoint"),
        "--fgt_ckpts",
        os.fspath(source / "FGT" / "checkpoint"),
        "--imgH",
        str(target_h),
        "--imgW",
        str(target_w),
        "--mixed_precision",
    ]

    started = time.perf_counter_ns()
    process = subprocess.Popen(command, cwd=os.fspath(source / "tool"))
    peak_vram: float | None = None
    while process.poll() is None:
        sample = _peak_vram_for_pid(process.pid)
        if sample is not None:
            peak_vram = sample if peak_vram is None else max(peak_vram, sample)
        time.sleep(0.15)
    if process.returncode != 0:
        raise RuntimeError(f"FGT upstream process exited with code {process.returncode}")

    video = result_dir / "result.mp4"
    if not video.is_file():
        raise FileNotFoundError("FGT completed without writing result.mp4")

    reader = imageio.get_reader(video)
    try:
        decoded = 0
        for index, frame in enumerate(reader):
            if index >= len(frame_paths):
                break
            image = Image.fromarray(frame).convert("RGB")
            image.save(output / f"backend_{index:08d}.png", compress_level=1)
            decoded += 1
    finally:
        reader.close()
    if decoded != len(frame_paths):
        raise RuntimeError(f"FGT returned {decoded} frames; expected {len(frame_paths)}")

    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
    args.result.write_text(
        json.dumps(
            {
                "backend": "fgt",
                "elapsed_ms": elapsed_ms,
                "peak_vram_mb": peak_vram,
                "frame_count": len(frame_paths),
                "inference_size": [target_h, target_w],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
