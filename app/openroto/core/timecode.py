from __future__ import annotations

from fractions import Fraction


def parse_rate(value: str | float | int) -> Fraction:
    if isinstance(value, float | int):
        if abs(float(value) - 29.97) < 0.001:
            return Fraction(30000, 1001)
        if abs(float(value) - 59.94) < 0.001:
            return Fraction(60000, 1001)
        return Fraction(str(value))
    normalized = value.strip().replace(",", ".")
    if "/" in normalized:
        return Fraction(normalized)
    return parse_rate(float(normalized))


def timecode_to_frame(timecode: str, rate: str | float | int) -> int:
    """Convert a non-drop-frame Resolve timecode to an absolute frame number."""
    parts = timecode.replace(";", ":").split(":")
    if len(parts) != 4:
        raise ValueError(f"Invalid timecode: {timecode}")
    hours, minutes, seconds, frames = (int(part) for part in parts)
    fps = parse_rate(rate)
    nominal = round(float(fps))
    if not 0 <= minutes < 60 or not 0 <= seconds < 60 or not 0 <= frames < nominal:
        raise ValueError(f"Invalid timecode: {timecode}")
    return ((hours * 60 + minutes) * 60 + seconds) * nominal + frames


def frame_to_timecode(frame: int, rate: str | float | int) -> str:
    if frame < 0:
        raise ValueError("frame must be non-negative")
    nominal = round(float(parse_rate(rate)))
    seconds, frames = divmod(frame, nominal)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
