# Tasks #55 + #47 + #53 — v2.25.0-runtimeimg (2026-07-30)

DEPLOYED and suite-green: `ALL PASS (15 dats + 3 fonts + 2 DLLs + frozen hash)`
+ `ALL PASS (14 cases + 5000x2 sweep)`. All work below was done OFFLINE from
disassembly + archive scans — zero game sessions, per the user's directive.

## THE #55 ROOT CAUSE (measured, kills the intake's prescribed fix)

The intake said "generate 2x for EA32F104". **That is impossible and was never
the fix**: a full any-type index scan of all seven shipped archives (new
instrument `tools\dbpf\find_tgi.py`) proves `{46a006b0,ea32f104}` and
`{46a006b0,6b998f30}` exist in NO archive — the .UI refs are **DANGLING
placeholders**. (`ea7f0eae`, the 768x600 splash bg, is also dangling;
`ea7f0eaf` is real.)

What actually paints the picker cells (disasm, exe 1.1.641):

- Picker-open fn **0x770420**: selects script `4bf325e8` (vehicle) vs
  `abfaef15` (ped) via `sbb/and/add` on the bool arg; cell count 28 vs 14 at
  `[edi+0x60]`; tabs 0x2c201cb0/b1/b2; cell buttons id `0x34560000+i`.
- Cell-populate fn **0x76FDB0**: per item reads exemplar props `0xEBFC5E26`
  (type), `0x2C0C922E` (earned gate), `0xEBFC5FBA` (sort), then QIs child
  `0x23450000+i` with iid `0xC12CEA13` (**GZWinBMP**) and calls its
  SetImage (vt[0x10]) with the image loaded by **0x602B70** from
  **{group 0x4C06F888, instance = exemplar property 0xEBFC5E5E}**.
- The Select-A-Sim builder (**0x775CC0**, script 0a243d80 @0x775D05) binds NO
  4C06F888 constants — its 22 placeholders (`imagerect=(0,0,36,41)` = portrait
  dims) receive runtime-GENERATED faces (Path 4). Different fix (BMPX hook).

Group 0x4C06F888: **112 entries, all type 0x856DDBAC, all in SimCity_1.dat**,
2x/1.5x/3x previews already existed (112 each). Only .UI refs to the group =
the two My Sims style thumbs (already-scaled subtrees) → whole-group in-place
2x is collision-free BY MEASUREMENT.

## GZWinBMP draw (disasm 0x9BC325 — enables the #47 hook)

- vtable 0x00ADF6A0, slot 88 = 0x9BC325, **151 slots** (measured: 151 code
  ptrs then 0).
- flags live on a holder object embedded at `[this+0xd8]` (its +4 = the image
  ptr at `[this+0xdc]`), tested via holder `vt[10](bit)`: 0x10 = has
  imagerect, 0x20 = 1:1 bitmap mapping (dst += src.l/t), **8 = EDGE 9-slice**
  (src /= 3 then helper 0x8D8800, MANY blits).
- PLAIN path: ONE `ctx->vt[38](img,&src,&dst)` with
  `dst = {areaL, areaT, areaL+srcW, areaT+srcH}` — **dst follows the SOURCE**.
  Same ctx slot 38 as the gauge class.

## WHAT SHIPPED (v2.25.0-runtimeimg)

1. **Data (#55):** `build_selective_safe.py` CODE_BOUND_TGIS += the whole
   4C06F888 group (reads dbpf/extracted-png-tgi.csv). SelectiveArt 506 → **616**
   at all three tiers. `build_dialog_static.py` new `RUNTIME_BOUND_2X` map:
   the two U-Drive-It picker scripts' placeholder imagerects now scale
   (4bf325e8: 28 rects, abfaef15: 14) because their runtime pixels are 2x;
   verify_doubled threads the exception. 0a243d80 deliberately untouched.
   DialogStatic stays 259/tier.
2. **Builder warnings (the intake's cross-cutting ask):** both builders now
   print `WARNING LEFT1X {g,i} ... DANGLING (runtime-supplied)` vs
   `MISSING-2X (will draw wrong)` classified against the PNG store. Current
   warnings: ea32f104-in-0a243d80 (expected, hook handles) + ea7f0eae splash.
3. **Code (#47): the BMPX hook** in UiSpike.cpp (namespace before
   ScalePanelsUnder, after the GAUGE namespace). ONE shared patched vtable
   copy (all GZWinBMPs share class vt 0x00ADF6A0 → no per-instance table, no
   cap, no leak on transient reopen, nothing for Disarm). Draw thunk: latch
   win W/H + id, skip EDGE mode (holder vt[10](8) exactly as the game tests
   it), swap ctx vt to a copy with slot 38 → BmpCtxBltThunk for THIS draw
   only. Blt thunk: one-shot, only the follows-source signature
   (dstSize==srcSize), scale dst about its own origin, self-limited to the
   live window (already-2x content or unscaled window ⇒ m clamps ≤1 = no-op).
   Positive class check vt==0x00ADF6A0 && vt[88]==0x9BC325 (law 3).
   Scopes: city pass → My Sims eight roots + **Graphs 0x8A8B5B71/72,
   0x0A4A8176**; IncrementalPass → pickers 0x6A243D9E + 0xCBF32603 searched
   from pMainWindow (covers view-parented too).
4. **#53:** kMaxChildrenPerLevel 96 → **256** + one-shot ERROR log on
   overflow in ChildSnapshot::Callback; kFgMax 6 → **12** (arrays kFgMax-
   sized, FlashGuardThunk<6..11> added; template is index-agnostic, checked).

## GRAPHS (intake bug 6) — hypothesis KILLED offline

I-6bc9065a (30KB) and I-ea2871aa (47KB) are **DIFFERENT panels, not stale
copies** (different roots visible, different sizes). Both are staged; every
art ref in both is 2x-in-place (refmap-verified, incl. abbead86/ebbeae28 —
"not retargeted" is what in-place looks like). All three roots' children are
standard GZWinBMP/Btn/Text — the chart line is controller-painted with NO
child window. BMPX now covers the roots' BMPs as self-limiting insurance;
if the chart LINE stays 1x it needs the live DPROBE pass (only remaining
Graphs unknown).

## EXPECTED LOG LINES NEXT GAME RUN

```
UiSpike: BMPX N instance(s) hooked under 0x698894D3 (city, x2.00)
UiSpike: BMPX N instance(s) hooked under 0x6A243D9E (dialog, x2.00)   <- picker open
UiSpike: BMPX draw id=0x22220000 img 36x41 win 72x82 -> dst 72x82 (x2.00)  <- portrait
```
- Picker thumbs (42x42→84x84 art): BMPX draw lines for them should clamp
  m→1.0 and NOT appear (dst already fills) — if one appears with x2.00, that
  vehicle's thumb instance is outside the 112 (report it).
- Zero `SUBSKIP`-style faults; edge-mode BMPs never logged.

## STILL OPEN (needs the game)

- #48 both halves (U-Drive-It ring dock = MCAL measure-only; sub-flyout strip
  = StripDump/DGP-OPEN before kParents opt-in). U-Drive-It's menu opens from
  the MY SIMS panel (the "U Drive It|Pick a land..." button lives in
  aa1f1f57), not from a toolbar flyout script.
- Graphs chart LINE + Building Style boxes: DPROBE live.
- Verify: pickers, My Sims faces, car/bike thumbs, and the standing
  RUN-SHEET-NEXT-SESSION.md Part 1/2.

## v2.25.1-graphsborn2x (2026-07-30, same day) — GRAPHS FIXED FROM OUR OWN LOG

User screenshot post-v2.25.0: white sheet off the panel's right edge +
radio columns overflowing. NO new measurement was taken — the deployed
build's own DGPKID dumps and sweep log already contained the answer:

- All three roots PERFECTLY placed (5b71 990,600 1092x896; 5b72 =
  +(0,604); band = +(10,648)) → the roots were never the problem.
- `incremental panel 0x8A8B5B71 - 1 windows scaled` every 1-2 s = the
  game RE-CREATES a chart child per data refresh, BORN at live
  (already-2x) size; the recursing sweep doubled it again. Math check:
  canvas design (14,32,502,288) x4 at root abs 990 → right edge ~2998 =
  the off-screen white sheet; radio columns design x 0/170/340 → live
  0/680/1360 = exactly 4x. (BMPX then stretched the displaced BMPs'
  ebbeae28 backing = solid white, which is why the sheet was VISIBLE.)

CURE = the advisor-strip architecture (law 1: fix it in DATA):
- `double_subtree_areas` on all three roots in BOTH scripts
  (I-6bc9065a: 12+6+19 areas; I-ea2871aa: 12+6+37) at all three tiers;
  markers stay 1x (the doubler's baked-in skip).
- All three roots added to `kDataScaledSubtreeIds` → the sweep scales
  ONLY the roots; children are born 2x from data and game-created
  refresh children inherit correct live metrics and are never touched.
- SelectiveArt stays 616 entries/tier; suites green; deployed (game was
  closed).

If a small residual artifact remains after this (a child re-imposed with
1x constants at select time), that is the DVPIN class — pin from the .UI
design table, do NOT re-enable child sweeping.

## v2.25.2 fonts (2026-07-30) — the clipped tick numbers

Post-v2.25.1 screenshots: the panel composes correctly, but the y-axis tick
numbers clipped to ")000" and the plot reads over-wide. Disasm of the chart
creation site (0x76D3D0) settled both offline:

- The chart WINDOW is correct: it takes the canvas 0x8A4B0AA0's born-2x
  area verbatim (GetArea → sub_9D7D97 → ChildAdd on the root; no
  constants) — do not touch it.
- The chart fetches its text styles BY GUID from the style manager:
  0xE9C86B5F (Legend) + 0xE9C86B6E (**ChartTickText**). Our FontStyle
  doubled ChartTickText 10→20, but the controller right-aligns the tick
  numbers into a label column whose width is a HARDCODED 1x constant →
  clipped digits. Same shape as the HTML engine's stock-size clone styles.
- FIX: `KEEP_STOCK = {"ChartTickText"}` in make_fontstyle.py (stays 10 at
  every tier), candidate + all four deployed FontStyle files updated; the
  stale --selfcheck fixed (now tolerates exactly the two HTML clone styles
  and the KEEP_STOCK rule; SELFCHECK OK, 88 styles).
- REMAINING (cosmetic, needs a byte patch): the chart's internal margin
  constants (label column / plot insets) are 1x code immediates — patching
  them per-tier would let ChartTickText scale again. The creation pair
  {0x6534284A, 0xCA4AD545} is a resource-key/service creation ([0xB43CA8]
  vt[0xC]) — the class vtable was NOT identified yet; 0x6534284A has 128
  creation sites (a generic host). Pick this up only if the user wants
  bigger tick numbers.

### ⏸ ON HOLD (user, 2026-07-30): Graphs chart interior

The user has put further chart-interior work ON HOLD — the tick-number
size and the internal margin proportions are now a STOCK-PARITY item:
capture the standard-resolution Graphs panel (Set-StockCompare) and judge
the 2x rendering against that A/B before touching anything else here.
What stays deployed: v2.25.1 born-2x subtrees + v2.25.2 ChartTickText at
stock 10px. What stays unbuilt: the margin-immediate byte patch scoped
above. Tracked as task #57.

## v2.25.3-udriveflyout (2026-07-30) — task #48, BOTH halves, zero measurement

User re-raised the U-Drive-It flyout + sub-flyout. Everything was derived
from existing artifacts (the live log + the .UI corpus + the locked
god/mayor machinery):

IDENTITY (from the user's own session log): the flyout is **tool-flyout
column A 0x8BB27C12** (script I-6bb27447: Earned Vehicles/Watercraft/
Aircraft/Mission Indicators; twin column B 0xAB954023 = Signs & Labels,
script I-cb95403e). Its sub-flyout logged `SUBSKIP container 0x8A6E61E0
258x874` — the 258-wide disaster strip family (the Earned Cars crash strip
was 88-wide; different layout, which is why the gate stays an ID LIST).

(a) DOCK — the alignment-marker rule, CONFIRMED against the log with zero
fitting: column A marker (4,150), spawn button 0xABB27A7A "U Drive It" on
sidebar 0xABB26B0E; btnAbs(30,922) − marker = (26,772) = the logged native
position EXACTLY. Two new kMayorFlyoutDock entries (mayorOnly=true →
generic CENTER-ANCHOR skip + the mayor-only dock loop, all existing
machinery): { 0x8BB27C12, 0xABB27A7A, -4,-150 } and { 0xAB954023,
0xAB9537B7, -3,-183 } (column B is NESTED — its spawn button lives inside
the Landscape flyout; anchor missing ⇒ no move, fail-safe). Column B's
five arts verified 2x-in-place in the refmap.

(b) SUB-FLYOUT — kHookParents + kParents += both column ids. The disaster
container/strip hooks (buffer force-recreate, item-field doubling via
ScaleRound, [0xE0] claim widen, ringBltY placement law, SUBDOCK) are all
menu-invariant since v2.24.0; the sub-flyout container is the SAME class +
width family, so the opt-in is the whole fix.

Built v2.25.3; game was running → Deploy-OnGameClose.ps1 armed
(_tests\, durable). VERIFY: open U-Drive-It from the sidebar — column
docked to the button (green track welded, not scattered); open Earned
Vehicles — strip 2x with seated icons, clicks across the full row width,
`SUBHOOK`/`SUBDOCK` lines replacing `SUBSKIP`. NO CRASH expected: same
architecture the five originals run. If Signs & Labels (inside Landscape)
docks wrong, read its MCAL line — never eyeball.

## v2.25.4-udriveanymode (2026-07-30) — the v2.25.3 gate-mismatch regression

v2.25.3 broke U-Drive-It COMPLETELY ("undocked and the sub flyouts no
longer open"). Log proof, not screenshot-read: ZERO `mayor flyout
0x8BB27C12` lines all session — the column got NO treatment. Root cause =
a GATE MISMATCH (law 4, unverified third state): `mayorOnly` made the
GENERIC sweep skip the column UNCONDITIONALLY, while the mayor-only dock
loop that was supposed to take over is gated on the mayor HUD 0xE9889775
being visible — and the SIM-MODE sidebar (where U-Drive-It opens) HIDES
that HUD (My Sims panel replaces it). Skip minus dock = raw 1x window;
"sub-flyouts don't open" was downstream (unclickable 1x buttons).
The frame-rate `SUBHOOK` spam was a RED HERRING: that log line fires per
pass by design (same cadence for the five known menus).

FIX: `anyMode` field on MayorFlyoutDock — the two column entries are
processed WITHOUT the mayor-HUD gate; their state gate is the flyout+
button search itself (neither exists outside their mode; aggregate init
leaves the five original entries anyMode=false, semantics unchanged).
Cross-checked connections: columns absent from kNeverScaleIds and the god
table; dock uses TABLE constants so runtime marker state is irrelevant
(same as the five proven entries); SUBDOCK's 40..200 width filter fits
the columns' 94x74 scaled buttons; kHookParents opt-in unchanged (the
container machinery engaged cleanly per the log - SUBCLAIM was already
widened by the shared container).

Deployed + suites green. VERIFY: sidebar -> U Drive It: `mayor flyout
0x8BB27C12 at(..) size 250x498 (docked)` in the log, column hugging the
button; Earned Vehicles opens 2x with seated icons.

## v2.25.5-icons-savebox (2026-07-30) — the strip icons + the Save box

User confirmed the U-Drive-It flyout + sub-flyout FIXED at v2.25.4, with
two residuals, both shipped here:

1. **Duplicated Fire Truck / Police Car strip icons.** Mining trail: the
   110 vehicle exemplars (all in SimCity_1.dat — the other archives carry
   ZERO exemplars, mostly S3D models) carry NO Item Icon B8 property, and
   their 0x8A416A99 values are not PNGs (a name-LTEXT key). So the menu
   binds those icons by CODE — the submenus-DLL "missing thumb" precedent —
   from the 90 UNBOUND members of icon group 0x6A386D26 (356 total − the
   266 exemplar-bound). The ItemIcons REPORT's claim "exactly 266 is
   correct" is FALSIFIED in-game. Fix: pool extended to the whole group
   (comment support added to load_distinct), ItemIcons 266 → **356** at all
   three tiers. Safety re-verified: 356/356 previews per tier, ZERO .UI
   refs to the group.
2. **Options → Save City collapsed confirmation.** Identified from the
   corpus by shape (small root + TextEdit + OK): script **I-e9263d4c
   "Text Entry"** (root 0xC9264BE2, 319x113) — the generic re-captioned
   prompt box the save flow titles "Save". Batch C in dialog-static:
   e9263d4c + sibling e9263de5 "Set Lot Size" (root 0x8926EEBE), 259 →
   **261** entries/tier; both roots added to kNeverScaleIds (standard
   parentage insurance). DLL v2.25.5.

Deployed + both suites green. VERIFY: Options → Save City shows a full-size
2x box; U-Drive-It Earned menus show ONE icon per cell for fire truck /
police car / freight.

## v2.25.6-saveboxruntime (2026-07-30) — the Save box bypasses the override

User: U-Drive-It FIXED ✅ at v2.25.5; the Save box still collapsed. That is
the KNOWN in-city-confirm bypass (the two quit dialogs' precedent, verbatim
from REGRESSION: "the game appears to build them through a code path that
bypasses the DBPF override, so they must be scaled at runtime"). Fix:
0xC9264BE2 (Text Entry / Save confirm) + 0x8926EEBE (Set Lot Size) added
to kCityDialogIds in IncrementalPass. The Batch-C static override stays
shipped (harmless; the guard skips an already-scaled box).

Tier-math fix in the same pass: the block's flat `w >= 400` "already
scaled" guard was a 2x-era constant (at 1.5x a scaled 249-wide Set Lot
Size = 374 px would re-scale). Now per-id designW with threshold
designW*5/4; f=2 identity holds for every pre-existing id.

Deployed + suites green. VERIFY: Options -> Save City -> full-size box;
log line `in-city dialog 0xC9264BE2 scaled (...) -> ...`.

## v2.25.7-savelatekids (2026-07-30) — the Save box, THIRD attempt, now measured

Attempts 1 (Batch-C static e9263d4c) and 2 (kCityDialogIds runtime) both
failed because the IDENTIFICATION was inferred from dialog SHAPE, violating
the rect-match law. The measurements that settled it:

- The live log at the save moment: `in-city dialog 0xAA921F4F scaled
  (1065,479 270x162) -> 540x324, 4 descendants` — the box is the
  QUIT-CONFIRM window family (270x161 = script 6a553aa4 exactly; the
  one-id-many-scripts trap), our runtime block DID scale it, ONE line =
  the scale was retained.
- Exe enumeration of ALL SEVEN modal-runner (sub_78E2F0) call sites:
  4a551b4c/0a55161d/6a553aa4 (quit family), 4a89b3f2 (disaster-save),
  0a5cf71d (game over), 2a41436c (obliterate) ×2 — **no "City Saved"
  script exists.** The save flow RE-USES the quit window and CREATES its
  content children (title/body/edit/OK) AFTER our one-shot pass — born 1x
  inside the scaled frame = the collapsed look.
- e9263d4c "Text Entry" IS real (4 exe load sites) — just not this box;
  Batch C stays shipped as legitimate coverage.

FIX: in kCityDialogIds, state==AlreadyScaled no longer skips — it runs an
idempotent CHILD re-pass (ScaleSubtree via scaleMap) every sweep while the
dialog is visible, so late-created content is caught within 250 ms. Log:
`in-city dialog 0x... LATE children: N scaled.`

LESSON (add to the laws): a dialog that LOOKS unique may be a REUSED
window re-captioned by code — before adding any new id, rect-match the
LIVE box against the log, and enumerate the modal-runner call sites to see
which script actually backs it.

## v2.25.8/9 — the Save box FINALLY identified: 0xAA8DEF97, code-laid, anonymous

Three fixes (static e9263d4c, runtime 0xC9264BE2/0x8926EEBE, late-children
on the quit family) all missed because the box exists in NO .UI script and
carries an id present in NO corpus artifact. v2.25.8 added **MWKID** — a
PERMANENT change-only dump of pMainWindow's direct children (+1 level):
id, CLASS VTABLE, rect, vis, logged only when the top-level set changes.
One user save later the box identified itself:

  root 0xAA8DEF97  vt=00ADC678  (950,475 500x175)
    anon vt=00AE20A0 (165,140 150x30)  <- OK
    anon vt=00ADF6A0 (18,35 468x98)   <- body  (GZWinBMP)
    anon vt=00ADF6A0 (12,8 473x25)    <- title (GZWinBMP)

Fully code-laid at 1x metrics; children ANONYMOUS (id=0) — pointer-walking
ScaleSubtree handles them fine. Also captured: the transient Save-As box
root 0x4A9DB60C (900x450). FIX (v2.25.9): { 0xAA8DEF97, designW 560 } in
kCityDialogIds (threshold 700 tolerates filename-dependent 1x widths; a
scaled instance >=1000 is skipped). The v2.25.7 late-children re-pass
covers content the save code creates after our scale.

LAW REINFORCED: a code-built box with anonymous children is INVISIBLE to
every script/corpus search — MWKID is now the standing first move for any
unknown transient dialog. e9263d4c/e9263de5 Batch C + the extra
kCityDialogIds entries stay (legitimate coverage, guards make them inert).

## v2.25.10-savebox-rects (2026-07-30) — the tearing, fully explained + fixed

v2.25.9 made the box full-size; the body then TORE into horizontal
stripes. Complete causal chain, all measured:

- The builder at exe 0x78DD80 creates root 0xAA8DEF97 and fetches text
  children 0xCA8CC4B6/0x4A8CC4A9 — those ids live in **I-ca8cbf0f**, the
  "Generic one-button notification popup" ALREADY in dialog-static since
  the v2.23.1 text sweep. (My earlier corpus hunt missed it because the
  root-width filter 200-420 excluded its 300-wide root... which the game
  then code-resizes to 500x175.)
- The game BYPASSES the staged .UI for this path → it renders the ORIGINAL
  script: body BMP {1abe787d,144161ee} imagerect=(22,35,180,180)
  edgeimage=yes at 1x — against art our dat serves at 2x. A 1x source
  rect over a 2x bitmap 9-slices into stripes = the tearing. (The quit
  boxes never tore because their frames carry NO imagerect.)
- FIX: BMPRECT — in the kCityDialogIds Fresh branch, walk the dialog's
  GZWinBMP children (positive class check vt==0x00ADF6A0), and where the
  flag holder ([this+0xd8] vt[10](0x10)) says an imagerect is present,
  ScaleRound the live fields [this+0xe8..0xf4]. One-shot per instance (the
  Fresh branch), so no re-doubling. Log: "... N imagerects x2.00" on the
  in-city dialog line.

LAW: for BYPASSED code-built dialogs, art-and-rect must be re-married AT
RUNTIME — the dat can only carry the art half.

## ✅ USER-CONFIRMED (2026-07-30 ~02:15)

- **Save City box PERFECT at v2.25.10** ("You did it"): full-size, clean
  frame, no tearing. The four-part chain (runtime scale + late-children +
  measured id + BMPRECT) is the complete treatment for BYPASSED code-built
  dialogs — reuse it as one unit.
- **U-Drive-It flyout + sub-flyout CONFIRMED at v2.25.4/5** (docked, strip
  2x, one icon per cell after ItemIcons 356).
- Task #48 CLOSED.

Still open: #47 remainder (occupant chips + Graphs chart line), #50 flash,
#54 Batch B measurement session, #57 Graphs-interior stock A/B (user
hold), tier verification. The RUN-SHEET remains the next structured pass.

## v2.25.11-bmpx-fgchain (2026-07-30) — why the portraits NEVER fixed

User report post-Save-box: My Sims faces still 1/4 top-left. Log facts:
- The Select-A-Sim picker IS live as root 0x6A243D9E at 868x762 (the
  STATIC override works for this dialog - MWKID proof).
- **ZERO `BMPX` lines in every session since v2.25.0** - the hook never
  engaged anywhere, ever.
- `DFG patched class vt=00ADF6A0 Plot=009BC325 (idx 4)`: FlashGuard
  patches CLASS vtables in place, and once it claimed GZWinBMP's slot 88,
  BMPX's positive check `vt[88]==0x9BC325` rejected every instance
  SILENTLY. Compounding irony: the kFgMax 6→12 raise (task #53, same
  session as BMPX) is what let DFG reach idx 4+ at all - the two fixes
  collided the day they shipped.

FIX: HookBmpInstance (and HookGaugeInstance, same latent hazard - DFG has
3 free slots left) accept slot 88 == the real draw OR any kFgThunks[i].
The chain stays intact: our per-copy draw -> FG thunk -> real draw.

LAW: **a "positive class check" that pins a vtable SLOT value must accept
every legitimate occupant of that slot - including OUR OWN other hooks.**
When two subsystems both key on slot 88, enumerate the interaction at
design time; a silent false-negative is invisible until a user report.

Deployed + suites green. VERIFY (next run): `BMPX N instance(s) hooked
under 0x6A243D9E (dialog, x2.00)` and faces filling their boxes in
Select-A-Sim + My Sims panels.

## v2.25.12/13 — the "duplicate dials" decoded by GBLT: a PRE-HOOK GHOST

GBLT + GAUGESCAN (user drive 07:49) settled it in one capture:
- The LIVE draw is CORRECT every frame: one blit per gauge, src sliding
  68 px per frame (the strips ARE 2x now: cell 68x60), dst rewritten
  (0,0,68,60) -> (0,0,136,120) x2.00. No second draw path, no unhooked
  twin (GAUGESCAN: exactly 2 instances, both HOOKED).
- The visible small dial = the FIRST 68x60 frame the game paints in the
  instant between console creation and our next sweep (<=250 ms). Needle
  frames are mostly TRANSPARENT, so the corrected 136x120 draws never
  cover the stale pixels baked into the console composite: a permanent
  top-left ghost. "Settles in the middle at top speed" = the live needle
  sweeping across/away from the ghost.
- Note in passing: the needle strips are now staged 2x (cell 68 not 34),
  and the dst rewrite's self-limit does NOT clamp on this console
  (136 <= 142 win) - harmless BECAUSE the strip content is genuinely 2x
  and slicing divides W by count, but the v2.23.2 note "a 2x strip
  self-limits to 1.0" is FALSE when the window is wider than the cell.

FIX (v2.25.13-gaugeheal): on a NEW dashboard, after hooking, force 3
sweeps of InvalidateSelfAndParents on the gauges + dash root so the
console re-composites and erases the ghost. Log: "GAUGE ghost-heal
invalidate (N left)". Deployer armed (game running).

## v2.25.14-dashborn2x (2026-07-30) — the duplicate dials, ROOT-CAUSED and cured

The v2.25.13 heal did NOT cure it (screenshots from that build; heal lines
present). The complete measured chain:

- GBLT: EVERY gauge Plot draw is scaled (30/30 `-> dst 136x120`),
  including during the heal invalidates. GAUGESCAN: exactly 2 instances,
  both hooked. So the small dial's pixels never come from Plot.
- Exemplar mining: frame counts are 55 (not 16); the 1x strip is
  3740x60 -> 1x cell = EXACTLY 68x60 (the strips were NEVER staged 2x -
  refmap 0 hits; "cell 68x60" was the 1x cell all along, and the x2 dst
  rewrite is correct).
- vt[93] GetBufferToDrawTo disasm: `mov eax,[ecx+0x6c]` — the "draw ctx"
  at [win+0x6c] IS the window's own PIXEL BUFFER. It is allocated at
  FIRST PAINT from the window's then-current size. Runtime-sweeping the
  console let the game paint once at 1x -> every gauge pbuff born 71x71
  -> the correct 136x120 draws CLIP into it -> at REST the engine
  composites the clipped buffer (small top-left dial); while DRIVING the
  active draws go direct (full dial). Value-dependence explained exactly.
- The v2.23.2 emu note "this class has no cached buffer" was RIGHT about
  the CLASS fields and WRONG about the WINDOW: the buffer is BASE state.
  Also: base dirty flag = [win+0x70] (slot 91 disasm); NEVER write the
  disaster lever's [win+0x114] on this class - the object is only 0x108
  bytes (heap overrun).

CURE = the born-2x law, third application: all 43 console scripts ship
with the 0x4BCB938A subtree pre-doubled (root-keyed block in
build_selective_safe.py - fires on `id=0x4bcb938a` in the text, 43/43
processed, 21-30 areas each, all tiers) + 0x4BCB938A in
kDataScaledSubtreeIds. Gauge windows are born 142x142 -> first paint
allocates a 2x buffer -> at-rest composite full. The dst-rewrite hook is
still required (strips stay 1x by design) and self-limits the same.
Diagnostics GBLT/GAUGESCAN kept (capped). Deployed + both suites green.

## v2.25.15-gaugestrips2x (2026-07-30) — "split, sides swapped" = STOP STRETCHING

The user's observation cracked it: NOT a duplicate — ONE dial, split with
its halves exchanged. With born-2x active and the log showing every draw
correct (win 142 pre-hook, src on exact 68-px frame boundaries, dst
rewritten), the only remaining moving part was the STRETCH itself:

- The extracted cells (gauge-strip-cells.png in this dir) prove the 1x
  strip slices perfectly at 68 px — 55 aligned complete dials.
- The strips are 2805-3740 px wide — PAST the 2048 texture-tile limit.
  STOCK only ever cell-COPIES from them (dst = src size); the ring blits
  that proved the ctx vt[38] "stretches" came from SMALL atlases. A
  stretch that samples across tile addressing on a WIDE source is the
  split/side-swap producer.
- (Also measured en route: cIGZBuffer 0x00AC1400's own slot 38 is a
  1-arg setter — the gauge's [0x6c] target is a DIFFERENT class; and the
  base dirty flag is [win+0x70], slot 91.)

CURE — remove stretching from the pipeline entirely:
1. The 16 needle-strip TGIs (mined from the 110 vehicle exemplars, prop
   0x2BE8E6CB) added to CODE_BOUND_TGIS → SelectiveArt 616 → **632** at
   all tiers (suite updated). With 2x strips the game's own dst = cellW
   math is a pure copy again, tile-safe like stock.
2. GaugeCtxBltThunk SNAPS m→1.0 when the clamped m < 0.75×tier (an
   already-scaled strip): no more residual 1.04x stretch, no stretch path
   at all. The born-2x windows/buffers (v2.25.14) stay — they are what
   makes cell==window work.

Deployed + both suites green. VERIFY: dials one clean full-size image at
every speed; log `GBLT ... src(x,0,x+136,120)` (2x cells) with NO
`GAUGE draw ... (x2.00)` rewrite lines (m snapped to 1).

## ✅ GAUGES USER-CONFIRMED at v2.25.15 ("That's working perfectly")

## v2.25.16-budgetdialogs (2026-07-30) — the budget sub-dialogs, MWKID-measured

Three new user reports. The budget one shipped immediately because MWKID
had already captured the identities from the user's own session:
- 0x4A9DB60C (900x450, department/Loans family), 0xEBB16D71 (900x492,
  Utilities), 0x0423278F (1000-wide Ordinances, HEIGHT VARIES: seen 970
  AND 554) — all root vt 00ADC678 + table child vt 00ACD0D8, game-built
  main-window transients that bypass overrides → kCityDialogIds. Master
  Power Budget is NESTED inside Utilities → covered by the late-children
  re-pass. Mechanism fix: the too-big guard now SKIPS WITHOUT a dead
  record (a dead record at Ordinances' tall state froze it at 1x even
  after it shrank). MORE department dialogs likely exist — each will
  identify itself via MWKID when opened; add ids as they appear.
Deployed (wait-for-close, 08:46:31) + both suites green.

PARKED AS TASKS: #58 Building Style Control (empty title bands - measure
the mod DLL's ~20 runtime ids first), #59 pause/mode screen-edge border
(code-painted, not a window - exe hunt), #60 USER-DIRECTED U-Drive-It map
bubbles at 2x-of-current (4x design; intentional stock-parity deviation).

## v2.25.17-budgetfix-bubbles (2026-07-30) — toast revert, REAL budget ids, bubbles

REGRESSION OWNED: v2.25.16's three "budget" ids were the ADVISOR TOASTS
(corpus PROOF: script 4a5a89d4/d5 root = 0x4A9DB60C, 2bb16d50 root =
0xEBB16D71 - already static-doubled 450x246→900x492, so the runtime entry
double-doubled every toast while the real budget dialogs stayed 1x). The
ids were inferred from MWKID TIMING, not content. LAW: kCityDialogIds
identity must be CONTENT-matched (corpus/root-id proof), never inferred
from which dialog the user "should" have had open.

REAL budget sub-dialogs, CONTENT-matched by their captions ("Monthly
Income/Expense/Estimate/Subtotal/Accept"): I-aa3acdfe root 0xAA3AC002 +
I-cbc3c2b9 root 0xCA4C332D (~220 controls each; the game content-fits
them to ~900-1000 wide at 1x → designW 1000). Master Power Budget =
nested instance → late-children re-pass. The skip-no-dead-record guard
change from v2.25.16 KEPT (correct on its own).

TASK #60 SHIPPED (user-directed): the mission bubble base
{46a006b0,094ac89a} now stages at 2x-OF-TIER (bubble4x[-tag]/ dirs,
Upscale2x --factor 2 over each tier preview; builder ART OVERRIDE path).
The bubble window is art-sized → 4x art = 2x current, data-only.
DELIBERATE stock-parity deviation. The 15 glyph-table entries stay at
tier scale - SHARED generic art (82B99D9D = every spinner's arrow strip,
46A006A7 = slider art); doubling them would resize every spinner/slider.
Glyphs will sit proportionally smaller inside the bigger bubble - if the
user wants them bigger too, identify bubble-exclusive glyph instances
first.

Deployed directly (game closed) + both suites green.

## v2.25.18-budgetrows (2026-07-30) — budget ROWS + bubble override withdrawn

User verified: toasts FIXED by the revert ✅; budget dialogs still wrong;
bubbles unchanged. Log decoded both:

- BUDGET: the masters ARE view-parented and the CITY SWEEP scales them as
  hidden templates at city load ("panel 0xAA3AC002 (158,40 500x464) ->
  (316,80 1000x928)" + 0xCA4C332D). The user's dialog WAS 2x-rooted; the
  overlapping content = game-created ROWS laid at 1x pitch at open. The
  late-children pass never ran because the game CONTENT-FITS the root
  height after our scale -> Classify = Unrecognized -> the old block
  order skipped everything. FIX: any kCityDialogIds dialog with a scale
  RECORD (AlreadyScaled OR Unrecognized) now runs the idempotent child
  pass BEFORE the width guard, every sweep while visible.
- BUBBLES: the deployed dat PROVABLY carried the 128x128 art (extracted +
  measured) and the map circles did not change -> the markers are NOT
  {46a006b0,094ac89a}. Override DISABLED in the builder
  (BUBBLE_OVERRIDE_ENABLED=False; art dirs + plumbing kept). Task #60
  reopened: the markers are likely WORLD-LAYER billboards (zoom-scaled by
  the renderer) - next step is the exe hunt for the marker draw.

Deployed via the extended Deploy-OnGameClose.ps1 (now also copies the 3
SelectiveArt tiers). Suites to re-run post-deploy.

### Task #60 offline progress (same day): the 094AC89A mechanism DECODED

Both exe load sites found (0x4B82F0 + 0x7AC620). The 0x4B82F0 marker path:
loads {856DDBAC,46A006B0,094AC89A} once (cached at [this+0x3C]), colorkey
setup, then `img->vt[0x30]` (GetRect) -> centers THE ART RECT on the
anchor ([this+0x28/0x2C]) -> creates the window via class 0x48E945B4 and
`vt[0xDC]`(SetArea) with that rect. **The window IS art-sized** - 4x art
WOULD grow this marker. Since the user's circles did not change, the blue
map circles are a DIFFERENT marker family (they also appear in normal
mayor view, e.g. beside the Trip Types panel - possibly the vehicle-
available/trip markers). NEXT for #60: identify the visible circles -
check the coverage-matrix root list for a marker/billboard family first,
else one aimed DPROBE band over a marker. Do NOT re-enable the 4x
override until the real consumer of 094AC89A is known (it may be the
U-Drive-It MISSION "!" bubble, which grew at v2.21.4 and would go 4x).

## v2.25.19-budgetstatic (2026-07-30) — the budget dialogs, THE PROVEN PATTERN

User (correctly): "take a step back and see how we've fixed similar
issues before." The step back: the budget rows' 1x pitch is SCRIPT DATA
— the two masters carry every department row as GZWinText children
(aa3acdfe: 128 texts, cbc3c2b9: 141; NO grids), and the game re-imposes
that geometry at open, so NO runtime child pass can stick (v2.25.18's
late-pass shipped and changed nothing — the Audio-playlist lesson: pitch
lives in data).

THE FIX = the Establish City pattern, exactly:
1. dialog-static TARGETS += aa3acdfe + cbc3c2b9 (areas ×2 [217/234],
   fonts → GUID [145/161], art via the global plan). DialogStatic 261 →
   **280** entries on all three tiers (suite updated).
2. kNeverScaleIds += 0xAA3AC002/0xCA4C332D — parentage MEASURED (the
   sweep log showed them as city panels), so static+swept would be 4x.
3. kCityDialogIds entries REMOVED (runtime has no role; the v2.25.18
   record-owning late-pass restructure stays for the other dialogs).
The game's content-fit height doubles naturally: it derives from the
doubled row geometry.

ALSO REPORTED (untriaged): "U-Drive-It: I clicked multiple [bubbles] and
one is still open" — a mission-proposal dialog (green box) stayed open
after clicking several map bubbles. May be plain game queueing of stacked
mission prompts; observe once before treating as ours.

Deployer armed (game running). Suites to verify post-deploy.

## v2.25.20-budgetinstances (2026-07-30) — THE ACTUAL BUDGET FLAW, FOUND

User (rightly insistent): "you have fixed this exact issue dozens of
times." The real flaw, finally measured end-to-end:

1. STATIC PATH PROVEN BYPASSED: the deployed DialogStatic carried the
   doubled aa3acdfe (root area=(316,80,1316,484), extracted from the
   deployed dat and measured) while the live template still read 500x464
   (DGPKID). The game loads these two scripts from SimCity_1.dat
   directly, quit-family style. v2.25.19 reverted (TARGETS back to 261,
   kNeverScaleIds entries removed - they had made the dialogs FULLY 1x).
2. RUNTIME PATH'S FLAW: **the id exists TWICE** - a PERMANENT hidden
   template (DGPKID: vis=0 always, parked at 158,40) plus the OPEN
   instance. GetChildWindowFromIDRecursive returned the TEMPLATE, the
   IsVisible() check failed, and every kCityDialogIds pass silently
   skipped the real dialog. The minimap non-unique-id trap, in a new
   costume.

FIX: IdCollectCtx - the kCityDialogIds loop now collects EVERY instance
of each id (bounded walk, up to 4) and runs the full Save-box treatment
per VISIBLE instance (root scale on Fresh + BMPRECT + late/reset child
re-pass). Budget masters re-added with designW **500** (the script
width; the game content-fits HEIGHT only - the earlier 1000 was another
inferred-not-measured number). VWKID (the view-layer MWKID twin) shipped
in the same build as a permanent instrument.

LAW (companion to the content-match law): **for any id in a runtime
dialog list, assume it is NON-UNIQUE - iterate all instances; a
visibility check after a first-match find is a silent skip.**

Deployed 10:27:15 + both suites green. VERIFY: open Budget -> Taxes /
Health & Education: `in-city dialog 0xAA3AC002 scaled (…500x…) -> 1000x…`
in the log, rows at proper pitch.

## v2.25.21-budgetholistic (2026-07-30) — the budget family, completed

v2.25.20's multi-instance fix WORKED (user screenshots: Taxes,
Transportation, Neighbor Deals all full-size with correct row pitch).
The holistic remainder, all identities MEASURED:

1. SPINNER ARROWS ("crushed" in Taxes): the art-sized spinner law at
   scale - all 21 corpus-unique spinner ids from the two master scripts
   added to kFontSizedIds (position-only). 0x00000202 EXCLUDED: it is
   also a 271-wide GZWinCombo in I-e9a56248 and kFontSizedIds is a
   GLOBAL id check - one Neighbor Deals spinner keeps the old behavior
   (follow-up: class-based check would need the GZWinSpinner vtable,
   which the descriptor string-pool does NOT provide - the vt hunt goes
   through the deserializer registration if ever needed).
2. ORDINANCES 0x0423278F re-added to kCityDialogIds - it was collateral
   in the toast revert but MWKID had it live at 1000x554/970 (it
   content-fits the modded ordinance list; when too tall to double, the
   skip-no-record guard waits for a shorter state).
3. BUSINESS DEALS empty-state = 0x4C30E4FA, VWKID-caught view-parented
   at 272x200 (parks off-screen at -272,-200 when closed). Added with
   designW 272.
4. Neighbor Deals combo text truncation ("7000N", "Unava..") NOT
   touched: possibly stock behavior (tight at 1x too) - stock-parity
   pass will judge.

Deployed 10:36:24 + suites green. VERIFY: Taxes % arrows normal-size;
Ordinances expands (or stays 1x only while its list is very long);
Business Deals box 2x.

## v2.25.22-dialogcenter (2026-07-30) — the Ordinances "can't close" regression

v2.25.21's Ordinances entry scaled the 1000-wide CENTERED dialog IN PLACE
(the block kept l,t - harmless for every small dialog before it), pushing
it to x=700..2700: Accept/Cancel/X off-screen, user stuck in the modal.
The "second frame" in the screenshot = the dialog's own inner estimate-
column border at 2x, not a duplicate.

FIX (mechanism-level): the kCityDialogIds scale now preserves the OLD
CENTER and clamps fully on-screen (nl = l + w/2 - newW/2, clamped to
[0, scr-new]). Applies to every entry; small dialogs barely move.

WATCH ITEM: if Ordinances still shows row GHOSTING/interleave after
centering (the mod-added rows may churn), the next step is reverting
0x0423278F and treating Ordinances as its own measured problem - do NOT
iterate blind.

Deployed 10:44:03 + both suites green.

## v2.25.23-budgetdata (2026-07-30) — THE BUDGET MYSTERY SOLVED: our own dats

The user demanded a holistic code examination. It delivered the real
root cause of the entire budget saga:

- The loader (exe 0x7658A0 etc.) fetches the masters as
  {T=0, G=96A006B0, I=CBC3C2B9/AA3ACDFE} through the RESOURCE MANAGER
  [0xB43DC4] vt[0xC] - the SAME override path the (working) toasts use.
  There never was an engine bypass.
- A Plugins-wide index scan found the smoking gun:
  **z_SC4UIScale_SelectiveArt-2x.dat ships its own copies of both budget
  scripts** (clone-retargeted, 1x geometry) and sorts AFTER DialogStatic
  → loads later → SILENTLY OVERRODE the doubled copies. Every "static
  double is bypassed" observation was our art dat beating our dialog dat.

THE CONVERGENT FIX (v2.25.23):
1. SelectiveArt no longer emits the two scripts (632 → **630**/tier).
2. DialogStatic doubles them again (261 → **280**/tier) - rows, spinner
   windows, content-fit height all derive from doubled data (the marquee
   principle; spinners self-size from their 2x arrow art and now match
   their data-doubled windows).
3. kNeverScaleIds has the two roots (doubled data + swept templates = 4x).
4. kCityDialogIds: masters REMOVED for good; 0x0423278F (Ordinances)
   REMOVED per the revert law (both runtime attempts tore it - own
   measured pass later; it may be an embedded master-B composition);
   0x4C30E4FA (Business Deals) stays.
5. The v2.25.22 center+clamp stays (correct generally).

LAW (the big one): **when an override "mysteriously doesn't load",
enumerate EVERY shipped copy of that TGI across all our own dats FIRST -
same-project dats compete in the same load order as foreign mods.**
Suite counts updated; deployed 10:56:28; both suites green.

VERIFY next session: Taxes/H&E/Utilities/Transportation/Neighbor Deals
all 2x with correct rows + normal spinner arrows (all born from data;
no runtime churn). Ordinances EXPECTED still broken (own pass pending).

## v2.25.24-budgetdock (2026-07-30) — THE BUDGET, FINAL ARCHITECTURE

v2.25.23 broke the MAIN Monthly Budget panel ("undocked and broke the
whole budget window") because the model was still wrong. The decisive
measurement: **BOTH scripts are MULTI-ROOT** - each of aa3acdfe/cbc3c2b9
carries FOUR top-level roots:
  0xAA3AC002 income section (500x202), 0xCA4C332D expense section
  (500x353), 0xAA3AC001 detail-dialog frame (558x505 - Taxes etc.),
  0xAA3AC000 balance bar (833x137).
The budget UI = a GRAPHS-CLASS COMPOSED PANEL: the game composes,
anchors and re-lays these roots at runtime from script-cached geometry.
NOT a modal family, NOT one docked panel - a composition.

FINAL TREATMENT (the Graphs pattern verbatim):
- selective-safe ships both scripts with children-only double_subtree_
  areas on ALL FOUR roots (46+42+100+23 / 76+41+88+23 areas; markers
  1x). SelectiveArt 632/tier.
- kDataScaledSubtreeIds += all four roots (sweep scales + anchors each
  root, never descends).
- dialog-static fully OUT of the budget family (261/tier); kNeverScale
  and kCityDialogIds budget entries all removed.

Deployed 11:10:57; both suites green. VERIFY: Monthly Budget docked and
composed correctly; Taxes/H&E/etc. detail dialogs (0xAA3AC001 instances)
born 2x with correct rows + spinner arrows; Ordinances still task #61.

## v2.25.25-budgetbuttons (2026-07-30) — THE DETAIL DIALOGS DECODED END-TO-END

Post-compact session. The user's four screenshots + the 11:23 session log
finally identified the detail dialogs beyond doubt — and CORRECTED the
v2.25.24 model:

- **Every budget detail dialog is ONE shared main-window transient,
  id 0x0423278F** (vt 00ADC678), re-populated per department. MWKID:
  Ordinances 11:23:25 (900x754), Neighbor Deals 11:23:36 (1000x970),
  Business Deals EMPTY BOX 11:23:45 (300x100!), Transportation 11:23:52
  (1000x826). They are NOT 0xAA3AC001 instances — 0xAA3AC001 (1116x1010,
  VWKID 11:23:23) is the MAIN Monthly Budget panel's frame. The
  "exe leads 0x779F92/0x77C156/0x78B955" from task #61 are exactly the
  three references to 0x0423278F — same window all along.
- **No treatment ever touched 0x0423278F** (no scale lines in the log),
  so every observed size is the game's own layout. Decoded:
  * frame: content-fits BOTH dimensions from (factor-sized) font
    metrics → already correct; centered on screen center.
  * rows 2640x36 / subtotal plates 128x20: ART-SIZED widgets born at
    2x because our dats ship their style PNGs 2x (140155B7 row strip
    1320x18, 140155CB/CC plates 64x10 — measured stock vs deployed).
    THE LAW: a code-created widget with a style PNG is born at the
    ART's size — whoever owns the art owns the widget size.
  * Accept/Cancel 180x30 at x=14 / x=W−195, y=H−40: EXE CONSTANTS —
    the five department builders (0x77D3xx Ordinances, 0x7818xx,
    0x7855xx, 0x7872xx, 0x7893xx families) hardcode
    `push 0x1e; push 0xb4; call [vt+0xD4]` (20 sites, whole-exe scan)
    plus anchors `sub r32,0xC3` (5) and `sub r32,0x28` (10). vt+0xD4 =
    SetSize(w,h); creation+placement helper = sub_77B960(parent, id,
    x, y, styleTGI, …), ids get +0x100 twins.
  * Business empty box: SetSize(300,100) x5 sites 0x77C19E-0x77C30A.

FIX SHIPPED (v2.25.25):
1. **CodePatches::ApplyBudgetButtonScale** — all 35 verified sites
   scaled by factor (360x60, anchors W−390/H−80 at f=2). Tier-general;
   skips whole patch if h or y-inset exceeds imm8 (f>3.17). Lever
   [Spike] BudgetButtonPatch=1. Expected log:
   `CodePatches: budget buttons 360x60 anchors W-390/H-80 (20 size + 5 x + 10 y sites).`
2. **Business empty box via kCityDialogIds {0x0423278F, designW 300}**
   (push 0x64 imm8 can't hold 200 — no in-place byte patch possible).
   This does NOT violate the Ordinances revert: the 375 threshold
   structurally excludes every populated department state (900/1000
   wide) — only the 300x100 empty box can ever match. Content-matched
   (MWKID 11:23:45 + screenshot).

STILL-1x REMAINDER, root-caused but NOT patched (consumer census first):
- Neighbor Deals combos 120x32 ("7000N"/"Unava" truncation) and
  Transportation/Taxes sliders 110x36 + spin arrows 16x36 — art-sized
  from the two DELIBERATELY-shared 1x glyph sets (46A006A7 slider art,
  82B99D9D spinner strip, v2.25.17 decision) and/or an unidentified
  combo-body PNG. Doubling any of them resizes every consumer game-wide;
  census before action. Combo truncation may also be stock-tight.
- Ordinances checkbox/eye-vs-text overlap (~16px): row-inset consts
  (x=18 checkbox, x=34 row) with art-sized 2x eyes — cosmetic, retest
  after the button fix before measuring further.

Deployed 11:44:23 (game closed, direct copy) + both suites green
(15 dats / SelectiveArt 632 / DialogStatic 261 — no dat changes).
VERIFY: all five department dialogs show full-size Accept/Cancel inside
the frame; Business Deals empty box 600x200 with separated title/text;
Ordinances buttons fixed (rows were already correct); toasts/Save box/
main Budget panel unchanged (regression group).

## v2.25.26-revert278F (2026-07-30, ~20 min after .25) — THE GUARD THAT COULDN'T

v2.25.25's {0x0423278F, designW 300} entry BROKE ORDINANCES exactly as
the old #61 warning predicted (user screenshot ~11:52: torn interleaved
rows, frame ballooned to ~1780, Accept/Cancel at 720x120 = the
exe-patched 360x60 doubled AGAIN by us). Root cause of the failure:
**the width guard tests a SNAPSHOT but the id is a LIFECYCLE.** The
shared transient passes through a small (<=375) state, takes a Fresh
scale record there, and the record-owning per-sweep child re-pass
(v2.25.18/20 machinery) then doubles everything the game lays into the
SAME window when it repopulates as Ordinances — including the freshly
correct exe-sized buttons. The guard held for every earlier entry only
because those dialogs never repopulate.

REVERTED same session (the revert law): 0x0423278F is BANNED from
kCityDialogIds permanently (comment in the table says why). The
Business Deals empty box stays 1x (300x100) — ACCEPTED for now; any
future fix must be RECORD-FREE (a one-shot content-matched resize with
no persistent record, or an exe-side lever), never this list.

LAW (the .25/.26 pair): **a width/size guard cannot gate a window that
REPOPULATES — the record outlives the state that matched.** Corollary
of "assume every id is non-unique": assume every TRANSIENT id is also
non-unique IN TIME.

The v2.25.25 exe button patch STAYS (correct at the source; the giant
buttons in the screenshot were our runtime double on top of it).
Deployed 11:55:26 (game closed) + both suites green. VERIFY: Ordinances
back to sane (art-born 2x rows + 360x60 buttons inside the frame);
other departments same; Business empty box small-but-functional at 1x.

## v2.25.27-ordinsets (2026-07-30) — "make the window fit the text"

User (rightly): go back to what we did before. The ledger check: for this
dialog dialog-static is PROVEN inapplicable (no .UI script), the runtime
dialog list is BANNED (three tears), kFontSizedIds is sweep-side only —
the applicable precedent is TASK #41 (tooltip): 2x content inside a
hardcoded 1x layout const -> scale the constant. Same mechanism that just
fixed the buttons.

ApplyOrdinanceInsetScale: the Ordinances builder lays its left column
with push-imm8 x consts — section headers + checkboxes at 18, row
text/strip windows at 34 — so the 2x checkbox art (32px, ours: style
144161EA shipped 2x) and the eye glyph (art 0x2A5C322B, DANGLING in all
archives = runtime-bound component vt[0xB4] SetImage at 0x77CBC9) pile
onto the text start. Six byte-verified sites x factor (18->36, 34->68):
income 0x77C998/0x77CA88/0x77CAE0, expense 0x77CE3E/0x77CF16/0x77CF6E.
Content-fit width grows with them. Lever [Spike] OrdinanceInsetPatch.
Expected log: `CodePatches: ordinance row insets x2.00 (6 of 6 sites).`
Scope deliberately Ordinances-only (one department at a time, the flyout
law); other departments' insets get their own measured sites if flagged.

Deployed 12:10:00 (game closed) + both suites green. VERIFY: checkbox,
eye and text each clear of the other in every Ordinances row; header
indent proportional; Accept/Cancel unchanged from v2.25.25.

## v2.25.28-ordnames (2026-07-30) — the seventh constant, measured this time

v2.25.27 verified from the user's own session log (MWKID 12:12:09): all
six sites took (checkboxes 36..68, rows/strips at 68, buttons 360x60
inside the frame) and the frame stays 900x754 (its width is set
independently of children — NOT content-fit from rows; the "window
didn't change size" observation is correct and fine). The remaining
overlap: **the ordinance NAME texts are SEPARATE windows** (ids
0xABCDE03+k, sub_779660, beyond MWKID's 24-child cap) created at their
own x const 68 (`push 0x44`) — the row move parked the row's eye
component exactly on them.

v2.25.28: the two name-x sites patched (income 0x77CC23, expense
0x77D0E0, signature 6a 44 55 51). Stock-coherent 2x is 136 but push-imm8
caps at 127 → the inset function now CLAMPS to 127 with a log line
instead of skipping. Layout: [chk 36..68][eye ~84..104][name 127+] —
23px clearance at the measured eye. Color-triplet pushes
(0x44,0x55,0x66 before a style TGI) identified and excluded.

Deployed 12:16:16 (game closed) + both suites green. Expected startup:
`ordinance row insets x2.00 (8 of 8 sites)` after two
`ordinance inset 136 clamped to 127` lines. VERIFY: checkbox / eye /
name each separated in every Ordinances row.

## ✅ ORDINANCES USER-CONFIRMED at v2.25.28 ("YOU SOLVED IT") — the family checklist

Screenshot proof 12:2x: checkbox / eye / name cleanly separated, buttons
full-size, subtotals right. THE PROVEN RECIPE (now the template): MWKID
dump from the user's own log -> builder disasm -> byte-patch the 1x
x-constants (imm8 clamp at 127) -> verify. Zero regressions in the .27/.28
pair.

USER-ORDERED CHECKLIST (tasks #62-#69), one department at a time:
1/8 Neighbor Deals, 2/8 Business Deals empty box, 3/8 Transportation,
4/8 Public Safety, 5/8 Health&Education, 6/8 Utilities,
7/8 City Beautification, 8/8 Government Budget.

Defect classification from the 12:2x screenshot set:
- EYE-ON-NAME (PS "(eye)ire Dept.", H&E "(eye)ealth", Utilities
  "(eye)ower"): the Ordinances disease in the slider-department rows.
- COUNT-ON-NAME (H&E "Large Medical Cente7", Utilities, Beautification
  "Community Garden2"): the building-count column const overrun by 2x
  names.
- SLIDER-ON-LABEL (Beautification "Parks and Recreation --o--",
  Government "Building Maintenance--o"): slider x const inside 2x labels.
- DEALS (Neighbor): labels at ~8, backing 206, combo 218 w=120
  (truncation) - all raw consts per MWKID.
- BUSINESS EMPTY BOX: SetSize(300,100) x5 sites known; plan w 600
  (imm32) + h 127 (imm8 max).

BUILDER MAP (id-base scan): Ordinances rows 0x77C9xx-0x77CDxx (DONE);
0xABCE100/200 deals loops at 0x77E616 AND 0x781C9F; slider rows
(0xABCDF00+0xABCE200/600) at 0x78771F region; six-section builder
0x786Cxx-0x786F07 (Utilities?); 14 push-0x12 sites in 0x77F5xx-0x7815xx
(TAXES many-row builder, currently no complaint - leave). NEIGHBOR DEALS
CAVEAT (measured 12:2x): its row loop COMPUTES positions from struct
fields ([esi+0x68]...) - not inline consts like Ordinances; next step is
tracing where the deals builder initializes its column geometry (the
0x7818xx builder prologue), NOT blind const patching. sub_77C3C0 is just
a destructor (free-chains), ignore it.

## v2.25.29-deptinsets (2026-07-30) — builder E (5 departments) + Business box

Signature-driven CREATION CENSUS of the whole budget region (scan of
every sub_779660/77B960/77B7B0 call with its pushed args - the scanner
is scan_creates.py, session scratchpad; the census table is reproducible
from region.asm). It identified the SLIDER-DEPARTMENT builder
(0x7883xx-0x7896xx, buttons 0x67/0x6D) serving Public Safety / H&E /
Utilities / City Beautification / Government:
- dept title x=20 (0x788395), "Monthly Expense" hdr x=18 (0x7883DD)
- category strip+eye rows x=18 (0x788ABF, 0x788F94; style 140155B7)
- category/item NAME columns x=48 (0x788527/0x78874D/0x788B3C/0x788FD3)
  -> the "(eye)ealth" overlap
- building-COUNT columns x=258 imm32 (0x788621/0x7887FB/0x788C36/
  0x789089) -> "Large Medical Cente7"
- "Subtotal" labels x=250 imm32 (0x7888F9/0x78931B)
- SLIDER create sub_7794E0(x=260 imm32 @0x788D1E, w=110 imm8 @0x788D1B)
  -> track through "Parks and Recreation"

ApplyBudgetFamilyScale (lever [Spike] BudgetDeptPatch): all of the above
x factor (imm8 clamp 127 - slider width 220->127), PLUS the Business
Deals empty box record-free at the source: 5x SetSize(300,100) ->
600x127 (h imm8-capped) + close-X (269,11) -> (538,22). Expected log:
`CodePatches: budget dept x2.00 (9 imm8 + 7 imm32 sites), bizbox 600x127 (7 sites).`

NOT in this build: Neighbor Deals (builder B rows come from helper
sub_77A080/77A120 via sub_77C3C0 with computed args - trace pending,
task #62) and Transportation-specific consts (builder D, 0x7872xx +
0x7877xx machinery, task #64; its 0x787204 create at x=0x159=345 noted).
Deployed 12:33:25 (game closed) + both suites green.

## v2.25.30-notchpin (2026-07-30) — the white bar + Business title, both measured

User verified v2.25.29 moved names/counts/sliders correctly; two
residuals, both root-caused from the fresh log + user insight ("the
white bar might be from stock"):

1. WHITE BAR = the STOCK funding-notch bitmap (ids 0x0ABCE2xx, 16 wide,
   MWKID 12:38:57: (339,y 16x36) per category row). Its x=339 is
   COMPOSED at runtime - a whole-exe scan finds NO literal 339 (both
   hits are struct-offset cmps at 0x9B46D4/0x9B4FD2) - so no byte patch
   exists. At stock, 1x names end ~180 and never reach it; 2x names do.
   FIX = NOTCHPIN in UiSpike (law-6 PIN-BACK, the DVPIN/RCI pattern):
   while transient 0x0423278F is visible, any 16-wide 0x0ABCE2xx child
   still at x=339 with a slider sibling (0x0ABCDF00|k) is re-seated at
   sliderX + 79*sliderW/110 (stock proportion, tier-general). No scale
   record, idempotent, deals rows (no slider sibling) untouched.
2. BUSINESS TITLE: the box interior texts are creates at 0x77C26C/92 -
   title 0xABCE000 at (10,5), body 0xABCE001 at (15,25); 2x title glyphs
   cover y=25. Four imm8 coordinate sites added to kDeptImm8Sites
   (doubled). Expected dept line now: `(13 imm8 + 7 imm32 sites)`.

Deployed 12:47:28 (game closed) + both suites green. VERIFY: notch sits
on the slider track in PS/H&E/Utilities/Beautification/Government; no
name crosses it; Business box title clear of body text.

## v2.25.31-bhdr (2026-07-30) — Business ✅ USER-CONFIRMED; header-float measured next

Business Deals box CONFIRMED working (task #63 closed). Notch pin
verified riding the track (H&E screenshot). REMAINING (user): the
"Monthly Expense/Estimate" HEADER ROW floats on the frame ABOVE the pink
section box in the slider departments (H&E + Utilities flagged; same
arrangement in all five). The header create (0x7883E7) has NO y arg -
sub_779660 flow-lays it from an internal cursor - so the fix needs the
LIVE geometry of headers 0xABCDE01/02 + the section box, which sat just
past MWKID's 24-child print cap. v2.25.31 raises the cap to 48
(measurement build; deployed 13:01). Next session's H&E open gives the
exact rects; then the header gets a computed pin or const, not a guess.

## v2.25.32 BHDR measurement + THE DECODE DIRECTIVE (2026-07-30 ~13:10)

BHDR (13:06) delivered the content pane's full anatomy — title (40,8
723x41), headers 0xABCDE01/02 at y=68 INSIDE their own band BMP
(0,58 1000x46), section slab BMPs from y=104, all texts vt 00ADFEB8 (a
second text class). Findings logged in
**tools/research/BUDGET-DETAIL-ANATOMY.md** (the new reference doc for
this dialog family — read it before touching anything here).

Surprises the measurement caught:
- The header is structurally CORRECT (inside its band, above the slabs);
  whether the band should be COLORED (art-starved → BMPX candidate) is
  a STOCK question, not decidable offline.
- My 0x7883DD header-x patch did NOT reach the live header (still x=18)
  — its real create site is an unfound branch.
- HIDDEN item-row sliders exist at the OLD consts (260,110) vis=0 — a
  second, unpatched slider creator.
- NOTCHPIN verified working (dumps show pre-pin state, user screenshot
  shows on-track).

USER DIRECTIVE (13:1x): scroll buttons are ALSO floating vs docked;
STOP incremental patching, decode the boxes fully, and COMPARE TO STOCK.
The stock capture procedure (AutoScale tier 1.0 = DLL fully dormant at
low resolution) is in the anatomy doc §5; the user runs it at 1200x800,
screenshots land in _tests/captures/stock-budget/. A speculative BMPX
hook under the pane was drafted and deliberately NOT shipped pending
that reference. The scroll arrows are in NO dump yet (deeper than the
pane's direct children) — measuring them is part of the next
instrumented pass, gated on the stock reference arriving first.

## STOCK CAPTURE SETUP (2026-07-30 ~13:2x) — game is now TRUE STOCK 1024x768 windowed

Parked to Documents\SimCity 4\_stockpark\: SC4UIScale.dll, the four
active z_ dats (DialogStatic/ItemIcons/SelectiveArt-2x + WebText),
zzz-SC4UIScale\, BOTH FontStyle.ini copies (Documents + install
Plugins - the probed one). dgVoodoo renamed .off (software mode per the
resolution-control memory). SC4GraphicsOptions.ini: Software / 1024x768
/ Windowed (prev values in the park dir). SC4TouchControls untouched
(hard rule). RESTORE = one command: _tests\Restore-StockPark.ps1
(game closed), then expect "tier 2.00 (scaling active)" on next launch.
[2026-08-23: that one-off script has been retired — the restore below ran
clean and the park backup dir no longer exists. Live stock instrument =
Set-StockCompare.ps1.]
Captures land in _tests\captures\stock-budget\.

## ✅ STOCK REFERENCE CAPTURED + PRODUCTION RESTORED (2026-07-30 13:2x)

Ten true-stock 1024x768 windowed captures (main budget x2 + all nine
detail dialogs) live in **_tests\captures\stock-budget\** with
STOCK-REFERENCE.md mapping files to dialogs and carrying THE STANDING
DIRECTIVE (user): our 2x output SHOULD BE these dialogs scaled, and
every fix is decided from GEOMETRY/MATH against this reference — stock
relationship expressed as math, verified against MWKID/BHDR rects —
NEVER pixel counting. Restore-StockPark.ps1 ran clean: DLL, four dats,
zzz overrides, both FontStyle.ini copies, dgVoodoo all back; graphics
config back to DirectX 2400x1600 FullScreen (verified ALL RESTORED).
Next launch must log "tier 2.00 (scaling active)". The parity pass
(task #70) now has its ground truth; first reads: header band, scroll
arrows, Neighbor Deals columns.

## v2.25.33-bandart (2026-07-30) — the stock-confirmed band fix + arrow hunt

First parity-pass build against the stock reference:
1. BMPX hook over the budget content pane 0x0423278E, installed from the
   BHDR block on every content change (idempotent per instance). Stock
   captures PROVED the header band is a colored strip attached to the
   section box; ours drew its 1x art invisibly (GZWinBMP
   dst-follows-src). Expected log per department open:
   `UiSpike: BMPX N instance(s) hooked under 0x0423278E (budget pane)`.
   VERIFY: header band (and title band) draw colored in the five slider
   departments; header visually attached to the box like stock.
2. BHDR now walks ONE level into the anonymous band/slab BMPs - the
   scroll arrows (stock: docked flush at the section's bottom-right)
   are somewhere below them and have appeared in no dump yet. The next
   session log identifies their windows; docking math comes from the
   stock relationship (arrow right edge = section right edge, bottom =
   section bottom).
Deployed 13:25:50 (game closed) + both suites green.

## v2.25.34-bandonly (2026-07-30) — the hook narrowed, revert law applied

v2.25.33 verdict from user screenshots: MIXED. The header band DID draw
colored + attached in Public Safety (the stock-correct outcome) — but
the whole-pane hook also re-drew the SECTION SLABS whose art embeds 1x
COLUMN-DIVIDER lines; doubled, they painted pale vertical stripes
through PS + H&E ("broken"). Ordinances "close!" (its headers were
always inside the section box — the hook contributed nothing there).
LAW ADDENDUM to the art-owns-size family: **a slab/backdrop art can
carry LAYOUT PIXELS (column dividers) — doubling its draw relocates the
layout inside it; only pure-band art is safe to redraw scaled.**

v2.25.34: the pane hook now gates to the HEADER BAND only (anonymous
id, T>0, height 20f..29f — font-derived so factor-scaled), slabs
excluded. Expected log:
`UiSpike: BMPX N header band(s) hooked under 0x0423278E (budget pane)`.
VERIFY: PS/H&E stripes GONE, header band still colored + attached.
Deployed 13:33:21 + both suites green.

STILL OPEN in the family: Neighbor Deals (#62, untouched yet — combo
truncation "7000N" vs stock "7000MWh/mo", column layout from a computed
helper); scroll-arrow docking (windows will appear in the deeper BHDR
dump next session); PS/H&E residuals after the stripe fix (re-verify,
then judge remaining deltas vs the stock captures BY GEOMETRY).

## v2.26.0-familyparity (2026-07-30) — THE COMPREHENSIVE PASS (plan-approved)

Three parallel decode agents mapped the ENTIRE budget-dialog machinery;
BUDGET-DETAIL-ANATOMY.md fully rewritten as the engine reference (band
stacker sub_77A6F0, art families, metric source 0x7881DE, group-1/2
twins, corrected identities: "subtotal plates"=SCROLL ARROWS, white bar=
track rule 140155C8, 0x77F5xx region=NEIGHBOR DEALS rows not Taxes).

SHIPPED (all in-memory, verify-before-write, values=round(stock*f)):
1. Band BMPX hooks REMOVED (v2.25.33/.34 - contraindicated: geometry/art
   already stock*2; the hook double-drew already-2x art).
2. LIVE dept header pair: 0x78898B (x 18f) + 0x7889C0 (margin 38f) - the
   earlier 0x7883DD patch had hit the DEAD group-1 twin.
3. Hidden item-row slider twin: 0x78916D (260f) + 0x78916A (110f cap127).
4. SCROLL-ARROW anchors: 14x sub r32,0x21 -> 33f (Ordinances 0x77D61C/61/
   A6/EB, deals 0x781ACD/B11/B52/B96, Transportation 0x787511/54, slider
   depts 0x7895AD/F3/0x789639/7F). Our 2x strips put ink at W-33f+16f =
   R-17f = the stock anchor.
5. NEIGHBOR DEALS: 13 labels 18f, 12 values 218f, 12 backings 206f
   (art 140155B8 verified already 2x in SelectiveArt), 12 combos 218f,
   14 right-cols 38f, title 20f/8f, header 18f - all imm sites; combo
   WIDTH via runtime pin (lea disp8 max 127): W==120 -> 120f, the combo
   class re-lays its own drop arrow. Expected startup line:
   `CodePatches: budget family x2.00 (31 imm8 + 44 imm32 + 29 sub-imm8 sites), bizbox 600x127 (7 sites).`
   (counts: imm8 13+4+9+4+3+... verify live; any shortfall = twin/byte
   mismatch to investigate, not force.)
Deployed 14:10:31 (game closed) + both suites green. VERIFY per plan: gray
band judged fresh (hooks gone), arrows docked R-17f/B-14f, deals full
"7000MWh/mo", H&E/PS headers at 36 w/ margin 76.

## v2.26.1-masterbudget (2026-07-30) — the eye-icon sub-dialogs, found by AUDIT

User: "the subflyouts you get to using the eye are not scaled" (Master
Power Budget / Master Police Budget, 1x-sized boxes with 2x text). The
log had ended before they opened, so this was decoded OFFLINE from the
engine model - no extra game session needed:

AUDIT: enumerated every band-art instance the budget region references
(region.asm push-imm scan) and tested each against the deployed
SelectiveArt dat. Result: 0x140155D0-D7 (depts/deals) SHIPPED,
0x140155F0-F7 (Ordinances) SHIPPED, and **0x2BFEB0CB-CF (650-wide
family) MISSING** - the only gap. That family belongs to the THIRD band
stacker sub_77A960 (caller 0x786C83), i.e. the MASTER BUDGET builder
(the decode agent had guessed "Transportation" for this caller; the
audit corrects it - Transportation renders fine and uses another path).
Per the engine (dialog W/H = SUM OF BAND ART SIZES) unstaged 1x bands =
a 1x-sized dialog holding 2x text = exactly the reported overlap. The
0x140155B4-F7 range in CODE_BOUND_TGIS never covered 0x2BFEB0xx.

FIX:
1. DATA: the five arts staged 2x in all three tiers (CB header 650x23,
   CC slab 650x36, CD cap 650x41, CE footer 650x40, CF title 650x29 ->
   1300-wide at 2x). SelectiveArt 632 -> **637** per tier;
   Test-DatIntegrity.ps1 updated in the same pass.
2. CODE: the master builder's interior columns added to the family
   tables - title x/y (20,8 @0x786CA4/A2), header x (21 @0x786E00),
   both funding sliders (x 200 @0x787024, x 305 @0x787075; widths 90
   @0x787021/0x787072 - 180 exceeds imm8 so they clamp to 127 with a log
   line), right column x (345 @0x7871FB). Its buttons and scroll arrows
   were already covered by the existing tables.
Deployed via wait-for-close (game was running). VERIFY: Master Power /
Police / Fire / Education boxes open at full 2x size with columns
(Buildings / Funding / Capacity / Monthly) separated.

LAW (extends law 13): **a dialog whose SIZE comes from art is 1x until
its ENTIRE art family is staged - audit families by enumerating the
code's art references, not by eyeballing which dialogs look wrong.**

## v2.26.2-masterrows (2026-07-30) — the master ROW LOOP, measured live

v2.26.1 verdict: the art staging WORKED - the master dialogs now open at
1300x338 (MWKID 14:41:56, i.e. the frame doubled from the staged bands)
and they reuse the SAME shared transient id 0x0423278F. What remained
was the row interior, and the live dump gave every number:
  name text 0x0ABCDE06/09 (21,y 177x30)  <- still stock
  sliders  0x0ABCE400/500  (400/610, 127x36) <- patched OK
  notches  0x0ABCE200-203  (263/368, 16x36)  <- stock-derived, left behind
That dump also PROVED the helper arg order (earlier push = WIDTH, later
push = X): the name window's measured 177 is exactly the 0xB1 pushed at
0x786FA4.

Root causes fixed in v2.26.2:
1. Row columns never patched -> collisions (capacity text x=400 sat under
   the patched slider 1 = the "strikethrough" rows; monthly width 85
   truncated "§12,0"; name width 177 clipped "Deluxe Police St").
   Sites added: name x 0x786FAA / w 0x786FA4; capacity x 0x7870E0 / w
   0x7870DD; monthly x 0x787168 / w 0x787165; column headers
   0x786E6E/76 (Funding 190@255), 0x786EAC/B4 (Capacity 220@350),
   0x786EE6/F1 (Monthly 135@470).
2. THE NOTCH DUPLICATE-CONSTANT TRAP: the loop re-derives each row's
   funding notch from the SLIDER X CONSTANTS in two NON-PUSH encodings -
   `lea ecx,[eax+0xC8]` @0x786F26 and `add eax,0x131` @0x786F2C - so
   patching only the push sites moved the sliders and orphaned the
   notches (263/368 = base 63 + STOCK 200/305). New RawImm32Site table
   patches both (opcode+imm verified). LAW: **a constant can appear in
   several ENCODINGS (push/lea/add); a byte-signature scan for `push`
   alone will miss its twins - scan by VALUE across encodings when a
   patched element's companion stays behind.**
3. NOTCHPIN generalized: pairs a notch with the nearest slider at/left of
   it in the same ROW across three slider families (dept 0x0ABCDF0k
   79/110, master 0x0ABCE40k / 0x0ABCE50k 63/90) and no longer keys on
   the single hardcoded x=339; idempotent (skips when already seated).
Expected startup line gains a fourth counter:
`budget family x2.00 (38 imm8 + 56 imm32 + 29 sub-imm8 + 2 notch sites)`.
Deployed 14:52:06 + both suites green.

STILL OPEN (measured, not yet judged): the ORDINANCE DESCRIPTION popup
(id 0x0423278D, live (30,340 840x125) inside the Ordinances dialog - the
user's "crushed" report). Same id as the Business Deals empty box but a
different sizing path; its 125 height cannot hold 2x body text. Decode
its size source (the 0x78B81A reference to 0x0423278D) before patching.

## v2.26.3-mastersubtotal (2026-07-30) — subtotal value + the white-bar identity

User on v2.26.2: "getting better" - names, sliders, capacity/monthly
columns all correct (live dump confirms name 354@42, slider 127@400,
notch 463 riding its track). Two residuals reported:

1. SUBTOTAL VALUE misplaced (red figure left of its own label, outside
   the box). CAUSE: the value is a SEPARATE create (sub_779B80 @0x787262,
   align 6 = right edge lands on x, w@0x78724A x@0x78724D) from the
   "Subtotal" LABEL (sub_779660 @0x787204, x@0x7871FB which v2.26.1 had
   already patched). Patching one and not the other inverted their order.
   Fixed: value right-edge 520 -> 1040 (stock relation W-130) + width
   85 -> clamp 127. LAW ECHO: label and value are independent creates -
   patch the PAIR or they cross over.

2. THE WHITE BAR = the funding-notch art (0x140155C8, ids 0x0ABCE2xx,
   16x36 at 2x) of the row's SECOND (Capacity) slider column. Measured:
   slider2 0x0ABCE50k sits at 610 with vis=0 while its notch 0x0ABCE20k
   at 673 can be visible -> a tick with no visible track. Positionally we
   are stock-faithful (stock: notch 368 inside the 305..395 track; ours
   673 inside 610..737 - the same proportion), so this is UNCHANGED stock
   behaviour merely twice as prominent. NOT patched: no stock master-
   dialog capture exists to judge it against (the 2026-07-30 stock set
   did not include the eye sub-dialogs). NEXT TIME AT 1024: capture
   Master Police/Power to settle whether stock shows that tick at all.

Deployed 15:05:40 + both suites green.

## STOCK MASTER-DIALOG REFERENCE (2026-07-30 15:11-15:12) + v2.26.4

Two true-stock 1024x768 captures of the eye sub-dialogs archived as
_tests\captures\stock-budget\stock-1024-master-1511*.png (Master Police,
Master Power). Programmatic measurement settled the open question:

**THE WHITE TICK IS STOCK.** Pixel scan of the stock Master Police row
band finds a 2px near-white vertical run at x=457 inside the funding
track - the same element we render at 2x. Our placement is proportionally
identical (stock notch inside its track; ours inside the doubled track),
so it is NOT a defect and must NOT be "fixed" away. Recorded so nobody
re-opens it.

**CAPACITY TEXT MUST NOT CLIP** (user: "nothing should be cut off"):
stock Master Power shows the full "45055/54727" (text bbox 610..755) and
"457/556"; our 2x truncates because the column's width constant clamps at
the push-imm8 ceiling (120 -> 127 instead of 240). Same for the monthly
column (85 -> 127 instead of 170) and, on the evidence of the stock
subtotal row, possibly the subtotal value's own width.

WHY NO PATCH THIS ROUND: converting those stock pixel measurements into
2x targets requires knowing sub_779B80's arg order (is the earlier push
WIDTH or something else?). That order is PROVEN for sub_779CA0 (name:
live 177x30 @21 == the pushed 177/21) but NOT for sub_779B80, and the
subtotal value's measured stock right edge does not match the assumed
520 - i.e. at least one assumption is wrong. Per measure-don't-infer the
fix waits for live rects of those windows.

v2.26.4-instancemeasure (deployed 15:19:27, suites green) makes that
possible: the budget pin/dump block now iterates EVERY 0x0423278F
instance (master + department are open simultaneously and share the id -
GetChildWindowFromID only ever returned one, which is why the master's
pane was never dumped), with a per-instance BHDR signature and a new
header line `BHDR instance N dlg (x,y WxH) pane children=N`. One open of
a master dialog now yields the capacity/monthly/subtotal window rects,
and the remaining columns become arithmetic.

## v2.26.5-notchwidth (2026-07-30) — three measured fixes, one self-inflicted

The v2.26.4 per-instance dump finally exposed the master dialog's pane
(BHDR instance 0 dlg (550,631 1300x338), 17 children) and settled
everything:

1. NOTCH PIN REGRESSION (mine, v2.26.2). The "generalized" pairing added
   a position test (`slider.L > notch.L + slider.W -> skip`) which is
   FALSE exactly when the notch still sits at its stock x - department:
   notch 339 vs slider 520 -> rejected -> the pin silently stopped
   firing on EVERY department dialog (user: "the white lines are wrong
   on the initial flyouts as well"). Log proof: 0x0ABCE200-205 all at
   x=339 beside sliders at 520. REWRITTEN with deterministic id pairing,
   no position test: dept notch 0x0ABCE20k <-> slider 0x0ABCDF0k (79/110);
   master notch n <-> row n/2, col n%2 -> 0x0ABCE400|row / 0x0ABCE500|row
   (63/90, both measured). LAW: **a pin's pairing rule must not depend on
   the state the pin is there to correct.**
2. CAPACITY/MONTHLY TRUNCATION. Measured: capacity texts (800,w127),
   monthly+subtotal texts (1040,w127) - x right, width stuck at the
   push-imm8 ceiling instead of 240/170 (stock 400,w120 / 520,w85; stock
   capture shows "45055/54727" in full). 240/170 are unencodable there,
   so a WIDTH PIN widens them (gated on a master-only slider id,
   idempotent). Stock adjacency 400+120=520 reproduces as 800+240=1040.
3. The (w,x) arg order for sub_779B80 is now PROVEN by those rects, and
   the subtotal-value patch (v2.26.3) is USER-CONFIRMED working - both
   master subtotals sit inside their boxes.

Deployed 15:37:54 + both suites green.

## v2.26.6-headerwidth (2026-07-30) — the last two master residuals

User on v2.26.5: everything good except (a) "Funding" header not over the
sliders, (b) Utilities capacity still cut off + headers not centred.

1. THE FIFTH HEADER. The master header row has FIVE text windows, not
   four: BHDR measured 0x0ABCDE02 at (150,68 190x30) = its exact STOCK
   pair, i.e. never patched (its create is 0x786E48, consts x@0x786E3B
   w@0x786E33 - a separate stanza from the DE03/DE04/DE05 trio I had
   found). "Funding" lives there, which is why the word stayed at half
   position while its sliders moved right. Both consts now scale.
   LAW ECHO (the dead-twin lesson again): enumerate a builder's creates
   by ID, not by how many labels the screenshot shows.
2. WIDTH PIN NEVER PERSISTED. v2.26.5 placed it inside the change-only
   BHDR dump branch, so it ran once per structural change while the
   master dialog RE-LAYS its rows on every refresh - the game simply
   overwrote it (log: capacity texts still (800,w127) after the pin
   shipped). Moved out of that branch with its own child snapshot: it
   now runs every sweep, idempotent. LAW: **a pin that corrects a
   value the game rewrites per refresh must run on the sweep, never
   inside a change-only branch.**

Deployed 15:50:40 + both suites green. VERIFY: "Funding" centred over the
funding sliders; Utilities capacity shows the full "45055/54727".

## v2.26.7-captionrelayout (2026-07-30) — built, awaiting game close to deploy

Four user items. Two FIXED, two INSTRUMENTED (measurement first, per the
standing rule - neither had ever been dumped):

1+2. CAPACITY CUT OFF **and** CAPACITY HEADER MISALIGNED are ONE bug.
   Stock/patched geometry: header (350,w220) -> (700,w440) centre 920;
   values (400,w120) -> (800,w240) centre 920 - identical centres BY
   CONSTRUCTION. Ours measured (800,w127): the clamped width both clips
   the digits AND shifts the column centre to 863, i.e. the 57px offset
   the user sees. The v2.26.6 width pin was correctly placed (verified by
   reading the built source) yet the text still clipped: the paint buffer
   is born at first-paint size - the SAME law as the U-Drive-It consoles
   and the gauges. v2.26.7 re-applies the CAPTION after widening
   (GetCaption/SetCaption, cIGZWin 160/161) to force the text object to
   re-measure into the new rect. Fixing the width fixes the alignment.
3. ORDINANCE DESCRIPTION POPUP ("crushed"): it is the SHARED text popup
   0x0423278D - the same window the Business Deals empty box uses, but
   opened through a different path (0x78B819 only fetches it by id), so
   the title/body coordinate patches made for the bizbox do not reach
   this instance. Its title/body live one level deeper than MWKID prints
   -> new POPKID dump for that id only.
4. REGION CITY-SELECT BUBBLE, Mayor Rating bar drawn twice: the region
   screen's children have never been dumped at all -> new RGKID
   change-only dump (direct children + one level), same shape as MWKID.

Built + both suites green; deploy pending game close (it was running).
NEXT SESSION: open Ordinances -> "Open Details" on any ordinance, then
go to the region and select a city. That one pass yields POPKID +
RGKID and both remaining fixes become arithmetic.

## v2.27.0-ordpopup (2026-07-30) — the ordinance popup SOLVED by measurement

Deployed 16:29:37 (auto, on game close). Two instrument bugs had to be
fixed first, both mine, both worth remembering:

INSTRUMENT LAW: **a change-only dump must hash the level BELOW the one it
prints.** MWKID/RGKID hashed only their top level, so a window that opens
one level down (the ordinance popup inside its dialog; the city bubble
inside a view layer) never changed the signature - the dumps stayed
silent with the popup on screen. v2.26.9 folds each window's CHILD COUNT
into the signature. Second: level-3 printing skipped !IsVisible children,
hiding the very windows being hunted (v2.27.0 prints them with vis=).

THE FIX (measured, POPKID 16:2x): the ordinance description popup is the
SAME window as the Business Deals empty box - 0x0423278D > content
0x0423278F > title 0x0ABCE000 (10,5 556x37) + body 0x0ABCE001
(15,25 795x75) - but built by a SECOND code path (0x78BA2D/0x78BA79)
carrying ITS OWN copies of the coordinate constants, which is why the
bizbox patches (0x77C260-88) never reached it. At 2x the title is 37 tall
while the body still starts at y=25 -> the description runs through the
title ("crushed"). All four constants now scale (0x78BA29/2B/75/77); the
popup's height is computed from body.y + body.h + margin, so the box
grows to fit by itself.
LAW ECHO (third time today): one window id can be built by several code
paths - patching the constants of one path proves nothing about another.

STILL OPEN (last item): region city-select bubble, Mayor Rating bar drawn
twice. Bubble LOCATED at last: 0x0A551C50 (1049,456 516x500), a child of
view layer 0x2BA6BB97 - never reachable by any previous instrument. Its
visible children are the 3 icon buttons + 3 stat rows + 2 backdrops; the
rating bar is among the children reported NOT visible or one level below,
which v2.27.0 now prints.

## v2.27.1-popfit (2026-07-30) — the popup grows to its text

v2.27.0 verdict (user: "90% there"): the title/body overlap IS gone -
measured (30,50) body under a (20,10 697x37) title. Remaining: the
description is cut off. MEASURED CAUSE: the body window itself is
750x25 - ONE line tall - inside an 840-wide box, so the text is clipped
at the WINDOW's edge, not the box's. sub_779660 sizes that window from
the UNWRAPPED caption (window width = 1000 - textWidth, height = one
line): a 1x-era assumption that only holds while the caption fits on one
line. At 1x these descriptions do; at 2x they do not.

FIX (POPFIT, runtime pin beside the budget pins, every sweep, gated on
the popup being visible): give the body the box's inner width
(popup.W - 2*inset), re-apply its caption so the text object re-wraps
and reports its true height (the caption trick that fixed the capacity
column), then grow popup AND its content child to body.T + body.H +
12*f. Logs `POPFIT body (...) -> popup WxH` for verification.

Deployed 16:35:36 (auto on close) + both suites green.
VERIFY: open several ordinances' details incl. a long one (Smoke
Detector) - whole description visible, box taller, title clear.
LAST OPEN ITEM: region city-select bubble Mayor Rating bar drawn twice
(bubble located: 0x0A551C50 under view layer 0x2BA6BB97; v2.27.0 dump
now prints its hidden children + one level deeper - needs one region
visit to capture).

## v2.27.2-fittotext (2026-07-30) — ask the text object, don't compute

v2.27.1 verdict: POPFIT never fired (0 log lines) because the box is NOT
too short - measured body 750x25 inside an 840x125 popup. The sentence is
clipped at the BODY WINDOW's right edge (text ends at ~774 = the window's
780 edge), i.e. the window is ONE LINE tall and narrower than the box
while the rendered text needs ~920. Widening + caption re-apply did not
make it re-wrap.

v2.27.2 stops hand-computing: QI the body to cIGZWinText (IID
0x212CDC1F) and call FitWindowToText(false,true) - the text object sizes
its own window to its wrapped content. If the engine will wrap at all,
this is the sanctioned lever; if it will not, the next log proves that
directly instead of another inferred patch. Deployed 16:43:37; suites
green.

## REGION BUBBLE — FULLY MEASURED, and the rating bar is NOT A WINDOW

RGKID (v2.27.0, hidden children + depth 4) captured the city-select
bubble 0x0A551C50 (1049,456 516x500) under view layer 0x2BA6BB97, with
every child: 0xCC06F4CF/0xAC06F4C4/0x6C06F4A0 (80x40 at ~220,94),
buttons 0x4A560000-3, three anon stat rows (294,194/224/256 ~186x32) and
two backdrops (0,392 516x86 / 0,0 516x392 with an inner 24,20 470x284).
NOTHING sits where the Mayor Rating bar renders (~37,198 216x30), so the
bar is CODE-PAINTED by the bubble's own draw routine.

NEXT STEP (zero-build A/B, user-runnable): set [Spike] RatingArrowPatch=0
in SC4UIScale.ini and re-check the bubble. Our ApplyRatingArrowScale
doubles the HUD rating-bar reveal multiplier (7->14 at 0x7E87B1/9D7/A02);
if that same controller paints the region bubble's bar, the doubled
multiplier is the duplication and the patch must be scoped to the city
HUD. If the bar is unchanged with the patch off, it is the bubble's own
painter and needs an exe hunt.

## v2.27.3-forcerelayout (2026-07-30) + the region A/B RESULT

REGION BUBBLE A/B (user-run, zero build): with [Spike]
RatingArrowPatch=0 the Mayor Rating bar in the city-select bubble STILL
draws doubled -> **our rating-arrow patch is NOT the cause** (setting
restored to 1; the city HUD needs it). Combined with the RGKID finding
that no window exists where the bar renders, the bar is painted by the
GAME's own bubble routine. That item is now a fresh exe hunt, not a
tweak: find the bubble's paint path (bubble 0x0A551C50 under view layer
0x2BA6BB97) and the fill-segment loop it uses.

ORDINANCE TEXT - the user named the mechanism: "it never expects to
wrap". Everything observed follows: the description's layout is computed
ONCE at creation against a width that is not this window's, so it
renders as one long line and is clipped at the window edge; widening the
window afterwards changes nothing because nothing re-triggers layout,
and re-applying the SAME caption is a no-op (the text object early-outs
on an unchanged string - which is why v2.27.1's caption re-apply and
v2.27.2's FitWindowToText both failed to wrap it).
v2.27.3: clear the caption to empty, then set it back. That is a genuine
change, so the text object must re-lay out at the window's CURRENT
width and break into lines; the popup then grows to the wrapped height.
Deployed 16:59:56 (auto on close) + both suites green.
IF THIS STILL DOES NOT WRAP: the wrap width lives inside the shared text
helper sub_779660 (`push 0x3e8` = 1000 at 0x77971A). Patching it is
GLOBAL - every label built by that helper derives its window width from
1000 - textWidth, and align-6 (right-anchored) labels position at
x - winWidth, so a blind change would shift every right-aligned column.
Scope it per-call-site or not at all.

## 2026-07-30 EVENING — SESSION END, HANDOFF WRITTEN, POPUP UNSOLVED

v2.27.3 deployed 16:59:56 (suites green). The ordinance popup fix FAILED a
third time (user: "Neither worked and I don't think you're solving it").

USER FEEDBACK THAT MATTERS MORE THAN THE BUG (verbatim): *"I just feel that
you haven't been referring to your own playbooks and testing. It's like a
regression of discipline when you should be checking your own documentation
THAT YOU CREATED."* Correct, and provable:
- BUDGET-DETAIL-ANATOMY.md §1, written by me earlier the same day, already
  states that sub_779660 sizes its window as `1000 - textWidth`
  (`push 0x3e8` @0x77971A). That is the prime suspect for the popup's wrap
  width. Three builds were spent without testing it because the doc was
  never re-read.
- STOCK-REFERENCE.md carries the user's directive (output = stock scaled,
  judged by geometry). Three fixes were attempted on a popup NEVER captured
  at 1x - the cheapest decisive fact, still ungathered.
COUNTERMEASURE SHIPPED: a PRE-FLIGHT checklist now heads HANDOFF.md (re-read
the element's doc section -> check the failed-attempts table -> confirm a
stock capture exists -> measure live rects -> express the fix as
round(stock*f) -> only then code -> verify from the log). README.md points
at it; the run sheet leads with it.

DOCS UPDATED FOR THE COMPACT: HANDOFF.md (plan-first directive + pre-flight
+ current state + the two open items), BUDGET-DETAIL-ANATOMY.md (new
§POPUP: full window tree, the two builder paths, the failed-attempts table,
the four questions a plan must answer, and the stock-capture procedure),
_tests/REGRESSION.md (expected startup lines for v2.27.3 + laws 14-21),
_tests/RUN-SHEET-NEXT-SESSION.md (banner), README.md (pre-flight pointer),
VERSION-HISTORY.txt (through v2.27.3), this checkpoint.

NEXT SESSION STARTS WITH: a PLAN for the ordinance popup (user order). Do
not ship code before answering §POPUP P4's four questions, and get the
stock capture first.
