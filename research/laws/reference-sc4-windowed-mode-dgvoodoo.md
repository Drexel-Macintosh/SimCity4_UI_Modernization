# Windowed Mode and the dgVoodoo Wrapper

`WindowMode=Windowed` in `SC4GraphicsOptions.ini` is not enough on an
installation that runs through the dgVoodoo DirectX wrapper. The wrapper
overrides the game's request and the title comes up borderless-fullscreen with
no title bar to drag.

The controlling settings live in the wrapper, not in the game:

    <SC4 install>\Apps\dgVoodoo.conf
        FullScreenMode = true     <- forces fullscreen, overrides SC4 entirely
        CaptureMouse   = true     <- traps the cursor, so the title bar is
                                     unreachable even when one exists

Both must be `false` for a real, movable OS window. Two rules apply when
editing that file:

- Write it **without a BOM**, the same rule that applies to every SC4 ini.
- Back it up first. `dgVoodooCpl.exe` sits beside it and rewrites the file
  whenever it is launched, discarding hand edits.

Once `FullScreenMode=false`, a windowed border appears at every render size
tested, from 1024x768 up to 2400x1800. Window size is not what removes the
border, including sizes past the desktop height and past DirectX 7's 2048
limit — a window taller than the desktop simply hangs off the bottom and still
drags.

`_tests\Set-Tier.ps1` performs the whole transition in one call, setting the
tier, the render resolution, and both wrapper keys together:

    .\_tests\Set-Tier.ps1 -Tier 1 -Windowed
    .\_tests\Set-Tier.ps1 -Tier 1 -Windowed -Width 1280 -Height 1024
    .\_tests\Set-Tier.ps1 -Auto -FullScreen -Width 2400 -Height 1600

It accepts `1`, `1.5`, `2`, `3`. The screen is part of the tier: a 1x baseline
on a very large desktop is not a reference, because every stock widget is
correct-but-tiny there and formatting — the only reason anyone asks for 1x —
goes unanswered. Judge 1x at a resolution the stock UI was drawn for.

## Read the tier from the run's own log line

Take the active tier from the `AutoScale: WxH -> tier` line emitted by the run
being analysed. Not from memory, not from the ini, and not from an earlier
launch. A resolution change between runs silently moves the tier, and the same
measurement then reads as a defect or as correct depending on which tier is
assumed: an 88px menu cell is "broken, should be 132" at 3x and "exactly right,
2x44" at 2x.

The ini's `WindowWidth`/`WindowHeight` is a **render request**, not the panel
and not necessarily what is rendered. It can legally exceed the desktop and
DirectX 7's 2048 limit. A resolution in that file is never evidence of what the
screen is.

Panel probes lie under DPI scaling. `Win32_VideoController` reports the render
resolution left in the ini rather than the panel, and a DPI-unaware
`Screen.Bounds` reports a 3840x2160 panel as 1920x1080 under 200% DPI. The
honest probe is `SetProcessDPIAware()` followed by
`GetSystemMetrics(SM_CXSCREEN/SM_CYSCREEN)`.

## Which number feeds the tier decision

Measured in source at `src\SC4UIScaleDllDirector.cpp:177-213`:

| Driver + WindowMode | resolution used for the tier |
|---|---|
| DirectX + FullScreen/Borderless | **monitor native** — the ini request is discarded |
| DirectX + Windowed | the requested window size |
| Software (any mode) | the requested size |

In the FullScreen branch (`:190-198`) `gfxW/gfxH` are overwritten with
`GetSystemMetrics(SM_CXSCREEN/SM_CYSCREEN)`, because dgVoodoo forces native
mode regardless of the request — a request for 1600x1200 still produces a
2400x1600 window tree. In the normal FullScreen configuration the ini
resolution therefore **cannot** change the tier.

The tier can still be demoted by a small ini resolution, but only in **DirectX
Windowed** or **Software**, where the request is what renders. Do not
generalise the demotion behaviour to FullScreen.

## Tier arithmetic

`ScaleTier::Decide` applies three tests, not one: a density cap on
`min(w/800, h/600)`, and a fit test against the largest 1x design pieces
(`kWidestDesignPx` = 880, `kTallestDesignPx` = 558):

    880*f <= w  &&  558*f <= h  &&  f <= min(w/800, h/600)

The true minimum per axis is the larger of the two tests, and each axis is
governed by a different constant:

    width  >= max(880*f, 800*f)  ->  880*f always wins   (1320 / 1760 / 2640)
    height >= max(558*f, 600*f)  ->  600*f always wins   (900 / 1200 / 1800)

Width is set by the widest design piece; height by the density cap. Quoting
either constant alone gets one axis wrong every time — quoting the cap alone
understates width, quoting the fit constants alone understates height.

| tier | minimum resolution |
|---|---|
| 1.5x | 1320 x 900 |
| 2x   | 1760 x 1200 |
| 3x   | 2640 x 1800 |

A 1920x1080 screen therefore gets 1.5x, not nothing. At 3840x2160 the cap is
`min(4.8, 3.6)` = 3.6 and the fit tests are `2640 <= 3840` and `1674 <= 2160`,
so 3x is admitted natively under plain AutoScale with no forcing.
