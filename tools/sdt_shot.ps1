# Snímek ze zadaného pohledu bez focusu: debug příkaz view (teleport hráče + kamera) a zachycení okna (fs25_capture.ps1).
# Souřadnice jako sdt_view.ps1 (Blender vleku). Před tím stačí jednou  sdt_debug.ps1 -Command hudOff  (bez HUD).
#   .\tools\sdt_shot.ps1 -From "0.3,2.2,1.3" -At "0.3,3.4,0.7" -Name s1 [-Scale 0.5]
param([Parameter(Mandatory = $true)][string]$From, [Parameter(Mandatory = $true)][string]$At, [string]$Name = "shot", [double]$Scale = 1.0)
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
& powershell -NoProfile -File (Join-Path $dir "sdt_debug.ps1") -ViewFrom $From -ViewAt $At | Out-Null
Start-Sleep -Milliseconds 2500
& powershell -NoProfile -File (Join-Path $dir "fs25_capture.ps1") $Name -Scale $Scale
