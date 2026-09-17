from pathlib import Path

path = Path(__file__).resolve().parents[1] / "app/openroto/inference/sam2_engine.py"
text = path.read_text(encoding="utf-8")
wrong_load = '''        progress: ProgressCallback | None = None,\n        *,\n        frame_ready: FrameReadyCallback | None = None,\n    ) -> None:\n        \"\"\"Load model weights only.\n'''
fixed_load = '''        progress: ProgressCallback | None = None,\n    ) -> None:\n        \"\"\"Load model weights only.\n'''
if wrong_load not in text:
    raise RuntimeError("Expected staged load() callback patch was not found")
text = text.replace(wrong_load, fixed_load, 1)
track_old = '''        direction: TrackingDirection,\n        progress: ProgressCallback | None = None,\n    ) -> None:\n'''
track_new = '''        direction: TrackingDirection,\n        progress: ProgressCallback | None = None,\n        *,\n        frame_ready: FrameReadyCallback | None = None,\n    ) -> None:\n'''
if track_old not in text:
    raise RuntimeError("Sam2Engine.track signature anchor was not found")
text = text.replace(track_old, track_new, 1)
path.write_text(text, encoding="utf-8")
print("Corrected progressive tracking callback signature")
