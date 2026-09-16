-- OpenRoto menu entry for DaVinci Resolve Free and Studio.

local ffi_ok, ffi = pcall(require, "ffi")
local user32 = nil
local kernel32 = nil
if ffi_ok then
    pcall(function()
        ffi.cdef[[
            int MessageBoxA(void* hWnd, const char* lpText, const char* lpCaption, unsigned int uType);
            int SetEnvironmentVariableA(const char* lpName, const char* lpValue);
        ]]
        user32 = ffi.load("user32")
        kernel32 = ffi.load("kernel32")
    end)
end

local function localDataPath()
    local value = os.getenv("LOCALAPPDATA")
    if value ~= nil and value ~= "" then return value end
    local userProfile = os.getenv("USERPROFILE")
    if userProfile ~= nil and userProfile ~= "" then
        return userProfile .. "\\AppData\\Local"
    end
    return nil
end

local function fileExists(path)
    local handle = io.open(path, "rb")
    if handle == nil then return false end
    handle:close()
    return true
end

local function logMessage(message)
    local localData = localDataPath()
    if localData == nil then return end
    local dir = localData .. "\\OpenRoto"
    pcall(function()
        os.execute('mkdir "' .. dir .. '" 2>nul')
        local f = io.open(dir .. "\\launcher.log", "a")
        if f then
            f:write(os.date("%Y-%m-%d %H:%M:%S ") .. tostring(message) .. "\n")
            f:close()
        end
    end)
end

local function showDialog(title, text, isError)
    logMessage(title .. ": " .. text)
    local flag = isError and 0x10 or 0x40
    if user32 ~= nil then
        local ok = pcall(function()
            user32.MessageBoxA(nil, tostring(text), tostring(title), flag)
        end)
        if ok then return end
    end
    pcall(function()
        local safeText = string.gsub(tostring(text), '"', "'")
        local safeTitle = string.gsub(tostring(title), '"', "'")
        local cmd = 'powershell -NoProfile -WindowStyle Hidden -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show(\\"'
            .. safeText
            .. '\\", \\"'
            .. safeTitle
            .. '\\")" 2>nul'
        os.execute(cmd)
    end)
end

local function resolveGlobal(name)
    local value = rawget(_G, name)
    if value == nil then return nil end
    if type(value) == "function" then
        local ok, result = pcall(value)
        if ok then return result end
        return nil
    end
    return value
end

local function pythonString(value)
    local escaped = string.gsub(tostring(value), "\\", "\\\\")
    escaped = string.gsub(escaped, "'", "\\'")
    return "'" .. escaped .. "'"
end

logMessage("=== OpenRoto.lua launcher invoked ===")
logMessage("Lua version=" .. tostring(_VERSION) .. ", ffi=" .. tostring(ffi_ok))
logMessage("APPDATA=" .. tostring(os.getenv("APPDATA")))
logMessage("LOCALAPPDATA=" .. tostring(os.getenv("LOCALAPPDATA")))
logMessage("USERPROFILE=" .. tostring(os.getenv("USERPROFILE")))
logMessage("OPENROTO_APP=" .. tostring(os.getenv("OPENROTO_APP")))
logMessage("FUSION_Python3_Home(before)=" .. tostring(os.getenv("FUSION_Python3_Home")))
logMessage("PYTHONHOME=" .. tostring(os.getenv("PYTHONHOME")))

local appData = os.getenv("APPDATA")
if appData == nil or appData == "" then
    showDialog("OpenRoto Error", "Could not locate APPDATA.", true)
    error("OpenRoto could not locate APPDATA.")
end

local localData = localDataPath()
if localData == nil then
    showDialog("OpenRoto Error", "Could not locate LOCALAPPDATA or USERPROFILE.", true)
    error("OpenRoto could not locate local application data.")
end

local appExecutable = os.getenv("OPENROTO_APP")
local appDir = nil
if appExecutable ~= nil and appExecutable ~= "" then
    appDir = string.match(appExecutable, "^(.*)\\[^\\]+$")
end
if appDir == nil or appDir == "" then
    appDir = localData .. "\\Programs\\OpenRoto"
    appExecutable = appDir .. "\\OpenRoto.exe"
end

local runtimeDir = appDir .. "\\python-runtime"
local runtimePython = runtimeDir .. "\\python.exe"
local runtimeDll = runtimeDir .. "\\python312.dll"
logMessage("appExecutable=" .. tostring(appExecutable) .. ", exists=" .. tostring(fileExists(appExecutable)))
logMessage("runtimeDir=" .. tostring(runtimeDir))
logMessage("runtime python exists=" .. tostring(fileExists(runtimePython)) .. ", python312.dll exists=" .. tostring(fileExists(runtimeDll)))

if not fileExists(appExecutable) then
    showDialog(
        "OpenRoto Error",
        "OpenRoto.exe was not found at:\n" .. appExecutable .. "\n\nReinstall OpenRoto and fully restart DaVinci Resolve.",
        true
    )
    error("OpenRoto executable not found: " .. appExecutable)
end

if not fileExists(runtimePython) or not fileExists(runtimeDll) then
    showDialog(
        "OpenRoto Error",
        "The bundled Python runtime is missing or incomplete. Reinstall the newest OpenRoto build and fully restart DaVinci Resolve.\n\nExpected: " .. runtimeDir,
        true
    )
    error("Bundled Python runtime incomplete: " .. runtimeDir)
end

-- Resolve/Fusion detects Python dynamically. Pin it to the runtime shipped with
-- OpenRoto before asking Fusion to initialise its Py3 interpreter. The installer
-- also persists this value so a clean Resolve restart sees it from process start.
if kernel32 ~= nil then
    local ok, result = pcall(function()
        return kernel32.SetEnvironmentVariableA("FUSION_Python3_Home", runtimeDir)
    end)
    logMessage("SetEnvironmentVariableA(FUSION_Python3_Home): ok=" .. tostring(ok) .. ", result=" .. tostring(result))
end
logMessage("FUSION_Python3_Home(after)=" .. tostring(os.getenv("FUSION_Python3_Home")))

local resolveHost = resolveGlobal("resolve") or resolveGlobal("Resolve")
local fusionHost = resolveGlobal("fusion") or resolveGlobal("fu") or resolveGlobal("app")
if fusionHost == nil and resolveHost ~= nil then
    local ok, value = pcall(function() return resolveHost:Fusion() end)
    logMessage("resolveHost:Fusion(): ok=" .. tostring(ok) .. ", value=" .. tostring(value))
    if ok then fusionHost = value end
end
if fusionHost == nil then
    fusionHost = resolveGlobal("Fusion")
end

logMessage("resolveHost=" .. tostring(resolveHost) .. ", type=" .. tostring(type(resolveHost)))
logMessage("fusionHost=" .. tostring(fusionHost) .. ", type=" .. tostring(type(fusionHost)))

if fusionHost == nil then
    showDialog(
        "OpenRoto Error",
        "DaVinci Resolve did not expose the Fusion scripting host. Restart Resolve and try again.\n\nSee %LOCALAPPDATA%\\OpenRoto\\launcher.log",
        true
    )
    error("OpenRoto could not access the Fusion scripting host.")
end

-- Probe Python before running the real bridge. Fusion can fail to initialise Py3
-- without throwing a useful Lua error, so the Python side must create a marker.
local probePath = localData .. "\\OpenRoto\\python-probe.log"
os.remove(probePath)
local probeCode = "!Py3: import os,sys,time; p=" .. pythonString(probePath)
    .. "; f=open(p,'w',encoding='utf-8'); f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + 'python=' + sys.version.replace('\\n',' ') + '; executable=' + str(sys.executable) + '; prefix=' + str(sys.prefix)); f.close()"
local probeOk, probeResult = pcall(function()
    return fusionHost:Execute(probeCode)
end)
logMessage("fusionHost:Execute(Py3 probe): ok=" .. tostring(probeOk) .. ", ret=" .. tostring(probeResult))

local probeFile = io.open(probePath, "r")
local probeText = nil
if probeFile ~= nil then
    probeText = probeFile:read("*a")
    probeFile:close()
end
logMessage("Python probe marker=" .. tostring(probeText))

if not probeOk or probeText == nil or probeText == "" then
    showDialog(
        "OpenRoto Python Error",
        "DaVinci Resolve could not initialise Python 3. OpenRoto now ships its own Python runtime, but Resolve has not loaded it.\n\nFully quit Resolve (including any remaining Resolve/Fusion processes), reinstall OpenRoto, and start Resolve again.\n\nDiagnostic log: %LOCALAPPDATA%\\OpenRoto\\launcher.log",
        true
    )
    error("Resolve Python 3 probe failed. FUSION_Python3_Home=" .. runtimeDir)
end

local bridgeDir = appData .. [[\Blackmagic Design\DaVinci Resolve\Support\OpenRoto]]
local bridgePath = bridgeDir .. [[\OpenRoto.py3]]
local bridgeSourcePath = bridgeDir .. [[\OpenRotoBridge.py]]
logMessage("bridge bootstrap=" .. bridgePath .. ", exists=" .. tostring(fileExists(bridgePath)))
logMessage("bridge source=" .. bridgeSourcePath .. ", exists=" .. tostring(fileExists(bridgeSourcePath)))

if not fileExists(bridgePath) or not fileExists(bridgeSourcePath) then
    showDialog(
        "OpenRoto Error",
        "The OpenRoto Resolve bridge is missing or incomplete. Reinstall OpenRoto and restart DaVinci Resolve.",
        true
    )
    error("OpenRoto bridge files missing in " .. bridgeDir)
end

logMessage("OpenRoto launcher: running diagnostic Python 3 bridge " .. bridgePath)
local runOk, runResult = pcall(function()
    return fusionHost:RunScript(bridgePath)
end)
logMessage("fusionHost:RunScript result: ok=" .. tostring(runOk) .. ", ret=" .. tostring(runResult))

if not runOk or runResult == false then
    showDialog(
        "OpenRoto Error",
        "DaVinci Resolve could not start the OpenRoto Python 3 bridge.\n\nCheck these logs:\n%LOCALAPPDATA%\\OpenRoto\\launcher.log\n%LOCALAPPDATA%\\OpenRoto\\bridge-bootstrap.log\n%LOCALAPPDATA%\\OpenRoto\\bridge-console.log",
        true
    )
    error("OpenRoto Python 3 bridge failed to start: " .. tostring(runResult))
end

logMessage("OpenRoto.lua launcher finished normally")
