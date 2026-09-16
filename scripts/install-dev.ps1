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
$heartbeatPath = Join-Path $env:LOCALAPPDATA "OpenRoto\free-agent-heartbeat.json"
$agentProtocol = "free-v3"
$programDataResolve = Join-Path $env:ProgramData "Blackmagic Design\DaVinci Resolve"

$allScriptDirs = @(
    $scriptDirs[0],
    $scriptDirs[1],
    (Join-Path $programDataResolve "Fusion\Scripts\Utility"),
    (Join-Path $programDataResolve "Support\Fusion\Scripts\Utility")
)
$legacyBridgeDirs = @(
    (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto"),
    (Join-Path $programDataResolve "Support\OpenRoto")
)

# Remove every legacy launcher location first. Resolve can discover more than one
# script root, so leaving a stale OpenRoto.lua anywhere can make Workspace > Scripts
# execute an older handoff protocol even when the current user copy is correct.
foreach ($dir in $allScriptDirs) {
    foreach ($name in @("OpenRoto.lua", "OpenRoto.py", "OpenRoto.py3", "OpenRoto Apply.lua")) {
        $path = Join-Path $dir $name
        try {
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
        } catch {
            Write-Warning "Could not remove stale Resolve script $path : $($_.Exception.Message)"
        }
    }
}

foreach ($dir in $legacyBridgeDirs) {
    foreach ($name in @("OpenRoto.py", "OpenRoto.py3", "OpenRotoBridge.py", "OpenRotoBridgeBase.py")) {
        $path = Join-Path $dir $name
        try {
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
        } catch {
            Write-Warning "Could not remove legacy Resolve bridge $path : $($_.Exception.Message)"
        }
    }
}

$launcherSource = Join-Path $projectRoot "resolve\OpenRoto.lua"
$launcherSourceHash = (Get-FileHash -LiteralPath $launcherSource -Algorithm SHA256).Hash
foreach ($dir in $scriptDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $launcherDestination = Join-Path $dir "OpenRoto.lua"
    Copy-Item -LiteralPath $launcherSource -Destination $launcherDestination -Force
    $installedHash = (Get-FileHash -LiteralPath $launcherDestination -Algorithm SHA256).Hash
    if ($installedHash -ne $launcherSourceHash) {
        throw "Resolve launcher verification failed at $launcherDestination."
    }
    Write-Host "Installed and verified Resolve launcher at $dir"
}

New-Item -ItemType Directory -Force -Path $bridgeDir | Out-Null
foreach ($staleName in @("OpenRoto.py", "OpenRoto.py3", "OpenRotoBridge.py", "OpenRotoBridgeBase.py")) {
    $stale = Join-Path $bridgeDir $staleName
    if (Test-Path -LiteralPath $stale) { Remove-Item -LiteralPath $stale -Force }
}
Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRotoEntry.py") -Destination (Join-Path $bridgeDir "OpenRoto.py3") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRoto.py") -Destination (Join-Path $bridgeDir "OpenRotoBridgeBase.py") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "resolve\OpenRotoRemovalBridge.py") -Destination (Join-Path $bridgeDir "OpenRotoBridge.py") -Force

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

    # A previous dev/install build may still own the singleton mutex. Find both
    # packaged and source-run OpenRoto agents by their command line. Never stop a
    # normal --session UI.
    try {
        $oldAgents = Get-CimInstance Win32_Process -ErrorAction Stop |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -match '(?i)(^|\s)--free-agent(\s|$)' -and
                ($_.Name -ieq 'OpenRoto.exe' -or $_.CommandLine -match '(?i)openroto')
            }
        foreach ($agent in $oldAgents) {
            Write-Host "Stopping previous OpenRoto Free agent process $($agent.ProcessId)."
            Stop-Process -Id $agent.ProcessId -Force -ErrorAction Stop
        }
        if ($oldAgents) { Start-Sleep -Milliseconds 500 }
    } catch {
        Write-Warning "Could not enumerate or stop a previous OpenRoto Free agent: $($_.Exception.Message)"
    }

    if (Test-Path -LiteralPath $heartbeatPath) {
        Remove-Item -LiteralPath $heartbeatPath -Force -ErrorAction Stop
    }

    $agentProcess = Start-Process -FilePath $appPath -ArgumentList "--free-agent" -WindowStyle Hidden -PassThru
    Write-Host "Started OpenRoto Free agent process $($agentProcess.Id) from $appPath."

    # Do not report a successful install until the process that owns the singleton
    # mutex proves that it is this exact executable and current handoff protocol.
    $verified = $false
    $heartbeat = $null
    for ($attempt = 0; $attempt -lt 80; $attempt++) {
        Start-Sleep -Milliseconds 100
        if (-not (Test-Path -LiteralPath $heartbeatPath)) { continue }
        try {
            $heartbeat = Get-Content -LiteralPath $heartbeatPath -Raw | ConvertFrom-Json
            $heartbeatExe = [System.IO.Path]::GetFullPath([string]$heartbeat.executable)
            $expectedExe = [System.IO.Path]::GetFullPath($appPath)
            if (
                [string]$heartbeat.protocol -eq $agentProtocol -and
                $heartbeatExe.Equals($expectedExe, [System.StringComparison]::OrdinalIgnoreCase)
            ) {
                $verified = $true
                break
            }
        } catch {
            # The agent writes atomically, but antivirus/indexers can still race a
            # read. Retry until the verification deadline.
        }
    }
    if (-not $verified) {
        try { Stop-Process -Id $agentProcess.Id -Force -ErrorAction SilentlyContinue } catch { }
        $detail = if ($heartbeat) {
            "Last heartbeat protocol=$($heartbeat.protocol), executable=$($heartbeat.executable)"
        } else {
            "No heartbeat was produced. Another stale agent may still own the mutex."
        }
        throw "OpenRoto Free agent verification failed. $detail"
    }
    Write-Host "Verified current OpenRoto Free agent protocol $agentProtocol (PID $($heartbeat.pid))."
}

$resolveApi = Join-Path $programDataResolve "Support\Developer\Scripting"
$resolveLib = "C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_API", $resolveApi, "User")
[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_LIB", $resolveLib, "User")

Write-Host "Installed the Studio Python bridge at $bridgeDir"
Write-Host "Resolve Free exchange directory: $freeExchange"
Write-Host "Fully restart DaVinci Resolve so Workspace > Scripts reloads the verified launcher."
