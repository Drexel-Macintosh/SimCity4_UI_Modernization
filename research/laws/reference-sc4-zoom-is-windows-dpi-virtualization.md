# The Zoomed-In Fault Is DPI Virtualization

A common report on high-DPI machines is that SimCity 4 looks "extremely zoomed
in" — the intro video, the loading screens, and the menu all appear magnified
and soft. This is Windows DPI virtualization, not a plugin, not a mod, and not
a graphics-wrapper setting. It can be confirmed with three registry/WMI reads
before any UI analysis is attempted.

## Instrument readings

Representative readings from an affected machine (a 2400x1600 panel running at
150% scaling):

| instrument | reading |
|---|---|
| `Win32_VideoController` (driver-reported, not virtualized) | panel = 2400 x 1600 |
| `HKCU\Control Panel\Desktop\WindowMetrics\AppliedDPI` | 144 = 150% scaling |
| `[Windows.Forms.Screen]` from a DPI-unaware process | 1600 x 1067 |
| `HKCU\...\AppCompatFlags\Layers` for `SimCity 4.exe` | `~ RUNASADMIN WINXPSP3` |

2400 / 1.5 = 1600 and 1600 / 1.5 = 1066.7: the virtualized desktop matches the
physical panel divided by the scale factor exactly. The driver mode and the
virtualized desktop metrics are two independent failure modes, so agreement
between them is genuine corroboration rather than one instrument read twice.

## Mechanism

The 2003 executable ships no DPI-awareness manifest, and the `WINXPSP3`
compatibility layer pins DPI virtualization on. Windows therefore renders the
whole window at the virtualized size and bitmap-stretches it by the scale
factor to fill the panel. Ask for 1024x768 and the result is 1536x1152 of
stretched pixels. This begins at the first frame — before any DLL, plugin, or
UI window exists.

## Why plugin-side hypotheses fail

The fault reproduces with zero plugins, at 1024x768 and at 1600x1200, windowed
and fullscreen, with and without a graphics wrapper such as dgVoodoo, and
across a clean reinstall — because none of those touch the shim. The shim lives
in `HKCU` keyed by executable path, so reinstalling to the same path re-arms it
immediately. Any investigation that varies plugins, resolution, or wrapper
settings is varying something the fault does not depend on.

## The split symptom

`SC4UIScaleDllDirector.cpp` calls `SetProcessDPIAware()` at DLL load. That is
far too late for the intro video and the loading screens, but early enough for
the game proper. So with the scaling plugin installed the videos are zoomed and
the game itself is not; with plugins removed nothing ever un-virtualizes and
the entire session stays zoomed. That asymmetry is diagnostic of the shim, and
is easily misread as "the mod is broken".

## Cure

Give the executable the `HIGHDPIAWARE` compatibility layer (Properties ->
Compatibility -> Change high DPI settings -> "Override high DPI scaling
behaviour: Application") and drop `WINXPSP3`. `RUNASADMIN` may be kept; it is
the reason the game runs elevated, which in turn is why the game holds the DLL
and DAT files open while running.

    HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers
      "<install>\Apps\SimCity 4.exe" = "~ RUNASADMIN HIGHDPIAWARE"

## Standing check

On any report that the whole screen is wrong, zoomed, or soft, read the compat
shim, `AppliedDPI`, and the physical display mode before touching the mod.
Three registry reads outrank any amount of UI-tree analysis. Re-check after
every reinstall or executable re-patch, since the shim outlives both.
