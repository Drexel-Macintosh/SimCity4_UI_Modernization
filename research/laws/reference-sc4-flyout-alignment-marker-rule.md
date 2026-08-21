# The Flyout Alignment-Marker Rule

## The rule

Every tool-flyout `.UI` script contains a hidden child with `id=0x0000AAAA` whose
size matches its spawn button. The game places the flyout at:

    flyoutPos = spawnButtonAbs - markerOffset

so once a subtree has been scaled to 2x, the correct dock target is:

    target = spawnButtonAbs - markerOffset(LIVE, i.e. already scaled)

This replaces per-flyout offset constants entirely. Eyeballed offsets and
screenshot tuning are unnecessary and unreliable; the marker is the game's own
placement input and is always available.

## Why the rule is trustworthy

Three independent confirmations:

- It reproduces all three locked, hand-tuned god-mode docks to the pixel:
  terraform (22,262), terrain-fx (22,502), day/night (22,742) — 7 for 7 across
  flyouts and modes.
- It predicts the game's native mayor-mode placement exactly: the Landscape
  marker (3,27) at 1x with a button absolute position of (28,398) yields
  (25,371), matching the measured placement.
- Two separate derivations agree on the same target (22,344): `button + 2R`
  where `R = native - buttonAbs`, and `button - marker2x`.

It also explains a special case a fixed-constant table cannot. The shared window
`0xCA35CBED` appears to need two different offsets (terrain-fx 40, day/night
160) because the container swaps SCRIPT, which moves the marker. The rule
handles both with no special case.

## Corollary: markers are positioning data — never scale them

Markers must not be scaled at runtime, and must not be scaled in shipped `.UI`
data either. Pre-scaling an advisor strip's whole subtree including its
`0x0000AAAA` marker causes the game — which reads the marker in native units —
to place the entire Advisors box shifted by exactly `-(markerOffset)`, i.e.
`-(229,63)`. `double_subtree_areas` in `build_selective_safe.py` skips
`id=0x0000AAAA` tags for this reason; any other data-side subtree scaling must
do the same.

## One window id can carry two scripts

`0x49923239` is both god/terraform (125x291 -> 250x582, marker (4,90)) and
mayor/Landscape Tools (125x249 -> 250x498, marker (3,27)). A single fixed offset
can never be right for both. Gate by mode (mayor HUD `0xE9889775` visible) or,
preferably, read the live marker.

## The marker's unit system must be measured, not assumed

The live marker's `GetL()`/`GetT()` are not reliably in screen units. The
invisible `0x0000AAAA` child is not always reached by its flyout's subtree
scale, and that state is permanent rather than a startup race. Measured live:
script `0xAB954023` marker (4,5) reads (8,10) — scaled; script `0x49923239`
marker (3,59) reads (3,59) — design units, still design units a second and many
sweep ticks later. Subtracting design units from a screen coordinate puts the
Landscape ring 59 px low, on the wrong circle.

Decide with `UiSpike::MarkerIsDesignUnits()`, which is a pure read of
`scaleMap`. Never call `Classify()` for this — it mutates the tug-of-war counter
and can tombstone a window merely for being asked.

Do not use the marker's size against its spawn button as the discriminator.
"The marker is sized like the spawn button" is true enough to mislead and false
in detail: one flyout's marker is 64 wide against a 47-unit design button,
scoring 34 vs 30. Size-based guessing fails silently. Ask the record of what was
scaled, not the geometry.

## How to apply

Measure with the `MCAL` log line: with `[Flyout] MayorDock=0` in the ini, the
DLL scales but never moves a mayor flyout, and prints the native position, the
spawn-button absolute position, the derived `R`, and the resulting target. Paste
`R` into `kMayorFlyoutDock` in `src\UiSpike.cpp` and set `derived=true`.

## Scope limit in mayor mode

Only Landscape reaches the flyout dock loop. Zones, Transportation, Utilities
and Civic fall through to the center-anchor branch of `ScalePanelRoot`, which
fires when both `gapT` and `gapB` exceed `frameH/4` and repositions the window
with no reference to its spawn button. Those flyouts are not "off by a
constant"; they are placed by an unrelated rule, and docking them requires
intercepting that path.

## Mayor-mode map (measured)

Buttons of toolbar `0x69E40A1F`, identified by position rather than enum order
— the dump enumerates children in reverse of `.UI` add order:

| # | Button | Id |
|---|--------|----|
| 1 | Landscape | `0x8991EE08` |
| 2 | Zones | `0x0991EE13` |
| 3 | Transportation | `0xA994824D` |
| 4 | Utilities | `0xE991EE2F` |
| 5 | Civic | `0x0991EE39` |
| 6 | Bulldoze | `0xE999C820` |
| 7 | Emergency | `0x6991EE42` |

Flyouts: Landscape `0x49923239`, Zones `0x69923479`, Transport `0xC99237A0`,
Utilities `0xE992F711`, Civic `0x699306ED`, Emergency `0x0992FD17`.

## The shared sub-flyout container `0x8A6E61E0`

Second-level menus (zone density, road types) do not follow the marker rule —
this container has no marker. Its own measured rules:

- **Placement law.** The game puts it at `nativeY = buttonCentreY - ringBltY - 29`
  and `nativeX = buttonAbsX + 20`, where `ringBltY` is where that particular menu
  blits its 1x ring sprite into the buffer. `ringBltY` varies per menu: 94 for
  zones and roads, 119 for rails. The older constant `btn + (20,-86)` was this
  same law evaluated at `ringBltY=94`, and it silently failed four transport
  menus (rails, depots and others). The DLL records `ringBltY` at blit time and
  computes the native position from the law. The dock delta `(-53,-24)` is
  menu-invariant, because native position and target both shift with `ringBltY`.
- **Height gate.** The container can be as short as 258x286, so the
  `destIsContainer` height gate must stay above 260, not above 300, or short
  menus get no 2x ring at all.
- **Identification.** Identify by exact width: `selfW == 258 && selfH >= 100`.
  Height-only gates miss the 258x206 Freight nested menu, leaving a 1x
  disconnected circle on that menu alone.
- **Shared class.** Its class is the disaster container `0x00AB6AA8` (strip child
  `0x00AB6D88`), so every disaster-container fix applies verbatim: buffer
  force-recreate for the 1x bar, strip item-field doubling for unseated icons,
  and ClaimScale + SelForce for right-half-only clicks.
- **Dock target.** Dock it to `btn + (-33,-110)` so the 2x ring lands on the
  button while ring, strip and bar stay welded — they are adjacent inside the
  buffer by construction, and moving the ring alone tears them apart.
- **`gBarDX=-53` is generic**, not a disaster-only tweak: it reflects one bar-art
  width, and because the bar is drawn flush right, widening it 2x overruns the
  buffer.
- **Ring nudge is derived, not dialled.** `SubRingDX=25`, `SubRingDY=-6` follow
  from the art: the 80x53 sprite is a keyring whose magenta hole (centre (25,26))
  must frame the button's off-centre ellipse (centre (21,15) within its 47x37
  cell). The button art being off-centre in its cell — not sprite padding — is
  why box-centre math lands 4-5 px off. Re-derive after any SubDock change with
  `python tools\flyout-sim\derive_subring.py`, which asserts the art and the
  expected values against the plain DBPF atlas `I-14215ed0..ed5`; no in-game
  dump is needed.

## Deep submenus (third-party plugin)

Deep submenus come from the third-party plugin `memo.submenus.dll` 2.1.0. Its
"back" action is a click on the physical button — the red arrow is only frame
art that happens to overlap the button at 1x — so clicks on the drawn arrow's
rect are forwarded to the button as a real OS click (`ArrowClick=1`). Its 55 own
Item Icons need 2x overrides: un-overridden 176x44 icons render duplicated in 2x
cells, because the game slices the strip by the doubled 88 px cell.

## Load-order law (proven live)

In the Documents plugins root, FILES load BEFORE subfolders, so a root `z_*.dat`
can never override a dat inside a subfolder. Overriding another Documents mod
requires a FOLDER that sorts after the target (`zzz-SC4UIScale\` beats
`150-mods\`); root packages only beat resources in the install directory. All
plugin-bound Item Icons (124 of them: 55 from the submenus mod plus 69
CAM/Maxis landmark icons) ship in
`zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat`, tier-gated.

When scanning plugin exemplars for Item Icons, parse BOTH exemplar formats:
roughly half of CAM's are TEXT exemplars, and binary-only parsing misses 30
icons.
