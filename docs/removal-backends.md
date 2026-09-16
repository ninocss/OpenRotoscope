# OpenRoto object-removal backends

OpenRoto keeps video inpainting separate from the packaged SAM2/Qt process. This avoids dependency conflicts and lets each optional backend use the Python/Torch stack it was designed for.

## Built-in: Temporal Fill

No setup is required. OpenRoto reconstructs masked pixels from nearby frames where the background is visible, then uses a spatial fallback for pixels that remain hidden. This is the fastest option and is intended for previews and simple shots.

## FGT++

Upstream: https://github.com/hitachinsk/FGT

License: MIT.

The official repository documents Ubuntu 20.04, Python 3.6.8 and PyTorch 1.10.1. Because that environment is much older than OpenRoto's packaged Python/Torch stack, OpenRoto runs FGT in an isolated sidecar Python environment instead of importing it into the main app.

Create a local environment that can run the upstream command below successfully:

```text
python tool/video_inpainting.py --path <frames> --path_mask <masks> --outroot <output>
```

Then set these variables before starting OpenRoto/Resolve:

```text
OPENROTO_FGT_ROOT=<path to FGT repository>
OPENROTO_FGT_PYTHON=<path to the Python executable for that FGT environment>
```

On Windows, upstream FGT is not officially supported. Use a Windows-compatible local port/environment if you have one. OpenRoto deliberately does not silently install or modify the legacy FGT environment.

## SVOR

Upstream: https://github.com/xiaomi-research/svor

License: Apache-2.0 for the SVOR repository. The upstream setup additionally downloads Wan2.1-VACE-1.3B and SVOR LoRA weights; review their upstream license terms before redistribution. OpenRoto does not bundle those weights.

The official SVOR repository documents Python 3.10, PyTorch 2.7.0 and optional Flash-Attention. It reports about 33 GB of GPU memory in the default mode and about 24 GB with `model_cpu_offload`.

Create the upstream SVOR environment and download the model files described by the project. Then set:

```text
OPENROTO_SVOR_ROOT=<path to SVOR repository>
OPENROTO_SVOR_PYTHON=<path to the Python executable for that SVOR environment>
```

Optional tuning variables:

```text
OPENROTO_SVOR_GPU_MEMORY_MODE=model_cpu_offload
OPENROTO_SVOR_SAMPLE_SIZE=720,1280
OPENROTO_SVOR_STEPS=20
```

If `OPENROTO_SVOR_SAMPLE_SIZE` is not set, the OpenRoto runner preserves the source aspect ratio and caps inference at roughly 1280x720. The generated result is resized back to the Resolve frame dimensions before mask-aware compositing.

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
