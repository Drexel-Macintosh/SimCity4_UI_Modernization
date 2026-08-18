---
name: reference-sc4-windowed-mode-dgvoodoo
description: "SC4 windowed mode with a title bar you can drag is controlled by dgVoodoo's FullScreenMode, NOT by SC4's WindowMode. Setting WindowMode=Windowed alone does nothing while the wrapper forces fullscreen."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-14T16:47:19.118Z
---

**`WindowMode=Windowed` in `SC4GraphicsOptions.ini` IS NOT ENOUGH.** The
dgVoodoo wrapper overrides it and the game comes up borderless-fullscreen with
no title bar to drag.

The controlling setting lives in the WRAPPER, not the game:

    C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\dgVoodoo.conf
        FullScreenMode = true     <- forces fullscreen, overrides SC4 entirely
        CaptureMouse   = true     <- traps the cursor; you cannot reach the
                                     title bar to drag the window

Set BOTH to `false` for a real, movable OS window. ⚠ Write that file **without
a BOM** (same rule as every SC4 ini). Back it up first — `dgVoodooCpl.exe` sits
beside it and rewrites the file if launched.

⛔ **THIS USER SWAPS MONITORS. NEVER CARRY A RESOLUTION BETWEEN SESSIONS.**
Measured 3840x2160 at 11:41 on 2026-08-14 and **2400x1600 at 12:42 the same
day** — a monitor change mid-session silently moved the tier from 3.00 to 2.00
and made a whole diagnosis wrong (an 88px menu cell reads as "broken, should be
132" at 3x and "exactly right, 2x44" at 2x). **Read the tier from the log's own
`AutoScale: WxH -> tier` line for the run you are analysing**, not from memory,
not from the ini, and not from an earlier launch in the same session.

⚠ An earlier revision of this file called this a
"2400x1600 machine" — that was the SC4 *render* resolution left in the ini by a
test, read back as if it were the panel. Measure the panel, never the ini:
`Win32_VideoController` and DPI-unaware `Screen.Bounds` BOTH lie here (they
returned 2400x1600 and 1920x1080 — the latter is 3840x2160 halved by 200% DPI).
The honest probe is `SetProcessDPIAware()` then `GetSystemMetrics(0/1)`.
At 3840x2160 the cap is `min(4.8, 3.6)` = 3.6, so **3x is admitted natively**.

**MEASURED 2026-08-14**, once `FullScreenMode=false`:
a windowed border appears at **1024x768 AND at 2400x1800**, so the oversized
window is NOT what removes it — resolution is innocent, including sizes past
the desktop height and past DirectX 7's 2048 limit. A window taller than the
desktop simply hangs off the bottom and still drags.

## The tier arithmetic that goes with it

`ScaleTier::Decide` caps on `min(w/800, h/600)`, so the LOWEST resolution that
admits each tier is:

| tier | minimum resolution |
|---|---|
| 1.5x | 1320 x 900 |
| 2x   | 1760 x 1200 |
| 3x   | **2640 x 1800** |

⚠ **THE CAP IS ONLY HALF THE GATE — an earlier version of this table said
1200x900 / 1600x1200 / 2400x1800 and was WRONG ON WIDTH.** Those are the cap
figures alone. `Decide` ALSO tests fit against the largest 1x design pieces, so
the true minimum per axis is the LARGER of the two tests:

    width  >= max(880*f, 800*f)  ->  880*f always wins   (1320 / 1760 / 2640)
    height >= max(558*f, 600*f)  ->  600*f always wins   (900 / 1200 / 1800)

Width is set by the widest design piece, height by the density cap. Quoting
either constant alone gets one axis wrong every time. The same mistake shipped
to players in `_packaging\SC4UIScale.ini` as "1760x1116 for 2x, 2640x1674 for
3x" (the fit constants, understating both heights) — fixed 2026-08-14.
A 1920x1080 screen gets **1.5x**, not nothing.

The full 3x gate is three tests, not one — `Decide` also checks FIT against the
largest 1x design pieces (`kWidestDesignPx`=880, `kTallestDesignPx`=558):
`880f <= w && 558f <= h && f <= cap`. At 3840x2160 that is `2640 <= 3840`,
`1674 <= 2160`, `3.0 <= 3.6` — **3x passes on this machine under plain
AutoScale**, no forcing needed.

⚠ The ini's WindowWidth/Height is a RENDER REQUEST, not the panel and not
necessarily what gets rendered. It can legally exceed the desktop (and DirectX
7's 2048 limit). **A resolution in that file is NEVER evidence of what the
screen is.**

**WHICH NUMBER FEEDS `Decide` DEPENDS ON THE MODE** — measured in source at
`src\SC4UIScaleDllDirector.cpp:177-213`:

| Driver + WindowMode | resolution used for the tier |
|---|---|
| DirectX + FullScreen/Borderless | **monitor native** — ini request DISCARDED |
| DirectX + Windowed | the requested window size |
| Software (any mode) | the requested size |

In the FullScreen branch (`:190-198`) `gfxW/gfxH` are overwritten with
`GetSystemMetrics(SM_CXSCREEN/SM_CYSCREEN)` because dgVoodoo forces native mode
regardless of the request (the in-source note records `request 1600x1200 ->
tree is 2400x1600`). So on this machine, in the normal FullScreen config, the
ini resolution **cannot** change the tier — 3840x2160 always yields 3.0.

The tier CAN still be demoted by a small ini resolution, but only in **DirectX
Windowed** or **Software**, where the request is what renders. Do not
generalise the demotion warning to FullScreen; a wrong-but-plausible version of
this cost one wrong explanation on 2026-08-14.

`Set-Tier.ps1` accepts only `1.5`, `2`, `3`. **For 1x use
`Set-StockCompare.ps1 -Mode Stock -Width W -Height H`** — it disables the whole
layer and sets the resolution in one go, and `-Mode Ours` restores both.
See [[reference-sc4-resolution-control]].
