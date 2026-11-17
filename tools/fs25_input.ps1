# Ovládání běžící FS25 při automatickém testu: pohyb myší, klávesy a snímek jen okna hry.
# Použití: .\fs25_input.ps1 "move:15,0,30; hold:W,3000; press:ENTER; wait:1000; shot:hra_05"
#   move:dx,dy,kroky   relativní pohyb myši (otáčení kamery)
#   hold:KLÁVESA,ms    podržet klávesu (W A S D E Q F X SPACE ENTER ESC SHIFT CTRL TAB BACKSPACE LEFT RIGHT UP DOWN 0-9 F1-F12)
#   press:KLÁVESA      krátký stisk
#   holdk:W+A,ms       několik kláves držených najednou
#   combo:ALT+7        kombinace kláves (modifikátory drží, dokud se nestiskne poslední)
#   wheel:delta,počet  kolečko myši (-120 = od sebe/oddálit, 120 = k sobě)
#   wait:ms            pauza
#   shot:jméno         snímek okna hry do out\mod_build\jméno.png (poloviční rozlišení)
#   small:jméno        snímek okna hry šířky 400 px (levný na tokeny)
#   shotfull:jméno     totéž v plném rozlišení (tenké debug čáry v dálce)
#   mouseto:fx,fy      kurzor na místo v klientské oblasti okna hry (fx, fy = 0..1 zleva a shora)
#   click:fx,fy        totéž a klik levým tlačítkem
#   drag:fx,fy,tx,ty   tažení levým tlačítkem z (fx,fy) do (tx,ty)
param([Parameter(Mandatory = $true)][string]$Actions)

Add-Type -AssemblyName System.Drawing
if (-not ("FsIn2" -as [type])) {
    Add-Type @"
using System; using System.Runtime.InteropServices;
public class FsIn2 {
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, int dx, int dy, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint f, UIntPtr e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint type);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  public struct POINT { public int X, Y; }
  public struct RECT { public int L, T, R, B; }
  public static void Move(int dx, int dy, int steps) { for (int i = 0; i < steps; i++) { mouse_event(1, dx, dy, 0, UIntPtr.Zero); System.Threading.Thread.Sleep(15); } }
  public static void Hold(byte vk, int ms) { byte sc = (byte)MapVirtualKey(vk, 0); keybd_event(vk, sc, 0, UIntPtr.Zero); System.Threading.Thread.Sleep(ms); keybd_event(vk, sc, 2, UIntPtr.Zero); }
}
"@
}

$keys = @{ SPACE = 0x20; ENTER = 0x0D; ESC = 0x1B; SHIFT = 0x10; CTRL = 0x11; TAB = 0x09; ALT = 0x12; BACKSPACE = 0x08; LEFT = 0x25; UP = 0x26; RIGHT = 0x27; DOWN = 0x28 }
function VK([string]$k) {
    $k = $k.ToUpper()
    if ($keys.ContainsKey($k)) { return [byte]$keys[$k] }
    if ($k -match '^F(\d{1,2})$') { return [byte](0x6F + [int]$Matches[1]) }
    if ($k -match '^0X[0-9A-F]+$') { return [byte][Convert]::ToInt32($k.Substring(2), 16) }
    if ($k.Length -eq 1) { return [byte][char]$k }
    throw "neznámá klávesa $k"
}

$p = Get-Process FarmingSimulator2025Game -ErrorAction Stop
$h = $p.MainWindowHandle
[void][FsIn2]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 400
function Client([string]$fx, [string]$fy) {
    $c = New-Object FsIn2+RECT; [void][FsIn2]::GetClientRect($h, [ref]$c)
    $pt = New-Object FsIn2+POINT; $pt.X = [int]([double]$fx * $c.R); $pt.Y = [int]([double]$fy * $c.B)
    [void][FsIn2]::ClientToScreen($h, [ref]$pt)
    return @($pt.X, $pt.Y)
}
function ToScreen([string]$fx, [string]$fy) { $s = Client $fx $fy; [void][FsIn2]::SetCursorPos($s[0], $s[1]); return $s }
$outDir = Join-Path (Split-Path $PSScriptRoot -Parent) "out\mod_build"

foreach ($a in ($Actions -split ';')) {
    $a = $a.Trim(); if (-not $a) { continue }
    $cmd, $arg = $a -split ':', 2
    switch ($cmd) {
        'move' { $v = $arg -split ','; [FsIn2]::Move([int]$v[0], [int]$v[1], [int]$v[2]) }
        'hold' { $v = $arg -split ','; [FsIn2]::Hold((VK $v[0]), [int]$v[1]) }
        'press' { [FsIn2]::Hold((VK $arg), 90) }
        'holdk' {
            $v = $arg -split ','; $ks = @($v[0] -split '\+' | ForEach-Object { VK $_ })
            foreach ($k in $ks) { [FsIn2]::keybd_event($k, [byte][FsIn2]::MapVirtualKey($k, 0), 0, [UIntPtr]::Zero) }
            Start-Sleep -Milliseconds ([int]$v[1])
            foreach ($k in $ks) { [FsIn2]::keybd_event($k, [byte][FsIn2]::MapVirtualKey($k, 0), 2, [UIntPtr]::Zero) }
        }
        'wheel' { $v = $arg -split ','; for ($i = 0; $i -lt [int]$v[1]; $i++) { [FsIn2]::mouse_event(0x0800, 0, 0, [BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$v[0]), 0), [UIntPtr]::Zero); Start-Sleep -Milliseconds 40 } }
        'combo' {
            $ks = @($arg -split '\+' | ForEach-Object { VK $_ })
            foreach ($k in $ks) { [FsIn2]::keybd_event($k, [byte][FsIn2]::MapVirtualKey($k, 0), 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60 }
            Start-Sleep -Milliseconds 90
            [array]::Reverse($ks)
            foreach ($k in $ks) { [FsIn2]::keybd_event($k, [byte][FsIn2]::MapVirtualKey($k, 0), 2, [UIntPtr]::Zero); Start-Sleep -Milliseconds 30 }
        }
        'wait' { Start-Sleep -Milliseconds ([int]$arg) }
        { $_ -in 'shot', 'small', 'shotfull' -and [FsIn2]::GetForegroundWindow() -ne $h } {
            # snímek jen okna hry: když je navrchu něco jiného (přepínač oken, jiná aplikace), nefotit
            Write-Output "PŘESKOČENO $arg - okno hry není v popředí"; continue
        }
        'shot' {
            # jen klientská oblast okna (bez rámečku a stínu, přes které je vidět okolní plocha)
            $c = New-Object FsIn2+RECT; [void][FsIn2]::GetClientRect($h, [ref]$c); $o = Client 0 0
            $w = $c.R; $hh = $c.B
            $b = New-Object System.Drawing.Bitmap $w, $hh
            [System.Drawing.Graphics]::FromImage($b).CopyFromScreen($o[0], $o[1], 0, 0, $b.Size)
            $f = Join-Path $outDir "$arg.png"
            (New-Object System.Drawing.Bitmap $b, ([int]($w / 2)), ([int]($hh / 2))).Save($f)
            Write-Output $f
        }
        'small' {
            # malý snímek (šířka 400 px) pro rychlé kontroly za málo tokenů
            $c = New-Object FsIn2+RECT; [void][FsIn2]::GetClientRect($h, [ref]$c); $o = Client 0 0
            $b = New-Object System.Drawing.Bitmap $c.R, $c.B
            [System.Drawing.Graphics]::FromImage($b).CopyFromScreen($o[0], $o[1], 0, 0, $b.Size)
            $f = Join-Path $outDir "$arg.png"
            (New-Object System.Drawing.Bitmap $b, 400, ([int](400 * $c.B / $c.R))).Save($f)
            Write-Output $f
        }
        'shotfull' {
            $c = New-Object FsIn2+RECT; [void][FsIn2]::GetClientRect($h, [ref]$c); $o = Client 0 0
            $b = New-Object System.Drawing.Bitmap $c.R, $c.B
            [System.Drawing.Graphics]::FromImage($b).CopyFromScreen($o[0], $o[1], 0, 0, $b.Size)
            $f = Join-Path $outDir "$arg.png"
            $b.Save($f)
            Write-Output $f
        }
        'mouseto' { $v = $arg -split ','; ToScreen $v[0] $v[1] | Out-Null }
        'click' {
            $v = $arg -split ','; ToScreen $v[0] $v[1] | Out-Null; Start-Sleep -Milliseconds 150
            [FsIn2]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 80; [FsIn2]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
        }
        'drag' {
            $v = $arg -split ','; $a = ToScreen $v[0] $v[1]; Start-Sleep -Milliseconds 150
            [FsIn2]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
            $b = Client $v[2] $v[3]
            for ($i = 1; $i -le 20; $i++) { [void][FsIn2]::SetCursorPos([int]($a[0] + ($b[0] - $a[0]) * $i / 20), [int]($a[1] + ($b[1] - $a[1]) * $i / 20)); Start-Sleep -Milliseconds 25 }
            [FsIn2]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
        }
        default { throw "neznámá akce $cmd" }
    }
}
