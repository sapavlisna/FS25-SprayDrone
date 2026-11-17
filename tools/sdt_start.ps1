# Spustí FS25 se zkušební hrou (slot 11, nebo -Slot N; -NoPrepare = save se nepřepisuje), počká na načtení, odklikne „Spustit“ a přesune okno na display 6 (1600x900).
# -Offscreen: okno hry po startu odsune mimo obrazovku (běží a jde ho fotit přes sdt_shot.ps1, ale nepřekáží).
# game.xml se po testu vrací příkazem  .\tools\sdt_start.ps1 -Stop
param([switch]$Stop, [switch]$Offscreen, [switch]$Force, [int]$Slot = 11, [switch]$NoPrepare, [string]$SaveArgs = "--unfolded --drone M --time 12:00 --player-at-ladder",
    [int]$Width = 1600, [int]$Height = 900)
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $dir
$game = Join-Path $env:USERPROFILE "Documents\My Games\FarmingSimulator2025"
$gameXml = Join-Path $game "game.xml"
$backup = Join-Path $root "out\game.xml.orig"
$running = Get-Process | Where-Object { $_.ProcessName -like 'FarmingSimulator2025*' }
if ($running -and -not (Test-Path $backup) -and -not $Force) {
    "Hra běží a nespustil ji tenhle skript (nejspíš ji hraješ): nic nevypínám. Zavři ji ručně, nebo přidej -Force."; return
}
$running | Stop-Process -Force -ErrorAction SilentlyContinue
if ($Stop) {
    if (Test-Path $backup) { Copy-Item $backup $gameXml -Force; Remove-Item $backup }
    "game.xml vrácen"; return
}
Start-Sleep 3
if (-not (Test-Path $backup)) { Copy-Item $gameXml $backup }
(Get-Content $backup -Raw) -replace '<width>\d+</width>', "<width>$Width</width>" -replace '<height>\d+</height>', "<height>$Height</height>" |
    Set-Content $gameXml -Encoding utf8
& powershell -NoProfile -File (Join-Path $dir "sdt_debug.ps1") -Off | Out-Null
Push-Location $root
if (-not $NoPrepare) { & python tools/prepare_testsave.py ($SaveArgs -split ' ') | Select-Object -Last 1 }
Pop-Location
$log = Join-Path $game "log.txt"
$start = Get-Date
Start-Process "C:\Program Files (x86)\Steam\steam.exe" -ArgumentList "-applaunch", "2300320", "-autoStartSavegameId", "$Slot", "-skipStartVideos", "-skipModUpdateDialog", "-cheats"
& powershell -NoProfile -File (Join-Path $dir "steam_continue.ps1")
Start-Sleep 20
for ($i = 0; $i -lt 60; $i++) {
    if ((Test-Path $log) -and (Get-Item $log).LastWriteTime -gt $start -and (Select-String -Path $log -Pattern 'densityMap_weed' -Quiet)) { break }
    Start-Sleep 5
}
Start-Sleep 30
& powershell -NoProfile -File (Join-Path $dir "fs25_focus.ps1")
& powershell -NoProfile -File (Join-Path $dir "fs25_input.ps1") "press:ENTER; wait:6000" | Out-Null
& powershell -NoProfile -File (Join-Path $dir "fs25_focus.ps1")
& powershell -NoProfile -File (Join-Path $dir "fs25_move.ps1") @(if ($Offscreen) { "-Off" })
Select-String -Path $log -Pattern 'compiler error|SprayDrone.*rror|attempt to' | Select-Object -Last 5 | ForEach-Object { $_.Line }
"hotovo"
