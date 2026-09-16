-- OpenRoto menu entry for DaVinci Resolve Free and Studio.

local ffi_ok, ffi = pcall(require, "ffi")
if ffi_ok then
    pcall(function()
        ffi.cdef[[
            int MessageBoxA(void* hWnd, const char* lpText, const char* lpCaption, unsigned int uType);
        ]]
    end)
end

local function logMessage(message)
    local localData = os.getenv("LOCALAPPDATA")
    if localData == nil or localData == "" then
        local userProfile = os.getenv("USERPROFILE")
        if userProfile == nil or userProfile == "" then
            return
        end
        localData = userProfile .. "\\AppData\\Local"
    end
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
    if ffi_ok and ffi.C and ffi.C.MessageBoxA then
        ffi.C.MessageBoxA(nil, tostring(text), tostring(title), flag)
    else
        pcall(function()
            local safeText = string.gsub(text, '"', "'")
            local safeTitle = string.gsub(title, '"', "'")
            local cmd = 'powershell -NoProfile -WindowStyle Hidden -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show(\\"'
                .. safeText
                .. '\\", \\"'
                .. safeTitle
                .. '\\")" 2>nul'
            os.execute(cmd)
        end)
    end
end

logMessage("=== OpenRoto.lua launcher invoked ===")

local appData = os.getenv("APPDATA")
if appData == nil or appData == "" then
    showDialog("OpenRoto Error", "Could not locate APPDATA.", true)
    error("OpenRoto could not locate APPDATA.")
end

local resolveHost = resolve
if resolveHost == nil and rawget(_G, "Resolve") ~= nil then
    local ok, value = pcall(rawget(_G, "Resolve"))
    if ok then resolveHost = value end
end

local fusionHost = fusion or fu or app
if fusionHost == nil and resolveHost ~= nil and type(resolveHost.Fusion) == "function" then
    local ok, value = pcall(function() return resolveHost:Fusion() end)
    if ok then fusionHost = value end
end
if fusionHost == nil and rawget(_G, "Fusion") ~= nil then
    local ok, value = pcall(rawget(_G, "Fusion"))
    if ok then fusionHost = value end
end

logMessage("resolveHost=" .. tostring(resolveHost) .. ", fusionHost=" .. tostring(fusionHost))

-- The .py3 extension is intentional: Resolve/Fusion uses it to select Python 3
-- while keeping the bridge inside Resolve's internal scripting context.
local bridgePath = appData .. [[\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py3]]

local bridgeFile = io.open(bridgePath, "r")
if bridgeFile == nil then
    showDialog(
        "OpenRoto Error",
        "The OpenRoto Resolve bridge is missing. Reinstall OpenRoto and restart DaVinci Resolve.",
        true
    )
    error("OpenRoto bridge not found: " .. bridgePath)
end
bridgeFile:close()

logMessage("OpenRoto launcher: running Python 3 bridge " .. bridgePath)

if fusionHost == nil then
    showDialog(
        "OpenRoto Error",
        "DaVinci Resolve did not expose the Fusion scripting host. Restart Resolve and try again.",
        true
    )
    error("OpenRoto could not access the Fusion scripting host.")
end

local runOk, runResult = pcall(function()
    return fusionHost:RunScript(bridgePath)
end)
logMessage("fusionHost:RunScript result: ok=" .. tostring(runOk) .. ", ret=" .. tostring(runResult))

if not runOk or runResult == false then
    showDialog(
        "OpenRoto Error",
        "DaVinci Resolve could not start the OpenRoto Python 3 bridge. Check %LOCALAPPDATA%\\OpenRoto\\launcher.log for details.",
        true
    )
    error("OpenRoto Python 3 bridge failed to start: " .. tostring(runResult))
end
