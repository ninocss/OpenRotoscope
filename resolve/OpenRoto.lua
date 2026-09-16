-- OpenRoto menu entry for DaVinci Resolve Free and Studio.
--
-- IMPORTANT: Resolve 21.1 can execute Workspace Lua scripts in a restricted
-- environment where io/package/require/process execution are unavailable. Keep
-- this launcher deliberately small and do not touch the filesystem from Lua.
-- Once Python starts, OpenRoto's diagnostic bootstrap owns file logging and all
-- filesystem/process work.

local function safePrint(message)
    if type(print) == "function" then
        pcall(print, "[OpenRoto] " .. tostring(message))
    end
end

local function fail(message)
    safePrint("ERROR: " .. tostring(message))
    error("OpenRoto: " .. tostring(message))
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

local resolveHost = resolveGlobal("resolve") or resolveGlobal("Resolve")
local fusionHost = resolveGlobal("fusion") or resolveGlobal("fu") or resolveGlobal("app")

if fusionHost == nil and resolveHost ~= nil then
    local ok, value = pcall(function() return resolveHost:Fusion() end)
    if ok then fusionHost = value end
end
if fusionHost == nil then
    fusionHost = resolveGlobal("Fusion")
end

local function getEnv(name)
    if os ~= nil and type(os.getenv) == "function" then
        local ok, value = pcall(os.getenv, name)
        if ok and value ~= nil and value ~= "" then return value end
    end
    if fusionHost ~= nil then
        local ok, value = pcall(function() return fusionHost:GetEnv(name) end)
        if ok and value ~= nil and value ~= "" then return value end
    end
    return nil
end

local function safeResolveValue(methodName)
    if resolveHost == nil then return nil end
    local ok, value = pcall(function()
        return resolveHost[methodName](resolveHost)
    end)
    if ok then return value end
    return nil
end

local productName = safeResolveValue("GetProductName")
local versionString = safeResolveValue("GetVersionString")
safePrint("launcher invoked; product=" .. tostring(productName) .. ", version=" .. tostring(versionString))
safePrint("fusion host=" .. tostring(fusionHost))

if fusionHost == nil then
    fail("DaVinci Resolve did not expose the Fusion scripting host.")
end

local appData = getEnv("APPDATA")
if appData == nil then
    fail("APPDATA is unavailable in the Resolve scripting environment.")
end

local runtimeHome = getEnv("FUSION_Python3_Home")
safePrint("FUSION_Python3_Home=" .. tostring(runtimeHome))
if runtimeHome == nil then
    fail(
        "The OpenRoto Python runtime is not configured. Reinstall the newest " ..
        "OpenRoto build, fully quit DaVinci Resolve, then start Resolve again."
    )
end

-- SetData/GetData are Fusion application data, not arbitrary filesystem I/O.
-- They let Lua confirm that the Python bootstrap actually executed without
-- relying on io.open/os.remove marker files, which are blocked by Resolve's
-- Workspace-script sandbox.
local markerKey = "OpenRoto.BootstrapStatus"
pcall(function() fusionHost:SetData(markerKey, nil) end)

local bridgePath = appData .. [[\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py3]]
safePrint("starting Python bridge: " .. bridgePath)

local runOk, runResult = pcall(function()
    return fusionHost:RunScript(bridgePath)
end)
safePrint("RunScript finished; ok=" .. tostring(runOk) .. ", result=" .. tostring(runResult))

if not runOk then
    fail("Resolve could not execute the OpenRoto Python bridge: " .. tostring(runResult))
end
if runResult == false then
    fail("Resolve rejected the OpenRoto Python bridge.")
end

local markerOk, markerValue = pcall(function()
    return fusionHost:GetData(markerKey)
end)
safePrint("Python bootstrap marker: ok=" .. tostring(markerOk) .. ", value=" .. tostring(markerValue))

if not markerOk or markerValue == nil or markerValue == "" then
    local editionHint = ""
    if productName == "DaVinci Resolve" then
        editionHint =
            " This is DaVinci Resolve Free; recent Resolve versions restrict " ..
            "Workspace-script access to Python and operating-system APIs more " ..
            "aggressively than Studio."
    end
    fail(
        "The Lua launcher ran, but the Python bootstrap never executed." ..
        editionHint ..
        " Check whether your Resolve edition/version permits internal Python " ..
        "scripts, then reinstall OpenRoto and fully restart Resolve."
    )
end

if string.sub(tostring(markerValue), 1, 7) == "failed:" then
    fail("The Python bootstrap failed: " .. tostring(markerValue))
end

safePrint("launcher finished with Python status=" .. tostring(markerValue))
