---
name: reference-sc4-subflyout-ring-law
description: "SC4 sub-flyout (0x8A6E61E0): the stem is PART of the ring sprite, and its Y (obj[0x104]/win[0x100] = our gSubRingBltY) is the ONE lever for where the flyout attaches — MEASURED via emu_plot, independent of the strip rect. Fix = container-to-model + ring-pinned, both halves or neither. #134: X IS now modelled — SubNativeDX = btnW/2-27 is NOT factor-independent (20 at f=2, 43 at f=3); the stale 20 desynced born-vs-sweep at 3x and killed the back-arrow zone. Ring nudges are derived per tier, never hand-entered. Two models died before this."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-05T16:43:54.309Z
---

**THE LAW.** The sub-flyout's stem is not a separate draw: the 80x53 ring
atlas cell is a keyring — annulus (magenta hole, the button shows through)
merging into a full-height connector wedge to the cell's right edge. Its Y
inside the container is the single quantity that decides where the flyout
attaches:

    ringY = (contentH >> 1) - ([0xF4] >> 1)      unclamped
          = cy - containerTop - [0x100]           general form

⚠ `(a>>1) - (b>>1)`, **NOT** `(a-b)>>1` — off by one on the rails menu.
Verified 4/4, zero residual (zones 94, rails 119, 8-item 192, disaster 138).
Stored at `obj[0x104]` / `win[0x100]`; **we already record it live as
`gSubRingBltY`** (`UiSpike.cpp:1505`), and it is **latched per open from the
1x contentH** — never recomputed from the live rect.

**WHY THE STRIP LOOKS FIXED IN STOCK.** Unclamped, `cy - top` is constant so
ringY is constant and the whole assembly tracks the button. Once a
screen-margin clamp pins `top`, `cy` keeps moving and **ringY absorbs the
difference: the strip stays put, only the ring+wedge slides.** The game's
last two clamps exist purely to keep ringY between the bar's end caps —
meaningless unless ringY is live per selection. User stated this before we
measured it: *"The flyout never moves — just where it attaches should."*

**INDEPENDENCE:** `stripTop = (contentH - stripH)>>1` and `stripLeft` carry
NO `cy` and no per-selection term. ringY is the only term with the button
centre ⇒ the attachment moves without moving the strip.

**✅ MEASURED, not inferred (v2.46.0, `tools\flyout-sim\emu_plot.py`).** Four
runs with `[0x100]` = 138 / 200 / 0 / 417 put the ring blit at exactly
y = 138 / 200 / 0 / 417; the three BAR rects were **byte-identical** every
time, and `[0xF4]` 6→12 moved the ring not at all. `win[0x100]` is the SOLE
stem-Y input at blit time and cannot touch the strip.

**THE SHIPPED FIX = BOTH HALVES IN ONE ACTION** (either alone is a revert):
container → the game's own clamped `SubPlaceTop()` at f; ring sprite →
offset by MINUS that move (`gSubRingAutoY`), pinning it where it already
draws.

**⚠ #134 SUPERSEDES THE OLD "X IS NOT MODELLED" CLAUSE (v2.86.0,
2026-08-05).** X *is* modelled now, and the old note had the danger exactly
backwards. The real defect was **`kSubNativeDX = 20`, commented
"factor-independent" — it is not.** The game seats the container 27px left of
the button CENTRE, so the offset grows with the button:

    SubNativeDX = btnW/2 - 27      94/2-27 = 20 (f=2)   141/2-27 = 43 (f=3)

MEASURED by the `SUBCAND` instrument at 3840x2160: `BTN(237,300 141x111)`,
game's own native `(280,207)`, `NATDX=43`. Halving is on the SCALED width —
`rhu(47f)/2` = 70 at f=3; `rhu(47f/2)` = 71 and misses by one.

**The stale 20 broke the coupled pair.** Born (`SUBBORN2`) docks from the
game's REAL native; the sweep predicts native as `buttonX + kSubNativeDX`. At
f=2 those agree, so 2x was always right. At f=3 they differed by 23px, so the
container rested 23px right of the law AND the sweep matched **neither**
`atNative` nor `atTarget` — it silently declined every 3x sub-flyout and
never ran. `gSubArrowAbs` (the back-arrow click zone) is assigned ONLY inside
that sweep, so **3x had a dead back-arrow zone nobody had reported.** The
visible ring offset and the invisible dead zone were one bug.

Ring nudges are now DERIVED per tier (`SubRingDXEff/DYEff`), the container
offset cancelling out of both axes:

    SubRingDX(f) = rhu(21f) - rhu(25f) - rhu(-16.5f)
    SubRingDY(f) = rhu(15f) - rhu(37f)/2 + rhu(26.5f) - rhu(26f)
    f=1.5: 19/-4    f=2: 25/-6 (reproduces shipped)    f=3: 37/-8

Gate: `tools\flyout-sim\gate_subnative.py` — predicts the game's measured
`(280,207)` from the button alone, 10 negative controls, all detecting.
A one-file ini can never be right at three tiers: **do not hand-enter
`SubRingDX/DY` again.** Whatever moves the sprite must also move the zone.

**⛔ #135 — `SubRingDX` MUST BE ZERO. THE WELD IS THE INVARIANT (v2.87.0).**
The ring, strip and bar are ONE shape in the buffer: ring spans `0..80f`, the
strip starts at exactly `80f`. **The ring's right edge IS the strip's left
edge.** So *any* non-zero `SubRingDX` drives the connector wedge that many px
INTO the panel, and the wedge's own top/bottom border lines then terminate
mid-panel — a visible "broken bar at the junction". User-reported and
user-confirmed present at **2x for months** (`SubRingDX=25`), simply tolerated;
it was never 3x-specific.

The alignment is now carried entirely by the DOCK, which moves the whole
assembly and keeps the weld:

    SubDockDX(f) = rhu(21f) - rhu(25f) - SubNativeDX()   -14 / -28 / -55
    SubRingDX(f) = 0 at every tier

⚠ This CHANGED two long-shipped f=2 constants on purpose (`-53 -> -28`,
`25 -> 0`) and moves the 2x assembly ~25px right. **If a gate ever reads -53
or 25 again, someone reverted the fix — that is not a baseline.**

This is the law's own rule finally applied: *"applying that delta to the RING
alone centres it but tears it off the strip/bar; applying it to the CONTAINER
moves the whole assembly together, so the ring seats on the button AND stays
joined."* Seating a ring by nudging the sprite is ALWAYS wrong — if the ring
is off its button, **the dock is wrong, fix that.**

Y is deliberately exempt: vertical ring-slide is the GAME's own mechanism
(ringY absorbs the screen clamp, `gSubRingAutoY`), so it has stock precedent.
Horizontal slide has none.

**THE DISASTER FAMILY HAD THE SAME BUG, IN THE INI.** Live
`[Disaster] RingDX=16 DockX=-2` vs the DLL's own defaults `RingDX=0 DockX=6`
(`UiSpike.cpp:1556/1558`). Those two configs put the RING in a BIT-IDENTICAL
screen position at every tier — `DockX` is tier-scaled (`ScaleRound`) and
`8*f` exactly cancels the seat-scaled `RingDX` — so the dial bought nothing
but moved the STRIP 16px (2x) / 24px (3x), driving the ring's neck into it.
That is the junction "lip". Fix = restore `RingDX=0 DockX=6`; **live-tunable,
no rebuild** (the `[Disaster]` RingDX/RingDY/DockX are re-read every ~20
sweeps). The SHIPPED `_packaging` ini carries neither key, so the public build
was never affected — this was a dev-ini-only defect.
Only two ring-X nudges exist in the codebase (`gRingDX`, `gSubRingDX`); both
are zero now. Ring sprites differ per family: mayor 80x53, disaster 94x62.

⚠ Do NOT reach for `LayerFix=1`. `REGRESSION.md:178-185` records that the
bar-tile replay is what opened the disaster family's junction gap, and the
sub-flyout family never drains `gBarCache` at all (`UiSpike.cpp:1584`) — the
mechanism is unrelated to this seam.

**LEVERS, each verified to touch only what is listed:** `gSubRingDX/DY` =
the ring+wedge sprite at blit time (ring only; `gSubRingBltX/Y` stay RAW
pre-offset so the dock law/`ringFresh` are unaffected) · `gBarDX`/`BarWiden`
= bar X only, Y never scaled · `gStripFieldScale` = item metrics only ·
`SubDockDX/DY` = the WHOLE assembly. We scale the strip rect ourselves at
`UiSpike.cpp:3931` ((80,25) game, (160,50) ours).

**⛔ TWO DEAD MODELS — each cost a shipped-and-reverted build:**
1. *"`cy` in `sub_79AD00` is the SELECTED button's centre."* FALSE — a stock
   capture of three pickers with buttons ~60px apart shows the strip in the
   SAME band. `cy` is the MENU anchor.
2. *"Move the container to fix a strip that overflows."* The ring is a
   latched blit INSIDE the container, so moving it slides the ring off the
   button 1:1 (v2.45.0, reverted same session). Our own source had said so
   since v2.15.0: *"ORIGIN STAYS PUT... scaling it UNDOCKED the circle."*

Related: [[feedback-sc4-scaling-laws]] law 42 (a gate is only as honest as
its scope — a 32/32 emulator pass proved the arithmetic on a mis-identified
input), [[reference-sc4-flyout-alignment-marker-rule]] (the OTHER family:
script flyouts dock by `buttonAbs - marker`, a different law entirely).
