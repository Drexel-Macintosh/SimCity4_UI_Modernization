# TRIAGE PLAYBOOK — from the user's sentence to the right instrument

**Purpose: turn ~162 numbered defects into a decision tree you can walk in
minutes.** Every branch below is keyed on what a user can actually SAY, because
that is all you ever get. Under each branch: what it has already been PROVEN NOT
TO BE (with entry numbers), the first measurement, the exact command, and the
historical entries that match.

### How this file relates to the others

| file | answers |
|---|---|
| **this file** | *"the user said X. What do I ask, measure and run, in what order?"* |
| `tools\research\TRIAGE.md` | *"the symptom maps to which MECHANISM and which LEVER?"* — the mechanism table. Read it after you have narrowed the branch here. |
| `_tests\REGRESSION.md` | the evidence behind every claim here. **Search it, never read it front to back.** |
| `tools\research\SC4-UI-ENGINE.md` | how the engine actually works, once you know which subsystem you are in. |
| `START-HERE.md` §3 | the standing rules. This file is those rules re-indexed by symptom. |

**A proposal that contradicts a documented, measured finding without addressing
it is worse than no proposal.** Cite the entry number when you touch settled
ground.

---

## 0. THE FOUR QUESTIONS — ASK THESE BEFORE YOU OPEN A FILE

They cost one message to the user. Not asking them cost **six wrong fixes in one
night** on #162 alone, plus ten refuted theories on #148.

### Q1 — IS IT LIGHTER OR DARKER? THIS IS RULE 1

This is the single highest-value question in the project and it is one word of
answer.

| answer | what it means | consequence |
|---|---|---|
| **darker / the colour of what's behind it / a gap** | **UNCOVERED.** Two objects disagree in size or position and you can see through the difference. | Gap-hunting instruments apply: `gate_art_vs_window.py`, `gate_btn_undercover.py`, `gate_abut_1_5x.py`. |
| **lighter / brighter / white** | **PAINTED.** Something drew those pixels. | **NO GAP-HUNTING GATE CAN EVER SEE IT.** Every one of them is looking for absence. Stop running them. |

> **#162.** Six fixes missed in a row because every single one hunted
> an uncovered gap. The user then answered two questions — *the lines are
> LIGHTER, and they are a SHORT SEGMENT* — and the search ended in a sentence.
> A bright line means something painted there.

### Q2 — HOW LONG IS IT?

| answer | family | entries |
|---|---|---|
| **a short segment, inside one control** (a few px) | a feature inside the ART is re-registered — NN row/column multiplicity, or a cell-boundary bleed | #162 (mechanism), #156 |
| **a full window edge** — often right edge **and** bottom = "the reverse L" | window vs art cell disagree by one pixel | #148, #155, #162 first half |
| **a panel-wide band, or a BREAK in a long rail** | art and window desynced on a tiled / 9-slice sheet, or a child rounded in the wrong frame | #160, #157, #161 |
| **across a whole sheet / states bleeding into each other** | the engine's own cell divide stopped being exact | #143, #156 |

### Q3 — WHICH TIERS?

**"1.5x only" is the NULL HYPOTHESIS, not a clue.** `Upscale2x.cs::ScaleDim`
returns early at an integer factor and `ScaleRound` is exact there, so **every**
disagreement between any two scalers in this project is 1.5x-only by
construction (#148). Matching that pattern tells you almost nothing.

| answer | what it means | do this FIRST |
|---|---|---|
| 1.5x only | null hypothesis — proves nothing on its own | go to Q4 |
| all three tiers | **not a rounding family.** A wrong RELATIONSHIP scaled faithfully is wrong everywhere | diff the `.UI` design against a correct sibling panel (#137) |
| 2x and 3x too, but stock is clean | ours: art, sweep, or a patch | the gate suite in §5 |
| **present at STOCK** | **NOT OURS.** Stop. | `_tests\Set-StockCompare.ps1 -Mode Stock -Width 1024 -Height 768` |

The stock control has closed a "regression" outright **three times** — #91
(dashboard minimap), #98 (Trip Types), #147 (blank graph caption, a Maxis defect
since 2003). Cost: one launch, no build. **Run it before the third theory, not
after the sixth.**
`-Mode Stock` leaves the mod DISABLED. `-Mode Ours` to restore — and check
with `Set-StockCompare.ps1 -Status` whether the tree is already sitting in
stock mode before trusting any measurement.

### Q4 — IS THERE A SIBLING THAT WORKS? 

> *"The sun and the moon are wrong"* is consistent with a hundred mechanisms —
> ten of them survived a full day of testing.
> *"**One** of these **five identical** buttons is wrong"* is consistent with
> almost none, and named the cause in minutes (#148).

**When a defect resists, stop instrumenting the broken instance and go hunting
for a working sibling.** Ask the user for the screenshot that has a control in
it. The pair is the experiment; the broken one alone is an anecdote.
The sibling can also be geometric: #162's "?" button carries the identical
defect in its art and is clean on screen only because its top 6 rows are clipped
above the parent origin.

---

## 1. THE 90-SECOND OPENING — run this before any theory

```
:: STEP 0 — the SDK lookup. One call, ~2 s, live sources, never a cache.
python tools\sdk\lookup.py 0xAA8DEF97       :: window id
python tools\sdk\lookup.py 46a006a6         :: art instance
python tools\sdk\lookup.py ca8cbf0f         :: .UI script instance

:: STEP 0b — IS IT OURS TO SCALE AT ALL?  (#154)
::   live rect == the .UI's own 1x area= TO THE PIXEL  =>  nothing ever
::   scaled it. Not a rounding bug, not a hook that missed. Every theory
::   below is off-target; go to branch I.
python tools\uiscripts\winning_corpus.py    :: third-party winners MUST be 0

:: STEP 1 — is the tree in a known-good state?
python tools\uimap\emu\gate_art_vs_window.py
python tools\uimap\emu\gate_btn_undercover.py
python tools\uimap\emu\gate_abut_1_5x.py
```

Then, and only then, pick a branch.

**Two questions on every diagnosis, never one** (START-HERE rule 12):
**(a)** have we hit this before? **(b)** is that cure VIABLE HERE? If it is,
**port it** — do not design a new mechanism beside it. If it is not, say why in
one sentence before writing anything. Question (b) is the one that gets skipped
and it has cost multiple sessions (#145, #146).

**Corollary that closed two defects on its own:** when one tier or variant
misbehaves and a sibling is confirmed fixed, the default hypothesis is **"the
known cure never reached this one"** — go read the GATE that decides who gets
the fix. `DOCK_NEUTRALIZE_MIN_FACTOR = 2.5` (#145) and `GetW() > 64` (#146) each
excluded exactly one tier from a cure that already worked.

---

## 2. THE SYMPTOM TREE

---

### BRANCH A — "THERE'S A LINE" the largest family, and the most expensive

Ask **Q1 (lighter/darker)** and **Q2 (how long)** before anything else.

#### A1. LIGHTER / BRIGHT / WHITE — something PAINTED it

**Already proven NOT to be:**

| ruled out | why | entry |
|---|---|---|
| the resampler introducing a colour | nearest-neighbour only ever COPIES source pixels; a colour absent from the 1x art can never come out of it at any factor | #143 |
| **but NOT "the upscaler is innocent"** | **NN cannot introduce a new COLOUR but it CAN introduce a new SHAPE.** `sy=(int)(oy/f)` gives EVEN source rows multiplicity 2 and odd rows 1 at f=1.5; a 1px bright run on an even row renders 2px and reads as a short bright segment | #162 (the precise gap in `Upscale2x.cs:76`) |
| damaged art | extract and back-map every pixel through `floor(o/f)`: **0 mismatches** on the reported sheets, 0 at 2x and 3x too. Positive control: the same differ reports 3215 differing px between two real variants | #148 dead end 4, #162 |
| the runtime blit code for flyout buttons | both `BltClassThunk` blocks are gated on sizes those buttons never have (`selfH>250 && 100<selfW<200`; `selfW==129±1`). **Six edits on a path that provably never executes** | #148 dead end 1 |
| an `imagerect` under-read | two repair attempts, both DAMAGED the thumbnail flyouts; and the reporting buttons carry no `imagerect` at all | #148 dead end 3 |
| "cell must equal window" as a general law | `gate_btn_cell_vs_window.py` measures **420 mismatches at 2x AND 3x** on user-confirmed-perfect tiers. Only ART-SIZED buttons are bound by it | #148 falsified law |
| `ScaleDim`'s tie-break direction | ties-down 701 vs ties-up 709 across 868 buttons. **Do not touch it for this** | #148 |
| band-mean luminance excess vs 1x | 40 random bands on 40 random sheets: 0.000 at 2x in 40/40, at 3x in 40/40, nonzero at 1.5x in 29/40. That signature is a property of ALL fractional NN, not of any defect. **Do not quote it as evidence** | #162 |

**First measurement — the free kill test (#162).** The mechanism is
PARITY-dependent, so it predicts a state the user can reach with the mouse:

> **Press and HOLD the button at 1.5x. If the bright line is NN row
> multiplicity, it must DISAPPEAR while held** (the pressed cell carries the same
> hairline one source row lower — ODD, multiplicity 1) **and come back on
> release.** One click, no build, settles it either way.

**Then:**
1. **Look at it.** These are the project's only pixel instruments — every other
   gate in `emu\` is arithmetic and its own README says *"IT NEVER LOOKS AT A
   PIXEL"*, which is exactly why ten theories were checked against numbers
   instead of an image (#148). `render_flyout.py` then killed two of them in
   three minutes each.
   ```
   python tools\uimap\emu\render_flyout.py --script <iid> --tier 15x --rule edges --out DIR
   python tools\uimap\emu\render_dialog.py  <iid> --tier 15x --out DIR
   ```
   **A CLEAN RESULT IS NOT PROOF THE SCREEN IS CLEAN.** `render_dialog.py`
   ignores z-order subtleties, text, edge/tiled blits and every runtime-drawn
   element. Read it as a **locator**, not a verdict. It was also structurally
   unable to draw #157's dialog until it gained a `nine_slice()` path — both
   nodes were 9-slice.
   **A diff that compares nothing reports agreement.** #157's first comparison
   run was vacuous because one set carried bare hex filenames and the other
   canonical ones (`--normalize-names` omitted): 0 of 4413 names matched and it
   printed "CHANGED 0" three times. **The `only-in-one` counter is what caught
   it** — always read the denominator before the verdict.
2. Check the state-boundary bleed case: does the ink start at the wrong column?
   `1x sheet 84 wide cell 21, ink at 42` → `1.5x sheet 132 cell 33, ink must be
   at 66`. Three columns of the next state hard against the previous cell's edge
   = three slivers (#156).

**Matching entries:** #143 (white seams, cell divide), #156 (state-strip cell
bleed), #162 (two phantom hairlines — mechanism: NN row multiplicity; the
press-and-hold kill test above is the discriminator).

#### A2. DARKER / A GAP — something is UNCOVERED

**First measurement, in this order:**

```
python tools\uimap\emu\gate_art_vs_window.py     :: art vs the sweep-scaled window
python tools\uimap\emu\gate_btn_undercover.py    :: strip cell vs window, BOTH halves
python tools\uimap\emu\gate_abut_1_5x.py         :: do abutting siblings separate?
```

**When you read `gate_btn_undercover.py`, read the RESIDUAL, not the verdict.**

> **A "KNOWN RESIDUAL" THAT EXISTS AT ONE TIER ONLY IS NOT A RESIDUAL — IT IS
> THE DEFECT, already located, already counted, sitting under a line that says
> PASS.** When a gate reports a nonzero number it has decided not to fail on,
> the question is not "is it tolerable" but **"does it vanish at the tiers that
> work?"** If it does, stop looking anywhere else. (#162)

Its output shape — the gate prints seven summary lines per tier, four from
`run()` and three from `run_static()`:

```
15x  runtime residual, ScaleDim cell-snap  : 34
15x  pre-scaled data : 50 ok / 0 BUILDER-WRONG / 132 art snapped by ScaleDim
15x  static residual (cell-window -> count): {(0,1):1, (1,0):1, (0,2):347, (0,6):3}
2x   runtime 0 | pre-scaled 182 ok / 0 / 0 | static none
3x   runtime 0 | pre-scaled 182 ok / 0 / 0 | static none
```

347 buttons whose art cell is 2px TALLER than its window at 1.5x, and **zero
at both integer tiers**. That is a live lead, not background noise.

**AND IT IS NOT THE ONLY LINE THE RULE CONDEMNS.** Quoting one of the seven
lines is how a second population stayed invisible. The gate reports
**three** 1.5x-only residual populations — 34 runtime, 347 static, and **132
pre-scaled** — each zero at 2x and 3x. The 132 are the ones with their own
id: the window is right (`ship == want` for all 132, measured) and the
**SHEET** is over-snapped by `ScaleDim`'s `CellUnit` — Zoom Out is 21px at 1x
and `R(21*1.5)=32`, but the 84px four-state sheet divides by both 3 and 4,
snaps on LCM 12, lands at 132, cell **33**. All three share one cause family,
and the cure for all three is an ART-dimension change that is reverted and
scoped game-wide — **reported, not failed**. Read every line the gate prints,
not the one this block quotes.

**The known causes of a gap, in order of how often they were the answer:**

| cause | signature | fix that shipped | entry |
|---|---|---|---|
| **odd left edge costs one pixel** | one of N identical controls; the broken one is the only odd `l`. `l=68 → w=71`, `l=69 → w=70`, art cell 71 | `ScaleSubtree`: a **leaf** (`GetChildCount()==0`) takes its size **size-derived**, `ScaleRound(w,f)`. Nothing moves. No-op at integer factors by construction. Logs `LEAFSIZE` | #148 v2.94.1 |
| **the same cure missing from ALL THREE paths** — `build_selective_safe.py` names all three | the same control is 83px at runtime and 82px in a static dat | `build_dialog_static.py::leaf_art_sized()` (`tools\dialog-static\build_dialog_static.py:748`). Static dialogs are *deliberately* excluded from the sweep, so nothing repaired them | #155 v2.98.0 |
| **…and missing from the THIRD path — a PRE-SCALED subtree the sweep never walks** | 1.5x only. A break down the **right** of every icon in the advisor row: staged window **82**x141 against an art cell of 332/4 = **83**x141 (`_tests\REGRESSION.md:10225`). Discriminator: the **WINDOW** is the wrong number here, the sheet is right — the opposite of an over-snapped sheet | `build_selective_safe.py::double_subtree_areas` scaled all four coordinates independently, so a child's SIZE depended on its POSITION: `R(392*1.5) − R(337*1.5)` = 588−506 = **82**, while the art is built as a length, `R(55*1.5)` = **83** per cell. Every one of the seven buttons (x2 scripts, `I-4a160034` / `I-cbc905cd`) sits at an odd `l` with an even `r`. #148's leaf rule now applies here too — no children + `image=` + no `imagerect` → size-derived (`tools\selective-safe\build_selective_safe.py:704-751`); provable no-op at an integer factor and FATAL-guarded at :758-761. **No runtime rule can repair this**: these roots are in `kDataScaledSubtreeIds` (`src\UiSpike.cpp:5373`) and `ScalePanelRoot` RETURNS there (`src\UiSpike.cpp:14557`) before its child loop, so neither `ScaleSubtree` nor #167's `stripBtnClass` ever walks them. Same doubler, same rule, for the other pre-scaled roots — Graphs, budget, dashboard `0x4BCB938A`, console variant `0xEC1A5CBF`, HUD dock (`build_selective_safe.py:1963, 2011, 2035, 2057, 2082`) | #170 v3.0.0 (added 2026-08-16) |
| **`ScaleRound` rounded half AWAY FROM ZERO** | a window whose ABSOLUTE design origin is negative comes out one pixel LONGER than the same span scaled as a length. 12 nodes have a negative absolute origin; 44 positions depend on them | `ScaleRound` now calls `RoundHalfUp` — one function body, 61 call sites, 0 change at 2x/3x (measured over all 2920 corpus nodes) | #162 |
| **child rounded in its OWN frame, not the parent's** | a break in a long rail; the cap misses the strip's bottom by one transparent pixel | round edges at the parent's absolute design origin: `R(1011+351)−R(1011)=526`, not `R(351)−R(0)=527`. `[UiSpike] ParentFrameRounding=0` restores the old maths | #161 |
| **tiled sheet snapped when it has no cell divide** | `blttype=tiled`; art 111x528 vs window 111x527 | `find_no_snap.py` → `no-snap.txt` (121 sheets) → `Upscale2x --no-snap`. Not `find_tiled.py`: that generator defaults to `--out tiled.txt` and emits only the **10** PROVEN-tiled TGIs; `tiled.txt` is a strict SUBSET of `no-snap.txt` (0 entries outside it), so regenerating the shipped list from it drops **exactly 111** sheets — every one admitted by the "bound 1:1 to a window of exactly its 1x size" rule — because `tiled.txt` is scoped to the original tiled finding alone while `no-snap.txt` adds the 1:1-window-bound role. Nothing fails: the file still exists, `Rebuild-Corpus.ps1` only tests `Test-Path`, and every downstream gate stays PASS | #160 |
| **9-slice sized by the wrong cell count** | `blttype=edge`; `180 → /3 wants 270, /4 wants 272, LCM 12 ships 276` | `find_nine_slice.py` → `nine-slice.txt`; `CellUnit {3}` for those sheets | #157 |

**THE SHEET'S ROLE DECIDES ITS SIZING RULE — and the role is DERIVED from the
`.UI` that binds it, never guessed from the number** (law 86):

| role | sizing rule | derived by | list (never hand-edit — re-run the generator) |
|---|---|---|---|
| N-state strip | preserve `width/N` | a `.UI` binds it to a window whose HEIGHT equals the sheet's and whose WIDTH divides it (#156) | `find_cell_strips.py` → `cell-strips.txt`, **193 sheets** (191 four-state, 2 eight-state) |
| 9-slice frame | preserve `width/3` | `blttype=edge` / `edgeimage=yes`, and no `.UI` ever draws it as a `GZWinBtn` state (#157) | `find_nine_slice.py` → `nine-slice.txt`, **30** |
| tiled / 1:1 background | **nothing at all** | `blttype=tiled`, **or bound 1:1 to a window of exactly its 1x size**, and never a button state or 9-slice (#160 + #162) | `find_no_snap.py` → `no-snap.txt`, **121** — this is the list `Upscale2x --no-snap` takes. `find_tiled.py` → `tiled.txt` (10) is the narrower #160-only ancestor |

All three lists are **exclusion-biased on purpose**: art binds by TGI and some
consumers are created at runtime and appear in no script, so a sheet nobody
proved is a strip keeps the sizing it has. An unknown consumer can be *missed*
by these lists, never *broken* by them.

**A model that would condemn STOCK is a broken model, not a finding.** A "is
the 1.5x width divisible by 3" check once flagged three 9-slice sheets as short
by 2 — they are not divisible by 3 at 1x either. Discarded (#160).

---

### BRANCH B — "IT'S THE WRONG SIZE"

**Ask first: is the window an INPUT or an OUTPUT?**

**`GZWinBMP` is dst-follows-src, so its window size is an OUTPUT, not an
input** (law 83). The draw computes `dst = areaL,areaT + srcW,srcH` and never
reads the window rect. A 128x32 window is a *consequence* of a 128x32 **buffer**.
**Resizing the consequence can never fix the cause** — #159 cost a full round of
work learning this; the cure was patching `cIGZBuffer::Init(128,32)` at
`0x007EEF59`.

| what the user says | almost always | first measurement | entry |
|---|---|---|---|
| "the box is too small for our scaling" / text clipped inside it | a runtime-rasterised buffer, not a window | find the `call [reg+0x0C]` (`cIGZBuffer::Init` slot 3) that carries those two constants. Positive control: the winning scan resolved **50 other distinct** constant Init sizes | #159 |
| it's **4x** / doubled twice | both the sweep AND a static package scaled it | check `kNeverScaleIds` vs `DialogStatic` TARGETS. A static dialog running through the sweep double-scales (the Establish-City 4x) | #83, #155 |
| a whole dialog opens **crushed / corrupted** | a **static** dialog the sweep does not scale | `DialogStatic` TARGETS (doubles `area=` in the script) | budget family |
| a panel is right but **one child** stays 1x | that child is **code-created** (live children > scripted `area=`) | patch the builder's constants | ENGINE §4.7 row 3 |
| a window with a render SURFACE is wrong, or a "fix" to it crashes | the window scaled, the surface did not. These are **one-shot Init at vtable+`0x0C`** | destroy + **recreate** at the new `blitSize` (`[+0xE4]`). Calling Init on a live surface corrupts it | #89, #109, v2.21.1 crash |
| art is a pixel wider than the window drawing it | `CellUnit` overshoot | `kCellCounts` is `{3,4}` and it was MEASURED: LCM{2,3,4,6,8,12,16,24}=152 mismatches, LCM{2,3,4}=98, **LCM{3,4}=34**, {4}=19, no snap=104 | #149 |
| the runtime and the offline art disagree on the same icon | two implementations of one rule | `ScaleTier.cpp` now carries the ported `ScaleDim`/`CellUnit` | #158 |

---

### BRANCH C — "IT'S IN THE WRONG PLACE"

**THE OFFSET-PARITY LAW (Law: offset parity) NAMES THE FAILING AXIS BEFORE YOU LOOK.**
For `f = p/q` in lowest terms, edge-derived rounding preserves a child's 1x
offset `d` from its frame **iff `q | d`**. At f=1.5 (q=2): **even offsets always
survive, odd offsets are a lottery** decided by the parity of the frame's own
coordinate. At an integer factor q=1, which is why 2x and 3x never show it.

| panel | offset | prediction | what the user said |
|---|---|---|---|
| advisor faces | (2,1) | y odd → 1px HIGH | "high" |
| My Sim grid | (3,2) | x odd → 1px LEFT | "left" |
| advisor detail | (2,2) | both even → never fails | correct at every tier |

**The cure is to SEAT, not to nudge:** place the child at
`frame + ScaleRound(offset)`, translate only, cap the delta at 1px, assert the
integer-factor no-op at the call site. Rejected on measurement: an ungated rule
moves 456 dashboard windows; `floor()` positions move 373/531 budget+graphs.
(#152, #153)

| what the user says | cause | entry |
|---|---|---|
| misplaced **identically at 2x and 3x** (same wrongness, scaled) | the RELATIONSHIP is wrong, not the tier math. Ours came from an offset eye-measured off a 2x screenshot. **Read the relationship out of the `.UI` design.** If another panel shares the widget id and renders correctly, DIFF THE TWO DESIGNS — a free controlled experiment | #137 |
| a flyout docks against the **wrong button** after a mod is installed | the mod replaced the script and MOVED its hidden `0x0000AAAA` marker; our table caches `R = −marker(1x)` off the STOCK script. Measured: LANDSCAPE (3,27)→(3,59); SIGNS & LABELS (3,183)→(4,5) = 178px of misdock | #94 |
| the ring / strip / bar of a sub-flyout is offset from each other | they are **ONE WELDED SHAPE**. Seat with the DOCK, never nudge a member | #135 |
| a panel is right and the thing ATTACHED to it (stem, arrow, connector) is not | a **COUPLED PAIR welded by a LATCH**. Fixing either half alone is not partial progress, it IS the bug (v2.45.0 shipped half and was reverted the same day). Ship both halves in one action, and **move the hit box with the sprite** | #95 |
| a break in a long rail / a cap that misses its strip | the child rounded in its own frame instead of the parent's | #161 |

**`GZWinMoveTo` IS A RELATIVE MOVE.** Measured the hard way, twice. The header
signature and the word *MoveTo* both read like absolute placement; they are
wrong. `seat (27,108) → asked for (43,124)` rendered BELOW the recess. **Do not
"fix" that call to `seat + delta` again** — the comment at the call site says so
(#145, #146 dead end 3).

**A FIX THAT MOVES THINGS IS JUDGED BY ITS DENSEST NEIGHBOURHOOD, NOT BY THE
CASE THAT REPORTED THE BUG.** The parity nudge was invisible on the Landscape
flyout (5 buttons, 50px apart) and slid 21 faces inside their frame in "Select A
My Sim". Reverted v2.94.0.

---

### BRANCH D — "IT'S CLIPPED / CUT OFF / OVERFLOWING"

**A CLIPPED RUNTIME STRING HAS TWO CONSTANTS, NOT ONE: THE SURFACE IT IS
DRAWN INTO, AND THE ANCHOR IT IS ALIGNED TO** (law 82, #159). Fixing the surface
alone widens the box and moves the text nowhere — which looks like "no progress"
but is half a cure, and **the SHIFT it produces is the evidence that names the
other half**. When a size fix visibly moves something without unclipping it, the
remainder is an ALIGNMENT constant measured from the OLD size.

| user's words | cause | first measurement | entry |
|---|---|---|---|
| "cut off on the left and the bottom" while placing an object | buffer + right-align anchor. `124 = 128−4`, the string is right-aligned 4px inside the OLD buffer; at 2x the figure measures ~140px → x = −16 | disassemble the composer's frame slots **with callee-cleanup modelled** — the first attempt did not and produced garbage offsets that would have justified a wrong patch | #159 |
| text **wraps to more lines than stock** and overflows at the BOTTOM | **THE BOX IS AN INPUT, NOT AN OUTPUT** (law 48). The wrap call READS `r->left`/`r->right` and never writes them. And ink does not scale linearly with point size — measured **x2.13** per doubling (n=17), so `round(stockBox*f)` is ~6% too narrow | `tools\uimap\emu\emu_text_extent.py` gives the widths. **A defect whose symptom is vertical can have its cause on the horizontal axis** | #57 |
| labels clipped at 1.5x | the font `round()` overshoots; it must **floor** | `tools\fonts\make_fontstyle.py N out.ini`; `--selfcheck` proves factor 2 == the candidate byte-identically | #142 |
| text breaks at a sensible word AND cuts mid-word at the box edge | `GZWinText` **regime 3** — break on `\n` only, then CLIP. Constructor default flags = 0, so code-created labels are all in it | `SetWinTextFlag(0x0002,true)` then a resize | law 24 |
| "it's off the edge" of a pane whose width says it should clear | you measured `GetW()`. The real boundary is `GetW() − 2*gutter − scrollbarW`, and `scrollbarW` is read LIVE so it moves per tier | state which width your arithmetic used | law 25 |
| an element **overlaps its neighbour only when the text is long** | a 1x inset/column constant against a 2x font | byte-patch the inset — watch the imm8 ceiling | ordinance/budget insets |
| shipping 2x art for one element makes a **neighbouring** element vanish | a **shared width budget**. Reverting the vanished element's art will NOT bring it back — that is the diagnostic, not a refutation. The budget need not be one constant: #57's was **SIX**, all measured off `winW` inside one builder | #88, #57 |

**FOUR SEPARATE FIXES EACH MOVED THE COLLISION WITHOUT CURING IT?** You are
patching outputs inside a budget nobody has read (law 49). **Stop probing the
output; disassemble the BUILDER.** Whoever allocates the child is whoever lays
it out. #57 took **six** failed patches before anyone read `sub_76D3D0`.
Rule of thumb: probe the output twice; after that, read the code that computes it.

**On an encoding ceiling:** an `imm8` is an ENCODING, not a law. #136 widened
`sub imm8` → `lea imm32` and 3x art went 651→655. But #159 is the inverse — the
height site is `push imm8`, `32*f` must stay ≤ 0x7F, and the patch **REFUSES
BOTH SITES rather than truncate**, because a doubled width with a 1x height
moves the clip from two edges to one and reads as a partial fix. **Declining
loudly is a legitimate outcome.**

---

### BRANCH E — "IT FLASHES / IT JUMPS / IT SNAPS INTO PLACE"

**Split the report first — these are three different families.**

#### E1. A 1-2 frame FLASH at a mode transition

**DECODED, NOT FIXABLE BY CADENCE. THREE CURES TRIED, ALL REVERTED.** The
sub-flyout items are **not windows** — they are blits into the container's paint
buffer, so no sweep can reach them. The window rect is corrected within ~1ms; the
paint buffer is still 1x for **20-36ms = 1-2 frames** at 54.5fps.

| tried | why it failed |
|---|---|
| `SetFlag` show hook | on-demand windows are BORN visible (`[this+0xC8]=0x8903`); there is no false→true transition |
| DATA pre-scale of the 8 HUD roots | **broke mayor mode** — composed HUD panels re-lay at runtime and have game-created children |
| born-2x sub-flyout (constants, then constants + 2x atlas) | `[+0xEC] = artH − 2*[+0xE8]` went −47; shipping both halves together still broke it, so a THIRD term is unidentified |

**`FlashGuard` (suppressing or deferring paints) is PERMANENTLY REJECTED** —
measured, did not fix the flash. The cure shape that works is **born-2x, never
suppress paints**.

#### E2. "It's wrong for a split second then snaps into place"

A **reactive pin**: the game re-lays on some event and our sweep corrects a tick
later. Cure = **born correct** (ENGINE §4.7 rows 3/4; #78 Data Views, #50
flyouts).

**Or it is OUR OWN corrective move.** #79c's cure was **DELETING a centring** —
SC4 had placed the dialog correctly all along. Before adding a pin, check
whether the thing that jumps is a latch we created (law 14).

#### E3. "It spawns wrong then snaps, on open or after the first click"

The corrective code exists and is correct — **it is simply not reached before the
first paint.** Ask WHICH PASS owns it.

**PROVE THE BRANCH EXECUTES BEFORE IMPROVING WHAT IT DOES.** Read the mode out
of the **live** ini and the `installed ... (mode N)` line out of the **log** —
never the default in a header. #137 shipped **two correct fixes on a dead path**:
the born-correct show path was gated behind `ShowHook`, which ships at 0, so it
had never executed once in ten versions.

Cures: give each consumer of a shared trampoline **its own gate** (law 59); add
the idempotent call to the tick as belt; gate the show path on **geometry**
(`w/h>0`) because the detour fires BEFORE the visible bit is set.

#### E4. "Correct on later uses, wrong on the FIRST use of a session"

An **uninitialised latch**, not a race — later uses are PRE-WARMED, not faster.
Prime the latch at birth (v2.36.2). Or see E2 — check whether the latch is ours.

#### E5. "It's missing on first open and appears after I scroll/click"

Two possibilities and they need different cures:
- **unpainted** — a hook landed after the first paint → ONE forced
  `InvalidateSelfAndParents()`, one-shot per window, never suppression;
- **if it SURVIVES a forced repaint it is a stale DECISION, not a stale
  frame.** The draw READS a flag some earlier code computed. v2.39.4 shipped the
  repaint cure on this symptom and cured nothing — the arrow flags
  `[0x118]/[0x119]` were computed at open from MIXED units (2x window, 1x item
  pitch = "nothing to scroll"). **Stop repainting; make the draw's INPUTS
  consistent at birth** (v2.39.5).

---

### BRANCH F — "IT'S DOUBLED / TILED / TWO SMALL COPIES SIDE BY SIDE"

**The count of visible copies is the SCALE RATIO.** 2 copies = 1x art in a 2x
cell. `GZWinBtn` picks its state cell as `imageWidth/4` (proportional, no pixel
constants), so an 88px slice out of a 176x44 strip spans TWO 44px states. **It
is ALWAYS a missing enlarged override at the TGI actually being drawn — never a
code-side stride bug** (#49).

| variant | cause | entry |
|---|---|---|
| a repeated PATTERN inside a box that is itself the right size | **src-follows-dst**: the class computes its SOURCE rect from the WINDOW, so under-sized art **TILES** instead of shrinking. Only known class: `cSC4WinAuraBar` `0x00797CC0`. Ship the art at the **WINDOW's** size — comparing art against the SOURCE rect looks fine and proves nothing | #72, law 35 |
| a custom lot installed AFTER our packages were built | **now handled automatically (#149, v3.0.0).** The boot scan indexes every DBPF under Plugins and enlarges uncovered ItemIcons before any consumer sees them. A well-formed third-party icon needs no action | #149 |
| a custom icon still broken after that | malformed art — a fractional authoring pitch (~45.36px against the engine's `imageWidth/4`), or no hover border. Escape hatch: `tools\itemicons\build_uncovered_icons.py`. Classify from disk BEFORE launching: `python tools\uimap\emu\sim_itemicon_states.py` | #149 |
| a stock icon a mod also ships | **coverage means OUR FILE LOADS LAST for that TGI**, not "the TGI is in one of our packages". Those two questions disagreed for exactly **1 icon in 392** — the one the user could see. Root `Plugins\` files load BEFORE subfolders | #139 |

**AN EXTENSION-FILTERED AUDIT THAT REPORTS "NO ART ANYWHERE" IS NOT EVIDENCE
OF ABSENCE.** `.SC4Lot`, `.SC4Desc` and `.SC4Model` are all DBPF archives and any
of them can supply art. A `*.dat`-only glob reported five Grutzehaus icons as
art-less and the "fix" shipped a 2x copy of an asset that path never requests —
inert, which is exactly why the symptom survived that build (#49).

---

### BRANCH G — "IT'S BLANK / MISSING / JUST A COLOURED BAR"

| variant | cause | first measurement | entry |
|---|---|---|---|
| a control renders as a **plain filled bar** — no glyph, no caption, just `fillcolor` — while identical siblings are fine | a **dangling art reference**: the `image=` TGI resolves to NOTHING. Classic cause: a **STALE DEPLOYED DAT** carrying clone refs from an older classification epoch | **diff the DEPLOYED script against the FRESH build output** — the diff is the diagnosis. stale and fresh dats have IDENTICAL sizes and entry counts; only content hashes catch it | #58 |
| a runtime-supplied image is 1x **intermittently** — right on one open, small on the next | **AN INSTALLED HOOK IS NOT AN EXECUTED HOOK.** Measured on #47: new dialog object, **25 instances hooked**, 13s on screen, **zero** draws through our hook | count **CALLS per user-visible event**, never installs. Then kick ONE `InvalidateSelfAndParents()` through **each hooked LEAF** — the ROOT alone does not reach them | #47 |
| the dashboard minimap blanks then jumps at city open | **NOT-A-BUG** — it does this at STOCK too (the game's own bake latency) | the stock control | #91 |
| a legend row has a swatch and no caption | **NOT-A-BUG at Power/Water** (stock since 2003; the exe's label table is one entry short). But the CAM variant IS ours to fix: CAM binds LTEXT `0xFF5D2E9F`, which exists in **0 of 118,896 records across 107 DBPF files**, with three sibling ids found in the same scan as positive controls. We ship the missing 20-byte resource; we never touch CAM's file | #147 |
| you are shipping INSURANCE for a state nobody has observed | **inert and broken look identical from the outside.** Make the probe **ADJUDICATE, not sight**: print `926x264 born/scaled 2x (insured)` vs `463x132 still 1x - insurance did NOT take` | #93, law 44 |

---

### BRANCH H — "IT'S PINK / MAGENTA / IT HAS PINK FRINGES"

**One cause, no exceptions.** Magenta `0xFF00FF` is the game's **TRANSPARENCY
KEY**. Any interpolating filter moves an exact key pixel to `0xFE01FE`; the key
test then misses it and **the key colour draws**. Every pixel bordering a keyed
region fringes.

**Free instant detector, no screenshot needed:** a package whose size moves the
wrong way. 1.5x has 2.25x the source pixels vs 2x's 4x, so a 1.5x dat must be
SMALLER than the 2x one. When bicubic shipped, `SelectiveArt-15x` went
**10.5 MB → 20.5 MB** against a 2x package of 11.4 MB (#143).

See §3 — the resampler is a FORBIDDEN cure and has been decided against twice.

---

### BRANCH I — "THE WHOLE DIALOG IS 1x / TINY, AND EVERY GATE IS GREEN"

**Nothing ever scaled it.** Usually a window a MOD **added**: it is in no target
list, has no stock twin to diff, and is never built, so no verifier can see it.

```
MWKID  0  id=0x10000005  (150,38 600x525)      <- CAM's info screen, live
.UI     area=(150,38,750,563) = 600x525        <- its own 1x design
```

Live rect == the `.UI`'s own 1x `area=` **to the pixel** ⇒ no lever ran.

```
python tools\uiscripts\winning_corpus.py    :: third-party winners MUST be 0
```

**A GATE THAT ONLY ASKS ABOUT YOUR OWN WORK CANNOT SEE WORK YOU NEVER
STARTED** (Law: the census runs both directions). CAM's Village Hall info screen rendered at 1x under 1.5x
fonts for the **entire life of the project** with every gate green, because every
gate asked *"is what we built still correct?"*. **Run the census in the other
direction: enumerate what EXISTS and subtract what is handled.** (#154)

Then watch for the trap that followed: v2.97.0 scaled the window (285→428) and
the bitmap (285→429) and left `imagerect=(0,0,285,30)` at 1x, so 143px of every
row stripe was bare. **A blit has THREE numbers — source, CROP, destination —
and scaling any two of them is not a partial fix, it is a new defect** (law 73).

---

### BRANCH J — "IT CRASHED"

**STEP 1 — READ THE GAME'S OWN EXCEPTION REPORT.** SC4 writes one with the
faulting EIP and the registers. Windows WER is a structural null here.

**STEP 2 — did you hook something?** Two crashes in one session came from
guessing a calling convention:

| crash | cause | rule |
|---|---|---|
| `PRIV_INSTRUCTION` at a garbage EIP, EDX still holding `0x00AC1400` | slot 20 declared `__fastcall` with TWO stack args, inferred from two visible pushes. **`__thiscall` is CALLEE-CLEANUP**: guess the arity wrong and the thunk cleans the wrong number of bytes | only ZERO-arg slots may be hooked by a typed thunk. **Unknown arity = a NAKED TAIL JMP** — it never returns to us, so it never cleans anything |
| `ACCESS_VIOLATION` at `0x0099C4A1` with ECX = 1 | `PlotPresent` declared `__stdcall`. It is a VIRTUAL: `__thiscall`, `this` in ECX, no stack args | **for any `__thiscall` target, write `__fastcall(void* self, void* edx)`.** Never infer convention or arity from a disassembly excerpt |

**STEP 3 — where did it happen?**

| context | cause | entry |
|---|---|---|
| the game dies on a **second-level menu** you did not validate | our disaster-derived surgery installed itself on a foreign menu. The container's CLASS check passed — the vehicle sub-flyout is the SAME class. **Class identity is necessary but NOT sufficient; the LAYOUT differs.** Cure: a known-menu gate; log `SUBSKIP` when it declines | v2.22.1 |
| city open, after you added scaling to `PostCityInit` | **MEASURED: ~25 windows of `SetW`/`SetH` there CRASHES the city open.** The threshold is not window count — two byte writes (`[+0xFD]`/`[+0xFE]` + `InvalidateSelf`) are safe at the same site. **Mutating window GEOMETRY during city init is categorically different from writing flags, at any size** | #89 v2.41.15 |
| after a "fix" to a window that owns a render surface | you called `Init` on a live surface. Destroy + recreate. If the subtree owns a one-shot surface, the scale and the recreate are **ONE action** — splitting them is the v2.41.15 crash | v2.21.1, #89 |
| region zoom | **a structure DERIVED from another was left behind when the source was resized.** Here the derivative was a hit mask, so it failed on mouse movement rather than on screen. Cure: **rebuild from pristine, never resize** | #132 |
| works in city 1, dies or silently skips in city 2 | a function-local static holding a **dead pointer**. Clear it in `Disarm`; `gGaugeEpoch` is the pattern | #92 |

---

### BRANCH K — "THE CLICK DOESN'T LAND / IT HITS THE WRONG THING"

| variant | cause | entry |
|---|---|---|
| a back arrow / control in a sub-flyout is dead at one tier | **the sweep silently DECLINED every 3x sub-flyout.** The decline was at a gate that logged nothing: the `SUBGEO` dump sat AFTER the `atNative/atTarget` test, so the one case that needed explaining produced no output at all — absence read as noise for two sessions | #134 |
| you moved a sprite and the click stayed behind | move the **hit box** with the sprite. The coupled pair is sprite + hit zone as well as container + sprite | #95 |
| a flyout's hit zones are offset | the ring+strip+bar are ONE welded shape; and the router is first-claim-wins with a two-gate hit model | `tools\research\` flyout hit-test playbook, `tools\flyout-sim\emu_hittest.py` |

**LOG BEFORE THE GATE, AND GIVE THE INSTRUMENT A POSITIVE CONTROL.** `SUBCAND`
prints every candidate pre-gate; `SUBSWEEP` proves the block was entered, so
silence below it is a MEASUREMENT rather than an absence.

---

### BRANCH L — "IT'S SLOW / IT HANGS"

| variant | verdict | entry |
|---|---|---|
| the **first** city open of a session takes ~a minute with a big plugin set | **MEASURED, no lever.** 54.3s wall / 53.1s CPU / 934 MB in 1,902,959 reads vs 9.2s / 3.3 MB / 4,008 reads for city #2. `CPU/wall = 0.92` = a saturated core; a 15s stretch did ZERO disk. **CPU-saturated, not disk-blocked — do not offer a prefetch cure** | #141 |
| the game hangs during city load after your change | **walking the tree inside `PostCityInit` HANGS the game** — measured, not feared | `UiSpike.cpp:14`, `:4357` |
| you want to run earlier than the ~1-2s post-arm gap | **THE WHOLE MESSAGE-QUEUE FAMILY IS DEAD.** A posted `WM_APP` beat `WM_TIMER` by 15ms (one timer period): the game does not pump messages **at all** during the city load tail | #89 v2.41.0 |
| shutdown spin | #104/#105/#107 — the WinMgr valid set is wholesale empty (1543 buckets, 0 entries) before teardown. `SpinProbe` is built; awaiting a capture | #104 |

**A BROKEN INSTRUMENT THAT CANNOT DECLINE TO SPEAK WILL FABRICATE.**
`Trace-Threads.ps1` printed *"ONE thread does essentially all the work"* from
**20 ms sampled across 20 threads** while the process had burned 186,000 ms —
`Win32_Thread` returns zeros when the querying shell is not elevated and the
target is. **Make every summary RECONCILE against an independent total first and
refuse to render a verdict below a stated threshold.**

---

### BRANCH M — "THIS WASN'T LIKE THIS BEFORE"

**THAT IS A BISECTION BOUNDARY, NOT AN OPINION** (Law: bisect, don't revert). Four defects were
reported minutes after a deploy, so both of that deploy's changes were reverted.
**The reverts fixed nothing** — the cause was a change from eight hours earlier.

> **WHEN A REVERT DOES NOT MOVE THE SYMPTOM, THE ATTRIBUTION WAS WRONG. STOP
> REVERTING AND GO BISECT.**

Then check, in this order — these are the three ways a fix silently fails to ship:

1. **Did every consumer get rebuilt?** #150: `kCellCounts` was corrected and
   **only three of nine packages were re-emitted**. The user's own sentence was
   the discriminator: *"Budget fixed. Thumbnails still broken."* — Budget's art
   is in SelectiveArt (rebuilt), thumbnails in ItemIcons (stale).
   **And `gate_namicons.py` had been RED for two hours, unread.**
   → **RUN THE GATE SUITE BEFORE THEORISING.**
2. **Is a build INPUT stale?** The three upscale trees (`tools\upscale\preview\`,
   `preview-15x\`, `preview-3x\`) have a repo regenerator —
   `tools\upscale\Rebuild-Corpus.ps1` maps `1.5→preview-15x`, `2→preview`,
   `3→preview-3x` and writes them. Other inputs are hand-made or
   separately generated — including the three `.txt` role lists, which
   `Rebuild-Corpus.ps1` confirms are produced separately by
   `find_cell_strips.py` and friends. Same shape: `cell-strips.txt` /
   `nine-slice.txt` / `no-snap.txt`, `refmap-<tag>.csv` (dialog-static reads
   the one selective-safe wrote — **hard ordering dependency**), `nam-up-*`,
   `uncovered-up-*`, `extracted-plugins\`.
   **The permanent hazard:** a hand-typed `Upscale2x.exe` line without
   `--cell-strips` / `--nine-slice` / `--no-snap` un-ships all three fixes at
   exit 0 with every gate green, because each gate measures the new tree
   against itself. `tools\packages\PACKAGES.md` therefore contains **zero**
   `Upscale2x.exe` invocations: step 1 runs `upscale\Rebuild-Corpus.ps1`, the
   single source for the command. It appends all three derived lists itself
   and refuses to run when a list is **missing** (no override) or **empty**
   (overridable only by explicitly passing `-AllowEmptyLists`). Use `-DryRun`
   to print the exact command line without spending a corpus rebuild; that is
   the cheap answer to "did we pass the lists?". **Never hand-type the
   upscaler command, never copy it into a doc, run the script.**
3. **Did you rebuild a tool binary and its output together?**
   **LAW: NEVER REBUILD A TOOL BINARY AND ITS OUTPUT IN THE SAME CHANGE.**
   `Upscale2x.exe` is not version-checked against `Upscale2x.cs`, so `Build.ps1`
   ships every uncommitted source edit since the binary was last produced.
   Hash the outputs against the previous build FIRST and treat any unexplained
   delta as a stop.

**To prove a package is unchanged, diff its ENTRIES, not its bytes.**
`DbpfPack` is **non-deterministic** — two runs from byte-identical inputs give
different SHA256s at the same length with `CHANGED: 0` payloads. A whole-file
hash once reported *"2x CHANGED"* on a correct fix (#145).

**A status instrument wrong in the SAFE-LOOKING direction is worse than none.**
`Set-Tier.ps1` reported all nine packages *"dependency-gated off"* while all nine
were loading, because `.dat` enumerates before `.dat.x1-disabled` and a plain
hashtable assignment let the disabled twin overwrite the active one (#144).

---

## 3. CURES THAT ARE FORBIDDEN, AND WHY

Each of these has been tried. Do not re-propose one without new measured
evidence that addresses the entry named.

| forbidden | why | entry |
|---|---|---|
| **`--hq` / bicubic / bilinear / any interpolating resampler, at ANY factor** | magenta `0xFF00FF` is the transparency key; interpolation turns an exact key pixel into `0xFE01FE`, the key test misses it, **and the key colour draws**. Shipped a pink Mayor Rating bar and pink outlines within one launch. `README.md:505` had rejected it **in writing, years earlier**, in the row describing the very tool being edited. **DECIDED TWICE.** And the first "revert" rewrote only the COMMENT above the statement — the tool went on printing `Mode: high-quality` and regenerated the whole tier bicubic again. **A comment is not code; a log line that contradicts your edit means the edit did not land** | #143 |
| **global height-snap removal** (`sNoHeightSnap` as a default) | moves **791 of 2280** pristine sheets and puts #143's white-seam fix back in play across the whole game. Scoped variants only, by TGI group or a derived list | `Upscale2x.cs` |
| **`--height-exact-strips`** (the scoped version) | built 2026-08-15, shipped, and **broke the "?" button** `{46a006b0,14415860}` while not moving the two hairlines at all. REMOVED from both builders; the flag remains in `Upscale2x.cs`, unused. The reasoning ("a horizontal strip has no vertical cell divide") is still sound in the abstract — it is simply not the cause of those lines | #162 |
| **runtime upscaling** | user order 2026-08-14: it would be unbounded and would end the property that every scaled pixel comes from a diffable build step. **And the blit cannot stretch anyway** — a 2538x6102 dest changed nothing; `Blt` is a 1:1 copy clipped to dest | `UiSpike.cpp:2984` |
| **whole-frame upscaling** | the northstar is *native high resolution with the UI ELEMENTS enlarged*. Whole-frame upscaling is the documented wrong turn | `project-sc4-ui-scaling-northstar` |
| **killing the game process** | it runs **ELEVATED** and holds the DLL and the dats open. `_tests\Deploy-OnGameClose.ps1` waits for it | START-HERE rule 1 |
| **suppressing or deferring paints (`FlashGuard`)** | measured: did not fix the flash. Permanently rejected. Cure shape is born-2x | #50 |
| **moving a control's POSITION in a `.UI` to fix its SIZE** | up to 2px at 1.5x; applied to 177 buttons it slid a 21-face grid inside its frame. Reverted v2.94.0. Change the SIZE of a **leaf** instead — nothing moves, bounded by 1px | #148 |
| **resizing ART to fit a window** | **art binds by TGI, and flyout strip items are created at RUNTIME and appear in NO `.UI`** — so a builder-side conflict check is blind by construction and reported 0 conflicts while being wrong. **Editing geometry in a `.UI` has the scope of that `.UI`; editing ART has the scope of the whole game** | #148 |
| **widening `CellUnit`'s divisor set** | `LCM{2,3,4,6,8,12,16,24}` = 152 mismatches, the worst option except doing nothing. The set is `{3,4}` and it was MEASURED. **LCM-of-everything is safe against cutting and unsafe against fitting** | #149 |
| **extending a short `imagerect` to its art** | broke the thumbnail flyouts **twice** — a `<=24px` tolerance widened small-atlas cells across two cells; the exact 1x-source test widened the LAST cell of each strip, which legitimately ends at the sheet edge. And `gate_imagerect_vs_art.py`'s integer-tier under-read count is a **BASELINE, not a failure** | #148 |
| **"fixing" `GZWinMoveTo` to `seat + delta`** | it is a **RELATIVE** move. Changed on the strength of its NAME, cost two builds and a user round-trip. The call site's comment says so | #145, #146 |
| **mutating window GEOMETRY inside `PostCityInit`** | ~25 `SetW`/`SetH` there crashes the city open, at any size. Flags + `InvalidateSelf` are safe at the same site | #89 |
| **resizing a render surface in place / calling `Init` on a live one** | corrupts it. Destroy and recreate, and treat scale+recreate as ONE action | v2.21.1, #89 |
| **any message-queue trick to run earlier during city load** | the game does not pump messages **at all** during the load tail. `WM_TIMER` cadence, `ShowHook` and `WM_APP` all die on that one fact | #89 |
| **region rotation** | tiles are baked at save time; 0 refs to rotate/angle/yaw across 197 decompiled functions, against a positive control | #133 |
| **re-pinning an exe fingerprint because a gate says "fingerprint mismatch"** | the 4GB patch silently blinded every exe-pinned gate. Procedure: bypass, run **every** byte-level assertion, re-pin only if all pass, and write down that you did | REGRESSION.md "THE 4GB PATCH…" |
| **changing the sweep cadence to win a race** | it already runs every ~16ms and `WM_TIMER` is lowest-priority. Remove the race instead | TRIAGE §5 |
| **measuring text through `cIGZFontSys`** | MSVC reverses overloaded vtable groups; you hit the wrong slot (null, then a swallowed fault) | law 27 |

---

## 4. BEFORE YOU BELIEVE A NULL

**NULL IS NOT EVIDENCE.** State the positive control: what would this instrument
have printed if the thing existed, and has it *ever* printed that?

**TWO BLIND INSTRUMENTS AGREEING IS WORTH EXACTLY AS MUCH AS ONE.** Corroboration
counts only between instruments with **independent failure modes** (law 34).

### The measured blind spots — check yours against this list

| instrument | blind to | note |
|---|---|---|
| `[Probe] EdgeBlt` | **EVERYTHING, by default.** It lives in the slot-29 `BltClassThunk`, which is installed only by `EnsureBufferClassBltHook()` from the god-flyout birth path. `ThinBlt` was given a self-arming block (`THINBLT armed — slot 29 hooked`); **`EdgeBlt` was not.** Setting `EdgeBlt=N` without opening a god flyout is a GUARANTEED NULL and nothing in the log says so | **two capture runs were burned on exactly this** (#162) |
| `[Probe] IconFit` / `IconCover` / `IconCentreOff` | doubly lazy — the `BltStripThunk` swap also requires `gStripProbe > 0`, default 24, **decremented to 0 by ordinary logging**. A probe armed late in a session sees nothing | map §6 |
| all `[Probe]`/`[Disaster]`/`[Flyout]` keys | read **ONCE on the first pass** unless `[UiSpike] LiveTune=1`. And the whole block lives inside `ScaleGodFlyouts` — **in region screen or menus, none of them are ever read** | map §6 |
| `SetFlagDetour` (show hooks) | fires only on a **0→1 transition**. A window created already visible never transitions | #89 refuted `ShowHook=2` |
| `RGKID` | stops above deeply-nested children — it skipped the region rating bar twice | law 20 |
| the UI buffer class | never composites to the screen, so a blit hook on it cannot see full-screen art | — |
| `tools\uimap\census.py` | scans `0xD4`/`0xDC`/`0xE0` but **not `0xD8`**, so every `call [reg+0xD8]` builder is invisible to the offline model | — |
| `constants.json` | **cannot represent a re-encoded block at all** (3 of the 8 #57 sites) | — |
| `LogMinimapBuffer` | samples 5 points of 4096. **It cannot see a block.** Five diagnoses died on it before `MMGRID` printed the buffer | #146 |
| `find_tgi.py`'s ancestor | carried a hard-coded list of seven archive names while the install ships **nine**. **Derive the inventory, never list it** | #140 |
| any `*.dat`-only glob | `.SC4Lot`/`.SC4Desc`/`.SC4Model` are DBPF too | #49 |
| a stock capture taken before 2026-08-05 | **SC4's plugin scan is RECURSIVE** — a stash INSIDE `Plugins\` disables nothing. 132 dats + 30 DLLs loaded through every "stock" capture for a whole session. Compounds with the **THIRD** `FontStyle.ini` in `<install>\Apps` | rule 3 |
| one linear `md.disasm()` over `.text` | capstone's linear sweep STOPS at the first undecodable byte. 37,426 instructions for 6,787,072 bytes = ~181 bytes/instruction, impossible — it covered ~2% and reported "0 candidates". **Locate call sites by byte pattern, then disassemble backwards** | #159 |

**And the inverse trap:** *"a guard that fires proves something is wrong; it
proves nothing about WHAT."* `id 0xAA243E23 occurs 0 times` was **true**, and the
conclusion drawn from it was false — the real cause was a `\b` turned into a
literal backspace byte by machine-generating a regex through a string template.
A correct fix was reverted on that (#153; Law: a guard firing proves something is wrong, not what). **Do not machine-generate
code containing regexes.**

---

## 5. THE GATE INDEX — which gate answers which question

**THE INTEGER-TIER LAW: any new metric or gate MUST read exactly ZERO at 2x
and 3x, or it is measuring itself.** `ScaleDim` returns early and `ScaleRound` is
exact at an integer factor, so a metric that is nonzero there is reporting its
own sampling pattern. `gate_row_banding.py`'s first version probed a fixed ±2
rows at every factor; once a ridge is f px thick that probe lands inside it and
2x/3x scored as "ragged" as 1.5x. **The mandatory integer control caught it —
had it not been there, that would have shipped as fix number seven** (#162).

| question | gate | integer control |
|---|---|---|
| does the shipped art cover the sweep-scaled window? | `python tools\uimap\emu\gate_art_vs_window.py` | HARD — `NEW at f=2 (must be 0)`; the f=1 shortfall is the stock baseline, subtracted |
| does a state-strip button's window equal its art cell? | `python tools\uimap\emu\gate_btn_undercover.py` | 15x/2x/3x; integer no-op by construction. Read the RESIDUAL lines, not the verdict (§A2) |
| do abutting siblings SEPARATE after parent-frame rounding? | `python tools\uimap\emu\gate_abut_1_5x.py` | HARD — FATALs "MODEL IS WRONG" |
| is the minimap blit size legal at every tier? | `python tools\uimap\emu\gate_minimap_snap.py` | FACTORS=(1.5,2,3) |
| are the NAM ItemIcon overrides present, exact, and winning? | `python tools\uimap\emu\gate_namicons.py` | TIERS 15x/2x/3x + 5 negative controls |
| do patch families overlap or split ownership of a constant? | `python tools\uimap\emu\gate_patch_families_combined.py` | exe-level. **Known gap:** tables registered nowhere (e.g. the cost-box family) are invisible to it — the exact gap it was built to close, still structurally present |
| does a fractional tier over-extend a partial crop? | `gate_imagerect_vs_art.py` | **the integer tier IS the baseline** — its under-read count is a BASELINE, not a failure; closing it broke thumbnails twice |
| "cell must equal window"? | `gate_btn_cell_vs_window.py` | inverted — **420 mismatches at 2x AND 3x is the proof the metric is not a defect metric.** REPORT ONLY, exit 0 always; records a FALSIFIED law |
| third-party `blttype=normal` blits — all three numbers | `gate_tp_bmp_fit.py` | control is **1x vs tier**, not integer-tier. **Has been wrong twice — read its header.** Negative control = a script extracted back out of a deployed dat → 48 findings |
| the graph-legend byte patch | `gate_graphlegend_leftanchor.py` | f=1 reduction. **THE BYTE GATE** — 127 checks. `--emit` prints the exact hex `CodePatches.cpp` must write. **Law (hand-encoded bytes): diff them against `--emit`, always** |
| the advice-row / ordinance / intro-video / graphs-band patches | `gate_advice_rowx.py`, `gate_ordinance_namex.py`, `gate_introvid.py`, `gate_graphs_banddock.py` | all carry f=1 reduction or 6 mandatory negative controls |
| sub-flyout native offset per tier | `python tools\flyout-sim\gate_subnative.py` | 3 tiers |
| a proposed blit-REWRITING predicate | `gate_iconfit_rule.py` | f∈(1.5,2,3) + 72/72 perturbation kills. **The predicate that shipped the white-line regression is REQUIRED to go red** |

**Pixel instruments (the only things here that look at an image):**
`render_flyout.py` (#148 — offline compositor, magenta keyed to alpha, 1:1 blit;
`--script <iid> --tier {15x,2x,3x} --rule {edges,size} --states N --out DIR`),
`render_dialog.py` (#155 — static `.UI` + shipped art composited and diffed
against a 1x NEAREST upscale; `<iid> [--tier 15x] [--out DIR]`). **Locators, not
verdicts** — see branch A1.

`crosscheck.py` exits 0 with **9 named SKIPs and 8 guarded DEFERRALS** — that
is **not** full coverage, and it says so.

---

## 6. THE LEVER LADDER — PICK THE SMALLEST BLAST RADIUS THAT WORKS

| lever | reaches | scope | cost |
|---|---|---|---|
| change the **SIZE** of a leaf window (DLL, `GetChildCount()==0`) | that window | smallest — nothing moves, ≤1px, no-op at integer factors | build |
| **runtime sweep** (`UiSpike`) | **any window its walk actually reaches — the ROOT of a `kDataScaledSubtreeIds` panel IS scaled and anchored, but the walk STOPS there**, idempotent via `scaleMap` (keyed on POINTER) | cannot reach content painted inside a buffer, or anything re-laid after the sweep — **and NOTHING BELOW a `kDataScaledSubtreeIds` root: `ScalePanelRoot` scales/moves the root, then RETURNS before its child loop, so no descendant is walked, at any tier — the return has no factor test. TEN ids — READ THE ARRAY in `src\UiSpike.cpp`, do not trust a hand-list: advisor strip `0x6A15C767`, three Graphs roots, two U-Drive-It roots, AND four budget/taxes roots (`0xAA3AC002`, `0xCA4C332D`, `0xAA3AC001`, `0xAA3AC000`). Below the root, geometry ships pre-scaled in the DATA (`double_subtree_areas`) and the number in the `.UI` is the number on screen — so a 1.5x defect on the advisor row is a BUILDER defect, never `ScaleSubtree`, which provably never runs there. The ROOT's own rect is the opposite: it is the sweep's OUTPUT, not the data's. Scope, stated no stronger: `ScaleSubtree` has NO such gate (`IsDataScaledSubtreeId` has one call site) — the guarantee holds because these roots are only entered through `ScalePanelRoot`.** | none |
| **`.UI` static doubling** (`DialogStatic` TARGETS) | dialogs the sweep does NOT scale | that `.UI` only. **Double-scales anything the sweep also reaches** | rebuild |
| change a window's **POSITION** in a `.UI` | that `.UI` only | up to 2px at 1.5x. **Judge it in the densest grid it touches** | rebuild |
| **byte patch** (`CodePatches`) | literal immediates in a builder | cannot reach runtime-composed values, or >127 in an imm8/disp8 without re-encoding | build; **verify bytes before write, always** |
| **draw hook** (`GZWinBMP` vtable `0x00ADF6A0`, slot 88) | runtime-supplied images drawing 1x | nothing not drawn by that class | build |
| **art data** (`SelectiveArt` / `DialogStatic` / `CODE_BOUND_TGIS`) | anything whose pixels come from a dat | **THE WHOLE GAME** — art binds by TGI and runtime-created consumers appear in no `.UI` | rebuild + entry-count update |

**Three blit behaviours exist — do not assume the first:**
1. **dst follows src** — `GZWinBMP` plain path: 2x art ⇒ 2x draw.
2. **stretch** — the 9-slice EDGE path.
3. **src follows dst** — `cSC4WinAuraBar`: under-sized art **TILES**.

**Before writing the plan, state:** the **prize** vs the **blast radius** (law 29
— refuse upside-down trades); the fix as **math that reduces to stock at f=1**;
the **acceptance test decided in advance**, with a positive control for any null
it relies on; and the **trap signature + revert** for each way it can go wrong.
Then work it **one item per build** — after six missed fixes, a result that
cannot be attributed is worth nothing (#162).

**And a package is not finished until it is in BOTH `Deploy-OnGameClose.ps1` AND
`Test-DatIntegrity.ps1`.** Three packages have rotted from exactly that omission,
and every one of them looked green.

---

## 7. IF NOTHING IN THE TREE MATCHES

1. **Run the stock control anyway.** One launch, no build, and it has closed
   three "regressions" outright.
2. **Ask for the case with a control in it** (Q4). It is worth more than any
   instrument pointed at the broken one alone.
3. **Build the instrument that can SEE the defect class, not another one that can
   only COUNT.** Paid for twice: `MMGRID` for the minimap (#146) and
   `render_flyout.py` for the flyouts (#148). When a defect is about the CONTENTS
   of a buffer, **dump the buffer — a picture of it, not a sample.**
4. **If the symptom matches a row but the current diagnosis says "unreachable",
   suspect the DIAGNOSIS** (law 34). That exact combination has been wrong twice.
5. **Check our own documents first.** #162 is the northstar case: five fixes and
   three probes were spent reasoning from mechanisms while a comment at the top
   of our own `UiSpike.cpp` named the exact defect class and the exact cure.

---

*Distilled from `_tests\REGRESSION.md` (~162 entries), the blocks in
`src\UiSpike.cpp` and `tools\upscale\Upscale2x.cs`, and `START-HERE.md` §3.
When you close a defect, add its branch row here in the same session — a
failure list without mechanisms just gets retried in a different order*
(law 23).
