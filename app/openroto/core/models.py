from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


class PointLabel(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class ModelPreset(StrEnum):
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"


class TrackingDirection(StrEnum):
    BOTH = "both"
    FORWARD = "forward"
    BACKWARD = "backward"


class SessionState(StrEnum):
    CREATED = "created"
    EXPORTING = "exporting"
    READY = "ready"
    LOADING_MODEL = "loading_model"
    SEGMENTING = "segmenting"
    TRACKING = "tracking"
    RENDERING = "rendering"
    APPLYING = "applying"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PointPrompt:
    frame: int
    x: float
    y: float
    label: PointLabel

    def __post_init__(self) -> None:
        if self.frame < 0:
            raise ValueError("frame must be non-negative")
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise ValueError("point coordinates must be normalized to 0..1")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PointPrompt:
        return cls(
            frame=int(value["frame"]),
            x=float(value["x"]),
            y=float(value["y"]),
            label=PointLabel(value["label"]),
        )


@dataclass(slots=True)
class MatteSettings:
    invert: bool = False
    expand_contract: int = 0
    feather: float = 0.0
    overlay_opacity: float = 0.48

    def __post_init__(self) -> None:
        if not -32 <= self.expand_contract <= 32:
            raise ValueError("expand_contract must be between -32 and 32 pixels")
        if not 0.0 <= self.feather <= 64.0:
            raise ValueError("feather must be between 0 and 64 pixels")
        if not 0.0 <= self.overlay_opacity <= 1.0:
            raise ValueError("overlay_opacity must be normalized")


@dataclass(slots=True)
class SessionManifest:
    session_id: str
    token: str
    bridge_host: str
    bridge_port: int
    project_id: str
    project_name: str
    timeline_id: str
    timeline_name: str
    clip_id: str
    clip_name: str
    track_index: int
    record_start: int
    record_end: int
    source_start: int
    source_end: int
    fps: float
    width: int
    height: int
    frames_dir: str
    matte_dir: str
    snapshot_path: str
    state: SessionState = SessionState.CREATED
    frame_pattern: str = "%08d.png"
    matte_pattern: str = "matte_%08d.png"
    schema_version: int = SCHEMA_VERSION
    linked_item_ids: list[str] = field(default_factory=list)

    @property
    def frame_count(self) -> int:
        return max(0, self.record_end - self.record_start)

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported session schema {self.schema_version}; expected {SCHEMA_VERSION}"
            )
        if len(self.session_id) < 8 or len(self.token) < 32:
            raise ValueError("Invalid session credentials")
        if self.bridge_host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("The Resolve bridge must use a loopback address")
        if not 1 <= self.bridge_port <= 65535:
            raise ValueError("Invalid Resolve bridge port")
        if self.track_index < 1:
            raise ValueError("track_index must be one-based")
        if self.record_end <= self.record_start:
            raise ValueError("Clip range is empty")
        if self.fps <= 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("Invalid media properties")
        paths = [Path(value) for value in (self.frames_dir, self.matte_dir, self.snapshot_path)]
        for path in paths:
            if not path.is_absolute():
                raise ValueError("Session paths must be absolute")
        frames, matte, snapshot = paths
        if frames.name != "frames" or matte.name != "matte":
            raise ValueError("Session frame and matte folders have invalid names")
        if frames.parent != matte.parent or snapshot.parent != matte.parent:
            raise ValueError("Session paths must share one session folder")

    def to_dict(self, *, include_token: bool = True) -> dict[str, Any]:
        result = asdict(self)
        result["state"] = self.state.value
        if not include_token:
            result.pop("token", None)
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SessionManifest:
        data = dict(value)
        data["state"] = SessionState(data.get("state", SessionState.CREATED))
        manifest = cls(**data)
        manifest.validate()
        return manifest


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    state: SessionState
    progress: float
    message: str
    detail: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.progress <= 1.0:
            raise ValueError("progress must be normalized")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "progress",
            "state": self.state.value,
            "progress": self.progress,
            "message": self.message,
            "detail": self.detail,
        }
