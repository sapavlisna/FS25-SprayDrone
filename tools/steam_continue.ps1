# Když Steam před spuštěním hry ukáže "Synchronizace se nezdařila" (Steam Cloud), klikne na "Přesto spustit" (okno ve středu obrazovky 1920x1080).
Add-Type @"
using System; using System.Runtime.InteropServices;
public class SteamClick { [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y); [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint dx,uint dy,uint d,UIntPtr e); }
"@
for ($i = 0; $i -lt 8; $i++) {
    if (Get-Process FarmingSimulator2025Game -ErrorAction SilentlyContinue) { return }
    Start-Sleep 3
}
[SteamClick]::SetCursorPos(909, 462) | Out-Null
Start-Sleep -Milliseconds 300
[SteamClick]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 80
[SteamClick]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
