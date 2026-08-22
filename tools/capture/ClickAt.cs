// Foreground-gated synthetic click for the autonomous comparison loop.
// Usage: ClickAt.exe <screenX> <screenY>
// SAFETY: brings the SimCity window to the foreground, then clicks ONLY if
// the foreground window belongs to the SimCity process AND the point lies
// inside that window's rect. Refuses otherwise, so it can never click the
// user's desktop or another application. Benign targets only (opening
// menus/dialogs); the caller never aims at destructive controls.
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;

class ClickAt
{
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc cb, IntPtr p);
    [DllImport("user32.dll")] static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
    [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
    delegate bool EnumWindowsProc(IntPtr h, IntPtr p);

    [StructLayout(LayoutKind.Sequential)] struct RECT { public int Left, Top, Right, Bottom; }
    const uint MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004;

    static int Main(string[] args)
    {
        if (args.Length < 2) { Console.Error.WriteLine("usage: ClickAt.exe <x> <y>"); return 2; }
        int x = int.Parse(args[0]), y = int.Parse(args[1]);

        uint gamePid = 0;
        foreach (Process p in Process.GetProcesses())
            if (p.ProcessName.IndexOf("SimCity", StringComparison.OrdinalIgnoreCase) >= 0) { gamePid = (uint)p.Id; break; }
        if (gamePid == 0) { Console.Error.WriteLine("SimCity not running"); return 1; }

        // Largest visible window of the game process.
        IntPtr hwnd = IntPtr.Zero; long best = 0;
        EnumWindows((wh, lp) => {
            uint pid; GetWindowThreadProcessId(wh, out pid);
            if (pid == gamePid && IsWindowVisible(wh)) {
                RECT r; if (GetWindowRect(wh, out r)) {
                    long a = (long)(r.Right - r.Left) * (r.Bottom - r.Top);
                    if (a > best) { best = a; hwnd = wh; }
                }
            }
            return true;
        }, IntPtr.Zero);
        if (hwnd == IntPtr.Zero) { Console.Error.WriteLine("no game window"); return 1; }

        ShowWindow(hwnd, 9 /*RESTORE*/); SetForegroundWindow(hwnd); Thread.Sleep(500);

        uint fgPid; GetWindowThreadProcessId(GetForegroundWindow(), out fgPid);
        if (fgPid != gamePid) { Console.Error.WriteLine("game not foreground (fg pid " + fgPid + ") - refusing click"); return 1; }

        RECT wr; GetWindowRect(hwnd, out wr);
        if (x < wr.Left || x > wr.Right || y < wr.Top || y > wr.Bottom) {
            Console.Error.WriteLine("point (" + x + "," + y + ") outside game rect - refusing"); return 1;
        }

        SetCursorPos(x, y); Thread.Sleep(120);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
        Thread.Sleep(40);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
        Console.WriteLine("clicked " + x + "," + y);
        return 0;
    }
}
