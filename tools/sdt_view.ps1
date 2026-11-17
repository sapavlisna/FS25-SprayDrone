# Postaví hráče v běžící hře na bod a otočí kameru; vyfotí malý snímek. Souřadnice jsou v Blenderu vleku (x vlevo, y dozadu mínus, z nahoru).
#   .\tools\sdt_view.ps1 -From "1.6,-0.7,0" -At "0.6,-0.7,1.0" -Name v1
#   .\tools\sdt_view.ps1 -From "..." -At "..." -Name v1 -Keys "hold:W,500"      po přesunu ještě stisk kláves (viz fs25_input.ps1)
param(
    [Parameter(Mandatory = $true)][string]$From,
    [Parameter(Mandatory = $true)][string]$At,
    [string]$Name = "view",
    [string]$Keys = ""
)
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
& powershell -NoProfile -File (Join-Path $dir "sdt_debug.ps1") -ViewFrom $From -ViewAt $At | Out-Null
Start-Sleep -Milliseconds 2200
& powershell -NoProfile -File (Join-Path $dir "fs25_focus.ps1")
$actions = if ($Keys -ne "") { "$Keys; wait:300; small:$Name" } else { "small:$Name" }
& powershell -NoProfile -File (Join-Path $dir "fs25_input.ps1") $actions
