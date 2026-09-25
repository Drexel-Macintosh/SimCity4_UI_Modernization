$src = @'
using System;
using System.Runtime.InteropServices;
using System.Diagnostics;
using System.Collections.Generic;

public static class ED {
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public struct DEVMODE {
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmDeviceName;
    public short dmSpecVersion; public short dmDriverVersion; public short dmSize; public short dmDriverExtra;
    public int dmFields; public int dmPositionX; public int dmPositionY; public int dmDisplayOrientation; public int dmDisplayFixedOutput;
    public short dmColor; public short dmDuplex; public short dmYResolution; public short dmTTOption; public short dmCollate;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmFormName;
    public short dmLogPixels; public int dmBitsPerPel; public int dmPelsWidth; public int dmPelsHeight;
    public int dmDisplayFlags; public int dmDisplayFrequency; public int dmICMMethod; public int dmICMIntent;
    public int dmMediaType; public int dmDitherType; public int dmReserved1; public int dmReserved2;
    public int dmPanningWidth; public int dmPanningHeight;
  }
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public struct DISPLAY_DEVICE {
    public int cb;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string DeviceName;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceString;
    public int StateFlags;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceID;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceKey;
  }
  [DllImport("user32.dll", CharSet = CharSet.Unicode)]
  public static extern bool EnumDisplaySettingsW(string dev, int mode, ref DEVMODE dm);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)]
  public static extern bool EnumDisplaySettingsExW(string dev, int mode, ref DEVMODE dm, int flags);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)]
  public static extern bool EnumDisplayDevicesW(string dev, int i, ref DISPLAY_DEVICE dd, int flags);

  public static string Run(int flags) {
    var sb = new System.Text.StringBuilder();
    var dm = new DEVMODE(); dm.dmSize = (short)Marshal.SizeOf(typeof(DEVMODE));
    var sw = Stopwatch.StartNew();
    bool ok0 = (flags < 0) ? EnumDisplaySettingsW(null, 0, ref dm) : EnumDisplaySettingsExW(null, 0, ref dm, flags);
    double t0 = sw.Elapsed.TotalMilliseconds;
    int n = ok0 ? 1 : 0;
    var distinct = new HashSet<string>(); var bpp = new Dictionary<int,int>(); var fixo = new Dictionary<int,int>(); var hz = new HashSet<int>();
    double slowest = 0; int slowIdx = -1;
    if (ok0) { distinct.Add(dm.dmPelsWidth + "x" + dm.dmPelsHeight); }
    for (int i = 1; ; i++) {
      double a = sw.Elapsed.TotalMilliseconds;
      bool ok = (flags < 0) ? EnumDisplaySettingsW(null, i, ref dm) : EnumDisplaySettingsExW(null, i, ref dm, flags);
      double d = sw.Elapsed.TotalMilliseconds - a;
      if (d > slowest) { slowest = d; slowIdx = i; }
      if (!ok) break;
      n++;
      distinct.Add(dm.dmPelsWidth + "x" + dm.dmPelsHeight);
      int b; bpp.TryGetValue(dm.dmBitsPerPel, out b); bpp[dm.dmBitsPerPel] = b + 1;
      int f; fixo.TryGetValue(dm.dmDisplayFixedOutput, out f); fixo[dm.dmDisplayFixedOutput] = f + 1;
      hz.Add(dm.dmDisplayFrequency);
    }
    double total = sw.Elapsed.TotalMilliseconds;
    sb.AppendFormat("flags={0}: calls={1} modes={2} distinctWxH={3} first(i=0)={4:F1}ms rest={5:F1}ms total={6:F1}ms slowestNonZero={7:F2}ms@{8}\n", flags, n + 1, n, distinct.Count, t0, total - t0, total, slowest, slowIdx);
    sb.Append("  bpp:"); foreach (var kv in bpp) sb.AppendFormat(" {0}={1}", kv.Key, kv.Value);
    sb.Append("  fixedOutput:"); foreach (var kv in fixo) sb.AppendFormat(" {0}={1}", kv.Key, kv.Value);
    sb.Append("  hz:"); foreach (var h in hz) sb.AppendFormat(" {0}", h);
    sb.Append("\n");
    return sb.ToString();
  }
  public static string Special() {
    var sb = new System.Text.StringBuilder();
    var dm = new DEVMODE(); dm.dmSize = (short)Marshal.SizeOf(typeof(DEVMODE));
    var sw = Stopwatch.StartNew();
    bool ok = EnumDisplaySettingsW(null, -1, ref dm);
    sb.AppendFormat("ENUM_CURRENT_SETTINGS {0} {1}x{2} {3}bpp {4}Hz in {5:F2}ms\n", ok, dm.dmPelsWidth, dm.dmPelsHeight, dm.dmBitsPerPel, dm.dmDisplayFrequency, sw.Elapsed.TotalMilliseconds);
    sw.Restart();
    ok = EnumDisplaySettingsW(null, -2, ref dm);
    sb.AppendFormat("ENUM_REGISTRY_SETTINGS {0} {1}x{2} in {3:F2}ms\n", ok, dm.dmPelsWidth, dm.dmPelsHeight, sw.Elapsed.TotalMilliseconds);
    for (int i = 0; ; i++) {
      var dd = new DISPLAY_DEVICE(); dd.cb = Marshal.SizeOf(typeof(DISPLAY_DEVICE));
      if (!EnumDisplayDevicesW(null, i, ref dd, 0)) break;
      sb.AppendFormat("adapter[{0}] {1} '{2}' flags=0x{3:X}\n", i, dd.DeviceName, dd.DeviceString, dd.StateFlags);
    }
    return sb.ToString();
  }
}
'@
Add-Type -TypeDefinition $src -Language CSharp
[ED]::Special()
[ED]::Run(-1)
[ED]::Run(-1)
[ED]::Run(0)
[ED]::Run(2)
