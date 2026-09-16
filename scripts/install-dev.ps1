[CmdletBinding()]
param(
    [string]$AppExecutable = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$scriptDirs = @(
    (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"),
    (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility"),
    "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility"
)

$bridgeDirs = @(
    (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\OpenRoto"),
    (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto"),
    "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\OpenRoto"
)

foreach ($dir in $scriptDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $stalePy = Join-Path $dir "OpenRoto.py"
    if (Test-Path -LiteralPath $stalePy) { Remove-Item -LiteralPath $stalePy -Force }
    $stalePy3 = Join-Path $dir "OpenRoto.py3"
    if (Test-Path -LiteralPath $stalePy3) { Remove-Item -LiteralPath $stalePy3 -Force }
    Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRoto.lua") -Destination (Join-Path $dir "OpenRoto.lua") -Force
}

foreach ($dir in $bridgeDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRoto.py") -Destination (Join-Path $dir "OpenRoto.py") -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRoto.py") -Destination (Join-Path $dir "OpenRoto.py3") -Force
}

if ($AppExecutable) {
    # Resolve-Path returns a PathInfo object. Persisting the object itself can
    # result in a relative/empty user environment variable, so explicitly use
    # its absolute string path.
    $appPath = (Resolve-Path -LiteralPath $AppExecutable).Path
    [Environment]::SetEnvironmentVariable("OPENROTO_APP", $appPath, "User")
    Write-Host "OPENROTO_APP now points to $appPath"
}

# Set DaVinci Resolve Scripting environment variables if not present
$resolveApi = "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
$resolveLib = "C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
$resolveModules = "$resolveApi\Modules"

[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_API", $resolveApi, "User")
[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_LIB", $resolveLib, "User")

Write-Host "Installed the Resolve Free/Studio Lua menu entry and Python 3 bridge. After a full Resolve restart, open Workspace > Scripts > OpenRoto."
