-- OpenRoto menu entry for DaVinci Resolve Free and Studio.
--
-- Resolve can execute Workspace Lua scripts in a restricted environment where
-- io/package/require/process execution are unavailable. Keep this launcher
-- filesystem-free. Once Python starts, OpenRoto's diagnostic bootstrap owns
-- file logging and all filesystem/process work.

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
local bmdHost = resolveGlobal("bmd")

if fusionHost == nil and resolveHost ~= nil then
    local ok, value = pcall(function() return resolveHost:Fusion() end)
    if ok then fusionHost = value end
end
if fusionHost == nil then
    fusionHost = resolveGlobal("Fusion")
end

local function safePrint(message)
    if type(print) == "function" then
        pcall(print, "[OpenRoto] " .. tostring(message))
    end
end

local function showDialog(title, message)
    if fusionHost == nil or bmdHost == nil then return false end
    local shown = false
    local ok = pcall(function()
        local ui = fusionHost.UIManager
        if ui == nil then return end
        local disp = bmdHost.UIDispatcher(ui)
        if disp == nil then return end
        local win = disp:AddWindow(
            {
                ID = "OpenRotoMessage",
                WindowTitle = tostring(title),
                Geometry = { 300, 220, 620, 190 },
            },
            ui:VGroup {
                ui:Label {
                    ID = "Message",
                    Text = tostring(message),
                    WordWrap = true,
                },
                ui:Button {
                    ID = "OK",
                    Text = "OK",
                },
            }
        )
        if win == nil then return end
        function win.On.OpenRotoMessage.Close(ev)
            disp:ExitLoop()
        end
        function win.On.OK.Clicked(ev)
            disp:ExitLoop()
        end
        win:Show()
        shown = true
        disp:RunLoop()
        win:Hide()
    end)
    return ok and shown
end

local function fail(message)
    safePrint("ERROR: " .. tostring(message))
    showDialog("OpenRoto — Startfehler", tostring(message))
    error("OpenRoto: " .. tostring(message))
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
        "Die OpenRoto-Python-Runtime ist in Resolve nicht konfiguriert. " ..
        "Installiere den neuesten OpenRoto-Build und beende Resolve danach vollständig."
    )
end

local markerKey = "OpenRoto.BootstrapStatus"
pcall(function() fusionHost:SetData(markerKey, nil) end)

local bridgePath = appData .. [[\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py3]]
safePrint("starting Python bridge: " .. bridgePath)

local runOk, runResult = pcall(function()
    return fusionHost:RunScript(bridgePath)
end)
safePrint("RunScript finished; ok=" .. tostring(runOk) .. ", result=" .. tostring(runResult))

if not runOk then
    fail("Resolve konnte die OpenRoto-Python-Bridge nicht ausführen: " .. tostring(runResult))
end
if runResult == false then
    fail("Resolve hat die OpenRoto-Python-Bridge abgelehnt.")
end

local markerOk, markerValue = pcall(function()
    return fusionHost:GetData(markerKey)
end)
safePrint("Python bootstrap marker: ok=" .. tostring(markerOk) .. ", value=" .. tostring(markerValue))

if not markerOk or markerValue == nil or markerValue == "" then
    local editionHint = ""
    if productName == "DaVinci Resolve" then
        editionHint =
            " Du verwendest DaVinci Resolve Free; interne Menü-Skripte sind erlaubt, " ..
            "aber Python muss von Resolve erfolgreich geladen werden."
    end
    fail(
        "Der Lua-Launcher wurde ausgeführt, aber die Python-Bridge ist nie gestartet." ..
        editionHint ..
        " Installiere den neuesten Build mit der gebündelten Python-3.10-Runtime " ..
        "und starte Resolve vollständig neu."
    )
end

if string.sub(tostring(markerValue), 1, 7) == "failed:" then
    fail("Die Python-Bridge ist fehlgeschlagen: " .. tostring(markerValue))
end

safePrint("launcher finished with Python status=" .. tostring(markerValue))
