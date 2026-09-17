from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openroto.core.models import ModelPreset
from openroto.inference.catalog import MODEL_CATALOG
from openroto.inference.model_cache import (
    download_model,
    hub_cache_root,
    model_home,
    model_is_installed,
    remove_model,
    repository_cache_dir,
)


class ModelCacheTests(unittest.TestCase):
    def test_model_cache_follows_hf_home(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"HF_HOME": directory}, clear=False):
                self.assertEqual(Path(directory), model_home())
                self.assertEqual(Path(directory) / "hub", hub_cache_root())
                self.assertEqual(
                    Path(directory) / "hub" / "models--facebook--sam2.1-hiera-tiny",
                    repository_cache_dir("facebook/sam2.1-hiera-tiny"),
                )

    def test_installed_model_requires_a_nonempty_snapshot(self):
        spec = MODEL_CATALOG[ModelPreset.FAST]
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"HF_HOME": directory}, clear=False):
                self.assertFalse(model_is_installed(spec))
                snapshot = repository_cache_dir(spec.repository) / "snapshots" / "abc123"
                snapshot.mkdir(parents=True)
                self.assertFalse(model_is_installed(spec))
                (snapshot / "config.json").write_text("{}", encoding="utf-8")
                self.assertTrue(model_is_installed(spec))

    def test_download_model_uses_the_same_cache_that_status_checks(self):
        spec = MODEL_CATALOG[ModelPreset.FAST]
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {"HF_HOME": directory, "HF_HUB_CACHE": str(Path(directory) / "hub")},
                clear=False,
            ):
                def fake_snapshot_download(*, repo_id: str, cache_dir: str) -> str:
                    self.assertEqual(spec.repository, repo_id)
                    self.assertEqual(hub_cache_root(), Path(cache_dir))
                    snapshot = repository_cache_dir(repo_id) / "snapshots" / "downloaded"
                    snapshot.mkdir(parents=True)
                    (snapshot / "model.pt").write_bytes(b"weights")
                    return str(snapshot)

                with patch("huggingface_hub.snapshot_download", fake_snapshot_download):
                    download_model(spec)
                self.assertTrue(model_is_installed(spec))

    def test_remove_model_only_removes_the_requested_repository(self):
        fast = MODEL_CATALOG[ModelPreset.FAST]
        balanced = MODEL_CATALOG[ModelPreset.BALANCED]
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"HF_HOME": directory}, clear=False):
                for spec in (fast, balanced):
                    snapshot = repository_cache_dir(spec.repository) / "snapshots" / "abc123"
                    snapshot.mkdir(parents=True)
                    (snapshot / "weights.bin").write_bytes(b"weights")
                remove_model(fast)
                self.assertFalse(repository_cache_dir(fast.repository).exists())
                self.assertTrue(repository_cache_dir(balanced.repository).exists())


if __name__ == "__main__":
    unittest.main()
