# Ladicí ovládání běžící hry (viz mod\...\scripts\SprayDroneDebug.lua): zapíše modSettings\FS25_SprayDroneTrailer\debug.xml,
# který hra čte jednou za sekundu.
# Použití:
#   .\tools\sdt_debug.ps1 -InfiniteBattery -InfiniteTank -Speed 4        zapnout, rychlost simulace x4
#   .\tools\sdt_debug.ps1 -Command coverField                            jednorázový příkaz (chargeAll, fillTrailer, fillDiesel,
#                                                                       fillWater, fillConcentrate, coverField, resetCoverage,
#                                                                       toolboxFill, toolboxOpen, toolboxDialog, spawnCanister, tiltCanister); ostatní volby zůstanou
#   .\tools\sdt_debug.ps1 -Command toolboxFill                           všechny sloty v bedně plné kanystry s tekutým hnojivem
#   .\tools\sdt_debug.ps1 -Command toolboxOpen                           přepnout víko bedny (otevřít / zavřít)
#   .\tools\sdt_debug.ps1 -Command spawnCanister                        vyrobit plný kanystr hnojiva před bednou
#   .\tools\sdt_debug.ps1 -Command fillWater                             hlavní nádrž plná vodou (pro míchání)
#   .\tools\sdt_debug.ps1 -Command fillConcentrate -ConcentrateType herbicide   koncentrátová nádrž plná (herbicide | liquidFertilizer, nebo přímo SDT_CONCENTRATE_*;
#                                                                       jen když je nádrž prázdná, jinak zůstává její druh)
#   .\tools\sdt_debug.ps1 -MistLoop                                      testovací let vedle vleku
#   .\tools\sdt_debug.ps1 -Off                                           smazat soubor (vše vypnuto)
param(
    [switch]$InfiniteBattery,
    [switch]$InfiniteTank,
    [switch]$MistLoop,
    [double]$Speed = 1,
    [string]$Command = "",
    [string]$ConcentrateType = "",
    [string]$ViewFrom = "",
    [string]$ViewAt = "",
    [string]$Raw = "",
    [switch]$Off
)

$dir = Join-Path $env:USERPROFILE "Documents\My Games\FarmingSimulator2025\modSettings\FS25_SprayDroneTrailer"
$file = Join-Path $dir "debug.xml"
if ($Off) {
    if (Test-Path $file) { Remove-Item $file }
    Write-Output "debug.xml smazán"
    return
}
New-Item -ItemType Directory -Force $dir | Out-Null

$id = 0
$old = $null
if (Test-Path $file) {
    [xml]$old = Get-Content $file -Raw
    $id = [int]$old.debug.commandId
}
if ($Command -ne "") { $id++ }
if ($old -ne $null) {
    if (-not $PSBoundParameters.ContainsKey("InfiniteBattery")) { $InfiniteBattery = [System.Convert]::ToBoolean($old.debug.infiniteBattery) }
    if (-not $PSBoundParameters.ContainsKey("InfiniteTank")) { $InfiniteTank = [System.Convert]::ToBoolean($old.debug.infiniteTank) }
    if (-not $PSBoundParameters.ContainsKey("MistLoop")) { $MistLoop = [System.Convert]::ToBoolean($old.debug.mistLoop) }
    if (-not $PSBoundParameters.ContainsKey("Speed")) { $Speed = [double]$old.debug.speed }
    if (-not $PSBoundParameters.ContainsKey("ConcentrateType")) { $ConcentrateType = [string]$old.debug.concentrateType }
}
$view = ""
if ($ViewFrom -ne "" -and $ViewAt -ne "") {
    # souřadnice v Blenderu (x, y, z) -> lokální souřadnice vleku v i3d (x, z, -y)
    $inv = [System.Globalization.CultureInfo]::InvariantCulture
    $parts = @()
    foreach ($s in @($ViewFrom, $ViewAt)) {
        $v = $s -split ',' | ForEach-Object { [double]::Parse($_, $inv) }
        $parts += $v[0].ToString($inv); $parts += $v[2].ToString($inv); $parts += (-$v[1]).ToString($inv)
    }
    $view = $parts -join ','
    $Command = "view"; $id++
}
if ($Raw -ne "") { $view = $Raw }
$xml = '<debug infiniteBattery="{0}" infiniteTank="{1}" mistLoop="{2}" speed="{3}" command="{4}" commandId="{5}" concentrateType="{6}" view="{7}"/>' -f `
    $InfiniteBattery.ToString().ToLower(), $InfiniteTank.ToString().ToLower(), $MistLoop.ToString().ToLower(), `
    $Speed.ToString([System.Globalization.CultureInfo]::InvariantCulture), $Command, $id, $ConcentrateType, $view
Set-Content -Path $file -Value $xml -Encoding UTF8
Write-Output $xml
