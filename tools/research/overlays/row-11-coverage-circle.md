# Row 11 — coverage-radius circle while placing civic buildings

**Session 2026-08-17. Attribution: EFFECTS MANAGER (§2.1). Grade: PARTIAL
(static disassembly + EFFDIR data; no live capture of a `PlopMode` spawn yet
— see LIVE PROBE). All VAs are static ImageBase 0x400000 VAs, bytes read from
the shipped Steam 1.1.641 exe this session.**

## VERDICT

The circle is a **named effect** spawned through `CreateEffectByName`
(`0x5939B0`, §2.1) — NOT a renderer decal of its own subsystem and NOT
tool-preview geometry. Effect names: **`PlopMode_<Family>_{Plop, Inactive,
Existing}`** (Family ∈ Police, Fire, Health, Education), resolved
case-insensitively against the EFFDIR name map (stored lowercase). The circle
geometry itself is the EFFDIR child family **`<family>_coverage_circle_*`**
(type-1 model/sprite children, file scale 1.0). Two independent spawn paths:

1. **Held-tool preview** (the circle under the ghost building): the
   plop-preview controller (methods `0x4BEF00`–`0x4C2900`).
2. **Existing-building circles** (shown over already-built stations/schools
   while the same tool is held): the loop at `0x7D21xx` + helper `0x7D1E40`.

## EVIDENCE

### Exe strings + their single consumers (byte-read this session)
- `.rdata` strings: `PlopMode_Police_Plop` @ `0xA90860`,
  `PlopMode_Police_Inactive` @ `0xA90844`, `PlopMode_Fire_Plop` @ `0xA90830`,
  `PlopMode_Fire_Inactive` @ `0xA90818`, `PlopMode_Health_Plop` @ `0xA90800`,
  `PlopMode_Health_Inactive` @ `0xA907E4`, `PlopMode_Education_Plop` @
  `0xA907CC`, `PlopMode_Education_Inactive` @ `0xA907B0`;
  `PlopMode_Police_Existing` @ `0xABB4B0`, `_Fire_` @ `0xABB498`,
  `_Health_` @ `0xABB47C`, `_Education_` @ `0xABB460`.
- Each `_Plop`/`_Inactive` string has exactly ONE .text ref, all inside the
  initializer `0x4C0680`: Police pair pushed at `0x4C0920`/`0x4C094F`, Fire
  `0x4C09D0`/`0x4C0A00`(≈`0x4C0A12`), Health `0x4C0A8A`/`0x4C0AB9`,
  Education `0x4C0B47`/`0x4C0B76`. Names stored into controller members
  **+0xC4 (Plop)** and **+0xB0 (Inactive)** via string-assign `0x424380`.
- Each `_Existing` string has exactly ONE ref, in the `0x7D21xx` loop
  (Police push at `0x7D2206` etc.), passed to helper `0x7D1E40`.
- ⛔ `plopmode`, `coverage_circle` do NOT appear in the exe — the lowercase
  forms live only in the EFFDIR name map (lookup is case-insensitive).

### Spawn = CreateEffectByName, both paths
- Effects-manager service pointer = global **`[0xB43D1C]`**; its interface
  vtable is **`0xA9F264`** (written by ctors `0x58FA70` / `0x5912F6`, both in
  the §2.1 effects-manager code region); slot **+0x1C** = entry `0xA9F280` =
  **`0x5939B0` CreateEffectByName** — the ONLY reference to `0x5939B0` in the
  whole image (single .rdata hit), so any `call [vt+0x1C]` on this service IS
  CreateEffectByName.
- Held-tool spawn: **`0x4C1710`** `call [eax+0x1C]`, ecx=`[0xB43D1C]`, args =
  (name c_str of member +0xB0/+0xC4, ppOut=&this+0xD8) — the doc's exact
  2-stack-arg signature. Instance pointers kept in members **+0xD8/+0xDC**
  (teardown method `0x4C0090` stops via vt+0x10(0)/releases both).
- Existing-path spawn: **`0x7D2015`** `call [eax+0x1C]`, ecx=`[0xB43D1C]`
  (sole `0xB43D1C` ref in the helper, at `0x7D1F93`), inside helper
  `0x7D1E40` which took (occupant, radius, name).

### EFFDIR data (rescued extract `tools\research\effdir\T-ea5118b0_G-ea5118b1_I-00000001.png`)
- Name map entries (format `[u32 len][name][u32 index]`):
  `plopmode_police_inactive`=0x33 @ file offset 0x104643,
  `plopmode_police_plop`=0x34 @ 0x104B7F, `plopmode_police_existing`=0x35 @
  0x1077DA, `plopmode_fire_existing`=0x38 @ 0x103CD0,
  `plopmode_education_plop`=0x3D @ 0x103710. (⚠ raw string scans show these
  names with a trailing "digit" — that is the LE index byte, e.g. 0x34='4',
  not part of the name.)
- Child records (doc §2.2 layout, parsed): e.g.
  `police_coverage_circle_plop_existing_normal` @ 0xA6D56,
  `police_coverage_circle_inactive_normal` @ 0xA6B18,
  `education_coverage_circle_plop_existing_normal` @ 0xA7B26 — all **type 1**
  (model/sprite class), flags 0, identity rot, translation (0,0,0), **file
  SCALE 1.0**, zoomMin/Max 0/0, zoom ramps (0.0, 1.0, 1.0, 1.0). Full family:
  {data, education, fire, health, police} × {existing, inactive,
  plop_collapse, plop_existing} × {normal, invert} (data has only
  existing_*). The normal/invert pair matches the renderer's
  `decalIgnoreDepth`/`decalInvertDepth` string family (`.rdata` file offsets
  0x69F44C/0x69F460) — depth-handling variants of one ground-projected decal.

### SIZING — where the number comes from
- Radius member = controller **+0x120**. Written in initializer `0x4C0680`:
  a coverage query `call [vt+0x50]`(occupant, 0.5f, &out+0x11C, &out+0x120)
  at **`0x4C0913`**; on failure the fallback **32.0f** (`C7 03 00 00 00 42`)
  is written at **`0x4C091A`**. Same query+fallback in the existing path at
  `0x7D21F0`/**`0x7D21F7`** (`mov [esp+0x14], 0x42000000`).
  (The radius ultimately comes from the building exemplar's coverage
  properties via that vt+0x50 interface — interface identity not chased;
  candidate ids pushed nearby in the initializer: 0x029244DB, 0x29F013E6 @
  `0x4C085C`/`0x4C0873`, unadjudicated.)
- Delivery, held-tool path (update method `0x4C2660`): guard `radius > eps`
  (fcomp against qword `[0xA80990]` at `0x4C26C7`); builds identity 3x3 on
  the stack; **doubles the radius — `fld [esi+0x120]; fadd st,st(0)` at
  `0x4C2701`/`0x4C270F`** (diameter), stores it as the transform's scale
  float `[esp+0x78]`; sets the §2.1 flag byte (bit0|bit1, `0x4C2778`,
  struct tag byte 2 at `0x4C2790`); hands the block to the effect instance
  via **`call [vt+0x20]`** at **`0x4C2798`**; starts it via vt+0x0C if not
  running (`0x4C27B4`). Second instance (+0xDC) same pattern at
  `0x4C27C6`ff.
- Existing path: helper `0x7D1E40` doubles the radius arg the same way
  (`fadd st,st(0)` at **`0x7D1EF4`** → `[esp+0x58]`), fills the same
  transform block (identities at `0x7D1FA0`–`0x7D2008`), then spawns.
- So: **on-screen size = EFFDIR child scale (1.0) × instance transform scale
  (= 2 × exemplar coverage radius) in WORLD units**, projected by the camera
  — the §2.1 activation chain (`0x5919D0` multiplies instance scale into
  every child spawn) does the rest. No screen-px constant anywhere on the
  path. Prediction the probe can check: a missing-property building draws a
  64 m (4-cell) diameter circle (2 × 32.0 fallback).

## TIER CALL

**Stay (world-anchored) — n/a at every tier, never patch.** The circle's
meaning is "these world cells are covered"; its size is derived from world
units end to end and scales with the camera, exactly like the §2.4 hover
quad. A tier multiplier here would make the circle LIE about coverage.

## LIVE PROBE (owed for DOCUMENTED)

Cheapest: **widen the existing BUBBLEALL census filter** (the `0x5939B0`
detour, `src\CodePatches.cpp:4305/4354` — already shipped) to also log names
starting `PlopMode` (or just rely on BUBBLEALL unfiltered mode if that is
what BUBBLEALL already is — then the probe is purely a CAPTURE, no build).
Positive control: pick up the police-station tool in mayor view →
one `PlopMode_Police_Plop` (+`_Inactive`) spawn logs immediately, plus one
`PlopMode_Police_Existing` per station in the city; drop the tool → no more
lines. To also prove sizing live, log `[instance+0x110]` one frame after a
`PlopMode` spawn — expected value = 2× the building's coverage radius
(64.0 exactly if the exemplar lacks the property). Existing captures are a
TRUE NULL with a stated scope limit: all nine 2026-08-17 BUBBLEALL captures
(40 lines each, cap) contain zero `PlopMode` lines because no placement tool
was held during those runs — their positive control (heli/region ambient
spawns) is present in every one.

## DEAD ENDS / NULLS (with positive controls)

- `radius|civic|school|range` find no effect names in EFFDIR (positive
  control: the same scan lists all 40 `*_coverage_circle_*` names).
- No `coverage_circle`/`plopmode` string in the exe (positive control: same
  scan finds the 12 `PlopMode_*` mixed-case strings).
- No direct E8 call to `0x5939B0` anywhere in .text (positive control: the
  scanner found the vtable route; the doc's §2.1 call-site list is
  return-address-based, i.e. also vtable calls).
- `s3d-name-sweep.txt` has no coverage-circle model name — consistent with a
  code-referenced EFFDIR child, not a lot prop.
