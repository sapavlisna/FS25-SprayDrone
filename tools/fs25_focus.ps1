Add-Type @"
using System; using System.Runtime.InteropServices;
public class Fg2 {
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int w, int hh, uint f);
 [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
}
"@
$p = Get-Process | Where-Object { $_.MainWindowTitle -like 'Farming Simulator 25*' } | Select-Object -First 1
$h = $p.MainWindowHandle
$fg = [Fg2]::GetForegroundWindow(); $d = 0
$t1 = [Fg2]::GetWindowThreadProcessId($fg, [ref]$d); $t2 = [Fg2]::GetCurrentThreadId()
[Fg2]::AttachThreadInput($t2, $t1, $true) | Out-Null
[Fg2]::ShowWindow($h, 9) | Out-Null
[Fg2]::SetWindowPos($h, [IntPtr](-1), 0, 0, 0, 0, 0x0003) | Out-Null
[Fg2]::SetWindowPos($h, [IntPtr](-2), 0, 0, 0, 0, 0x0003) | Out-Null
[Fg2]::BringWindowToTop($h) | Out-Null
[Fg2]::SetForegroundWindow($h) | Out-Null
[Fg2]::AttachThreadInput($t2, $t1, $false) | Out-Null
