param([switch]$Off)
Add-Type @"
using System; using System.Runtime.InteropServices;
public class Mv { [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int w, int hh, uint f);
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r); public struct R { public int L,T,Rr,B; } }
"@
$p = Get-Process | Where-Object { $_.MainWindowTitle -like 'Farming Simulator 25*' } | Select-Object -First 1
if ($Off) { [Mv]::SetWindowPos($p.MainWindowHandle, [IntPtr]::Zero, -4000, -3000, 0, 0, 0x0001 -bor 0x0004 -bor 0x0010) | Out-Null }
else { [Mv]::SetWindowPos($p.MainWindowHandle, [IntPtr]::Zero, 100, 60, 0, 0, 0x0001 -bor 0x0004) | Out-Null }
$r = New-Object Mv+R; [Mv]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null
"okno: $($r.L),$($r.T) - $($r.Rr),$($r.B)"
