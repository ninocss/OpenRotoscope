from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _write_result(path: Path, **payload) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _frame_path(root: Path, index: int) -> Path:
    for candidate in (
        root / f"{index:08d}.png",
        root / f"frame_{index:08d}.png",
        root / f"frame_{index + 1:08d}.png",
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"OpenRoto frame {index + 1} is missing")


def _mask_path(root: Path, index: int) -> Path:
    candidate = root / f"mask_{index:08d}.png"
    if not candidate.is_file():
        raise FileNotFoundError(f"OpenRoto mask {index + 1} is missing")
    return candidate


def _encode_video(frames_dir: Path, masks_dir: Path, work: Path, count: int, fps: float) -> tuple[Path, Path, tuple[int, int]]:
    import imageio.v2 as imageio
    import numpy as np
    from PIL import Image

    first = Image.open(_frame_path(frames_dir, 0)).convert("RGB")
    width, height = first.size
    first.close()
    input_video = work / "input.mp4"
    mask_video = work / "mask.mp4"
    video_writer = imageio.get_writer(str(input_video), fps=fps, codec="libx264", quality=9, macro_block_size=1)
    mask_writer = imageio.get_writer(str(mask_video), fps=fps, codec="libx264", quality=10, macro_block_size=1)
    try:
        for index in range(count):
            with Image.open(_frame_path(frames_dir, index)) as image:
                rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
            with Image.open(_mask_path(masks_dir, index)) as image:
                mask = np.asarray(image.convert("L"), dtype=np.uint8)
            mask_rgb = np.repeat((mask > 0)[..., None].astype(np.uint8) * 255, 3, axis=2)
            video_writer.append_data(rgb)
            mask_writer.append_data(mask_rgb)
    finally:
        video_writer.close()
        mask_writer.close()
    return input_video, mask_video, (width, height)


def _find_result_video(root: Path) -> Path:
    videos = [path for path in root.rglob("*.mp4") if path.name not in {"input.mp4", "mask.mp4"}]
    if not videos:
        raise RuntimeError("SVOR did not produce an output video")
    return max(videos, key=lambda path: path.stat().st_mtime)


def _decode_video(video: Path, output_dir: Path, expected: int, size: tuple[int, int]) -> None:
    import imageio.v2 as imageio
    from PIL import Image

    output_dir.mkdir(parents=True, exist_ok=True)
    reader = imageio.get_reader(str(video))
    count = 0
    try:
        for index, frame in enumerate(reader):
            if index >= expected:
                break
            image = Image.fromarray(frame).convert("RGB")
            if image.size != size:
                image = image.resize(size, Image.Resampling.LANCZOS)
            image.save(output_dir / f"removed_{index:08d}.png", compress_level=1)
            count += 1
    finally:
        reader.close()
    if count != expected:
        raise RuntimeError(f"SVOR returned {count} frames, expected {expected}")


def _sample_size(width: int, height: int) -> tuple[int, int]:
    override = os.environ.get("OPENROTO_SVOR_SAMPLE_SIZE", "").strip()
    if override:
        values = override.lower().replace("x", ",").split(",")
        if len(values) == 2:
            return int(values[0]), int(values[1])
    max_width, max_height = 1280, 720
    scale = min(1.0, max_width / width, max_height / height)
    sample_w = max(64, int(round(width * scale / 16)) * 16)
    sample_h = max(64, int(round(height * scale / 16)) * 16)
    return sample_h, sample_w


def _svor_video_length(frame_count: int) -> int:
    if frame_count <= 1:
        return 1
    # SVOR's Wan VAE uses a temporal compression ratio of four and floors the
    # requested length to 4n+1. Round up here so the generated video always
    # contains at least all OpenRoto frames; padded tail frames are discarded.
    return ((frame_count - 1 + 3) // 4) * 4 + 1


def run(job_path: Path) -> None:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    root = Path(job["backend_root"])
    frames = Path(job["frames_dir"])
    masks = Path(job["masks_dir"])
    output = Path(job["output_dir"])
    expected = int(job["frame_count"])
    fps = float(job.get("fps", 24.0))
    result_json = Path(job["result_json"])

    script = root / "predict_SVOR.py"
    if not script.is_file():
        raise RuntimeError(f"SVOR runner not found: {script}")

    work = output.parent / ".svor-work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    input_video, mask_video, original_size = _encode_video(frames, masks, work, expected, fps)
    sample_h, sample_w = _sample_size(*original_size)
    save_dir = work / "result"
    save_dir.mkdir(parents=True, exist_ok=True)
    inference_length = _svor_video_length(expected)

    command = [
        sys.executable,
        str(script),
        "--input_video",
        str(input_video),
        "--input_mask_video",
        str(mask_video),
        "--save_dir",
        str(save_dir),
        "--sample_size",
        f"{sample_h},{sample_w}",
        "--video_length",
        str(inference_length),
        "--fps",
        str(max(1, int(round(fps)))),
    ]
    memory_mode = os.environ.get("OPENROTO_SVOR_GPU_MEMORY_MODE", "model_cpu_offload").strip()
    if memory_mode:
        command.extend(["--gpu_memory_mode", memory_mode])
    steps = os.environ.get("OPENROTO_SVOR_STEPS", "").strip()
    if steps:
        command.extend(["--num_inference_steps", steps])

    process = subprocess.run(command, cwd=str(root), check=False)
    if process.returncode != 0:
        raise RuntimeError(f"SVOR inference exited with code {process.returncode}")
    result_video = _find_result_video(save_dir)
    _decode_video(result_video, output, expected, original_size)
    _write_result(
        result_json,
        ok=True,
        backend="svor",
        video=str(result_video),
        sample_size=[sample_h, sample_w],
        requested_video_length=inference_length,
        gpu_memory_mode=memory_mode,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    args = parser.parse_args()
    job = json.loads(args.job.read_text(encoding="utf-8"))
    result_json = Path(job["result_json"])
    try:
        run(args.job)
        return 0
    except Exception as error:
        _write_result(result_json, ok=False, error=f"{type(error).__name__}: {error}")
        print(f"OpenRoto SVOR runner failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
