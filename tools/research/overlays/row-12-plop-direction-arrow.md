# Row 12 — plop direction arrow on a held lot — ATTRIBUTED (PARTIAL, static)

> **CURRENT GRADE: MEASURED** — confirmed live 2026-08-30.
>
> ⛔ **The dated header below is the ORIGINAL session's grade and is
> superseded.** It is kept rather than rewritten because this project
> annotates history instead of editing it — but the front door
> (`docs/DECOMPILATION-STATUS.md`) grade-scans the top of this file, so
> the line above is the one that counts. See the MEASURED section at the
> end of this file for what changed and how it was proven.

**Date:** 2026-08-17 · **Exe:** SimCity 4.exe 1.1.641.0 Steam x86, ImageBase 0x400000
**Verdict:** **Effects manager (§2.1) + EFFDIR (§2.2).** The held-lot direction
arrow is a named Swarm effect, `"Lot_Direction_Arrow"`, spawned by the Lot Plop
tool's preview-refresh function through `CreateEffectByName`, world-anchored,
zoom-gated to close zooms via three per-zoom child copies. **Grade: PARTIAL** —
every link below is byte-read from the shipped exe / a fresh EFFDIR extract,
but nothing has been seen on screen or in a live capture yet (the doc's law:
static = PARTIAL, say so).

## Evidence chain (every claim with an address)

1. **The name exists in the exe**: `"@Lot_Direction_Arrow"` at `.rdata`
   **VA 0xA90903** (file 0x690903). It sits in the placement-preview string
   cluster — `"selection_red"` 0xA908D8, `"selection_blue"` 0xA908E8,
   `"building_footprint_notok"` 0xA90920, `"building_footprint_ok"` 0xA9093D,
   `"Lot Plop"` file 0x6906E8 — not the UDI cluster.
2. **One code ref, skipping the `@`**: `push 0xA90904` at **VA 0x4C2A87**
   (`68 04 09 A9 00`), preceded by `push edi` (ppOut) at 0x4C2A86.
3. **The call is CreateEffectByName**: at **0x4C2A8E** `call [edx+0x1C]` with
   `ecx = ebp = [0xB43D1C]` (loaded at 0x4C2A70). The vtable at
   **.rdata 0xA9F264** has slot +0x1C = **0x5939B0** (= the byte-verified
   CreateEffectByName, §2.1) and slot +0x0C = **0x594A30** (= the §2.2 one-shot
   Init) — so `[0xB43D1C]` is the effects-manager service pointer and this
   virtual call lands in the exact function the BUBBLEFX/BUBBLEALL detour
   covers. **Expected census line: ret=0x004C2A91.**
4. **The owner function**: `__thiscall` starting **0x4C2090** (prologue
   `81 EC A4 00 00 00 55 8B E9`, preceded by `ret 0x10` at 0x4C208D). The same
   function spawns the rest of the held-lot preview family:
   `"selection_blue"` push at 0x4C2326, `"selection_red"` push at 0x4C2531,
   another spawn via `[0xB43D1C]` at 0x4C283D; it self-recurses at 0x4C2D45.
   This is the Lot Plop tool's preview-effect refresher.
5. **Rotation-only transform, no scale**: facing int read from `[esi+0x3C]`,
   4-way switch `cmp ecx,3 / jmp [ecx*4+0x4C2F10]` at **0x4C2B0D–0x4C2B1D**
   (jump table 0x4C2F10); angle = facing × **−π/2** (double at `.rdata`
   **0xA908F8** = −1.570795, `fmul` at 0x4C2BE7); sin/cos matrix built on the
   stack (0x4C2C01–0x4C2C80); transform blob delivered to the effect instance
   via `call [vt+0x20]` at **0x4C2CD3**, instance started via `call [vt+0x14]`
   at **0x4C2CDA**. **No write to instance scale (+0x110) anywhere** — ctor
   default 1.0 (0x5C047E) stands.
6. **No pixel constant on the path**: direct-call scan of 0x4C2090–0x4C2F10
   finds 10 distinct targets, NONE = the px→world helper 0x7F6690 (positive
   control: the scan does find the float helper 0x9EEF04 called at 0x4C2B05,
   which I disassembled). Constants used are −π/2, 2^32 (0xA80AA8, unsigned
   fixup), 0.5 (0xA84D2C), 6.0 (0xA90900) — all angle/index math.
7. **EFFDIR side** (fresh extract `tools\research\effdir\
   T-ea5118b0_G-ea5118b1_I-00000001.png`, TGI {EA5118B0, EA5118B1, 1}):
   - Name map entry at resource offset **0x109152**: `[len 0x13]`
     `"lot_direction_arrow"` `[u32 index 0x32]` → effect index 50.
     Map framing **[len][name][index-after]** proven by the doc's own anchor:
     `mission_selection_yellow` map entry at 0x107293 is followed by 0x47B,
     the §2.2 documented index. (Lookup must be case-insensitive: exe pushes
     `Lot_Direction_Arrow`, map holds lowercase.)
   - **Six child-reference records** (type 1 = model/sprite class, flags 0,
     identity rot, zero trans, **SCALE = 1.0**, ramps [0,1,1,1]):
     `lot_direction_arrow_z5` at 0xA6825 / 0xA689A / 0xA690F and
     `lot_direction_arrow_invert_z5` at 0xA6984 / 0xA6A00 / 0xA6A7C.
     The three copies per name differ ONLY in the byte pair at nameEnd+61/62:
     **(3,4), (4,5), (5,6)** — cross-checked against the
     `mission_selection_yellow` child (0x1027C4) which reads **(1,6)** = all
     six zooms, so the pair is the real zoomMin/zoomMax. The arrow is
     **zoom-banded to close zooms (~3–5/6; absent at 1–2)**; exact
     inclusive/exclusive semantics unadjudicated.
     NOTE: `build_mission_bubble_fx.py`'s prose layout puts zoomMin/Max at
     nameEnd+57/58 — on these records +57/58 read 0. The pair that varies is
     at +61/62. The builder's CODE only touches the SCALE float so the prose
     off-by-2 never mattered; do not patch zoom bytes from the prose layout.

## Dead ends / corrections (state the nulls with controls)

- **No S3D candidate**: `s3d-name-sweep.txt` (1,957 rows present = positive
  control) has ZERO names matching arrow/direction/compass. Correct null —
  the geometry comes from the effect's type-1 model/sprite class children,
  not a named S3D prop.
- **"lot_direction_arrow2" does not exist** — ASCII-scan artifact: the run is
  the 19-char map name + the low byte 0x32 ('2') of the index that follows.
- **No capture line yet**: 9 capture logs contain 360 BUBBLEALL lines, none
  `lot_direction_arrow`. NOT evidence of a different drawer: every log hits
  its 40-line cap during city load, and no capture session exercised the plop
  tool. (Positive control: the same hook logs `atmospheric_effects`,
  `natural_gas_smoke`, etc. from the same code family.)
- **Not chased (leads for other rows)**: `"@greenarrow"` `.rdata` 0xA97C4F is
  consumed via the .data name-pointer table (entry at **0xB09AF8**, table
  0xB09AE0, §2.1) — sits in the UDI/count_down cluster; possible candidate
  for census row 15 (neighbor-connection arrows) — unverified. EFFDIR also
  holds `green_arrow` (map idx 0x3DD area) and `level_arrow_select_{n,e,s,w}_
  {active,inactive}` (terrain-leveling arrows) plus the
  `preview_*` (network preview) and `*_coverage_circle_plop_*` families —
  the latter is the obvious opener for census row 11.

## Sizing

World units end to end: EFFDIR child SCALE 1.0 × instance scale 1.0 (never
written) → rendered at world scale, camera-zoomed, art swapped per zoom band.
No screen-px constant exists on this path. The only levers, if ever wanted:
the 6 child SCALE floats (resource offsets nameEnd+53: 0xA6870, 0xA68E5,
0xA695A, 0xA69D8, 0xA6A54, 0xA6AD0 — data route closed by the §2.2 load law)
or a BUBBLEFX-style post-spawn instance write (+0x110 scale, +0xDD |= 0x06)
name-filtered to `lot_direction_arrow`.

## Tier call

**STAY — world-anchored, n-a.** Same class as the hover quad (row 6) and grid
decals (row 7): the camera scales it with the terrain, so it is correct at
every UI tier by construction. It reads as world content, not pixel-fixed
furniture; do not patch.

## Live probe (to promote PARTIAL → DOCUMENTED)

Zero new code: arm the existing unfiltered CreateEffectByName census
(BUBBLEALL, detour on 0x5939B0), load a city, pick any ploppable building so
the held preview shows, rotate it once. Expect
`BUBBLEALL lot_direction_arrow ret=0x004C2A91 ok=1` (ret = the instruction
after the 0x4C2A8E virtual call). Positive control: the session's usual
city-load BUBBLEALL lines (e.g. `atmospheric_effects ret=0x0059406A`). Mind
the 40-line cap — plop BEFORE the cap fills, or raise the cap for the run.
An on-screen size check (optional second half): temporarily extend the
MissionBubbleFx hook filter to `lot_direction_arrow` with scale 2.0 — the
arrow doubling on screen is the model-predicts-measurement proof.
