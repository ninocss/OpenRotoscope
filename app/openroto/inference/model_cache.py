from __future__ import annotations

import os
import shutil
from pathlib import Path

from openroto.inference.catalog import ModelSpec


def model_home() -> Path:
    configured = os.environ.get("HF_HOME")
    if configured:
        return Path(configured)
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local / "OpenRoto" / "Models"


def hub_cache_root() -> Path:
    configured = os.environ.get("HF_HUB_CACHE")
    if configured:
        return Path(configured)
    return model_home() / "hub"


def repository_cache_dir(repository: str) -> Path:
    return hub_cache_root() / ("models--" + repository.replace("/", "--"))


def model_is_installed(spec: ModelSpec) -> bool:
    snapshots = repository_cache_dir(spec.repository) / "snapshots"
    if not snapshots.is_dir():
        return False
    for snapshot in snapshots.iterdir():
        if snapshot.is_dir() and any(snapshot.iterdir()):
            return True
    return False


def download_model(spec: ModelSpec) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as error:
        raise RuntimeError("The Hugging Face model manager is not installed.") from error

    model_home().mkdir(parents=True, exist_ok=True)
    cache_dir = hub_cache_root()
    cache_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=spec.repository, cache_dir=str(cache_dir))
    if not model_is_installed(spec):
        raise RuntimeError(f"{spec.display_name} finished downloading but its cache is incomplete.")


def remove_model(spec: ModelSpec) -> None:
    cache_dir = repository_cache_dir(spec.repository)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
