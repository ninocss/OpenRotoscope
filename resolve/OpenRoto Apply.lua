-- Apply a matte rendered by the OpenRoto Free handoff.
--
-- Resolve Free 21.1+ can execute Workspace Lua scripts but blocks Python and
-- ordinary filesystem/process APIs. This script therefore reads all session
-- metadata from Fusion application data and lets Resolve import the .comp file
-- produced by the external OpenRoto companion.

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

local stageKey = "OpenRoto.ApplyStage"
local errorKey = "OpenRoto.ApplyError"

local function setData(key, value)
    if fusionHost == nil then return false end
    local ok = pcall(function() fusionHost:SetData(key, value) end)
    return ok
end

local function fail(message)
    local text = tostring(message)
    setData(stageKey, "failed: " .. text)
    setData(errorKey, text)
    if type(print) == "function" then pcall(print, "[OpenRoto Apply] ERROR: " .. text) end
    error("OpenRoto Apply: " .. text)
end

local function getData(key)
    if fusionHost == nil then return nil end
    local ok, value = pcall(function() return fusionHost:GetData(key) end)
    if ok then return value end
    return nil
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

setData(errorKey, nil)
setData(stageKey, "entered")

if resolveHost == nil or fusionHost == nil then
    fail("DaVinci Resolve did not expose the scripting host.")
end

local sessionId = getData("OpenRoto.Free.SessionId")
local timelineId = getData("OpenRoto.Free.TimelineId")
local clipId = getData("OpenRoto.Free.ClipId")
local recordStart = tonumber(getData("OpenRoto.Free.RecordStart"))
local recordEnd = tonumber(getData("OpenRoto.Free.RecordEnd"))
local linkedIds = tostring(getData("OpenRoto.Free.LinkedIds") or "")
local compPath = getData("OpenRoto.Free.CompPath")
local snapshotPath = getData("OpenRoto.Free.SnapshotPath")

if sessionId == nil or timelineId == nil or clipId == nil or compPath == nil then
    fail("No Resolve Free OpenRoto session is waiting to be applied. Start OpenRoto on a clip first.")
end

local manager = resolveHost:GetProjectManager()
local project = manager and manager:GetCurrentProject() or nil
if project == nil then fail("Open the Resolve project that contains the OpenRoto session.") end
local timeline = project:GetCurrentTimeline()
if timeline == nil then fail("Open the original Resolve timeline before applying OpenRoto.") end
if tostring(timeline:GetUniqueId()) ~= tostring(timelineId) then
    fail("Return to the original timeline before applying the OpenRoto matte.")
end

setData(stageKey, "validating-target:" .. tostring(sessionId))
local target = findClipById(timeline, clipId)
if target == nil then fail("The original OpenRoto clip is no longer present on this timeline.") end
if tonumber(target:GetStart()) ~= recordStart or tonumber(target:GetEnd()) ~= recordEnd then
    fail("The OpenRoto clip was moved or trimmed. Start a new OpenRoto session for this clip.")
end
if linkedIdString(target) ~= linkedIds then
    fail("The clip's linked items changed while OpenRoto was open. Start a new session.")
end

local linked = {}
local okLinked, linkedItems = pcall(function() return target:GetLinkedItems() end)
if okLinked and type(linkedItems) == "table" then
    for _, item in pairs(linkedItems) do
        local okType, itemType = pcall(function() return item:GetType() end)
        local okStart, itemStart = pcall(function() return item:GetStart() end)
        local okEnd, itemEnd = pcall(function() return item:GetEnd() end)
        if okType and okStart and okEnd and tostring(itemType) == "audio" and
           tonumber(itemStart) == recordStart and tonumber(itemEnd) == recordEnd then
            table.insert(linked, item)
        end
    end
end

local compoundItems = { target }
for _, item in ipairs(linked) do table.insert(compoundItems, item) end

setData(stageKey, "creating-compound:" .. tostring(sessionId))
local compound = timeline:CreateCompoundClip(compoundItems, { name = "OpenRoto" })
if compound == nil then fail("Resolve could not create the OpenRoto compound clip.") end

setData(stageKey, "importing-comp:" .. tostring(sessionId))
local importOk, composition = pcall(function() return compound:ImportFusionComp(tostring(compPath)) end)
if not importOk or composition == nil then
    local restored = false
    if snapshotPath ~= nil then restored = restoreSnapshot(project, timeline, tostring(snapshotPath)) end
    if restored then
        fail("Resolve could not import the OpenRoto Fusion composition. The safety timeline snapshot was restored.")
    else
        fail("Resolve could not import the OpenRoto Fusion composition. The safety snapshot remains in the OpenRoto session folder.")
    end
end

pcall(function() compound:SetClipColor("Sky") end)
setData("OpenRoto.Free.LastApplied", tostring(sessionId))
setData(stageKey, "completed:" .. tostring(sessionId))
setData(errorKey, nil)
if type(print) == "function" then pcall(print, "[OpenRoto Apply] completed " .. tostring(sessionId)) end
