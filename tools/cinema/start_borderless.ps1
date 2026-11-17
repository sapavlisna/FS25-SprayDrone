# Start hry pro ostré natáčení (varianta A ze zaznam_navrh.md): okno 1920x1080 jako windowed_fullscreen, NE offscreen.
# Jako tools\sdt_start.ps1 (stejný backup game.xml do out\game.xml.orig, návrat přes `tools\sdt_start.ps1 -Stop`), ale přidá fullscreenMode a okno nepřesouvá.
param([int]$Slot = 13, [int]$Width = 1920, [int]$Height = 1080, [double]$Scaling = 1.0)
$dir = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "tools"
$root = Split-Path -Parent $dir
$game = Join-Path $env:USERPROFILE "Documents\My Games\FarmingSimulator2025"
$gameXml = Join-Path $game "game.xml"
$backup = Join-Path $root "out\game.xml.orig"
Get-Process | Where-Object { $_.ProcessName -like 'FarmingSimulator2025*' } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 3
if (-not (Test-Path $backup)) { Copy-Item $gameXml $backup }
$sc = $Scaling.ToString([cultureinfo]::InvariantCulture)
(Get-Content $backup -Raw) -replace '<width>\d+</width>', "<width>$Width</width>" -replace '<height>\d+</height>', "<height>$Height</height>" `
    -replace '<fullscreenMode>[^<]*</fullscreenMode>', '<fullscreenMode>windowed_fullscreen</fullscreenMode>' `
    -replace '<scaling>[^<]*</scaling>', "<scaling>$sc</scaling>" | Set-Content $gameXml -Encoding utf8
& powershell -NoProfile -File (Join-Path $dir "sdt_debug.ps1") -Off | Out-Null
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
"hotovo"
