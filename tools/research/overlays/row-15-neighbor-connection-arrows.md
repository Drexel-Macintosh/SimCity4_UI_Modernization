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

## 6. Dead ends and unknowns

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

## 7. Census row replacement (§3)

| 15 | neighbor-connection arrows at city edges | marker occupant from exemplar `{6534284A, C977C536, 29F10000}` "UI8x1x3_ConnectArrow" — OccupantSize {8,3,1} m + own S3D `{5AD0E817, BADB57F1, 29F10000}` + LTEXT "Neighbor Connection"; sole creator `push 0x29F10000` at 0x6D4A66 (fn 0x6D4860, +15.5f cases {3,7,0xB}); drawn via the renderer direct-read iid 0xE4FDA3D4 (QI 0x6CE260 → this+4). NOT effects / signpost quad / marker strip (`tools\research\overlays\row-15-neighbor-connection-arrows.md`) | n-a presumed (world-anchored, metres) — eyes-on/probe owed | PARTIAL |
