# Záznam obrazovky ffmpegem: ddagrab (Desktop Duplication) -> h264_nvenc, 60 fps, výstup out\trailer\raw\<Name>.mp4.
# Používá se jen při ostrém natáčení (hra na celé obrazovce 1080p, viz tmp\trailer\zaznam_navrh.md, varianta A).
#   .\tools\cinema\record.ps1 -Name s01 -Seconds 8                 8 s pevně, pak ffmpeg skončí sám
#   .\tools\cinema\record.ps1 -Name s01 -Seconds 8 -Readback       záložní řetězec přes RAM (bez hwmap do CUDA)
#   .\tools\cinema\record.ps1 -Name s01 -Seconds 8 -Fps 30 -Output 1   jiný výstup monitoru (output_idx)
# Před spuštěním do souboru out\trailer\raw\<Name>.start.txt zapíše čas začátku (ISO), podle něj se přestřihne proti řádkům "CINEMA" v log.txt.
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][double]$Seconds,
    [int]$Fps = 60,
    [int]$Output = 0,
    [int]$Cq = 16,
    [switch]$Cuda
)
$ffmpeg = "C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$dir = Join-Path $root "out\trailer\raw"
New-Item -ItemType Directory -Force $dir | Out-Null
$out = Join-Path $dir "$Name.mp4"
$grab = "ddagrab=output_idx=${Output}:framerate=${Fps}:draw_mouse=0"
if ($Cuda) { $chain = "$grab,hwmap=derive_device=cuda,scale_cuda=format=nv12" } else { $chain = "$grab,hwdownload,format=bgra,format=nv12" }
$t = [string]::Format([cultureinfo]::InvariantCulture, "{0:F3}", $Seconds)
(Get-Date -Format o) | Set-Content -Path (Join-Path $dir "$Name.start.txt") -Encoding ascii
& $ffmpeg -hide_banner -loglevel warning -y -filter_complex $chain -t $t `
    -c:v h264_nvenc -preset p5 -tune hq -rc vbr -cq $Cq -b:v 0 -maxrate 120M -bufsize 240M -profile:v high -g 120 -bf 2 `
    -movflags +faststart $out
"hotovo: $out"
