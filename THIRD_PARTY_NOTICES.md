# Third-party notices

OpenRoto itself is distributed under the MIT License. Runtime dependencies, optional backends and model weights retain their own licenses and terms.

## Bundled/runtime dependencies

- **CPython 3.10.11** — Copyright Python Software Foundation and contributors. OpenRoto's Windows build bundles the official unmodified CPython embeddable distribution for the Resolve bridge. CPython is distributed under the Python Software Foundation License Version 2 and its bundled notices.
- **PyTorch / torchvision** — Copyright PyTorch contributors. BSD-style license. The OpenRoto application may install CUDA-enabled wheels during the Windows build and may download separate backend-specific PyTorch environments on demand.
- **PySide6 / Qt for Python** — Copyright The Qt Company. Available under LGPLv3/GPLv3 or a commercial Qt license. OpenRoto uses the unmodified libraries dynamically.
- **Pillow** — Pillow license.
- **NumPy** — BSD-3-Clause license.
- **platformdirs** — MIT license.
- **huggingface_hub** — Apache License 2.0.

The release packaging should reproduce the license files and notices required by the redistributed packages beside the installed application.

## Downloaded AI models

- **Segment Anything 2 / SAM 2.1** — Copyright Meta Platforms, Inc. Code and checkpoints are provided under the upstream Apache License 2.0 terms. Checkpoints are downloaded from Meta's published model repositories and are not committed to this source repository.

## Optional object-removal backends

These backends are integrations only. OpenRoto does **not** vendor their source repositories, Python environments or model weights in its installer or source tree. On Windows, OpenRoto can download and prepare them on demand under the user's local OpenRoto data directory. Users can instead provide their own environments through the documented `OPENROTO_*` overrides.

- **FGT / FGT++** — upstream repository: <https://github.com/hitachinsk/FGT>. The upstream repository is MIT licensed. OpenRoto's managed setup also downloads the published FGT/LAFC checkpoints from the upstream `hitachinsk/FGT` Hugging Face repository. The upstream project does not officially support Windows; OpenRoto's managed environment is a compatibility integration rather than an upstream Windows distribution.
- **SVOR** — upstream repository: <https://github.com/xiaomi-research/svor>. The upstream repository is Apache-2.0 licensed. OpenRoto's managed setup downloads the published SVOR LoRA weights from `HigherHu/SVOR` and the `Wan-AI/Wan2.1-VACE-1.3B` base model. Those model components keep their own upstream licenses and terms and are not redistributed by OpenRoto.

OpenRoto intentionally does not bundle ProPainter or E2FGVI as default removal backends because their published terms restrict use to non-commercial scenarios.

## Trademarks and affiliation

OpenRoto is an independent project. It is not affiliated with, endorsed by or sponsored by Blackmagic Design, DaVinci Resolve, Meta, Hitachi Research, Xiaomi Research or the maintainers of the optional model projects.

Third-party names are used only to identify compatible software or models.
