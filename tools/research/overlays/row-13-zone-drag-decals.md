# Row 13 — zone drag rectangle + zone color decals (2026-08-17)

> **CURRENT GRADE: MEASURED + DECODED** — 2026-08-30; see the row body for which half is attributed.
>
> ⛔ **The dated header below is the ORIGINAL session's grade and is
> superseded.** It is kept rather than rewritten because this project
> annotates history instead of editing it — but the front door
> (`docs/DECOMPILATION-STATUS.md`) grade-scans the top of this file, so
> the line above is the one that counts. See the MEASURED section at the
> end of this file for what changed and how it was proven.

**VERDICT (PARTIAL — static disassembly, no live capture yet):**
the persistent **zone color decals are drawn by the LOT-DISPLAY cell-quad
builder `0x6CC970`** — a code-generated, cell-indexed overlay owned by the
lot/zone display class (vtables `0xAB1B98/0xAB1B88/0xAB1B70`), fed by
`cISC4ZoneManager` color+alpha and inserted into the renderer through the
same `0xE4FDA3D4` drawable idiom as the marker family. **Not EFFDIR effect
records** (no `zone*` effect name exists in the 2,411-name EFFDIR extract)
and **not the §2.2 zoom-gated grid decals** (those are the drag cursor's
*furniture*, spawned separately as `local_grid` / `local_tile_outline`).
World-anchoring is **proven at the units level** (below): every quantity in
the chain is a cell index or a world unit; the engine's one px→world helper
is never called by any zone-family function.

All addresses are file VAs at ImageBase 0x400000, exe 1.1.641 Steam
(LAA-flipped, code identical). Derived fresh this session from the shipped
exe bytes unless marked otherwise.

## 1. The attribution chain (every claim with its address)

### 1a. `[0xB43D14]` IS the cISC4ZoneManager — double-derived
- Service bank filled at `0x601C74–0x601CE6` from the facade `[0xB43CEC]`
  (set from an argument at `0x601C14` = SetCity-style):
  `[0xB43D08]`=vt+0x84, `[0xB43D0C]`=vt+0x88, `[0xB43D10]`=vt+0x8C,
  **`[0xB43D14]`=vt+0x90**, `[0xB43D18]`=vt+0x94, **`[0xB43D1C]`=vt+0x154**.
- `vendor\gzcom-dll\gzcom-dll\include\cISC4City.h`: slot 36 (=0x90) is
  `GetZoneManager`, slot 33 (0x84) `GetLotManager`, slot 85 (=0x154) is
  `GetEffectsManager`. **Cross-check:** the doc already proves `[0xB43D1C]`
  is the effects manager (§2.1 CreateEffectByName vt+0x1C) — the same bank
  read both ways lands on the same header, so the header slot math is right.
- Independent semantic check: publisher fn `0x412530` (start; `mov ebp,
  [0xB43D14]` at `0x412540`) calls `[ebp]->vt+0x18(3..9)` and publishes the
  results as `g_num_rzone_hd_tiles` (str `0xA817C0`, pushed `0x412EF2`,
  type 3 = ResidentialHighDensity per the header enum) …
  `g_num_izone_h_tiles` (str `0xA8173C`, pushed `0x412FCA`, type 9).
  vt+0x18 = `GetZoneCount(ZoneType)` per the header — enum and slot both
  line up. (These are CITY STAT counters for the script/tuning system, NOT
  texture-variant counts — first-guess corrected.)

### 1b. The decal builder `0x6CC970` (slot 43, vt+0xAC of vtable 0xAB1B98)
- Prologue `83 EC 70 53 8B 5C 24 78` (sub esp,0x70; push ebx; …). Stack arg
  = a **cISC4Lot**; `this` = the display/manager object (fields: +0x24 = the
  per-cell LOT GRID, +0x4C/+0x50 = city cell bounds).
- **Signature MEASURED 2026-08-30, not derived from the prologue.** A review
  correctly objected that a prologue reading `[esp+0x78]` proves arg1 *exists*
  and says nothing about an arg2 — and a typed detour that under-pops corrupts
  the caller's stack. Linear disassembly settles it: the function has exactly
  **two exits, `0x6CC9AA` and `0x6CCE10`, both `ret 4`** — one stack argument.
  Both exits are `pop edi/ebp/ebx; add esp,0x70; ret 4` with **no `al`/`eax`
  set on either path**, so the function is **`void`**: it returns nothing, and
  any probe "returning success" on a suppressed call would be inventing a value
  no caller reads. Full signature: `void __thiscall(cISC4Lot*)`.
- The arg is proven a cISC4Lot by THREE independent vtable-slot matches
  against `vendor\...\cISC4Lot.h`:
  - `vt+0x7C` at `0x6CC984` → `GetZoneType` (slot 31), result 0..15
    dispatched through a 16-entry jump table at `0x6CC995`
    (table `0x6CCE14`, index bytes `0x6CCE1C`; non-RCI kinds route to the
    sibling handler `0x6CAAF0`, its only caller `0x6CC99F`).
  - `vt+0x38` at `0x6CCA0F` → `GetBoundingRect` (slot 14) fills the cell
    rect the loop walks ([esp+0x60..0x6C]).
  - `vt+0x58` at `0x6CCA2F` → `GetSize(u8&,u8&)` (slot 22), consulted only
    for types 7..9 (agriculture/industry hatch suppression).
- ZoneManager consumption (ecx = `[0xB43D14]`, byte-verified in the listing):
  - **`vt+0x3C GetZoneDragColor(type)` at `0x6CC9B9`** → unpacked to RGB
    bytes [esp+0x18..0x1A] (`shr 24/16/8` at `0x6CC9C0–0x6CC9CD`).
  - **`vt+0x40 GetZoneDisplayAlpha()` at `0x6CC9D9`** → the A byte
    [esp+0x1B]. So decal RGBA = drag color + display alpha — the SAME color
    source serves the drag rectangle and the laid decal.
- City clamp: `[0xB43CEC]` vt+0x178 / vt+0x174 at `0x6CC9E8/0x6CC9FB` =
  `CellCountZ/CellCountX` (cISC4City slots 94/93), minus one → max cell
  index; the loop tests cells against `this+0x4C/+0x50`.
- Per-cell edge logic (`0x6CCAB5–0x6CCBAA`): neighbor cells fetched from
  the lot grid `[this+0x24]->vt+0x18(x,z,0)`; a neighbor equal to this lot
  clears the edge flag; otherwise the neighbor lot's `vt+0x5C GetFacing`
  (slot 23) decides — this is what draws the rectangle's border edges only
  on region boundaries.
- Per-cell emit: `this->vt+0xA8` (slot 42 = `0x6C6CF0`) at `0x6CCC3C` with
  a 4-int cell key + out {u32,u8,u8} — a hash-cached texture-variant lookup
  (cache walker `0x6C0030`, keyed by shl-4 folds at `0x6C6CFB–0x6C6D0E`).
  16-byte records accumulate ((end−start)>>4 at `0x6CCDAF`).
- Tail: `this->vt+0xA4` (slot 41 = `0x6C41A0`) at `0x6CCD9B` gets/creates
  the drawable ATTACHMENT: kind id `0x497F6D9D` pushed `0x6C41CB` on the
  attachment manager `[this+0x28]->vt+0x84`; on miss GZCOM-creates clsid
  **`0xC97F987C`** with iid `0x097F6D98` (`0x6C422D`), or directly
  `new(0x60)` + ctor `0x5E05B0` (`0x6C423D/0x6C424B`); record list handed
  over via `[obj]->vt+0x20(ptr,count,0)` at `0x6CCDB4`.
- Class registry (.data name/id pair list): `0xB08CC4` "cSC4FoundationOccupant"
  / `0xB08CC8` = `0xC97F987C`, next pair `0xB08CCC`
  "cSC4LotBaseTextureOccupant" / `0xB08CD0` = `0x29802083`. The
  name↔id pairing DIRECTION in this table is unadjudicated (no anchor pair
  verified); record only that `0xC97F987C` sits in the lot-surface-occupant
  neighborhood of the registry.

### 1c. The owning class (drawer host)
- Ctor `0x6C8650` (real init; thin thunk `0x6C7280`) writes vtables
  `0xAB1B98` (this+0), `0xAB1B88` (this+4), `0xAB1B70` (this+8).
- QI `0x6C3B80`: accepts `0x4818E5D2`/`0x4818E5D1` → this+0,
  `0x452294AA` (= GZIID_cIGZMessageTarget2, `GZCLSIDDefs.h:77`) → this+4,
  **`0xE4FDA3D4` → this+8** — the SAME iid the renderer QIs 129x/cycle from
  caller `0x90E00D` on marker objects (REGRESSION.md:11997, census row 1's
  live suspect). The zone overlay rides the same renderer drawable idiom.
- Main vt slot 5 (`0x6C3C40`) returns constant `0x6818E5C9` (a kind/class
  id; not in the .data registry). The concrete class NAME is UNRESOLVED —
  it is a lot/zone DISPLAY manager, not cISC4LotManager (its slot 5 would
  be GetLot) and not cISC4ZoneManager (slot 5 would be GetZoneGrid).

### 1d. The drag-rectangle tool + its effect furniture
- Zone-family tool-control init functions cache the service bank and create
  TWO effect instances: ensure-`local_grid` helper **`0x5FB340`**
  (`cmp [ecx],0; CreateEffectByName("local_grid", &slot)` via `[0xB43D1C]`
  vt+0x1C, name str `0xAA66D0`) — callers `0x4C16C6`, `0x4DA706`,
  `0x660CE9`, `0x662244`; plus `CreateEffectByName("local_tile_outline")`
  (name str `0xA92C80`) at `0x4DA77A`, `0x660D15`, `0x662270` into
  [control+0x94]. The tool caches ZoneManager (`[0xB43D14]` → [control+0x30]
  at `0x4DA712`) and LotManager (`[0xB43D08]` → [control+0x34]).
- These effect names are EFFDIR type-1 records (extract offsets:
  `local_grid` family incl. `local_grid_decal_z2..z5_4`; `local_tile_outline*`
  at 0xA60CA–0xA654B in the decoded extract) — world-unit children of the
  §2.1/§2.2 system; the doc already proved the z4 grid decals sit at ±0.25
  world offsets with z5 exactly half (§2.2) — zoom-gated but world-sized.
- The preview fill path in the tool (`0x4C1740` function family, texture
  fetch near `0x4C1A02`) reuses the same cell/texture machinery; its exact
  quad-emission was NOT walked — preview drawer attribution is inferred
  from shared services + shared color source, stated as such.

## 2. WORLD-ANCHORING — proven from code, with controls

1. **Units audit (opcode):** every quantity in builder `0x6CC970` is a cell
   index (ints), a city cell bound, an RGBA byte, or a texture key. There
   is NO screen-px constant and NO resolution/zoom read anywhere in
   `0x6CC970`, `0x6CAAF0`, `0x6C6CF0`, `0x6C41A0`.
2. **The px→world helper negative, WITH positive control:** helper
   `0x7F6690` (the §2.3/§2.5 px→world converter — the ONLY mechanism this
   engine family uses to make screen-fixed world quads) has exactly **18
   call sites** in .text: `0x46CD0A/23/5A/75`, `0x5F0FA3`,
   `0x5F1EF3/1F03/1F2F`, `0x5F20B6/C6` (signpost 44px/150px — the doc's
   byte-verified sites, §2.3), `0x5F607D/6094/60B6/60CA/60DE`,
   `0x5F69E8/6AE5/6AFD` (marker strip, §2.5). **Zero** sites in the zone
   bands (0x4C1xxx tool, 0x46xxxx lot methods, 0x5FBxxx ensure helper,
   0x6C3000–0x6CD000 overlay class, 0x5E0xxx attachment). The scan sees
   pixel-sizing exactly where the doc proves it exists, and none here.
3. **Sibling data:** the drag cursor furniture (`local_grid*`,
   `local_tile_outline*`) are EFFDIR records whose transforms are world
   units (±0.25-cell z4 offsets, §2.2 proof) — consistent, same-system.

Therefore the decals/drag rect are sized by THE CELL (16m world) and the
camera; they cannot shrink at a UI tier. (This is the code-level proof the
row asked for; the grade stays PARTIAL until one live capture runs the
probe below — the #188 law: a model is DOCUMENTED only when a prediction
meets a measurement.)

## 3. SIZING — the numbers that control on-screen size
- **Geometry: none.** Size IS the lot's cell rect (cISC4Lot::GetBoundingRect)
  in city cells; on-screen size = camera projection of 16m cells. No
  constant to patch, nothing tier-dependent.
- **Color:** `cISC4ZoneManager::GetZoneDragColor(type)` (vt+0x3C, consumed
  `0x6CC9B9`) — per-type RGBA (data-driven; exemplar-backed).
- **Alpha:** `GetZoneDisplayAlpha` (vt+0x40, consumed `0x6CC9D9`); default
  via vt+0x44; TOGGLED live by data-view code at `0x7A4A9E/0x7A4AB2` and
  `0x7A4EC4/0x7A4F00` (SetZoneDisplayAlpha vt+0x48) — e.g. the Zones data
  view driving the overlay opaque.
- **Texture variant:** per-cell cached lookup `0x6C6CF0`/`0x6C0030` (4-int
  key → {u32 tex, u8, u8}). API-level source `GetTextureForZone`
  (ZoneManager vt+0x38) exists but a proven ZoneManager-object call site
  was NOT found this session (see instrument note below).
- Grid-at-zoom-4/5 lines: EFFDIR zoom ramps on `local_grid_decal_z4_*/z5_*`
  (§2.2) — zoom-gated, world-sized.

## 4. TIER CALL
**Stay (world-anchored) — n-a at every tier, by construction.** The census's
"world-anchored by observation" is now backed by the units audit + the
0x7F6690 negative-with-control. Do not patch anything here; the only
tier-adjacent lever that could ever matter is the EFFDIR zoom ramps on the
grid decals (visibility gating, not size).

## 5. INSTRUMENT-SCOPE ERRATA (this session's own)
- A windowed scan ("any `call [reg+0x38]` within 120 bytes of a
  `[0xB43D14]` read") flagged `0x6CCA0F`, `0x467843`, `0x4C1A02` as
  GetTextureForZone. WRONG CHANNEL for the first two: the object there is a
  **cISC4Lot**, so vt+0x38 = GetBoundingRect. `0x4C1A02`'s object is
  unresolved (leading bytes misaligned in the listing). Lesson: a slot
  displacement is only meaningful with the OBJECT it is called on.
- BUBBLEALL captures (9 logs, `_tests\captures\`) contain NO zone/grid
  effect spawns — **null without positive control**: those sessions were
  UDI balloon hunts; no zone tool was ever dragged, and `local_grid` spawns
  lazily on first tool use (`0x5FB340` caches). Not evidence of anything.

## 6. LIVE PROBE (the one cheapest capture to move PARTIAL → DOCUMENTED)
- **Hook site:** detour builder `0x6CC970` (stock prologue
  `83 EC 70 53 8B 5C 24 78`, verify-before-write), log-only:
  `this`, the lot arg, lot vt+0x7C zone type, the rect from lot vt+0x38,
  and the RGBA assembled at [esp+0x18..0x1B].
- **Expected positive:** bursts of calls while zoning (drag-release lays
  lots ⇒ one call per new/updated lot) and at city load (existing zoned
  lots rebuild); the RGBA matches the on-screen zone color per type
  (prediction: type 1..3 → the green family from GetZoneDragColor).
- **Expected negative control:** zero calls while idling in a view with no
  zoning activity after the initial build (the marker-strip SPSTRIP idiom:
  ship the probe WITH any future change, §4 law).
- Optional second channel: widen BUBBLEFX's name filter to `local_` for one
  run and drag a zone — expect `local_grid`/`local_tile_outline` spawns on
  first tool activation (positive control for the §2.2 sibling claim).

## 7. Dead ends / ruled out (each with its control)
- **EFFDIR records for the zone colors:** the 2,411-name decoded extract
  (`tools\research\effdir\T-ea5118b0...png`) contains NO `zone*` effect
  name (positive control: the same scan finds `grid_flash`,
  `local_grid_decal_z4_1`, `lot_direction_arrow_z5`, the 18
  `mission_selection_*`). The zone colors are not effect-spawned.
- **`tool_plop_zone` / `PlaceZone` strings:** audio. `tool_plop_zone`
  (str `0xA81030`, ref `0x40CB23`) is a sound-object name near the
  `0xB207CC` audio service; `PlaceZone` (str `0xAA17D4`, ref `0x5C462C`)
  is a sound-cue registration (`push id 0xEBB48D31; push name; call
  vt+0x18` in a table of siblings).
- **Signpost/marker ownership:** the px→world helper audit (item 2 above)
  excludes both pixel systems from this visual's chain.
- **S3D/prop art:** zero `zone` hits in `s3d-name-sweep.txt` (1,957 rows
  present = its own positive control) and `propsim-exemplars.txt`.
- `kRenderDecals` (str `0xABB7CC`, ref `0x7DF7B2`) + `RenderDecals` pass
  markers (`0x7D14E4/0x7D167B`) = the EFFECTS-manager decal render pass
  (the §2.1 world; the stats line `0xA9F108` counts its decals). Context
  for the grid-decal siblings, not the zone-color drawer.

*Written by the row-13 census agent, 2026-08-17. Static-only; no live run.*
