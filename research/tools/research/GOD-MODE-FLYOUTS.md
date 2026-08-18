> ## ⚠ SUPERSEDED IN PLACES — READ THIS FIRST (2026-07-29)
>
> This doc predates v2.12.2 and later work. **One of its instructions is now
> actively harmful:** it states twice that `0x0A78827A` is inert and should be
> REMOVED from `SCALED_WINDOW_IDS`. That is wrong — `0x0A78827A` IS the
> founded-city god toolbar, and it must stay in BOTH the art list and the
> runtime lists. Following the old advice re-breaks founded-city god mode.
>
> Also superseded here: the ticker-marquee runtime-doubling advice (the marquee
> is now never-touch with its width shipped in DATA), and the class label
> `0x00ADF6A0` = "generic windows" (it is GZWinBMP-like: it sizes the draw from
> the SOURCE image).
>
> Current sources of truth: `tools\research\SC4-UI-ENGINE.md` (engine model,
> incl. §9 listing every doc contradiction found), `_tests\REGRESSION.md`,
> and `HANDOFF.md`. Keep this file for the god-flyout mechanism history —
> the derivations and the click-fix reverse engineering remain valid.

# God-mode tool flyouts — status, mechanisms, and the Disaster problem

> **2026-07-29:** god mode remains COMPLETE and its docks LOCKED, but four
> later laws generalise the mechanisms in this log (alignment markers are
> positioning data in DATA as well as at runtime; runtime is sometimes
> structurally too late so the fix belongs in the shipped `.UI`; never scale
> font/art-sized controls; identify windows positively, never by size
> heuristic) — plus the LOAD-ORDER LAW, which can silently shadow any art fix
> here. They are summarised at the top of `HANDOFF-god-mode-flyouts.md`, with
> full detail in `_tests\REGRESSION.md` and the test axes in
> `_tests\SCENARIOS.md`.

Last updated 2026-07-28. Current build: **v2.10.5-bar-widen** (disaster BAR+RING+
PICTURES all ~2x in-game & clickable). **>>> For current state + next steps, read
`HANDOFF-god-mode-flyouts.md` → "SESSION STATE — READ THIS FIRST" (very top). <<<**
This file below is the older running log.
All work lives in `src/UiSpike.cpp` → `UiSpike::ScaleGodFlyouts()`.

> **NEW DEVS / MODELS: read `HANDOFF-god-mode-flyouts.md` (same folder) FIRST.**
> It is the self-contained onboarding doc and supersedes this file for getting
> started; this file remains the raw running log of dead-ends and detail.
>
> **Disaster status (v2.7.76): DOCKED, member-field doubling UNTESTED.**
> Container docked at offset (28,130). v2.7.76 doubles 6 member fields at
> offsets 0xE0-0xF4 on the container (the fields Plot() reads for drawing
> coordinates). **Has NOT been tested** — user handed off before launching SC4.
> The dock block is LIVE (search `"disaster flyout (anon)"`).

---

## STATUS AT A GLANCE

| # | Tool (button) | Flyout window | Docked | Scaled | State |
|---|---|---|---|---|---|
| 1 | Terraform (green) | `0x49923239` | offset (6,−80) | yes | **DONE, user-confirmed** |
| 2 | Terrain Effects (tan) | `0xCA35CBED` | offset (6,40) | yes | **DONE, user-confirmed** |
| 3 | Reconcile Edges | *(no flyout)* | — | — | n/a |
| 4 | **Create Disasters (orange)** | anonymous `id==0` | **yes (28,130)** | **yes** | **BORN-AT-PLACE v2.39.4 — awaiting eyes-on** |
| 5 | Day/Night (blue) | rides `0xCA35CBED` | via coupling | yes | **DONE, user-confirmed** |

**Do not "improve" 1/2/5 casually — they were painful to converge and are confirmed correct.**

---

## THE MECHANISM THAT WORKS (flyouts 1, 2, 5)

Dock target = scaled toolbar strip `0xC991EDA8` live pos + design offset × f:

```
targetL = tbLiveL + ScaleRound(offX, f)
targetT = tbLiveT + ScaleRound(offY, f)
```

**Offsets are DERIVED, never hand-tuned.** From `_vanilla-reference/FINDINGS.md`
"EXACT STOCK DIMENSIONS" (1280×1024, f=1.0), with toolbar stock (5,435):

```
0x49923239 (11,355) -> ( 6,-80)   terraform    <- matches shipped value
0xCA35CBED (11,475) -> ( 6, 40)   terrain-fx   <- matches shipped value
```
Both derived values equal the confirmed-correct ones, so the formula
`offset = flyoutStock − toolbarStock` is validated. **Use it. Do not guess
offsets by eye — many hours were lost doing exactly that.**

### Day/Night rides Terrain-FX (non-obvious, critical)
Terrain-FX and Day/Night **share** the `0xCA35CBED` window. Its offset drives
whichever is showing, 1:1:
- `offY 40` → ring on btn2 (correct for terrain-fx)
- `offY 160` → ring on btn5 (correct for day/night)

So the offset is chosen at runtime by which tool is active, detected via
`0xCA35CB74` visibility (day/night's sub-tool; visible ONLY under day/night —
terrain-fx shows the 4-button set `0x0AA44502..05` instead). Day/Night has no
dock entry of its own; `0xABB26B0E` is a frozen hidden template at Y1045.

### Other hard-won rules
- **`gateVisible` is per-flyout.** Terrain-FX must be gated on `IsVisible()`
  (a closed one docked onto day/night breaks it). ⚠ **CORRECTED 2026-07-31:**
  the sentence that used to sit here — *"Disaster's root is `vis=0` always"* —
  was about `0x0A78827A`, a **different** window (see Dead end 1). The real
  disaster container is `vis=1` in every logged sighting, and the sweep block
  that finds it *requires* `IsVisible()`. Do not re-derive from the old claim.
- **`InvalidateSelfAndParents()`** (cIGZWin.h:187) after any geometry change —
  otherwise the game keeps the stale paint until a mouse hover invalidates it
  ("only scales after I move the mouse over it").
- **`ScaleSubtree` doubles child POSITIONS, not just sizes.** Correct for 1/2/5
  (whole layout scales coherently); it **destroys** Disaster (flings its
  thumbnail strip from rel X184 → X368).

---

## DISASTER (button 4) — SOLVED v2.39.4 (awaiting eyes-on). Read before touching.

> **2026-07-31 — this section was headed "UNSOLVED" for 28 versions and was two
> mechanism generations stale.** Everything below about the ANATOMY is still
> correct and still worth reading; the "no independent control" conclusion is
> not. What changed: the flyout was the **first** one we ever scaled (v2.11.x)
> and was still on generation 1 (scale-after-`IsVisible()`), while every other
> flyout had been upgraded twice. v2.39.0–.4 moved it to **born-at-Place**
> (`SubPlaceDetour`, return address `0x007E74D6`, distinct from the first-level
> twin's `0x007EB196`): size, dock and item metrics are now all applied at
> birth, plus one forced repaint (`DISHEAL`) for the chrome.
>
> Two self-inflicted regressions were paid for on the way, both now laws:
> born-scaling took the window **off the sweep**, which had been silently
> supplying its strip item metrics (→ tiny thumbnails, law 16); and writing
> metrics at birth **poisoned the game-wide shared `gStripBase*` latch** (→
> duplicated picker icons everywhere, law 17 — prime a shared latch from a
> STOCK value, never from a scaled one).
>
> Details: `_tests\REGRESSION.md` → "CREATE DISASTER FLYOUT", and
> `tools\research\MECHANISM-GENERATIONS.md`.

### What it is
Three visually independent pieces: **orange circle**, **orange bar**,
**disaster pictures** (clickable thumbnails).

Only **two windows** exist for it (verified by open-vs-closed diff over 29 open
and 41 closed frames, anonymous windows included):

```
0x00000000  par 0x9A47B417   282x678   <- container (paints circle + bar)
0x00000000  par 0x00000000    88x578   <- thumbnail strip (the pictures)
```

### Dead ends — do NOT repeat these
1. **`0x0A78827A` is NOT the disaster flyout**, despite that label in
   `_vanilla-reference/FINDINGS.md`. It is a hidden `vis=0` god sub-tool strip
   (its `.UI` script `I-aa53e3ea` lists Obliterate/Reconcile/Disasters/
   Day-Night buttons) sitting at abs(5,1071) 74×291. **The FINDINGS label is
   wrong.** ⚠ But the rest of this entry was measured **before a city was
   founded** — it goes LIVE once one exists, and "docking/scaling it changes
   nothing" is false there. It IS the founded-city god toolbar; see the banner
   at the top of this file. Keep it in `SCALED_WINDOW_IDS`.
2. **Hand-tuned offsets.** X was bracketed 22 (too left) ↔ 126 (too right) and
   Y 518 (too high) ↔ 758 (too low) across ~8 build cycles without converging.
   The container is not the thing that positions the circle.
3. **`ScaleSubtree` on the container** — flings the strip and bar apart.
4. **Force-scaling the container** — window became 564×1356 but the art stayed
   1×; the art does not follow the window rect.

### The decisive finding (DPROBE)
A change-triggered probe running at **sweep frequency** (the 1-second
`LiveDump` can only ever capture settled states, which is why every earlier
investigation failed) recorded **ZERO geometry changes** across
open → settle → hover → mouse-away, with our dock disabled.

**Yet the bar visibly jumps on hover.** Therefore the circle and bar are
**painted art inside the container**, not windows. The hover is a *paint-state*
change. This is why no dock, offset, or resize ever gave independent control.

### Class identity (DCLASS probe)
```
container 282x678  vtable = 0x00AB6AA8   answers ONLY to cIGZWin
strip      88x578  vtable = 0x00AB6D88   answers ONLY to cIGZWin
generic windows    vtable = 0x00ADF6A0
```
Two distinct specialized classes. Neither exposes `cIGZWinGen`/`cIGZWinBMP`,
so **there is no supported image/paint API** — the cheap route is closed.

### Where we stopped: the draw hook (IN PROGRESS)
Only remaining lever = intercept `GZPaint()`.

- `cIGZWin::GZPaint` is virtual **#85**. `cIGZUnknown` adds exactly 3 slots and
  **neither class declares a virtual destructor** (verified) ⇒ **vtable index 87**.
- `cIGZWin` has 144 virtuals (147 slots); concrete class adds more ⇒ copy 256.
- Installed as a **per-instance vtable copy**; the shared class vtable
  (0x00AB6AA8) is **never written**, so no other window is affected.

**RESULT (v2.7.33-dprobe): installed cleanly, NEVER FIRED.**
```
DHOOK installed on ptr2BFED818 (282x678) origVt=00AB6AA8 origGZPaint=0099BE4C
installed: 1   FIRED: 0
```
One install (the tight size gate 200-400 x 500-900 correctly matched only the
disaster container), no crash, and **zero fires even after 6 forced
`InvalidateSelfAndParents()` calls**. So this window is **not painted through
its own `GZPaint` virtual** — something else drives its rendering.

### Slot scan (v2.7.34-slotscan) — the systematic replacement
Guessing one slot at a time is too slow, so hook the whole draw-related RANGE
at once and log which the game actually calls.

**SAFETY RULE — only zero-argument slots may be hooked this way.** `__thiscall`
is callee-cleanup, so a thunk declared with the wrong argument count cleans the
wrong number of stack bytes and corrupts the stack. Indices **87..97** are the
range scanned.

⛔ **THE SLOT TABLE THAT USED TO SIT HERE WAS OFF BY ONE, AND THIS FILE IS
WHERE THAT ERROR WAS BORN.** It omitted **slot 89 `Draw`**, shifting every name
after it, and it was copied verbatim into `SC4-UI-ENGINE.md` §2.1 and into
`UiSpike.cpp`'s header. It cost a probe build on #89: a caller asking "93" for
`GetBufferToDrawTo` got `[ecx+0x6c]`, the DRAW CONTEXT, and "92" returned NULL.
**Corrected 2026-08-01 from the exe** (base `cGZWin` vt `0x00A8D000`):

| idx | offset | virtual | VA |
|---|---|---|---|
| 87 | `+0x15C` | `GZPaint` | `0x0099BE4C` |
| 88 | `+0x160` | **`Plot`** | base `0x009A0A17` / minimap `0x007A79B0` |
| 89 | `+0x164` | **`Draw`** ← was missing | `0x0099BA07` |
| 90 | `+0x168` | `CalcAbsoluteArea` | `0x0099DCE4` |
| 91 | `+0x16C` | `InvalidateSelf` | `0x0099BECC` |
| 92 | `+0x170` | `InvalidateSelfAndParents` | `0x0099BED1` |
| 93 | `+0x174` | `GetDrawContext` (`= [ecx+0x6c]`) | `0x0099BEF9` |
| 94 | `+0x178` | `GetBufferToDrawTo` (`= [ecx+0x68]`) | `0x0099BEFD` |
| 95–97 | — | **UNNAMED — hooked, never identified** | — |
| 100 | `+0x190` | `PrivateBuffer(bool)` — ⛔ **NOT zero-arg** | `0x0099EA70` |
| 101 | `+0x194` | `GetPrivateBuffer` (`= [ecx+0x64]`) | `0x009D419D` |

⚠ The old names for 94–97 (`SetBufferToDrawTo`, `SetBufferToDrawToRecursive`,
`SetAreaToDrawTo`, `SetAreaToDrawToRecursive`) came from the community header,
and at least some of those **take arguments** — so the sentence "87..97 are
*exactly* the zero-arg draw group" was never true. It is deleted above rather
than repeated. The range is still hooked in full, and that is safe only because
the thunks return `uintptr_t` and never assume an arity. See
`SC4-UI-ENGINE.md` §2.1 for the canonical copy.

Thunks are `template <int IDX>` and return `uintptr_t`, which preserves EAX
exactly for every one of them (the void-returning slots just have their garbage
EAX ignored by the caller).

**Built-in positive control:** our own forced `InvalidateSelfAndParents()` now
routes through the swapped vtable, so **slot 92 must fire** (this was written as
"slot 91" under the old off-by-one numbering — one more way the wrong table made
a real null unreadable). If 92 fires and others do not, the hook machinery is
proven and the silence is real. If 92 also stays silent, the vtable swap itself
is not taking effect and the index base is wrong.

Next: whichever slot fires is the live interception point on the exact window
that paints circle + bar. If NOTHING fires including 91, move the hook up the
parent chain to `0x9A47B417`.

### DEAD END — reading the rendered frame back (v2.7.33–2.7.41, do NOT retry)
Nine builds tried to measure the orange ring's pixel position objectively by
reading the render buffer in-process. It cannot be done:
- The container has **no private buffer** (`GetPrivateBuffer()` = null).
- It paints into the shared **main/parent draw-to buffer = 2400×1600 32bpp**
  (`qiBuf=1`), at absolute screen coords — the right buffer in principle.
- But that buffer is **GPU-only**: `Lock(0)`/`Lock(0x8000)` succeed, yet every
  pixel reads `(0,0,0)` and `GetColorSurfaceBits()`/`Stride()` return **0**.
  There is no CPU-readable copy of the frame. `GetPixel` sees nothing.
- The container's own `GetBufferToDrawTo()` returns junk (`1537×0 qiBuf=0`)
  outside its draw sequence.
So the ring's color/position is NOT measurable from the DLL. The GZPaint→Plot
hook (index 88) does fire and IS a valid interception point, but the pixels it
writes go straight to GPU memory. Objective measurement, if ever needed, must
come from a real screen capture, not a buffer read. **The container is at
abs(126,518) 282×678 when settled** (matches the old FINDINGS value).

### Known regression to fix later
`0x0A78827A` is in `SCALED_WINDOW_IDS`
(`tools/selective-safe/build_selective_safe.py:102`) and the marker recurses
into **all children** — so we 2×'d the disaster thumbnail textures while the
control still blits them at 1× source rects. **That is why the thumbnails look
zoomed in.** Removing it requires regenerating the dats and updating the
240-entry expectation in `_tests/Test-DatIntegrity.ps1`.

---

## DEBUG INSTRUMENTS CURRENTLY IN THE BUILD

All in `ScaleGodFlyouts()`; remove when Disaster is settled.

| Log prefix | What it does |
|---|---|
| `DPROBE` | Walks all of `0x9A47B417`'s subtree each sweep; logs only windows whose pos/size/vis **changed**. Keyed by **window pointer** (keying by id/parent collapses anonymous windows together — that mistake wasted a run). Band-limited to X −150..500, Y 380..1250 to exclude the constantly-animating bottom query panels. |
| `DCLASS` | One-shot per window: vtable pointer + which GZWin interfaces it answers to. |
| `DHOOK` | GZPaint hook install + fire logging (observe-only). |

**The disaster dock block is wrapped in `#if 0`** so our movement doesn't
pollute the probe. Re-enable only after the three elements are controllable.

Settings: `LiveDumpMs=1000`, `LogLevel=3` in
`Documents\SimCity 4\Plugins\SC4UIScale.ini`.

---

## BUILD / DEPLOY

```
MSBuild src\SC4UIScale.vcxproj -p:Configuration=Release -p:Platform=Win32
copy build\Release\SC4UIScale.dll  "%USERPROFILE%\OneDrive\Documents\SimCity 4\Plugins\"
```
Kill SimCity first (it locks the DLL). Bump `UISCALE_VERSION_STR` in
`src/SC4UIScaleDllDirector.cpp` every build so the log banner identifies it.

## VERIFYING
Open each god tool and check the coloured ring wraps its own button:
Terraform→1, Terrain-FX→2, Disaster→4, Day/Night→5. Nothing may render on
button 3 (Reconcile has no flyout). Check both the **settle** and **hover**
states — several bugs only appeared in one of them.

---

## 2026-07-27 UPDATE (full Plot pipeline reverse-engineered)

Disassembled container Plot() **completely** (0x0079B0E0..0x0079B48F, 279 insns;
dump in scratch `container_plot_full.txt`) and probed the live object. The whole
draw/blit pipeline is now understood — and it explains why NO member-field lever
scales the art.

### The pipeline (container 282x678, vtable 0x00AB6AA8)
1. **Top gate:** `test byte[0x114],1; je end`. Plot only REDRAWS when the dirty
   bit is set; it clears it after. **Normally dirty=0** (confirmed live) → Plot
   early-exits to the blit path and just re-blits the cached buffer.
2. **Redraw path (dirty=1 only):** reallocates the internal buffer `[0xdc]` to
   the window rect `[0xa8..0xb4]` size (realloc check at 0x79b117 compares
   buffer W/H to `[0xb0]-[0xa8]`/`[0xb4]-[0xac]`), then draws the bar/circle into
   it via `[0xd8]`(drawContext)`->[0x74]` + the arc helper `0x8d8bc0`, using
   rects = window W/H minus the `[0xe0..0xf4]` field insets.
3. **Blit path (always):** `[0x68]`(dest buffer)`->Blt(src=[0xdc], ...)` using a
   rect at `[0x24..0x30]`; `[eax+0x30]`=cIGZBuffer idx12 GetBufferArea,
   `[ebx+0x74]`=idx29 Blt.

### Live object values (DOBS, natural/un-forced)
```
r24 [0x24..0x30] = (0,0,282,678)     window SIZE at local origin
win [0xa8..0xb4] = (66,682,348,1360) absolute rect (282x678, docked at 66,682)
dst68 [0x68]     = 2400x1600 32bpp   THE FULL SCREEN buffer
srcBuf [0xdc]    = 141x339 32bpp     <-- HALF the window (282x678)
v100 [0x100]=138  dirty[0x114]=0x00  f118=256 f11c=0 f120=0
```
**The cached buffer is 141x339 — exactly half the on-screen window.** So the art
is drawn small and the flyout is a **stretch-blit of a 141x339 buffer onto the
282x678 window** (already a 2x stretch). The apparent "1x" look is inherent to
the stock art's thin bar / small thumbs, magnified by this being a bitmap
stretch rather than real 2x windows like Terraform's sub-buttons.

### LEVERS TRIED — all four member-level writes RULED OUT
| Build | Wrote | Result | Meaning |
|-------|-------|--------|---------|
| v2.7.78 | 6 fields `[0xe0..0xf4]` x2 (persisted, verified) | no change | fields are insets, not size |
| v2.7.79 | window rect `[0xa8..0xb4]` x2, no redraw | no change | on-screen size is NOT this rect |
| v2.7.80 | window rect x2 + fields x2 + **force dirty** | **SHRANK** | redraw realloc'd buffer 141->564, killing the 141->display stretch → art half size |
| v2.7.83 | `r24 [0x24..0x30]` x2 (stuck, verified) | no change | on-screen size is NOT r24 |

**Conclusion:** the on-screen SIZE is neither the window rect, nor r24, nor the
fields. Only forcing a redraw changed the display — and it SHRANK it, by
reallocating the buffer to match the window and thereby destroying the implicit
141→display 2x stretch. The real on-screen size is set by the **parent's
compositing of this child** (the blit dest region on `[0x68]`), which is not in
any member field we can write — it's decided when the parent asks the child to
paint. Position IS reachable (GZWinMoveTo moved the flyout, updating `[0xa8]`),
but SIZE is not.

### 2026-07-27 (cont.) — OFFLINE EMULATOR + src/dst decouple WORKS
Built `tools/flyout-sim/emu_plot.py`: runs the REAL container Plot()
(0x0079B0E0) under the Unicorn CPU emulator with a synthetic object, stubs the
buffer/drawctx vtable calls, and CAPTURES the exact rects Plot feeds each draw.
Renders them to a PNG (`--png`). Reusable for any Mayor-mode painted control.
Requires `pip install unicorn` (capstone+PIL already present).

**Emulator findings (natural 1x -> the 4 container draws):**
```
bar-top cap  dst(229,0,  282,25)   x[229-282]=53w (right-anchored)
bar-spine    dst(229,25, 282,653)  drawn by the ARC helper 0x8d8bc0 (TILES)
bar-bot cap  dst(229,653,282,678)
ring/circle  dst(0,138,  94,200)   x[0-94]=ec wide (LEFT-anchored)
```
At all-fields-x2: ring->188w, bar->106w — the correct 2x target (ring encircles
the 2x button; bar 2x thick). Circle is LEFT-anchored (x[0,ec]), bar is
RIGHT-anchored (x[W-e0,W]) - that opposite anchoring is why blind field-doubling
looked wrong.

**Key mechanism (finally cracked):** the element draws are
`[0xdc]->Blt(drawCtx, srcRect, dstRect)` and are 1:1 (src size == dst size).
Doubling the fields doubles BOTH -> the srcRect reads PAST the 1x texture edge =
the tiling MESS. FIX (v2.7.94, IN-GAME CONFIRMED the buffer Blt STRETCHES):
double the fields (2x dst) + hook `[0xdc]`'s Blt to HALVE the srcRect back to 1x
-> the real texture stretches to the 2x dst. **First build ever to put the
disaster thumbnails ON the bar.**

**Remaining (all sim-modelable):**
1. Ring not reaching 2x in-game though the sim says 188 -> debug (src guard? or
   ring is partly the arc). 2. Bar spine "chopped" = the arc helper 0x8d8bc0
   TILES its texture; needs the same stretch treatment (model the arc in the
   emulator first). 3. Thumbnails show 1/4 / unchanged = they are the SEPARATE
   STRIP control (0x0079AA70, vtable 0x00AB6D88), which the container hook never
   touches; needs its own emulation + src/dst decouple. 4. Re-dock once sizes
   settle. Current deployed = v2.7.95 (container decouple + thumb-guard).
   gFieldMask=0x3F, gCtxHalve on [0xdc].

### BLT HOOK RESULT (v2.7.84-88) — the pipeline is fully mapped; no clean lever
Hooked the flyout's screen composite `[0x68]->Blt` (idx29) via a surgical
per-instance vtable swap around the container's Plot call (restored after; no
other window affected). Captured the real args:
```
Blt(src=[0xdc] 141x339 buffer, srcRect a2=(0,0,141,339),
    dstRect a3=(0,0,282,678), clip a4=null)
```
- **a3 (dest rect) is NOT a scale lever.** Set a3 to 846x2034, then it
  accumulated to **2538x6102** (a3 is a persistent, reused rect) — and the screen
  was UNCHANGED. A 2538x6102 dest producing zero change proves the Blt is a
  **1:1 clipped copy**, not a stretch: on-screen art size = the SOURCE buffer
  size (141), positioned at the dest origin, clipped to the dest.
- **Forcing the redraw (v2.7.87, dirty bit only)** reallocated the buffer 141→282
  (the natural window rect) and redrew — but the layout is **WIDTH-DRIVEN**, so
  drawing at 282 wide RE-FLOWED the flyout (scroll bar shoved far right,
  over-tall) instead of magnifying it. User: wrong. **Reverted (v2.7.88).**

### CONCLUSION (2026-07-27): no runtime lever uniformly scales this flyout
Every reachable lever is exhausted: fields (insets), window rect, r24, the Blt
dest rect (1:1 copy ignores it), and forced redraw (re-flows the width-driven
layout). The flyout draws its art into a 141x339 buffer with a width-driven
internal layout and 1:1-copies it to screen. To magnify it uniformly you must
change the game's compiled coordinate MATH (binary-patch Plot at 0x0079B0E0 /
the arc helper 0x8d8bc0 to scale the field-derived positions), or replace the
source textures with 2x art AND fix the fixed source-rect blits (the zoomed-
thumbnail problem). Both are large, fragile efforts. The natural state (v2.7.88)
= the flyout stretched into its 2x-docked window, which is its correct compact
appearance; runtime enlargement beyond that is not available. **Recommend: keep
natural + the (28,130) dock; revisit only via binary Plot patch or 2x-art dat.**

### Remaining paths (both non-trivial)
1. **Hook the blit** — swap `[0x68]`'s vtable (or the container's) around the
   original Plot call so the `Blt` (idx29) dest rect is scaled 2x; the 141x339
   buffer then stretches to 2x the current on-screen area. Surgical (restore the
   vtable after Plot) but the Blt arg layout wasn't fully parseable statically.
2. **SetW/SetH virtuals** (NOT direct member writes) — may notify the parent to
   composite the child at 2x. **v2.7.74 already tried this and it broke** (ring
   vanished, bar stretched, strip flew) because SetW sets dirty → redraw →
   buffer realloc → lost stretch. Would need to also suppress the realloc.
3. **Accept it** — the flyout may already be effectively 2x (buffer stretched to
   the 2x window); its "small" look is the stock art design, unlike Terraform's
   real-window sub-buttons.

---

## 2026-07-26 UPDATE (second model session)

### Version history this session
| Version | Change | Result |
|---------|--------|--------|
| v2.7.73 | Restore button dat-only fix | ✅ Deployed, working |
| v2.7.74 | CAA hook + window SetW/SetH ×2 | ❌ CAA returns 0x06752001 (not rect ptr); window scaling caused regressions (ring gone, bar stretched, strip flew right) |
| v2.7.75 | Revert window scaling, CAA observe-only | ✅ Back to dock-only state |
| v2.7.76 | Member field dump + doubling at 0xE0-0xF4 | ⏳ **UNTESTED** — user handed off before launching SC4 |

### Dead ends confirmed this session
1. **CalcAbsoluteArea hook (slot 89)** — returns `0x06752001` for both container
   and strip, every frame. Same value = NOT a per-window rect pointer. Reads as
   garbage when dereferenced (`L=422416 T=-1340969632...`). **DEAD.**
2. **Window SetW/SetH ×2** — caused regressions: orange ring disappeared
   (probably painted at offset from window bottom/center), bar stretched
   vertically, strip flew right. Painted art does NOT follow window rect.
   **REVERTED.**
3. **Binary-patch Plot() for immediates** — disassembly of both Plot() functions
   (container 0x0079B0E0, strip 0x0079AA70) shows **ZERO hardcoded drawing
   immediates**. All coordinates come from member fields. **NOT POSSIBLE.**

### Key discovery: Plot() reads member fields, not immediates
Disassembled both Plot() functions with capstone
(`%USERPROFILE%\Documents\Qwen\sc4_disasm_disaster_plot.py`):

**Container Plot() (0x0079B0E0):** reads `[this+0xe0..0xf4]` as 6 int32 layout
params, plus `[this+0xa8..0xb4]` (window rect), plus `[this+0xd8]` (draw context
ptr). Calls `[drawCtx+0x74]` (blit virtual) with rects built from those fields.
Also calls `0x8d8bc0` (circle arc helper). No `push imm32` for coordinates.

**Strip Plot() (0x0079AA70):** loops over items from `[this+0xd8]` array.
Reads item size from `[this+0xf4]`, spacing from `[this+0xf8]`, count from
`[this+0xfc]`. Computes blit rects from `[this+0x24]`, `[this+0x28]`,
`[this+0x68]`. No hardcoded drawing immediates.

### Member field values (DMEM dump, container 282×678)
```
Offset  Index   Value   Role in Plot()
0xE0    m[0x38]   53    bar pitch / vertical spacing
0xE4    m[0x39]   25    vertical offset
0xE8    m[0x3A]   12    horizontal offset
0xEC    m[0x3B]   94    circle/bar size param
0xF0    m[0x3C]   62    state offset
0xF4    m[0x3D]    6    small offset
```

v2.7.76 doubles all 6 at hook-install time. **Strip fields NOT yet dumped** —
the strip's Plot() reads from 0xE4-0xFC, similar range but different class.

### What the next model needs to do
1. **TEST v2.7.76** — launch SC4, open disaster tool, check screenshot + log.
   Look for `DMEM DOUBLED` lines. Does the art render at 2×?
2. **If art scales:** recompute dock offY (circle internal offset doubles from
   ~178px to ~356px, so `new_offY ≈ (860 - 356 - tbLiveT) / 2 ≈ 41`). Also
   add DMEM dump + doubling for the strip window.
3. **If art doesn't scale:** the member fields alone aren't enough. Plot() also
   uses the window rect `[this+0xa8..0xb4]` — but v2.7.74 proved scaling the
   window rect causes regressions. The drawing may combine both in a way that
   requires careful analysis of the full disassembly. Consider hooking Plot()
   (slot 88) with a naked asm thunk that doubles the member fields on the stack
   before calling the original, then restores them after.
4. **Strip scaling:** the strip (88×578, vtable 0x00AB6D88) also needs its
   member fields dumped and doubled. Its Plot() at 0x0079AA70 reads from
   `[this+0xe4..0xfc]`. Add a DMEM dump in the strip hook install block
   (search `DHOOK2 installed`).
5. **Clean up:** once disaster is settled, strip DPROBE/DCLASS/DHOOK/DHOOK2/
   DPOS/DCAL/DMEM/CAA/CAA2 diagnostics and the dead buffer-scan helpers
   (ScanRegion, SafeBufProbe, etc.). The vtable swap is stable but it's
   overhead + risk you don't want in a shipping build.

### Known regression to fix later
`0x0A78827A` is in `SCALED_WINDOW_IDS`
(`tools/selective-safe/build_selective_safe.py` ~L102) and its marker recurses
into **all children** — so the disaster thumbnail textures got 2×'d while the
control still blits them at 1× source rects → they render **zoomed in**.
Fixing = remove that id, **regenerate the dats**, and update the **240-entry**
expectation in `_tests/Test-DatIntegrity.ps1`.
