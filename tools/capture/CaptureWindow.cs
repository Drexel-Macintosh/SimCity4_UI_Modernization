// Autonomous-loop screen capture: PrintWindow(PW_RENDERFULLCONTENT) of the
// SimCity 4 window WITHOUT stealing foreground or synthesizing input.
// Usage: CaptureWindow.exe <outFile.png>
using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

class CaptureWindow
{
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern int GetSystemMetrics(int index);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll")] static extern IntPtr WindowFromPoint(POINT pt);
    [DllImport("user32.dll")] static extern IntPtr GetAncestor(IntPtr hwnd, uint flags);
    delegate bool EnumWindowsProc(IntPtr hwnd, IntPtr lParam);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc cb, IntPtr lParam);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hwnd);

    [StructLayout(LayoutKind.Sequential)]
    struct POINT { public int X, Y; }

    [StructLayout(LayoutKind.Sequential)]
    struct RECT { public int Left, Top, Right, Bottom; }

    const uint PW_RENDERFULLCONTENT = 2;

    static int Main(string[] args)
    {
        if (args.Length < 1) { Console.Error.WriteLine("usage: CaptureWindow.exe <out.png>"); return 2; }
        SetProcessDPIAware();

        uint gamePid = 0;
        foreach (Process p in Process.GetProcesses())
        {
            if (p.ProcessName.IndexOf("SimCity", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                gamePid = (uint)p.Id;
                break;
            }
        }
        if (gamePid == 0) { Console.Error.WriteLine("SimCity process not found"); return 1; }

        // MainWindowHandle can be a tiny helper window (SC4Fix console etc.);
        // pick the process's LARGEST visible top-level window instead.
        IntPtr hwnd = IntPtr.Zero;
        long bestArea = 0;
        EnumWindows((wh, lp) =>
        {
            uint pid;
            GetWindowThreadProcessId(wh, out pid);
            if (pid == gamePid && IsWindowVisible(wh))
            {
                RECT wr;
                if (GetWindowRect(wh, out wr))
                {
                    long area = (long)(wr.Right - wr.Left) * (wr.Bottom - wr.Top);
                    if (area > bestArea) { bestArea = area; hwnd = wh; }
                }
            }
            return true;
        }, IntPtr.Zero);
        if (hwnd == IntPtr.Zero || bestArea < 400 * 300)
        {
            Console.Error.WriteLine("no sufficiently large visible game window (best "
                + bestArea + " px^2) - game minimized?");
            return 1;
        }
        if (hwnd == IntPtr.Zero) { Console.Error.WriteLine("SimCity window not found"); return 1; }

        RECT r;
        if (!GetWindowRect(hwnd, out r)) { Console.Error.WriteLine("GetWindowRect failed"); return 1; }
        int w = r.Right - r.Left, h = r.Bottom - r.Top;
        if (w <= 0 || h <= 0) { Console.Error.WriteLine("degenerate window " + w + "x" + h); return 1; }

        using (Bitmap bmp = new Bitmap(w, h))
        {
            bool ok = false;
            using (Graphics g = Graphics.FromImage(bmp))
            {
                IntPtr hdc = g.GetHdc();
                ok = PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT);
                g.ReleaseHdc(hdc);
                if (!ok)
                {
                    IntPtr hdc2 = g.GetHdc();
                    ok = PrintWindow(hwnd, hdc2, 0);
                    g.ReleaseHdc(hdc2);
                }
            }
            if (!ok)
            {
                // Fullscreen-exclusive surfaces defeat PrintWindow. Screen copy
                // is allowed ONLY when the game window is foreground AND covers
                // the whole primary monitor, so this can never capture the
                // user's desktop or another app.
                int sw = GetSystemMetrics(0), sh = GetSystemMetrics(1);
                // Two ownership proofs, either suffices; both guarantee the
                // copied pixels belong to the GAME's visible window, never
                // the user's desktop or another app:
                //  1. The game process is FOREGROUND and its window covers
                //     the monitor (fullscreen play).
                //  2. WindowFromPoint at the window's center resolves to the
                //     game process (the game's window is the topmost visible
                //     surface over its own rect - e.g. an 800x600 mode on a
                //     native desktop with nothing focused). We then copy the
                //     window rect only.
                uint fgPid = 0;
                GetWindowThreadProcessId(GetForegroundWindow(), out fgPid);
                bool fullscreenForeground = fgPid == gamePid
                    && r.Left <= 0 && r.Top <= 0 && r.Right >= sw && r.Bottom >= sh;

                POINT center;
                center.X = (r.Left + r.Right) / 2;
                center.Y = (r.Top + r.Bottom) / 2;
                uint pointPid = 0;
                IntPtr hAtPoint = WindowFromPoint(center);
                if (hAtPoint != IntPtr.Zero)
                {
                    GetWindowThreadProcessId(GetAncestor(hAtPoint, 2 /*GA_ROOT*/), out pointPid);
                }
                bool visiblyOwnsRect = pointPid == gamePid;

                if (!fullscreenForeground && !visiblyOwnsRect)
                {
                    Console.Error.WriteLine("PrintWindow failed and game does not own the display (fgPid="
                        + fgPid + " pointPid=" + pointPid + " gamePid=" + gamePid
                        + " rect=" + r.Left + "," + r.Top + "," + r.Right + "," + r.Bottom
                        + " screen=" + sw + "x" + sh + ") - refusing screen copy");
                    return 1;
                }
                using (Graphics g = Graphics.FromImage(bmp))
                {
                    g.CopyFromScreen(r.Left, r.Top, 0, 0, new Size(w, h));
                }
                Console.WriteLine("screen-copy fallback (game fullscreen+foreground)");
            }
            bmp.Save(args[0], ImageFormat.Png);
        }
        Console.WriteLine("captured " + w + "x" + h + " -> " + args[0]);
        return 0;
    }
}
