# The Sub-Flyout Ring Law

The sub-flyout family (window id `0x8A6E61E0`) draws its stem as part of the ring
sprite, not as a separate element. The 80x53 atlas cell is a keyring: an annulus
with a magenta hole (the button underneath shows through) merging into a
full-height connector wedge that runs to the cell's right edge. Ring sprites
differ per family — mayor-mode 80x53, disaster 94x62.

## The one lever

The ring's Y inside the container is the single quantity that decides where the
flyout attaches:

    ringY = (contentH >> 1) - ([0xF4] >> 1)      unclamped
          = cy - containerTop - [0x100]           general form

The halving detail matters: `(a>>1) - (b>>1)`, **not** `(a-b)>>1`. The two forms
differ by one on the rails menu. The closed form reproduces four captured menus
with zero residual (zones 94, rails 119, eight-item 192, disaster 138).

The value lives at `obj[0x104]` / `win[0x100]`, is recorded live as
`gSubRingBltY` (`UiSpike.cpp:1505`), and is **latched per open from the 1x
`contentH`** — never recomputed from the live rect.

### Why the strip looks fixed in stock

Unclamped, `cy - containerTop` is constant, so `ringY` is constant and the whole
assembly tracks the button. Once a screen-margin clamp pins `containerTop`, `cy`
keeps moving and `ringY` absorbs the difference: the strip stays put and only the
ring and wedge slide. The game's last two clamps exist purely to keep `ringY`
between the bar's end caps, which is meaningless unless `ringY` is live per
selection. The observable behaviour is exactly that — the flyout does not move,
only where it attaches.

### Independence of the strip

`stripTop = (contentH - stripH) >> 1` and `stripLeft` carry no `cy` term and no
per-selection term. `ringY` is the only quantity containing the button centre,
so the attachment point moves without moving the strip.

### Measured, not inferred

`tools\flyout-sim\emu_plot.py` drives the emulated blit path directly. Four runs
with `[0x100]` set to 138 / 200 / 0 / 417 placed the ring blit at exactly
y = 138 / 200 / 0 / 417; the three bar rects were byte-identical every time, and
changing `[0xF4]` from 6 to 12 moved the ring not at all. `win[0x100]` is the
sole stem-Y input at blit time and cannot touch the strip.

### The vertical fix is two halves or nothing

Applying either half alone is a revert. The container goes to the game's own
clamped `SubPlaceTop()` evaluated at factor `f`; the ring sprite is offset by
minus that same move (`gSubRingAutoY`), pinning it where it already draws.

## The X term is not factor-independent

The container is seated 27px left of the button *centre*, so the horizontal
offset grows with the button:

    SubNativeDX = btnW/2 - 27      94/2 - 27 = 20 (f=2)    141/2 - 27 = 43 (f=3)

Measured with the `SUBCAND` instrument at 3840x2160: `BTN(237,300 141x111)`, the
game's own native placement `(280,207)`, `NATDX=43`. The halving is on the
*scaled* width — `rhu(47f)/2` is 70 at f=3, while `rhu(47f/2)` is 71 and misses
by one. (`rhu()` is the project-wide round-half-up scaling helper; one rounding
convention everywhere.)

A hard-coded `kSubNativeDX = 20`, commented "factor-independent", breaks a
coupled pair. Born-scaled placement (`SUBBORN2`) docks from the game's real
native position, while the sweep predicts native as `buttonX + kSubNativeDX`. At
f=2 those agree, so 2x looks correct forever. At f=3 they differ by 23px: the
container rests 23px right of the law, *and* the sweep matches neither
`atNative` nor `atTarget`, so it silently declines every 3x sub-flyout and never
runs. `gSubArrowAbs` — the back-arrow click zone — is assigned only inside that
sweep, so 3x also has a dead back-arrow zone that no visual inspection reports.
The visible ring offset and the invisible dead zone are one bug.

Ring nudges are therefore **derived per tier** (`SubRingDXEff` / `SubRingDYEff`),
with the container offset cancelling out of both axes:

    SubRingDX(f) = rhu(21f) - rhu(25f) - rhu(-16.5f)
    SubRingDY(f) = rhu(15f) - rhu(37f)/2 + rhu(26.5f) - rhu(26f)
    f=1.5: 19 / -4      f=2: 25 / -6      f=3: 37 / -8

`tools\flyout-sim\gate_subnative.py` predicts the game's measured `(280,207)`
from the button rect alone and carries ten negative controls, all detecting. A
single-file ini value cannot be right at three tiers, so `SubRingDX/DY` must
never be hand-entered. Whatever moves the sprite must also move the click zone.

## The weld is the invariant: SubRingDX must be zero

Ring, strip and bar are one shape in the buffer. The ring spans `0..80f` and the
strip starts at exactly `80f`: the ring's right edge *is* the strip's left edge.
Any non-zero `SubRingDX` therefore drives the connector wedge that many pixels
into the panel, and the wedge's own top and bottom border lines terminate
mid-panel — the visible "broken bar at the junction". This is not tier-specific;
it is present at 2x whenever `SubRingDX` is non-zero.

Horizontal alignment is carried entirely by the dock, which moves the whole
assembly and preserves the weld:

    SubDockDX(f) = rhu(21f) - rhu(25f) - SubNativeDX()      -14 / -28 / -55
    SubRingDX(f) = 0 at every tier

This intentionally supersedes two earlier f=2 constants (`-53` becomes `-28`,
`25` becomes `0`) and shifts the 2x assembly about 25px right. A gate that reads
`-53` or `25` is reading a reverted fix, not a baseline.

Seating a ring by nudging the sprite is always wrong: applying a delta to the
ring alone centres it but tears it off the strip and bar, while applying the same
delta to the container moves the whole assembly together, so the ring seats on
the button *and* stays joined. If the ring is off its button, the dock is wrong —
fix the dock.

Y is deliberately exempt. Vertical ring-slide is the game's own mechanism
(`ringY` absorbing the screen clamp, mirrored by `gSubRingAutoY`), so it has
stock precedent. Horizontal slide has none.

## The same bug expressed as configuration

A development ini carrying `[Disaster] RingDX=16 DockX=-2` against the DLL's own
defaults `RingDX=0 DockX=6` (`UiSpike.cpp:1556` / `1558`) puts the *ring* in a
bit-identical screen position at every tier: `DockX` is tier-scaled through
`ScaleRound`, and `8*f` exactly cancels the seat-scaled `RingDX`. The dial buys
nothing but moves the *strip* 16px at 2x and 24px at 3x, driving the ring's neck
into it. That is the junction "lip". The cure is to restore `RingDX=0 DockX=6`;
the `[Disaster]` `RingDX` / `RingDY` / `DockX` keys are re-read roughly every 20
sweeps, so this is live-tunable with no rebuild. The shipped `_packaging` ini
carries neither key, so released builds are unaffected.

Only two ring-X nudges exist in the codebase — `gRingDX` and `gSubRingDX` — and
both are zero.

`LayerFix=1` is not the lever for this seam. The bar-tile replay is what opens
the disaster family's junction gap, and the sub-flyout family never drains
`gBarCache` at all (`UiSpike.cpp:1584`), so that mechanism cannot be the cause
here.

## Levers, each verified to touch only what is listed

- `gSubRingDX` / `gSubRingDY` — the ring-plus-wedge sprite at blit time, ring
  only. `gSubRingBltX` / `gSubRingBltY` stay raw and pre-offset, so the dock law
  and `ringFresh` are unaffected.
- `gBarDX` / `BarWiden` — bar X only; bar Y is never scaled.
- `gStripFieldScale` — item metrics only.
- `SubDockDX` / `SubDockDY` — the whole assembly.

The strip rect is scaled explicitly at `UiSpike.cpp:3931`: the game's `(80,25)`
becomes `(160,50)` at f=2.

## Two models that do not survive measurement

1. *"`cy` in `sub_79AD00` is the selected button's centre."* False. A stock
   capture of three pickers whose buttons are roughly 60px apart shows the strip
   in the same band each time. `cy` is the menu anchor.
2. *"Move the container to fix a strip that overflows."* The ring is a latched
   blit inside the container, so moving the container slides the ring off its
   button 1:1. The origin stays put; scaling it undocks the circle.

Related: a gate is only as honest as its scope — a 32/32 emulator pass can prove
the arithmetic while running on a mis-identified input. And this law governs one
family only: script flyouts belong to the alignment-marker rule and dock by
`buttonAbs - marker`, which is a different law entirely.
