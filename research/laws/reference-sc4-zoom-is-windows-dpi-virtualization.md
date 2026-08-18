---
name: reference-sc4-zoom-is-windows-dpi-virtualization
description: "The SC4 'everything is extremely zoomed in' fault (intro video, loading screens, menu) is Windows DPI VIRTUALIZATION, not a plugin and not our mod. Panel is 2400x1600 at 150% (AppliedDPI 144); the 2003 exe is DPI-unaware and carried a WINXPSP3 compat shim, so Windows renders it small and bitmap-stretches 1.5x. Cure = HIGHDPIAWARE compat layer. Lives in HKCU so it SURVIVES REINSTALLS."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-05T19:33:07.025Z
---

# The "extremely zoomed in" SC4 fault = Windows DPI virtualization

**MEASURED 2026-08-05**, after it survived a full game reinstall and a
zero-plugin launch:

| instrument | reading |
|---|---|
| `Win32_VideoController` (driver, not virtualized) | panel = **2400 x 1600** (Intel Iris Xe) |
| `HKCU\Control Panel\Desktop\WindowMetrics\AppliedDPI` | **144 = 150% scaling** |
| `[Windows.Forms.Screen]` from DPI-unaware PowerShell | **1600 x 1067** |
| `HKCU\...\AppCompatFlags\Layers` for `SimCity 4.exe` | **`~ RUNASADMIN WINXPSP3`** |

2400/1.5 = 1600 and 1600/1.5 = 1066.7 — the virtualized desktop matches the
physical panel over 1.5 **exactly**. These are two INDEPENDENT failure modes
(driver mode vs. virtualized desktop metrics), so they corroborate properly —
see [[feedback-blind-instruments-agreeing]].

**MECHANISM.** SC4's 2003 exe has no DPI-awareness manifest, and `WINXPSP3`
compatibility mode pins DPI virtualization ON. Windows therefore renders the
whole window at the virtualized size and **bitmap-stretches it 1.5x** to the
panel. Ask for 1024x768 and you get 1536x1152 of stretched pixels. This starts
at the **first frame** — before any DLL, plugin, or UI window exists.

**WHY EVERY EARLIER HYPOTHESIS FAILED.** It reproduces with zero plugins, at
1024x768 and 1600x1200, windowed and fullscreen, with and without dgVoodoo, in
July captures and today, and through a clean reinstall — because none of those
touch the shim. The shim lives in **HKCU keyed by exe path**, so a reinstall to
the same path re-arms it instantly. The user said "NOTHING IN THE INSTALL IS
DOING IT THE GAME IS FROM 2003" and was right on both counts.

**IT ALSO EXPLAINS THE SPLIT SYMPTOM.** `SC4UIScaleDllDirector.cpp` calls
`SetProcessDPIAware()` at DLL load — far too late for the intro video and
loading screens, but early enough for the game proper. So WITH our mod the
videos are zoomed and the game is not; with plugins removed nothing ever
un-virtualizes and the whole session stays zoomed. That asymmetry was
diagnostic and got read as "the mod is broken" instead.

**THE CURE:** give the exe the `HIGHDPIAWARE` compat layer (Properties ->
Compatibility -> Change high DPI settings -> "Override high DPI scaling
behaviour: Application"), and drop `WINXPSP3`. Keep `RUNASADMIN` if wanted —
that is why the game runs elevated ([[feedback-sc4-deploy-on-close]]).

    HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers
      "<install>\Apps\SimCity 4.exe" = "~ RUNASADMIN HIGHDPIAWARE"

**STANDING CHECK:** on any "the whole screen is wrong / zoomed / soft" report,
read the compat shim + AppliedDPI + physical mode BEFORE touching the mod. It
is three registry reads and it outranks any amount of UI-tree analysis. Also
re-check it after any reinstall or exe re-patch, since the shim outlives both.

Related: [[project-sc4-ui-scaling-northstar]],
[[feedback-sc4-plugins-scan-is-recursive]] (the other false premise from the
same session), [[reference-sc4-resolution-control]].
