# Row 8 — orange/green mission guidance arrows (UDI drive mode)

**Session 2026-08-17, subagent attribution pass. Grade: PARTIAL (static
disassembly + data decode; nothing here is screen-proven yet — the minted
law says only a live capture or eyes-on promotes this to DOCUMENTED).**

All VAs are 1.1.641 Steam image-base 0x400000, read from the shipped exe this
session with `tools\research\disasm_at.py` and scratch byte-scans. All TGIs
were read from the shipped archives (QFS-decompressed with
`tools\uimap\emu\qfs_ab.py`) this session — nothing below is CARRIED.

## 1. What "bubblefsh sheets 21-26" actually is (the [R:11496] shorthand decoded)

The literal string `bubblefsh` exists NOWHERE — not in the exe (byte-scan of
the whole image for `[Bb]ubble`: zero hits) and not in any of the archives
(full 9-archive, every-entry, raw+QFS scan for `bubblefsh`: zero hits;
positive control: the same scanner found `4bb0ecf3_driving_bubble` and 5
other `bubble` strings). It was the session's shorthand for a family of
FSH-content sheets that live in the "mission bubble" icon group:

- **The art: six 128x128 32-bit (FSH code 0x7D) sheets, instances
  `0x6BE09921..0x6BE09926`** — "sheets 21-26" = the instance low byte.
  They ship TWICE:
  - `{856DDBAC, 46A006B0, 6BE09921..26}` in **SimCity_1.dat** — stored under
    the PNG type id but the payload is SHPI/FSH (the extractor's
    `PngMagic=no` rows in `tools\dbpf\extracted-png-tgi.csv`);
  - `{7AB50E44, 1ABE787D, 6BE09921..26}` in **SimCity_2.dat** — proper FSH
    type. **The exe consumes THIS copy** (type/group imms at the load site,
    §2 below).
- Decoded content (this session, PNGs in scratch): 21/23/25 = ORANGE,
  22/24/26 = GREEN twins. 21-24 = curved arrows (mirrored pairs, 2129 opaque
  px), 25/26 = straight arrows (1906 opaque px). Exactly the row-8 visual.
- Group 0x46A006B0 is the same group the signpost/marker composer takes its
  icon PNGs from; the neighbours are `4bb0ecf3_driving_bubble`,
  `144161A3_dispatch_mysim_tinyheadbubble`, `14315E00..` fire-dispatch
  sheets — which is why the balloon-era session met them and wrote the
  "bubblefsh" shorthand.

## 2. The DRAWER (the thing row 8 said was unfound)

**Owner: the U-Drive-It DRIVING view-input control — a lazily-created
singleton at `.bss [0xB21D74]`.** Chain, all byte-read this session:

- **Getter/factory `0x506850`** (2 stack args): allocates **0xC0** bytes
  (`push 0xC0` at 0x50685D → 0x5E55E0), calls ctor, stores to `[0xB21D74]`.
  Callers: `0x437411`, `0x50DF04`, `0x524E7F`, `0x5252EA` (message/dispatch
  code; `0x50DF04` sits in a dispatcher comparing message ids `0x0B70C96D`
  / `0xCC478B79` at `0x50DE7E`/`0x50DF1C`).
- **Ctor `0x565480`**: vtables **`0xA9D9B0`** (+0), **`0xA9D9A0`** (+0x28),
  **`0xA9D98C`** (+0x2C); base-class ctor `0x5FB320`. The +0x2C vtable
  shares 13 base implementations (`0x5FB020/0x5FB070/0x5FB0B0/0x5FB0E0/
  0x5FB170/0x5FB260/0x517F70/0x989960/0x40CE70/0x648EF0/0x648F00/0x5DEB40/
  0x407990`) with the UDI OFFER control's vtable `0xA901A0` — same
  view-input-control family (this also corroborates the §2.4 CARRIED
  `0xA901A0` as far as family membership).
- **Owner Init = vtbl `0xA9D98C` slot 12 = `0x565A10`**: reads services
  `[0xB43CF4]` (float via vt+0x18 → this+0x6C, and `1.0f/x` → +0x70),
  creates the **arrow drawer** via **ctor `0x5649D0`** → stored at
  **owner+0x9C** (0x565D52-0x565D79), calls the drawer's one-shot resource
  init **`0x5633C0`** (sole caller `0x565D7F`), then REGISTERS the drawer
  with a QI'd service: `call [vt+0x80](drawer, 5, 0x3E8)` at `0x565D98`.
- Mission code consumes the singleton: `mov ecx,[0xB21D74]` at **`0x52E393`**
  (tests owner+0x30) — the same 0x52Exxx mission-situation region as the
  in-mission glow caller `0x52E8AE` (§2.1). UDI territory, not tutorial.

**Drawer object (ctor `0x5649D0`)**: vtables **`0xA9D974`** (+0) /
**`0xA9D95C`** (+4); fields: +0xC init flag, +0x1C..0x28 = -1 latches,
**+0x2C..0x40 = the SIX arrow textures**, **+0x44/+0x48 = the TrainSwitch
S3D models**. Likely per-frame draw = vtbl slot 3 `0x5657A0` (walks a
row/col range obtained from service `[0xB43CEC]` vt+0xA0 — reads like a
visible-cell walk; INFERENCE, not byte-proven semantics).

**Resource init `0x5633C0`** (one-shot on flag this+0xC; prologue
`81 EC A4 00 00 00 55`):

- Touches `[0xB43DD0]` (vt+0x28) — **independently corroborates the §2.4
  CARRIED render-service slot `0xB43DD0` as a live service pointer.**
- Builds a 4-point template on the stack (`0x56340E–0x563481`): vec3
  components only **0 / 8.0f / 16.0f** (imm32 `0x41000000`/`0x41800000`) —
  8/16 = half-cell / one-cell in WORLD units (16 m = one tile; same unit
  convention as the §2.4 hover quad, [R:11350]). Loop `0x5634A0–0x563543`
  writes **table[j][i] = normalize(P[i]−P[j])** into the **.bss 4x4 vec3
  table at `0xB229B8`** (`0xB229C0` = its second float; the exe image holds
  no initial data — runtime-written only). Read back at **`0x564B43`**
  (`lea eax,[eax*4+0xB229B8]` after (a*4+b)*3 indexing) inside the
  path/direction fn `0x564A60`.
- QIs the texture manager at `0x56355A` with iids
  **{0x1AC0E11A, 0xFAC0E219}** (same pair the region cloud emitter uses,
  `SDK-GAPS.md` §10.1), then **loads the six sheets by TGI
  `{7AB50E44, 1ABE787D, 0x6BE09921..26}`** via vt+0x18 →
  **this+0x2C..0x40**. Sites (sole refs to these ids in the whole image):
  `0x563587, 0x5635A9, 0x5635CB, 0x5635ED, 0x56360F, 0x563631`.
- Then loads TWO S3D models `{5AD0E817, BADB57F1, 0x8BB70000/0x8BB80000}`
  via `0x7FEDE0` → this+0x44/+0x48. Their FSH twins are named
  **`8bb70000_TrainSwitch_Normal` / `8bb80000_TrainSwitch_Depressed`** —
  this is the very code §2.5's dead-end list met as "the TrainSwitch pair
  at `0x563572`" [R:11573] (0x563571 is the `mov edi,0x7AB50E44` type-imm
  right before the first arrow-sheet store). The dismissal was correct for
  the BALLOON; the same function is the row-8 drawer's loader. The UDI
  drive furniture (guidance arrows + rail levers) loads in one place.

## 3. Sizing semantics

- **No screen-px constant on the path.** The loader/drawer never calls the
  px→world helper `0x7F6690` (its call targets are only `0x8793EC`,
  `0x7D2B50`, `0x7FEDE0`, `0x4495C0`; positive control: the signpost
  builder `0x5F20A0` DOES call `0x7F6690`).
- Geometry derives from the 8/16 world-unit template → the `0xB229B8`
  direction table; textures are 128x128 world-mapped sheets. Everything on
  the path is **world units → world-anchored**, the same class as the zone
  decals (row 13) and hover quad (row 6).
- If a size lever is ever wanted: the template imms at
  `0x56341E–0x563481` (world growth — footprint widens with it), or 2x art
  under `{7AB50E44,1ABE787D,6BE09921..26}` for crispness only (standard
  resource path — data-overridable, unlike EFFDIR).

## 4. Tier call

**Stay (n-a, world-anchored) — predicted, not yet screen-proven.** At
1.5x/2x/3x the arrows keep their world footprint like all world content;
they are guidance paint on the road, not screen furniture. No patch.

## 5. Nulls, with positive controls

- BUBBLEALL (unfiltered CreateEffectByName census, 2026-08-17 captures):
  **no arrow-family effect name ever spawned** (positive control: 16
  distinct names logged in the same captures, incl. `mission_selection_red`
  on a click [R:11568]). Weak null — no UDI mission was DRIVEN in any
  captured session — but moot: the drawer found consumes textures directly,
  not via the effects manager.
- exe ASCII scan: no `bubble`/`bubblefsh` string (positive control: the
  same scanner finds the `mission_selection` prefix family).
- `s3d-name-sweep.txt`: no arrow-named S3D (positive control: 1,957 named
  rows; the TrainSwitch S3Ds are also absent from the sweep — the sweep
  missed `{5AD0E817,BADB57F1,8BB7000x/8BB8000x}`, worth knowing before
  trusting other sweep nulls).
- EFFDIR extract: no arrow record consulted — not needed once the direct
  code path was found.

## 6. Live probe (verification procedure)

Log-only naked hook on **`0x5633C0`** (one-shot; fires at most once per
control lifetime). Log: this-ptr, then after-original the six dwords at
this+0x2C..0x40 (nonzero = textures resolved) — tag `ARROWTEX`.
Positive control: start a U-Drive-It DRIVING mission and get route guidance
on screen — the line must print BEFORE the first arrow appears, six
nonzero slots. Negative control: plain mayor view, no line. If arrows are
ON SCREEN and the line never printed → this attribution is REFUTED (the
SPQUAD lesson; do not patch past a dead probe). Optional dev-only kill
test after the log passes: skip loading sheet 25/26 → straight arrows lose
their texture on screen = consumer proven pixel-for-pixel.

## 7. Dead ends this session

- `bubblefsh` as a literal name: does not exist anywhere (see §1).
- Tutorial arrow Lua (`tutorial_draw_arrow_at`, kDRAW_ARROW_FOR_WINDOW=16,
  SimCity_1.dat G=4A5E8EF6 I=FF263B45 etc.) — a DIFFERENT arrow system
  (window-relative tutorial pointer), not row 8; recorded here so nobody
  chases it for this row again.
- The six sheets' PNG-typed twins in group 46A006B0 are NOT what the code
  loads (the exe imms name type 7AB50E44 group 1ABE787D); art overrides
  must target the FSH-typed copy in SimCity_2.dat.
