[CmdletBinding()]
param(
    [string]$AppExecutable = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

$scriptDirs = @(
    (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"),
    (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility")
)
$bridgeDir = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\OpenRoto"
$freeExchange = Join-Path $env:LOCALAPPDATA "OpenRoto\FreeExchange"
$freeSessions = Join-Path $env:LOCALAPPDATA "OpenRoto\Sessions"

$allScriptDirs = @(
    $scriptDirs[0],
    $scriptDirs[1],
    "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility"
)
$legacyBridgeDirs = @(
    (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto"),
    "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\OpenRoto"
)

foreach ($dir in $allScriptDirs) {
    foreach ($name in @("OpenRoto.py", "OpenRoto.py3")) {
        $path = Join-Path $dir $name
        try {
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
        } catch {
            Write-Warning "Could not remove stale Resolve script $path : $($_.Exception.Message)"
        }
    }
}

$allUsersLua = "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.lua"
try {
    if (Test-Path -LiteralPath $allUsersLua) { Remove-Item -LiteralPath $allUsersLua -Force }
} catch {
    Write-Warning "Could not remove legacy Resolve script $allUsersLua : $($_.Exception.Message)"
}

foreach ($dir in $legacyBridgeDirs) {
    foreach ($name in @("OpenRoto.py", "OpenRoto.py3", "OpenRotoBridge.py")) {
        $path = Join-Path $dir $name
        try {
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
        } catch {
            Write-Warning "Could not remove legacy Resolve bridge $path : $($_.Exception.Message)"
        }
    }
}

foreach ($dir in $scriptDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRoto.lua") -Destination (Join-Path $dir "OpenRoto.lua") -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRoto Apply.lua") -Destination (Join-Path $dir "OpenRoto Apply.lua") -Force
    Write-Host "Installed Resolve launch/apply scripts at $dir"
}

New-Item -ItemType Directory -Force -Path $bridgeDir | Out-Null
foreach ($staleName in @("OpenRoto.py", "OpenRoto.py3", "OpenRotoBridge.py")) {
    $stale = Join-Path $bridgeDir $staleName
    if (Test-Path -LiteralPath $stale) { Remove-Item -LiteralPath $stale -Force }
}
Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRotoEntry.py") -Destination (Join-Path $bridgeDir "OpenRoto.py3") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRoto.py") -Destination (Join-Path $bridgeDir "OpenRotoBridge.py") -Force

New-Item -ItemType Directory -Force -Path $freeExchange | Out-Null
New-Item -ItemType Directory -Force -Path $freeSessions | Out-Null

if ($AppExecutable) {
    $appPath = (Resolve-Path -LiteralPath $AppExecutable).Path
    [Environment]::SetEnvironmentVariable("OPENROTO_APP", $appPath, "User")
    Write-Host "OPENROTO_APP now points to $appPath"

    $runtimePath = Join-Path (Split-Path -Parent $appPath) "python-runtime"
    if (-not (Test-Path -LiteralPath (Join-Path $runtimePath "python.exe"))) {
        throw "Bundled Resolve Python runtime was not found at $runtimePath. Run scripts\build.ps1 first."
    }
    [Environment]::SetEnvironmentVariable("FUSION_Python3_Home", $runtimePath, "User")
    Write-Host "FUSION_Python3_Home now points to $runtimePath"

    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    New-Item -Path $runKey -Force | Out-Null
    $agentCommand = '"' + $appPath + '" --free-agent'
    New-ItemProperty -Path $runKey -Name "OpenRoto Free Agent" -Value $agentCommand -PropertyType String -Force | Out-Null
    Write-Host "Registered the OpenRoto Free agent for user login."

    try {
        Start-Process -FilePath $appPath -ArgumentList "--free-agent" -WindowStyle Hidden
        Write-Host "Started the OpenRoto Free agent."
    } catch {
        Write-Warning "Could not start the OpenRoto Free agent: $($_.Exception.Message)"
    }
}

$resolveApi = "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
$resolveLib = "C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_API", $resolveApi, "User")
[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_LIB", $resolveLib, "User")

Write-Host "Installed the Studio Python bridge at $bridgeDir"
Write-Host "Resolve Free exchange directory: $freeExchange"
Write-Host "Fully restart DaVinci Resolve so Workspace > Scripts is rescanned."
