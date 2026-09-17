# OpenRoto object-removal backends

OpenRoto keeps video inpainting separate from the packaged SAM2/Qt process. FGT++ and SVOR run in isolated local Python environments so their Torch and dependency versions cannot replace OpenRoto's own packages.

## Built-in: Temporal Fill

No setup is required. OpenRoto reconstructs masked pixels from nearby frames where the background is visible, then uses a spatial fallback for pixels that remain hidden. This is the fastest option and is intended for previews and simple shots.

## Automatic setup on Windows

FGT++ and SVOR are downloaded on first use. Selecting either backend and starting Preview or Remove & Apply makes OpenRoto:

1. download a pinned upstream source revision;
2. create a private Python runtime under `%LOCALAPPDATA%\OpenRoto\RemovalBackends\<backend>`;
3. install the backend-specific Python/Torch dependencies;
4. download the required model weights;
5. verify the runtime, source files and weights before starting inference.

An interrupted or incomplete setup is repairable: start the backend again and OpenRoto retries the missing setup steps. Installation output is written to the backend's `install.log` file.

OpenRoto downloads these third-party files on demand; they are not bundled in the OpenRoto installer.

## FGT++

Upstream: https://github.com/hitachinsk/FGT

License: MIT.

The official FGT repository targets an old Linux/Python/PyTorch stack. OpenRoto therefore uses a Windows compatibility sidecar with its own Python 3.8 runtime and legacy PyTorch/CUDA packages. The upstream project does not officially support Windows, so GPU/driver combinations that cannot run the legacy CUDA stack can still fail even when installation completes.

OpenRoto downloads the FGT/LAFC checkpoints from the upstream `hitachinsk/FGT` Hugging Face repository and keeps the upstream RAFT checkpoint shipped in the source checkout.

The FGT runner is launched from the upstream `tool` directory so its relative config and checkpoint paths resolve correctly.

## SVOR

Upstream: https://github.com/xiaomi-research/svor

License: Apache-2.0 for the SVOR repository. The model repositories have their own published license terms; review them before redistribution.

OpenRoto creates a Python 3.10 sidecar with the upstream PyTorch 2.7/CUDA 12.6 dependency stack. It downloads:

- `HigherHu/SVOR` LoRA weights;
- `Wan-AI/Wan2.1-VACE-1.3B` base model.

The Wan2.1 base model is large (roughly 19 GB on Hugging Face), in addition to the SVOR LoRAs and Python/Torch environment. SVOR also requires substantial GPU memory. The upstream project reports about 33 GB in its default mode and about 24 GB with model CPU offload. OpenRoto defaults to `model_cpu_offload`.

Optional tuning variables:

```text
OPENROTO_SVOR_GPU_MEMORY_MODE=model_cpu_offload
OPENROTO_SVOR_SAMPLE_SIZE=720,1280
OPENROTO_SVOR_STEPS=20
```

If `OPENROTO_SVOR_SAMPLE_SIZE` is not set, the OpenRoto runner preserves the source aspect ratio and caps inference at roughly 1280x720. SVOR's Wan VAE uses a temporal compression ratio of four, so OpenRoto pads the inference length to the next valid `4n+1` length and discards only the generated tail frames. The result is resized back to the Resolve frame dimensions before mask-aware compositing.

## Manual environments / overrides

Advanced users can still provide their own sidecar environments. Set both variables for the backend before starting OpenRoto/Resolve:

```text
OPENROTO_FGT_ROOT=<path to FGT repository>
OPENROTO_FGT_PYTHON=<path to the Python executable>

OPENROTO_SVOR_ROOT=<path to SVOR repository>
OPENROTO_SVOR_PYTHON=<path to the Python executable>
```

When any override is configured, OpenRoto treats that backend as user-managed and will not download, replace or repair files in the supplied environment.

## Backend safety

FGT++ and SVOR return complete RGB frames, but OpenRoto does not trust them to preserve the rest of the frame. After inference, OpenRoto composites the generated image through the padded/feathered SAM2 removal mask. Pixels outside the removal area therefore remain the original Resolve export.

Managed source archives are pinned to known upstream Git revisions. OpenRoto also rejects path-traversal entries in downloaded ZIP archives and refuses to replace symlinked managed backend directories.

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

- total elapsed milliseconds;
- effective frames per second;
- approximate peak VRAM delta sampled with `nvidia-smi`;
- OpenRoto removal timing values;
- backend license/VRAM metadata.

Peak VRAM is an approximation because `nvidia-smi` observes total GPU memory use, including other applications. Visual quality is intentionally not reduced to a synthetic score; compare the generated sequences/contact sheets on the actual shot.
