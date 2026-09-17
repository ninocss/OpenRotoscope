from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _write_result(path: Path, **payload) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _find_result_video(root: Path) -> Path:
    videos = sorted(root.rglob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not videos:
        raise RuntimeError("FGT did not produce a result.mp4 file")
    return videos[0]


def _decode_video(video: Path, output_dir: Path, expected: int) -> None:
    import imageio.v2 as imageio
    from PIL import Image

    output_dir.mkdir(parents=True, exist_ok=True)
    reader = imageio.get_reader(str(video))
    count = 0
    try:
        for index, frame in enumerate(reader):
            if index >= expected:
                break
            Image.fromarray(frame).convert("RGB").save(
                output_dir / f"removed_{index:08d}.png", compress_level=1
            )
            count += 1
    finally:
        reader.close()
    if count != expected:
        raise RuntimeError(f"FGT returned {count} frames, expected {expected}")


def run(job_path: Path) -> None:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    root = Path(job["backend_root"])
    frames = Path(job["frames_dir"])
    masks = Path(job["masks_dir"])
    output = Path(job["output_dir"])
    expected = int(job["frame_count"])
    result_json = Path(job["result_json"])

    script = root / "tool" / "video_inpainting.py"
    tool_dir = root / "tool"
    if not script.is_file():
        raise RuntimeError(f"FGT runner not found: {script}")
    if not frames.is_dir() or not masks.is_dir():
        raise RuntimeError("OpenRoto frame or mask directory is missing")

    work = output.parent / ".fgt-work"
    shutil.rmtree(work, ignore_errors=True)
    outroot = work / "result"
    outroot.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        str(script),
        "--path",
        str(frames),
        "--path_mask",
        str(masks),
        "--outroot",
        str(outroot),
    ]
    # FGT resolves configs and checkpoints relative to tool/. Running from the
    # repository root makes its default ../FGT and ../LAFC paths point outside
    # the checkout.
    process = subprocess.run(command, cwd=str(tool_dir), check=False)
    if process.returncode != 0:
        raise RuntimeError(f"FGT inference exited with code {process.returncode}")

    result_video = _find_result_video(outroot)
    _decode_video(result_video, output, expected)
    _write_result(result_json, ok=True, backend="fgt", video=str(result_video))


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
        print(f"OpenRoto FGT runner failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
