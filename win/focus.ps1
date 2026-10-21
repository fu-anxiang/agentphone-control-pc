$ErrorActionPreference = 'Stop'
$sig = @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class WinAct {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  public static void Activate(IntPtr h) {
    if (IsIconic(h)) ShowWindow(h, 9);
    SetForegroundWindow(h);
  }
}
'@
Add-Type -TypeDefinition $sig
$needle = $env:PCC_TITLE
$hit = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$needle*" } |
       Select-Object -First 1
if (-not $hit) { "NOTFOUND"; exit 1 }
[WinAct]::Activate($hit.MainWindowHandle) | Out-Null
"FOCUSED: " + $hit.MainWindowTitle
