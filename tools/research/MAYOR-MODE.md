# MAYOR-MODE — city-mode UI scaling mechanisms

City mode is everything the game shows once a city is loaded: the mayor
toolbar and its flyouts, the second-level menus, the query panels, the news
reader and ticker, the advisors, the budget, Data Views, U-Drive-It, and the
founded-city god tools. This file records the mechanism behind each one —
which code path reaches the window, what the measured geometry is, and which
list or builder owns the fix.

City HUD `.UI` scripts live in group `0x96a006b0`, with `0x08000600` 800x600
twins.

Companion references: `tools\research\GOD-MODE-FLYOUTS.md` (pre-founding god
tools), `tools\research\ITEMICONS.md` (code-bound button art),
`tools\research\DYNAMIC-CONTROLS.md` (code-repopulated controls),
`tools\research\CITY-DOCK-OVERLAP.md` (window-tree enumeration order).

---

## 1. The two paths a city window can take

`ScalePanelsUnder(pView, "city")` in `src\UiSpike.cpp` walks the DIRECT
VISIBLE CHILDREN of `SC4View3DWin` (`0x9A47B417`) and runs `ScalePanelRoot` on
each. The city pass is the inverse of the region pass: region is
whitelist-only (`isRegionPass && !IsRegionPanelId` → skip), while city scales
everything visible that is not explicitly excluded.

The second path is DATA. A window parented to the MAIN WINDOW
(parent `0x00000000`) is a SIBLING of the app window, and the app window holds
only the view — so the city sweep never reaches it and it renders at pure 1x
stock. Those windows are collision-free static-double targets: the `.UI`
script ships pre-doubled and no runtime scaling touches it.

Choosing between the two starts with parentage. Verify it per window with the
live-dump diagnostic (`LiveDumpMs`) before picking a mechanism.

### The 1x→2x pop

A floating window that the sweep does reach is born at 1x and doubled by the
next ~250ms `UiSpike` tick, which reads on screen as a size pop — the same
signature behind "loading time between pages", the route-query jump, and the
day/night jump on first selection. Static-doubling the `.UI` script so the
game builds the window pre-doubled removes the pop and the wrong size in one
change.

### When runtime is structurally too late

When the game reads a child window's geometry BEFORE the first sweep can run —
3D head framing bound at city load, ticker marquee init caches — no runtime
scaling can win. That geometry ships PRE-SCALED in the `.UI` and the parent is
made root-only in the DLL. Two windows are in this class: the advisor strip
subtree (`kDataScaledSubtreeIds` + `double_subtree_areas`) and the ticker
marquee width.

---

## 2. The alignment-marker rule — how SC4 places every flyout

Every tool-flyout `.UI` script contains a hidden child `id=0x0000AAAA` whose
size equals its SPAWN BUTTON's size. The game positions the flyout as:

```
flyoutPos = spawnButtonAbs - markerOffset
```

so once the subtree is scaled to 2x, the correct dock target is:

```
target = spawnButtonAbs - markerOffset(LIVE, already scaled)
```

Equivalently, with `R = nativePlacement - spawnButtonAbs` ( = -marker at 1x ):

```
target = spawnButtonAbs + f*R        <- what kMayorFlyoutDock stores
```

Alignment markers are POSITIONING DATA. Never scale `0x0000AAAA`, at runtime
or in data.

**Three independent confirmations of the rule:**

1. It reproduces all three locked god docks to the pixel: terraform
   (22,262), terrain-fx (22,502), day/night (22,742).
2. It predicts the game's own native mayor placement: Landscape marker
   (3,27), button abs (28,398) → (25,371), which is what `MCAL` measures in
   game.
3. Two separate derivations agree on (22,344) for Landscape — `button + 2R`
   and `button - marker2x`.

It also explains the one case the constant table needed a special case for:
the shared window `0xCA35CBED` needs two offsets (terrain-fx 40, day-night
160) because swapping SCRIPT moves its marker. The rule handles that
automatically.

**Trap: one window id can carry TWO scripts.** `0x49923239` is god/terraform
(125x291 → 250x582, marker (4,90)) AND mayor/Landscape Tools (125x249 →
250x498, marker (3,27)). A single fixed offset can never serve both; the
mayor-mode gate separates them.

### Measuring a new flyout

1. Set ini `[Flyout] MayorDock=0` — mayor flyouts are scaled but never MOVED.
2. Open the flyout in game, quit.
3. Read the `MCAL` line: it prints native pos, spawn-button abs, the derived
   `R`, and the target that `R` would produce.
4. Paste `R` into `kMayorFlyoutDock`, set `derived=true`, `MayorDock=1`.

### The mayor toolbar map

The live dump enumerates children in REVERSE of `.UI` add order
(`CITY-DOCK-OVERLAP.md` §1.2), so a button is identified by its Y POSITION,
never by enumeration order. Toolbar root `0x69E40A1F`, live (8,364) 314x976.

| # | Button | live abs | Flyout | Flyout id | marker (1x) | dock target |
|---|---|---|---|---|---|---|
| 1 | `0x8991EE08` | (28,398) | Landscape | `0x49923239` | (3,27) | (22,344) verified in game |
| 2 | `0x0991EE13` | (28,498) | Zones | `0x69923479` | (3,77) | (22,344) verified in game |
| 3 | `0xA994824D` | (28,598) | Transportation | `0xC99237A0` | (3,77) | (22,444) derived |
| 4 | `0xE991EE2F` | (28,698) | Utilities | `0xE992F711` | (3,77) | (22,544) derived |
| 5 | `0x0991EE39` | (28,798) | Civic | `0x699306ED` | (3,227) | (22,344) derived |
| 6 | `0xE999C820` | (28,922) | Bulldoze | (none) | - | - |
| 7 | `0x6991EE42` | (28,1010) | Emergency | `0x0992FD17` | live (6,468) 100x80 | (22,542) |

Buttons 1 and 2 both land at (22,344): each flyout's marker sits lower by
exactly the button pitch, and the two cancel. That is the rule being
self-consistent.

### Which code path each flyout uses

- **Landscape `0x49923239`** is in `kGodToolFlyoutIds`, so the sweep skips it
  and `ScaleGodFlyouts`'s god loop handles it; the mayor entry overrides the
  anchor while `mayorModeActive`.
- **Zones / Transportation / Utilities / Civic** reach NEITHER the god loop
  nor `ScaleMenuFlyouts`. They fall through to `ScalePanelRoot`'s
  CENTER-ANCHOR branch (which fires when `gapT` and `gapB` both exceed
  `frameH/4`) and get repositioned with no reference to the spawn button —
  zones lands at y=241 because `421 + 180 - 360 = 241`. They carry the
  `mayorOnly` flag so the sweep skips them and the mayor loop docks them.

---

## 3. The shared sub-flyout container `0x8A6E61E0`

The strip that opens when a tool is picked INSIDE a flyout (zone density, road
types, and the rest). Facts, all measured:

- It is a **direct child of the 3D view**, not of the flyout that spawned it,
  so it inherits nothing from that flyout's dock.
- It is **SHARED by every tool** — seen at 258x482, 258x874, 258x776,
  258x384, 258x580, resizing per content. A per-tool anchor fixes one tool's
  sub-menu and breaks the other four.
- It has **NO `0x0000AAAA` marker**, so the marker rule cannot supply an
  offset.
- **Position:** the game places it correctly from LIVE window positions,
  already accounting for the docked parent. The generic sweep was DOUBLING its
  coordinates from the screen origin (178→356, 274→548). The cure is to skip
  it in the sweep, size it, and never move it.
- **Class:** container `0x00AB6AA8`, strip child `0x00AB6D88` — byte-identical
  to the Disaster flyout (proved by the `SVT` probe), which is why every
  Disaster draw fix applies verbatim and no new reverse engineering was
  needed. Sharing `gVtCopy`/`gVtCopy2` is safe here BECAUSE the class is
  identical; the "one window only" warning in the code is about hooking
  DIFFERENT classes.

### Every symptom and its cause

| Symptom | Cause | Fix |
|---|---|---|
| Wrong position | the generic sweep took `ScalePanelRoot`'s left/top edge branch and doubled the coords from the screen origin (178,274)→(356,548) | `IsSubFlyoutId` skips it in the sweep |
| Not tracking the selected item | the game places it at `selectedButtonAbs + (20,-86)` (measured: btn(158,560)+(20,-86) = live (178,474)) | nothing to fix — read the placement law below |
| Ring not on the button | the 2x ring needs the whole assembly moved | dock to `btn + (-33,-110)` = native + (-53,-24); derived: `ring centre = container + (0,94) + (80,53) = btn + (100,61)`, `button centre = btn + (47,37)` |
| Bar 1x | stale 1x paint buffer | `gForceRecreate` (the Disaster fix — same class) |
| Icons not seated | strip item fields 1x | `gStripFieldScale=2` (the Disaster fix) |
| Bar clipped to a sliver | `gBarDX=-53` is GENERIC, not disaster-specific: bar art is 53 wide drawn FLUSH RIGHT (buf 258, dst x 205..258); widening 2x without the shift overruns by 53 | never gate `gBarDX` |
| Circle 1x | the Disaster ring upscale tests `sw > 80`; this sprite is EXACTLY 80 wide, so it missed by one pixel | range widened to 70..140 x 35..100, gated `!gDisasterDrawTuning` |
| Circle moved when scaled | an earlier revision scaled the ring ORIGIN as well | scale SIZE only; the origin stays, plus `SubRingDX`/`DY` |
| Only the right half clickable | the container's custom `IsPointInMe` claims only the rightmost `[this+0xe0]` px, still 1x | `ClaimScale=2` + `SelForce=1` — the gates INTERSECT, both are required |

`gDisasterDrawTuning` gates ONLY the disaster-measured ring offsets
(`RingDX`/`RingDY`). It must NOT gate `gBarDX`/`gBarWiden`, which are generic.
It is 0 when the sub-flyout container is hooked and 1 for disaster; the two are
never live simultaneously (god vs mayor mode).

`gBarDX = -53` in full: the bar art is 53px wide and the game draws it FLUSH
AGAINST THE RIGHT EDGE of the container buffer (sub-flyout: buf 258 wide, bar
dst x = 205..258). Widening 2x without shifting puts it at 205..311, i.e. 53px
past the buffer end, so the bar clips to a sliver and the icon strip
(x 160..248) no longer overlaps it. Shifting left by exactly one bar width
keeps it flush: `152 + 106 = 258`.

### The sub-flyout placement law

The game centres each menu's **1x ring sprite** on the button, and `ringBltY`
varies per menu, so a constant native offset can never match them all:

```
nativeY = buttonCentreY − ringBltY − 29        nativeX = buttonAbsX + 20
```

zones: `274 = 397−94−29`   rails: `549 = 697−119−29`, both with residual ZERO.
Ring dst is (0,94) for zones and (0,119) for rails and depots. The constant
−86 is this law evaluated at `ringBltY=94`, which is why five transport menus
sat at native while zones and roads docked.

**Corollary:** the dock delta (−53,−24) is MENU-INVARIANT — native and target
both shift with `ringBltY`, so their difference cannot depend on it.

Three code deltas implement it:

1. The sub-flyout ring 2x draw records `gSubRingBltX/Y` plus buffer W×H.
2. The dock computes `natT = btnCentreY − gSubRingBltY − kSubPlaceBias(29)`
   instead of `bt − 86`, gated on the record matching the container's current
   size (blits fire every frame against the 4×/sec sweep, so a stale record
   self-corrects).
3. `destIsContainer` height gate 300 → **260**: one transport menu is 258x286
   and below 300 its ring never got the 2x draw at all.

Log line: `SUBDOCK 0x8A6E61E0 btn=0x… abs(…) ringY=119 native(178,549)
-> target(125,525)`.

**Two-item nested menus need the width gate, not a height gate.** The Freight
Train sub-sub-menu container is **258x206**, under both `h>300` and the
widened `h>260`, so its ring got no 2x, no blit record and no law dock. The
sub-flyout path keys on the container's EXACT width:
`destIsSubContainer = (selfW == 258 && selfH >= 100)`; the disaster path keeps
the old heuristic untouched. Observed sizes: 258 x
206/286/384/482/580/678/776/874.

### `SubRingDX` / `SubRingDY` are derived, not dialled

`[Flyout] SubRingDX=25  SubRingDY=-6`, derived from the art alone — the atlas
is plain DBPF art, so no in-game dump is needed. What the measurements show:

1. The source atlas is **292x53**, on disk as
   `T-856ddbac G-1abe787d I-14215ed0..ed5` (six colour variants, ONE identical
   magenta mask; matches the live `DCTX area=(0,0,292,53)` trace).
2. The 80x53 sprite is a **KEYRING, not a padded circle**: an annulus on the
   left whose magenta **hole** (31x21 ellipse, centre exactly **(25,26)** by
   flood fill) frames the selected button, merging into a full-height
   connector wedge with **zero right padding**. Closing the right gap by
   trimming padding is impossible — there is none.
3. The flyout button's visible **ellipse is off-centre in its 47x37 cell**:
   luminance bbox (1,0)..(41,30), centre **(21,15)** against cell centre
   (23.5,18.5) (art `G-46a006b0 I-14215e40..42`, 4 states each, all
   identical). That (-2,-3) offset — not sprite padding — is why box-centre
   math reads 4-5px off and the ring looks low.
4. Align **hole centre == ellipse centre** (all 2x screen px, buffer==screen;
   the 2x-pixel +0.5s cancel):

   ```
   SubRingDX = 2*ex - (nx + SubDockDX + rx + 2*hx) = 42 - (20-53+ 0+50) = 25
   SubRingDY = 2*ey - (ny + SubDockDY + ry + 2*hy) = 30 - (-86-24+94+52) = -6
   ```

   with `(hx,hy)=(25,26)` hole, `(ex,ey)=(21,15)` ellipse, `(nx,ny)=(20,-86)`
   the game's native container offset (`SUBDOCK` log), `(rx,ry)=(0,94)` ring
   dst (`RCAL` log). `SubDock` appears in the formula, so the derivation is
   re-run after any `SubDock` change.

`I-14215edd` has the same 292x53 dims but is a DIFFERENT sprite with no
enclosed hole. If a menu ever draws its ring from it, the offsets are
re-measured against that sprite.

---

## 4. The deep-submenu mod (`memo.submenus.dll` 2.1.0)

The deep submenu system is a third-party DLL plugin at
`Plugins\memo.submenus.dll`, open source at github.com/memo33/submenus-dll.
Both of its 2x defects are fixed WITHOUT touching the mod — the DLL and an art
override only.

### Duplicated item icons

The mod binds **55 Item Icon instances of its own** (property `0x8A2602B8` in
its dats' exemplars; all icons 176x44 4-state strips in the same dats),
outside the stock 266 that the root ItemIcons-2x package covers.
Un-overridden, the game slices the 1x strip by the DOUBLED 88px cell, so each
cell shows TWO 1x states side by side, which reads as "duplicated instead of
stretched". Fix: extract all 55, upscale 2x nearest-neighbour (the preview-set
method), ship as
**`Plugins\zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat` (55 entries)**,
tier-gated by `ScaleTier` like the root packages. Root ItemIcons-2x stays at
**266** (stock pool only). Any future submenu pack with new icons repeats this
recipe.

### THE LOAD-ORDER LAW

Within the Documents `Plugins` tree, **root FILES load BEFORE subfolders** — a
root `z_*.dat` can NEVER override a dat inside a subfolder. (Putting the 55
icons in the root ItemIcons dat produced 321 entries and icons that stayed
duplicated with the package deployed.) Overriding another Documents mod
requires a FOLDER that sorts after the target's folder: `zzz-SC4UIScale\`
beats `150-mods\`. The root packages still work because they override
INSTALL-directory resources only.

### The dead back arrow

The mod's "back" action is A CLICK ON THE PHYSICAL MENU BUTTON
(`Hook_HandleButtonActivatedReopen` in its source). The red arrow is baked
into its five 292x53 menu-frame atlases (`0xAC581B70..74`, essentials dat)
inside the ring-box wedge, measured (52,14)..(62,38) at 1x. At 1x the arrow
art and the button overlap, so clicking the arrow WAS clicking the button; the
2x ring draw pushes the visible arrow just past the button's right edge into
dead space (a whole session of arrow-clicking fired `DHIT136` twice).

Fix (`[Flyout] ArrowClick=1`): claim the drawn arrow's rect through the
verified routing chain (container slot 121 `ContPt121Thunk` → strip slot 62)
and, at the strip's commit handler (slot 136), synthesize a REAL OS click
(`SetCursorPos` plus posted down/up) at the selected button's centre. The
centre is structurally outside the arrow zone (btn+47 against zone start
btn+80), so there is no recursion.

`[0xe0]` must NEVER be widened for this. It is dual-use — claim width AND a
draw-side-halved Plot inset — which is why the claim extension is a slot-121
thunk and not a field write.

---

## 5. Flyout art: the frame scales, code-bound art does not

A flyout frame scaled by the sweep still draws 1x button art in its doubled
slots — terrain-pattern tiles, grayscale disaster thumbnails, sun/moon icons,
brush tools. That is the same class as toolbar ItemIcons and the TrendBar art:
code-bound button art that a frame scale cannot touch. The cure is a 2x
override dat at the same TGIs, plus the window's id in the selective-safe
builder's `SCALED_WINDOW_IDS`.

### `GZWinBMP` sizes the draw from the SOURCE image

The disassembly of class `0x00ADF6A0`'s Plot (`0x9BC325`) settles the whole
family: it is **GZWinBMP**, and it draws its image with **dst = origin +
srcWxH** (the 3-state branch divides src by 3 then draws via helper
`0x8D8800`). The draw size FOLLOWS THE SOURCE IMAGE, so 2x art gives a 2x
draw with no code hook at all.

That makes the Emergency flyout an art-pass gap, not a new mechanism. The
"panel" `0x2992FD21` is the flyout's ring/frame BITMAP
(`image={46a006b0,14215e2c}`, `imagerect 114x270`), and Emergency was the last
mayor flyout added to the selective-safe builder — identical symptom and
identical fix to Zones, Transport and Utilities: 1x art with a 1x `imagerect`
inside a correctly-placed 2x window draws the ring at half size in the wrong
band. `0x0992FD17` belongs in `SCALED_WINDOW_IDS`.

**Before treating a flyout bug as a NEW mechanism, check whether the window
ever got its art pass.**

### Emergency Tools geometry and vtable reference

`0x0992FD17` (mayor Emergency Tools, 308x840) docks at (22,542); live marker
(6,468) 100x80. Its picture panel `0x2992FD21` (496x636 at (0,2)) is **class
vtable `0x00ADF6A0`** — NOT the disaster container (`0x00AB6AA8`), NOT the
strip (`0x00AB6D88`). `EBLT` records ZERO blits through the hooked buffer
class (`0x00AC1400`) while the panel is open and painting, so it paints
through a different buffer path. Its buttons (5 × 94x74) are class
`0x00ADDAF0` and scale normally.

Vtable dump from the exe (imagebase `0x400000`, vtable file offset
`0x6df6a0`). The class follows the FAMILY SLOT LAYOUT — the same lever slots
as the disaster classes:

- slot 87 = `0x0099BE4C` (`GetNotificationTarget`; the per-class draw
  `GZPaint` is slot 88), **slot 88 GZPaint = `0x009BC325` (override)**
- slots 136/138 mouse = `0x009BC2D0` / `0x009BC27C` (overrides, the click-fix
  slots)
- slot 121 = `0x0099C8F5` (base), slot 133 = `0x0093878E`, slot 149 =
  `0x0099BBBE`
- draw group 87..97: `0099be4c 009bc325 0099ba07 0099dce4 0099becc 0099bed1
  0099bef9 0099befd 0099c6f8 0099d57e 0099cf6a`
- Plot `0x009BC325` calls: `005e5620 008d8800 0093878e 0099bc31 0099bdf3
  0099be0a 0099c2c3 0099cf49 0099d938 0099db6b 009bc2fa 009bc447`; it
  references its own vtable cluster `0x00ADF63C/66C/6A0`. There is no
  buffer-class constant in its first `0x500` bytes — the buffer arrives
  through the shared base helpers (`0x0099cf49`, `0x0099d938`, `0x0099db6b`).

Instruments for this family: ini `[Flyout] EmergLog` (EVTP child-class dump +
EBLT blit log).

### The god cluster's art

The god toolbar's end-cap art `{46a006b0,14415870}` on window `0x00000001`
drew 1x anchored top-left while the WINDOW scaled correctly: the god scripts
were absent from selective-safe's `SCALED_WINDOW_IDS`, so the shared art got
cloned for the flyout and the ORIGINAL was left at 1x. `0xC991EDA8`,
`0x49923239` and `0xABB26B0E` belong in `SCALED_WINDOW_IDS`, which puts the
god cluster art at 2x in place and fixes the art of every clickable god menu
at the same time.

---

## 6. Founded-city god mode

**The founded-city trap:** every "hidden", "never-visible", "frozen template"
or "docking it changes nothing" note in the god-mode research was measured
BEFORE a city was founded. Several of those windows BECOME LIVE once a city
exists, so a note that is accurate pre-founding is not evidence about the
founded-city path. When a founded-city window misbehaves, capture a STOCK
founded-city reference first: it answers three questions at once — is this
stock behaviour, does the control work in stock, and what does correct look
like.

### `0x0A78827A` — the founded-city god toolbar

Obliterate City / Reconcile Edges / Disaster / Day-Night. It sat in
`kGodToolFlyoutIds`, which makes the city sweep SKIP it outright, so it
rendered at dead stock 74x291 at (5,1071) — and (5,1071)..(79,1362) is exactly
where the clipped fragments at the far left edge appeared. What identified it
was a stock founded-city capture: stock god mode is COLLAPSED BY DEFAULT (not
a bug), and its expand tab reveals exactly four tools, which is precisely the
button list in `0x0A78827A`'s script `I-aa53e3ea`. The four buttons NAMED the
window.

Fix: out of `kGodToolFlyoutIds`, into `kGodPanelIds`. The panel transform
reproduces the recorded dock target (5,1071)→(10,542): `2*5=10`,
`2*1071-1600=542`. Log confirms
`panel 0x0A78827A (5,1071 74x291) -> (10,542 148x582)`.

### `0xABB26B0E` — the god panel a founded city actually shows

Symptom: switching to god mode in a founded city shows almost no UI, a few
clipped fragments at the left edge, no tool rail. One log line identifies it:
`id=0xABB26B0E pos(3,1045) size(314x976) vis=0`. Stock rect is (3,1045)
157x488, i.e. BOTTOM-anchored. It had been doubled to 314x976 but never moved,
so it ran y=1045..2021 on a 1600px screen — **421px below the bottom edge**,
and what rendered was the sliver that fit.

The root cause was a stale ASSUMPTION rather than broken machinery: the id sat
in `kSizeOnlyIds` (scale, never move) on the strength of a pre-founding note
calling it a frozen hidden template at Y1045 that day/night merely rode on.
That is true before a city is founded and false afterwards, when `0xABB26B0E`
is the panel god mode shows (its two live 148x116 god buttons are in the
dump).

Fix: moved to `kGodPanelIds` (bottom-anchored panel transform, scaled BY ID
even while it reports `vis=0`) and removed from `kGodToolFlyoutIds`.
`kSizeOnlyIds` and its loop are deleted. The target is derived, not eyeballed:
the panel transform `y' = f*y - (f-1)*frameH` gives `2*1045-1600 = 490` →
**(6,490)**, which is exactly the recorded dock position for this id. Its twin
`0x69E40A1F` has the IDENTICAL stock size (157x488) and already renders right
through this path.

### The god toolbar chain

1. **TWINS:** the god toolbar always double-draws — `0x69E40A1F` (stock-layout
   panel) plus `0xC991EDA8` (tile strip), both from scripts `I-a991ed83` /
   `I-69e3d347` sharing root id `0xC991EDA8`. The roots report `vis=0` while
   their children draw, so the visibility gate skipped them; they are scaled
   BY ID even while hidden (`kGodPanelIds`).
2. **FLYOUT ROOTS** carry the same `vis=0` quirk, so `ScaleGodFlyouts` drops
   the `IsVisible` gate and docks with
   `toolbarLive + f*(flyoutStock - toolbarStock)` using the toolbar's
   `ScaleRecord` `origL/T`. Disaster and day/night dock exactly:
   (5,1071)→(10,542) and (3,1045)→(6,490).
3. **GHOST SUN** is the end-cap art case in §5.

The diagnostic that cracked it was the 1s live full-tree watcher with the menu
toggled between dumps, plus absolute-position queries. It also caught the
mode-transition behaviour: the game RESETS the UI to stock on every mode or
menu toggle (status bar 476x43 ghost, toolbar pages 40x36) and the sweep
re-scales about a second later, which is the "loading time" and "first-open
small" symptom. The cure is the VISIBILITY GATE, not sweep latency: the
affected ids are pre-scaled while hidden.

The terraform `0xCA35CBED` and terrain-fx `0x49923239` docks used to fire on
MID-ANIMATION captures ((26,352)→(52,-896), off-screen). A guard skips the
dock when the target lands outside the frame and catches the resting frame
instead.

### God-mode window sizes under the sweep

| Window | Id | Stock → 2x |
|---|---|---|
| God toolbar | `0xC991EDA8` | 74x351 → 148x702 |
| Terraform flyout | `0xCA35CBED` | 125x231 → 250x462 |
| Terrain-effect flyout | `0x49923239` | 125x291 → 250x582 |
| Disaster flyout | `0x0A78827A` | 74x291 → 148x582 (7 windows) |
| Day/night | `0xEBB16D71` | 450x450 |

---

## 7. Main-window children: queries, confirms and toasts

The building query panel is a child of the MAIN WINDOW (parent `0x00000000`),
a SIBLING of the app window — not under the view, and not under the app
window, which holds only the view. The city sweep never reaches it, so it
renders at pure 1x stock (root 292x334, rows 175x18). That makes
static-doubling collision-free.

The whole 117-panel query family (root `0x10000005` plus the `0x89e1567c`
container) is auto-discovered by
`tools\dialog-static\build_dialog_static.py:discover_query_family` and
static-doubled. The residential query is verified 2x clean in game. Query
Clicker is the same family and the same fix.

Confirm and message boxes are main-window children too, and each is a
static-double:

- Obliterate City / Reconcile Edges confirm: runtime id `0x27DF05BE`
  (339x200), scripts `I-2a41436c`, `I-6a9455c9`. This is a SEPARATE msg-box
  template from the generic `ea8cc3c6`, which is why doubling `ea8cc3c6` does
  not reach it.
- Obliterate `2a41436c`; Reconcile ×3 `0a4d0c43` / `ca4d0b22` / `8a4d0a17`.
  The Reconcile "highlighted areas" variant was squished while only one of the
  three root-`0x6a4d0a59` variants was doubled; all three are doubled.
- Advisor toasts: five message-box scripts `I-4a5a89d4`, `I-4a5a89d5`,
  `I-2bb16d50`, `I-0bbc06b6`, `I-4bbc080f` go into the dialog-static builder.

Day/Night (`0xEBB16D71`, 450x450, script `I-2bb16d50`) is a main-window child
on the same static-double path; its blue selection ring is code-bound aura
art, so the ring needs a 2x override at its TGI rather than a frame scale.

---

## 8. News, ticker, and the HTML engine

**All news text is the game's HTML engine, not FontStyle.** Ticker roll,
reader headline rows, story pages, advisor and message popups, tutorials and
Credits are one rich-text engine (item clsid `0xaa12e5f5`). Both AdviceList
instances — ticker marquee `0xAA12F33C` and reader list `0x6A231531` — are
`cSC4WinAdviceList` `0xca1492ac`, whose items host it.

Exe templates in `.rdata` carry literal `SIZE=2` / `SIZE=3`; 189 locale
LTEXTs embed their own `<font size="N">`; SIZE resolves through two `.rdata`
point tables (FONT `0xACD4A0` `{8,10,12,14,18,24,36}`, H1..H7 `0xAB4AD0`).
`FontStyle.ini` never reaches this path — which explains the long-standing
community limitation that font size does not work for news.

The fix has four parts:

1. `ApplyHtmlSizeScale` scales both tables by the factor and retargets the
   popup builders' `Message*` style GUIDs at stock-size clones
   `MessageHeaderHtml` / `MessageBodyHtml` `0x5c4b0914` / `0x5c4b0915` (in all
   six FontStyle files). These three parts are COUPLED.
2. AdviceList geometry: the reader list is scale-self-never-recurse; the
   marquee is WIDTH-only (height = `3*lineHeight` from the 2x font, Y
   animates); the ticker root-only rule is removed, so the BMP and clip strip
   scale normally.
3. Selective art covers the exe news page art `0x140155b4..f7` plus the
   `sc4://image` LTEXT art (`tools\selective-safe\html-image-refs.txt`).
   Deliberate hole: `html_TextBG` `14416264` stays 1x, because three HUD
   panels 9-slice it.
4. Credits LTEXT size maps are calibrated in
   `tools\dialog-static\build_dialog_static.py` against the scaled tables —
   uncalibrated bumps compound.

The rich-item creation sites are `0x443FCA`, `0x76A183` and `0x78CE12`.

### The ticker marquee ships its width in DATA

The game re-imposes the marquee's init-cached 1x geometry every roll tick, so
a runtime width scale is undone within a frame and the headline wraps. The
marquee DESIGN width ships scaled inside the edited `.UI` (SelectiveArt
`I-2a2aed99`; 676→1352 at 2x, 484→968), and the DLL never touches the marquee
at all (`kAdviceListNeverTouchIds`).

### The two window-tree facts behind it

| Window | Evidence | Layer |
|---|---|---|
| News reader `0xAA231508` | `pos(260,348) size(880x456)` = dead stock, but **`vis=0` while visibly drawing**, so the sweep's visibility gate skips it | window tree; scale by id even while hidden (the `kGodPanelIds`/`kRegionPanelIds` rule). The accompanying visual error was 2x art in a 1x frame and resolves with the art pass |
| News ticker `0xCA2AEDC0` | container `1514x86` = EXACTLY 2x of stock 757x43 (root-only scale worked), but child `0x6A2AEDCA` is still `757x43` | draw/child layout. The `kRootOnlyScaleIds` premise — that `cSC4WinAdviceList` re-lays children to the container each frame — does not hold for that child |

News reader script: `I-2a2aed99`, a VIEW child.

---

## 9. Advisors

The advisor faces are LIVE 3D HEAD RENDERS whose framing is created ONCE (head
binder at exe `0x41DE20`, slot reuse on later entries) and re-derived only on
an advisor VIEW SWITCH. A window Hide+Show fires but changes nothing:
visibility is not the trigger. Because the framing is bound at city load, the
geometry ships PRE-SCALED IN DATA.

The strip subtree is pre-scaled in data (20 `area=` edits per script, at all
three factors, verified 16/16 against live 2x values) via
`kDataScaledSubtreeIds` + `double_subtree_areas`, so the heads are framed from
2x buttons at bind time — no injected input and no flash. `[Flyout]
AdvisorHeal=0` is an escape hatch.

The rest of the advisor family:

- Strip `0x6A15C767` carries 2x art and the hidden pre-scale.
- Briefing page and expanded view `0xAA15EF06` / `0x2A1D96B1` are in the art
  pass.
- The AdviceLists `0x0010010x` are guarded never-recurse.

---

## 10. Budget

The expanded budget's black areas were an ART-PASS gap with already-perfect 2x
geometry. `0xAA3AC001` (expanded), `0xAA3AC002` (Taxes) and `0xCA4C332D`
(Loan) go into `SCALED_WINDOW_IDS` with the budget-art conflicts resolved;
Taxes and Loan also go into `kAlwaysScaleCityIds`, because they measure 1x
while hidden.

An art-pass gap looks exactly like a geometry bug. Measure before assuming.

---

## 11. Building Style Control — a plugin that REPLACES a stock script

**A distinct failure class, worth recognising on sight.** A plugin can REPLACE
a stock `.UI` script wholesale, and a root package can never override it
(the load-order law). CoriBoom's 36 Slot Building Styles UI replaces the
Building Style Control script from `150-mods\`, so that panel had never been
scaled and the sweep doubled the mod's 73 windows over its 1x `imagerect`s.

**RECOGNITION RULE: if a panel's live window count or root size does not match
the stock script being edited, a plugin replaced that script.** Here: live
532x640 with 73 windows against stock 531x406.

Fix: build from the MOD's script into
`Plugins\zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI[-tag].dat` — a
`thirdparty-ui\` builder input, synced by `ScaleTier`, 1 entry. Developer
callout: `tools\research\UPSTREAM-BUILDINGSTYLES-REPORT.md`.

Both states are verified at 2x: the mod's 36-slot layout and the STOCK
4-style panel with its four previews. The mod's layout has NO style previews
at all; that is its design, not a scaling bug.

---

## 12. Data Views panel

THREE COUPLED PARTS — breaking one regresses the panel:

1. **Sweep + art.** Root `0xAA32BCE6` is scaled and covered by the art pass.
   The root was previously skipped by id under the label
   `kGZWin_MenuContainer`, an early-spike guess at plop-menu machinery; the
   dump proves the subtree is purely the Data Views fold-out panel.
2. **DVMAP surface recreate** — the crash preventer. Map child `0x00004203` is
   a SECOND `cSC4WinMiniMap` instance (`GetClassID 0x7A6580` → clsid
   `0xCA318388`) whose one-shot display surface stayed 256 while the data-view
   renderer `sub_7A2F60` built window-sized 512 buffers (rect read
   `0x7A301E`, buffer create `0x7A3094`). The dock-minimap surface-recreate
   lever runs on `0x4203`.
3. **DVPIN.** The game re-lays the legend on every view select with 1x origins
   and 2x font-derived pitches, so a pin-back pass re-imposes the scaled
   design geometry each sweep while the page is visible (the RCI treatment,
   against DPROBE-measured targets).

**COUPLING RULE: the art pass without the DVMAP block is the crash build.**

Expected log: `DVMAP 2X win 512x512 blitSize=512` plus
`recompute 0x7A7840 ok`. Eyes-on check: expand, pick a view, confirm the 512
map. Stock shifts 3px between states by design.

The expand path itself is pure show/hide with no moves — the crash was always
the map child.

Script identity: the live script is **`I-2bc9060f`** (rect-matched);
`I-ea287193` and `I-0b72f276` are stale copies under the same root id. Art
instances `140155ec` and `14416264` go shared-clone (Audio Options
`I-ca53f06e` keeps `14416264` at 1x — never force in-place).

**Law:** an id-skip written in an earlier phase is a scenario axis. Re-audit
every surviving id-skip once its subtree's real owner is known. And the panel
lifecycle axis includes EXPAND: a fix confirmed on the compact state only is
half-tested.

---

## 13. U-Drive-It

Two fixes, both DPROBE- and disassembly-measured.

**The driving status panel is a self-inflicted 4x double-scale.**
`discover_query_family()` auto-enrols the eleven `0x10000005`-marked
U-Drive-It scripts into the static dat, but their root `0x10000006` parents at
the 3D VIEW, so the sweep doubles the already-doubled panel. The cure is
`kNeverScaleIds` (the Establish City rule) plus a parentage warning in
`tools\dialog-static\build_dialog_static.py`.

**The tiny mission bubble** is code-bound art `{46a006b0,094ac89a}` plus the
15-glyph mission table at VA `0x44DEC7`, both routed through `CODE_BOUND_TGIS`
in the selective-safe builder. Two glyphs are conflict-skipped by the
classifier: `46a006a4` and `46a006a6`.

Testing note: mission bubbles are ONE-SHOT. Each can only be selected once, so
verification needs an unused bubble.

---

## 14. Tooltips

The tip layer `0x2AAB8CC1`, class `0x00AB6770`, code-paints all of its
content. Two mechanisms:

- **Wrap width 250 → 500:** the `TooltipWrapPatch` byte patch (`push 0xfa`
  twice in the tip Plot at `0x798710`). Tooltip boxes sized for 1x text while
  the font is 2x clip and overflow without it.
- **Torn fill / clipped corners:** the bar transform was eating tip buffers
  through size heuristics. The bar block is mode-split — god → disaster
  (200-400 wide, >500 high), mayor → sub (`w == 258`).

**Size heuristics cannot identify windows whose size follows CONTENT
(tooltips are the type case).** Positive identification means exact width,
mode splits, or class+id.

Pill caps are NEVER y-doubled — x-widen only, which is the approved disaster
look.

---

## 15. My Sims

The panel needs a code-level slot-pitch hook plus 2x portraits; its root is
`0x698894D3` (`ITEMICONS.md` Q3). All nine roots plus the AdviceList guard are
covered. A deferral is not a neutral state: a deferred window inside an
otherwise-scaled ecosystem tears apart, which is how the deferral itself
became the defect.

---

## 16. Standing hazards

Each of these cost a regression once.

- **Plot-hook naturals are captured ONCE.** Any other writer that runs first
  poisons them. The sweep INVALIDATES when strip fields are still 1x and NEVER
  writes those fields; writing them poisons the Plot hook's one-shot natural
  capture and produces 4x pitch everywhere.
- **Size heuristics cannot identify content-sized windows.** Use exact width,
  a mode split, or class+id.
- **The alpha guard is `0 < a < 128`, NEVER `a < 128`** — stock art is `a==0`.
- **Root `z_*.dat` files CANNOT override subfolder dats** (the load-order
  law).
- **Parse BOTH exemplar formats** (binary EQZB and text) — CAM is about half
  text.
- **An art sweep must scan `.SC4Lot` containers**, or lot-carried art is
  missed.
- **1x art inside a doubled frame is a bug**, never an acceptable residual.
- **Latches must clear in `Disarm`**, or the second city loaded in a session
  breaks.
- **For a SHARED container, the right class is not the right window.** Class
  identity proves which fixes port; it does not name the instance to hook.
- **Auto-discovery rules can enrol unchecked parentage** — see §13.
- **The mode-transition flash is the VISIBILITY GATE**, not sweep latency.
  Never cure it by suppressing paints.

---

## 17. Third-party menu content (CAM and friends)

- **Duplicated landmark icons** need a full-plugin icon scan including TEXT
  exemplars: +69 icons plus Missing Thumb `0x144161EC`.
- **CAM's ten unreachable items** (police, fire, jail, lifeguard) are
  exemplar-patch cohorts (`0x05342861` / `G-B03697D1` / prop `0x0062E78A`),
  shipped as `MenuFix.dat`. Developer callout:
  `tools\research\UPSTREAM-CAM-REPORT.md`.
- **Submenu icon packs** follow the recipe in §4.

---

## 18. Instruments

| Log tag | ini key | What it answers |
|---|---|---|
| `MCAL` | `[Flyout] MayorDock=0` | flyout native pos, spawn-button abs, derived `R`, target |
| `SCAL` | (automatic) | sub-flyout against the open parent flyout, and every button in it |
| `SVT` | (automatic) | concrete class vtables — is this the Disaster class? |
| `SBLT` | `[Flyout] SubBltLog=1` | EVERY blit into the sub-flyout buffer, unmodified src/dst |
| `RCAL` | `[Flyout] RingCal=1` | ring-sized blits and their dest buffer — painted art or window art? |
| `EVTP` / `EBLT` | `[Flyout] EmergLog` | Emergency child-class dump and blit log |
| `DPROBE` | `[Probe] Enabled=1` + band | change-triggered geometry; catches transient windows |
| `SUBDOCK` | (automatic) | sub-flyout native, `ringY`, and dock target |
| `DVMAP` | (automatic) | Data Views map surface size and blit size |

---

## 19. Script index

Scripts that carry city-mode panels, by panel:

- **Obliterate confirm:** `I-2a41436c`, `I-aa53e3ea` (`aa53e3ea` is a
  god-mode tool cluster script and also carries day/night).
- **Boundary "already match" message:** `I-0a4d0c43`.
- **Building query (Make Historical):** `I-2a567dc1`, `I-4a5672bf`,
  `I-ca56783a` — the residential, commercial and civic query variants.
- **Trip Types / route query:** `I-0b72f276`, `I-2bc9060f`, `I-abb0120f`.
- **Disaster:** `I-0a41be3e`, `I-0a41be3f`, `I-4a89b3f2`, `I-69e3d347`,
  `I-899302fc`, `I-a991ed83`, plus the `08000600`-group 800x600 twins.
- **Day/night and aura:** `I-69e3d347`, `I-aa356502`, `I-aa53e3ea`.
- **News reader:** `I-2a2aed99`.
- **Advisor toasts:** `I-4a5a89d4`, `I-4a5a89d5`, `I-2bb16d50`, `I-0bbc06b6`,
  `I-4bbc080f`.
- **God toolbar twins:** `I-a991ed83`, `I-69e3d347`.
- **Founded-city god toolbar:** `I-aa53e3ea`.

81 scripts in total contain a "Close" button; most of them are query panels.

---

## 20. Method

Three ordered phases per section, and the order is not optional:

1. **FOUNDATION / MECHANICS** — make it scale at all.
2. **FLOW** — make it POSITION correctly: dock flyouts to their buttons, no
   overlap, right place.
3. **LOOK** — 2x art for every button and icon, no 1x inside a 2x frame.

Art before mechanics and flow does not hold. Stock is a temporary development
step, never a finished state.

**Every value that is MEASURED lands first try:** the `MCAL` dock pass, the
alignment-marker rule, the `SVT` class probe, the `SBLT` bar trace, the `RCAL`
ring identification, the container-dock arithmetic. **Every value inferred
from a screenshot costs two or three builds**, and twice it broke something
that already worked — terraform shifted twice from a mode test exercised in
only two of its three states, and the minimap was covered by a panel moved on
an assumption. Three screenshot-driven builds failed on the sub-flyout bar
before one `SBLT` trace found the cause immediately.

**When two symptoms contradict each other** (centre it here, attach it there),
the work is at the wrong LAYER — move up one level. That is exactly how the
sub-flyout ring resolved: the ring was never what should move, the container
was.
