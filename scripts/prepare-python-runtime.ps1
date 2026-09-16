[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Destination,
    [string]$Version = "3.10.11"
)

$ErrorActionPreference = "Stop"

$destinationPath = [System.IO.Path]::GetFullPath($Destination)
$buildRoot = Join-Path ([System.IO.Path]::GetTempPath()) "OpenRoto-PythonRuntime"
$archive = Join-Path $buildRoot "python-$Version-embed-amd64.zip"
$url = "https://www.python.org/ftp/python/$Version/python-$Version-embed-amd64.zip"

New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
if (Test-Path -LiteralPath $destinationPath) {
    Remove-Item -LiteralPath $destinationPath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null

Write-Host "Downloading CPython $Version embeddable runtime from $url"
Invoke-WebRequest -Uri $url -OutFile $archive -UserAgent "OpenRoto build"
Expand-Archive -LiteralPath $archive -DestinationPath $destinationPath -Force

$pythonExe = Join-Path $destinationPath "python.exe"
$pythonDll = Get-ChildItem -LiteralPath $destinationPath -Filter "python3*.dll" | Select-Object -First 1
$stdlibZip = Get-ChildItem -LiteralPath $destinationPath -Filter "python3*.zip" | Select-Object -First 1

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Bundled Python runtime is missing python.exe"
}
if (-not $pythonDll) {
    throw "Bundled Python runtime is missing python3*.dll"
}
if (-not $stdlibZip) {
    throw "Bundled Python runtime is missing the Python standard-library zip"
}

# Keep Resolve on CPython 3.10 for the in-process bridge. Resolve/Fusion's
# Windows scripting stack has historically depended on APIs removed in Python
# 3.12, so the application can still be built with 3.12 while the tiny bridge
# gets a separate, known-compatible interpreter.
& $pythonExe -I -c "import ctypes, json, pathlib, socket, subprocess, sys; assert sys.version_info[:2] == (3, 10), sys.version; print(sys.version); print(sys.prefix)"
if ($LASTEXITCODE -ne 0) {
    throw "Bundled Python runtime failed its Resolve bridge smoke test"
}

Set-Content -LiteralPath (Join-Path $destinationPath "OPENROTO_PYTHON_RUNTIME.txt") `
    -Value "CPython $Version embeddable Windows x64 runtime for the DaVinci Resolve bridge." `
    -Encoding UTF8

Write-Host "Bundled Resolve Python runtime prepared at $destinationPath"
