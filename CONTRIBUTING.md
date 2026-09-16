# Contributing to OpenRoto

Thanks for contributing.

OpenRoto is currently a Windows-first developer preview for DaVinci Resolve Free and Studio. Changes that touch Resolve integration, session handling, tracking, object removal or packaging should be treated as regression-sensitive.

## Development setup

Use Python 3.12 for the standalone application:

```powershell
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -e ".[inference,dev]"
```

For CUDA development, install the PyTorch build documented in `README.md` before installing the optional inference dependencies.

## Before opening a pull request

Run:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tests\run_ui_smoke.py
```

If QML changed, run the relevant files through `pyside6-qmllint`.

If packaging, Resolve integration or installer scripts changed, also validate the packaged app and installer path where possible.

## Pull-request expectations

- Keep changes focused and explain the user-visible behavior.
- Add or update regression tests for bugs.
- Do not commit model weights, rendered footage, Resolve projects, local session folders or generated installers.
- Do not commit credentials, API keys, private certificates or local `.env` files.
- Keep optional third-party AI backends isolated from OpenRoto's packaged Python environment unless their dependency and license requirements are compatible.
- Preserve the non-destructive Resolve workflow and DRT recovery path.
- Treat DaVinci Resolve Free and Studio as separate integration paths when changing the bridge or launcher.

## Licensing

By contributing code or documentation, you agree that your contribution may be distributed under the repository's MIT License.

Do not submit third-party code, model weights or assets unless their license permits redistribution and the required notices are included.
