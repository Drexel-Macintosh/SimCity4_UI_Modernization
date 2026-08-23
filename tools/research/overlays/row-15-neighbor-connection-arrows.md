# Row 15 — neighbor-connection arrows at city edges

**Date:** 2026-08-17 · **Grade: PARTIAL** (static disassembly + data attribution;
no screen or live-capture proof — the doc's evidence law forbids DOCUMENTED).
**Verdict: a marker OCCUPANT built from the `UI8x1x3_ConnectArrow` exemplar —
an S3D world model in metres, NOT an effect, NOT the signpost 44px quad, NOT
the marker strip.** Presumed world-anchored → n-a at scaled tiers; live proof
owed.

All VAs are ImageBase 0x400000, SimCity 4.exe 1.1.641.0 Steam x86 (LAA bit
flipped, code identical). All file offsets are into the named archives of the
9-archive discovered set.

## 1. The attribution chain (each step with its evidence)

1. **The exemplar.** `{T=0x6534284A EXMP, G=0xC977C536, I=0x29F10000}` in
   `SimCity_1.dat` (offset 111117434, 180 bytes; extract:
   `tools\dbpf\extracted-exemplars-SimCity_1\T-6534284a_G-c977c536_I-29f10000.png`).
   Exemplar name (prop 0x20, file offset 0x32): **`UI8x1x3_ConnectArrow_29F1`**.
   It is the ONLY `UI`-prefixed exemplar in the whole G=0xC977C536 group across
   all extracted archives (one-pass name sweep of every
   `extracted-exemplars-*/T-6534284a_G-c977c536_I-*.png`).
2. **Its properties** (hand-decoded from the 180-byte EQZB, offsets in file):
   - `0x27812810` (OccupantSize, float x3) at 0x4B, values at 0x58/0x5C/0x60 =
     **{8.0, 3.0, 1.0}** — the name's "8x1x3" in METRES (x, height, z).
     Bytes: `00 00 00 41 / 00 00 40 40 / 00 00 80 3F`.
   - `0x27812821` (model key RKT, u32 x3) at 0x64, TGI at 0x71 =
     **S3D {0x5AD0E817, 0xBADB57F1, 0x29F10000}**.
   - `0x8A416A99` (user-visible-name key, u32 x3) at 0x86, TGI at 0x94 =
     LTEXT `{0x2026960B, 0x6A554AFD, 0xEAABE73F}`.
   - bools `0x6A95E503` (0x7D), `0x8A5E5DB8`=1 (0xA0), `0xCAA9AB92`=1 (0xAA).
3. **The tooltip text names the feature.** The LTEXT
   `{0x2026960B, 0x6A554AFD, 0xEAABE73F}` lives in `SimCityLocale.DAT`
   (offset 345405, 42 bytes) and decodes (UTF-16LE after the 4-byte header) to
   **"Neighbor Connection"**. Verified by direct read this session.
4. **The model exists.** `find_tgi.py 29f10000` → `SimCity_1.dat
   T=0x5AD0E817 G=0xBADB57F1 I=0x29F10000, offset 140503203, size 244` (a tiny
   S3D — an arrow plate). It does NOT appear in
   `tools\research\effdir\s3d-name-sweep.txt` (grep `29f1` = 0 rows, grep
   `arrow` = 0 rows) — the sweep's own stated scope limit (names only; an
   unnamed or TGI-referenced S3D is invisible). Positive control: the sweep
   resolves same-T/G neighbors (`CasinoSign_RW8x16_Z5S` rows).
5. **The sole code consumer.** The instance id 0x29F10000 appears as an
   immediate at exactly ONE .text site: **`push 0x29F10000` at 0x6D4A66**,
   inside virtual function **0x6D4860** (prologue `8B 54 24 08 83 EC 0C 53 55
   56 57`). The push feeds `call [edx+0x3C]` on an argument object at
   0x6D4A6D — create-attachment-from-exemplar-instance. Before it, the
   function special-cases `edi ∈ {3, 7, 0xB}` (cmps at 0x6D4A36/3B/40) and
   adds **15.5f** (`fadd [0xAB1CA8]`, value read from the exe = 15.5) to the
   coordinate at [esp+0x14] — a WORLD-UNIT position nudge (which axis those
   three cases represent is NOT proven; recorded as observed).
6. **The owning class implements the renderer's direct-read drawable.** Fn
   0x6D4860 sits in the vtable run at .rdata 0xAB1EF8 (table base in the
   0xAB1CB0/0xAB1DD8 family; vtable installs at 0x6CF277 `mov [esi],0xAB1CB0`
   + [esi+4]=0xA80784, and 0x6CF292/0x6CF2F8 write 0xAB1DD8). The class QI at
   **0x6CE260** accepts iids {1, 0x0773FEF1, **0xE4FDA3D4**} and for
   0xE4FDA3D4 returns **this+4** (`lea eax,[ecx+4]` at 0x6CE284) — the exact
   idiom byte-proven for the marker family at 0x5E89D0 `[R:12018]`, where
   0xE4FDA3D4 = the interface the renderer QIs ~129x/frame from caller
   0x90E00D. So the arrow rides the SAME renderer direct-read draw lane that
   census row 1 is currently hunting.
7. **The marker factory reads the exemplar's size prop.** 0x4A24D0 (the
   marker factory/selector, `[R:11861]`) pushes property id **0x27812810** at
   0x4A25D3 — the very property this exemplar carries as {8,3,1} metres.
   ConnectArrow has NO 0x2977AA47 class-selector prop → it takes the
   factory's DEFAULT branch = the base marker class (ctor 0x5EE050,
   vt family 0xAA4900/0xAA4868, `[R:11861]`) — the same family whose vt1
   drawable the renderer consumes. The generic marker-exemplar fetch builds
   TGI {0x6534284A, 0xC977C536, ·} at 0x426E31/0x426E39.

## 2. Candidates RULED OUT (each null with its positive control)

- **Effects manager / EFFDIR.** The 1,094,484-byte EFFDIR extract
  (`tools\research\effdir\T-ea5118b0_G-ea5118b1_I-00000001.png`) contains NO
  neighbor/connection-arrow effect name. Positive control: the same scan finds
  406-record families incl. `mission_selection_*`, `tugropeconnection`.
  - `level_arrow_select_{east,west,north,south}_{active,inactive}` (10 copies
    each, 0xA238E–0xA4FED) looked promising (4 compass directions + states)
    but sits BETWEEN `mountain_tool_*` (0xA19A4), `valley_tool_*` (0xA1ABC),
    `flora_tool_*` (0xA51A3), `fauna_tool_*` (0xA53BF) records — it is the
    **god-mode terrain LEVEL tool** arrow family, not city-edge arrows. The
    name never appears in the exe (full-exe scan, 0 hits; positive control:
    the same scan finds `greenarrow`/`Lot_Direction_Arrow`).
  - `greenarrow` (0xA97C50) IS exe-referenced — from the UDI mission-effect
    name table 0xB09AE0, slot [6] at 0xB09AF8 (table also holds the five
    `mission_selection*` names + `count_down`) → it belongs to census ROW 8's
    UDI guidance family, not row 15. (Bonus fact for row 8's owner.)
    NOTE: the "@" seen before it in raw bytes is float 2π (0x40C90FDB), not
    part of the string; same for `Lot_Direction_Arrow` (preceded by 6.0f),
    which is referenced at 0x4C2A88 — row 12's family.
  - **Live spawn census null:** the unfiltered BUBBLEALL capture lines
    (9 logs, `_tests\captures\SC4UIScale-2026-08-17-18*.log` +
    `-REGRESSION-mayorhat.log`) contain no arrow-ish name. Positive control:
    81 `white_blinking_light_fast` + the 12-effect offer family are recorded.
    Scope: those runs were UDI scenes/city loads with a 40-line cap; a
    city-edge arrow spawn may simply never have been in frame — this null
    ALONE would prove nothing; it merely corroborates the data-side null.
- **Signpost quad (§2.3) / marker strip (§2.5).** The ConnectArrow visual is
  bound to its OWN S3D model by exemplar RKT — not composed from the 52px
  icon cells or the 64px disc strip. The signpost/composer family was
  live-proven 2026-08-17 to draw the POLE-BALLOON family (mayor-hat sign,
  dispatch lollipops) `[R:12084]`, and the marker-strip table 0xAA523C has a
  proven sole consumer 0x5F6067 `[R:11596]`. No pixel constant appears
  anywhere on the ConnectArrow path found here.
  The two-gap close did NOT happen: 0x4A24D0's "kind table" is
  the marker CLASS-selector switch on exemplar prop 0x2977AA47 (values →
  ctors 0x5EE050/0x5F0210/0x5EE360, already minted at `[R:11861]`), and the
  §2.3 signpost kinds table at [this+0x70] remains UNKNOWN — the SPTEX
  capture is the adjudicator for that gap.
- **Named S3D prop route.** No arrow/connection-named S3D in the 1,957-row
  sweep (grep = 0; positive control above). Explained by the TGI-referenced,
  unnamed 244-byte model — the sweep cannot see it, exactly per its scope
  note in the census §4 table.

## 3. SIZING — what numbers control the on-screen size

- **World units, from data, no code constant:**
  - the S3D model geometry `{0x5AD0E817, 0xBADB57F1, 0x29F10000}`
    (SimCity_1.dat offset 140503203, 244 bytes);
  - exemplar OccupantSize prop `0x27812810` = **{8.0, 3.0, 1.0} metres**
    (file bytes at 0x58/0x5C/0x60 of the 180-byte exemplar), read by the
    marker factory (push 0x27812810 at 0x4A25D3);
  - position nudge 15.5f at .rdata **0xAB1CA8** (fadd at 0x6D4A49, cases
    edi∈{3,7,0xB}).
- No screen-px immediate, no per-zoom table on this path (contrast: 44.0f at
  0x5F20AF; 0xAA523C). The camera therefore scales the arrow with zoom like
  any world object — **zoom-scaled by construction, tier-independent**.

## 4. TIER CALL

**Stay (world-anchored) — n-a at 1.5x/2x/3x, do NOT patch.** The size chain
is metres end to end. This is the census decision-tree case 3 outcome. If a
future eyes-on shows the arrow constant-size across zooms, this call is WRONG
and the drawer applies a screen-space normalization — re-open with the probe
below.

## 5. LIVE PROBE (the single cheapest adjudicator, since this is static-only)

One log-only naked hook at **0x6D4860** (prologue `8B 54 24 08 83 EC 0C 53 55
56 57` — verify bytes before install), logging `this`, `edi` (the 3/7/0xB
case selector), the xyz floats at [esp+0x10..0x18] after the 0x6D4A49 nudge,
and the out-pointer written by the [edx+0x3C] call.
- **Positive control:** load a city that HAS a road/rail touching the edge —
  expect exactly one line per visible edge arrow (count them on screen).
- **Negative control:** a city with zero neighbor connections — zero lines.
- **Sizing acceptance (no extra code):** with arrows on screen, measure one
  arrow at two adjacent zooms — world-anchored predicts ~2x per zoom step;
  pixel-fixed predicts equal px. The prediction-vs-measurement pair is the
  #188-law acceptance test.

## 6. THE S3D FORMAT — HAND-DECODE (register #28, 2026-08-23)

`SimCity_1.dat` reports this resource's on-disk size as 244 bytes (offset
140503203) — but the archive's compression directory (`DIR`, type
`0xE86B1EEF`) lists `{T=0x5AD0E817,G=0xBADB57F1,I=0x29F10000}` with declared
**uncompressed size 336**, and the 244 on-disk bytes carry the QFS/RefPack
header (`10 FB` signature at byte 4, 3-byte big-endian decompressed-size field
at bytes 6-8 = `0x000150` = **336**, agreeing with the `DIR` record
independently). **The 244-byte figure in §1.4/§3 above and in the register is
the compressed size; the format lives in the 336-byte decompressed buffer.**
Decompressed here with a direct Python port of the `QfsDecompress` already in
`tools\dbpf\DbpfExtract.cs`; reproducible via `python
tools\dbpf\decode_s3d_plate.py` (extractions saved alongside it in
`tools\dbpf\extracted-s3d\`).

All offsets below are into the **336-byte decompressed buffer**.

**Chunk chain** — a `tag(4 ASCII) + length(u32 LE, counts its OWN 8-byte
header + body)` header repeats end-to-end: for every chunk except `ANIM`, the
computed `body_end` lands exactly on the next tag's first byte with zero gap
or overlap — measured, not assumed:

| tag | @offset | declared len | body span | body (hex) |
|---|---|---|---|---|
| `3DMD` | 0 | *(no length field — see below)* | — | — |
| `HEAD` | 8 | 12 | 16–19 (4B) | `01000500` |
| `VERT` | 20 | 100 | 28–119 (92B) | *(see vertex table below)* |
| `INDX` | 120 | 30 | 128–149 (22B) | `01000000000002000600000001000200030000000200` |
| `PRIM` | 150 | 26 | 158–175 (18B) | `010000000100000000000000000006000000` |
| `MATS` | 176 | 75 | 184–250 (67B) | `01000000ab00000004030100ff7f0000000000010000e51e0303000021000200` + string |
| `ANIM` | 251 | **9301 — ANOMALOUS, see below** | real span 259–311 (~53B) | *(see below)* |
| `PROP` | 312 | 12 | 320–323 (4B) | `00000000` (empty) |
| `REGP` | 324 | 12 | 332–335 (4B) | `00000000` (empty — ends the file exactly at byte 335) |

- **Bytes 0-7**: magic `3DMD` (4 ASCII bytes) followed by an **unresolved**
  4-byte field (`68 25 00 00` = 9576 LE) that is NOT a chunk length (9576 >>
  336) — likely a version/type/model-id field outside the tag+len convention.
- **`HEAD` body** (4 bytes, `01 00 05 00`): two `u16` = `{1, 5}`, meaning
  unresolved.
- **`VERT` body** (92 bytes) — **fully decoded as a 4-vertex textured quad**:
  - `u32` @28 = **1** (a leading `=1` field recurs at the start of `VERT`,
    `INDX`, `PRIM` and `MATS` bodies — plausibly a per-chunk sub-record
    count, all `1` because this model has exactly one vertex/index/primitive/
    material group).
  - `u16` @32 = 0, `u16` @34 = **4** → **vertex count = 4**.
  - 4 bytes @36-39 (`01 40 00 80`) — unresolved (does not parse as a clean
    float32; not yet attributed).
  - **20× `float32` LE @40-119**, stride 20 bytes/vertex = 5 floats/vertex
    (X, Y, Z, U, V), confirmed by the paired-corner symmetry of a flat quad:

    | vtx | X | Y | Z | U | V | offset |
    |---|---|---|---|---|---|---|
    | 0 | 4.586182 | 14.457275 | 4.235352 | 0.993862 | 0.703125 | 40-59 |
    | 1 | −3.037231 | 14.457520 | 7.393311 | 0.980469 | 0.703125 | 60-79 |
    | 2 | −3.037354 | 1.753174 | 7.393311 | 0.980469 | 0.720982 | 80-99 |
    | 3 | 4.586304 | 1.753174 | 4.235596 | 0.993862 | 0.720982 | 100-119 |

    X, Y, Z and U each take exactly **two** distinct values shared by
    diagonally-paired corners — the signature of a flat rectangular plate,
    not an arbitrary mesh. (These are raw model-space coordinates; they were
    NOT tested against the exemplar's `{8,3,1}` m `OccupantSize` — different
    space, no claim of a match either way.)
  - **`INDX` body** (22 bytes): `u32` @128=1 (leading-1 pattern again), `u16`
    @132=0 / `u16` @134=2 (unresolved pair), `u16` @136 = **6** → index
    count, then **6× `u16` indices @138-149 = `[0,1,2,3,0,2]`** — two
    triangles, `(0,1,2)` and `(3,0,2)`, i.e. the quad split on the 0–2
    diagonal. Consistent end-to-end with `VERT`'s 4 vertices.
  - **`PRIM` body** (18 bytes): `u16` sequence `[1,0,1,0,0,0,0,6,0]` — the
    `6` at offset 172 matches `INDX`'s index count; the remaining fields
    (plausibly primitive-type / material-index / first-index) are
    unresolved.
  - **`MATS` body** (67 bytes): `u32` @184=1 (leading-1 pattern), `u32`
    @188=171 (`0xAB`, unresolved), 24 unresolved bytes @192-215 (a `FF 7F`
    byte pair @196-197 is *suggestive* of an alpha/blend value but
    unconfirmed), then a **1-byte length prefix `0x22`=34 @216** immediately
    followed by a **34-character un-terminated-until-next-byte ASCII string
    @217-249**: `"29F10000_ConnectArrow_Ui8x1x3_Z1S"` (the model's own hex
    instance id + the exemplar family/zoom/orientation name), then a NUL
    @250. This is an independent, in-file confirmation of the TGI
    attribution in §1 above — the model names itself.
  - **`ANIM` — the one anomaly.** The `u32` immediately after the tag
    (`55 24 00 00` @255-258 = 9301) does **not** fit the tag+len convention
    that holds exactly for every other chunk in this file (only ~53 bytes
    remain before `PROP` @312, not 9301−8). Whether this field means
    something else entirely for `ANIM` records (a different unit, a
    hash/type id) or is simply wrong is **undetermined** — flagged, not
    guessed at. The real ~53-byte body decodes cleanly regardless: `u16`
    @259=1, `u16` @261=30, `u32` @263=3, 6 zero bytes @267-272, `u16`
    @273=1, then a **`u16` length prefix @275=27** followed by a
    **27-byte NUL-terminated string @277-303**: `"ConnectArrow_Ui8x1x3_Z1S_0"`
    (same family name + a `_0` take/frame suffix), then 8 more zero bytes
    @304-311.
  - **`PROP`/`REGP`**: both empty placeholders (4 zero-byte bodies each);
    `REGP`'s body ends at byte 335, the last byte of the file — the chunk
    chain tiles the entire 336-byte buffer with no slack.

**What this settles for register #28**: a real, byte-cited partial decode of
the Maxis S3D chunk format (`3DMD`/`HEAD`/`VERT`/`INDX`/`PRIM`/`MATS`/`ANIM`/
`PROP`/`REGP`, 8-byte tag+length headers, a recurring leading `=1` sub-count,
a 4-vertex/6-index/1-primitive/1-material textured quad) from one concrete
instance. **Not decoded**: the `HEAD` body's second field, the `VERT` body's
unresolved 4 bytes before the float array, most of `MATS`'s numeric fields,
and — the standout anomaly — what `ANIM`'s post-tag `u32` actually encodes.
No general S3D reader/writer exists yet; this is one instance's fields, not a
schema proven across other S3Ds.

## 7. Dead ends and unknowns

- The meaning of edi ∈ {3,7,0xB} (network types? edges?) — unproven.
- The owning class's NAME: `cSC4NeighborConnection` exists at .rdata 0xA896B0
  but has NO pointer xref anywhere in the file (whole-file scan; positive
  control: `greenarrow`'s pointer found at 0xB09AF8) — GZCOM name strings
  here are not pointer-referenced, so the identification "this class = the
  neighbor-connection object" rests on the tooltip + sole-consumer chain, not
  on a name match.
- Whether hover/click on the arrow resolves via §2.4's pick or via the 16m
  cell fallback (0x4D78ED) — untested.
- vt slot index of 0x6D4860 within its exact vtable base (the 0xAB1CB0 vs
  0xAB1DD8 table boundary was not pinned precisely).

## 8. Census row replacement (§3)

| 15 | neighbor-connection arrows at city edges | marker occupant from exemplar `{6534284A, C977C536, 29F10000}` "UI8x1x3_ConnectArrow" — OccupantSize {8,3,1} m + own S3D `{5AD0E817, BADB57F1, 29F10000}` + LTEXT "Neighbor Connection"; sole creator `push 0x29F10000` at 0x6D4A66 (fn 0x6D4860, +15.5f cases {3,7,0xB}); drawn via the renderer direct-read iid 0xE4FDA3D4 (QI 0x6CE260 → this+4). NOT effects / signpost quad / marker strip (`tools\research\overlays\row-15-neighbor-connection-arrows.md`) | n-a presumed (world-anchored, metres) — eyes-on/probe owed | PARTIAL |
