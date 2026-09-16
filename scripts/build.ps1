[CmdletBinding()]
param(
    [string]$Python = "3.12",
    [string]$ResolvePythonVersion = "3.10.11",
    [switch]$SkipCuda
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv-build"
$distPath = Join-Path $projectRoot "dist"
$distAppPath = Join-Path $distPath "OpenRoto"

function Stop-OpenRotoProcessesFromPath([string]$rootPath) {
    $root = [System.IO.Path]::GetFullPath($rootPath).TrimEnd('\') + '\'
    foreach ($process in (Get-Process -Name "OpenRoto" -ErrorAction SilentlyContinue)) {
        $processPath = $null
        try {
            $processPath = $process.Path
        } catch {
            continue
        }
        if (-not $processPath) { continue }
        $fullProcessPath = [System.IO.Path]::GetFullPath($processPath)
        if (-not $fullProcessPath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
            continue
        }
        Write-Host "Stopping local build process $($process.Id): $fullProcessPath"
        Stop-Process -Id $process.Id -Force -ErrorAction Stop
        try { $process.WaitForExit(5000) | Out-Null } catch { }
    }
}

function Remove-DirectoryWithRetry([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return }
    $lastError = $null
    for ($attempt = 1; $attempt -le 6; $attempt++) {
        try {
            Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction Stop
            return
        } catch {
            $lastError = $_
            if ($attempt -lt 6) {
                Start-Sleep -Milliseconds (250 * $attempt)
            }
        }
    }
    throw "Could not remove old build output at $path. Close any Explorer windows or processes using files there and retry. Last error: $($lastError.Exception.Message)"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required to build OpenRoto. Install it from https://docs.astral.sh/uv/."
}

# install-dev.ps1 may have started the Free agent directly from dist\OpenRoto.
# Stop only processes whose executable lives inside this repository's build
# output, then remove that output before PyInstaller tries to replace it.
Stop-OpenRotoProcessesFromPath $distAppPath
Remove-DirectoryWithRetry $distAppPath

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
    --add-data "$(Join-Path $projectRoot 'app\openroto\ui\PolishedMain.qml');openroto/ui" `
    --add-data "$(Join-Path $projectRoot 'app\openroto\ui\TimedMain.qml');openroto/ui" `
    --add-data "$(Join-Path $projectRoot 'app\openroto\ui\openroto.svg');openroto/ui" `
    --add-data "$(Join-Path $projectRoot 'THIRD_PARTY_NOTICES.md');." `
    --collect-all sam2 `
    --collect-all PySide6 `
    --hidden-import torch `
    --hidden-import torchvision `
    --distpath $distPath `
    --workpath (Join-Path $projectRoot "build\pyinstaller") `
    (Join-Path $projectRoot "app\openroto_launcher.py")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$runtimeDestination = Join-Path $distPath "OpenRoto\python-runtime"
& (Join-Path $PSScriptRoot "prepare-python-runtime.ps1") `
    -Destination $runtimeDestination `
    -Version $ResolvePythonVersion
if ($LASTEXITCODE -ne 0) {
    throw "Preparing the bundled Resolve Python runtime failed with exit code $LASTEXITCODE"
}

Write-Host "OpenRoto app created at $distPath\OpenRoto"
Write-Host "Resolve Python runtime created at $runtimeDestination"
