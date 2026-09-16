from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import SessionManifest


def read_manifest(path: str | Path) -> SessionManifest:
    manifest_path = Path(path).expanduser().resolve(strict=True)
    with manifest_path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("Session manifest must contain a JSON object")
    return SessionManifest.from_dict(value)


def atomic_write_json(path: str | Path, value: dict[str, Any]) -> None:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_manifest(path: str | Path, manifest: SessionManifest) -> None:
    manifest.validate()
    atomic_write_json(path, manifest.to_dict())

