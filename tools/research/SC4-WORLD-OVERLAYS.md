# SC4-WORLD-OVERLAYS — UI-like visuals drawn OUTSIDE the window tree

**What this file is.** The catalog of every system in SimCity 4 Deluxe
1.1.641 that draws something a player reads as *interface* — balloons,
markers, signs, glows, dots, rings, decals — **without owning a `cIGZWin`
window**. These visuals live in the renderer / present path: no window id, no
`.UI` script, no BMPX draw line, invisible to every window census, and (for
the pixel-fixed ones) physically shrinking at our scaled tiers. This file is
the renderer-side sibling of the window-side SDK.

**COMPANION DOC — read the right one.** `SC4-UI-ENGINE.md` is the SDK for
everything the GZWin engine draws (windows, `.UI` scripts, art binding,
widget classes); its §0 defines the boundary from the window side and its
triage rule ends with "it is outside this SDK — write down the negatives and
move on." **This file is where you move on TO.** When a defect crosses the
boundary in the other direction — a visual turns out to BE a window after
all — go back to `SC4-UI-ENGINE.md` (its §0 records two elements wrongly
exiled from the window tree; §2.7 below records the mirror case).

**Evidence rules.** Same as the engine SDK: every non-obvious claim carries a
source — a disassembly VA, a log line, a REGRESSION.md line number `[R:NNNN]`,
or a tool path. Binary facts are from `SimCity 4.exe` **1.1.641.0 Steam (x86,
4GB-patched)**, ImageBase `0x400000`; runtime code rebases every VA by
`(moduleBase − 0x400000)` exactly as `src\CodePatches.cpp` does. Three
provenance grades appear here and are never mixed silently:

- **(byte-verified)** — the bytes were read from the shipped exe and are
  quoted in a durable source (`_tests\REGRESSION.md`, `src\CodePatches.cpp`,
  `tools\effdir\build_mission_bubble_fx.py`, `VERSION-HISTORY.txt`).
- **CARRIED** — stated in the 2026-08-17 session's click-trace working
  notes, which lived in the volatile scratchpad and are gone. The claim is
  recorded because losing it would cost a re-derivation, but it has NOT been
  re-verified against a durable extract. **Re-verify the bytes before
  building anything on a CARRIED value.** A wrong VA is a landmine; the
  #188 hunt stepped on four (§1).
- **UNKNOWN** — a work item, deliberately left blank. An UNKNOWN entry is
  worth more than an invented one.

**Note — the U-Drive-It offer balloon is RESOLVED.** It is a **City
Situation Indicator, category 4**, drawn by
`cSC4DispatchVehicleView::Draw` = **`0x0046D990`** and sized by **nine inline
`.text` immediates** — shipped as `ApplyCsiIndicatorScale` in v3.0.38 and
**USER-CONFIRMED at 3x on 2026-08-18**; the shared dispatch path was
user-confirmed the same day. The account is at the END of this file
("RESOLVED 2026-08-18") and in `tools\research\CITY-SITUATION-INDICATORS.md`.
An earlier attribution (marker strip built by `0x5F5FB0` under occupant
marker type `0xCB79919B`) was refuted on screen; where a passage below still
mentions it, the CSI reading wins.

---

## 1. THE TWO-WORLDS LAW — decide which side owns a defect in ONE observation

Everything a player sees is drawn by exactly one of two systems, and every
instrument in this project is scoped to one side only:

| | **Window world** | **Renderer world** |
|---|---|---|
| drawn by | GZWin tree, panel-sized buffer blits | render/present path onto the 3D view |
| enumerable by | window census, full-depth dumps, `SMALLWIN` | nothing window-side — structurally invisible |
| seen by | `BMPX`/`SEATPROBE` draw hooks | `BUBBLEFX`/`SPPROBE` spawn+draw hooks (§4) |
| sized by | `.UI` `area=`, sweep, static builder | world units, screen-px constants, EFFDIR scale |
| clicked via | routed hit-test (ENGINE §2.2) | renderer ray-pick against drawn geometry (§2.4) |
| our lever | ENGINE §§2–7 (sweep, pins, art, statics) | this doc §§2.1–2.5 (imm patches, spawn hooks, data) |

**The decision tree — one observation each:**

1. **Does a full-depth window dump (or `SMALLWIN` census) show a window at
   the visual's position while it is on screen?** → window world. Close this
   file; use `SC4-UI-ENGINE.md` + `TRIAGE.md`. Honor the census's scope
   limits first (§4) — a capped or depth-limited census that shows nothing is
   not a clean null.
2. **No window, but the visual is CLICKABLE?** → renderer world, and the
   click resolves through the ray-pick path (§2.4). The drawer is one of the
   systems in §2 — and "renderer-drawn" means *unreachable by the window
   tree*, **not unpatchable**: pick radii and quad sizes are constants or
   data, and constants are patchable `[R:11331]`.
3. **No window and not clickable** (shadows, decals, ambient effects) → the
   effects manager (§2.1), or plain world content (props/automata — content,
   not UI). Usually world-anchored and therefore correct at every tier
   without us (§ sizing semantics, below).

**Sizing semantics — the vocabulary this doc uses per system:**

- **world-anchored** — sized in world units; the camera scales it. Correct at
  every tier by construction; *n/a* in the census. (Example: the 16.0f
  one-cell hover quad, §2.4.)
- **pixel-fixed** — a hardcoded screen-px constant; identical px at every
  zoom, resolution and tier — i.e. *physically smaller* on a high-DPI rig.
  These are OUR defect class. (Example: the signpost 44px quad, §2.3.)
- **zoom-ramped** — data-driven per-zoom values (EFFDIR zoom ramps, the
  route-dot per-zoom table). In between: scales with zoom steps but not with
  the tier.

**THE #188 CASE HISTORY — why this file exists.** Roughly 17 launches over
two days aimed byte-true, review-passed patches at the U-Drive-It offer
balloon and missed it, because the balloon's drawer had never been
cataloged: the window tree can't reach it (three census generations,
uncapped-clean `[R:11318]`), the EFFDIR override is structurally inert
(one-shot first-provider load, §2.2), the `mission_selection` effects are
the in-mission glow not the balloon `[R:11486]`, and the signpost quad
builder was proven DORMANT with balloons on screen (`SPQUAD=0`,
`[R:11562]`). A code-built MARKER STRIP (§2.5, scaled v3.0.7) looked like
the answer — its model even predicted the measurement (zoomTable[2]=0.75 ×
64px disc = 48px = the user's measured 45–48px, `[R:11586]`) — **and was
still wrong**; the eyes-on ran and failed. The real drawer is
`cSC4DispatchVehicleView::Draw` **`0x0046D990`** (CSI, category 4), found
by **SUPPRESSION**: killing one function and watching the balloons vanish
identified the drawer in a single launch (law 100), after which a **3x**
exaggeration separated the two overlapping quads that 1.5x could not (law
101). The standing cure is this catalog: **before aiming at any in-world
visual, find its row in §3; if the owning system reads UNKNOWN, the first
deliverable is the identification, not a patch.** Two grading laws came out
of it: a prediction that matches is NECESSARY, not sufficient — two systems
can size a visual alike; and a row graded DOCUMENTED on a static model is
not documented — only screen- or live-capture-proven attributions earn the
grade.

---

## 2. SYSTEM CATALOG

Each system: WHAT IT DRAWS · MECHANISM · SIZE/SCALE SEMANTICS · OUR COVERAGE
· INSTRUMENT · STATUS.

### 2.1 The Swarm effects manager (`CreateEffectByName` world)

**WHAT IT DRAWS.** Named visual effects spawned into the 3D scene: the UDI
in-mission target glows (`mission_selection_*`, 18 variants incl. `_shrink`
despawns and `_water_` floats), fires/smoke/explosion effects, windmill and
helicopter shadows, zoom-gated grid decals, celebration fireworks — every
"particle-ish" or sprite-ish transient the simulation conjures by name.

**MECHANISM (byte-verified, 2026-08-17 `[R:11339–11417]`,
`src\CodePatches.cpp:4062–4106`).**

- Effects are requested **by name**: name table `0xB09AE0`; the five UDI call
  sites are `0x52C6C1`/`0x52C6B9` (offer), `0x529DA8`/`0x529D9C` (shrink),
  `0x528BC9` (red); the in-mission glow spawns at `0x52C4E0`, sole caller
  `0x52E8AE`, gated on an ACTIVE mission situation `[R:11521]`.
- `CreateEffectByName` = **`0x5939B0`**, `__thiscall` + 2 stack args (name,
  ppOut), result in AL. Stock prologue `83 EC 10 57 8B F9 8B 4C 24 18`.
  Success writes `*ppOut` only at `0x593AB9`; failure paths never write it
  (`CodePatches.cpp:4312`).
- The returned 0x14C-byte **effect instance** carries four transform blocks;
  the 4th is ours: rot 3x3 at `+0xE0`, translation `+0x104`, **scale
  `+0x110`**, flag byte **`+0xDD`** (bit1 = scale≠1, bit2 = rotation present
  — `ReadTransform 0x5DA930`'s convention). Constructor `0x5C0150` writes
  1.0f to `+0x110` (at `0x5C047E`) and 0 to `+0xDD` (at `0x5C0496`); record
  bind `0x5BFF80` resets the block only when the mask byte is already nonzero
  (`0x5C008F`).
- **Activation math `0x5919D0`** tests the flag (`mov dl,[ebp+0xDD]; test
  dl,dl` at `0x591DFE`/`0x591E0A`), copies the child scale to the active
  entry (`0x591D6C` → entry+0x34), multiplies instance scale into EVERY child
  spawn (`fld` at `0x591FDE`, `fmul [esi+0x48]` at `0x591FEA`; direct copy
  `0x592071` when the instance carries no transform), and delivers the
  finished transform to the live render object at `0x592125`
  (`vt+0xC(&transform,…)`).
- **Law:** `SetParameter` has **no scale id** — ids run 0..0x13 only; position-only
  `SetParameter` at `0x52C73F`. The runtime scale lever is the instance
  transform block, nothing else `[R:11415]`.

**SIZE/SCALE SEMANTICS.** Per-child file scale (EFFDIR, §2.2) × instance
transform scale, in **world units** — but individual effects can still read
as screen furniture (the target glow). Zoom ramps (4 floats) + zoomMin/
zoomMax bytes gate visibility per zoom (§2.2 record layout) — zoom-ramped.

**OUR COVERAGE.** `InstallMissionBubbleScale` (v3.0.4, `CodePatches.cpp:4354`)
detours `0x5939B0`; for names prefixed `mission_selection` (exactly the 18;
the exe holds exactly 5 strings with the prefix, all UDI) it writes the tier
factor to `+0x110` and `0x06` to `+0xDD` **after** the original returns, only
on a pristine (ctor-state) instance; refusals log UNCAPPED. Ini:
`MissionBubbleFx` (0 off / 1 log / 2 fix / 3 fix+probe), `MissionBubbleScale`
(<=0 follow tier; >0 literal, clamped to (1,8]). Live; the only spawn
observed so far fired on a CLICK (`mission_selection_red`, `[R:11568]`).
The RED question is ANSWERED: red = the **engaged-target glow**, already
scaled by this hook, so the click halo grows with the balloon `[R:11613]`.
The red-spawn site is recorded both as `0x528BC7` (`[R:11613]`) and
`0x528BC9` (`CodePatches.cpp:4065`) — 2 bytes apart, unadjudicated; re-read
the bytes before patching at either (reference gap G29, `SDK-GAPS.md` §13).
No other effect family is scaled or needs to be (world-anchored).

**INSTRUMENT.** `BUBBLEFX` log lines (§4). Positive control: the
"BUBBLEFX installed" line at startup; per-spawn lines prove consumption.

**STATUS: DOCUMENTED** (mechanism opcode-proven end to end).

### 2.2 The EFFDIR resource + the one-shot first-provider load law

**WHAT IT DRAWS.** Nothing directly — it is the *database* §2.1 executes:
effect definitions, child references, transforms, zoom ramps.

**MECHANISM (byte-verified `[R:11354–11417, 11450–11464]`,
`tools\effdir\build_mission_bubble_fx.py` header).**

- Resource TGI `{0xEA5118B0, 0xEA5118B1, 0x00000001}` in `SimCity_1.dat`,
  1,094,484 bytes decompressed (QFS). Names resolve through a **1,149-entry
  name→index map** (`mission_selection_yellow` = index 0x47B).
- Each named **child reference** is packed as: `[u32 nameLen][name][u8
  type][u32 flags][9 f32 rot 3x3][3 f32 trans][f32 SCALE][u8 zoomMin][u8
  zoomMax][u16 copies][u16 mult][4 f32 zoom ramps][2 u16 weights][u32
  effectIndex]`. type 1 = model/sprite class (mgr `+0x10C` table). Layout
  proven twice: semantically across all 406 records (windmill_shadow
  translated (19,0,−9); helicopter shadows z−5; zoom-4 grid decals ±0.25 with
  zoom-5 exactly half) AND by parser disassembly (`ReadChild 0x5AB690` /
  `ReadTransform 0x5DA930`; scale read at `0x5DAA2B` → child+0x48).
- **Law — THE LOAD LAW.** The effects manager fetches this resource **ONCE**, at
  GZCOM service Init **`0x594A30`** (one-shot flag mgr `+0x1AC`, app
  startup), via exact-TGI GetResource, and the resolver **`0x97377F`** is
  **FIRST-PROVIDER-IN-LIST-WINS** (`FF 50 4C` DoesEntryExist per segment) —
  no last-wins override semantics, and the fetch precedes/outranks BOTH
  plugin trees. **A plugin override of this TGI is structurally inert from
  both `Documents\Plugins` and `<install>\Plugins`** — proven by two control
  launches carrying an unmissable 3x scale `[R:11433, 11450]`. The data route
  is closed short of editing `SimCity_1.dat` itself, which is not our
  doctrine.
- The **instance≠1 merge loop** (`0x5947EC–0x594888`) is a real add-on
  mechanism but shares the same Init timing; same-name records select by
  key = max(record+4) <= mgr`+0xB90`, where B90 = **graphics detail level**
  (default 5) — an LOD selector, NOT plugin priority `[R:11459]`.

**SIZE/SCALE SEMANTICS.** The per-child SCALE float (13th float; file byte
nameEnd+53) is consumed into every spawn (§2.1 chain). All 406 shipped
records carry scale 1.0. Zoom ramps/min/max gate per-zoom visibility.

**OUR COVERAGE.** None shipped, none possible via data (load law). The
builder `tools\effdir\build_mission_bubble_fx.py` is kept as **format
documentation** — fresh QFS extract per build, frozen 18-name set, FATAL
gates, 72-byte predicted diff — do not redeploy its output as a fix; its
runtime replacement is the §2.1 hook. Decoded extract + manifest:
`tools\research\effdir\`.

**INSTRUMENT.** None live (parse happens once at startup, before our DLL can
see anything useful). The builder's preflight asserts double as an offline
format gate.

**STATUS: DOCUMENTED.**

### 2.3 Signpost occupants (`cSC4SignpostOccupant`) + the route-dot subsystem — the DORMANT TWIN

**WHAT IT DRAWS.** Camera-facing billboard quads raised on a pole above a
world position — **live membership UNKNOWN** (reference gaps G30/G31): the
v3.0.5-era attribution of the police/fire dispatch lollipops to this quad is
static analysis, and the dispatch/emergency markers are now known to be
**other categories of the CSI dispatch-indicator system**
(`cSC4DispatchVehicleView`; CSI is category 4), reaching the **same pin
quad** as the balloon — at `0x0046E852`, `cmp [esi+4],4 ; je 0x46E38E`
sends category 4 down its own branch which REJOINS the common code — seen
scaling correctly with the CSI patch, user-confirmed 2026-08-18. Whether a
separate lollipop visual still draws through this quad is exactly what an
SPTEX kind census answers. This system is the marker-strip system's
**dormant twin** (`[R:11599]`): same billboard idea, zero observed calls in
every capture so far. A sibling sub-visual draws the **8x8 route dots** (the
dotted path line). **NOT the UDI offer balloon** — that was the #188 hunt's
fourth mis-aim (`[R:11562]`), vindicated: the dormant-builder null was a
TRUE null, the balloon was never a signpost.

**MECHANISM (byte-verified `[R:11507–11560]`, `CodePatches.cpp:4108–4130`).**

- Occupant class clsid **`0xAB72FBB3`** (`cSC4SignpostOccupant`).
- **Quad builder `0x5F20A0`** (stock prologue `83 EC 48 53 55`): builds the
  billboard at a **HARDCODED 44.0f SCREEN PIXELS** — `push 44.0f` at
  `0x5F20AF` (`68 00 00 30 42`) into the px→world helper **`0x7F6690`**, with
  `push 150.0f` at `0x5F20BF` (`68 00 00 16 43`) as the pole raise height.
  The signpost's **kind** is at `[this+0x70]`; **kind 4 = mission balloon**
  (per the static trace — but see STATUS).
- **Texture compose `0x5F12D0`** (first draw): background PNG
  `{856DDBAC, AB7E5421, 2BB075B4}` + icon PNG `{856DDBAC, 46A006B0,
  [this+0x1A8]}` composed in **52px cells**, loaded via the STANDARD resource
  path `0x602B70` — so tier art overrides ARE viable here (unlike §2.2), but
  art alone cannot change the quad size (cell layout hardcoded).
  Texture-ensure per draw: `0x5F1610` (prologue `83 EC 10 53 56`).
- **Kinds table: UNKNOWN** beyond kind 4. The full table was read in the
  session's click-trace notes (volatile, gone). Re-deriving it is cheap: one
  `SPTEX` capture in a scene with dispatched units names every live kind
  (§4). Do not guess kind numbers.
- **Route dots**: their own subsystem at **`0x5F7400`** (real enclosing fn —
  `0x5F7400` itself decodes mid-instruction; the enclosing function is
  `0x5F73A0`), drawing 8x8 dots — a different sub-visual from the quad,
  untouched by any patch of ours. The older comment giving this subsystem
  "its own per-zoom table at `0xAA523C`" (`CodePatches.cpp:4124`) is WRONG —
  the sole-consumer proof shows the only reference to that table, at
  `0x5F74AD`, is a **texture-loop END-BOUND compare, not a size read**
  `[R:11596]`; the table belongs to the marker-strip builder (§2.5). How
  route dots ARE sized: dot size = `[this+0x80]` sizeParam (ctor default
  **1.0f** @`0x5F838D`; SetSize `0x5F7B10` = iface `0xAA5680` slot 6,
  clamped (0,8]; serialized, load `0x5F7E50`) × **16.0f** (`.rdata
  0xA8D45C`, read `0x5F78CA` = one cell) × texture aspect — world-derived,
  no literal-size call site exists in the exe (control: all 7
  iid-`0x2B3B7D86` and 42 iid-`0xE9793A65` refs scanned).

**SIZE/SCALE SEMANTICS.** **Pixel-fixed** (44px quad, 150px raise, at every
zoom AND resolution) — the canonical tier-shrink defect class. Route dots:
8x8 px × sizeParam × 16.0f (world-derived).

**OUR COVERAGE.** v3.0.5 `ApplySignpostScale` (`CodePatches.cpp:4131`)
patches both imms × tier factor (66/225px at 1.5x), verify-before-write
both-or-neither, single-span VirtualProtect. **The patch is live and
executing but the builder has never been seen running**: SPPROBE measured
zero calls with balloons on screen and clicked (`SPQUAD=0`, `SPTEX=0`
`[R:11562]`), so the 44→66 write currently executes nowhere — left in place,
harmless `[R:11599]`. Route dots: NOT scaled by anything, by design so far.

**INSTRUMENT.** `SPPROBE` (`MissionBubbleFx=3`): log-only naked hooks on
`0x5F20A0` (logs this, kind, and the imm actually live in the code page) and
`0x5F1610` (kind census per draw). §4 for scope limits.

**STATUS: PARTIAL** — mechanism byte-verified; consumer set (which visuals
are signposts, which kinds exist) unproven live (reference gaps G30/G31).

### 2.4 The renderer pick / hit-test path (how a sprite takes a click)

**WHAT IT "DRAWS".** Nothing — it is the CLICK side of the renderer world,
and the reason none of these visuals need a pick-radius patch: **the
clickable region IS the drawn geometry**, so a size lever on the visual grows
the click target with it `[R:11346–11352]`.

**MECHANISM.**

- The UDI offer control's hit test is a **renderer ray-pick**: `cISC43DRender`
  **vt+0x104, slot 65**, called at `0x4B8A38` (byte-verified;
  `CodePatches.cpp:4082`). No radius constant exists anywhere on the path.
  **For the offer balloon this is NOT the bounding mechanism:** the CSI's
  clickable area is the **icon quad's own `+0xD0`/`+0xD4` rectangle**
  (35×35, halved to ±17.5 by `Draw`), user-confirmed as "only the inner
  glyph is clickable, not the grey around it". Whatever this ray-pick
  serves, it is not what bounds the balloon.
- Pick results are filtered by an **occupant-type whitelist** — `Accept` fn
  **`0x4B8880`**, accepting **5 automata families** (byte-verified count;
  **the five family ids are UNKNOWN** — carried only in the volatile session
  notes, re-derivation = read `0x4B8880`'s compare chain) **plus** the
  signpost occupant accepted at `0x4B8947` (byte-verified,
  VERSION-HISTORY v3.0.5).
- Helper `0x4B8A00` wraps the pick; its sole caller chain is this control's
  **two mouse handlers** — the surgical place for a multi-sample pick detour
  if a visual ever grows without its click following (planned fallback,
  never needed `[R:11390]`).
- **Law:** the `16.0f` imms at `0x4B8B3D`/`0x4B8B42` are the **one-cell hover
  ground-quad in WORLD units** (the cursor cell highlight) — world-anchored,
  correct at every tier. **Never patch them** `[R:11350]`.
- For the balloon, no pick-side change is ever needed: the CSI's click box
  IS the drawn icon rect (`+0xD0`/`+0xD4`), so scaling the icon immediate
  grows the hit box automatically. (The earlier form of this bullet rested
  on the refuted §2.5 marker-strip attribution; the conclusion survives for
  this different reason.)
- CARRIED (unverified): the offer view-input-control's vtable at
  **`0xA901A0`**, and the `cISC43DRender` service pointer slot at
  **`[0xB43DD0]`**. Both from the session click-trace notes only. Re-verify
  before use; recorded so the next hunt starts from an address, not from
  zero. Partial corroboration for the area: shipped code reads the live
  view/zoom object through **`[0xB43DD8]`** (zoom at `+0xC`,
  `CodePatches.cpp:4286` — byte-verified by being in the running DLL). Note
  `0xA901A0` is byte-proven the DEMOLISH control's vtable elsewhere (§3 row
  10) — the "offer view-input control" label collides; re-derive before use.

**SIZE/SCALE SEMANTICS.** n/a (geometry-derived). The hover quad is
world-anchored.

**OUR COVERAGE.** Nothing patched, deliberately: every shipped size lever
(§2.1, §2.3) grows the click target for free via this path.

**INSTRUMENT.** None dedicated. A click's downstream effects are visible in
`BUBBLEFX` (a UDI offer click spawns `mission_selection_red` `[R:11568]`).

**STATUS: PARTIAL** — architecture proven, whitelist membership + control
vtable unverified.

### 2.5 Marker strips — builder `0x5F5FB0` and zoom table `0xAA523C`

**The offer-balloon attribution is REFUTED.** The U-Drive-It offer balloon
is NOT a marker strip — it is the City Situation Indicator of §3 row 1 /
`CITY-SITUATION-INDICATORS.md`. What this section documents is the builder
and table themselves, whose byte facts stand; **what they draw on screen is
UNCONFIRMED** (reference gap G30) — the only visual ever claimed for them
was the balloon, and that claim fell.

**MECHANISM (byte-verified 6/6: table bytes, sole-consumer proof, builder
prologue `[R:11595]`; `CodePatches.cpp:4212–4231`, VERSION-HISTORY v3.0.7).**

- The billboard strip is **CODE-GENERATED** by builder **`0x5F5FB0`** (stock
  prologue `55 8B EC 83 E4 F8`): content icons (24px default) + 8px margins
  + **64px disc**, every pixel dimension multiplied by the **per-zoom float
  table at `.rdata 0xAA523C` = {0.5, 0.75, 1.0, 1.5, 2.0}**
  (`3F000000 3F400000 3F800000 3FC00000 40000000`).
- **Sole consumer proven**: the table is read at `0x5F6067`
  (`fld [ecx*4+0xAA523C]`); the only other `.text` reference, `0x5F74AD`
  inside the route-dot fn, is a texture-loop END-BOUND compare, not a read
  `[R:11596]`. Patching the table therefore reaches this builder's output and
  nothing else.
- CARRIED (session notes only, absent from every durable source): frame
  art = 8x8 FSH tiles at `{7AB50E44, 1ABE787D, 0x8B4A6560–67}`,
  vertex-stretched and therefore resolution-independent (the notes said
  "ten" tiles over an 8-instance range — the count and range disagree;
  re-derive before using either).
- The renderer pick (§2.4) tests the verts this builder writes, so whatever
  it draws would grow its click target with the visual — no pick-side patch
  `[R:11597]`.
- **Dead ends CLOSED during the hunt** `[R:11600]`: no balloon-named
  S3D exists because the CSI geometry is code-built ("marker-post" S3Ds =
  construction props by exemplar name; "balloon" S3Ds = tourist props); the
  TrainSwitch pair at `0x563572` was rail levers `[R:11573]`; the sheet
  `{46a006b0, 094ac89a}` ("mission bubble base" — the name is #60-era
  guesswork) is **32x32 RGBA, 164 of 1024 pixels with alpha > 0, all pure
  white, a hollow anti-aliased RING about 22px across** (centre row
  `.....######.........######......`); flattening the alpha onto a white
  page is what produced the earlier "solid white square" misreading
  `[R:13734]`. It is not the CSI's art (the CSI draws eight 152×38 PNG
  strips). The `[mgr+0xAC4]` offer-population slot (CARRIED) stays recorded
  for the next offer-machinery question.

**SIZE/SCALE SEMANTICS.** **Pixel-dimensioned, zoom-ramped**: fixed px
constants × the per-zoom table — between the two pure classes.

**OUR COVERAGE.** v3.0.7 `ApplyMarkerZoomScale` (`CodePatches.cpp:4233`)
multiplies all 5 table floats by the tier factor (1.5x →
{0.75, 1.125, 1.5, 2.25, 3.0}), verify-before-write against the stock bit
patterns, single VirtualProtect span, "MARKERZOOM table x1.50" log line.
**The eyes-on ran and FAILED (2026-08-17):** the balloons did not move —
they were never this builder's output; the v3.0.23 follow-up moved the
MAYOR-HAT pole balloon instead and was reverted in v3.0.24. The patch stays
shipped because it provably reaches `0x5F5FB0`'s output (§3 row 16: the
route-trace family), and the dispatch markers were later confirmed to scale
through the CSI pin quad instead (§3 row 5).

**INSTRUMENT.** `SPSTRIP` (§4) — the strip-builder hook added to SPPROBE
mode 3, the positive control the signpost hooks lacked.

**STATUS: the builder and table are DOCUMENTED; their on-screen output is
UNCONFIRMED** (reference gap G30). Grading law: a row graded DOCUMENTED on a
static model is not documented — only screen- or live-capture-proven
attributions earn the grade.

### 2.6 The terrain / region bake family (already conquered — window-owned surfaces)

These LOOK like renderer work (they paint the world) but are **window-owned
bakes**: a window class owns a surface, bakes terrain/data into it, and blits
panel-sized. They are documented elsewhere; listed here so the census can
cite them instead of re-opening them.

| system | doc | status |
|---|---|---|
| dock/dashboard minimap terrain bake (power-of-two blit law, 5-blitter jump table, x8 hole) | `SC4-UI-ENGINE.md` §2.4; #121 zoom-cliff fix `[R:4985]` (`ApplyMiniMapX8Bake`, 15 bytes in-memory) | CLOSED, user-confirmed |
| Data Views map (terrain base + unbounded cell overlay; alpha-blend birth order) | `[R:4985–5100]` | CLOSED (#121) |
| region screen (city tiles, bubbles, zoom rebuild) | `tools\research\REGION-SCREEN.md` (197 fns); #131 closed `[R:5748]`, #132 fixed by REBUILDING not resizing `[R:5863]` | CLOSED |
| disaster-flyout ring sprite (screen-space sprite over the UI; seat-scaling law) | `[R:5198–5242]`, `UiSpike.cpp:1849–1869` | 2x/3x user-confirmed; 1.5x not eyes-on (#123) |
| WarriorUI terraform ring (third-party flyout scripts + ring art, load-order collision) | `[R:3883]`, `UPSTREAM-WARRIOR-REPORT.md` | shipped v2.43.0 |

### 2.7 THE BOUNDARY CASE — the during-mission map marker window `0x48E945B4`

**Window-side but world-anchored** — kept here because it is the standing
counter-example to "in-world ⇒ not a window", and because #188's balloon was
initially mistaken for it.

- A **code-created GZWinBMP** (vtable `0x00ADF6A0`), parented straight to the
  3D view under NO listed root, **TRANSIENT** (present one sample, absent
  0.5s later) — which is why every static census missed it for weeks
  `[R:1898–1938]` (#60).
- **BORN at its bound art's size**, then swept ×f — so tier art compounded to
  **32f²** on screen (72/128/288) until #186 pinned the art family at a fixed
  96px (= 3× design) for 96f on screen at every tier `[R:11218–11296]`,
  shipped v3.0.3. The bind-time-geometry trap is the #176 LATCH LAW family.
- Art is **code-bound** (pushed beside the window id at `0x4B8314` /
  `0x7AC651`; zero `.UI` refs) `[R:1088]`. The family's base TGI
  `{46a006b0,094ac89a}` is **32x32 RGBA, 164 of 1024 pixels at alpha > 0,
  all pure white — a hollow anti-aliased RING about 22px across** (centre
  row `.....######.........######......`); flattening the alpha onto a
  white page produced an earlier "solid white square" misreading
  `[R:13734]`. The pin is harmless and the "bubble base" NAME is #60-era
  guesswork `[R:11326]`.
- Covered by `kBmpxCityRoots` + the BMPX fit rule (dst follows source,
  reduced to fit — overshoot structurally impossible) `[R:1912–1917]`.

**Decision-tree consequence:** a world-anchored visual that IS a window will
show up in a census **only transiently** — sample while the visual is
actually on screen, or the null is not a null.

---

## 3. THE GAP CENSUS — every in-world UI-like visual a player can SEE

Columns: **owning system** (§2 ref or UNKNOWN) · **tier scaling** (correct /
broken / untested / n-a) · **doc** (DOCUMENTED / PARTIAL / UNKNOWN).
UNKNOWN rows are the backlog this file exists to expose. The table was
walked from the game's feature surface, not from a code enumeration — treat
it like the SC4 archive inventory: **discover, don't trust the list**; add
rows the moment a new in-world visual is reported.

| # | visual (player's words) | owning system | tier scaling | doc |
|---|---|---|---|---|
| 1 | **UDI offer balloon** (blue disc + glyph, idle mayor view) | **CITY SITUATION INDICATOR, category 4** of the dispatch-indicator system: drawn by `cSC4DispatchVehicleView::Draw` **`0x0046D990`**, keyed on the AUTOMATON (QI iid `0xA9B40F05`), identified by SUPPRESSION on screen. **TWO quads**, both sized by **inline `.text` immediates**: icon + **click box** 35×35 (`mov eax,0x420C0000` at `0x0046CC47`, imm at `0x0046CC48`, stored to record `+0xD0`/`+0xD4`, halved to ±17.5 by `Draw`) and pin/backing 64×64 (eight ±32.0f at `0x0046EABD..0x0046EB6F`). Art = eight 152×38 PNG strips (type `0x856DDBAC`), each present TWICE, in groups `0x46A006B0` (drawn) and `0x1ABE787D`. Full write-up: `tools\research\CITY-SITUATION-INDICATORS.md`; summary at the end of this file. (The earlier marker-strip attribution, v3.0.7, was refuted on screen; every ELIMINATION in that hunt stands — signpost quad, composer cells, effect-instance scale, windows, EFFDIR overrides, the `0xE4FDA3D4`/`0x90E00D` "per-frame draw" lead (that iid is `cIGZSerializable`; the caller is `GetClassObject`, i.e. save + object creation), and the marker per-object-size suspect.) | **CLOSED — `ApplyCsiIndicatorScale`, shipped v3.0.38; USER-CONFIRMED at 3x, 3840×2160, 2026-08-18.** | **DOCUMENTED** (screen-proven) |
| 2 | UDI during-mission map marker (edge bubble) | window `0x48E945B4` (§2.7) | correct (fixed-96, v3.0.3) | DOCUMENTED |
| 3 | UDI in-mission target glow (`mission_selection_*`, incl. the red engaged-target click halo `[R:11613]`) | effects manager (§2.1) | scaled v3.0.4 | DOCUMENTED |
| 4 | UDI route dots (dotted path) | signpost-occupant module (row 16). Note: `0x5F7400` is a PHANTOM VA — it decodes mid-instruction; the real enclosing fn is `0x5F73A0`. **Sizing FOUND:** dot size = `[this+0x80]` sizeParam (ctor default **1.0f** @`0x5F838D`; SetSize `0x5F7B10` = iface `0xAA5680` slot 6, clamped (0,8]; serialized, load `0x5F7E50`) × **16.0f** (`.rdata 0xA8D45C`, read `0x5F78CA` = one cell) × texture aspect. No literal-size call site exists in the exe (control: all 7 iid-`0x2B3B7D86` and 42 iid-`0xE9793A65` refs scanned) | world-derived ⇒ n-a | PARTIAL |
| 5 | police/fire dispatch markers | **`cSC4DispatchVehicleView` — the dispatch-indicator system** (full write-up `tools\research\CITY-SITUATION-INDICATORS.md` §1). These markers are the OTHER categories of the same drawer whose **category 4** is row 1's UDI offer balloon (category test `cmp ecx, 4` @`0x0046DD6C`); `cSC4DispatchVehicleView::Draw` = **`0x0046D990`**. Byte-proof they reach the same pin quad: the eight ±32.0f inline immediates `0x0046EABD..0x0046EB6F` are **NOT category-guarded** — `cmp [esi+4],4 ; je 0x46E38E` @`0x0046E852` sends CSI down its own branch which **rejoins the common code** `[R:13970–13984]`. (The earlier "marker strips, shared builder `0x5F5FB0`" attribution rested on the refuted balloon premise and is void; the v3.0.5 signpost-lollipop attribution stays superseded either way, §2.3.) Whether MARKERZOOM (`0xAA523C`) ALSO reaches these markers is untested (§2.5 asserts row 16 does; nothing screen-side has tested the dispatch markers) | pin quad co-scaled by **`ApplyCsiIndicatorScale`** (v3.0.38, `src\CodePatches.cpp:4352`, shared uncategorised path) — **USER-CONFIRMED 2026-08-18 at 1.5x**: a dispatch marker was observed and renders correctly `[R:13979]` | PARTIAL |
| 6 | one-cell cursor hover quad (ground highlight) | UDI control hover quad (§2.4, 16.0f world) | n-a (world-anchored) — **never patch** | DOCUMENTED |
| 7 | zoom-gated grid decals (zone/cell grid at zoom 4/5) | effects manager records (§2.2) | n-a (world-anchored, zoom-ramped) | PARTIAL |
| 8 | orange/green guidance arrows (UDI drive mode) | **UDI DRIVING view-input control** singleton `.bss [0xB21D74]` — arrow drawer at owner+0x9C (ctor `0x5649D0`, vt `0xA9D974`/`0xA9D95C`), one-shot texture init **`0x5633C0`** holds the ONLY refs to all six sheets (`0x563587`–`0x563631`), registered via `[vt+0x80](drawer,5,0x3E8)` @`0x565D98`. Art re-located durably: six 128×128 FSH `{7AB50E44,1ABE787D,0x6BE09921–26}` — orange 21/23/25, green 22/24/26 (note: "bubblefsh" was volatile shorthand; that literal string exists in NO archive — 9-archive raw+QFS scan, control: same scanner found `4bb0ecf3_driving_bubble`). Same loader owns the TrainSwitch S3D pair [R:11573]. Notes: `overlays\row-08-guidance-arrows.md` | n-a (world units: 8.0/16.0 template `0x56340E`–`0x563481`; never calls px→world `0x7F6690`, control: signpost builder does) | PARTIAL |
| 9 | disaster-flyout ring sprite | screen-space sprite, seat-scaled (§2.6) | correct 2x/3x; 1.5x not eyes-on (#123) | DOCUMENTED |
| 10 | building/lot selection glow (query & demolish hover) | **Occupant HIGHLIGHT FLAG** — `cISC4Occupant::SetHighlight(mode,sendNow)` at vt+0x44 (`cISC4Occupant.h:57-58`); the renderer tints the occupant's OWN model, so there is no separate visual. Query tool (clsid `0xC7AF928E`) sets mode **7** @`0x4CBF9D` (saves old at `[this+0x40]`, restores `0x4CBF65`); Demolish (`0x46DDB5F1`) sets **5** @`0x4B99F6`; mayor-default control sets 5 @`0x4DB34A`, clears @`0x4DAD7E` and spawns one `local_tile_outline` effect @`0x4DA77A`. Change posts `kSC4MessageOccupantHighlightChange` `0xA2D1C5B9` (`0x80D600`). Note: vtable `0xA901A0` is byte-proven the DEMOLISH control's — §2.4's "offer view-input control" label collides; re-derive before use | n-a (the tint covers exactly the model) | PARTIAL |
| 11 | coverage-radius circle while placing civic buildings | **Effects manager (§2.1)** — named effect `PlopMode_<Family>_{Plop,Inactive,Existing}` (Police/Fire/Health/Education) via CreateEffectByName; drawable = EFFDIR children `<family>_coverage_circle_{existing,inactive,plop_collapse,plop_existing}_{normal,invert}` (type-1 ground-projected decal) | n-a (world-anchored decal) | PARTIAL |
| 12 | plop direction arrow on a held lot | **Effects manager (§2.1) + EFFDIR (§2.2)** — named effect `Lot_Direction_Arrow`, spawned by the Lot Plop tool's preview refresh; zoom-gated to close zooms by three per-zoom child copies. NOT an S3D prop (control: `s3d-name-sweep.txt` has 1,957 rows, zero arrow/direction/compass names) | n-a (world-anchored, zoom-ramped) | PARTIAL |
| 13 | zone drag rectangle + zone color decals | **Lot-display CELL-QUAD BUILDER** (renderer world, code-generated — not effects, not a window): per-lot quads built by `0x6CC970` (vt slot 43 = +0xAC of vtable `0xAB1B98`; QI `0x6C3B80`) | n-a — world-anchoring now DERIVED from the builder, no longer "by observation" | PARTIAL |
| 14 | god-mode terraform brush ring (in-world cursor circle) | **Effects manager (§2.1) — the cursor/brushEffect family, EFFDIR-defined (§2.2)**: named terrain-decal effects `mountain_tool_active` / `valley_tool_active` / `level_tool_active` / `smooth_tool_active` (+`_inactive` twins), each a parent with `_normal`/`_invert` decal children; `mayorlandscape_tool_*` = the mayor-mode landscape brush. Distinct from the WarriorUI terraform ring and the disaster-flyout ring sprite | n-a (world-anchored decal) | PARTIAL |
| 15 | neighbor-connection arrows at city edges | **THE MARKER-OCCUPANT FAMILY (§2.5) — and the family's Rosetta stone.** Exemplar **`UI8x1x3_ConnectArrow_29F1` {0x6534284A, 0xC977C536, 0x29F10000}** carrying **OccupantSize {8,3,1} m** at exemplar bytes 0x58/0x5C/0x60, read by the marker factory via property **`0x27812810` @`0x4A25D3`**; binds its own S3D `{0x5AD0E817,0xBADB57F1,0x29F10000}`; created by `0x6D4860` (push `0x29F10000` @`0x6D4A66`, +15.5f nudge `.rdata 0xAB1CA8`). **The name encodes the size.** (The 2026-08-17 extrapolation that row 1's balloon size is exemplar data of this shape is void: row 1's size is NINE inline `imm32` floats inside `.text` — see row 1. The `OccupantSize`/exemplar finding stands FOR THIS ROW.) | n-a (world units, no px imm, no zoom table on the path) | PARTIAL |
| 16 | traffic/commute route overlay (query route trace) | **Signpost-occupant module** — GZCOM clsid `0xAB72FBB3`, ONE 0x590-byte class (ctor `0x5F5510`); no separate route-dot subsystem exists. **Sizing:** quad px = per-item pixel size (item vt+0x14, read `0x5F69CB`) → px→world `0x7F6690` on live view `[0xB43DD8]` (call `0x5F69E8`) → × **`0xAA523C[zoom]`** (`fmul` `0x5F69ED`; table read `fld [ecx*4+0xAA523C]` @`0x5F6064`). ⇒ our shipped MARKERZOOM patch DOES scale this family (and rows 4/5), just never row 1 | pixel-derived ⇒ SHOULD scale; co-scaled by MARKERZOOM since v3.0.7 | PARTIAL |
| 17 | in-world lot signs (casino/highway/user signs) | S3D lot props (see `s3d-name-sweep.txt`) — world objects, not UI | n-a | DOCUMENTED |
| 18 | ambient shadows (windmill, helicopter) | effects manager child transforms (§2.2) | n-a (world-anchored) | DOCUMENTED |
| 19 | news zeppelin / blimp | automaton (world object) | n-a | DOCUMENTED |
| 20 | pause/alert screen border | window `cSC4WinAlertBorder` id `0x6A5E44B6` (ENGINE §0 — was wrongly exiled from the window world) | correct (v2.37.2) | DOCUMENTED |
| 21 | minimap / Data Views / region bakes | window-owned surfaces (§2.6) | correct | DOCUMENTED |
| 22 | fireworks / celebration effects | effects manager (§2.1) | n-a | DOCUMENTED |

**Census tally: 22 rows · 0 UNKNOWN owning-system rows.** Row 1's owner is
the CSI drawer `0x0046D990`, and row 1 is the first row in this table to
earn **DOCUMENTED** the way the grading law demands: identified by
SUPPRESSION on screen, then user-confirmed at 3x after the fix shipped
(v3.0.38). Row 5's drawer is settled the same way, but its cell is
deliberately still PARTIAL — whether MARKERZOOM (`0xAA523C`) ALSO reaches
those markers has never been tested on screen. Rows 11/13/14/16 were all
DERIVED from the owning code or data, not presumed; rows 8 and 10–16 have
never been looked at by anyone outside this pass.

**Law 99, minted here:** every sweep that reported "the constant is inert"
or "no size data exists" searched `.rdata`, while both of row 1's levers
were immediates inside instructions. If a sweep did not scan `.text`
immediates, it did not look. (The 2026-08-17 extrapolation that row 1's
size was exemplar data of row 15's shape was wrong in exactly this way.)
Grading law: a row graded DOCUMENTED on a static model is not documented —
only screen- or live-capture-proven attributions earn the grade.

---

## 4. INSTRUMENTS — what can SEE this side, and each one's scope limit (law 42)

A gate is only as honest as its scope. Every probe below states what it
CANNOT see; a null from any of them without its positive control is not
evidence.

| instrument | what it sees | positive control | SCOPE LIMIT |
|---|---|---|---|
| **BUBBLEFX** (`CodePatches.cpp:4305`, ini `MissionBubbleFx>=1`) | every successful `CreateEffectByName` whose name starts `mission_selection`; pre-state of the instance; whether we scaled it | "BUBBLEFX installed on CreateEffectByName" at startup; one line per spawn | name-filtered — sees NO other effect names (widen the filter to census the effect world); routine lines capped at 12/session (refusals uncapped); sees nothing spawned by other routes |
| **SPPROBE** = SPQUAD + SPTEX (`CodePatches.cpp:4189`, ini `MissionBubbleFx=3`) | every signpost quad build (this, kind, LIVE imm from the code page) and every texture-ensure (kind census) | "SPPROBE armed" line | only these two functions — a visual drawn by ANY other builder is invisible (proved twice: zero calls while balloons drew via §2.5); log lines capped at 24 each (counters uncapped); dev-mode only, do not ship armed |
| **SPSTRIP** (`CodePatches.cpp:4276`, rides SPPROBE mode 3, v3.0.7) | every marker-strip build at `0x5F5FB0`: this, current zoom, and the LIVE `0xAA523C` table value for that zoom — the positive control the signpost hooks lacked | "MARKERZOOM table x1.50" at install + SPSTRIP `table=1.125` at zoom 2 on next launch `[R:11608]` | only builder `0x5F5FB0`; log cap 16 (counter uncapped); zoom read depends on the view object at `[0xB43DD8]` being non-null (logs zoom=0xFFFFFFFF/table=0 otherwise — that is a scope artifact, not a measurement) |
| **SMALLWIN** census (`UiSpike.cpp:12454`, default OFF) | every VISIBLE <=80px window under the 3D view, every ~2s | the armed line, printed per run | **depth-3 walk, panel subtrees excluded, 200-line budget** — d2's 24-cap truncated on panel furniture and silently hid the answer `[R:11321]`; a census cap is a silent scope limit. WINDOW WORLD ONLY: proves "not a window", never "what it is" |
| **BMPX / SEATPROBE** draw hooks (ENGINE §7, `UiSpike.cpp`) | every GZWinBMP draw under a **listed root** (`kBmpxCityRoots`) | the per-draw `img WxH win WxH -> dst` line | root-LIST scoped — an unlisted root hooks nothing (#60 was exactly this `[R:1898]`); a root that IS the BMP hooks silently on older builds `[R:1931]`. WINDOW WORLD ONLY |
| effdir extract + builder gates (`tools\effdir\`, `tools\research\effdir\`) | the EFFDIR bytes: record layout, name map, scale fields | frozen-set FATAL both directions; 72-byte predicted diff | OFFLINE — proves what the file says, never what the engine consumed (§2.2 load law: the engine may be reading a copy that is not yours) |
| `s3d-name-sweep.txt` (§2.5 dead-ends) | every named S3D across the nine archives | 1,957 rows present | names only — an unnamed or code-composed drawable is invisible (the balloon was EXACTLY this: geometry code-built, no S3D to find `[R:11600]`); remember the archive count is DISCOVERED (nine), never listed |

**The instrument lesson:** every future lever on this side ships with its own
positive-control probe in the same build — v3.0.7 shipped SPSTRIP with the
MARKERZOOM lever, and v3.0.38's CSI fix was identified by a suppression probe
on `0x0046D990` plus a 3x exaggeration to separate two overlapping quads.
(The SPSTRIP-era identification itself did NOT stick — §2.5 — which is why
the probe-with-lever pattern is necessary but never sufficient.) Two scope
limits learned the hard way: **(a)** none of these probes can see an
**inline `.text` immediate** — every "constant is inert" verdict here was a
filtered null (law 99); **(b)** a research probe is not free — SPPROBE mode
3's `SpGetterLog` crashed the game on an unguarded speculative deref, and a
dev-only level must be returned to its default when the investigation ends
`[R:13680]`.

---

## Reference questions — the ones the census says are worth the most

(The first edition's #1 — "what draws the offer balloon?" — is answered:
CSI category 4, `cSC4DispatchVehicleView::Draw` `0x0046D990`, end of this
file. The marker-strip answer offered on 2026-08-17 was wrong; the hunt ran
~17 launches over two days before suppression settled it.)

1. **One live capture in a scene with dispatched units** (census rows 4–5;
   §§2.3, 2.5; reference gaps G30/G31). It adjudicates: SPTEX naming
   whatever kinds the dormant signpost quad still owns (rebuilding the lost
   kinds table for free), what draws through `0x5F5FB0` at all, and the fate
   of the v3.0.5 44px patch — promote it or retire it on measurement. The
   dispatch markers themselves are settled (§3 row 5: CSI pin quad, confirmed
   at 1.5x); the capture is worth MORE now, because `0x5F5FB0` and the
   signpost quad both ended the hunt with **no confirmed on-screen consumer
   at all**.
2. **The pick whitelist's five automata families** (§2.4, `0x4B8880`;
   reference gap G32). Reading one compare chain turns "can the player click
   it?" into a table lookup for every future in-world visual — and settles
   which census rows can even take a click, which halves the space every
   future hunt has to search.
3. **Are there sibling per-zoom tables in `.rdata`?** The marker-strip
   discovery hands us an idiom: pixel constants × a 5-float zoom ramp at a
   `.rdata` table with one consumer (`0xAA523C`/`0x5F6067`). A one-pass
   sweep for {0.5, 0.75, 1.0, 1.5, 2.0}-shaped float runs (and near
   variants) could pre-locate the size levers for several census rows (8,
   10–16).

*Created 2026-08-17 from the #188 session (`_tests\REGRESSION.md:11318–11614`,
`src\CodePatches.cpp:4062–4460`, v3.0.2–v3.0.7); marker-strip update folded
in the same day (`[R:11586]`). New in-world facts go HERE the same session
they are measured (METHOD.md law: the docs are the SDK); window-side facts go
to `SC4-UI-ENGINE.md`.*

---

## RESOLVED 2026-08-18 — the U-Drive-It offer balloon (City Situation Indicator)

**Full write-up: `tools/research/CITY-SITUATION-INDICATORS.md`.** Summary for
this census, because several rows above chase it under wrong names:

The balloon is **CSI, category 4 of the dispatch-indicator system**, drawn by
`cSC4DispatchVehicleView::Draw` = **0x0046D990** and keyed on the AUTOMATON
(QI iid 0xA9B40F05), which is why it tracks a moving vehicle. Identified by
SUPPRESSION — killing that one function made the balloons vanish on screen.

It is **TWO quads**, and every earlier attempt here assumed one:

* pin / backing 64x64 — eight ±32.0f INLINE immediates at 0x0046EABD..0x0046EB6F
* icon + **CLICK BOX** 35x35 — `mov eax,0x420C0000` at 0x0046CC47 (imm at
  0x0046CC48), stored to the record's `+0xD0`/`+0xD4`, halved to ±17.5 by Draw

Art: 8 PNG strips (type 0x856DDBAC), 152x38 = four 38x38 states, each present
**twice** in groups 0x46A006B0 (drawn) and 0x1ABE787D.

### Settled leads recorded under wrong names

* The three "wrong name" leads are confirmed wrong and stay recorded as
  such: `mission_selection` is the in-mission ground glow,
  `aircraftindicate` is a landing ring, `Tag1x1x3_Helicopter` is a helipad
  prop. **None is the balloon.** Names describe the owning subsystem, not
  the visual.
* The signpost quad builder being DORMANT with balloons on screen was a TRUE
  null, correctly recorded — the balloon was never a signpost.
* The offer control's hit test as a renderer ray-pick does not bound the
  CSI: the clickable area is the icon quad's own `+0xD0`/`+0xD4` rectangle,
  user-confirmed ("only the inner glyph is clickable, not the grey around
  it").
* The marker-strip attribution (§2.5: occupant marker `0xCB79919B`, builder
  `0x5F5FB0`) is refuted for the balloon; the builder's own byte facts
  stand, and its eyes-on ran and failed (2026-08-17; the v3.0.23 follow-up
  moved the mayor-hat pole balloon and was reverted in v3.0.24).
* The 1x bubble art `{46a006b0,094ac89a}` is a hollow anti-aliased ring
  (32x32 RGBA, 164 of 1024 pixels with alpha > 0, all pure white, ~22px
  across `[R:13734]`) — not "a solid white 32x32" — and it is not the CSI's
  art.

### Status of this identification

**Shipped:** `ApplyCsiIndicatorScale` (`src/CodePatches.cpp`), mode >= 2,
both-or-neither over all nine immediates, tier-general — **v3.0.38**. Art
generated at 1.5x/2x/3x and wired into `Deploy-OnGameClose.ps1`, so the dist
bundle picks it up from the manifest.

**Screen-proven:** the balloon **USER-CONFIRMED at 3x, 3840×2160, 2026-08-18**
("disc, glyph, pin and pole all proportional"). The pin quad's shared path —
the eight ±32 immediates are NOT category-guarded — shipped as a named
UNVERIFIED blast radius and was **user-confirmed the same day**: a dispatch
marker was observed rendering correctly, so the contingency of splitting
`kCsiQuad` is not needed and stays unbuilt.

**STATUS: DOCUMENTED** — and it earns the grade under this file's own law:
identified by suppression on screen, then confirmed on screen after the fix.

### Why the census missed it for so long

Every sweep that reported "no art involved" or "constant is inert" was honest
but **filtered**: the art check covered only one of the two resource groups,
and every constant sweep searched `.rdata` while both size levers are `imm32`
values inside `.text` instructions. See laws 99-105.
