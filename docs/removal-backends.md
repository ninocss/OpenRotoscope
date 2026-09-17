# OpenRoto object-removal backends

OpenRoto keeps video inpainting separate from the packaged SAM2/Qt process. FGT++ and SVOR run in isolated sidecar Python environments so their PyTorch/dependency versions do not alter OpenRoto or DaVinci Resolve.

## Built-in: Temporal Fill

No setup is required. OpenRoto reconstructs masked pixels from nearby frames where the background is visible, then uses a spatial fallback for pixels that remain hidden. This is the fastest option and is intended for previews and simple shots.

## Automatic installation

FGT++ and SVOR are installed on first use. Select the backend and start **Preview removal** or **Remove & Apply**. OpenRoto then:

1. downloads the pinned upstream source into `%LOCALAPPDATA%\OpenRoto\RemovalBackends\<backend>\repo`;
2. creates an isolated Python 3.10 sidecar environment;
3. installs that backend's inference dependencies;
4. downloads the required model weights from Hugging Face; and
5. starts inference only after the complete installation has been moved into its final location.

On Windows the installer downloads the official Python 3.10.11 embeddable runtime, bootstraps a virtual environment, and does not require a system Python installation. Failed or cancelled installs stay outside the final backend directory, so an incomplete download is not reported as Ready.

The first installation can be large, especially SVOR because it also downloads `Wan-AI/Wan2.1-VACE-1.3B`.

## FGT++

Upstream: https://github.com/hitachinsk/FGT

License: MIT.

OpenRoto installs the upstream source in an isolated Python 3.10 environment with a compatibility set based around PyTorch 1.13.1 and NumPy 1.23.5. It downloads the official pretrained FGT/LAFC weights from `hitachinsk/FGT` on Hugging Face and lays them out in the checkpoint directories expected by the upstream object-removal script.

The upstream project originally documented Ubuntu 20.04, Python 3.6.8 and PyTorch 1.10.1. OpenRoto's sidecar exists specifically to avoid importing that legacy dependency stack into the main app.

## SVOR

Upstream: https://github.com/xiaomi-research/svor

License: Apache-2.0 for the SVOR repository. The managed setup also downloads model files from `HigherHu/SVOR` and `Wan-AI/Wan2.1-VACE-1.3B`; their license terms apply to those weights.

OpenRoto installs PyTorch 2.7.0 / torchvision 0.22.0 in the isolated sidecar, then installs the inference-only dependencies required by `predict_SVOR.py`. It downloads:

- `HigherHu/SVOR/remove_model_stage1.safetensors`
- `HigherHu/SVOR/remove_model_stage2.safetensors`
- `Wan-AI/Wan2.1-VACE-1.3B`

The upstream project reports roughly 33 GB of GPU memory in its default mode and roughly 24 GB with `model_cpu_offload`. OpenRoto defaults to `model_cpu_offload`.

Optional tuning variables:

```text
OPENROTO_SVOR_GPU_MEMORY_MODE=model_cpu_offload
OPENROTO_SVOR_SAMPLE_SIZE=720,1280
OPENROTO_SVOR_STEPS=20
```

If `OPENROTO_SVOR_SAMPLE_SIZE` is not set, the OpenRoto runner preserves the source aspect ratio and caps inference at roughly 1280x720. The generated result is resized back to the Resolve frame dimensions before mask-aware compositing.

## External environments

Advanced users can still bypass the managed installer with explicit environment variables:

```text
OPENROTO_FGT_ROOT=<path to FGT repository>
OPENROTO_FGT_PYTHON=<path to its Python executable>

OPENROTO_SVOR_ROOT=<path to SVOR repository>
OPENROTO_SVOR_PYTHON=<path to its Python executable>
```

If either variable for a backend is set, OpenRoto treats that backend as externally managed and will not overwrite or repair it automatically.

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

The benchmark writes one output sequence and contact sheet per available backend plus `benchmark.json` containing total elapsed time, effective FPS, approximate peak VRAM delta, OpenRoto timing values, and backend metadata.
