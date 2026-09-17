# OpenRoto object-removal backends

OpenRoto keeps video inpainting separate from the packaged SAM2/Qt process. This avoids dependency conflicts and lets each optional backend use its own Python/Torch stack.

## Built-in: Temporal Fill

No setup is required. OpenRoto reconstructs masked pixels from nearby frames where the background is visible, then uses a spatial fallback for pixels that remain hidden. This is the fastest option and is intended for previews and simple shots.

## Automatic installation

On Windows, select `FGT++` or `SVOR` in the Remove workflow and click the install button. OpenRoto stores managed backends under:

```text
%LOCALAPPDATA%\OpenRoto\RemovalBackends\<backend>\
```

Each managed backend gets its own Python runtime, source checkout and model weights. The main OpenRoto/Resolve Python environment is not modified.

The install button performs these steps:

1. downloads the official upstream source archive;
2. downloads an isolated CPython runtime;
3. installs the backend's Python/Torch dependencies;
4. downloads the official pretrained weights;
5. marks the backend `Ready` only when its source, runtime and required weights are all present.

A failed or interrupted install remains unavailable and can be retried. OpenRoto surfaces the setup command error in the Remove panel.

## FGT++

Upstream: https://github.com/hitachinsk/FGT

Weights: https://huggingface.co/hitachinsk/FGT

License: MIT.

The upstream project documents Ubuntu 20.04, Python 3.6.8 and PyTorch 1.10.1. Its pretrained repository contains the FGT and LAFC checkpoints. OpenRoto's managed Windows installation uses an isolated Python 3.9 runtime with PyTorch 1.10.1 and copies the official Hugging Face checkpoints into the directory layout expected by `tool/video_inpainting.py`.

FGT is legacy research code and upstream does not officially support Windows. The managed installer keeps its compatibility packages isolated so they cannot downgrade OpenRoto itself. If the upstream code is incompatible with a particular GPU/driver, the backend runner reports the underlying error instead of changing the main application environment.

## SVOR

Upstream: https://github.com/xiaomi-research/svor

SVOR LoRA weights: https://huggingface.co/HigherHu/SVOR

Base model: https://huggingface.co/Wan-AI/Wan2.1-VACE-1.3B

License: Apache-2.0 for the SVOR repository. Review the upstream model licenses before redistribution.

The managed installer uses Python 3.10 and PyTorch 2.7.0, then installs the upstream `requirements.txt`. It downloads both SVOR LoRA checkpoints and the complete `Wan2.1-VACE-1.3B` model into the repository's `models/` directory.

SVOR requires a large download and substantial GPU memory. Upstream reports about 33 GB of GPU memory in its default mode and about 24 GB with `model_cpu_offload`.

Optional tuning variables:

```text
OPENROTO_SVOR_GPU_MEMORY_MODE=model_cpu_offload
OPENROTO_SVOR_SAMPLE_SIZE=720,1280
OPENROTO_SVOR_STEPS=20
```

If `OPENROTO_SVOR_SAMPLE_SIZE` is not set, the OpenRoto runner preserves the source aspect ratio and caps inference at roughly 1280x720. The generated result is resized back to the Resolve frame dimensions before mask-aware compositing.

## Manual/external environments

Advanced users can still point OpenRoto at environments they manage themselves:

```text
OPENROTO_FGT_ROOT=<path to FGT repository>
OPENROTO_FGT_PYTHON=<path to its Python executable>

OPENROTO_SVOR_ROOT=<path to SVOR repository>
OPENROTO_SVOR_PYTHON=<path to its Python executable>
```

When either override is active for a backend, OpenRoto treats it as external and does not install into or delete that environment. The external repository must already contain the required model weights.

Automatic managed installation is currently Windows-only. On other platforms use the upstream setup plus these environment variables.

## Backend safety

FGT++ and SVOR return complete RGB frames, but OpenRoto does not trust them to preserve the rest of the frame. After inference, OpenRoto composites the generated image through the padded/feathered SAM2 removal mask. Pixels outside the removal area therefore remain the original Resolve export.

## Benchmark

Use the same tracked OpenRoto frame and mask sequence for every backend:

```powershell
python .\scripts\benchmark-removal.py `
  --frames-dir "$env:LOCALAPPDATA\OpenRoto\Sessions\<session>\frames" `
  --masks-dir "$env:LOCALAPPDATA\OpenRoto\Sessions\<session>\matte\raw" `
  --frame-count 120 `
  --fps 24
```

The benchmark writes one output sequence and contact sheet per available backend plus `benchmark.json` containing:

- total elapsed milliseconds
- effective frames per second
- approximate peak VRAM delta sampled with `nvidia-smi`
- OpenRoto removal timing values
- backend license/VRAM metadata

Peak VRAM is an approximation because `nvidia-smi` observes total GPU memory use, including other applications. Visual quality is intentionally not reduced to a synthetic score; compare the generated sequences/contact sheets on the actual shot.
