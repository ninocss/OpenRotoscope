"""OpenRoto application package."""

from __future__ import annotations

import os
from pathlib import Path

__version__ = "0.1.0"


# Configure Hugging Face before SAM2/huggingface_hub is imported.  SAM2's
# ``from_pretrained`` helper does not expose a cache_dir argument, so giving the
# process an OpenRoto-owned HF_HOME keeps the Settings downloader and SAM2
# runtime on the same cache.  Explicit user HF_HOME/HF_HUB_CACHE overrides are
# always respected.
if "HF_HOME" not in os.environ and "HF_HUB_CACHE" not in os.environ:
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    os.environ["HF_HOME"] = str(local / "OpenRoto" / "Models")
