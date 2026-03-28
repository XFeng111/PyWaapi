-- @description kusa_Wwhisper Assistant Core Functions
-- @version 1.0
-- @author Based on Kusa's kusa_Wwhisper Assistant
-- @about Encapsulates "Create new track and item" and "Generate project from Profiler TXT" functions

----------------------------------------------------------------------
-- 必要的依赖函数和变量（从原脚本提取）
----------------------------------------------------------------------

local colors = {}
if os.getenv("HOME") ~= nil then
    colors = {
        {name = "Red", value = 33226752},
        {name = "Green", value = 16830208},
        {name = "Blue", value = 16806892},
        {name = "Yellow", value = 0},
        {name = "Orange", value = 32795136},
        {name = "Purple", value = 28901614},
    }
else
    colors = {
        {name = "Red", value = 16777471},
        {name = "Green", value = 16809984},
        {name = "Blue", value = 33226752},
        {name = "Yellow", value = 16842751},
        {name = "Orange", value = 16810239},
        {name = "Purple", value = 33489151},
    }
end

local rtpcData = {}

-- 简单工具函数
-- local function print(string)
--     reaper.ShowConsoleMsg(string .. "\n")
-- end

local function tableToString(tbl, depth)
    if depth == nil then depth = 1 end
    if depth > 5 then return "..." end
    local str = "{"
    for k, v in pairs(tbl) do
        local key = tostring(k)
        local value = type(v) == "table" and tableToString(v, depth + 1) or tostring(v)
        str = str .. "[" .. key .. "] = " .. value .. ", "
    end
    str = str:sub(1, -3)
    str = str .. "}" .. "\n"
    return str
end

local function isJSFXInstalled(pluginName)
    local found = false
    local index = 0
    while true do
        local retval, name, ident = reaper.EnumInstalledFX(index)
        if not retval then break end
        if name:find(pluginName) then
            found = true
            break
        end
        index = index + 1
    end
    return found
end

----------------------------------------------------------------------
-- "Create new track and item" 相关函数
----------------------------------------------------------------------

-- 创建新轨道和MIDI项的函数
-- 参数: gameObjectName - 游戏对象名称
-- 返回: 成功创建返回true，否则返回false
local function Create_new_track_and_item(gameObjectName)
    local function handlePannerFX(track)
        local pluginName = "JS: kusa_Wwhisper Params"
        local found = isJSFXInstalled(pluginName)
        
        if found then
            local fxIndex = reaper.TrackFX_GetByName(track, pluginName, true)
            local numParams = reaper.TrackFX_GetNumParams(track, fxIndex)
            for paramIndex = 0, math.min(3, numParams) - 1 do
                local envelope = reaper.GetFXEnvelope(track, fxIndex, paramIndex, true)
            end
            return false
        else
            reaper.DeleteTrack(track)
            local userChoice = reaper.ShowMessageBox(pluginName .. " is not installed. Required for spatialisation. Visit docs?", "Error", 4)
            if userChoice == 6 then
                reaper.CF_ShellExecute("https://github.com/TFKusa/kusa_reascripts/blob/master/Documentation/WWHISPER%20-%20DOCUMENTATION.md")
            end
            return true
        end
    end

    local function pannerOnTrackSetup(track)
        reaper.SetTrackAutomationMode(track, 4) -- Latch mode
        return handlePannerFX(track)
    end

    local function handleTrackForMIDIItem(name)
        local trackIndex
        local selectedTrack = reaper.GetSelectedTrack(0, 0)
        if selectedTrack then
            trackIndex = reaper.GetMediaTrackInfo_Value(selectedTrack, "IP_TRACKNUMBER")
        else
            trackIndex = reaper.GetNumTracks()
        end
        reaper.InsertTrackAtIndex(trackIndex, true)

        local newTrack = reaper.GetTrack(0, trackIndex)
        reaper.GetSetMediaTrackInfo_String(newTrack, "P_NAME", name, true)
        local shouldStop = pannerOnTrackSetup(newTrack)
        return shouldStop, newTrack
    end

    local function getStartEndPointSelectionOrSelectedItem()
        local loopStartTime, loopEndTime = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
        local itemStart, itemEnd
        if loopStartTime == loopEndTime then
            local item = reaper.GetSelectedMediaItem(0, 0)
            if item then
                itemStart = reaper.GetMediaItemInfo_Value(item, "D_POSITION")
                local itemLength = reaper.GetMediaItemInfo_Value(item, "D_LENGTH")
                itemEnd = itemStart + itemLength
            else
                reaper.ShowMessageBox("No item selected or time selection.", "Error", 0)
                return nil, nil
            end
        else
            itemStart = loopStartTime
            itemEnd = loopEndTime
        end
        return itemStart, itemEnd
    end

    -- 核心实现
    if not gameObjectName or gameObjectName == "" then
        reaper.ShowMessageBox("Please enter a Game Object name first!", "Error", 0)
        return false
    end
    
    local itemStart, itemEnd = getStartEndPointSelectionOrSelectedItem()
    if not itemStart or not itemEnd then
        return false
    end
    
    local shouldStop, track = handleTrackForMIDIItem(gameObjectName)
    if not shouldStop then
        local midiItem = reaper.CreateNewMIDIItemInProj(track, itemStart, itemEnd, false)
        reaper.SetMediaItemInfo_Value(midiItem, "B_LOOPSRC", 0)
        print("Created track and item for: " .. gameObjectName)
        return true
    end
    return false
end

----------------------------------------------------------------------
-- "Generate project from Profiler TXT" 相关函数
----------------------------------------------------------------------

-- 从Profiler TXT文件生成项目的函数
-- 参数: filePath - 可选，TXT文件路径；如果未提供则弹出文件选择对话框
-- 返回: 成功生成返回true，否则返回false
local function Generate_project_from_Profiler_TXT(filePath)
    local function isValidLine(line)
        return not line:match("^Timestamp") and line:match("%S")
    end

    local function extractDescription(description)
        return description and description:match("\"([^\"]*)\"") or ""
    end

    local function insertResult(results, timestamp, objectType, objectName, gameObject, description, posOrValue, interpTime)
        table.insert(results, {
            timestamp = timestamp,
            objectType = objectType,
            objectName = objectName,
            gameObject = gameObject,
            description = description,
            posOrValue = posOrValue,
            interpTime = interpTime
        })
    end

    local function shouldProcessObjectPosition(description)
        return string.sub(description, 1, 11) == "SetPosition"
    end

    local function shouldProcessObjectRTPC(description)
        return string.sub(description, 1, 13) == "SetRTPCValue:"
    end

    local function shouldProcessObjectRTPCInterp(description)
        return string.sub(description, 1, 27) == "SetRTPCValueWithTransition:"
    end

    local function shouldProcessObjectInit(description)
        return string.sub(description, 1, 15) == "RegisterGameObj"
    end

    local function parsePositionGameObject(description)
        local positionsTable = {}
        local positionPattern = "Position:%(X:(%-?%d+%.?%d*),Y:(%-?%d+%.?%d*),Z:(%-?%d+%.?%d*)%)"
        local posX, posY, posZ = string.match(description, positionPattern)
        positionsTable["Position"] = {X = posX, Y = posY, Z = posZ}

        local orientationFrontPattern = "Front:%(X:(%-?%d+%.?%d*[eE]?%-?%d*),Y:(%-?%d+%.?%d*[eE]?%-?%d*),Z:(%-?%d+%.?%d*[eE]?%-?%d*)%)"
        local frontX, frontY, frontZ = string.match(description, orientationFrontPattern)
        positionsTable["OrientationFront"] = {X = frontX, Y = frontY, Z = frontZ}
        
        local orientationTopPattern = "Top:%(X:(%-?%d+%.?%d*[eE]?%-?%d*),Y:(%-?%d+%.?%d*[eE]?%-?%d*),Z:(%-?%d+%.?%d*[eE]?%-?%d*)%)"
        local topX, topY, topZ = string.match(description, orientationTopPattern)
        positionsTable["OrientationTop"] = {X = topX, Y = topY, Z = topZ}

        return positionsTable
    end

    local function parseRTPCGameObject(description)
        local rtpcPattern = "%s*(-?%d+%.?%d*)"
        return string.match(description, rtpcPattern)
    end

    local function parseRTPCInterpGameObject(description)
        local rtpcPattern = "Target Value:%s*(-?%d+%.?%d*[eE]?[+-]?%d*),%s*Over%s*(%d%d):(%d%d)%.(%d%d%d)%s*ms"
        local value, mins, secs, ms = string.match(description, rtpcPattern)
        value = tonumber(value)
        local interpTime = (tonumber(mins) * 60 + tonumber(secs)) * 1000 + tonumber(ms)
        return {value = value, interpTime = interpTime}
    end

    local function parseLogLine(line)
        local parts = {}
        for part in line:gmatch("[^\t]+") do
            table.insert(parts, part)
        end
        local gameObject = ""
        if (parts[2] == "Event" or parts[2] == "Switch" or parts[2] == "State Changed" or parts[2] == "API Call") then
            local timestamp = parts[1]
            local objectType = parts[2]
            local description = parts[3]
            local objectName = parts[4]
            if parts[2] == "State Changed" then
                gameObject = "Transport/Soundcaster"
            else
                gameObject = parts[5]
            end
            if shouldProcessObjectPosition(description) then 
                gameObject = parts[4]
            end

            if shouldProcessObjectRTPC(description) then
                if parts[7] then
                    objectType = "SetRTPCValue"
                end
            end

            if shouldProcessObjectRTPCInterp(description) then
                if parts[7] then
                    objectType = "SetRTPCValueInterp"
                end
            end

            if description:match("^\"") and description:match("\"$") then
                description = description:sub(2, -2)
            end

            return timestamp, objectType, description, objectName, gameObject
        end
        return nil
    end

    local function filterConsecutiveEntries(entries)
        local filtered = {}
        local previous = nil
        local duplicates = {}

        local function addFromDuplicates()
            if #duplicates > 0 then
                table.insert(filtered, duplicates[1])
                if #duplicates > 1 then
                    table.insert(filtered, duplicates[#duplicates])
                end
                duplicates = {}
            end
        end

        for _, entry in ipairs(entries) do
            if not previous or (previous.gameObject ~= entry.gameObject or 
              previous.posOrValue.Position.X ~= entry.posOrValue.Position.X or 
              previous.posOrValue.Position.Y ~= entry.posOrValue.Position.Y or 
              previous.posOrValue.Position.Z ~= entry.posOrValue.Position.Z or 
              previous.posOrValue.OrientationFront.X ~= entry.posOrValue.OrientationFront.X or 
              previous.posOrValue.OrientationFront.Y ~= entry.posOrValue.OrientationFront.Y or 
              previous.posOrValue.OrientationFront.Z ~= entry.posOrValue.OrientationFront.Z) then
                addFromDuplicates()
                table.insert(filtered, entry)
            else
                table.insert(duplicates, entry)
            end
            previous = entry
        end
        addFromDuplicates()

        return filtered
    end

    local function processLogFile(filePath)
        local file, err = io.open(filePath, "r")
        if not file then
            reaper.ShowMessageBox("Failed to open file: " .. err, "Error", 0)
            return nil
        end

        local results = {}
        for line in file:lines() do
            if isValidLine(line) then
                local timestamp, objectType, description, objectName, gameObject = parseLogLine(line)

                if (objectType == "Event" or objectType == "Switch" or objectType == "State Changed") then
                    local extractedDescription = extractDescription(description)
                    insertResult(results, timestamp, objectType, objectName, gameObject, extractedDescription, nil, nil)
                elseif description then
                    if shouldProcessObjectPosition(description) then
                        local positionsTable = parsePositionGameObject(description)
                        objectType = description:match("(%w+)}?")
                        insertResult(results, timestamp, objectType, nil, gameObject, nil, positionsTable, nil)
                    elseif shouldProcessObjectRTPC(description) then
                        local rtpcValue = parseRTPCGameObject(description)
                        objectType = "SetRTPCValue"
                        insertResult(results, timestamp, objectType, objectName, gameObject, nil, rtpcValue, nil)
                    elseif shouldProcessObjectRTPCInterp(description) then
                        local rtpcInterpTable = parseRTPCInterpGameObject(description)
                        objectType = "SetRTPCValueInterp"
                        insertResult(results, timestamp, objectType, objectName, gameObject, nil, rtpcInterpTable.value, rtpcInterpTable.interpTime)
                    elseif shouldProcessObjectInit(description) then
                        local pattern = "RegisterGameObj:%s([%w_%.]+)%s%(%ID:(%d+)%)"
                        gameObject, _ = string.match(description, pattern)
                        objectType = "InitObj"
                        insertResult(results, timestamp, objectType, nil, gameObject, nil, nil, nil)
                    end
                end
            end
        end
        
        file:close()
        return results
    end

    local function createTracksForGameObjects(entries)
        local uniqueGameObjects = {}
        local createdTracks = {}
        for _, entry in ipairs(entries) do
            if entry and entry.gameObject then
                uniqueGameObjects[entry.gameObject] = true
            end
        end
        for gameObjectName, _ in pairs(uniqueGameObjects) do
            local trackIndex = reaper.CountTracks(0)
            reaper.InsertTrackAtIndex(trackIndex, true)
            local track = reaper.GetTrack(0, trackIndex)

            if track then
                reaper.GetSetMediaTrackInfo_String(track, "P_NAME", gameObjectName, true)
                table.insert(createdTracks, {track = track, name = gameObjectName})
            end
        end
        return createdTracks
    end

    local function convertTimestampToSeconds(timestamp)
        local hours, minutes, seconds, milliseconds = timestamp:match("(%d+):(%d+):(%d+).(%d+)")
        hours = tonumber(hours)
        minutes = tonumber(minutes)
        seconds = tonumber(seconds)
        milliseconds = tonumber(milliseconds) / 1000
        return (hours * 3600) + (minutes * 60) + seconds + milliseconds
    end

    local function getTotalDurationInSeconds(entries)
        local minTimestampValue = math.huge
        local maxTimestampValue = -math.huge

        for _, entry in ipairs(entries) do
            local timestampValue = convertTimestampToSeconds(entry.timestamp)
            if timestampValue < minTimestampValue then
                minTimestampValue = timestampValue
            end
            if timestampValue > maxTimestampValue then
                maxTimestampValue = timestampValue
            end
        end
        return maxTimestampValue - minTimestampValue + 1, minTimestampValue
    end

    local function createMIDIItems(createdTracks, totalDurationInSeconds)
        local createdItems = {}
        for _, trackInfo in ipairs(createdTracks) do
            local track = trackInfo.track
            local newItem = reaper.CreateNewMIDIItemInProj(track, 0, totalDurationInSeconds + 1)
            reaper.SetMediaItemInfo_Value(newItem, "B_LOOPSRC", 0)
            table.insert(createdItems, {item = newItem, track = track})
        end
        return createdItems
    end

    local function getColorValue(colors, colorName)
        for _, colorInfo in ipairs(colors) do
            if colorInfo.name == colorName then
                return colorInfo.value
            end
        end
        return 0
    end

    local function filterEntriesByType(entries, objectTypeFilter, offsetInSecondsToStartProject)
        local filteredEntries = {}
        for _, entry in ipairs(entries) do
            if entry.objectType == objectTypeFilter then
                local timestampInSeconds = convertTimestampToSeconds(entry.timestamp) - offsetInSecondsToStartProject
                table.insert(filteredEntries, {
                    timestamp = timestampInSeconds, 
                    objectName = entry.objectName, 
                    gameObject = entry.gameObject, 
                    description = entry.description, 
                    posOrValue = entry.posOrValue, 
                    interpTime = entry.interpTime, 
                    initialValue = entry.initialValue, 
                    minValue = entry.minValue, 
                    maxValue = entry.maxValue
                })
            end
        end
        return filteredEntries
    end

    local function findTrackInTable(createdTracks, trackName)
        for _, trackInfo in ipairs(createdTracks) do
            if trackInfo.name == trackName then
                return trackInfo.track
            end
        end
        return nil
    end

    local function prepareForProfilerMarkers(entry, createdTracks)
        if entry.gameObject then
            local track = findTrackInTable(createdTracks, entry.gameObject)
            if not track then
                local trackIndex = reaper.CountTracks(0)
                reaper.InsertTrackAtIndex(trackIndex, true)
                track = reaper.GetTrack(0, trackIndex)
                reaper.GetSetMediaTrackInfo_String(track, "P_NAME", entry.gameObject, true)
                table.insert(createdTracks, {track = track, name = entry.gameObject})
            end
            local item = reaper.GetTrackMediaItem(track, 0)
            return reaper.GetActiveTake(item)
        end
        return nil
    end

    local function gatherAllRTPCInfo()
        rtpcData = {}
        if reaper.AK_Waapi_Connect("127.0.0.1", 8080) then
            local args = reaper.AK_AkJson_Map()

            local ofTypeArray = reaper.AK_AkJson_Array()
            reaper.AK_AkJson_Array_Add(ofTypeArray, reaper.AK_AkVariant_String("GameParameter"))

            local from = reaper.AK_AkJson_Map()
            reaper.AK_AkJson_Map_Set(from, "ofType", ofTypeArray)
            reaper.AK_AkJson_Map_Set(args, "from", from)

            local returnArray = reaper.AK_AkJson_Array()
            reaper.AK_AkJson_Array_Add(returnArray, reaper.AK_AkVariant_String("name"))
            reaper.AK_AkJson_Array_Add(returnArray, reaper.AK_AkVariant_String("min"))
            reaper.AK_AkJson_Array_Add(returnArray, reaper.AK_AkVariant_String("max"))
            reaper.AK_AkJson_Array_Add(returnArray, reaper.AK_AkVariant_String("initialValue"))
            
            local options = reaper.AK_AkJson_Map()
            reaper.AK_AkJson_Map_Set(options, "return", returnArray)

            local dummy = reaper.AK_AkJson_Map()
            local result = reaper.AK_Waapi_Call("ak.wwise.core.object.get", args, options)
            
            if result then
                local status = reaper.AK_AkJson_GetStatus(result)
                if status then
                    local rtpcs = reaper.AK_AkJson_Map_Get(result, "return")
                    if rtpcs then
                        local numRtpcs = reaper.AK_AkJson_Array_Size(rtpcs)
                        for i = 0, numRtpcs - 1 do
                            local rtpc = reaper.AK_AkJson_Array_Get(rtpcs, i)
                            local name = reaper.AK_AkVariant_GetString(reaper.AK_AkJson_Map_Get(rtpc, "name"))
                            local minValue = reaper.AK_AkVariant_GetDouble(reaper.AK_AkJson_Map_Get(rtpc, "min"))
                            local maxValue = reaper.AK_AkVariant_GetDouble(reaper.AK_AkJson_Map_Get(rtpc, "max"))
                            local initialValue = reaper.AK_AkVariant_GetDouble(reaper.AK_AkJson_Map_Get(rtpc, "initialValue"))
                            table.insert(rtpcData, {name = name, minValue = minValue, maxValue = maxValue, initialValue = initialValue})
                        end
                    end
                end
            else
                print("Failed to call WAAPI.")
            end
        else
            reaper.ShowMessageBox("Could not connect to WAAPI. RTPC data unavailable.", "Warning", 0)
        end
        return rtpcData
    end

    local function handleProfilerEvents(entries, offsetInSecondsToStartProject, createdTracks)
        local eventEntries = filterEntriesByType(entries, "Event", offsetInSecondsToStartProject)
        for _, entry in ipairs(eventEntries) do
            local take = prepareForProfilerMarkers(entry, createdTracks)
            local takeMarkerName = "Event;" .. entry.objectName
            local color = getColorValue(colors, "Red")
            reaper.SetTakeMarker(take, -1, takeMarkerName, entry.timestamp, color)
        end
    end

    local function handleProfilerSwitch(entries, offsetInSecondsToStartProject, createdTracks)
        local switchEntries = filterEntriesByType(entries, "Switch", offsetInSecondsToStartProject)
        for _, entry in ipairs(switchEntries) do
            local take = prepareForProfilerMarkers(entry, createdTracks)
            local takeMarkerName = "Switch;" .. entry.objectName .. ";" .. entry.description
            local color = getColorValue(colors, "Blue")
            reaper.SetTakeMarker(take, -1, takeMarkerName, entry.timestamp, color)
        end
    end

    local function handleProfilerState(entries, offsetInSecondsToStartProject, createdTracks)
        local stateEntries = filterEntriesByType(entries, "State Changed", offsetInSecondsToStartProject)
        for _, entry in ipairs(stateEntries) do
            local take = prepareForProfilerMarkers(entry, createdTracks)
            local takeMarkerName = "State;" .. entry.objectName .. ";" .. entry.description
            local color = getColorValue(colors, "Green")
            reaper.SetTakeMarker(take, -1, takeMarkerName, entry.timestamp, color)
        end
    end

    local function handleProfilerPosition(entries, offsetInSecondsToStartProject, createdTracks)
        local posEntries = filterEntriesByType(entries, "SetPosition", offsetInSecondsToStartProject)
        local posEntriesFiltered = filterConsecutiveEntries(posEntries)
        for _, entry in ipairs(posEntriesFiltered) do
            local take = prepareForProfilerMarkers(entry, createdTracks)
            local roundedPosX = entry.posOrValue.Position.X
            local roundedPosY = entry.posOrValue.Position.Y
            local roundedPosZ = entry.posOrValue.Position.Z

            local roundedOrFrontX = 1
            local roundedOrFrontY = 0
            local roundedOrFrontZ = 0

            local roundedOrTopX = 0
            local roundedOrTopY = 1
            local roundedOrTopZ = 0

            if entry.posOrValue.OrientationFront.X then
                roundedOrFrontX = tonumber(entry.posOrValue.OrientationFront.X)
                roundedOrFrontY = tonumber(entry.posOrValue.OrientationFront.Y)
                roundedOrFrontZ = tonumber(entry.posOrValue.OrientationFront.Z)
            end
            if entry.posOrValue.OrientationTop.X then
                roundedOrTopX = tonumber(entry.posOrValue.OrientationTop.X)
                roundedOrTopY = tonumber(entry.posOrValue.OrientationTop.Y)
                roundedOrTopZ = tonumber(entry.posOrValue.OrientationTop.Z)
            end

            local takeMarkerName = "SetPos;" .. roundedPosX .. ";" .. roundedPosY .. ";" .. roundedPosZ .. ";" .. 
                                  roundedOrFrontX .. ";" .. roundedOrFrontY .. ";" .. roundedOrFrontZ .. ";" .. 
                                  roundedOrTopX .. ";" .. roundedOrTopY .. ";" .. roundedOrTopZ .. ";"
            local color = getColorValue(colors, "Yellow")
            reaper.SetTakeMarker(take, -1, takeMarkerName, entry.timestamp, color)
        end
    end

    local function handleProfilerRTPC(entries, offsetInSecondsToStartProject, createdTracks)
        local rtpcEntries = filterEntriesByType(entries, "SetRTPCValue", offsetInSecondsToStartProject)
        for _, entry in ipairs(rtpcEntries) do
            if entry.description then
                local take = prepareForProfilerMarkers(entry, createdTracks)
                if take then
                    local takeMarkerName = "RTPCLeg;" .. entry.objectName .. ";" ..  entry.posOrValue
                    local color = getColorValue(colors, "Orange")
                    reaper.SetTakeMarker(take, -1, takeMarkerName, entry.timestamp, color)
                end
            end
        end
    end

    local function findClosestRTPCMarkerBeforeTimestamp(take, timestamp, objectName)
        local numMarkers = reaper.GetNumTakeMarkers(take)
        local closestMarkerName = nil
        local closestMarkerPosition = -1
        local closestPattern = nil
        local patterns = {"RTPCLeg;", "RTPCInterp;"}

        for i = 0, numMarkers - 1 do
            local retval, name, _ = reaper.GetTakeMarker(take, i)
            local components = {}
            for str in string.gmatch(name, "([^;]+)") do
                table.insert(components, str)
            end
            local componentName = components[2]

            for _, pattern in ipairs(patterns) do
                if retval and retval <= timestamp and string.sub(name, 1, string.len(pattern)) == pattern and componentName == objectName then
                    if retval > closestMarkerPosition then
                        closestMarkerPosition = retval
                        closestMarkerName = name
                        closestPattern = pattern
                    end
                end
            end
        end

        if closestMarkerName then
            closestPattern = string.sub(closestPattern, 1, -2)
        end

        return closestMarkerName, closestPattern
    end

    local function handleProfilerRTPCInterp(entries, offsetInSecondsToStartProject, createdTracks)
        local rtpcInterpEntries = filterEntriesByType(entries, "SetRTPCValueInterp", offsetInSecondsToStartProject)
        if rtpcInterpEntries then
            for _, entry in ipairs(rtpcInterpEntries) do
                if entry then
                    local take = prepareForProfilerMarkers(entry, createdTracks)
                    if take then
                        local initRTPCValue
                        local closestMarkerName, closestMarkerPattern = findClosestRTPCMarkerBeforeTimestamp(take, entry.timestamp, entry.objectName)
                        if not closestMarkerName and entry.initialValue then
                            closestMarkerName = "None"
                            initRTPCValue = entry.initialValue
                        elseif closestMarkerPattern == "RTPCLeg" then
                            local temp = closestMarkerName:match("([%d%.]+)$")
                            initRTPCValue = tonumber(temp)
                        elseif closestMarkerPattern == "RTPCInterp" then
                            local pattern = "[^;]*;[^;]*;[^;]*;([%d%.]+)"
                            local temp = closestMarkerName:match(pattern)
                            initRTPCValue = tonumber(temp)
                        elseif not initRTPCValue then
                            initRTPCValue = 0
                        end

                        local takeMarkerName = "RTPCInterp;" .. entry.objectName .. ";" ..  initRTPCValue .. ";" ..  entry.posOrValue .. ";" .. entry.interpTime
                        local color = getColorValue(colors, "Purple")
                        reaper.SetTakeMarker(take, -1, takeMarkerName, entry.timestamp, color)
                    end
                end
            end
        end
    end

    local function handleProfilerInit(entries, offsetInSecondsToStartProject, createdTracks)
        local gameObjEntries = filterEntriesByType(entries, "InitObj", offsetInSecondsToStartProject)
        for _, entry in ipairs(gameObjEntries) do
            local take = prepareForProfilerMarkers(entry, createdTracks)
            if take then
                local takeMarkerName = "InitObj;"
                local color = getColorValue(colors, "Red")
                reaper.SetTakeMarker(take, -1, takeMarkerName, entry.timestamp, color)
            end
        end
    end

    local function enrichEntriesWithRtpcData(entries, rtpcData)
        for _, entry in ipairs(entries) do
            for _, rtpc in ipairs(rtpcData) do
                if entry.objectName == rtpc.name then
                    entry.initialValue = rtpc.initialValue
                    entry.maxValue = rtpc.maxValue
                    entry.minValue = rtpc.minValue
                    break
                end
            end
        end
        return entries
    end

    -- 核心实现
    if not filePath then
        local retval, selectedFilePath = reaper.GetUserFileNameForRead("", "Select Profiler TXT File", "txt")
        if not retval then
            print("File selection cancelled")
            return false
        end
        filePath = selectedFilePath
    end

    local entries = processLogFile(filePath)
    if not entries then
        return false
    end

    gatherAllRTPCInfo()
    entries = enrichEntriesWithRtpcData(entries, rtpcData)
    local createdTracks = createTracksForGameObjects(entries)
    local totalDuration, minTimestamp = getTotalDurationInSeconds(entries)
    createMIDIItems(createdTracks, totalDuration)
    local offset = minTimestamp
    
    handleProfilerInit(entries, offset, createdTracks)
    handleProfilerEvents(entries, offset, createdTracks)
    handleProfilerSwitch(entries, offset, createdTracks)
    handleProfilerState(entries, offset, createdTracks)
    handleProfilerPosition(entries, offset, createdTracks)
    handleProfilerRTPC(entries, offset, createdTracks)
    handleProfilerRTPCInterp(entries, offset, createdTracks)

    print("Project generated from: " .. filePath)
    return true
end

----------------------------------------------------------------------
-- 指定Listener
----------------------------------------------------------------------

-- 将所有含"Camara"的轨道名称修改为"Listener"
local function renameCamaraTracksToListener()
    local modifiedCount = 0  -- 记录修改的轨道数量
    local totalTracks = reaper.CountTracks(0)  -- 获取总轨道数
    
    -- 遍历所有轨道
    for i = 0, totalTracks - 1 do
        local track = reaper.GetTrack(0, i)  -- 获取第i个轨道
        if track then
            -- 获取当前轨道名称
            local _, currentName = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
            
            -- 检查轨道名称是否包含"Camara"（精确匹配）
            if currentName and string.find(currentName, "Camera", 1, true) then
                -- 修改轨道名称为"Listener"
                reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "Listener", true)
                modifiedCount = modifiedCount + 1
                -- reaper.ShowConsoleMsg("修改轨道名称: " .. currentName .. " -> Listener\n")
            end
        end
    end
    
    return modifiedCount
end

----------------------------------------------------------------------
-- 函数调用示例
----------------------------------------------------------------------

-- 执行函数并处理结果
reaper.Undo_BeginBlock()  -- 开始撤销块

-- 示例1: 创建新轨道和项目（需要提供游戏对象名称）
Create_new_track_and_item("WwiseCaptureLog")

-- 示例2: 从Profiler TXT生成项目（可指定路径或使用文件选择对话框）
Generate_project_from_Profiler_TXT()  -- 弹出文件选择对话框
-- Generate_project_from_Profiler_TXT("C:/path/to/profiler_log.txt")  -- 直接指定文件路径

-- 指定Listener
-- local changedCount = renameCamaraTracksToListener()

reaper.Undo_EndBlock("一键导入CaptureLog", -1)  -- 结束撤销块

-- 刷新界面显示
reaper.TrackList_AdjustWindows(false)
reaper.UpdateArrange()