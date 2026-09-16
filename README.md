# OpenRoto

OpenRoto is a local, open-source rotoscoping and object-removal workflow for DaVinci Resolve Free and Studio on Windows.

It can:

- export the clip under the playhead from Resolve;
- select and track a subject with SAM 2.1;
- render an alpha matte and apply it back through Fusion;
- remove a tracked object and reconstruct the covered background;
- run locally without uploading footage, prompts, masks or project data.

> **Status:** developer preview. The Resolve Free round trip has been validated on real timelines. Studio support, installer/release packaging and the optional learned object-removal backends should still be treated as pre-1.0 software.

## Rotoscope workflow

1. Put the playhead over the video clip you want to process.
2. Choose **Workspace > Scripts > OpenRoto**.
3. Resolve exports the visible clip range and OpenRoto opens automatically.
4. In **Rotoscope**, left-click the subject and right-click areas that must be excluded.
5. Scrub to difficult frames and add correction points where needed.
6. Choose **Fast**, **Balanced** or **High**, then track.
7. Adjust expand/contract, feather or invert.
8. Choose **Render & Apply**.

OpenRoto creates a non-destructive compound/Fusion setup. The original source remains available inside the compound.

## Object removal

The **Remove** tab reuses the same SAM2 selection and tracking data, then reconstructs the masked region.

Available backends:

| Backend | Availability | Intended use |
| --- | --- | --- |
| Temporal Fill | Built in | Fast local fallback; best when the hidden background is visible in nearby frames |
| FGT++ | Optional local sidecar | Classical learned video inpainting on consumer hardware |
| SVOR | Optional local sidecar | High-quality diffusion-based removal for high-VRAM systems |

FGT++ and SVOR are not bundled with OpenRoto. Their code, environments and model weights remain separate and keep their upstream licenses. See [docs/removal-backends.md](docs/removal-backends.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## SAM2 quality presets

| Preset | SAM2.1 checkpoint | Intended use |
| --- | --- | --- |
| Fast | Hiera Tiny | Quick previews and straightforward shots |
| Balanced | Hiera Base Plus | Default for most footage |
| High | Hiera Large | Difficult motion and fine boundaries |

OpenRoto uses CUDA automatically when PyTorch detects a compatible NVIDIA GPU. CPU inference remains available but can be much slower. SAM2 checkpoints download only when first selected and are then available offline.

## Requirements

- Windows 10 or Windows 11, 64-bit
- DaVinci Resolve 21.1 or newer, Free or Studio
- NVIDIA GPU strongly recommended
- roughly 6 GB VRAM for Balanced and 10 GB for High are comfortable SAM2 targets
- enough temporary disk space for the exported image sequence
- internet access when a model is downloaded for the first time

No system Python installation is required by the packaged application. OpenRoto ships a private official CPython **3.10.11** embeddable runtime for the Resolve Python bridge and packages the Qt application separately with PyInstaller.

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

Run the main checks:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tests\run_ui_smoke.py
pyside6-qmllint app\openroto\ui\Main.qml
```

Build the application and installer:

```powershell
.\scripts\build.ps1
.venv-build\Scripts\python.exe tests\run_packaged_smoke.py .\dist\OpenRoto\OpenRoto.exe
iscc .\installer\OpenRoto.iss
```

For local Resolve testing after a build:

```powershell
.\scripts\install-dev.ps1 -AppExecutable .\dist\OpenRoto\OpenRoto.exe
```

Fully restart Resolve after installing or updating the Workspace script.

## Resolve Free integration

Resolve Free uses a filesystem handoff because Workspace scripting restrictions can prevent the normal in-process Python bridge from running.

The Lua launcher:

- creates a DRT safety snapshot;
- renders the target clip to `%LOCALAPPDATA%\OpenRoto\FreeExchange`;
- waits for the OpenRoto Free agent to claim the session;
- waits for a local apply/cancel control signal;
- applies the generated Fusion composition and records an acknowledgement.

The installed Free agent is protected by a singleton mutex. Development installs verify the current agent with a `free-v3` heartbeat so a stale executable cannot silently keep handling new exports.

## Diagnostics

Runtime diagnostics are stored under `%LOCALAPPDATA%\OpenRoto`:

- `free-agent.log` — Resolve Free exchange/claim diagnostics;
- `app.log` — packaged application startup and uncaught errors;
- `console.log` — stdout/stderr from the packaged application;
- bridge logs — Studio/bootstrap diagnostics when that path is used.

Lua also exposes persistent stage information through Fusion application data, including `OpenRoto.LauncherStage`, `OpenRoto.LauncherError` and `OpenRoto.Free.SessionId`.

## Architecture and safety

- `resolve/OpenRoto.lua` is the Resolve Workspace entry point.
- `resolve/OpenRotoEntry.py` and the bridge scripts implement Studio integration.
- `app/openroto` is the standalone Qt Quick application.
- Resolve communication is loopback-only or filesystem-local depending on edition.
- Session credentials are generated per run; no fixed API key is stored in the repository.
- The app keeps raw masks separate from final mattes so edge settings can be changed without rerunning tracking.
- The Resolve bridge validates the target timeline/clip before modifying the edit.
- If application fails after a timeline mutation begins, OpenRoto uses the DRT safety snapshot to recover where supported.

Session data lives under `%LOCALAPPDATA%\OpenRoto\Sessions`. Final matte/removal sequences can remain referenced by Fusion, so do not delete a session directory while a Resolve project still uses it.

## Privacy

OpenRoto does not include telemetry and does not upload footage, points, masks or Resolve project data. Network access is used for explicit package/model downloads and build-time dependency downloads.

## Security

Please do not publish security-sensitive reports as public issues. See [SECURITY.md](SECURITY.md).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development and pull-request expectations.

## License

OpenRoto is released under the [MIT License](LICENSE). Runtime and optional model components retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

OpenRoto is independent software and is not affiliated with, endorsed by or sponsored by Blackmagic Design, DaVinci Resolve, Meta, FGT++/Hitachi Research or Xiaomi Research.
