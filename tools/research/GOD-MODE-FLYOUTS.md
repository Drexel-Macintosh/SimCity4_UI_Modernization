# God-mode tool flyouts

Mechanism reference for the god-mode tool flyouts: how each one is identified,
docked and scaled, and the full reverse engineering of the Create Disasters
flyout's paint pipeline. The runtime code lives in `src/UiSpike.cpp` →
`UiSpike::ScaleGodFlyouts()`.

Companion references: `tools\research\SC4-UI-ENGINE.md` (the engine model and
the canonical `cIGZWin` vtable map) and `tools\research\SDK-GAPS.md` (where the
community headers diverge from the shipped executable).

---

## The five god tools

| # | Tool (button) | Flyout window | Dock offset (1x units) | Scaling mechanism |
|---|---|---|---|---|
| 1 | Terraform (green) | `0x49923239` | (6, −80) | dock + subtree scale |
| 2 | Terrain Effects (tan) | `0xCA35CBED` | (6, 40) | dock + subtree scale |
| 3 | Reconcile Edges | none | — | — |
| 4 | Create Disasters (orange) | anonymous, `id == 0` | (6, 130) | born-at-place |
| 5 | Day/Night (blue) | `0xCA35CBED` (shared with 2) | (6, 160) | rides flyout 2 |

Flyouts 1, 2 and 5 are converged and locked. Their offsets are derived
constants, not tuning values — treat a change to any of them as a change to the
derivation below.

---

## The dock mechanism (flyouts 1, 2 and 5)

The dock target is the scaled toolbar strip `0xC991EDA8`'s live position plus a
design offset scaled by the tier factor:

```
targetL = tbLiveL + ScaleRound(offX, f)
targetT = tbLiveT + ScaleRound(offY, f)
```

Offsets are **derived**, never hand-tuned. From the clean 1:1 vanilla capture at
1280×1024 (f = 1.0), with the toolbar at stock (5,435):

```
offset = flyoutStock − toolbarStock

0x49923239  stock (11,355)  ->  ( 6,-80)   terraform
0xCA35CBED  stock (11,475)  ->  ( 6, 40)   terrain-fx
```

Both derived values equal the confirmed-correct shipped ones, which validates
the formula. Bracketing an offset by eye does not converge: the disaster
container was bracketed X 22 (too far left) ↔ 126 (too far right) and Y 518 (too
high) ↔ 758 (too low) across eight build cycles without landing, because the
container is not the window that positions the visible circle.

### Day/Night rides Terrain Effects

Terrain Effects and Day/Night **share** the `0xCA35CBED` window. Its offset
drives whichever tool is showing, 1:1:

- `offY 40` → ring lands on button 2 (correct for Terrain Effects)
- `offY 160` → ring lands on button 5 (correct for Day/Night)

So the offset is selected at runtime by which tool is active. Detection is by
`0xCA35CB74` visibility — Day/Night's sub-tool, visible only while Day/Night is
the open tool. Terrain Effects swaps in the four-button set
`0x0AA44502..05` instead. The shared root `0xCA35CBED` stays `vis=1` for both,
so it cannot be used as the discriminator. Day/Night has no dock entry of its
own.

### Per-flyout rules

- **`gateVisible` is per-flyout.** Terrain Effects must be gated on
  `IsVisible()`, because a closed Terrain-FX flyout docked on top of Day/Night
  breaks Day/Night. The disaster container is `vis=1` in every logged sighting
  and the sweep block that finds it requires `IsVisible()`.
- **`InvalidateSelfAndParents()`** (`cIGZWin.h:187`) must follow any geometry
  change. Without it the game keeps the stale paint until a mouse hover
  invalidates the region, so the flyout scales only after the pointer crosses
  it.
- **`ScaleSubtree` doubles child POSITIONS as well as sizes.** That is correct
  for flyouts 1, 2 and 5, whose whole layout scales coherently. It destroys the
  disaster flyout: the thumbnail strip flies from relative X184 to X368.

---

## The founded-city god toolbar `0x0A78827A`

`0x0A78827A` is the god toolbar in a founded city. Its `.UI` script
`I-aa53e3ea` lists the Obliterate / Reconcile / Disasters / Day-Night buttons.

Before a city is founded the window sits hidden (`vis=0`) at abs(5,1071),
74×291, and moving it changes nothing on screen. Once a city exists it goes
live and carries the god UI, so it belongs in `SCALED_WINDOW_IDS`
(`tools/selective-safe/build_selective_safe.py`) and in the runtime lists.
Removing it from either breaks founded-city god mode.

`0x0A78827A` is not the Create Disasters flyout. The visible disaster flyout is
an anonymous (`id == 0`) child of the 3D view `0x9A47B417`.

The `SCALED_WINDOW_IDS` marker recurses into **all** children of the id it
marks. On the disaster thumbnails that doubled the textures while the control
still blitted them with 1× source rects, which reads on screen as zoomed-in
thumbnails. Supplying the strip's item metrics from the birth path resolves it;
`0x0A78827A` stays in both the art list and the runtime lists.

---

## Create Disasters — anatomy

Three visually independent pieces: an **orange circle**, an **orange bar**, and
the **disaster pictures** (clickable thumbnails).

Only **two windows** exist for it, established by diffing 29 opened frames
against 41 closed ones with anonymous windows included:

```
0x00000000  par 0x9A47B417   282x678   <- container (paints circle + bar)
0x00000000  par 0x00000000    88x578   <- thumbnail strip (the pictures)
```

When settled, the container sits at abs(126,518), 282×678.

The circle and the bar are **painted art inside the container**, not child
windows. A change-triggered probe running at sweep frequency recorded **zero**
geometry changes across open → settle → hover → mouse-away with the dock
disabled, while the bar visibly moves on hover — the hover is a paint-state
change. A 1-second `LiveDump` can only ever capture settled states, which is
why lower-frequency sampling never showed this. Because the pieces are not
windows, no dock, offset, or resize gives independent control of them.

### Class identity

```
container 282x678  vtable = 0x00AB6AA8   answers ONLY to cIGZWin
strip      88x578  vtable = 0x00AB6D88   answers ONLY to cIGZWin
generic windows    vtable = 0x00ADF6A0   (GZWinBMP: it sizes the draw from
                                          the SOURCE image)
```

Two distinct specialized classes. Neither exposes `cIGZWinGen` or
`cIGZWinBMP`, so there is no supported image or paint API on them.

---

## Create Disasters — the Plot pipeline

Container `Plot()` (`0x0079B0E0..0x0079B48F`, 279 instructions) is disassembled
in full, and the pipeline explains why no member-field write scales the art.

1. **Top gate:** `test byte[0x114],1; je end`. `Plot` only redraws when the
   dirty bit is set, and clears it afterwards. The bit is normally 0 (confirmed
   live), so `Plot` early-exits to the blit path and re-blits the cached buffer.
2. **Redraw path (dirty = 1 only):** reallocates the internal buffer `[0xdc]`
   to the window-rect size `[0xa8..0xb4]` — the realloc check at `0x0079B117`
   compares buffer W/H against `[0xb0]-[0xa8]` / `[0xb4]-[0xac]` — then draws
   the bar and circle into it via `[0xd8]`(drawContext)`->[0x74]` plus the arc
   helper `0x8d8bc0`, using rects built from the window W/H minus the
   `[0xe0..0xf4]` field insets.
3. **Blit path (always):** `[0x68]`(dest buffer)`->Blt(src=[0xdc], ...)` using
   the rect at `[0x24..0x30]`. `[eax+0x30]` is `cIGZBuffer` idx12
   `GetBufferArea`; `[ebx+0x74]` is idx29 `Blt`.

### Live object values (natural, un-forced)

```
r24 [0x24..0x30] = (0,0,282,678)     window SIZE at local origin
win [0xa8..0xb4] = (66,682,348,1360) absolute rect (282x678, docked at 66,682)
dst68 [0x68]     = 2400x1600 32bpp   the full-screen buffer
srcBuf [0xdc]    = 141x339 32bpp     HALF the window (282x678)
v100 [0x100]=138  dirty[0x114]=0x00  f118=256 f11c=0 f120=0
```

The cached buffer is 141×339 — exactly half the on-screen window — so the flyout
is a stretch-blit of a 141×339 buffer onto a 282×678 window. The compact look is
inherent to the stock art's thin bar and small thumbnails magnified by a bitmap
stretch, rather than the real 2× sub-windows Terraform uses.

### The four container draws — ⚠ CORRECTED 2026-08-23: the table below is the 2x-WINDOW RE-FLOW, not stock 1x

**This section was mis-titled "at 1x" and that mislabel cost real
debugging time.** The rects below were captured with the emulator object's
window rect at its live MODDED state (282x678 — see `emu_plot.py`'s
default fields), with 1x layout fields: the bar is right-anchored to the
DOUBLED window (`282−53 = 229`), i.e. this is the mixed-1x/2x re-flow the
game produces at 2x, which is exactly the layout the mod's draw hooks
receive and must reconstruct from. Only the ring rect is stock-identical
(left-anchored, Y from a field — confirmed byte-identical at both window
sizes).

TRUE STOCK 1x (window = buffer = 141x339; run
`python tools/flyout-sim/emu_plot.py --fields a8=0,ac=0,b0=141,b4=339 --buf=141,339`,
golden in `_tests/golden/disaster-stock-1x-drawlist.txt`):

```
bar-top cap  src(94,0,147,25)    dst(88,0,  141,25)
bar-spine    src(94,25,147,37)   dst(88,25, 141,314)  25 tiles of 53x12, last clipped to 1 row
bar-bot cap  src(147,37,200,62)  dst(88,314,141,339)  a DIFFERENT source sprite than the top cap
ring/circle  src(0,0,94,62)      dst(0,138, 94,200)   ring right 94 overlaps bar left 88 by 6px - THE WELD
```

The 2x-window re-flow (window = buffer = 282x678, `emu_plot.py` defaults,
golden in `_tests/golden/disaster-live-2x-drawlist.txt`):

```
bar-top cap  dst(229,0,  282,25)   x[229-282]  width 53 from field 0xe0  (right-anchored to the LIVE window)
bar-spine    dst(229,25, 282,653)  53 tiles via the tiler 0x8d8bc0
bar-bot cap  dst(229,653,282,678)
ring/circle  dst(0,138,  94,200)   x[0-94]     LEFT-anchored, identical to stock
```

The v4.0.40 rebuild (see `_tests/REGRESSION.md` "DISASTER FLYOUT REBUILD")
maps each re-flowed draw back to its stock rect and scales it by f, which
is why the weld is exact at every tier with zero tuning.

With all six fields doubled the ring reaches 188 wide and the bar 106 — the
correct 2× target, where the ring encircles the 2× button and the bar is twice
as thick. The circle is **left**-anchored (`x[0,ec]`) and the bar is
**right**-anchored (`x[W-e0,W]`); that opposite anchoring is why blind field
doubling looks wrong on screen.

The element draws are `[0xdc]->Blt(drawCtx, srcRect, dstRect)` and are 1:1 —
source size equals destination size. Doubling the fields doubles both, so the
source rect reads past the 1× texture edge and the art tiles. The working form
is to double the fields for a 2× destination and hook `[0xdc]`'s `Blt` to halve
the source rect back to 1×, which makes the real texture stretch into the 2×
destination.

### Member field values (container 282×678)

```
Offset  Index   Value   Role in Plot()
0xE0    m[0x38]   53    bar pitch / vertical spacing
0xE4    m[0x39]   25    vertical offset
0xE8    m[0x3A]   12    horizontal offset
0xEC    m[0x3B]   94    circle/bar size param
0xF0    m[0x3C]   62    state offset
0xF4    m[0x3D]    6    small offset
```

Strip `Plot()` (`0x0079AA70`) loops over items from the `[this+0xd8]` array,
reading item size from `[this+0xf4]`, spacing from `[this+0xf8]` and count from
`[this+0xfc]`, and computes its blit rects from `[this+0x24]`, `[this+0x28]`
and `[this+0x68]`.

Neither `Plot()` contains a single hardcoded drawing immediate — there is no
`push imm32` for a coordinate in either function. Every coordinate comes from a
member field, so binary-patching immediates is not a route here.

---

## Create Disasters — levers that do not scale the art

| Lever | Result | Meaning |
|---|---|---|
| 6 fields `[0xe0..0xf4]` ×2 (persisted, verified) | no change | the fields are insets, not size |
| Window rect `[0xa8..0xb4]` ×2, no redraw | no change | on-screen size is not this rect |
| Window rect ×2 + fields ×2 + force dirty | shrank | the redraw realloc'd the buffer 141 → 564, destroying the 141 → display stretch |
| `r24 [0x24..0x30]` ×2 (stuck, verified) | no change | on-screen size is not r24 |
| `ScaleSubtree` on the container | strip and bar fly apart | positions scale independently of the painted art |
| Force-scaling the container | window became 564×1356, art stayed 1× | the art does not follow the window rect |
| `SetW`/`SetH` virtuals ×2 | ring vanished, bar stretched vertically, strip flew right | `SetW` sets dirty → redraw → buffer realloc → the stretch is lost |
| Forced redraw (dirty bit only) | buffer realloc'd 141 → 282 and re-flowed | the internal layout is WIDTH-driven, so a wider draw re-flows rather than magnifies |

The on-screen size is therefore neither the window rect, nor r24, nor the
fields. It is set by the **parent's compositing of the child** — the blit
destination region on `[0x68]` — decided when the parent asks the child to
paint, and reachable through no member field. Position **is** reachable:
`GZWinMoveTo` moves the flyout and updates `[0xa8]`.

### The screen composite is a 1:1 clipped copy

Hooking the flyout's screen composite `[0x68]->Blt` (idx29) through a surgical
per-instance vtable swap around the container's `Plot` call — restored
immediately after, so no other window is affected — captures the real arguments:

```
Blt(src=[0xdc] 141x339 buffer, srcRect a2=(0,0,141,339),
    dstRect a3=(0,0,282,678), clip a4=null)
```

`a3` is not a scale lever. Set to 846×2034 it accumulates to 2538×6102 — `a3`
is a persistent, reused rect — and the screen is unchanged. A 2538×6102
destination producing zero change proves the `Blt` is a **1:1 clipped copy**,
not a stretch: on-screen art size equals the SOURCE buffer size (141),
positioned at the destination origin and clipped to the destination.

### Reading the rendered frame back is not possible

The orange ring's pixel position cannot be measured in-process:

- The container has **no private buffer** — `GetPrivateBuffer()` returns null.
- It paints into the shared main/parent draw-to buffer, 2400×1600 32bpp
  (`qiBuf=1`), at absolute screen coordinates. That is the right buffer in
  principle.
- That buffer is **GPU-only**. `Lock(0)` and `Lock(0x8000)` both succeed, yet
  every pixel reads `(0,0,0)` and `GetColorSurfaceBits()` / `Stride()` return
  **0**. There is no CPU-readable copy of the frame, and `GetPixel` sees
  nothing.
- The container's own `GetBufferToDrawTo()` returns junk (`1537×0 qiBuf=0`)
  outside its draw sequence.

The `GZPaint` → `Plot` hook at index 88 does fire and is a valid interception
point, but the pixels it writes go straight to GPU memory. Objective
measurement of the ring must come from a real screen capture.

---

## Create Disasters — the born-at-place mechanism

The disaster flyout is scaled at **birth** rather than at runtime, through
`SubPlaceDetour` at return address `0x007E74D6` — distinct from the first-level
twin's `0x007EB196`. Size, dock and item metrics are all applied at birth, plus
one forced repaint for the chrome. The live dock block is findable in
`src/UiSpike.cpp` by the string `"disaster flyout (anon)"`; its offsets are
`gRingDockX = 6` / `gRingDockY = 130` in 1x units (scaled by `f` at use), both
live-tunable through `[Disaster] DockX` and `DockY` in the ini.

Two properties of that mechanism are load-bearing:

- **Born-scaling takes the window off the sweep.** The sweep had been supplying
  the strip's item metrics, so the birth path must supply them itself or the
  thumbnails render tiny.
- **The `gStripBase*` latch is game-wide and shared.** Priming it from a scaled
  value duplicates picker icons across the whole game. Prime a shared latch from
  a STOCK value.

Full generation-by-generation detail of the birth mechanism is in
`tools\research\MECHANISM-GENERATIONS.md`.

---

## The `cIGZWin` draw-related vtable slots

`cIGZWin::GZPaint` is virtual number **85** in the header, and `cIGZUnknown` adds
exactly three slots, with neither concrete class declaring a virtual
destructor. The real per-class draw entry is index **88**, not 87: the vendor
header is missing one virtual at real slot 57, so every index past it shifts by
one. Index 87 is `GetNotificationTarget`. The canonical copy of this table is
`SC4-UI-ENGINE.md` §2.1, and the header-drift rule is `SDK-GAPS.md` §1.

| idx | offset | virtual | VA |
|---|---|---|---|
| 87 | `+0x15C` | `GetNotificationTarget` | `0x0099BE4C` |
| 88 | `+0x160` | **`GZPaint`** (per-class draw) | base no-op `0x00949ADE`; container `0x0079B0E0`; strip `0x0079AA70` |
| 89 | `+0x164` | **`Plot`** (composite + present) | `0x0099BA07` |
| 90 | `+0x168` | `CalcAbsoluteArea` | `0x0099DCE4` |
| 91 | `+0x16C` | `InvalidateSelf` | `0x0099BECC` |
| 92 | `+0x170` | `InvalidateSelfAndParents` | `0x0099BED1` |
| 93 | `+0x174` | `GetDrawContext` (`= [ecx+0x6c]`) | `0x0099BEF9` |
| 94 | `+0x178` | `GetBufferToDrawTo` (`= [ecx+0x68]`) | `0x0099BEFD` |
| 95–98 | — | `SetBufferToDrawTo` / `…Recursive` / `SetAreaToDrawTo` / `…Recursive` | `0x0099C6F8` / `0x0099D57E` / `0x0099CF6A` / `0x0099D5B7` |
| 100 | `+0x190` | `PrivateBuffer(bool)` — **takes an argument** | `0x0099EA70` |
| 101 | `+0x194` | `GetPrivateBuffer` (`= [ecx+0x64]`) | `0x009D419D` |

`cIGZWin` has 144 virtuals (147 slots) and a concrete class adds more, so a
vtable copy of 256 entries covers every case. Hooks are installed as a
**per-instance vtable copy**; the shared class vtable (`0x00AB6AA8`) is never
written, so no other window is affected.

### Hooking the range safely

`__thiscall` is callee-cleanup, so a thunk declared with the wrong argument
count cleans the wrong number of stack bytes and corrupts the stack. Indices
87..97 are hooked as a range. The community-header names for 95–98 include
argument-taking variants, so the range is not uniformly zero-argument; hooking
it in full is safe only because the thunks are declared
`template <int IDX>`, return `uintptr_t`, and never assume an arity. Returning
`uintptr_t` preserves EAX exactly for every slot — the void-returning ones
simply have their garbage EAX ignored by the caller.

**Built-in positive control:** a forced `InvalidateSelfAndParents()` routes
through the swapped vtable, so **slot 92 must fire**. If 92 fires and the
others stay silent, the hook machinery is proven and the silence is real
evidence. If 92 also stays silent, the vtable swap is not taking effect and the
index base is wrong.

### Two slot-identity traps

- **Slot 89 (`Plot`, `0x0099BA07`)** ends `mov al,bl; ret`, writing only the
  low byte of `eax`. Its return value is caller garbage with `al = 0x01`, which
  reads as `0x06752001` for the container and the strip alike — an identical
  value from two different windows, and not a per-window rect pointer.
  Dereferencing it yields nonsense (`L=422416 T=-1340969632`).
- **Slot 90 (`CalcAbsoluteArea`, `0x0099DCE4`)** is the real absolute-rect
  recompute. It returns nothing and writes the rect in place at
  `[this+0x14..0x20]`.

A hook installed on index 87 sits on `GetNotificationTarget` and never fires:
it logs a clean install with zero calls even after repeated forced
`InvalidateSelfAndParents()`, which is a null produced by the slot arithmetic
rather than by the window. The container is painted through slot 88
(`0x0079B0E0`).

---

## Diagnostics

All in `ScaleGodFlyouts()`.

| Log prefix | What it does |
|---|---|
| `DPROBE` | Walks the whole `0x9A47B417` subtree each sweep and logs only windows whose position, size or visibility **changed**. Keyed by **window pointer** — keying by id or parent collapses all the anonymous windows into one entry. Band-limited to X −150..500, Y 380..1250 to exclude the constantly animating bottom query panels. |
| `DCLASS` | One-shot per window: the vtable pointer plus which `GZWin` interfaces the window answers to. |
| `DHOOK` | `GZPaint` hook install and fire logging, observe-only. |

Enable with `LiveDumpMs=1000` and `LogLevel=3` in
`Documents\SimCity 4\Plugins\SC4UIScale.ini`.

---

## Building and deploying

```
MSBuild src\SC4UIScale.vcxproj -p:Configuration=Release -p:Platform=Win32
copy build\Release\SC4UIScale.dll  "%USERPROFILE%\Documents\SimCity 4\Plugins\"
```

Close SimCity 4 first — a running game holds the DLL open. Bump
`UISCALE_VERSION_STR` in `src/SC4UIScaleDllDirector.cpp` per build so the log
banner identifies which binary is loaded.

## Verifying

Open each god tool and check that the coloured ring wraps its own button:
Terraform → 1, Terrain Effects → 2, Create Disasters → 4, Day/Night → 5.
Nothing may render on button 3, which has no flyout. Check both the **settle**
and the **hover** state — several defects in this area render correctly in one
and wrongly in the other.
