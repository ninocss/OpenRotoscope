-- OpenRoto menu entry for DaVinci Resolve Free and Studio.
--
-- Studio keeps the in-process Python bridge. Resolve Free 21.1+ runs this Lua
-- launcher in a restricted sandbox that can use Resolve's application/render
-- APIs but cannot start Python or external processes. Free therefore renders
-- the selected clip into OpenRoto's fixed exchange folder; the installed
-- OpenRoto Free agent notices the frames and opens the normal UI. The launcher
-- stays alive and waits for a dofile() control signal so Render & Apply can
-- complete without a second Workspace > Scripts action.

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
if fusionHost == nil then fusionHost = resolveGlobal("Fusion") end

local stageKey = "OpenRoto.LauncherStage"
local errorKey = "OpenRoto.LauncherError"
local countKey = "OpenRoto.LauncherCount"
local launchCount = 0

local function setData(key, value)
    if fusionHost == nil then return false end
    local ok = pcall(function() fusionHost:SetData(key, value) end)
    return ok
end

if fusionHost ~= nil then
    pcall(function()
        launchCount = tonumber(fusionHost:GetData(countKey)) or 0
        launchCount = launchCount + 1
        fusionHost:SetData(countKey, launchCount)
        fusionHost:SetData(errorKey, nil)
        fusionHost:SetData(stageKey, "lua-entered #" .. tostring(launchCount))
    end)
end

local function setStage(stage)
    local value = tostring(stage)
    if launchCount > 0 then value = value .. " #" .. tostring(launchCount) end
    setData(stageKey, value)
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
            { ID = "OpenRotoMessage", WindowTitle = tostring(title), Geometry = { 300, 220, 620, 190 } },
            ui:VGroup {
                ui:Label { ID = "Message", Text = tostring(message), WordWrap = true },
                ui:Button { ID = "OK", Text = "OK" },
            }
        )
        if win == nil then return end
        function win.On.OpenRotoMessage.Close(ev) disp:ExitLoop() end
        function win.On.OK.Clicked(ev) disp:ExitLoop() end
        win:Show()
        shown = true
        disp:RunLoop()
        win:Hide()
    end)
    return ok and shown
end

local function fail(message)
    local text = tostring(message)
    setData(errorKey, text)
    setStage("failed: " .. text)
    safePrint("ERROR: " .. text)
    showDialog("OpenRoto — Startfehler", text)
    error("OpenRoto: " .. text)
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
    local ok, value = pcall(function() return resolveHost[methodName](resolveHost) end)
    if ok then return value end
    return nil
end

local function asNumber(value, fallback)
    if value == nil then return fallback end
    local cleaned = string.gsub(tostring(value), ",", ".")
    return tonumber(cleaned) or fallback
end

local function safeId(value)
    local cleaned = string.gsub(tostring(value or ""), "[^A-Za-z0-9-]", "")
    if #cleaned > 20 then cleaned = string.sub(cleaned, 1, 20) end
    if #cleaned < 4 then cleaned = "clip" .. cleaned end
    return cleaned
end

local function waitBriefly()
    if bmdHost ~= nil then
        local ok = pcall(function() bmdHost.wait(0.10) end)
        if ok then return end
    end
    if os ~= nil and type(os.clock) == "function" then
        local started = os.clock()
        while os.clock() - started < 0.10 do end
    end
end

local function getSetting(project, timeline, name, fallback)
    local ok, value = pcall(function() return timeline:GetSetting(name) end)
    if ok and value ~= nil and tostring(value) ~= "" then return value end
    ok, value = pcall(function() return project:GetSetting(name) end)
    if ok and value ~= nil and tostring(value) ~= "" then return value end
    return fallback
end

local function findTrackIndex(timeline, target)
    local ok, first, second = pcall(function() return target:GetTrackTypeAndIndex() end)
    if ok then
        if type(first) == "table" then
            local index = tonumber(first[2] or first.trackIndex or first.index)
            if index ~= nil and index >= 1 then return index end
        elseif tostring(first) == "video" then
            local index = tonumber(second)
            if index ~= nil and index >= 1 then return index end
        end
    end

    local targetId = tostring(target:GetUniqueId())
    local count = tonumber(timeline:GetTrackCount("video")) or 0
    for trackIndex = 1, count do
        local items = timeline:GetItemListInTrack("video", trackIndex) or {}
        for _, item in pairs(items) do
            local itemOk, itemId = pcall(function() return item:GetUniqueId() end)
            if itemOk and tostring(itemId) == targetId then return trackIndex end
        end
    end
    return 0
end

local function linkedIdString(target)
    local ids = {}
    local ok, linked = pcall(function() return target:GetLinkedItems() end)
    if ok and type(linked) == "table" then
        for _, item in pairs(linked) do
            local idOk, id = pcall(function() return item:GetUniqueId() end)
            if idOk and id ~= nil then table.insert(ids, tostring(id)) end
        end
    end
    table.sort(ids)
    return table.concat(ids, ",")
end

local function findClipById(timeline, clipId)
    local tracks = tonumber(timeline:GetTrackCount("video")) or 0
    for trackIndex = 1, tracks do
        local items = timeline:GetItemListInTrack("video", trackIndex) or {}
        for _, item in pairs(items) do
            local ok, id = pcall(function() return item:GetUniqueId() end)
            if ok and tostring(id) == tostring(clipId) then return item end
        end
    end
    return nil
end

local function restoreSnapshot(project, timeline, snapshotPath)
    local mediaPool = project:GetMediaPool()
    if mediaPool == nil then return false end
    local ok, restored = pcall(function() return mediaPool:ImportTimelineFromFile(snapshotPath) end)
    if not ok or restored == nil then return false end
    local oldName = tostring(timeline:GetName())
    pcall(function() timeline:SetName("__OpenRoto failed") end)
    pcall(function() restored:SetName(oldName) end)
    pcall(function() project:SetCurrentTimeline(restored) end)
    pcall(function() mediaPool:DeleteTimelines({ timeline }) end)
    return true
end

local function pickPngCodec(project)
    local formats = project:GetRenderFormats() or {}
    for formatName, extension in pairs(formats) do
        if string.lower(string.gsub(tostring(extension), "^%.", "")) == "png" then
            local codecs = project:GetRenderCodecs(extension) or project:GetRenderCodecs(formatName) or {}
            local fallback = nil
            for codecName, codecId in pairs(codecs) do
                if fallback == nil then fallback = codecId end
                if not string.find(string.lower(tostring(codecName)), "16", 1, true) then
                    return tostring(extension), codecId
                end
            end
            if fallback ~= nil then return tostring(extension), fallback end
        end
    end
    error("Resolve exposes no PNG image-sequence renderer.")
end

local function freeExport()
    setStage("free-context")
    if resolveHost == nil then error("Resolve application object is unavailable.") end
    if type(dofile) ~= "function" then
        error("Resolve Free does not expose dofile(), which OpenRoto needs for automatic apply.")
    end
    local manager = resolveHost:GetProjectManager()
    local project = manager and manager:GetCurrentProject() or nil
    if project == nil then error("Open a Resolve project before starting OpenRoto.") end
    local timeline = project:GetCurrentTimeline()
    if timeline == nil then error("Open a timeline before starting OpenRoto.") end
    local target = timeline:GetCurrentVideoItem()
    if target == nil then error("Place the playhead over the video clip you want to mask.") end

    local targetId = tostring(target:GetUniqueId())
    local trackIndex = findTrackIndex(timeline, target)
    if trackIndex < 1 then error("Could not determine the selected clip's video track.") end
    local startFrame = math.floor(asNumber(target:GetStart(), 0))
    local endFrame = math.floor(asNumber(target:GetEnd(), 0))
    local frameCount = endFrame - startFrame
    if frameCount < 1 then error("The selected clip has no renderable frames.") end

    local width = math.floor(asNumber(getSetting(project, timeline, "timelineResolutionWidth", 1920), 1920))
    local height = math.floor(asNumber(getSetting(project, timeline, "timelineResolutionHeight", 1080), 1080))
    local fps = asNumber(
        getSetting(project, timeline, "timelineFrameRate", getSetting(project, timeline, "timelinePlaybackFrameRate", 24)),
        24
    )
    local fps1000 = math.floor(fps * 1000 + 0.5)
    local sessionId = safeId(targetId) .. "-" .. tostring(launchCount)

    local localData = getEnv("LOCALAPPDATA")
    if localData == nil then error("LOCALAPPDATA is unavailable in Resolve Free.") end
    local exchangeDir = localData .. [[\OpenRoto\FreeExchange]]
    local sessionDir = localData .. [[\OpenRoto\Sessions\]] .. sessionId
    local prefix = "OpenRotoFree_" .. sessionId ..
        "_n" .. tostring(frameCount) ..
        "_w" .. tostring(width) ..
        "_h" .. tostring(height) ..
        "_f" .. tostring(fps1000)
    local snapshotPath = exchangeDir .. "\\OpenRotoFree_" .. sessionId .. ".drt"
    local finalSnapshotPath = sessionDir .. [[\backup.drt]]
    local matteDir = sessionDir .. [[\matte]]
    local compPath = matteDir .. [[\OpenRoto.comp]]
    local controlPath = matteDir .. [[\CONTROL.lua]]
    local appliedAckPath = matteDir .. [[\APPLIED.drt]]
    local failedAckPath = matteDir .. [[\APPLY_FAILED.drt]]
    local originalLinkedIds = linkedIdString(target)

    setData("OpenRoto.Free.SessionId", sessionId)
    setData("OpenRoto.Free.TimelineId", tostring(timeline:GetUniqueId()))
    setData("OpenRoto.Free.ClipId", targetId)
    setData("OpenRoto.Free.RecordStart", startFrame)
    setData("OpenRoto.Free.RecordEnd", endFrame)
    setData("OpenRoto.Free.TrackIndex", trackIndex)
    setData("OpenRoto.Free.LinkedIds", originalLinkedIds)
    setData("OpenRoto.Free.CompPath", compPath)
    setData("OpenRoto.Free.SnapshotPath", finalSnapshotPath)
    setData("OpenRoto.Free.FrameCount", frameCount)

    setStage("free-snapshot")
    local snapshotOk, snapshotResult = pcall(function()
        return timeline:Export(snapshotPath, resolveHost.EXPORT_DRT, resolveHost.EXPORT_NONE)
    end)
    if not snapshotOk or snapshotResult == false then
        error("Resolve could not create the OpenRoto safety snapshot.")
    end

    local presetName = "__OpenRotoFree_" .. sessionId
    local temporaryTimeline = nil
    local jobId = nil
    local savedPreset = false
    local originalTimeline = timeline

    local function cleanup()
        if jobId ~= nil then pcall(function() project:DeleteRenderJob(jobId) end) end
        pcall(function() project:SetCurrentTimeline(originalTimeline) end)
        if temporaryTimeline ~= nil then
            pcall(function() project:GetMediaPool():DeleteTimelines({ temporaryTimeline }) end)
        end
        if savedPreset then
            pcall(function()
                project:LoadRenderPreset(presetName)
                project:DeleteRenderPreset(presetName)
            end)
        end
    end

    local renderOk, renderError = pcall(function()
        setStage("free-render-setup")
        savedPreset = project:SaveAsNewRenderPreset(presetName) == true
        if not savedPreset then error("Resolve could not snapshot its current render settings.") end

        temporaryTimeline = timeline:DuplicateTimeline("__OpenRoto Free Export " .. tostring(launchCount))
        if temporaryTimeline == nil then error("Resolve could not duplicate the timeline for export.") end
        if project:SetCurrentTimeline(temporaryTimeline) == false then
            error("Resolve could not activate the isolated export timeline.")
        end

        local videoTracks = tonumber(temporaryTimeline:GetTrackCount("video")) or 0
        for index = 1, videoTracks do
            temporaryTimeline:SetTrackEnable("video", index, index == trackIndex)
        end
        local audioTracks = tonumber(temporaryTimeline:GetTrackCount("audio")) or 0
        for index = 1, audioTracks do temporaryTimeline:SetTrackEnable("audio", index, false) end

        local formatId, codecId = pickPngCodec(project)
        if project:SetCurrentRenderFormatAndCodec(formatId, codecId) == false then
            error("Resolve rejected the PNG image-sequence format.")
        end
        project:SetCurrentRenderMode(1)
        if project:SetRenderSettings({
            SelectAllFrames = false,
            MarkIn = startFrame,
            MarkOut = endFrame - 1,
            TargetDir = exchangeDir,
            CustomName = prefix,
            UseUniqueFilenames = false,
            ExportVideo = true,
            ExportAudio = false,
        }) == false then
            error("Resolve rejected the OpenRoto render range.")
        end

        jobId = project:AddRenderJob()
        if jobId == nil or jobId == "" then error("Resolve could not add the OpenRoto render job.") end
        setStage("free-rendering")
        if project:StartRendering({ jobId }, false) == false then
            error("Resolve could not start the OpenRoto frame export.")
        end

        local iterations = 0
        while project:IsRenderingInProgress() do
            iterations = iterations + 1
            if iterations > 432000 then
                pcall(function() project:StopRendering() end)
                error("OpenRoto frame export timed out.")
            end
            waitBriefly()
        end
        local status = project:GetRenderJobStatus(jobId) or {}
        local jobStatus = tostring(status.JobStatus or status["JobStatus"] or "")
        if jobStatus ~= "Complete" then
            local detail = tostring(status.Error or status["Error"] or jobStatus or "unknown render error")
            error("Resolve frame export failed: " .. detail)
        end
    end)

    cleanup()
    if not renderOk then error(renderError) end

    setData("OpenRoto.Free.ExportPrefix", prefix)
    setStage("free-export-ready:" .. sessionId)
    safePrint("Resolve Free export ready for OpenRoto agent: " .. sessionId)

    return {
        sessionId = sessionId,
        project = project,
        timeline = timeline,
        timelineId = tostring(timeline:GetUniqueId()),
        clipId = targetId,
        recordStart = startFrame,
        recordEnd = endFrame,
        linkedIds = originalLinkedIds,
        compPath = compPath,
        snapshotPath = finalSnapshotPath,
        controlPath = controlPath,
        appliedAckPath = appliedAckPath,
        failedAckPath = failedAckPath,
    }
end

local function applyFreeSession(context)
    local project = context.project
    local timeline = project:GetCurrentTimeline()
    if timeline == nil then error("Open the original Resolve timeline before applying OpenRoto.") end
    if tostring(timeline:GetUniqueId()) ~= tostring(context.timelineId) then
        error("Return to the original timeline before applying the OpenRoto matte.")
    end

    setStage("free-validating-target:" .. tostring(context.sessionId))
    local target = findClipById(timeline, context.clipId)
    if target == nil then error("The original OpenRoto clip is no longer present on this timeline.") end
    if tonumber(target:GetStart()) ~= context.recordStart or tonumber(target:GetEnd()) ~= context.recordEnd then
        error("The OpenRoto clip was moved or trimmed while OpenRoto was open.")
    end
    if linkedIdString(target) ~= context.linkedIds then
        error("The clip's linked items changed while OpenRoto was open.")
    end

    local linked = {}
    local okLinked, linkedItems = pcall(function() return target:GetLinkedItems() end)
    if okLinked and type(linkedItems) == "table" then
        for _, item in pairs(linkedItems) do
            local okType, itemType = pcall(function() return item:GetType() end)
            local okStart, itemStart = pcall(function() return item:GetStart() end)
            local okEnd, itemEnd = pcall(function() return item:GetEnd() end)
            if okType and okStart and okEnd and string.lower(tostring(itemType)) == "audio" and
               tonumber(itemStart) == context.recordStart and tonumber(itemEnd) == context.recordEnd then
                table.insert(linked, item)
            end
        end
    end

    local compoundItems = { target }
    for _, item in ipairs(linked) do table.insert(compoundItems, item) end

    setStage("free-creating-compound:" .. tostring(context.sessionId))
    local compound = timeline:CreateCompoundClip(compoundItems, { name = "OpenRoto" })
    if compound == nil then error("Resolve could not create the OpenRoto compound clip.") end

    setStage("free-importing-comp:" .. tostring(context.sessionId))
    local importOk, composition = pcall(function()
        return compound:ImportFusionComp(tostring(context.compPath))
    end)
    if not importOk or composition == nil then
        local restored = restoreSnapshot(project, timeline, tostring(context.snapshotPath))
        if restored then
            error("Resolve could not import the OpenRoto Fusion composition; the safety timeline snapshot was restored.")
        end
        error("Resolve could not import the OpenRoto Fusion composition; the safety snapshot remains in the session folder.")
    end

    pcall(function() compound:SetClipColor("Sky") end)
    setData("OpenRoto.Free.LastApplied", tostring(context.sessionId))
    setStage("free-confirming-apply:" .. tostring(context.sessionId))
    local ackOk, ackResult = pcall(function()
        return timeline:Export(tostring(context.appliedAckPath), resolveHost.EXPORT_DRT, resolveHost.EXPORT_NONE)
    end)
    if not ackOk or ackResult == false then
        error("The matte was applied, but Resolve could not write the completion acknowledgement.")
    end
    setStage("free-apply-completed:" .. tostring(context.sessionId))
    setData(errorKey, nil)
end

local function waitForFreeControl(context)
    setStage("free-waiting-apply:" .. tostring(context.sessionId))
    local expectedApply = "openroto-free-apply:" .. tostring(context.sessionId)
    local expectedCancel = "openroto-free-cancel:" .. tostring(context.sessionId)
    local iterations = 0

    while true do
        iterations = iterations + 1
        if iterations > 432000 then
            error("OpenRoto Free session timed out while waiting for Render & Apply.")
        end

        local controlOk, controlValue = pcall(dofile, tostring(context.controlPath))
        if controlOk then
            local token = tostring(controlValue or "")
            if token == expectedCancel then
                setStage("free-cancelled:" .. tostring(context.sessionId))
                return
            end
            if token == expectedApply then
                setStage("free-apply-requested:" .. tostring(context.sessionId))
                local applyOk, applyError = pcall(function() applyFreeSession(context) end)
                if not applyOk then
                    pcall(function()
                        context.timeline:Export(
                            tostring(context.failedAckPath),
                            resolveHost.EXPORT_DRT,
                            resolveHost.EXPORT_NONE
                        )
                    end)
                    error(applyError)
                end
                return
            end
        end
        waitBriefly()
    end
end

local productName = safeResolveValue("GetProductName")
local versionString = safeResolveValue("GetVersionString")
safePrint("launcher invoked; product=" .. tostring(productName) .. ", version=" .. tostring(versionString))

if fusionHost == nil then error("OpenRoto: DaVinci Resolve did not expose the Fusion scripting host.") end
setStage("fusion-host-ready")

-- Resolve Free 21.1+ does not execute Python utility scripts. Keep all Resolve
-- interaction in this Lua invocation. The external app sends apply/cancel via
-- a tiny dofile() control script in the unique session directory.
if tostring(productName) == "DaVinci Resolve" then
    local exportOk, contextOrError = pcall(freeExport)
    if not exportOk then fail("DaVinci Resolve Free export failed: " .. tostring(contextOrError)) end
    local waitOk, waitError = pcall(function() waitForFreeControl(contextOrError) end)
    if not waitOk then fail("DaVinci Resolve Free apply failed: " .. tostring(waitError)) end
    return
end

-- Studio path: preserve the existing in-process Python bridge and automatic
-- round-trip apply behavior.
local appData = getEnv("APPDATA")
if appData == nil then fail("APPDATA is unavailable in the Resolve scripting environment.") end
setStage("appdata-ready")

local runtimeHome = getEnv("FUSION_Python3_Home")
safePrint("FUSION_Python3_Home=" .. tostring(runtimeHome))
if runtimeHome == nil then
    fail("Die OpenRoto-Python-Runtime ist in Resolve nicht konfiguriert. Installiere den neuesten Build und beende Resolve danach vollständig.")
end
setStage("python-home-ready")

local markerKey = "OpenRoto.BootstrapStatus"
pcall(function() fusionHost:SetData(markerKey, nil) end)
local bridgePath = appData .. [[\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py3]]
setStage("python-runscript-requested")
local runOk, runResult = pcall(function() return fusionHost:RunScript(bridgePath) end)
setStage("python-runscript-returned ok=" .. tostring(runOk) .. " result=" .. tostring(runResult))
if not runOk then fail("Resolve konnte die OpenRoto-Python-Bridge nicht ausführen: " .. tostring(runResult)) end
if runResult == false then fail("Resolve hat die OpenRoto-Python-Bridge abgelehnt.") end

local markerOk, markerValue = pcall(function() return fusionHost:GetData(markerKey) end)
setStage("bootstrap-status ok=" .. tostring(markerOk) .. " value=" .. tostring(markerValue))
if not markerOk or markerValue == nil or markerValue == "" then
    fail("Der Lua-Launcher wurde ausgeführt, aber die Studio-Python-Bridge ist nie gestartet. Installiere den neuesten Build und starte Resolve vollständig neu.")
end
if string.sub(tostring(markerValue), 1, 7) == "failed:" then
    fail("Die Python-Bridge ist fehlgeschlagen: " .. tostring(markerValue))
end
setStage("launcher-finished status=" .. tostring(markerValue))
