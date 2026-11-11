# Restore and foreground the browser window used by browser.bat.
#   powershell -NoProfile -ExecutionPolicy Bypass -File show-browser.ps1 chrome.exe
#
# Chrome started from a script may come up minimized, and a reused instance
# may be sitting minimized or behind other windows - either way the user sees
# nothing and thinks it never launched. ShowWindow(SW_RESTORE) works without
# foreground rights, which SetForegroundWindow alone does not.
param([string]$Exe = "chrome.exe")

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class WinShow {
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
'@

$ids = @(Get-CimInstance Win32_Process |
         Where-Object { $_.Name -eq $Exe -and $_.CommandLine -like '*ekwing-auto-profile*' } |
         Select-Object -ExpandProperty ProcessId)
$w = Get-Process -Id $ids -ErrorAction SilentlyContinue |
     Where-Object { $_.MainWindowHandle -ne 0 } |
     Select-Object -First 1
if ($w) {
    [WinShow]::ShowWindow($w.MainWindowHandle, 9) | Out-Null   # SW_RESTORE
    [WinShow]::SetForegroundWindow($w.MainWindowHandle) | Out-Null
    exit 0
}
exit 1
