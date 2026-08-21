# SC4-WORLD-OVERLAYS — UI-like visuals drawn OUTSIDE the window tree

**What this file is.** The catalog of every system in SimCity 4 Deluxe
1.1.641 that draws something a player reads as *interface* — balloons,
markers, signs, glows, dots, rings, decals — **without owning a `cIGZWin`
window**. These visuals live in the renderer / present path: no window id, no
`.UI` script, no BMPX draw line, invisible to every window census, and (for
the pixel-fixed ones) physically shrinking at scaled tiers. This file is the
renderer-side sibling of the window-side SDK.

**COMPANION DOC — read the right one.** `SC4-UI-ENGINE.md` is the SDK for
everything the GZWin engine draws (windows, `.UI` scripts, art binding,
widget classes); its §0 defines the boundary from the window side and its
triage rule ends with "it is outside this SDK — write down the negatives and
move on." **This file is where you move on TO.** When a defect crosses the
boundary in the other direction — a visual turns out to BE a window after
all — go back to `SC4-UI-ENGINE.md` (its §0 records two elements that belong
to the window tree despite drawing in the world; §2.7 below records the
mirror case).

**Evidence basis.** Binary facts are from `SimCity 4.exe` **1.1.641.0 Steam
(x86, 4GB-patched)**, ImageBase `0x400000`; runtime code rebases every VA by
`(moduleBase − 0x400000)` exactly as `src\CodePatches.cpp` does. A VA quoted
here was read from the shipped exe; a wrong VA is a landmine, so re-read the
bytes at the address before writing to it.

**The U-Drive-It offer balloon** is a **City Situation Indicator, category
4**, drawn by `cSC4DispatchVehicleView::Draw` = **`0x0046D990`** and sized by
**nine inline `.text` immediates**; the fix ships as `ApplyCsiIndicatorScale`.
The account is at the END of this file and in
`tools\research\CITY-SITUATION-INDICATORS.md`.

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
| the lever | ENGINE §§2–7 (sweep, pins, art, statics) | this doc §§2.1–2.5 (imm patches, spawn hooks, data) |

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
   data, and constants are patchable.
3. **No window and not clickable** (shadows, decals, ambient effects) → the
   effects manager (§2.1), or plain world content (props/automata — content,
   not UI). Usually world-anchored and therefore correct at every tier
   without a patch (§ sizing semantics, below).

**Sizing semantics — the vocabulary this doc uses per system:**

- **world-anchored** — sized in world units; the camera scales it. Correct at
  every tier by construction; *n/a* in the census. (Example: the 16.0f
  one-cell hover quad, §2.4.)
- **pixel-fixed** — a hardcoded screen-px constant; identical px at every
  zoom, resolution and tier — i.e. *physically smaller* on a high-DPI rig.
  This is the defect class the catalog targets. (Example: the signpost 44px
  quad, §2.3.)
- **zoom-ramped** — data-driven per-zoom values (EFFDIR zoom ramps, the
  route-dot per-zoom table). In between: scales with zoom steps but not with
  the tier.

**THE CATALOG RULE — why this file exists.** A billboard visual in the 3D
view has no window id to look up, and two unrelated systems can size a visual
so closely that a static model predicts the measured pixel count and is still
naming the wrong drawer. **Before aiming at any in-world visual, find its row
in §3 and patch the system that row names.** Two grading rules follow from
that: a prediction that matches is NECESSARY, not sufficient; and an
attribution built on a static model is not an attribution — only screen- or
live-capture-proven attributions are. The fastest identification method is
**SUPPRESSION**: kill one candidate drawer, watch whether the visual
disappears, and the drawer is named in a single launch. When two quads
overlap, run the probe at **3x**, where their sizes separate, rather than at
1.5x, where they do not.

---

## 2. SYSTEM CATALOG

Each system: WHAT IT DRAWS · MECHANISM · SIZE/SCALE SEMANTICS · SCALING
COVERAGE · INSTRUMENT.

### 2.1 The Swarm effects manager (`CreateEffectByName` world)

**WHAT IT DRAWS.** Named visual effects spawned into the 3D scene: the UDI
in-mission target glows (`mission_selection_*`, 18 variants incl. `_shrink`
despawns and `_water_` floats), fires/smoke/explosion effects, windmill and
helicopter shadows, zoom-gated grid decals, celebration fireworks — every
"particle-ish" or sprite-ish transient the simulation conjures by name.

**MECHANISM** (`src\CodePatches.cpp:4062–4106`).

- Effects are requested **by name**: name table `0xB09AE0`; the five UDI call
  sites are `0x52C6C1`/`0x52C6B9` (offer), `0x529DA8`/`0x529D9C` (shrink),
  `0x528BC9` (red); the in-mission glow spawns at `0x52C4E0`, sole caller
  `0x52E8AE`, gated on an ACTIVE mission situation.
- `CreateEffectByName` = **`0x5939B0`**, `__thiscall` + 2 stack args (name,
  ppOut), result in AL. Stock prologue `83 EC 10 57 8B F9 8B 4C 24 18`.
  Success writes `*ppOut` only at `0x593AB9`; failure paths never write it
  (`CodePatches.cpp:4312`).
- The returned 0x14C-byte **effect instance** carries four transform blocks;
  the 4th is the one to write: rot 3x3 at `+0xE0`, translation `+0x104`,
  **scale `+0x110`**, flag byte **`+0xDD`** (bit1 = scale≠1, bit2 = rotation
  present — `ReadTransform 0x5DA930`'s convention). Constructor `0x5C0150`
  writes 1.0f to `+0x110` (at `0x5C047E`) and 0 to `+0xDD` (at `0x5C0496`);
  record bind `0x5BFF80` resets the block only when the mask byte is already
  nonzero (`0x5C008F`).
- **Activation math `0x5919D0`** tests the flag (`mov dl,[ebp+0xDD]; test
  dl,dl` at `0x591DFE`/`0x591E0A`), copies the child scale to the active
  entry (`0x591D6C` → entry+0x34), multiplies instance scale into EVERY child
  spawn (`fld` at `0x591FDE`, `fmul [esi+0x48]` at `0x591FEA`; direct copy
  `0x592071` when the instance carries no transform), and delivers the
  finished transform to the live render object at `0x592125`
  (`vt+0xC(&transform,…)`).
- **Law:** `SetParameter` has **no scale id** — ids run 0..0x13 only;
  position-only `SetParameter` at `0x52C73F`. The runtime scale lever is the
  instance transform block, nothing else.

**SIZE/SCALE SEMANTICS.** Per-child file scale (EFFDIR, §2.2) × instance
transform scale, in **world units** — but individual effects can still read
as screen furniture (the target glow). Zoom ramps (4 floats) + zoomMin/
zoomMax bytes gate visibility per zoom (§2.2 record layout) — zoom-ramped.

**SCALING COVERAGE.** `InstallMissionBubbleScale` (`CodePatches.cpp:4354`)
detours `0x5939B0`; for names prefixed `mission_selection` (exactly the 18;
the exe holds exactly 5 strings with the prefix, all UDI) it writes the tier
factor to `+0x110` and `0x06` to `+0xDD` **after** the original returns, only
on a pristine (ctor-state) instance; refusals log UNCAPPED. Ini:
`MissionBubbleFx` (0 off / 1 log / 2 fix / 3 fix+probe), `MissionBubbleScale`
(<=0 follow tier; >0 literal, clamped to (1,8]). The `mission_selection_red`
variant is the **engaged-target glow**, spawned on a click and scaled by this
same hook, so the click halo grows with the balloon. No other effect family
is scaled or needs to be (world-anchored).

**INSTRUMENT.** `BUBBLEFX` log lines (§4). Positive control: the
"BUBBLEFX installed" line at startup; per-spawn lines prove consumption.

### 2.2 The EFFDIR resource + the one-shot first-provider load law

**WHAT IT DRAWS.** Nothing directly — it is the *database* §2.1 executes:
effect definitions, child references, transforms, zoom ramps.

**MECHANISM** (`tools\effdir\build_mission_bubble_fx.py` header).

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
- **Law — THE LOAD LAW.** The effects manager fetches this resource **ONCE**,
  at GZCOM service Init **`0x594A30`** (one-shot flag mgr `+0x1AC`, app
  startup), via exact-TGI GetResource, and the resolver **`0x97377F`** is
  **FIRST-PROVIDER-IN-LIST-WINS** (`FF 50 4C` DoesEntryExist per segment) —
  no last-wins override semantics, and the fetch precedes and outranks BOTH
  plugin trees. **A plugin override of this TGI is structurally inert from
  both `Documents\Plugins` and `<install>\Plugins`** — proven by two control
  launches carrying an unmissable 3x scale. The data route is closed short of
  editing `SimCity_1.dat` itself, which is outside this project's doctrine.
- The **instance≠1 merge loop** (`0x5947EC–0x594888`) is a real add-on
  mechanism but shares the same Init timing; same-name records select by
  key = max(record+4) <= mgr`+0xB90`, where B90 = **graphics detail level**
  (default 5) — an LOD selector, NOT plugin priority.

**SIZE/SCALE SEMANTICS.** The per-child SCALE float (13th float; file byte
nameEnd+53) is consumed into every spawn (§2.1 chain). All 406 shipped
records carry scale 1.0. Zoom ramps/min/max gate per-zoom visibility.

**SCALING COVERAGE.** None via data — the load law closes that route. The
builder `tools\effdir\build_mission_bubble_fx.py` is kept as **format
documentation** — fresh QFS extract per build, frozen 18-name set, FATAL
gates, 72-byte predicted diff — do not redeploy its output as a fix; the
runtime replacement is the §2.1 hook. Decoded extract + manifest:
`tools\research\effdir\`.

**INSTRUMENT.** None live: the parse happens once at startup, before the mod
DLL can see anything useful. The builder's preflight asserts double as an
offline format gate.

### 2.3 Signpost occupants (`cSC4SignpostOccupant`) + the route-dot sub-visual

**WHAT IT DRAWS.** Camera-facing billboard quads raised on a pole above a
world position. The dispatch/emergency markers are **other categories of the
CSI dispatch-indicator system** (`cSC4DispatchVehicleView`; CSI is category
4), reaching the **same pin quad** as the balloon — at `0x0046E852`,
`cmp [esi+4],4 ; je 0x46E38E` sends category 4 down its own branch which
REJOINS the common code, so they scale with the CSI patch. An `SPTEX` kind
census (§4) names every kind this signpost quad still draws in a live scene.
A sibling sub-visual draws the **8x8 route dots** (the dotted path line).
**This system is NOT the UDI offer balloon** — the balloon is the CSI of §3
row 1, and the signpost quad builder measures zero calls with balloons on
screen.

**MECHANISM** (`CodePatches.cpp:4108–4130`).

- Occupant class clsid **`0xAB72FBB3`** (`cSC4SignpostOccupant`).
- **Quad builder `0x5F20A0`** (stock prologue `83 EC 48 53 55`): builds the
  billboard at a **HARDCODED 44.0f SCREEN PIXELS** — `push 44.0f` at
  `0x5F20AF` (`68 00 00 30 42`) into the px→world helper **`0x7F6690`**, with
  `push 150.0f` at `0x5F20BF` (`68 00 00 16 43`) as the pole raise height.
  The signpost's **kind** is at `[this+0x70]`; **kind 4 = mission balloon**.
- **Texture compose `0x5F12D0`** (first draw): background PNG
  `{856DDBAC, AB7E5421, 2BB075B4}` + icon PNG `{856DDBAC, 46A006B0,
  [this+0x1A8]}` composed in **52px cells**, loaded via the STANDARD resource
  path `0x602B70` — so tier art overrides ARE viable here (unlike §2.2), but
  art alone cannot change the quad size (cell layout hardcoded).
  Texture-ensure per draw: `0x5F1610` (prologue `83 EC 10 53 56`).
- **Route dots**: their own sub-visual at **`0x5F73A0`** (note `0x5F7400`
  decodes mid-instruction and is not a function start; `0x5F73A0` is the
  enclosing function), drawing 8x8 dots — a different sub-visual from the
  quad, untouched by any patch here, and it does NOT own the per-zoom table
  at `0xAA523C`: the only reference to that table inside this function, at
  `0x5F74AD`, is a **texture-loop END-BOUND compare, not a size read**. The
  table belongs to the marker-strip builder (§2.5). How route dots ARE sized:
  dot size = `[this+0x80]` sizeParam (ctor default **1.0f** @`0x5F838D`;
  SetSize `0x5F7B10` = iface `0xAA5680` slot 6, clamped (0,8]; serialized,
  load `0x5F7E50`) × **16.0f** (`.rdata 0xA8D45C`, read `0x5F78CA` = one
  cell) × texture aspect — world-derived, no literal-size call site exists in
  the exe (control: all 7 iid-`0x2B3B7D86` and 42 iid-`0xE9793A65` refs
  scanned).

**SIZE/SCALE SEMANTICS.** **Pixel-fixed** (44px quad, 150px raise, at every
zoom AND resolution) — the canonical tier-shrink defect class. Route dots:
8x8 px × sizeParam × 16.0f (world-derived).

**SCALING COVERAGE.** `ApplySignpostScale` (`CodePatches.cpp:4131`) patches
both immediates × tier factor (66/225px at 1.5x), verify-before-write
both-or-neither, single-span VirtualProtect. Route dots are world-derived and
take no patch.

**INSTRUMENT.** `SPPROBE` (`MissionBubbleFx=3`): log-only naked hooks on
`0x5F20A0` (logs this, kind, and the immediate actually live in the code
page) and `0x5F1610` (kind census per draw). §4 for scope limits.

### 2.4 The renderer pick / hit-test path (how a sprite takes a click)

**WHAT IT "DRAWS".** Nothing — it is the CLICK side of the renderer world,
and the reason none of these visuals need a pick-radius patch: **the
clickable region IS the drawn geometry**, so a size lever on the visual grows
the click target with it.

**MECHANISM.**

- The UDI offer control's hit test is a **renderer ray-pick**: `cISC43DRender`
  **vt+0x104, slot 65**, called at `0x4B8A38` (`CodePatches.cpp:4082`). No
  radius constant exists anywhere on the path. **For the offer balloon this
  is NOT the bounding mechanism:** the CSI's clickable area is the **icon
  quad's own `+0xD0`/`+0xD4` rectangle** (35×35, halved to ±17.5 by `Draw`) —
  only the inner glyph takes the click, not the grey around it.
- Pick results are filtered by an **occupant-type whitelist** — `Accept` fn
  **`0x4B8880`**, accepting **5 automata families** **plus** the signpost
  occupant accepted at `0x4B8947`. The compare chain at `0x4B8880` names the
  five family ids.
- Helper `0x4B8A00` wraps the pick; its sole caller chain is this control's
  **two mouse handlers** — the surgical place for a multi-sample pick detour
  if a visual ever grows without its click following.
- **Law:** the `16.0f` imms at `0x4B8B3D`/`0x4B8B42` are the **one-cell hover
  ground-quad in WORLD units** (the cursor cell highlight) — world-anchored,
  correct at every tier. **Never patch them.**
- For the balloon, no pick-side change is needed: the CSI's click box IS the
  drawn icon rect (`+0xD0`/`+0xD4`), so scaling the icon immediate grows the
  hit box automatically.
- Shipped code reads the live view/zoom object through **`[0xB43DD8]`** (zoom
  at `+0xC`, `CodePatches.cpp:4286`). Vtable `0xA901A0` is the DEMOLISH
  control's (§3 row 10).

**SIZE/SCALE SEMANTICS.** n/a (geometry-derived). The hover quad is
world-anchored.

**SCALING COVERAGE.** Nothing patched, deliberately: every shipped size lever
(§2.1, §2.3, §2.5, and the CSI patch) grows the click target for free via
this path.

**INSTRUMENT.** None dedicated. A click's downstream effects are visible in
`BUBBLEFX` (a UDI offer click spawns `mission_selection_red`).

### 2.5 Marker strips — builder `0x5F5FB0` and zoom table `0xAA523C`

**WHAT IT DRAWS.** The traffic/commute route-trace family (§3 row 16) — a
code-generated billboard strip. It is not the UDI offer balloon; that is the
City Situation Indicator of §3 row 1.

**MECHANISM** (table bytes, sole-consumer proof and builder prologue all read
from the exe; `CodePatches.cpp:4212–4231`).

- The billboard strip is **CODE-GENERATED** by builder **`0x5F5FB0`** (stock
  prologue `55 8B EC 83 E4 F8`): content icons (24px default) + 8px margins
  + **64px disc**, every pixel dimension multiplied by the **per-zoom float
  table at `.rdata 0xAA523C` = {0.5, 0.75, 1.0, 1.5, 2.0}**
  (`3F000000 3F400000 3F800000 3FC00000 40000000`).
- **Sole consumer proven**: the table is read at `0x5F6067`
  (`fld [ecx*4+0xAA523C]`); the only other `.text` reference, `0x5F74AD`
  inside the route-dot function, is a texture-loop END-BOUND compare, not a
  read. Patching the table therefore reaches this builder's output and
  nothing else.
- The renderer pick (§2.4) tests the verts this builder writes, so what it
  draws grows its click target with the visual — no pick-side patch.
- **Art facts for this family.** The CSI geometry is code-built, so no
  balloon-named S3D exists to find ("marker-post" S3Ds are construction props
  by exemplar name; "balloon" S3Ds are tourist props). The TrainSwitch pair
  at `0x563572` is rail levers. The sheet `{46a006b0, 094ac89a}` is **32x32
  RGBA, 164 of 1024 pixels with alpha > 0, all pure white, a hollow
  anti-aliased RING about 22px across** (centre row
  `.....######.........######......`) — it is not the CSI's art (the CSI
  draws eight 152×38 PNG strips).

**SIZE/SCALE SEMANTICS.** **Pixel-dimensioned, zoom-ramped**: fixed px
constants × the per-zoom table — between the two pure classes.

**SCALING COVERAGE.** `ApplyMarkerZoomScale` (`CodePatches.cpp:4233`)
multiplies all 5 table floats by the tier factor (1.5x →
{0.75, 1.125, 1.5, 2.25, 3.0}), verify-before-write against the stock bit
patterns, single VirtualProtect span, "MARKERZOOM table x1.50" log line. It
reaches `0x5F5FB0`'s output — the route-trace family of §3 row 16.

**INSTRUMENT.** `SPSTRIP` (§4) — the strip-builder hook that rides SPPROBE
mode 3, and the positive control for this lever.

### 2.6 The terrain / region bake family — window-owned surfaces

These LOOK like renderer work (they paint the world) but are **window-owned
bakes**: a window class owns a surface, bakes terrain/data into it, and blits
panel-sized. They are documented elsewhere; listed here so the census can
cite them instead of re-opening them.

| system | where it is documented |
|---|---|
| dock/dashboard minimap terrain bake (power-of-two blit law, 5-blitter jump table, x8 hole) | `SC4-UI-ENGINE.md` §2.4; zoom-cliff fix `ApplyMiniMapX8Bake`, 15 bytes in-memory |
| Data Views map (terrain base + unbounded cell overlay; alpha-blend birth order) | `SC4-UI-ENGINE.md` §2.4 |
| region screen (city tiles, bubbles, zoom rebuild) | `tools\research\REGION-SCREEN.md` (197 fns); the zoom rebuild is fixed by REBUILDING the surface, not resizing it |
| disaster-flyout ring sprite (screen-space sprite over the UI; seat-scaling law) | `UiSpike.cpp:1849–1869` |
| WarriorUI terraform ring (third-party flyout scripts + ring art, load-order collision) | the third-party patch set (flyout script overrides + ring art) |

### 2.7 THE BOUNDARY CASE — the during-mission map marker window `0x48E945B4`

**Window-side but world-anchored** — the standing counter-example to
"in-world implies not a window".

- A **code-created GZWinBMP** (vtable `0x00ADF6A0`), parented straight to the
  3D view under NO listed root, and **TRANSIENT** (present one sample, absent
  0.5s later), which is why a static census does not see it.
- **BORN at its bound art's size**, then swept ×f — so tier art compounds to
  **32f²** on screen (72/128/288) unless the art family is pinned. The art
  family is pinned at a fixed 96px (= 3× design) for 96f on screen at every
  tier. The bind-time-geometry trap is the LATCH LAW family: a SetImage-latched
  crop is a hidden consumer of bind-time geometry.
- Art is **code-bound** (pushed beside the window id at `0x4B8314` /
  `0x7AC651`; zero `.UI` refs). The family's base TGI `{46a006b0,094ac89a}`
  is **32x32 RGBA, 164 of 1024 pixels at alpha > 0, all pure white — a hollow
  anti-aliased RING about 22px across** (centre row
  `.....######.........######......`). The pin is harmless.
- Covered by `kBmpxCityRoots` + the BMPX fit rule (dst follows source,
  reduced to fit — overshoot structurally impossible).

**Decision-tree consequence:** a world-anchored visual that IS a window shows
up in a census **only transiently** — sample while the visual is actually on
screen, or the null is not a null.

---

## 3. THE CENSUS — every in-world UI-like visual a player can SEE

Columns: **owning system** (§2 ref) · **tier scaling** (correct / scaled by /
n-a). The table was walked from the game's feature surface, not from a code
enumeration — treat it like the archive inventory: **discover, don't trust
the list**; add rows the moment a new in-world visual is reported.

| # | visual (player's words) | owning system | tier scaling |
|---|---|---|---|
| 1 | **UDI offer balloon** (blue disc + glyph, idle mayor view) | **CITY SITUATION INDICATOR, category 4** of the dispatch-indicator system: drawn by `cSC4DispatchVehicleView::Draw` **`0x0046D990`**, keyed on the AUTOMATON (QI iid `0xA9B40F05`), identified by SUPPRESSION on screen. **TWO quads**, both sized by **inline `.text` immediates**: icon + **click box** 35×35 (`mov eax,0x420C0000` at `0x0046CC47`, imm at `0x0046CC48`, stored to record `+0xD0`/`+0xD4`, halved to ±17.5 by `Draw`) and pin/backing 64×64 (eight ±32.0f at `0x0046EABD..0x0046EB6F`). Art = eight 152×38 PNG strips (type `0x856DDBAC`), each present TWICE, in groups `0x46A006B0` (drawn) and `0x1ABE787D`. Full write-up: `tools\research\CITY-SITUATION-INDICATORS.md`; summary at the end of this file | scaled by **`ApplyCsiIndicatorScale`**, confirmed on screen at 3x, 3840×2160 |
| 2 | UDI during-mission map marker (edge bubble) | window `0x48E945B4` (§2.7) | correct — art family pinned at 96px |
| 3 | UDI in-mission target glow (`mission_selection_*`, incl. the red engaged-target click halo) | effects manager (§2.1) | scaled by `InstallMissionBubbleScale` |
| 4 | UDI route dots (dotted path) | signpost-occupant module (row 16). Note: `0x5F7400` decodes mid-instruction and is not a function start; the enclosing fn is `0x5F73A0`. **Sizing:** dot size = `[this+0x80]` sizeParam (ctor default **1.0f** @`0x5F838D`; SetSize `0x5F7B10` = iface `0xAA5680` slot 6, clamped (0,8]; serialized, load `0x5F7E50`) × **16.0f** (`.rdata 0xA8D45C`, read `0x5F78CA` = one cell) × texture aspect. No literal-size call site exists in the exe (control: all 7 iid-`0x2B3B7D86` and 42 iid-`0xE9793A65` refs scanned) | world-derived ⇒ n-a |
| 5 | police/fire dispatch markers | **`cSC4DispatchVehicleView` — the dispatch-indicator system** (full write-up `tools\research\CITY-SITUATION-INDICATORS.md` §1). These markers are the OTHER categories of the same drawer whose **category 4** is row 1's UDI offer balloon (category test `cmp ecx, 4` @`0x0046DD6C`); `cSC4DispatchVehicleView::Draw` = **`0x0046D990`**. Byte-proof they reach the same pin quad: the eight ±32.0f inline immediates `0x0046EABD..0x0046EB6F` are **NOT category-guarded** — `cmp [esi+4],4 ; je 0x46E38E` @`0x0046E852` sends CSI down its own branch which **rejoins the common code** | pin quad co-scaled by **`ApplyCsiIndicatorScale`** (`src\CodePatches.cpp:4352`, shared uncategorised path); a dispatch marker renders correctly at 1.5x |
| 6 | one-cell cursor hover quad (ground highlight) | UDI control hover quad (§2.4, 16.0f world) | n-a (world-anchored) — **never patch** |
| 7 | zoom-gated grid decals (zone/cell grid at zoom 4/5) | effects manager records (§2.2) | n-a (world-anchored, zoom-ramped) |
| 8 | orange/green guidance arrows (UDI drive mode) | **UDI DRIVING view-input control** singleton `.bss [0xB21D74]` — arrow drawer at owner+0x9C (ctor `0x5649D0`, vt `0xA9D974`/`0xA9D95C`), one-shot texture init **`0x5633C0`** holds the ONLY refs to all six sheets (`0x563587`–`0x563631`), registered via `[vt+0x80](drawer,5,0x3E8)` @`0x565D98`. Art: six 128×128 FSH `{7AB50E44,1ABE787D,0x6BE09921–26}` — orange 21/23/25, green 22/24/26. The same loader owns the TrainSwitch S3D pair. Notes: `overlays\row-08-guidance-arrows.md` | n-a (world units: 8.0/16.0 template `0x56340E`–`0x563481`; never calls px→world `0x7F6690`, control: the signpost builder does) |
| 9 | disaster-flyout ring sprite | screen-space sprite, seat-scaled (§2.6) | correct |
| 10 | building/lot selection glow (query & demolish hover) | **Occupant HIGHLIGHT FLAG** — `cISC4Occupant::SetHighlight(mode,sendNow)` at vt+0x44 (`cISC4Occupant.h:57-58`); the renderer tints the occupant's OWN model, so there is no separate visual. Query tool (clsid `0xC7AF928E`) sets mode **7** @`0x4CBF9D` (saves old at `[this+0x40]`, restores `0x4CBF65`); Demolish (`0x46DDB5F1`) sets **5** @`0x4B99F6`; mayor-default control sets 5 @`0x4DB34A`, clears @`0x4DAD7E` and spawns one `local_tile_outline` effect @`0x4DA77A`. Change posts `kSC4MessageOccupantHighlightChange` `0xA2D1C5B9` (`0x80D600`). Vtable `0xA901A0` is the DEMOLISH control's | n-a (the tint covers exactly the model) |
| 11 | coverage-radius circle while placing civic buildings | **Effects manager (§2.1)** — named effect `PlopMode_<Family>_{Plop,Inactive,Existing}` (Police/Fire/Health/Education) via CreateEffectByName; drawable = EFFDIR children `<family>_coverage_circle_{existing,inactive,plop_collapse,plop_existing}_{normal,invert}` (type-1 ground-projected decal) | n-a (world-anchored decal) |
| 12 | plop direction arrow on a held lot | **Effects manager (§2.1) + EFFDIR (§2.2)** — named effect `Lot_Direction_Arrow`, spawned by the Lot Plop tool's preview refresh; zoom-gated to close zooms by three per-zoom child copies. NOT an S3D prop (control: `s3d-name-sweep.txt` has 1,957 rows, zero arrow/direction/compass names) | n-a (world-anchored, zoom-ramped) |
| 13 | zone drag rectangle + zone color decals | **Lot-display CELL-QUAD BUILDER** (renderer world, code-generated — not effects, not a window): per-lot quads built by `0x6CC970` (vt slot 43 = +0xAC of vtable `0xAB1B98`; QI `0x6C3B80`) | n-a — world-anchoring derived from the builder |
| 14 | god-mode terraform brush ring (in-world cursor circle) | **Effects manager (§2.1) — the cursor/brushEffect family, EFFDIR-defined (§2.2)**: named terrain-decal effects `mountain_tool_active` / `valley_tool_active` / `level_tool_active` / `smooth_tool_active` (+`_inactive` twins), each a parent with `_normal`/`_invert` decal children; `mayorlandscape_tool_*` = the mayor-mode landscape brush. Distinct from the WarriorUI terraform ring and the disaster-flyout ring sprite | n-a (world-anchored decal) |
| 15 | neighbor-connection arrows at city edges | **THE MARKER-OCCUPANT FAMILY (§2.5) — and the family's Rosetta stone.** Exemplar **`UI8x1x3_ConnectArrow_29F1` {0x6534284A, 0xC977C536, 0x29F10000}** carrying **OccupantSize {8,3,1} m** at exemplar bytes 0x58/0x5C/0x60, read by the marker factory via property **`0x27812810` @`0x4A25D3`**; binds its own S3D `{0x5AD0E817,0xBADB57F1,0x29F10000}`; created by `0x6D4860` (push `0x29F10000` @`0x6D4A66`, +15.5f nudge `.rdata 0xAB1CA8`). **The name encodes the size**, and the size is exemplar data for this family — row 1's size, by contrast, is nine inline `imm32` floats inside `.text` | n-a (world units, no px imm, no zoom table on the path) |
| 16 | traffic/commute route overlay (query route trace) | **Signpost-occupant module** — GZCOM clsid `0xAB72FBB3`, ONE 0x590-byte class (ctor `0x5F5510`). **Sizing:** quad px = per-item pixel size (item vt+0x14, read `0x5F69CB`) → px→world `0x7F6690` on live view `[0xB43DD8]` (call `0x5F69E8`) → × **`0xAA523C[zoom]`** (`fmul` `0x5F69ED`; table read `fld [ecx*4+0xAA523C]` @`0x5F6064`) | pixel-derived ⇒ co-scaled by MARKERZOOM (`ApplyMarkerZoomScale`) |
| 17 | in-world lot signs (casino/highway/player signs) | S3D lot props (see `s3d-name-sweep.txt`) — world objects, not UI | n-a |
| 18 | ambient shadows (windmill, helicopter) | effects manager child transforms (§2.2) | n-a (world-anchored) |
| 19 | news zeppelin / blimp | automaton (world object) | n-a |
| 20 | pause/alert screen border | window `cSC4WinAlertBorder` id `0x6A5E44B6` (ENGINE §0 — window world, despite drawing over the view) | correct |
| 21 | minimap / Data Views / region bakes | window-owned surfaces (§2.6) | correct |
| 22 | fireworks / celebration effects | effects manager (§2.1) | n-a |

**Census tally: 22 rows, every owning system identified.** Row 1's owner is
the CSI drawer `0x0046D990`, identified by SUPPRESSION on screen and
confirmed on screen at 3x after the fix shipped; row 5's drawer is settled
the same way at 1.5x. Rows 11/13/14/16 are DERIVED from the owning code or
data.

**The `.rdata` blindness rule:** a sweep that reports "the constant is inert"
or "no size data exists" after searching only `.rdata` has not looked — both
of row 1's size levers are immediates inside `.text` instructions. Any
constant sweep on this side must scan `.text` immediates as well.

---

## 4. INSTRUMENTS — what can SEE this side, and each one's scope limit

A gate is only as honest as its scope. Every probe below states what it
CANNOT see; a null from any of them without its positive control is not
evidence.

| instrument | what it sees | positive control | SCOPE LIMIT |
|---|---|---|---|
| **BUBBLEFX** (`CodePatches.cpp:4305`, ini `MissionBubbleFx>=1`) | every successful `CreateEffectByName` whose name starts `mission_selection`; pre-state of the instance; whether it was scaled | "BUBBLEFX installed on CreateEffectByName" at startup; one line per spawn | name-filtered — sees NO other effect names (widen the filter to census the effect world); routine lines capped at 12 per run (refusals uncapped); sees nothing spawned by other routes |
| **SPPROBE** = SPQUAD + SPTEX (`CodePatches.cpp:4189`, ini `MissionBubbleFx=3`) | every signpost quad build (this, kind, LIVE immediate from the code page) and every texture-ensure (kind census) | "SPPROBE armed" line | only these two functions — a visual drawn by ANY other builder is invisible; log lines capped at 24 each (counters uncapped); dev-mode only, do not ship armed |
| **SPSTRIP** (`CodePatches.cpp:4276`, rides SPPROBE mode 3) | every marker-strip build at `0x5F5FB0`: this, current zoom, and the LIVE `0xAA523C` table value for that zoom — the positive control for the MARKERZOOM lever | "MARKERZOOM table x1.50" at install + SPSTRIP `table=1.125` at zoom 2 on the next launch | only builder `0x5F5FB0`; log cap 16 (counter uncapped); zoom read depends on the view object at `[0xB43DD8]` being non-null (logs zoom=0xFFFFFFFF/table=0 otherwise — that is a scope artifact, not a measurement) |
| **SMALLWIN** census (`UiSpike.cpp:12454`, default OFF) | every VISIBLE <=80px window under the 3D view, every ~2s | the armed line, printed per run | **depth-3 walk, panel subtrees excluded, 200-line budget** — a depth-2 24-cap truncates on panel furniture and silently hides the answer; a census cap is a silent scope limit. WINDOW WORLD ONLY: proves "not a window", never "what it is" |
| **BMPX / SEATPROBE** draw hooks (ENGINE §7, `UiSpike.cpp`) | every GZWinBMP draw under a **listed root** (`kBmpxCityRoots`) | the per-draw `img WxH win WxH -> dst` line | root-LIST scoped — an unlisted root hooks nothing; a root that IS the BMP hooks silently. WINDOW WORLD ONLY |
| effdir extract + builder gates (`tools\effdir\`, `tools\research\effdir\`) | the EFFDIR bytes: record layout, name map, scale fields | frozen-set FATAL both directions; 72-byte predicted diff | OFFLINE — proves what the file says, never what the engine consumed (§2.2 load law: the engine reads the first provider in the list, which may be a different copy) |
| `s3d-name-sweep.txt` | every named S3D across the nine archives | 1,957 rows present | names only — an unnamed or code-composed drawable is invisible (the CSI balloon is exactly this: geometry code-built, no S3D to find); the archive count is DISCOVERED per run, never listed |

**The instrument lesson:** every lever on this side ships with its own
positive-control probe in the same build — the MARKERZOOM lever shipped with
SPSTRIP, and the CSI fix was identified by a suppression probe on
`0x0046D990` plus a 3x exaggeration to separate the two overlapping quads.
The probe-with-lever pattern is necessary but never sufficient: a probe that
fires proves the lever reaches its builder, not that the builder draws the
visual in question. Two scope limits hold across all of them: **(a)** none of
these probes can see an **inline `.text` immediate**, so any "constant is
inert" verdict from them is a filtered null; **(b)** a research probe is not
free — SPPROBE mode 3 arms speculative reads inside a draw path, so it is
dev-only and the ini returns to its default when the investigation ends.

---

## THE U-DRIVE-IT OFFER BALLOON — City Situation Indicator, category 4

**Full write-up: `tools/research/CITY-SITUATION-INDICATORS.md`.** Summary for
this census:

The balloon is **CSI, category 4 of the dispatch-indicator system**, drawn by
`cSC4DispatchVehicleView::Draw` = **0x0046D990** and keyed on the AUTOMATON
(QI iid 0xA9B40F05), which is why it tracks a moving vehicle. Identified by
SUPPRESSION — killing that one function makes the balloons vanish on screen.

It is **TWO quads**:

* pin / backing 64x64 — eight ±32.0f INLINE immediates at 0x0046EABD..0x0046EB6F
* icon + **CLICK BOX** 35x35 — `mov eax,0x420C0000` at 0x0046CC47 (imm at
  0x0046CC48), stored to the record's `+0xD0`/`+0xD4`, halved to ±17.5 by Draw

Art: 8 PNG strips (type 0x856DDBAC), 152x38 = four 38x38 states, each present
**twice** in groups 0x46A006B0 (drawn) and 0x1ABE787D.

### Names that describe a neighbouring subsystem, not the balloon

* `mission_selection` is the in-mission ground glow, `aircraftindicate` is a
  landing ring, and `Tag1x1x3_Helicopter` is a helipad prop. **None is the
  balloon.** Names describe the owning subsystem, not the visual.
* The signpost quad builder measures zero calls with balloons on screen: the
  balloon is not a signpost.
* The offer control's renderer ray-pick does not bound the CSI: the clickable
  area is the icon quad's own `+0xD0`/`+0xD4` rectangle — only the inner
  glyph takes the click, not the grey around it.
* The 1x bubble art `{46a006b0,094ac89a}` is a hollow anti-aliased ring
  (32x32 RGBA, 164 of 1024 pixels with alpha > 0, all pure white, ~22px
  across) and belongs to the map-marker window family (§2.7), not to the CSI.

### The shipped fix

`ApplyCsiIndicatorScale` (`src/CodePatches.cpp`), mode >= 2, both-or-neither
over all nine immediates, tier-general. Art is generated at 1.5x/2x/3x and
wired into `Deploy-OnGameClose.ps1`, so the dist bundle picks it up from the
manifest.

The balloon renders correctly at 3x, 3840×2160 — disc, glyph, pin and pole
all proportional. The pin quad's eight ±32 immediates are NOT
category-guarded, so the same write also scales the dispatch markers of §3
row 5, which render correctly at 1.5x; `kCsiQuad` therefore needs no
per-category split.

### Why a balloon this visible is hard to attribute

A sweep that reports "no art involved" or "constant is inert" can be honest
and still **filtered**: an art check that covers one of two resource groups
misses the drawn copy, and a constant sweep restricted to `.rdata` misses
both size levers, which are `imm32` values inside `.text` instructions.
