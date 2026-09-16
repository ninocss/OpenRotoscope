[CmdletBinding()]
param(
    [string]$Python = "3.12",
    [switch]$SkipCuda
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv-build"
$distPath = Join-Path $projectRoot "dist"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required to build OpenRoto. Install it from https://docs.astral.sh/uv/."
}

uv venv $venvPath --python $Python --clear
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if (-not $SkipCuda) {
    uv pip install --python $pythonExe `
        "torch==2.11.0+cu130" "torchvision==0.26.0+cu130" `
        --index-url "https://download.pytorch.org/whl/cu130"
}

uv pip install --python $pythonExe -e "$projectRoot[inference,dev]"

& $pythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name OpenRoto `
    --paths (Join-Path $projectRoot "app") `
    --add-data "$(Join-Path $projectRoot 'app\openroto\ui\Main.qml');openroto/ui" `
    --add-data "$(Join-Path $projectRoot 'app\openroto\ui\openroto.svg');openroto/ui" `
    --add-data "$(Join-Path $projectRoot 'THIRD_PARTY_NOTICES.md');." `
    --collect-all sam2 `
    --collect-all PySide6 `
    --hidden-import torch `
    --hidden-import torchvision `
    --distpath $distPath `
    --workpath (Join-Path $projectRoot "build\pyinstaller") `
    (Join-Path $projectRoot "app\openroto\main.py")

Write-Host "OpenRoto app created at $distPath\OpenRoto"
