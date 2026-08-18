// Holds the display awake while running (no system settings touched).
// Used by the autonomous capture loop: the panel powering off at night
// kicks the fullscreen game out of exclusive mode (auto-minimize), making
// captures impossible. Kill this process to release the hold.
using System;
using System.Runtime.InteropServices;
using System.Threading;

class KeepDisplayOn
{
    [DllImport("kernel32.dll")]
    static extern uint SetThreadExecutionState(uint flags);

    const uint ES_CONTINUOUS = 0x80000000;
    const uint ES_DISPLAY_REQUIRED = 0x00000002;
    const uint ES_SYSTEM_REQUIRED = 0x00000001;

    static void Main()
    {
        SetThreadExecutionState(ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED);
        Console.WriteLine("display hold active - kill to release");
        Thread.Sleep(Timeout.Infinite);
    }
}
