# Row 4 — UDI route dots: THE SIZE SOURCE (byte-walk, 2026-08-17)

> **CURRENT GRADE: CLOSED** — confirmed on screen 2026-08-31 - it is NOT a separate visual.
>
> ⛔ **The dated header below is the ORIGINAL session's grade and is
> superseded.** It is kept rather than rewritten because this project
> annotates history instead of editing it — but the front door
> (`docs/DECOMPILATION-STATUS.md`) grade-scans the top of this file, so
> the line above is the one that counts. See the MEASURED section at the
> end of this file for what changed and how it was proven.

**Task scope.** Row 4 of `SC4-WORLD-OVERLAYS.md` §3: the sizing of the UDI
route dots was UNKNOWN after the `0xAA523C` supersession. This file is the
byte-walk from the doc's claimed subsystem VA (`0x5F7400`) to the actual size
math. Attribution proper is row 16's job; everything here is **PARTIAL
(static)** by the doc's evidence law — no live capture was run (rules: never
launch the game). Every VA below was read from the shipped exe this session
with `tools\research\disasm_at.py` (1.1.641 Steam x86, ImageBase 0x400000).

## 0. The headline

**`0x5F7400` is not a function.** It decodes mid-instruction. The enclosing
function starts at **`0x5F73A0`** (prologue `83 EC 0C 56 8B F1`) and is the
**INIT of the marker-STRIP view class (class A)** — the same class that owns
builder `0x5F5FB0` and the `0xAA523C` zoom table. Inside it:

- `0x5F7418`: `push 0xAB72FBB3` (cSC4SignpostOccupant clsid, via vt+0x20).
- `0x5F7455`: 14-arg ctor call `0x7D2B50` building the renderer object at
  `[this+0x574]` (init frame; ctor frame +0xC higher).
- `0x5F7460–0x5F74B1`: **the texture preload loop** — iterates the
  **10-dword instance table at `.rdata 0xAA5214`**, loading TGI
  `{0x7AB50E44, 0x1ABE787D, <inst>}` into `[this+0x540..0x567]`.
  Table contents (byte-read): `8B4A6560,61,62,63,64,65,64,65,66,67` —
  **10 slots, 8 distinct instances 0x8B4A6560–67** (slots 6,7 repeat 64,65).
  This RESOLVES §2.5's CARRIED "ten tiles over an 8-instance range"
  discrepancy: both numbers were right.
- `0x5F74AB`: `cmp ebx, 0xAA523C` — the loop's END BOUND (the zoom table
  starts where the instance table ends). Confirms `[R:11596]`: not a size
  read.

So the "route-dot subsystem at 0x5F7400" CARRIED claim points at the strip
class's init, whose only 8x8 content is the **frame art preload** (the 8x8
FSH tiles of §2.5). The census's "8x8 px sprites" wording is explained twice
over (see §2 below) and by neither reading is it a screen-px quad size.

## 1. The module has TWO marker view classes, not one

| | class A (strip) | class B (sprite/dot) |
|---|---|---|
| ctor | `0x5F5510` (vt `0xAA5268`/`0xAA5478`…) | `0x5F8300` (vt `0xAA54B4`/`0xAA5680`…) |
| init/rebuild | `0x5F73A0` | `0x5F7810` |
| registers | clsid `0xAB72FBB3` (`0x5F7418`) | occupant marker type `0xCB79919B` (`0x5F7F58`, in view-attach `0x5F7F40`) |
| geometry | code-built strip `0x5F5FB0`, px consts × `0xAA523C` | ONE billboard quad per instance ×2 sprite lists |
| messages | `0xA6B79602`, `0x6CDB65B` | those + `0x26D31EC1` (`0x5F771F`) |
| object size | large (0x580+) | **0xBC bytes — pool of 87** (allocator `0x5F7680`: 0x57 nodes × 0xBC) |
| dtor/shutdown | `0x5F5E20` | `0x5F76C0` |

Class B is the **dot-shaped** drawer: each instance draws one small billboard
at a world position, added to TWO sprite lists (normal + occluded/ghost
pass; blink variants use lists 2/3 — attach helper `0x5F7C80` picks list
index `blink?2:0` and `blink?3:1` from the sprite-list service
`[0xB43CF4]`→vt+0x108, getter `0x602160`). An 87-node pool for 0xBC-byte
instances is exactly a dotted-path population, and the mayor hover handler
`0x4D7950` QIs marker occupants for **iid `0x2B3B7D86`** — class B's
interface (QI `0x5F7650` accepts exactly that iid) — pushing 0.5f/0.7f into
**vt+0x28** (`0x5F7C00`, intensity — the `[R:11705]` 0.7f highlight),
NOT into SetSize.

## 2. THE SIZE SOURCE (class B) — all byte-verified

**Blast radius of a hook on the rebuild — MEASURED 2026-08-30, discharging the
probe plan's stated prerequisite.** This note previously asserted "no vtable
refs, coverage total" without establishing that the *callers* are all class B,
which is the claim a hook that writes `[this+0x80]` actually depends on. Scanned
`.text` for every `E8 rel32` resolving to `0x5F7810`:

| Call site | Returns to | Inside class B (`0x5F7650`–`0x5F8450`) |
|---|---|---|
| `0x5F7AFE` | `0x5F7B03` | yes |
| `0x5F7B3C` | `0x5F7B41` | yes |
| `0x5F7BF4` | `0x5F7BF9` | yes |
| `0x5F7C6C` | `0x5F7C71` | yes |
| `0x5F7D72` | `0x5F7D77` | yes |
| `0x5F805F` | `0x5F8064` | yes |
| `0x5F8259` | `0x5F825E` | yes |

Seven direct callers, seven inside class B, and **zero `.rdata` references** —
so the function is reachable only from class B and never through a vtable. A
detour on it therefore cannot see another class's object, which is what makes
writing the size member unconditionally safe. *Positive control for the
scanner:* the same pass finds the expected caller counts for other functions in
the module, and a target with known vtable entries returns a non-zero `.rdata`
count.

The rebuild `0x5F7810` computes the on-screen size:

```
0x5F7887  [this+0xB0] vt+0xC(&dims)      ; texture GetDims -> w,h ints
0x5F788A  fild w ; fild h ; fdivp        ; aspect = w/h
0x5F78C4  fmul [this+0x80]               ; x sizeParam
0x5F78CA  fmul dword [0xA8D45C]          ; x 16.0f  (.rdata, = ONE CELL in world units)
0x5F78D0  fst  [this+0x90]               ; final sprite size, WORLD UNITS
0x5F78DC  fmul dword [0xA84D2C]          ; x 0.5f -> half-extent
0x5F78EE  [this+0x80] x dword [0xA8E178] ; x 8.0f -> other half-extent
```

- `[this+0x90]` is pushed to the sprite-list **Add** (vt+0xC) at
  `0x5F799C`/`0x5F79EE` for both sprites, AND the same halves build the
  dot's **world-space bounding box** at `[this+0x40..0x54]`
  (`0x5F7952`–`0x5F7985`, ±0.1f z from `0xA8C950`) — the box is added to
  the dot's world position, which pins the units: **WORLD, not screen px.**
- **sizeParam `[this+0x80]`**: ctor default **1.0f** (`0x5F838D–0x5F8392`);
  setter = interface `0xAA5680` **slot 6 = `0x5F7B10`** (also `0xAA5620`
  slot 30, `0xAA5610` slot 34), range-checked `> 0.0f` (`0xA81054`) and
  `<= 8.0f` (`0xA8E178`), rebuild on write. **No call site in the exe
  pushes a literal into it** (scanned all 7 refs to iid `0x2B3B7D86` and all
  42 refs to iid `0xE9793A65` for vt+0x18 with float pushes — the only
  float-push hits were the 0.5f/0.7f intensity writes at
  `0x4D7989`/`0x4D7A3A` into vt+0x28). It is also **serialized** in the
  occupant (save/load pair `0x5F7DB0`/`0x5F7E50`; load reads it at
  `[obj+0x70]`, int-legacy path `0x5F7EBB` fild). So a dot's size is
  exemplar/creation data or the 1.0f default — not code.
- **Default result: aspect × 1.0 × 16.0 = one 16 m cell-ish quad**
  (aspect from the texture dims; see the atlas note below).

**The per-zoom table that superseded `0xAA523C` for THIS class is at
`.data 0xB0A978`** — read at `0x5F7932`:
`fld [ (( [this+0xAC] + zoom*4 ) *4) + 0xB0A978 ]`, zoom = live view object
`[0xB43DD0]`→vt+0x28→`[obj+0x18]` (this read corroborates §2.4's CARRIED
`0xB43DD0` = cISC43DRender service slot). 5 rows (zoom 1–5) × 4 cols
(col = `[this+0xAC]`, ctor default 1, setter `0x5F7D60` = interface slot 9):

```
zoom1: 0.25  0.00  0.125 0.875
zoom2: 0.75  0.00  0.625 0.875
zoom3: 0.75  0.50  0.625 0.375
zoom4: 0.25  0.50  0.125 0.375
zoom5: 0.00  0.00  0.000 0.000
```

Quarter/eighth-step values in [0,1): this is a **texture-atlas coordinate
(per-zoom FRAME select), not a size ramp**. It is pushed as the 4th Add arg
(`0x5F794B`). If the dot atlas is 32 px wide, a 0.25-step cell is **8 px —
the census's "8x8" is the atlas CELL, not a screen quad**. (The OTHER 8x8
family — FSH `0x8B4A6560–67` — is class A's strip-frame art; two different
8x8s, one census phrase.)

- **Class B never calls the px→world helper `0x7F6690`** — full-.text scan
  found exactly 18 callers: 4 at `0x46CDxx`, the rest class A
  (`0x5F0FA3–0x5F20C6` signpost, `0x5F607D–0x5F60DE` + `0x5F69E8`,
  `0x5F6AE5`, `0x5F6AFD` strip builder). Positive control for the scan: it
  found the known 44px/150px calls at `0x5F20B6`/`0x5F20C6`.
- The dot texture `[this+0xB0]`: bound by data, not by a hardcoded TGI in
  class B (no TGI push found in `0x5F76C0–0x5F8450`; the strip class's
  hardcoded pair `{856DDBAC,…}` has no class-B analogue). Recoverable live:
  log `[this+0xB0]` in the probe below and query its TGI.

## 3. Other facts nailed in passing

- `0x5F4960` = **500 ms blink timer** (`cmp eax,0x1F4` at `0x5F496E`,
  toggles `[this+0xAD]`), fed by message `0x86AD10EE` delta/1000
  (`mul 0x10624DD3; shr edx,6` = ÷1000 at `0x5F7556`).
- Class A's icon loop sizes strip icons: `fild width; call 0x7F6690;
  fmul [zoom table value]` at `0x5F69CE–0x5F69ED` — px→world × zoom ramp,
  4 verts/icon, 20-byte stride into `[this+0x4BC]`.
- Class-B interface `0xAA5680` slots: 3 `0x5F8400` (returns this+0xC),
  5 `0x5F8410` (forwards `[this+0x6C]` vt+0x34), 6 SetSize `0x5F7B10`,
  7 SetBlink `0x5F8170` (`[this+0x8C]`), 8 SetColor3f `0x5F7B50`
  (`[this+0x9C..A4]`, defaults 255,255,255, eps 1e-4 `0xAA54A0`),
  9 SetFrameCol `0x5F7D60` (`[this+0xAC]`), 10 SetIntensity `0x5F7C00`.
- `0x5F8430` returns type id `0x8B79C707` (class B GetType).
- The `[R:11695]` SPATTACH null (zero `0x5F7C80` calls at city load) does
  NOT eliminate class B for route dots: **no UDI mission was active in that
  capture, so no dots were on screen** — instrument scoped to the wrong
  scene, not a clean null.

## 4. Dead ends (each with its control)

- EFFDIR name scan for route/dot/path families: no route-dot effect exists
  (control: the same scan finds `mission_selection_*` ×18 and
  `tornadoui_dots`). The dots are not effects-manager spawns.
- No BUBBLEALL/route lines in `_tests\captures\*.log` (control: the greps
  return IconSynth/MDRIFT lines, so the logs are readable; BUBBLEALL lines
  simply carry no dot-named spawns — expected, they filter effect names).
- `push 8.0f` sites in the module: only `0x5F609D`/`0x5F60D3` (strip
  margins, class A) — no 8.0f quad constant anywhere in class B; 8.0f
  appears in class B only as the SetSize UPPER CLAMP and the half-extent
  multiplier.

## 5. The one cheapest live probe (spec)

SPATTACH (already shipped, `CodePatches.cpp` v3.0.9, hook `0x5F7C80`,
prologue `53 56 8B F1 8B 86 84 00 00 00` — re-verified this session) is the
right instrument; the missing ingredient was the SCENE. Run:
`MissionBubbleFx=3`, load a city, **accept a U-Drive-It mission and keep the
dotted path on screen**. Expect per dot: one SPATTACH line, return address
`0x5F7F74` / `0x5F8079` / `0x5F8187` / `0x5F826A` (class-B callers of the
attach helper), count ≈ number of visible dots (≤87). Extend the log with
`[this+0x80]` (dot size, expect 1.0f or the exemplar value) and
`[this+0xB0]`→GetTGI (names the dot atlas). Positive control: dots visibly
on screen during the capture; if dots draw and SPATTACH stays 0, class B is
eliminated for row 4 and the dots belong to class A's strip path (already
tier-scaled by MARKERZOOM).

*Written 2026-08-17 by the row-4 sizing agent. Static grade: PARTIAL.*
