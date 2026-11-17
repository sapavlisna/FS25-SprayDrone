# Snímek okna hry bez focusu (PrintWindow s PW_RENDERFULLCONTENT): .\fs25_capture.ps1 jméno [-Scale 0.5]
# Výsledek: out\mod_build\<jméno>.png. Vypíše průměrný jas, ať je poznat černý (nezachycený) snímek.
param([Parameter(Mandatory = $true)][string]$Name, [double]$Scale = 1.0)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class FsCap {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
"@
$p = Get-Process | Where-Object { $_.ProcessName -like 'FarmingSimulator2025Game*' -and $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { "hra neběží"; exit 1 }
$r = New-Object FsCap+RECT
[FsCap]::GetClientRect($p.MainWindowHandle, [ref]$r) | Out-Null
$w = $r.R; $h = $r.B
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$dc = $g.GetHdc()
[FsCap]::PrintWindow($p.MainWindowHandle, $dc, 3) | Out-Null
$g.ReleaseHdc($dc); $g.Dispose()
$sum = 0; $n = 0
for ($y = 0; $y -lt $h; $y += 40) { for ($x = 0; $x -lt $w; $x += 40) { $c = $bmp.GetPixel($x, $y); $sum += $c.R + $c.G + $c.B; $n++ } }
$out = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "out\mod_build\$Name.png"
if ($Scale -ne 1.0) { $b2 = New-Object System.Drawing.Bitmap $bmp, ([int]($w * $Scale)), ([int]($h * $Scale)); $b2.Save($out); $b2.Dispose() } else { $bmp.Save($out) }
$bmp.Dispose()
"{0} (jas {1:N0}/765)" -f $out, ($sum / $n)
