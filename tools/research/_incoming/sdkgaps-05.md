# TARGET: PRIMARY: `tools\research\BUDGET-DETAIL-ANATOMY.md` — new **§7. THE ROW WINDOWS (the harness's UNKNOWN-STOCK class)**, inserted after §6 DEAD ENDS and before §POPUP. Three secondary blocks: (B) `tools\research\SC4-UI-ENGINE.md` widget catalogue — the `+0x100` outer/inner pair; (C) `tools\research\_checkpoints\uimap-stage4-diff.md` — rewrite of FINDING 5 and of NEXT ACTION 2; (D) `tools\uimap\diff\RESUME.md` §"What is still missing" — the art-rect oracle.

## SUMMARY
All 45 "unjudgeable" windows are identified and 32 of them now have exact stock rects. The 35 under `0x0423278F` are NOT "all 32x32" (contradicts FINDING 5): the surviving capture holds 12 checkbox cells (32x32), 12 four-state ordinance ROW STRIPS (2640x36), 4 scroll arrows (128x20), 2 Accept/Cancel (360x60), the content pane and the popup — 32 enumerated, 3 unrecoverable because the v2.28.1 log is gone. Their ids are not "per-row generics with no identity": they are two literal ID BASES in the exe, `mov [esp+0x3c],0x12C` and `mov [esp+0x24],0x1F4` at 0x77C670/0x77C678, plus a general engine law — every window built through `sub_77B960` appears at **id+0x100** (outer) with the raw id as its child, proven twice inside the exe itself (0x77D330 vs 0x77D350; 0x78BAC1 vs 0x78BADD) and twice live. Stock geometry for all of them is ART-derived, so it comes from PNG IHDR headers, not from any layout emulator — which corrects the checkpoint's NEXT ACTION 2. Every group is measurably correct at 2x today; two rows (arrow y, Accept x) are correct-by-patch but not yet confirmed by a live 2x rect. The single artifact that retires the class is a generated `tools\uimap\art-rects.json` (art TGI → stock/shipped IHDR + create-type cell divisor), NOT a new game session.

## CONTRADICTIONS
- FINDING 5 in `_checkpoints\uimap-stage4-diff.md` says the 35 windows under 0x0423278F are 'all 32x32'. MEASURED: only 12 are 32x32; 12 are 2640x36 (row strips), 4 are 128x20 (scroll arrows), 2 are 360x60 (Accept/Cancel), 1 is 900x754 (content pane), 1 is 840x125 (popup). Evidence: `_checkpoints\pds-cache\SC4UIScale-snapshot.log:373-404`, 32 distinct (id, vt, rect) tuples under that parent.
- FINDING 5 says 'their ids are per-row generics appearing in no .UI script under a stable identity'. MEASURED: they are two literal exe id bases — `mov [esp+0x3c],0x12C` @0x77C670 and `mov [esp+0x24],0x1F4` @0x77C678 — incremented per row, plus the +0x100 outer/inner law. The identity is fully stable and derivable offline.
- FINDING 5 / NEXT ACTION 2 say stage 3 emitting rects 'should convert ~35 UNKNOWN-STOCK rows'. It cannot: for these windows the exe supplies only x and y; w and h are the ART's dimensions. A layout emulator cannot produce 2640x36 because that number is a PNG IHDR field. The art table, not the emulator, is the missing oracle.
- FINDING 8.4's 'the stock-budget PNGs are never opened — deliberate ... which is part of why finding 5's 35 unknowns exist' conflates two different PNG sets. The ten stock SCREENSHOTS are indeed not rect sources; the ART PNGs are, and reading their IHDR is exact integer geometry, not pixel counting. Keeping the art closed is what left the 35 unjudgeable.
- `BUDGET-DETAIL-ANATOMY.md` §4's note on the ordinance-name clamp — '[the 127 clamp] still clears the measured eye (ends ~104) by 23px' — was screenshot-inferred. MEASURED from the art alpha: the eye ink occupies x=4..25 of the 330-wide cell, so at 2x it ends at 68+51 = 119 and the clamp clears it by 8px, not 23. Still clear (stock gap is 9px, so the clamp actually preserves the stock proportion), but the recorded number is wrong.
- `BUDGET-DETAIL-ANATOMY.md` §1 says 'one slab art = TWO rows' without stating the odd case. MEASURED on two independent sections in one dialog: slabs = floor(rows/2) (3 rows -> 1 slab of 36; 9 rows -> 4 slabs of 144), with the row counts clamped to 9 at 0x77C829. That is the only decomposition that reproduces both the 100px inter-section gap and the 377px dialog height.
- `BUDGET-DETAIL-ANATOMY.md` §2 records the +0x100 as a local quirk of the four scroll arrows ('exe ids 0x451-0x454 +0x100 at runtime'). It is a general engine law for every `sub_77B960` create, proven inside the exe at two unrelated sites (0x77D330/0x77D350 and 0x78BAC1/0x78BADD) and live for four id pairs. It belongs in SC4-UI-ENGINE.md, and it silently breaks any raw-id join between builders.json and a live tree.

## OPEN
- Two rows of the §7.2 table are correct-by-patch but have never been seen live at 2x: the four scroll-arrow Y values (expected 112/400/312/600 after `kBudgetLeaDisp8Sites` 4->8, v2.29.0; the only capture shows the unpatched 108/396/308/596) and Accept's x (expected 28 after `{0x77D31F,0x0E}`, v2.29.0; the only capture shows 14). One post-v2.29.0 log with the Ordinances dialog open confirms or refutes both.
- Does the budget Accept/Cancel plate render with 1x chrome? `0x144161EB` is SHARED (refmap.csv:216, clone+retarget to group 0x470261EA), so it does not ship 2x in place, and the six hardcoded `push 0x144161EB` sites (0x77D316, 0x77D497, + twins) have no CodePatches retarget. The window is code-sized 360x60. Cheapest check needs no build: compare border thickness in `stock-1024-131917.png` against a 2x shot.
- Does slabs = floor(rows/2) generalise to the other four department families, or is it specific to the Ordinances stacker `sub_77A480`? One BHDR capture of any slider department settles it and would also validate the whole §7.3 height formula as a predictor.
- Where exactly does the +0x100 get applied? Neither `sub_77B960` nor `sub_77B7B0` adds it; both pass the raw id to the window manager's create (`call [vt+0x28]`, type 2 vs type 4). The offset lives inside the type-2 create path. Not load-bearing for any fix, but it is the last unexplained step in BLOCK B's law.
- The three unrecoverable windows of the original 35. They can be re-observed rather than reconstructed: open the master budget plus one slider department together (both share id 0x0423278F and both are open at once, per UiSpike.cpp:8335-8339) with the log kept.
- No `BHDR` line survives in any log on this box, so the content pane's children (title 0xABCDE00, headers 0xABCDE01/02, per-row names 0xABCDE03+k at the clamped x=127, and the value column) have zero measured 2x rects even though `parse_log.py` already parses and attributes them. That is the second-largest blind spot after the art table, and it is one capture away.

---

================================================================================
BLOCK A — for `tools\research\BUDGET-DETAIL-ANATOMY.md`, NEW §7
(place after §6 DEAD ENDS, before §POPUP)
================================================================================

## 7. THE ROW WINDOWS — what the diff harness calls UNKNOWN-STOCK

§1-3 decode the bands, the columns and the four sizing regimes. What was never
written down is the CONTENTS of a department dialog: the per-row windows the
builder creates in a loop. `tools\uimap\diff` reports 45 live windows no oracle
can judge and 35 of them are these. They are not anonymous and they are not
generic — the whole set is generated from two literal ID BASES and one engine
convention, and every one of their stock rects is recoverable offline.

### 7.1 The two id counters

    0x77C670   c744243c 2c010000   mov dword ptr [esp+0x3c], 0x12C
    0x77C678   c7442424 f4010000   mov dword ptr [esp+0x24], 0x1F4

Both are set ONCE, at the top of the Ordinances builder `sub_77C660`, before
either group loop, and both are incremented per row (`inc ecx` @0x77CAE2 /
`inc edx` @0x77CB1D). So the ids run CONTINUOUSLY across the income/expense
boundary — they are not per-section. `0x12C` is the CHECKBOX id (passed to
`CheckStrip` sub_77B7B0 @0x77CA8E / 0x77CF1C); `0x1F4` is the ROW STRIP id
(passed to `Button` sub_77B960 @0x77CAEB / 0x77CF79).

EVIDENCE: `SimCity 4.exe` file offsets 0x37C670 / 0x37C678, bytes as above;
live ids 0x0000012C…0x00000137 and 0x000002F4…0x000002FF, 12 of each, in
`tools\research\_checkpoints\pds-cache\SC4UIScale-snapshot.log:381-403`
(MWKID, v2.27.3-forcerelayout, 2400x1600, f=2.00).

`0x1F4 + 0x100 = 0x2F4`. That offset is the engine law in BLOCK B, not a
mystery: the strip window the tree carries is the OUTER of a `sub_77B960`
button pair.

### 7.2 The 32 windows, with stock geometry

Dialog: `0x0423278F` live **900x754** → stock **450x377**. Row pitch stock 18
(= height(slab art 0x140155F2 = 450x36)/2, the §1 metric rule). Section row
origins stock y=52 (income) and y=152 (expense).

| runtime id | n | what | exe evidence | STOCK rect (dialog-relative) | live 2x |
|---|---|---|---|---|---|
| 0x0000012C..0x137 | 12 | ordinance ENABLE CHECKBOX — one cell of the 8-state art `{0x46A006B0,0x144161EA}` | CheckStrip @0x77CA8E/0x77CF1C, `push 0x12` @0x77CA88/0x77CF16 | (18, 52+18k) **16x16** | (36, 104+36k) 32x32 |
| 0x000002F4..0x2FF | 12 | ordinance ROW STRIP — the 4-state row plate that carries the eye glyph, art `{0x46A006B0,0x140155B7}` | Button @0x77CAEB/0x77CF79, `push 0x22` @0x77CAE0/0x77CF6E | (34, 52+18k) **1320x18** | (68, 104+36k) 2640x36 |
| 0x00000551..0x554 | 4 | per-section scroll arrows (§2), art CB=▲ CC=▼ | Buttons @0x77D628/0x77D66D/0x77D6B2/0x77D6F7, exe ids 0x451-0x454 | (417, 56 / 200 / 156 / 300) **64x10** | (834, 112/400/312/600) 128x20 |
| 0x0000016D | 1 | CANCEL | Button @0x77D4AC, exe id 0x6D, `sub ecx,0xC3` @0x77D4A0 | (255, 337) **180x30** | (510, 674) 360x60 |
| 0x000001CD | 1 | ACCEPT | Button @0x77D329, exe id 0xCD, `push 0xE` @0x77D31F | (14, 337) **180x30** | (28, 674) 360x60 |
| 0x0423278E | 1 | the CONTENT PANE (hosts every TextLabel — §7.4) | created before the loops; parent for `sub_779660` (`[esi+0x10]`) | (0,0) **450x377** | (0,0) 900x754 |
| 0x0423278D | 1 | the shared text popup (§POPUP) | `sub_78B120` | (30, y) **390x125** | (60, y) 780x250 |

Row y stock, in full: income k=0..2 → 52, 70, 88; expense k=0..8 → 152, 170,
188, 206, 224, 242, 260, 278, 296.

EVIDENCE (stock rects, three independent sources that agree):
1. **Art IHDR** (exact integers, not pixel counting):
   `0x140155B7` 1320x18 → shipped 2640x36 (4 states, cell 330/660);
   `0x144161EA` 128x16 → 256x32 (8 cells of 16/32);
   `0x140155CB`/`CC` 64x10 → 128x20; `0x140155B4` 88x20 → 176x40;
   band set `0x140155F0-F7` = 450 x {29,23,36,41,23,36,41,40}.
   Read from `tools\dbpf\extracted\SimCity_1\T-856ddbac_G-46a006b0_I-*.png`
   and `tools\selective-safe\stage\T-0x856ddbac_G-0x46a006b0_I-0x*.png`.
2. **Exe immediates**: 0x12→18, 0x22→34, 0x21→33 (W−33), 0xC3→195 (W−195),
   0x28→40 (H−40), 0xE→14, `push 0x1e;push 0xb4` = SetSize(180,30) @0x77D33F
   and @0x77D35F.
3. **The true-stock 1024x768 Ordinances capture**
   `_tests\captures\stock-budget\stock-1024-131917.png`. Dialog art origin
   (292,238) in that image. Eye-glyph run tops at x=338 come out at screen y
   290,308,326 | 390,408,…,534 → dialog-relative 52,70,88 | 152,170,…,296,
   pitch **18**, and income→expense delta **100** — identical to the live 2x
   delta 200 halved. Accept's left border sits at screen x=306 = 292+14 and
   Cancel's at 547 = 292+255, to the pixel. The single visible ▼ sits at
   screen (709,538) = dialog (417,300) = the derived group-2 down arrow.

### 7.3 Band arithmetic — the dialog height closes exactly

    H = F0 + F1 + F2·floor(n1/2) + F3 + F4 + F5·floor(n2/2) + F6 + F7
      = 29 + 23 + 36·1 + 41 + 23 + 36·4 + 41 + 40 = 377          (n1=3, n2=9)

and the income→expense gap 100 = 36 (one slab) + 41 (cap) + 23 (header).
`n1`/`n2` are the enacted/available counts accumulated at 0x77C734/0x77C73C and
**clamped to 9** at 0x77C829 (`mov edx,9; cmp; jbe`) before the stacker call
@0x77C84E. Two independent fits (n=3→1 slab, n=9→4 slabs) give `floor(n/2)`,
not `ceil` — refining §1's "one slab art = TWO rows", which does not say what
an ODD row count does.
EVIDENCE: live 900x754 (snapshot:373), the eight F-series IHDRs, the two
measured section origins. HYPOTHESIS: that `floor` generalises to the other
four department families — untested, one BHDR capture settles it.

### 7.4 Why the ordinance NAME texts are NOT in this list

The builder uses TWO parents. CheckStrip / Button / arrows / Accept / Cancel
take `edi` = the function's window argument = `0x0423278F`. Every
`sub_779660` TextLabel — the title `0xABCDE00`, the headers `0xABCDE01/02` and
the per-row names `0xABCDE03+k` at `push 0x44` (68) @0x77CC23 / 0x77D0E0 —
takes `[esi+0x10]`, which is the content pane `0x0423278E`. That puts them at
depth 3, and MWKID prints depth 2 (`UiSpike.cpp:8243-8283`, main window's
children + one level). They are reachable only through BHDR
(`UiSpike.cpp:8413-8419`, which states the same thing).
CONSEQUENCE: the name column is invisible to MWKID by CONSTRUCTION, so its
absence from a log is never evidence about it.

Measured refinement of §4's clamp note: the eye ink inside the row strip runs
x=4..25 of the 330-wide cell (x=8..51 of 660 at 2x). So at 1x the name at x=68
clears the eye by 68−(34+25) = **9 px**; at 2x with the imm8 clamp at 127 it
clears by 127−(68+51) = **8 px**, i.e. the clamp preserves the stock gap almost
exactly. §4's "clears the measured eye (ends ~104) by 23px" was a
screenshot-inferred number; the art says the eye ends at 119, and the clamp is
tighter — but still clear. Not a defect, and now a measured value.
EVIDENCE: alpha scan of the two PNGs above, per 330/660 cell.

### 7.5 Verdict at 2x, per group, and how it is known

- **Checkboxes — CORRECT.** POSITIVE CONTROL: the window is one art cell. With
  the stock 128x16 art it would be 16x16; live is 32x32, which only the shipped
  256x32 art can produce. x = 36 = 2×18 from the patched `0x77CA88`.
- **Row strips — CORRECT.** Live 2640x36 is byte-for-byte the shipped PNG's
  IHDR; the 1x art would give 1320x18. x = 68 = 2×34 from `0x77CAE0`.
  The window is 4× wider than the dialog at BOTH tiers (1320 in a 450 frame,
  2640 in a 900 frame) — that is the 4-state strip convention, not overflow.
- **Scroll arrows — SIZE CORRECT, POSITION correct-by-patch, NOT yet
  confirmed live.** 128x20 = shipped art. x=834 = 900−66 confirms the v2.26.0
  W−33→W−66 fix from a live rect (first such confirmation on record). The Y in
  the v2.27.3 snapshot is 108/396/308/596 = the UNPATCHED `lea [ebp+4]`, four
  px high per arrow; `kBudgetLeaDisp8Sites` (0x77D618/65C/6A2/6E6, 4→8) fixes
  it in v2.29.0 and the expected rects are 112/400/312/600. No 2x log since
  v2.29.0 contains this dialog, so that is a PREDICTION, not a measurement.
  The down-arrow Y is `ebp + rowPitch·8 + 4` (`lea ecx,[ebp+eax*8+4]` @0x77D65C,
  eax = rowPitch `[esi+0x88]`): 396−108 = 288 = 36·8 live, so the `*8` term
  self-scales through the art-derived pitch and needs no patch.
- **Accept / Cancel — SIZE CORRECT, ACCEPT X correct-by-patch, NOT yet
  confirmed live.** 360x60 = 2×(180x30) from `kBudgetBtnSizeSites`; Cancel
  x=510 = 900−390 confirms the W−195 patch live. Accept measured x=14 (1x) in
  the v2.27.3 snapshot; `{0x77D31F, 0x0E}` (v2.29.0) makes it 28. Also a
  prediction until a post-v2.29.0 capture exists.
- **Content pane / popup — CORRECT / FIXED.** Pane tracks the dialog exactly.
  The popup's snapshot rects (840x125, close-X at 809,11) are the pre-v2.28.2
  state §POPUP documents as fixed (`{0x78B9A1,0x3C}`, `{0x78BAAD,0x0B}`,
  `{0x78BAAF,2,-31}`, POPBOX pin). Its close-X window 176x40 = shipped
  `0x140155B4` — art-born-2x and correct even in that build.

### 7.6 OPEN — the one art the buttons cannot reach

`0x144161EB` (the Accept/Cancel plate, stock 120x30) is classified **SHARED**
in `tools\selective-safe\refmap.csv:216` — 151 occurrences across 109 `.UI`
files, action `clone+retarget` to group `0x470261EA`. It therefore does NOT
ship 2x in place, and there is no 2x PNG for it under `stage\`. But the budget
builders bind it by a hardcoded `push 0x144161EB` at **0x77D316** and
**0x77D497** (and the four twins in the other families), which no CodePatches
retarget touches — the only retargets in the file are the four popup STYLE
guids at 0x52CCEE/0x52CD01/0x762F85/0x762F98. So a code-sized 360x60 button is
drawn from a 1x plate.
STRUCTURAL NULL, stated per the null rule: `_checkpoints\pds-cache\
art_coverage.py` could never have flagged this — it parses `.UI` ROOTS
(328 of them) and code-created windows are outside its input entirely. Its
silence is not coverage.
HYPOTHESIS (visual consequence): 9-slice/stretch leaves 1x-thick chrome on the
two biggest buttons in every budget dialog. CHEAPEST CHECK, no build: compare
the Accept plate's border thickness in `stock-1024-131917.png` (stock 180x30)
against the same button in a 2x screenshot — equal pixel thickness means the
plate is 1x. If confirmed, the fix is a fifth guid retarget of the six
`push 0x144161EB` sites, exactly the `kPopupStyleRetargets` pattern.

================================================================================
BLOCK B — for `tools\research\SC4-UI-ENGINE.md`, widget catalogue / creation
(this is general to the whole exe, not to the budget)
================================================================================

**THE `+0x100` OUTER/INNER PAIR.** Every window created through the button
factory `sub_77B960` appears in the live tree TWICE: an OUTER window with
`id + 0x100`, and its child with the RAW id. The tree carries the outer; code
that later wants the caption/image surface fetches the raw id. Both are sized
from the same art unless the builder explicitly resizes them, and builders that
care resize BOTH. The check-strip factory `sub_77B7B0` does NOT do this — its
window carries the raw id, unpaired.

Mechanism: the two factories differ only in the create TYPE passed to the
window manager — `push 2` @0x77B9D8 (button) vs `push 4` @0x77B828 (check
strip). Neither factory adds 0x100 itself; the offset is applied inside the
type-2 create.

EVIDENCE — the exe proves it on its own, twice, without any live data:
    0x77D321  push 0xcd     ; create id
    0x77D330  push 0xcd     ; GetChildWindowFromID -> SetSize(180,30) @0x77D348
    0x77D350  push 0x1cd    ; GetChildWindowFromID -> SetSize(180,30) @0x77D368
    0x78BA95  push 0x384    ; create id
    0x78BAC1  push 0x384    ; -> SetSize(w,125)
    0x78BADD  push 0x484    ; -> SetSize(w,125)
Both pairs are fetched from the SAME parent. And live, in the tree:
    POPKID 0  id=0x00000168 vt=00AE20A0 (809,11 176x40)
    POPKID 0.0 id=0x00000068 vt=00ADDAF0 (0,0 44x40)      <- 176 = 4 x 44
    POPKID 1  id=0x00000484 vt=00AE20A0 (0,0 840x125)
    POPKID 1.0 id=0x00000384 vt=00ADDAF0 (0,0 840x125)
(`_checkpoints\pds-cache\SC4UIScale-snapshot.log:410-413`.)

Class fingerprint for the tree dumps: `vt=00AE20A0` is the outer button class,
`vt=00ADDAF0` the inner image/caption class.

WHY IT MATTERS TO EVERY ORACLE: a builder census keyed on the `push <id>`
immediates lists `0x451`, `0x6D`, `0x384`, `0x1F4`; the live tree shows
`0x551`, `0x16D`, `0x484`, `0x2F4`. A join on raw id misses 100% of them and
reports them as unknown windows. `BUDGET-DETAIL-ANATOMY.md` §2 recorded the
+0x100 as a bare observation about four scroll arrows; it is a general rule
with a stated mechanism and it applies to every `sub_77B960` call site in the
exe.

CONSEQUENCE FOR `tools\uimap`: `builders.json`'s `identification.childIds` must
be widened to `{id, id+0x100}` for every `Button` primitive call before any
model-vs-live join can be meaningful.

================================================================================
BLOCK C — for `tools\research\_checkpoints\uimap-stage4-diff.md`
(replaces FINDING 5, and NEXT ACTION item 2)
================================================================================

## FINDING 5 (REVISED) — the 45 are named; 32 now have stock rects

The original table said the 35 under `0x0423278F` were "generic ids like
0x0000012C, all 32x32". **Both halves are wrong.** The set is four distinct
families plus two containers, and only 12 of them are 32x32:

| ids | n | size | what |
|---|---|---|---|
| 0x0000012C-0x137 | 12 | 32x32 | ordinance checkbox cells |
| 0x000002F4-0x2FF | 12 | 2640x36 | ordinance row strips (exe id 0x1F4+k, +0x100) |
| 0x00000551-0x554 | 4 | 128x20 | per-section scroll arrows |
| 0x0000016D, 0x1CD | 2 | 360x60 | Cancel, Accept |
| 0x0423278E | 1 | 900x754 | content pane |
| 0x0423278D | 1 | 840x125 | shared text popup |

That is 32. The remaining 3 are NOT RECOVERABLE: the v2.28.1 log the census
ran on has been overwritten (the current `SC4UIScale.log` is
v2.37.0-dvorigin, 11:15 today, and contains ZERO `0x0423278F` records), and
none of the six archived `.bak-*`/`.prev` logs contains the string `0423278F`
either. They are almost certainly from a second department instance sharing
the id — the `0x0ABCE1xx` combo backing plates, `0x0ABCE2xx` notch bitmaps or
`0x0ABCE4xx` master slider, all of which BUDGET-DETAIL-ANATOMY §2 already
identifies. The one surviving capture is
`tools\research\_checkpoints\pds-cache\SC4UIScale-snapshot.log` (v2.27.3, 45 KB).

Also wrong: "their ids are per-row generics appearing in no `.UI` script under
a stable identity". They are two literal id bases in the exe
(`0x12C` @0x77C670, `0x1F4` @0x77C678) plus the `+0x100` law, and they are
perfectly stable — Ordinances always yields 0x12C+k and 0x2F4+k.

The 3 under `0x0423278D` are exact and unchanged: `0x00000168` close-X outer,
`0x00000484` backdrop outer, `0x0423278F` popup content (POPKID 0/1/2).

The "7 elsewhere" cannot be re-derived; the only generic-id windows in the
surviving snapshot outside the budget tree are ids 0x2/0x3/0x4/0x5 under the
advisor toast `0x4A9DB60C` and one id 0 under the quit confirm `0xAA921F4F`,
and all of those are `<= 0xFF` so the harness buckets them AMBIGUOUS-ID, not
UNKNOWN-STOCK. State the loss rather than reconstruct it.

## FINDING 5b — the null is measured, and its positive control is stated

Today's log has **466 MWKID lines and zero budget records**. The instrument is
demonstrably alive; the user simply never opened the Budget panel this session.
And **no log on this box, current or archived, contains a single `BHDR` line** —
so the deepest budget layer (the content pane's children: title, headers, the
per-row name and value texts) has never been captured in a form the harness can
read, even though `parse_log.py:81-82` already knows how to attribute it
(`BHDR i -> 0x0423278E`). The BHDR rects quoted in BUDGET-DETAIL-ANATOMY (e.g.
"BHDR 15:33:38, master 1300x338") come from logs that no longer exist.

## NEXT ACTION 2 (CORRECTED)

The old text — "when stage 3 emits rects, re-run … should convert ~35
UNKNOWN-STOCK rows" — cannot work, and the reason is worth writing down.
For these windows the exe supplies only X and Y. **W and H come from the art
and from nowhere else** (§3's ART-derived regime). A Unicorn layout emulator
can reproduce an x from a `push imm8` and a y from a row cursor; it can never
produce 2640x36, because that number is a PNG header. Stage 3's own state.json
holds five cases and all five are popup-body FILL arithmetic — nothing that
would touch a row.

The correct next action is BLOCK D.

================================================================================
BLOCK D — for `tools\uimap\diff\RESUME.md`, §"What is still missing"
THE SINGLE ARTIFACT THAT RETIRES THE CLASS
================================================================================

**`tools\uimap\art-rects.json` — a generated art-dimension oracle.**

One model output, no game session, no new capture. For every art TGI that
`builders.json` shows bound to a create (`primitiveCalls[*].args` — `BandArt`
instId, `BmpArt` instId, `Button` captionTgi, `CheckStrip` artTgi), emit:

    { "0x140155B7": { "stock": [1320,18], "shipped": {"1.5":[1980,27],
                       "2":[2640,36], "3":[3960,54]}, "cells": 4 },
      "0x144161EA": { "stock": [128,16],  "shipped": {"2":[256,32]}, "cells": 8 } }

Sources, all already on disk and all exact integers:
`tools\dbpf\extracted\SimCity_1\*.png` (stock IHDR),
`tools\selective-safe\stage{,-15x,-3x}\*.png` (shipped IHDR),
`tools\selective-safe\refmap.csv` (EXCLUSIVE / SHARED / clone+retarget — so the
table also flags §7.6-class art that a code create cannot reach).
`cells` comes from the create TYPE, which `builders.json` already records:
type 2 (`sub_77B960`) window = the WHOLE strip; type 4 (`sub_77B7B0`) window =
one cell (art height square). Both rules are measured, live, in BLOCK A.

Then teach `_extract_windows()` in `diff.py` a fifth stock source: for a live
window whose builder call binds art, expected size = the shipped IHDR (or
stock × f for the divisor case). That single join converts every art-derived
window in every budget family — and every flyout, dock and toolbar window built
the same way — from UNKNOWN-STOCK to MATCH/MISMATCH, at 1x, 1.5x, 2x and 3x
simultaneously, because IHDRs exist for all four packages.

**What it does NOT need:** the founded-city inert capture of FINDING 8.2. That
capture is still the right thing for the city HUD, but it is not what these 35
were waiting for — they were waiting for a table this repo has been able to
build since the DBPF extractor shipped. Reading a PNG's IHDR is geometry and
math; it is not the pixel counting STOCK-REFERENCE.md's directive forbids, and
FINDING 8.4's "the PNGs are never opened" was written about the ten
`stock-budget` SCREENSHOTS, not about the art.

**What it still will not cover** (state it so this is not read as a clean bill):
windows whose W/H come from a code `SetSize` (Accept/Cancel 180x30, the popup
box) — those are `builders.json` constants and are already checkable — and
windows sized from TEXT, which remain ONE-AXIS-EXACT territory.

