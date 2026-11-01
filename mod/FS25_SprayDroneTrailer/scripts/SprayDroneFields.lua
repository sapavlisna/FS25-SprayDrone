-- Klasifikace polí spec.<jméno> (SprayDroneStation.SPEC_NAME) pro vlek se dvěma drony (docs/DVA_DRONY_NAVRH.md, kap. 1.5).
-- shared = patří vozidlu (konstanty z XML, nastavení, pokrytí, baterie, centrála, bedna); drone = patří jednomu dronu
-- (stav, uzly, trasa). Dron 1 je přímo spec, dron 2 je pohled (SprayDroneDrones.createView), který čte a zapisuje sdílená
-- pole do spec a per-drone drží sám. Nové pole se musí zapsat do právě jednoho seznamu (tools/audit_spec_fields.py).

SprayDroneFields = {}

SprayDroneFields.shared = {
    -- konstanty z XML (oba drony mají stejnou variantu a stejné parametry)
    "acceleration", "ascentSpeed", "batteryCapacity", "batteryKey", "batteryKwh", "batteryMass", "batteryReserve", "batteryStowFrom", "batteryStowUntil", "batterySwapBelow",
    "batteryVariant", "chargeRate", "climbFactor", "climbSpeed", "concentrateFillUnitIndex", "corridorHeight", "cruiseSpeed",
    "descentFactor", "dieselFillUnitIndex", "dieselPerSecond", "drainRate", "droneMass", "droneName", "droneRadius", "fillUnitIndex",
    "hoverFactor", "isScanDrone", "limeInlet", "maxRange", "maxTransitHeight", "mixerProducts", "mixerRatios", "mixerTypes", "navBlinkOn", "navBlinkPeriod", "navLightIntensity",
    "palletDistance", "palletRate", "pumpRate", "rangeCap", "readyCharge", "rotorPitch", "securedFoldTime", "sprayHeight",
    "sprayingSpeed", "swapTime", "tankCapacity", "trailerFoldEnd", "turnAcceleration", "usageScale", "variants", "workWidth", "yawSpeed",
    -- sdílený běhový stav a nastavení
    "fieldId", "flightAreas", "areaVersion", "transitHeight", "obstacleClearance", "sideClearance", "headlands", "headlandFirst",
    "settingsVersion", "coverage", "coverageDirtyFlag", "coverageSyncTime", "dirtyFlag", "positionDirtyFlag", "flightSyncTimer",
    "batteries", "batteryNodes", "batteryParents", "batteryShown", "batteryMoves", "batterySlotDeck", "batteryStowed", "chargerLeds",
    "chargerLedShown", "lastFoldProgress", "numCharging",
    "generatorEnabled", "generatorRunning", "exhaust", "exhaust2", "numGenerators", "powerSyncTimer", "sound",
    "transferMode", "transferPallet", "transferPalletUnit", "palletSearchTime", "transferSyncTimer",
    "toolbox", "relaySlots", "ladder", "actionEvents", "actionStates", "frozen", "loadedFrozen", "centerOfMass", "shapeOrigins", "padShapes", "stuckWarningTime",
    -- nová pole vozidla
    "numDrones", "drones", "activeDrones", "numBatterySlots", "batterySlotBits", "transferDrone", "layerGap",
    "droneCameraRequested", "firstDroneCamera", "secondVariant", "secondVariants", "level", "plannerScreenNode", "plannerScreenOn", "screenWakeTime", "sdtScreenShown",
    -- plevel vybraného pole pro plán herbicidu
    "weedShareCache",
    -- sken pole (druh mise, úroveň skenu a parametry postřiku, na které se po skenu vrací)
    "missionMode", "scanCell", "scanSpeed", "scanMaxWind", "sprayMaxWind", "sprayWorkWidth", "sprayFlightHeight", "sprayFlightSpeed",
    -- aplikace podle skenu (nastavení, parametry z XML, maska a vypnutí masky pro srovnávací plán)
    "applyMode", "spotMargin", "spotGap", "spotMaxAge", "spotMaskCache", "spotOff",
    -- uložená pumpa, přepočet trasy po změně nafty, záznam dějů
    "pumpSlot", "routeDiesel", "sdtWatch",
    -- drony na plošinách (varianta na plošině 1 / 2, za hry vyměnitelná)
    "pads", "numPads", "padSlots",
    -- baterie jako předměty (SprayDroneBatterySlots): šachty nabíječky, počet baterií z konfigurace obchodu
    "batterySlots", "batteryConfigCount",
    -- kufr skenovacího dronu (SprayDroneCase): profil, zdroj nabíjení, kufry nabíjené od centrály vleku, víko a vizuál
    "portable", "chargeSource", "caseSourceTimer", "caseLoads", "caseActivatable", "caseVisuals",
    -- vzorkovač AIRASI (SprayDroneSamples): parametry, bednička, mřížka bodů pole, přeskočené body, kruh odběru PF, vizuál
    "isSamplerDrone", "sampler", "sampleBox", "samplerGrid", "samplerSkip", "samplerCircle", "samplerVisuals",
    -- naklikané body odběru po polích a nastavení automatických bodů
    "samplerPicks", "samplerAuto"
}

SprayDroneFields.drone = {
    -- let a poloha
    "airborne", "avoidClimbTo", "avoidHeight", "avoidRayLength", "guardOffUntil", "guardNextCheck", "returnEnergy", "returnEnergyTime", "batch", "batchHeight", "flightTime", "isLinked", "isSpraying",
    "lastSprayTime", "lastWorldPos", "moveDir", "netTarget", "path", "pos", "speed", "sprayFrom", "sprayTypeIndex", "litersPerMeter",
    "massPerLiter", "velocity", "worldAccel", "wpIndex", "yawRate", "drainPos", "drainParams", "drainFactor", "tilt", "lookaheadPoints",
    -- stav mise
    "state", "status", "notifiedStatus", "missionActive", "serviceTimer", "swapChecked", "swapPending", "swapTimer", "isPumping", "isMixing", "isSwapping",
    "waitingForCharge", "waitingForPower", "pumpCapChecked", "pumpTankTarget", "batteryAtStart", "estimatedEnergy", "estimatedTime", "waitingForPad",
    "waitingForRelay", "waitingForClearance", "batchRelays", "signalLostTime", "signalCheckTime", "scanning", "weatherCheckTime",
    -- náplň a baterie dronu
    "battery", "droneBattery", "droneFillLevel", "droneFillType",
    -- kde dron vzlétl (kufr se za letu nesmí pohnout, SprayDroneCase.MOVE_TOLERANCE)
    "launchX", "launchZ",
    -- vzorkovač: vzorky v dronu, výdrž nad bodem odběru, vysunutá sonda, vzorky této dávky a dávky po sobě bez vzorku (pojistka)
    "samplesCarried", "samplerBoxes", "sampleHold", "probeOut", "samplerBatchSamples", "samplerIdleBatches",
    -- trasa a cache
    "corridor", "drawLegs", "hopCache", "numBatches", "pathCache", "pathCacheSize", "range", "rangeKey", "routeClipped", "routeDirty",
    "routeInfo", "routeFull", "routeTimer", "spotRouteRevision", "transitCache", "transitCacheSize", "layerOffset", "droneIndex", "rootSpec", "pfDose",
    -- dosah rádia (SprayDroneLink.getShapeMaxRange) a pruhy pole mimo dosah kufru pro plánovač
    "radioMax", "outOfReachLegs",
    -- uzly a vizuál
    "appliedUnfold", "unfold", "unfoldMoving", "foldHold", "batterySlotDrone", "clamps", "clampsVisible", "droneKey", "dronePrefix", "effects",
    "foldParts", "hasDrone", "hose", "hoseConnect", "hoseT", "spraySoundOn", "rotorPitchFactor", "rotorStartDelay",
    "rotorRetryTime", "hotspot", "localRot", "localTrans", "navLights", "node", "parent", "pad",
    "propBlades", "propPaintMaterial", "propSource", "rotors", "rotorSpeed", "rotorsParked", "rotorVolumeScale", "samples", "soundPitch",
    "soundVolume", "sprayEffectPlacement", "sprayEffectsActive", "sprayEffectsPlaced",
    "sprayEffectsShown", "tiltNode", "camera", "outCamera", "homeYawOffset",

}
