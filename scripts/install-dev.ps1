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
    foreach ($staleName in @("OpenRoto.py", "OpenRoto.py3")) {
        $stale = Join-Path $dir $staleName
        if (Test-Path -LiteralPath $stale) { Remove-Item -LiteralPath $stale -Force }
    }
    Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRoto.lua") -Destination (Join-Path $dir "OpenRoto.lua") -Force
}

foreach ($dir in $bridgeDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    foreach ($staleName in @("OpenRoto.py", "OpenRoto.py3", "OpenRotoBridge.py")) {
        $stale = Join-Path $dir $staleName
        if (Test-Path -LiteralPath $stale) { Remove-Item -LiteralPath $stale -Force }
    }
    Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRotoEntry.py") -Destination (Join-Path $dir "OpenRoto.py3") -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRoto.py") -Destination (Join-Path $dir "OpenRotoBridge.py") -Force
}

if ($AppExecutable) {
    # Resolve-Path returns a PathInfo object. Persisting the object itself can
    # result in a relative/empty user environment variable, so explicitly use
    # its absolute string path.
    $appPath = (Resolve-Path -LiteralPath $AppExecutable).Path
    [Environment]::SetEnvironmentVariable("OPENROTO_APP", $appPath, "User")
    Write-Host "OPENROTO_APP now points to $appPath"

    $runtimePath = Join-Path (Split-Path -Parent $appPath) "python-runtime"
    if (-not (Test-Path -LiteralPath (Join-Path $runtimePath "python.exe"))) {
        throw "Bundled Resolve Python runtime was not found at $runtimePath. Run scripts\build.ps1 first."
    }
    [Environment]::SetEnvironmentVariable("FUSION_Python3_Home", $runtimePath, "User")
    Write-Host "FUSION_Python3_Home now points to $runtimePath"
}

# These variables are useful for Studio/external scripting and harmless for the
# in-app Free/Studio bridge. The menu bridge itself reuses Resolve's live object.
$resolveApi = "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
$resolveLib = "C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"

[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_API", $resolveApi, "User")
[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_LIB", $resolveLib, "User")

Write-Host "Installed the Resolve Lua launcher, diagnostic Python 3 bootstrap, and bridge."
Write-Host "Fully restart DaVinci Resolve so it sees FUSION_Python3_Home, then open Workspace > Scripts > OpenRoto."
