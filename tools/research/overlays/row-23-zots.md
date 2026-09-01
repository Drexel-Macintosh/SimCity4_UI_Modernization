# Row 23 — zot warning discs (no-power / no-water / no-road / no-job balloons over buildings)

> **CURRENT GRADE: DOCUMENTED** — live-confirmed 2026-08-24, "40+ claims, zero refuted". Unchanged since; stamped here only so every row file in this folder carries its grade in the same place.

**Date:** 2026-08-23, live-confirmed 2026-08-24 · **Grade: DOCUMENTED** (every VA below was derived once and then
independently re-derived by an adversarial second pass — 40+ claims, zero refuted —
and the §5 live zoom pair has now confirmed the prediction on screen) · **Verdict: world-anchored prop occupants — correct at every tier by
construction; no cure, no lever, nothing for the mod to do.** VA basis:
`SimCity 4.exe` 1.1.641.0, ImageBase `0x400000`.

Closes register **B#3** (`research/UNKNOWNS-AND-NEXT-TARGETS.md`), the last whole
visible feature with no census row. Decode instruments preserved in
`tools/research/zots-decode/`.

## §1 The attribution chain (each step with its evidence)

1. **The ids are engine-pushed, not data-driven.** All seven `.text` imm32 sites
   from the positive-control-verified sweep (`udriveit/exe-instance-sweep.txt`)
   are `push imm32` instructions (opcode at sweep-addr − 1):
   NoPower `0x0FD10000` @`0x6CADAA`/`0x6CC11D`, NoWater `0x1C430000` @`0x6CAF3E`,
   NoCar `0x107A0000` @`0x6CB195` (+ the outlier, step 6), NoWork `0x1C440000`
   @`0x6CB1C6`/`0x6CB1E8`.
2. **Four updater methods of one class own the band sites** (int3-delimited):
   `0x6CABB0` per-occupant **NoPower** (ret 0xC), `0x6CAE30` **NoWater** (ret 0xC),
   `0x6CAFC0` **NoCar/NoWork** commute updater (ret 0x10, holds three sites),
   `0x6CBF40` **region NoPower sweep** (ret 4). Owner = the census **row-13
   "drawer host"** (ctor `0x6C8650`, vtables `0xAB1B98`/`0xAB1B88`/`0xAB1B70`,
   QI `0x6C3B80`) — the same class that builds zone-drag cell quads.
3. **One shared helper `0x6C98C0` = AddZot(occupant, zotInstanceId, kindCode)**,
   ret 0xC. Every band site is `push kind; push zotId; push occupant; call 0x6C98C0`
   with kind codes **4=NoPower, 5=NoWater, 6=NoCar, 7=NoWork**. The helper reads
   the occupant's current-kind attribute **iid `0xC999C45E`** (create-if-missing,
   bag vt+0x34) and **bails if newKind ≥ existingKind** (`jae` @`0x6C9967`) —
   *lower kind wins*: NoPower outranks NoWater outranks NoCar outranks NoWork.
   Displaced weaker zots are removed via `0x6C9780`.
4. **A zot is a CITY PROP.** Anchor = building bbox top Y (or occupant position)
   **+ 3.0f** (`.rdata 0xA85074`, `fadd` @`0x6C99E7`); orientation from the live
   view `[[0xB43DD8]+0x10]`; then `[this+0x30]→vt+0x68` where `[this+0x30]` is
   lazily bound (@`0x6CBA4A`) from `[0xB43D10]` = `cISC4City` vt+0x8C
   **GetPropManager**. Concrete vtable `0xA8F928`; slot +0x68 = `0x4A2670` (ret 0xC)
   = **`cSC4PropManager::AddLotProp(propID, &pos, orientation)`** → core `0x4A2010`
   (placementKind=2) → **CreateProp** vt+0x3C = `0x4A3040` → GetPropProfile →
   GZCOM CreateObject(default clsid `0x2977AA47`, iid `0xE9793A65`
   `cISC4PropOccupant`) → the same 0x68-byte base occupant class as the marker
   family (ctor `0x5EE050`, vt `0xAA4900`/`0xAA4868`). The new prop gets
   `SetRemovalFlags(3)` (vt+0x30) and is stamped with its kind in property
   **`0x48E95539`** (@`0x6C9A24`). ⚠ header note: gzcom-dll's `cISC4PropManager.h`
   puts the 3-arg AddLotProp at naive slot +0x64 — the shipped vtable has it at
   **+0x68** (byte-verified); the adjacent overload pair is swapped.
5. **Conditions, per zot** (byte-verified data flow): **NoPower** ⇔ PowerSimulator
   (`[0xB43DA0]` = city vt+0x10C) vt+0x94(cellX,cellZ) false; cell coords =
   bbox-center ÷ 2·CellWidth (city vt+0x16C/0x170 — no hard-coded 16).
   **NoWater** ⇔ demand>supply via BuildingDevelopmentSimulator tables AND NOT
   PlumbingSimulator (`[0xB43D94]` = city vt+0x100) vt+0x2C(cellX,cellZ);
   occupant purpose (occ vt+0x84) must be 2..4. **NoCar/NoWork** ⇔ commute flags
   from occupant trip methods + TrafficSimulator (`[0xB43DA8]` = city vt+0x114)
   destination-jobs check; purpose must be 1/3/4, NoWork only at purpose==3;
   per-occupant hysteresis counters (attr iids `0xE999B11F`/`0x8999B20B`/`0x8999B10B`).
6. **The NoCar outlier `0x6BB52B`** (fn `0x6BB3B0-0x6BB565`) is the **garbage/
   landfill simulator** hand-inlining the identical AddLotProp call — a landfill
   tract has no building occupant to hang the kind state on. Chain:
   kGZMSG_MonthPassed `0x66956816` → handler `0x6B9EA0` → monthly update
   `0x6B91D0` → per-landfill tick `0x6BD390` → predicate `0x6BB8F0` (traffic
   subnetworks over the footprint serve ≥1 of the 12 RCI groups, table `0xAB15E0`)
   → on failure `0x6BB3B0` places the zot at the nearest footprint cell
   (spiral iterator `0x43FE10`/`0x440850`), Y = terrain altitude
   (`[0xB43CF4]` = city vt+0x150 → vt+0x4C) + 3.0f, caches it at `[this+0x44]`;
   on recovery removes via PropManager vt+0x74 **RemovePropA**.
   This also resolves the site-count asymmetry: NoPower = per-occupant + region
   sweep (2), NoWork = two branches of one fn (2), NoCar = band + landfill (2),
   NoWater = per-occupant only (1).
7. **Removal:** `0x6C9780` RemoveZot(occupant, kind) enumerates props at the
   occupant's position (PropManager vt+0x60 = `0x4A3240`, filter kind 2), matches
   property `0x48E95539` == kind, removes via vt+0x74. `0x6C9A40`
   ClearZotIfKind. Kind 6 create/clear posts GZ message **`0x4C04DE69`** (1/2).
8. **Spatial thinning gate `0x6C3B10`** (regcall ecx=occ, edx=cellX, eax=cellZ):
   occupant types 1–6 pass iff `(x+z) % 4 == 0`; types 7–9 iff `x%4==0 && z%4==0`
   — un-lotted powerable occupants (power-line runs) get a NoPower balloon on a
   lattice, not per cell.

## §2 Candidates RULED OUT (each null with its positive control)

- **TagKind manager** — the zot exemplars carry a REAL S3D (TagKind binds NULL)
  and no TagKind property `0xABB90E58`; no pointer to the TagKind builder
  `0x4FBFE0` exists anywhere in the image (byte-scan), and the TagKind spine's
  slot +0x68 (`0x50C0D0`) has ret 0x14 — wrong arity for the observed ret 0xC call.
- **Signpost / pixel-fixed lane** — the px→world primitive `0x7F6690` has exactly
  **18 callers** (fresh re-scan; list matches `REGRESSION.md:13305`), **none** in
  `0x6BA000-0x6CD000`. Positive control: the known signpost caller is on the list.
- **Marker billboard strip** — no `0xAA523C` per-zoom table access on any path.
- **Effects manager** — zots are spawned by prop instance id, never by name.
- **Window world** — prop occupant through the renderer; no `cIGZWin` at any step.

## §3 Sizing

On-screen size comes **entirely from the S3D vertex coordinates, in world
metres**, per zoom model: Z1/Z2 are single 4-vertex camera-tilted plates
(15.566 × 23.966 m, rotated 22.5° about Y); Z3–Z5 are 7-vertex/18-index
three-face open boxes (Z5: 13.386 × 12.851 × 13.401 m). All four zots share
identical geometry per zoom — only UVs/texture differ.
**OccupantSize `{12,12,2}` is a simulator footprint, not render geometry**
(nothing in any model measures 2): CreateProp's init `0x4A2A70` reads it at
`0x4A2B41` (the CreateProp twin of the documented `0x4A25D3` read) and stores it
as raw float3 bbox metadata at `[this+0x48..0x50]`. The tenths-byte SetSize
(`0x5ED400` → `[this+0x5E/0x5F]`) is **never called** on this chain — those
bytes keep the ctor's 0.

## §4 Tier call

**n-a — correct at every tier by construction.** World-anchored (zero px→world
callers), sized in world metres, scaled by the camera like any building. No knob
exists and none is needed. Zots are also **click-transparent** to the documented
renderer ray-pick (`0x4B8880`): GetType returns the interned prop instance id
(CreateProp passes it at `0x4A3103`), matching none of the five whitelist ids,
and the `0xA823821E` family channel's nested QI re-check demands signpost type
`0xAB72FBB3`, which the base prop class is not.

## §5 ✅ LIVE PROBE RUN 2026-08-24 — PREDICTION CONFIRMED ON SCREEN

**Grade PARTIAL → DOCUMENTED.** The user supplied a zoom pair of the same city
(Centropolis, 11/26/192, identical date/population/balance in both frames, so
nothing but the camera changed).

- **Zoomed out:** the no-power zots render as small dots scattered over the tile.
- **Zoomed in:** the same zots render as large red roundels with a yellow
  lightning bolt, tens of pixels across.

The zots **scale with the camera**, exactly as §3 predicts for geometry sized in
S3D vertex **world metres**. A pixel-fixed drawer would have produced identical
pixel sizes in both frames; it did not.

⭐ **The negative control landed in the same two frames, unplanned and better
than the one requested.** The blue dispatch balloons (car / helicopter glyphs)
appear in BOTH frames at **essentially the same pixel size** despite the large
zoom change — i.e. they are **pixel-fixed**, which is precisely what the
dispatch-indicator decode (register #8) says: those categories are sized by the
inline screen-space immediates (32.0f/35.0f), not by world geometry. So one
image pair simultaneously confirms *world-anchored* for zots and *pixel-fixed*
for the dispatch family, using each as the other's control. That is the
strongest single piece of evidence in this row.

**Consequence, unchanged:** zots need no cure at any tier, by construction.

## §5b Original probe spec (retained for method)

Spawn lever: cheat **`0xAA7A2746` "TastyZots"** (registered @`0x7E9A09`) or an
organically unpowered lot. Acceptance: screenshot pair at adjacent zooms — a
world-anchored zot grows ~2× in pixels per zoom step. Negative control in the
same frames: a pixel-fixed visual (the route-query signpost overlay, row 16)
which must NOT grow 2×. Also adjudicates the presumption that Z1..Z5 model
selection follows camera zoom (named `Z<n><S/W/N/E>`, never live-measured).

## §6 Art tables (decoded end-to-end, instruments in `tools/research/zots-decode/`)

- **80 S3D models**: `{T=0x5AD0E817, G=0xBADB57F1, I = base | zoomIdx<<8 | rotIdx<<4}`,
  zoomIdx 0–4 = Z1–Z5, rotIdx 0–3 = S/W/N/E, each self-naming in MATS/ANIM
  (e.g. `0fd10400_NoPower_Zot_Z5S`).
- **Textures**: FSH `{T=0x7AB50E44, G=0x1ABE787D}` in **SimCity_2.dat**, all
  single-entry 256×256 DXT1 atlases (27 distinct across the 80 models). Z5
  sprites are 123×151 px crops of `0x1E060400` (NoPower) / `0x1E060410` (NoCar) /
  `0x1E060420` (NoWater) / `0x1ED30400` (NoWork); all four Z1 sprites are ~6×9 px
  strips sharing atlas `0x1EE50010`. The MATS-embedded FSH id sits 8 bytes before
  the `21 00 02 00 <len>` name preamble.
- **LTEXT** `{T=0x2026960B, G=0x6A554AFD}` (SimCityLocale.DAT), carried by
  exemplar prop `0x8A416A99` "User Visible Name Key": `0xAA8C41B2` "No Power",
  `0xCA8C4185` "No Road Connection", `0x8A8C41CF` "No Water", `0x2A8C41ED` "No Job".
- **Exemplar props identified**: `0xAA1DD396` = OccupantGroups, value `0x5001` =
  literally **"Prop: Zot"** (siblings 0x5002 Stoplight … 0x5007 Construction);
  `0x09F00E59` = "Ignore lot state effects" (bool); `0xE9F0FA86` =
  "Self-illuminated" (bool).
- **Exactly four zots ship.** No radiation/flooded/mail variant exists: all 2,371
  group-`0xC977C536` exemplars (game+plugins), all 8,963 decompressed exemplars
  across SimCity_1..5+EP1, and a decompressed byte-scan of all 43,495
  group-`0xBADB57F1` S3Ds each yield only the four families.

## §7 Dead ends / open

- MATS numeric fields (the u32 after the leading count; the `FF 7F` pair) and the
  ANIM post-tag u32 remain unattributed — same residue as register #28.
- Which consumer reads the `{12,12,2}` footprint for zots (culling? occupant
  queries?) is undetermined; the render provably doesn't.
- Whether the tiny Z1/Z2 plate models are ever drawn (vs always the boxes) is
  unmeasured.
- `[[0xB43DD8]+0x10]` reads as the camera orientation feeding AddLotProp's
  `int32 orientation`; the field neighbors the proven zoom field +0xC but its
  exact semantic is inferred, not named.
- The zot-holder attribute interface (QI iid `0xC999C45E` on the building
  occupant) and message `0x4C04DE69` are mapped but unnamed.
- The drawer-host class's concrete name is still unresolved (row-13's standing
  gap, kind id `0x6818E5C9`).

## §8 Census row (as appended to SC4-WORLD-OVERLAYS.md §3)

See row 23 in the census table.
