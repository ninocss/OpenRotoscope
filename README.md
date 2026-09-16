# OpenRoto

OpenRoto is a local, open-source subject masking workflow for DaVinci Resolve
Free and Studio. It exports the clip under the playhead, opens a focused
annotation window, tracks one subject with SAM 2.1, and applies the resulting
alpha matte back to the clip through Fusion.

> **Current status:** working developer preview. The application, Resolve
> bridge, SAM2 backend, CUDA detection, Fusion graph, installer definition and
> automated checks are implemented. The final Resolve/Fusion round trip still
> needs to be validated against real timelines before a signed release is cut.

## Workflow

1. Put the playhead over the topmost video clip you want to isolate.
2. Choose **Workspace > Scripts > OpenRoto**.
3. Resolve exports the visible clip range and OpenRoto opens automatically.
4. Left-click the subject. Right-click areas that must be excluded.
5. Scrub to difficult frames and add correction points where needed.
6. Choose **Fast**, **Balanced**, or **High**, then track in both directions.
7. Adjust overlay, expand/contract, feather or invert.
8. Choose **Render & Apply**. OpenRoto creates a non-destructive compound and
   adds the Fusion matte automatically.

The source clip remains inside the compound. Closing OpenRoto before applying
does not modify the original timeline.

## Quality presets

| Preset | SAM2.1 checkpoint | Intended use |
| --- | --- | --- |
| Fast | Hiera Tiny | Quick previews and straightforward shots |
| Balanced | Hiera Base Plus | Default for most footage |
| High | Hiera Large | Difficult motion and fine boundaries |

OpenRoto uses CUDA automatically when PyTorch detects a compatible NVIDIA GPU.
The packaged Windows build pins the CUDA 13.0 runtime. CPU inference remains
available but can be much slower. Model checkpoints download only when first
selected and are then available offline.

## Requirements

- Windows 10 or Windows 11, 64-bit
- DaVinci Resolve 21.1 or newer, Free or Studio
- An NVIDIA GPU is strongly recommended; 6 GB VRAM for Balanced and 10 GB for
  High are comfortable targets
- Enough temporary disk space for a lossless PNG sequence of the visible clip
- Internet access the first time each SAM2 preset is loaded

No system Python installation is needed by the release installer. Resolve 21.1
provides the Python runtime used by the menu bridge; the OpenRoto application
ships its own runtime.

## Development

Create a Python 3.12 environment and install the application:

```powershell
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -e ".[inference,dev]"
```

For an NVIDIA release environment, install the pinned CUDA wheels first:

```powershell
uv pip install --python .venv\Scripts\python.exe `
  torch==2.11.0+cu130 torchvision==0.26.0+cu130 `
  --index-url https://download.pytorch.org/whl/cu130
```

Run the checks:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tests\run_ui_smoke.py
pyside6-qmllint app\openroto\ui\Main.qml
```

Build the packaged application and installer:

```powershell
.\scripts\build.ps1
.venv-build\Scripts\python.exe tests\run_packaged_smoke.py .\dist\OpenRoto\OpenRoto.exe
iscc .\installer\OpenRoto.iss
```

For local Resolve testing after a build:

```powershell
.\scripts\install-dev.ps1 -AppExecutable .\dist\OpenRoto\OpenRoto.exe
```

Restart Resolve after installing or updating the menu script.
OpenRoto installs a sandbox-compatible Lua menu entry in Resolve's documented
`Utility` script folder. The Lua launcher calls Fusion's internal `RunScript`
API with an `OpenRoto.py3` bridge, keeping the bridge inside Resolve while
explicitly selecting its Python 3 runtime. It does not require or fall back to
an external system Python installation.

## Architecture and safety

- `resolve/OpenRoto.lua` is the Resolve Free/Studio menu entry. It executes the
  installed `OpenRoto.py3` copy of `resolve/OpenRoto.py` through Fusion's
  internal `RunScript` API. The bridge identifies the clip, writes a DRT safety
  snapshot, exports frames from a temporary duplicate timeline and owns all
  Resolve API calls.
- `app/openroto` is the standalone Qt Quick application. It communicates with
  the Resolve bridge through an authenticated loopback-only JSON-lines socket.
- The app writes raw masks separately from the final alpha sequence so edge
  settings can change without repeating AI tracking.
- Before applying, the bridge verifies the project, timeline, clip ID, trim and
  a fingerprint of every timeline item. If the edit changed, it refuses to
  touch the timeline and asks for a new session.
- The final Fusion graph merges the original media over a transparent
  background and uses the rendered RGBA mask sequence as the Merge effect mask.
- If Fusion application fails after creating the compound, the bridge imports
  the DRT snapshot and restores the original timeline.
- No footage, prompts or telemetry leave the computer. Network access is used
  only for package and model downloads.

Session data lives under `%LOCALAPPDATA%\OpenRoto\Sessions`. Input frames are
temporary. Final mattes remain there because the Fusion Loader references them;
do not delete a session that is still used by a Resolve project.

## Known preview limitations

- A signed production installer has not been generated in this repository yet.
- Resolve PNG renderer naming and the imported Fusion Loader graph need a live
  end-to-end verification on both Free and Studio before version 1.0.
- The first model load can take several minutes because Hugging Face downloads
  the selected checkpoint.
- Direction-only tracking intentionally makes frames outside the selected pass
  transparent. Use **Both directions** for a complete clip matte.

## License

OpenRoto is released under the [MIT License](LICENSE). SAM2 and other runtime
components retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).

OpenRoto is independent software and is not affiliated with Blackmagic Design,
DaVinci Resolve, Meta, or KVN Rotoscope.
