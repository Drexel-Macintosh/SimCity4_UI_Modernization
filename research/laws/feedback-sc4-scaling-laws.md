---
name: feedback-sc4-scaling-laws
description: THE 105 LAWS (as of 2026-08-18; **69 "this wasn't like this before" is a BISECTION BOUNDARY, not an opinion - two reverts were spent on changes that had nothing to do with the symptom because the reports merely ARRIVED after a deploy; when a revert does not move the symptom the attribution was wrong, go bisect**; **70 a "SAFE" over-approximation is still a change and it is paid for in PIXELS - CellUnit's LCM{2,3,4,6,8,12,16,24} made a 200px FOUR-state sheet snap on 8, pushing 300 (already a clean multiple of 4) to 304 so every cell shipped a pixel too wide; measured 152 vs 34 for LCM{3,4}, i.e. the shipped set was the worst option except doing nothing**; **65** a fix that MOVES things is judged by its DENSEST NEIGHBOURHOOD - a 2px nudge was invisible on a 5-button flyout and wrecked a 21-face grid, the advisors, the budget rows and the dock**; **66 editing geometry in a .UI has the scope of THAT .UI; editing ART has the scope of the WHOLE GAME - flyout strip items are created at RUNTIME, appear in no .UI, and still bind art by TGI, so the builder's conflict check was blind by construction**; **67 when the SIZE is wrong change the SIZE, not the position and not the art - leaf windows take ScaleRound(w,f) size-derived; containers keep edge-derived or #143's white seams come back**; **68 read the format off the SHIPPED BYTES - the LTEXT header is a CHARACTER COUNT, and the neighbouring record is both the format spec and the style guide**; NEWEST AND MOST USEFUL: **64 GO FIND THE INSTANCE THAT HAS A SIBLING THAT WORKS - "the sun and moon are wrong" survived TEN failed theories in a day; "ONE of these FIVE identical buttons is wrong" named the cause in minutes (the broken one is the only one at an ODD left edge, and ScaleSubtree is edge-derived so odd l costs the window 1px at f=1.5 while the art cell keeps all 71). Also: ScaleDim's CellUnit is a GUESS the BUILDER never has to make - sheetW = states*ScaleRound(w*f); and regenerate from the 1x source, never resample the upscaled sheet**) (also: **60 the "broken at 1.5x, perfect at 2x/3x" tier signature is the NULL HYPOTHESIS, not evidence - EVERY two-scaler disagreement is 1.5x-only by construction, and four theories matched it perfectly while all four were wrong**; **61 GZWinBtn STRETCHES - cell need not match window; 420 mismatches at 2x AND 3x on user-confirmed-perfect tiers, so this may never justify changing ScaleDim/ScaleSubtree**; **62 build the instrument that can SEE the defect class, not another that can only COUNT - tools\uimap\emu\render_flyout.py is the first offline COMPOSITOR and killed two theories in 3 min each**; **63 before repairing a discrepancy, prove the broken thing actually READS the value you are changing - the imagerect under-read was real arithmetic, broke the thumbnails twice, and those buttons have no imagerect at all**) (older: THE FIFTY-NINE laws as of 2026-08-05; 59 every consumer of a SHARED HOOK needs its OWN gate - #127's born-correct dock sat behind ShowHook, which ships at 0, so it NEVER EXECUTED for ten versions and two correct fixes changed code on a dead path; prove the branch runs from the LIVE ini + the 'installed (mode N)' log line, never Settings.h. Also: an ANCHOR'S LIFETIME is part of the dock, and a show detour fires BEFORE the visible bit so gate on GEOMETRY**) (older: THE FIFTY-TWO laws as of 2026-08-04) that decide every SC4 UI-scaling fix (latest: **51 when the game REFUSES to do something, find the one instruction that refuses - do NOT paint over it; #121 burned ~13 builds on five pixel-level cures before one unsigned compare (a 5-entry blitter table indexed zoom+2) turned out to be the whole defect, and compositing ORDER made every post-hoc repair impossible in principle**; **52 a fallback you did not retire is a bug with a polite name - the real fix landed and the OLD workaround still overwrote it; the gate must be a live expression, never a sentence in a comment, and prove retirement with a log census**; 50 a documented setting that does nothing is a LIE and needs a gate; 49 wasteful-looking code is load-bearing until the comment says otherwise, and prefer an EXISTING counter over a new flag; 48 a gate can be RIGHT about its bytes and WRONG about the question; 47 a control that DRAWS right but does not RESPOND = our geometry pushed it outside an ANCESTOR's rect, and the stock control settles it in 2 min with no build; 42 an offline gate is only as honest as its SCOPE; 41 an installed hook is not an EXECUTED hook; 40 deploy-line+hash-pair for every built package; 39 SetFlag-detour+design-child-count born-correct lever; 35 check what your own REPAIR destroys) (incl. law 23: scoping a guard to the case you tested leaves the untested cases unguarded; law 25: an explicit size after a clone beats the style PNG; law 26: a test that performs the step under test cannot fail) (never scale markers / font-sized controls / AdviceList children; runtime is sometimes structurally too late so fix it in DATA; identify windows positively not by size; early-phase skip lists rot; a dangling .UI ref means find the BINDER not the art; a first-open jump may be OUR correction not the game's error; gate every override built from another mod's data; your own source comment is an instrument with a SCOPE). Each cost a bad build. Read before touching UiSpike.cpp, CodePatches.cpp or any .UI generator.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-06T21:12:26.290Z
---

Learned across 2026-07-28/29, each paid for with at least one shipped
regression. Full detail: `_tests\REGRESSION.md`; test axes:
`_tests\SCENARIOS.md`; summary in the project `README.md` → *LAWS*.

**1. RUNTIME IS SOMETIMES STRUCTURALLY TOO LATE — FIX IT IN DATA.** Where the
game reads geometry BEFORE the first sweep can run, no timing trick wins:
3D advisor heads are framed when BOUND at city load; the ticker marquee's width
is cached at init and re-imposed every roll tick. Ship that geometry pre-scaled
in the shipped `.UI` and make the parent root-only (`kDataScaledSubtreeIds`) so
children are not scaled twice. Both cases burned 2-3 runtime "fixes" first
(hide/show, synthesized clicks, per-frame re-apply) that half-worked; the data
fix deleted the hack entirely.

**2. NEVER SCALE THESE:**
- **Alignment markers** (`id=0x0000AAAA`) — positioning DATA. The game places a
  panel at `anchor − markerOffset` in NATIVE units, so scaling one displaces
  the whole panel by exactly that offset. True at runtime AND in shipped data.
- **Font-sized / art-sized controls** (`kFontSizedIds`) — a control sized from
  its rendered caption or its own art is ALREADY correct once fonts/art are 2x;
  scaling again doubles it (a row went 2x too tall; a spinner overflowed its
  parent and lost its down arrow entirely).
- **`cSC4WinAdviceList` children** — items are game-sized to the container.
- Never suppress paints to hide an open-flash; **pre-scale while HIDDEN**.

**3. IDENTIFY WINDOWS POSITIVELY, NEVER BY SIZE HEURISTIC.** Content-sized
windows (tooltips!) defeat any size range. Use exact width, class+id, or an
explicit mode split.

**4. STATE GATES MUST BE VERIFIED IN ALL THREE STATES** — pre-founding god,
founded god, founded mayor. A gate right in two and wrong in the third is the
most expensive bug class here. Founding a city makes several "hidden/inert"
windows go LIVE, invalidating notes measured pre-founding.

**5. ONE-SHOT CAPTURES ARE FRAGILE.** The Plot hook captures strip fields once;
any other writer running first poisons it (a sweep-side write captured 88 as
"natural" → forced 176 → 4x pitch everywhere). Sweep-side code may INVALIDATE,
never write.

**6. SKIP LISTS FROM AN EARLIER PHASE ROT (2026-07-29, task #45).** An
id-exclusion is a CLAIM about the tree, and claims written before the tree was
understood go stale silently: the city sweep skipped 0xAA32BCE6 for weeks under
a spike-era "plop-menu machinery" label — one dump read proves it is the Data
Views panel, left 1x among the 2x HUD. When a subtree's real owner becomes
known, re-audit every skip that touches it. Corollary (proven twice, I-898897de
then I-2bc9060f): when one window id has several script copies, identify the
LIVE script by rect-matching a runtime dump, never by filename or guesswork.
BUT the sequel is its own law: the standard fix on that panel was perfect
COMPACT and **crashed the game on EXPAND** — the lifecycle axis includes
expand, and on panels carrying code-painted surfaces the untested state can be
fatal, not just ugly. SOLVED the same night by offline disassembly, ✅
user-confirmed at v2.21.3: the expand path was innocent (pure show/hide); the
killer was the map child 0x00004203 = **a second cSC4WinMiniMap instance**
whose ONE-SHOT display surface stayed 256 while the renderer (sub_7A2F60)
built window-sized buffers. TWO REUSABLE RULES: (a) **every cSC4WinMiniMap
instance that gets scaled needs the destroy-and-recreate surface lever**
(GetClassID 0x7A6580 = clsid 0xCA318388, iid 0xCA318385 — find instances by
those); (b) **code-managed legends get re-laid on every view-select with 1x
origin constants + 2x font-derived pitches** — cure is a PIN-BACK pass
re-imposing scaled design geometry each sweep while visible (DVPIN, the
RCI-column treatment; targets DPROBE-measured, never inferred). The panel is
THREE coupled parts — sweep+art (358), DVMAP recreate, DVPIN — breaking any
one regresses it (REGRESSION.md "DATA VIEWS PANEL").

**7. A DANGLING .UI REF MEANS THE PIXELS ARRIVE AT RUNTIME — FIND THE BINDER,
NOT THE ART (2026-07-30, v2.25.0).** "Generate the missing 2x" is a category
error when the referenced TGI exists in NO shipped archive under ANY type
(prove it with `tools\dbpf\find_tgi.py`, an any-type index scan — the
type-filtered extraction CSV cannot prove absence). The U-Drive-It picker
cells' `{46a006b0,ea32f104}` is such a placeholder: binder 0x76FDB0 SetImages
{group 0x4C06F888, vehicle-exemplar prop 0xEBFC5E5E} at runtime. Fix = stage
the WHOLE runtime-bound group 2x (collision-checked) + scale the placeholder
imagerects with it (`RUNTIME_BOUND_2X` in build_dialog_static.py) — but ONLY
for scripts whose runtime pixels really are that group; the Select-A-Sim
picker shares the SAME placeholder TGI yet receives runtime-GENERATED
portraits (imagerect 36x41 = the tell), fixed instead by the self-limiting
BMPX dst hook (GZWinBMP Plot 0x9BC325 draws dst = src size at the window
origin; window rect never read). Both builders now print classified
`WARNING LEFT1X ... DANGLING vs MISSING-2X` lines — read them every build.

Related: [[reference-sc4-flyout-alignment-marker-rule]],
[[feedback-sc4-measure-dont-infer]], [[feedback-sc4-prescale-while-hidden]],
[[project-sc4-ui-scaling-northstar]], [[feedback-sc4-regression-net]]

**8. SAME-PROJECT DATS COMPETE IN THE LOAD ORDER LIKE FOREIGN MODS**
(2026-07-30, the budget saga). When an override "mysteriously doesn't
load", enumerate EVERY shipped copy of that TGI across our OWN dats first
(Plugins-wide index scan). SelectiveArt (alphabetically after
DialogStatic) shipped 1x-geometry copies of the budget scripts and
silently beat the doubled ones for hours of debugging.

**9. EVERY ID IN A RUNTIME DIALOG LIST IS NON-UNIQUE UNTIL PROVEN
OTHERWISE.** A hidden template + the open instance share one id; a
first-match find plus IsVisible() silently skips the real window. Iterate
ALL instances (IdCollectCtx). Dialog scaling must PRESERVE THE CENTER and
clamp on-screen (a doubled-in-place 1000-wide modal put its buttons at
x=2700 - unclosable).

**10. IDENTITY = CONTENT-MATCH, NEVER TIMING-CORRELATION.** Ids picked
from "what the user had open when the log line appeared" were the advisor
toasts, double-doubling them. Corpus root-id proof or exe builder proof.

**11. CLASSIFY THE WINDOW SYSTEM BEFORE PICKING A MECHANISM.** Run a
depth-tracked TOP-LEVEL-ROOT CENSUS of the script first: the budget is a
four-root COMPOSED panel (Graphs-class -> children-only data double +
kDataScaledSubtreeIds); mis-modeling it as modals or one docked panel
each broke something different. Also: pbuffs are born at first-paint size
([win+0x6c]) - a swept window painted once at 1x keeps a clipped buffer
forever; born-2x data is the fix (U-Drive-It consoles).

**12. NEVER STRETCH FROM A WIDE (>2048 px) TILED TEXTURE** - stock only
cell-copies; a stretched blt across tile addressing splits/side-swaps the
image (gauge needle strips). Ship scaled art so draws are pure copies and
snap any hook multiplier to 1.0 for already-scaled sources. Corollary: a
positive vtable-slot check must accept OUR OWN other hooks in that slot
(FlashGuard patched GZWinBMP's slot 88 and BMPX silently never engaged).

**13. A CODE-CREATED WIDGET WITH A STYLE PNG IS BORN AT THE ART'S SIZE**
(2026-07-30, v2.25.25, the budget detail dialogs). The exe's
create-helper (sub_77B960 pattern: parent, id, x, y, styleTGI) sizes the
window from its style PNG — so widgets whose style art WE ship 2x come
out 2x with no other treatment (budget rows: strip 140155B7 1320x18 →
2640x36 windows), and a widget still 1x inside an otherwise-correct
dialog is either an explicit exe `SetSize(w,h)` const (patch the builder
immediates — CodePatches::ApplyBudgetButtonScale, 35 verified sites) or
art deliberately left 1x (shared glyphs 46A006A7 slider / 82B99D9D
spinner — CENSUS CONSUMERS before doubling; they resize game-wide).
Frames that content-fit from font metrics self-scale and must NOT be
runtime-scaled on top. HARD COROLLARY (v2.25.26, cost an immediate
user-visible tear): **a size/width guard cannot gate a REPOPULATING
window — the scale record outlives the state that matched**, and the
record-owning child re-pass then doubles whatever the game lays into
the same window later. 0x0423278F (the shared budget transient) is
BANNED from kCityDialogIds in every form; transient ids are non-unique
IN TIME, not just in the tree.

**14. BEFORE CORRECTING A WINDOW THE GAME JUST PLACED, CHECK THAT THE GAME
WAS WRONG.** (2026-07-31, task #79c.) The quit confirm jumped 213px on the
FIRST open of each session and was perfect afterwards. The defect was not the
game's placement — it was OUR corrective move; opens #2+ only looked right
because they inherited the moved position (**an uninitialised LATCH, law of
v2.36.2: later opens are PRE-WARMED, not faster**). Read out of the exe rather
than inferred, SC4 places modal dialogs at
`x=(W-w)/2` (`0x0078E409`) and `y=(H-h)/3` (`0x0078E3DF`) — deliberately a
little above centre — confirmed against three measured births (h=162→479,
175→475, 324→425). Once the dialog was born at its true SIZE the game placed it
correctly on its own, and the cure was to DELETE our centring, not to make it
faster. **A first-open jump is as likely to be our correction as the game's
error.** Corollary: match the game's own rule when you must position something,
so the born path and the runtime path cannot disagree.

**15. AN OVERRIDE BUILT FROM ANOTHER MOD'S DATA MUST BE GATED ON THAT MOD.**
Otherwise uninstalling the mod does not uninstall it — our copy lives in
`zzz-SC4UIScale\` and outranks everything. See
[[project-sc4-thirdparty-patches]] for the mechanism
(`ScaleTier::kThirdPartyDeps`) and the measurement that proved it live.

**16. BORN-SCALING TAKES A WINDOW OFF THE SWEEP — SO IT INHERITS EVERYTHING THE
SWEEP WAS QUIETLY DOING FOR IT.** (2026-07-31, Create Disaster, v2.39.0.)
Marking a container born makes `Classify` return `AlreadyScaled`, and the sweep
then skips **the whole subtree**. The strip item metrics it had been scaling all
along silently stopped: an 88x578 strip window full of 44px cells. This is the
v2.36.2 law and I quoted it in my own comment before breaking it. Before
born-scaling anything, enumerate what the sweep currently does to that subtree —
geometry, child rects, control fields, hook installs — and take on all of it.

**17. PRIME A SHARED LATCH FROM A *STOCK* VALUE; NEVER LET IT SEE A SCALED ONE.**
(2026-07-31, v2.39.1 — **duplicated icons GAME-WIDE**, a regression of the
picker-icon fix from the day before.) `SlotThunk2<88>` latches its 1x base from
a strip's own fields on the FIRST Plot, then writes `base*f` forever — and
`gStripBase*` is **shared by every strip in the game**. Writing a scaled 88 into
those fields at birth made it latch 88 and write 176, doubling every picker cell
so both art states showed side by side. **The cure is never "stop scaling" — it
is to prime the latch from the builder's own stock argument** so it cannot see a
scaled value. Corollary: before writing any field an existing hook also reads,
find the hook, read what it does with that field, and check whether the global
is **shared**.

**18. A LATE HOOK INSTALL LEAVES A STALE FRAME — CURE IT WITH ONE FORCED
REPAINT, NOT A FASTER INSTALL.** (2026-07-31, v2.39.4.) The disaster scroll
arrow was reported "missing on first open, appears after you scroll". It was
never missing — it was **unpainted**: the window painted its first frame before
the vtable swaps were in, and nothing asked it to paint again. Scrolling was the
user hand-triggering the repaint. Force ONE invalidate at the instant the state
goes live. ⚠ This is a forced repaint, **not** paint suppression (`FlashGuard`
blanked windows and is permanently banned). ⚠ Latch it **one-shot per window**:
the block that does it can run every sweep tick — 809 times in one measured
session.

**19. MATCH INI KEYS EXACTLY, NEVER BY SUBSTRING.** A guard testing for
`"BornScale"` matched the existing `SubBornScale` key, so a kill-switch write
silently did nothing and the path stayed enabled while being reported off. Use
`^\s*KEY\s*=`.

**21. A STALE FRAME THAT SURVIVES A FORCED REPAINT IS A STALE *DECISION*.**
(2026-07-31 evening, v2.39.5, ✅ user-confirmed "Disaster works!".) v2.39.4
shipped law 18's repaint cure on the missing scroll arrow and it cured
NOTHING — the draw only READS flags (`[0x118]/[0x119]`, born 0) that an
open-time decision computes; the user's scroll was not "triggering a repaint",
it was RECOMPUTING the decision. The decision had mixed units: born-2x strip
window ÷ still-1x item pitch = "nothing to scroll". Cure: **born rect requires
born METRICS** — write the strip's `0xF4/F8/FC` to `base×f` at birth, AFTER
Place, latches already primed from stock (law 17 satisfied), behind a
READ-GUARD that refuses unless the fields still hold the exact stock values.
Corollaries, both measured the same night: (a) **a dock cache must be warmable
BEFORE the first open** — warm it from the persistent anchor (the toolbar) on
every sweep tick, never from the transient window (a latch that can only warm
while the flyout is open is cold on open 1 *by construction*); (b) **a
corrective move ≠ born docked when part of the assembly is PARENTLESS** — the
disaster strip doesn't follow a container move; only the game's own layout
places it, and that runs at open (from the docked container) or on hover.
Offline proof pattern: emulate the three states (stock / half-born / born) and
assert the decision flips only in the half-born one (`emu_subflyout.py
--builder=disaster`, 62 checks).
⚠ FRAME COROLLARY (v2.39.8, found by the guard itself): **a disassembly-derived
field offset must state its FRAME.** The strip has TWO: object-relative
`0xF8/0xFC/0x100` (SetItemMetrics' `self`, vptr at +0, what birth writes) and
window-relative `0xF4/F8/FC` (the Plot's `this` = the cIGZWin embedded at +4).
v2.39.5 wrote the window frame's offsets on the object → the read-guard
refused on every open and printed `metrics left to Plot` instead of corrupting
a field. When two code sites disagree by exactly 4, they are probably both
right in different frames. The founded-city god-mode eyes-on is what exposed
it — the pre-founding "works!" hadn't isolated the no-scroll arrow (law 4:
all three states).

**22. YOUR OWN SOURCE COMMENT IS AN INSTRUMENT WITH A SCOPE — AUDIT IT LIKE
ONE.** (2026-07-31 evening, task #81.) The FLYOPEN comment said "the seven
call sites"; an exhaustive E8-rel32 scan found ELEVEN plus a byte-identical
TWIN opener (`sub_7E5D80`) with two more. Three flyouts were wrongly filed as
generation 1 on the comment's authority, and the one real generation-1 flyout
(Signs & Labels, via the unhooked twin) was invisible to it. The comment
answered "which sites did we enumerate", not "which sites exist" — the SCOPE
NULL, now proven to live in our own comments too. When a coverage claim in a
comment gates a design, re-derive it from the exe (the scan is minutes).
Bonus finds from the same audit: kGodToolFlyoutIds' two comments were SWAPPED
for weeks; `gMayorDock` defaults 0 and no redistributable ini sets it.

**23. SCOPING A GUARD TO THE CASE YOU TESTED LEAVES THE UNTESTED CASES
UNGUARDED — AND A STATE TEST MUST TEST THE STATE, NOT A PROXY FOR IT.**
(2026-07-31, the "Saving Disabled" box at 4x, ✅ user-confirmed cure.) Two
mistakes in one guard, a day apart. First: v2.38.0 added an "already scaled,
leave it alone" guard but **narrowed it to the two ids that session had
tested**, explicitly documenting the others as uncovered — and the save flow
reuses one of those very windows, so it arrived data-born 2x and got scaled
again (measured `MWKID 0xAA8DEF97 (200,241 2000x700)` = exactly 4x its 500x175
design; the `newW > scrW` bail can't catch it, 2000 < 2400). **Blast-radius
caution (law 29) is for changes that ACT; it does not apply to a guard that
only ever declines to act — narrowing that one ADDS risk.** Second: the guard's
test was `w >= designW*5/4`, which is true of an arrived-2x window **and** of
one WE scaled a tick earlier — so it would have dead-coded the per-sweep
child re-pass for the whole table and poisoned a once-per-id instrument. The
real predicate is "do we have a scale record?" — hoist `Classify` and require
`Fresh`. Caught by a 3-lens adversarial review AFTER the user confirmed the
visible fix, which is the point: **an eyes-on confirms the pixels in one
state; it cannot see a later-sweep or other-dialog regression.** ⚠ That same
review also predicted a failure the screenshot REFUTED (1x children, citing a
note that predated the family becoming data-born) — refuters inherit stale
notes too, so adjudicate them against measurement like any other claim.

**24. BEFORE CALLING TWO OF YOUR OWN LISTS CONTRADICTORY, CHECK WHAT EACH
PREDICATE IS ACTUALLY CONSULTED BY.** (2026-07-31, task #85.) Three ids sat in
both `kNeverScaleIds` and `kCityDialogIds` and I filed it as a structural
defect. It was not: `IsNeverScaleId` is honoured **only** by `ScaleOnShow`
(dormant at the shipped ShowHook=1 default) and the city sweep's
DIRECT-children loop — NOT `ScaleSubtree`, so membership never protects
against recursive descent (v2.39.13: my first write-up of this very law
misnamed the sites — law 22 struck inside law 24; the #85 mapping also proved
no width threshold works where 1x and scaled candidate sets OVERLAP — the
robust guard is an EXACT PRODUCT MATCH against measured per-id 1x bases). The
list means "never scaled *by the sweep*" — and the
dialog block is the separate mechanism for main-window transients the sweep
cannot reach. Two compatible statements about one window, read as a
contradiction because the NAME overstates the scope. **The reflex tidy-up
would have deleted a safety net**: measurement (`who_owns_tgi.py` + the staged
corpora) showed all three are data-born at *every* scaled tier, so the dialog
block's scaling of them is unreachable in any shipping configuration — i.e.
belt-and-braces for a package-load failure. The fix was documentation plus a
**self-maintaining assertion** (a one-shot log naming the overlap, which
changes if someone adds a new id), not an edit. General form: **a list's name
is a claim about scope; verify it against the call sites, and prefer making a
surprise self-explaining over removing it.**

**25. LAW 13 HAS A CONVERSE, AND THE ADVICE-LIST FURNITURE IS ITS PROOF:**
a code-created widget is born at the art's size ONLY when the creator does not
size it explicitly — **an explicit SetSize/SetArea after the clone beats the
style PNG, and then 2x art just gets `fill=yes`-downscaled into the 1x window
(no visible change).** (2026-07-31, the News row X: shipped the 2x strip on the
law-13 inference, second eyes-on refuted it — template script area 100x100,
live clone ~20px = code-sized.) Check for the explicit size BEFORE shipping
art: if the live size matches neither the art nor the script, the creator
sizes it and the lever is the sizing CONSTANT (CodePatches, the
budget-buttons pattern), with the 2x art as prerequisite, not cure. Extra
trap here: the AdviceList row furniture sits inside the no-recurse subtree
(`kAdviceListScaleSelfIds`), unreachable by every scaling pass BY DESIGN —
so "why is only this child 1x" questions on advice lists always resolve to
code-side levers.

**26. A TEST THAT DOES THE MECHANISM'S JOB BY HAND CANNOT FAIL — AND WHEN A
GUARD'S DATA IS AN UNMEASURED ASSIGNMENT, GIVE EVERY MEMBER EVERY CANDIDATE.**
(2026-07-31, task #83, both halves ✅ user-confirmed.) The mod-removed test
script moved BOTH the mod's file and our override, which is exactly what the
dependency gate is supposed to do — so it verified rendering only and the gate
was never actually exercised. A `-GateOnly` mode that moves only the mod
proved the gate fires on the SAME launch (`SyncStaticLayers` runs in
`PreAppInit`, before the plugin scan) — and immediately caught a 4x dialog I
had shipped an hour earlier. **General rule: if the test performs the step
under test, it is a rendering test wearing a gate test's name.** The defect it
found is law 23's third strike, this time inside law 23's own fix: I gave each
confirm id the single base I *believed* its script owned, and the
script↔id mapping was swapped, so the exact-match guard matched nothing and
re-scaled a data-born dialog (`in-city dialog 0xAA921F4F scaled (540x322) ->
1080x644`). Cure: **three candidate bases per id, every family member carrying
all of them**, so the mapping stops mattering — verified safe by arithmetic
(products never collide with any 1x base at 1.5x/2x/3x). Corollary worth
keeping: an exact-match guard fails LOUDLY on bad data where a threshold would
have accidentally succeeded; that argues for completing the data, not for
loosening the guard.

**27. WHEN SCALING ONE ELEMENT DELETES A DIFFERENT ONE, THEY SHARE A WIDTH
BUDGET — AND REVERTING THE VANISHED ELEMENT'S OWN ART PROVES NOTHING.**
(2026-07-31, task #88, the News row dismiss X. ✅ user-confirmed at v2.40.2.
Coda worth keeping: once the shared total is correct, scaling the *other*
member is free — both forms declare the SAME total, so it only redistributes
width. My first build held the X at stock on an encoding argument that was
true but too conservative; the user had to ask twice. When you decline to scale
something for a stated reason, re-check that reason after the mechanism is
fully understood.) Every advice row is a
three-column HTML table whose total is the hard constant `GetW() - 61`
(`83 EE 3D` @`0x0079388F`, 61 = 18 + 18 + a flat 25 reserve). 2x arrow art
grows the arrow column by 18, eats the reserve, and carries the LAST column
past the pane's content edge. So the X disappeared because of the *arrow*.
Reverting the four X glyphs to 1x changed nothing — and that null was read for
a day as "the X's size is not the cause, so we're out of levers", when it was
actually the **diagnostic that named the arrow**. Cure = re-derive the shared
constant from the art (`round(18f) + 43`), restoring the confirmed-good
declared total rather than budgeting the overflow. Two habits this earns:
**(a)** when art makes a NEIGHBOUR vanish, look for the constant that sums the
parts, not for a property of the thing that vanished; **(b)** justify the new
constant as *restoring a known-good total* — that survives the parts of the
chain you have not measured, where "budget the overflow" does not.
Generation 8 in `MECHANISM-GENERATIONS.md`, and the first where the DATA half
is unsafe alone: art without the patch removes a working control, so the two
ship and revert together and the ini switch is NOT a safe revert.

**28. THE BOUNDARY IS THE CONTENT WIDTH, NOT `GetW()` — IT MOVES PER TIER, AND
IT MOVES WHEN A SCROLLBAR APPEARS.** (2026-07-31, verified by disassembling
`sub_9BCBC5` @`0x009BCBC5`, then confirmed by eyes-on the same evening.) A
text pane's usable width is `GetW() - 2*gutter - scrollbarW`, gutter default
**5**, and **`scrollbarW` is fetched LIVE** from the scrollbar's own `GetW()`
(vt+`0x0C` then vt+`0xA4`). Three consequences:
- arithmetic that asks "does my content fit" against the raw window width is
  measuring the wrong edge — #88's row is invisible while `paneW` arithmetic
  says it is still 7px inside;
- **a "fixed" reserve usually decomposes.** #88's stock 25 is
  `2*gutter (10) + stock scrollbar cell (16)`, and only the scrollbar half
  scales — our a6 bar really is 32px at 2x because `SetImage` sizes it as
  art width / 12. Shipping a flat 25 was half the answer. **Test: does your
  general form reduce to the game's own constant at f=1?** If it does, the
  split is right; that check is free and it is what proves the decomposition.
- **a scrollbar that APPEARS changes the boundary mid-session.** A collapsed
  list has no bar and passes with a wrong reserve; expand a row and the bar
  arrives and the last column goes over. So **any width budget on a scrollable
  surface must be eyes-on tested in BOTH states**, and unless you are willing
  to detour shared code, budget for the worst case unconditionally — no single
  flat value is correct in both.

This was already written in `SC4-UI-ENGINE.md` §5.0 the day before and two
independent refuters still called the quantity an unmeasured null — the
standing order (check our previous work) applies to *agent* conclusions too.

**20. A FAMILY THAT STILL MISBEHAVES THOUGH "WE FIXED THAT" IS ON AN OLDER
MECHANISM GENERATION.** (2026-07-31, Create Disaster.) Our scaling mechanisms
have gone through **seven** generations (scale-when-visible → pre-scale-hidden →
data pre-scale → builder constant patch → born-at-Place → born chrome state →
data-born + dependency gate), and a family fixed under an early one is NOT
revisited when a better one lands. Disaster was the FIRST flyout we ever scaled
and sat on generation 1 for 28 versions while every sibling was upgraded twice;
its doc still said "UNSOLVED". So: **before designing anything, look up the
family's generation** — `tools\research\MECHANISM-GENERATIONS.md` lists the
generations, which families are still behind, and the one cheap measurement that
confirms each. Corollary, and the reason this law is expensive: **the older the
note, the more confidently wrong it is.** That audit found five stale claims
still being quoted as fact, including one about a *different window* being used
to justify a gate on this one.

**29. IN A UNION-RECT CONTAINER YOU CANNOT DATA-PRE-SCALE *SOME* CHILDREN — ALL
OR NONE.** (2026-08-01, HUD dock, task #89.) A container whose rect is the
**union of its children with no clamp** grows when any child is pre-doubled past
the design frame, and an edge-anchored parent then drags everything with it: the
dock minimap ended up rendered *outside* the dock. And "all" is not always
available — doubling the dock's whole subtree requires
`kDataScaledSubtreeIds`, which **stops the walk**, and the god/mayor **flyout
docking runs inside that walk**, so every flyout came unstuck. Both doors shut ⇒
that container is **runtime-scaled only**. Before pre-scaling any child, ask what
computes the PARENT's rect.

**30. A LIST CAN GRANT TWO POWERS; CHECK BOTH BEFORE JOINING IT.**
`kDataScaledSubtreeIds` means "do not scale this" **and** "do not walk here"
(`ScalePanelRoot` returns early). The dock only ever needed the first, and
taking the second broke unrelated machinery that lived inside the recursion.
Cousin of law 25 (naming failure): **read the consult SITES, not the name.**

**31. MATCHING THE SOLVED FAMILY IS STEP ONE; STEP TWO IS THE NEW HOST'S OWN
CONSTRAINTS.** The corrupted-minimap symptom correctly matched the advisor-faces
family (#43: load-time damage is cured in DATA, never by a faster sweep) — and
applying that cure broke the dock twice, because the *host* had a union rect and
a docking recursion that the advisor strip does not. `CITY-DOCK-OVERLAP.md`
already documented the union rect; it was read that same session and not applied.
**The family tells you the shape of the cure; the host tells you whether it fits.**

**32. PROBE FIRST — A LOG-ONLY BUILD IS ALMOST FREE AND KILLS THEORIES CHEAPLY.**
Same session, four theories: the two builds that only LOGGED each refuted a
theory and cost nothing; the two that CHANGED BEHAVIOUR each shipped a
regression the user had to find. When a mechanism is not yet established, ship
the instrument, not the fix. Corollary: **a probe that fails is still a
result** — reading garbage through the wrong offset is how we learned
`[win+0x6c]` is the draw context and that our own vtable slot list is off by one.

**33. AN INFERENCE WRITTEN DOWN AS A MEASUREMENT WILL SILENTLY KILL YOUR NEXT
SEVEN CANDIDATES.** (2026-08-01, task #89 — the most expensive mistake of the
day, and it was mine.) I recorded *"the corruption is present BEFORE our sweep"*
in four documents as a measured fact. It never was: its only evidence was a
probe line reading `vis=1 onscreen=1`, produced by an `IsVisible()` walk up the
parent chain — **no rect test, no composition, no pixel**. It proved the
visibility FLAGS were set and nothing more. Worse, the conclusion had been
attached to it by a theory (*2x art in 1x windows*) that we then REFUTED for
that window — **the argument died and the premise it produced stayed in the
file**, where it became the decisive kill in six of seven later candidates.
Three defences: (a) when you write a fact, write the INSTRUMENT beside it and
what that instrument can physically see; (b) when a theory dies, grep for the
premises it introduced and kill them too; (c) if a constraint is doing a lot of
killing, re-derive it before trusting it — cousin of law 21 (a stale frame that
survives a REPAINT is a stale DECISION).

**34. A "SAFE" PROBE HELPER IS ONLY SAFE ON THE TYPE IT WAS WRITTEN FOR.**
Same session: `SafeBufProbe` is SEH-wrapped and had been safe for years on COM
buffers — so I pointed it at `[+0x114]`, which is a plain `{pixel ptr, w, h}`
struct. `QueryInterface` is a VIRTUAL call, so it loaded **the first pixel of
the map raster as a vtable pointer and called through it**. SEH caught the
fault, which is exactly why it survived review and shipped. **`__try` makes a
wild call survivable, not correct** — and every value it returned was garbage
being read as a measurement. Check the TYPE at the offset before reusing a
prober.

**35. WHEN A REPAIR IS IN THE FRAME, CHECK WHAT THE REPAIR *DESTROYS* BEFORE
HUNTING FOR WHAT CORRUPTS.** (2026-08-01, task #89 — six refuted mechanisms,
one day.) The dock minimap showed a wrong image on city open. Every theory
asked *what writes the bad pixels* — the message queue, 2x art in a 1x window,
data pre-scale, a stale private buffer, an uninitialised raster, the vtable.
All six died. The answer was that **nothing wrote bad pixels: our own
surface-recreate ERASED GOOD ONES.** We destroyed the display surface, built a
new one and pre-cleared it to black — so the map vanished until the engine's
own bake landed, and the user read the empty box as corruption. The cure was to
carry the old picture across the recreate (capture → recreate → black floor →
repaint bilinear), *not* to find a corruptor. **If your code touches the thing
that looks broken, put your own repair on the suspect list FIRST — it is the
one candidate that never gets refuted, because nobody thinks to accuse it.**

**36. SAMPLE ON A DIAGONAL, AND REPORT A DISTINCT COUNT.** Same session, and it
nearly buried law 35. A raster probe sampled `p[0]`, `p[n/4]`, `p[n/2]`,
`p[n-1]`; for a 64-wide buffer `n/4` and `n/2` are exact multiples of the
width, so both landed on **column 0** — three of four samples were the border.
Four identical greys came back and I read them as "the buffer is blank", which
is not what they showed. **Any sample stride that shares a factor with the row
pitch degenerates to one column.** Sample a diagonal through the centre, and
have the instrument report *how many distinct values it saw* so the answer does
not depend on a human eyeballing hex.

**37. "SMALLER THAN THE THING THAT WAS BANNED" IS NOT A SAFETY ARGUMENT.**
(2026-08-01, task #89, `EarlyBake=2` — crashed on its first city open.) The
`PostCityInit` ban came from a 456-window full tree walk. I reasoned that one
subtree of ~25 windows was therefore safe, shipped it, and it crashed. The log
proved the *quantitative* reasoning was fine — `ScaleAll done, 431 windows`,
exactly 25 fewer, so idempotence worked perfectly — and that the *categorical*
reasoning was wrong: **two byte writes at that site are safe and 25 geometry
mutations are not.** Writing a flag and re-laying a window are different KINDS
of act, and scaling one down does not make it the other. When a ban's stated
reason is a quantity, ask what the quantity was a proxy FOR before assuming a
smaller dose is safe.

**38. A LIVE ESCAPE HATCH IS NOT A SAFE DEFAULT.** Same build: the crashing
mode shipped as the *compiled default*, with the ini key as its guard. That
protected the one machine whose ini I had edited and would have crashed every
other install. **If the only thing between a user and a crash is a line in a
config they did not write, the default is wrong.** Ship the unproven mode OFF,
and let the ini be how it gets turned ON — never the reverse.

**39. THE BORN-CORRECT LEVER FOR CITY-LOAD PANELS IS THE `SetFlag` DETOUR +
DESIGN-CHILD-COUNT GATE.** (2026-08-01, #89 closed, user-confirmed twice.) The
three families in one line each: the *message queue* never fires during the
load tail; *geometry inside `PostCityInit`* crashes; but the `SetFlag` detour
runs on the game's own stack **and keeps firing after init returns** — so gate
on the subtree reporting its **full design child count** (the direct "fully
built" signal; a consecutive-checks stability test loses ~625ms because
SetFlag is scarce during load) and scale there. Measured +328ms/+109ms vs the
sweep's +968ms. Two corollaries that made it work: (a) if the subtree owns a
one-shot surface, scale and recreate are **one action** — splitting them was
the v2.41.15 heap-overrun crash; (b) route through the sweep's own
`ScalePanelRoot` so `scaleMap` makes the later sweep a no-op instead of a 4x.

**40. EVERY BUILT PACKAGE GETS A DEPLOY LINE AND A HASH PAIR IN THE SAME
CHANGE - EQUAL SIZES PROVE NOTHING.** (2026-08-02, #58 radio rows.)
`ThirdPartyUI` was never added to `Deploy-OnGameClose.ps1`; its deployed
copy froze at the 2026-07-29 epoch while the art classification moved on
(SHARED->EXCLUSIVE), leaving clone refs dangling - five radio rows drew as
bare fillcolor bars. Stale and fresh dats had IDENTICAL byte sizes AND entry
counts (the ref rewrite swaps equal-length hex), so every existing check was
structurally blind. The guard is `Test-DatIntegrity`'s DEPLOYED==BUILT
content-hash section. Corollary from the same A/B: a stock-compare staging
script must disable EVERY layer we own (`zzz-` subfolder included) or the
"stock" capture silently keeps our data live on the exact panel measured.

**41. AN INSTALLED HOOK IS NOT AN EXECUTED HOOK — COUNT CALLS, NOT INSTALLS.**
(2026-08-02, #47 closed, user-confirmed.) Our GZWinBMP draw override reported
`25 instance(s) hooked` on the failing open — TRUE, and it read as "this panel
is covered" — while the engine painted those cells through a path that never
calls the per-window Draw, for 13 seconds on screen. Every earlier theory died
because they all assumed the hook RAN. The instrument that solved it counts
**calls per user-visible event** (a per-open census of COUNTS, which cannot
saturate the way a log-line budget does), so a failing event is guaranteed to
leave a line saying so. Corollaries: (a) invalidate the **LEAF** you hooked,
not just its root — the root's dirty flag does not reach the leaves' draw path
(measured: root-only = "less frequent but still happening"); (b) intermittency
in a draw defect usually means TWO PAINT PATHS, not randomness — find which one
runs when it looks right.

**42. AN OFFLINE GATE IS ONLY AS HONEST AS ITS SCOPE - STATE THE SCOPE.**
(2026-08-02, #95 Phase 2, shipped and reverted the same session.) A python
model of SC4's own `sub_79AD00` matched the REAL machine code **32/32 exact**
at 8 item counts x 4 scale factors, clamps included. It was right - about the
CONTAINER. The emulator does not model the RING blit, and moving the container
slid the ring off its button by exactly the distance moved, which the user saw
instantly. The pass was real and the conclusion was wrong, because nobody
wrote down what the harness DOESN'T cover. Corollaries: (a) before trusting a
gate, name the parts of the system it omits - if the omitted part is coupled
to the part you are changing, the gate cannot clear you; (b) our own source
had already recorded the coupling ("ORIGIN STAYS PUT... scaling it UNDOCKED
the circle", v2.15.0) - grep the thing you are about to move for the word that
describes its partner; (c) a 197px measured error is a real finding even when
the fix built on it is wrong - keep the measurement, revert the behaviour.

**43. A COUPLED PAIR SHIPS TOGETHER OR NOT AT ALL — AND THE SECOND HALF IS
USUALLY ALREADY IN YOUR HANDS.** (2026-08-02, #95, v2.45.0 reverted →
v2.46.0 shipped.) When two quantities are welded by a latch, changing one is
not "progress toward" the fix, it IS the bug: v2.45.0 moved the container to
the game's own clamped position — correct, validated, and it slid the ring
off its button, so it was reverted the same day. The missing half turned out
to be a lever we had recorded live for seven versions (`gSubRingBltY`) and an
offset we already applied at blit time (`gSubRingDY`). Corollaries: (a) before
building the second half, spend one command proving the mechanism — four
`emu_plot --fields` runs converted a HIGH-CONFIDENCE INFERENCE into a
measurement for free, and the honest label "inference, not a byte-read" is
what made that test get run at all; (b) pin the half you are NOT fixing to
its **measured-correct current value** rather than re-deriving it — the
derivation may use a different convention (here the game's own X anchor draws
the ring 13f right of the button centre, ours centres it: both "right", 26px
apart, and swapping conventions mid-fix would have silently desynced the
birth path from the sweep); (c) **whatever moves a sprite must also move its
hit box** — a relocated ring with a stationary back-arrow zone is a
regression no screenshot shows; (d) a gate for the second half must be able
to FAIL on the first half's code, or it is decoration.

**44. A PROBE FOR A FIX MUST ADJUDICATE THE FIX, NOT JUST SIGHT THE TARGET.**
(2026-08-02, #93, v2.48.0 → v2.48.1.) Shipping insurance for something never
observed leaves you unable to tell INERT from BROKEN — so make the probe
print the verdict, not the sighting. UDVAR was written to say
`463x132 means still 1x - insurance did NOT take` / `born/scaled 2x
(insured)`, and on its FIRST outing it reported the failure: the data half
had doubled the child while the root stayed 1x, because the city sweep skips
`vis=0` windows and only `kAlwaysScaleCityIds` grants the visibility
exception. A sighting-only probe would have printed "found it!" and left a
2x-child-in-a-1x-root state shipping indefinitely, looking fixed.
Corollaries: (a) the same line should carry the facts that decide the NEXT
move — parent id, sibling-vs-child, visibility — so one appearance closes the
question instead of scheduling another session; (b) when a task's premise is
a question ("identify which vehicle spawns it"), let the probe test the
PREMISE too: the answer here was "no vehicle — it is resident and hidden",
which no amount of vehicle-cycling would ever have produced; (c) put the
probe in BEFORE the fix is confirmed, not after — its value is highest
exactly when you believe you are done.

**45. IF THE GENERATOR'S OUTPUT IS NOT THE SHIPPABLE FILE, THE GENERATOR'S
OUTPUT WILL EVENTUALLY SHIP.** (2026-08-02, #57 phase 4.) Two font styles were
hand-added to `FontStyle.candidate.ini` AFTER generation, so
`make_fontstyle.py <factor> <out.ini>` — the exact command `PACKAGES.md`
documents — produced a file missing them, and the DLL's popup retarget then
pointed at styles that did not exist at 1.5x/3x. It "degrades softly", i.e.
fails invisibly, and shipped that way for five weeks. Anyone following the
docs produced the broken file. Corollaries: (a) make the generator emit the
hand-added part and FATAL if its own output lacks it; (b) upgrade the
self-check from "the values I compute are right" to **byte-identical to the
known-good artifact** — the old size-only check passed happily while two whole
styles were absent; (c) the asset family with no deploy automation and no
content assertion is the one that has already rotted — fonts were the last
such family here and had drifted, exactly as the dats had in #58; (d) a
generator that writes to whatever path you name will happily fill a *source*
directory with intermediates that someone later deploys — regenerate every
copy, or the stale one is a loaded gun. Related: law 40 (hash pairs, equal
sizes prove nothing), law 44 (a probe must adjudicate).

**46. PROVE THE REPAINT BEFORE YOU TUNE THE VALUE.** (2026-08-02, #57, three
shipped-and-reverted builds in one session.) On a CODE-PAINTED control that
renders into its own cached buffer, every field-level fix looks identical to
no fix at all — so tuning values first burns a build per hypothesis and
teaches nothing. All three attempts on the Graphs chart "worked" by their own
logs: the sentinel re-arm re-laid the rect, the font change applied, the
direct rect write STUCK and was still there three ticks later — and the
screen never moved once. Corollaries: (a) FIRST establish that the thing
re-renders when you poke it (change something guaranteed visible — a fill
colour, an obviously wrong rect — and confirm pixels move); only then hunt
the right value; (b) `InvalidateSelfAndParents` is NOT proof of a repaint for
this class — the established lever is the buffer force-recreate
(`SlotThunk<88>` + `gForceRecreate`), the same one the sub-flyout and the
gauge dials needed; (c) "the field holds the value I wrote" is a WRITE
confirmation, never a RENDER confirmation — our probe proved persistence and
we still had nothing; (d) when N different levers all produce zero visual
change, stop trying levers — the common factor is downstream of all of them.
Related: law 41 (installed ≠ executed), law 44 (a probe must adjudicate).

**47. A CONTROL THAT DRAWS RIGHT BUT DOES NOT RESPOND: CHECK WHETHER OUR OWN
GEOMETRY PUSHED IT OUTSIDE AN *ANCESTOR'S* RECT.** #103 established that sprite
and hit box are the SAME rect on this engine (`SetW/SetH/SetSize/GZWinMoveTo`
all funnel into `SetArea` → `CalcAbsoluteArea` → `[this+0x14]`), and concluded
from that that "drawn right, click dead" could not be geometric. **Wrong, and it
cost a NOT-A-BUG closure on a real defect.** The rects agree, but the router's
hit walk descends only into children whose rect CONTAINS THE POINT — so a child
that is perfectly self-consistent is still unreachable if any ancestor no longer
covers it. The engine does not clip the draw, so it keeps painting in the old
place and looks fine.
#110: our POPBOX pin gave the empty-ledger popup the ORDINANCE twin's stock
height (125 vs its own 100). Its host IS the box — a top-level 600x127 window,
127 only because CodePatches hits the `push imm8` ceiling — so the pin's own y
clamp resolved to `127 − 250 = −123` and put the close-X at host-local y=−101,
above the host. Logged **19 times** as `POPBOX 600x127 -> 600x250 at y=-123` and
read past every time, because nothing said a negative y was pathological.
Corollaries:
(a) **When you resize a window, ask what its PARENT is.** If the host is itself
    a box sized by the same patched constants, growing the child alone is
    guaranteed to displace it. Move the whole set or none (law 43).
(b) **A clamp that can go negative is a bug detector you already own** — assert
    it, or it just silently relocates things.
(c) **A twin pair must each reduce to ITS OWN stock value at f=1.** Sharing one
    constant across two builders is how a correct fix becomes a wrong one.
(d) **The stock control settles it in two minutes and needs no build.**
    `Set-StockCompare -Mode Stock` then click the thing. If it works in stock,
    it is ours — no amount of disassembly outranks that.

**48. A GATE CAN BE RIGHT ABOUT ITS BYTES AND WRONG ABOUT THE QUESTION.**
`gate_103_closepath.py` decoded the budget dialog's command dispatch correctly
and PASSED a real positive control — then was quoted for "the X cannot close the
box", which it never tested. Nobody ever established that a CLICK on that X
arrives at `sub_78B120` as command `0xCC`; it does not. The positive control
only proved the CLASSIFIER could recognise a close idiom, not that the handler
is the path a mouse click takes. Distinct from law 42 (scope of an offline
model) and from "null is not evidence": here the instrument found something
REAL, on a path nobody had shown was the relevant one. **Before quoting any
gate, state the step that connects its subject to the observed symptom — and if
that step is untested, the verdict is UNDETERMINED, not proven.**


**49. WASTEFUL-LOOKING CODE IS LOAD-BEARING UNTIL THE COMMENT SAYS OTHERWISE —
AND THE OPTIMISATION YOU WANT IS USUALLY ALREADY MEASURED.**
Five loops in `UiSpike.cpp` re-enumerated a whole child list once PER CHILD, on a
16 ms tick. The obvious fix — hoist the enumeration out of the loop — is WRONG,
and the site's own comment says why: the list is re-read because OUR OWN WRITES
can make the game destroy a later sibling, so a pre-loop snapshot is stale by
construction and the crash returns under rapid menu switching.
(a) **The sound gate was conditional, not removal**: re-verify only when the
    PREVIOUS iteration actually mutated something. Nothing else runs in the
    stack frame (single UI thread, our code never pumps).
(b) **Prefer an EXISTING counter over a new flag.** The plan called for a fresh
    `mutatedSincePrevVerify` set at every mutation site, with the warning that
    "a missed one reintroduces the crash silently". Auditing first showed
    `count` already was that flag — every `SetW/SetH/GZWinMoveTo` is paired with
    a `count++`, and it *has* to be, because `count` is the same number the
    `"%d windows scaled"` log lines are read from. A new flag can silently miss
    a site; this one cannot without breaking an instrument we have relied on for
    dozens of fixes. **When you need "did anything change?", look for a number
    the code already maintains and that something else already checks.**
(c) **Grep direction is a real trap**: searching for `count++` AFTER each
    mutation found nothing at the third cluster and nearly produced "this path
    does not count" — the increment sits BEFORE the writes.
(d) Write the refutation at the site. A ⛔ DO-NOT-HOIST note now guards it.

**50. A DOCUMENTED SETTING THAT DOES NOTHING IS A LIE, AND IT NEEDS A GATE.**
Three keys in the 24 KB user ini (`Scaling/AutoConfig`, `PresentWidth`,
`PresentHeight`) were parsed into `Settings` and then read by nothing at all. A
player could set them, see no change, and have no way to distinguish "wrong
value" from "dead key" — the ini is an INSTRUMENT and it was lying.
(a) The shipped ini documents ONLY keys the code reads; everything else falls
    back to code defaults, and absent IS the supported configuration.
(b) `_tests\Test-ShippingIniKeys.py` enforces it, checks for a BOM, and asserts
    a POSITIVE CONTROL — it caught its own false failure on `ScaleFactor`
    (read through a `GetPrivateProfileFloat` helper with no trailing `W`).
    **The first version of a consistency gate is usually wrong about the code,
    not about the data — make it prove it can fail before you trust a pass.**
(c) Same family as the silent truncation caps (task #53) and law 42: every one
    of these is an instrument that reports success while never having looked.


**49-ADDENDUM (2026-08-04, the hardest-won line in this file): THE COUNTER WAS
RIGHT AND THE RE-BASELINE WAS THE BUG — AND MY OWN "ZERO MUTATIONS" SCAN HAD NO
POSITIVE CONTROL.** Law 49's fix shipped with a use-after-free that only a
57-agent adversarial review caught (the independent refuter tried to kill the
finding and instead produced the minimal fix).
(a) **A verify proves liveness of ONE pointer, never of the remainder.** The
    v2.69.0 gate re-baselined its mutation signal whenever a verify ran,
    crediting every LATER index with a check that looked up only the current
    one. Kill sequence: i=0 mutates and the game tears down c1 AND c2; i=1
    verifies (c1 dead, continue), signal consumed; i=2 skips its verify and
    dereferences freed c2. Fix = delete the five mid-loop re-baselines: the
    baseline is taken once, before the loop. The skip window is only the
    provably-safe prefix before the FIRST mutation — and the steady state
    still costs zero enumerations, which is where the whole O(n^2) win lived.
    **When optimising a safety check, the only sound skip is the one you can
    prove from a state the checked object was KNOWN GOOD in.**
(b) **My "verified zero mutations inside the block" was a null with no
    positive control** — the scan's regex matched Set*/GZWinMoveTo CALLS, and
    the block's real mutations were raw VTABLE SWAPS (`*(void***)w = gVtCopy`),
    a flag write, and Invalidate*(). It gated the disaster draw-hook re-find
    off and the regression was REACHED on the dev machine (ini has Probe
    Enabled=0). A mutation scan must enumerate mutation MECHANISMS (calls,
    vtable stores, flag writes, invalidations), and must first prove it can
    see each one. Same law as NULL IS NOT EVIDENCE, applied to my own tool.
(c) **Adversarial review of your own fresh changes is not optional at this
    project's stakes**: 46 findings raised against v2.69.0, 38 refuted, 8
    real — including one crash and one reached-on-this-machine behavior
    regression, both mine, both same-day. The refuters killed 83%% of the
    noise AND sharpened the real ones.


**51. WHEN THE GAME REFUSES TO DO SOMETHING, FIND THE ONE INSTRUCTION THAT
REFUSES — DO NOT PAINT OVER IT.** (#121, 2026-08-04.) The Data Views map drew
data cells on black at 2x on small tiles. FIVE pixel-level cures were built and
all failed: one-shot seed (wiped by the game's ~1 Hz re-clear), a 30-sweep heal
(its black test compared against numeric 0; the game's black is `0xFF000000`, so
it had NEVER fired), a per-sweep cached heal (produced WRONG CELL COLOURS), and
a size clamp (correct, but the user rejected the smaller map).
(a) **The killer fact was COMPOSITING ORDER**: the game clears, bakes, then
    ALPHA-BLENDS cells onto whatever base exists. With a black base the cells are
    BORN dark — no later repair can un-blend them. *When your fix has to run
    after the thing it fixes, ask whether the damage is already baked in.*
(b) **The real cause was ONE unsigned compare.** `0x7A8560 lea ecx,[edx+2];
    cmp ecx,4; ja skip; jmp [ecx*4+0x7A8628]` — a 5-entry blitter table indexed
    `zoom+2`, so `zoom=-3` wrapped to 0xFFFFFFFF and skipped the tile. The dest
    math either side was FULLY GENERAL. 15 bytes re-pointed at a 6-entry table
    (entry 0 ours, 1..5 the game's own stubs) fixed it completely.
(c) **The disassembly should have been step 1, not step 10.** ~13 builds were
    spent guessing against the user's eyes; the disasm answered it in one pass.
    This is law "measure, don't infer" with a bigger price tag. **If two
    successive fixes in the same area fail, STOP shipping and go read the code
    that is refusing you.**
(d) A recompute that marks dirty is NOT a paint. The paint was message-driven
    and landed after the panel was visible; calling the game's own bake
    synchronously while hidden removed the last jump.

**52. A FALLBACK YOU DID NOT RETIRE IS A BUG WITH A POLITE NAME.**
After the real fix landed, the map still jumped on open — because the OLD
dock-seed workaround still fired and overwrote the correctly-baked terrain with
a blurry upscale. Good map → worse map → re-bake. The header comment already
said the seed and heal "are FALLBACKS that must stand down when this is true";
**the condition had never been wired.** A comment describing code that does not
exist is the same defect as a lying log line (law 48 family).
(a) **When a real fix supersedes a workaround, gate the workaround OFF in the
    same commit** and prove it with a log census — the acceptance evidence here
    was `SEEDED 0 / probes 0 / HEALED 0 / CLAMPED 0 / faults 0` alongside
    `x8bake=live blits=16 clips=0`.
(b) Keep the workaround as an explicitly gated fallback for when the real fix
    DECLINES (wrong exe build, another mod owns the site) — but the gate must be
    a live expression, never a sentence in a comment.
(c) **The stock control decided this session TWICE**, both times against my own
    stated expectation: the black map was ours, and the open-jump was ours after
    I suggested it was probably stock. Two minutes, no build, each time.

**53. EXTRAPOLATE A TUNED CORRECTION THE WAY THE THING IT CORRECTS IS PLACED.**
The disaster ring's RingDX/RingDY are a correction over the game's 1x ring-blit
anchor, hand-tuned at f=2. v2.71.6 carried them to other tiers by scaling by
**(f-1)** — a law that asserts *the correction is zero at f=1*. It is not: the
1x anchor is the **UNDOCKED** seat, and the ring only sits on the button after
the **dock** runs, which is itself a scaled placement (every term ∝ f). So the
docked seat scales linearly and the (f-1) law drifted — at 3x it parked the ring
8px right and 7px low ("not 1:1 docked"). Cure = **SEAT-SCALING**: keep the
sprite's CENTRE at its f=2 docked seat scaled by f/2, subtract the scaled
half-size. Bit-identical at f=2, so the tuned tier cannot regress.
(a) Before choosing (f-1) vs f, ask **what state the f=1 value describes**. An
    (f-1) law is only sound when f=1 is the SAME state you tuned in.
(b) 2x is a blind spot for tier math: both laws agree there. **A tier
    extrapolation is unproven until a THIRD tier has seen it** — and fixing one
    tier silently moves the others (this one nudged 1.5x by +5/+4, still
    unverified).
(c) A tier fix ships with its own re-verify obligation named, per tier.

**54. A FIX THAT PRODUCES NO LOG LINE DID NOT RUN. STOP RE-DERIVING THE VALUE.**
#127 cost TWO builds proving the same arithmetic twice. Attempt 1 sat inside the
anchor block (the child is anchored BEFORE its anchor sibling, and only once, so
the guard was always false); attempt 2 sat in the load-time sweep (the panel only
exists once the USER OPENS it). Both times the user said "it did not move at all"
and the log had ZERO instances of the fix's own log line. That absence WAS the
diagnosis, and it was read as noise twice.
(a) When a fix has no visible effect, the FIRST question is **"did my code
    run?"**, never "is my value right?". Put a named log line on the write path.
(b) Absence of that line is a MEASUREMENT, not a null - it needs no control,
    because the line is emitted unconditionally on the path being tested.
(c) Ask WHICH PASS and WHICH ORDER before writing a placement fix: load-time
    sweep, per-tick incremental, or the show hook. A user-openable panel does
    not exist during the load sweep.

**55. DOCK RELATIONSHIPS BELONG IN A TABLE (user standing direction).**
"ALL OF THE UI ELEMENTS SHOULD BE DOCKED VIA MAP." A panel positioned RELATIVE
TO ANOTHER gets a row - `{child, anchor, offX, offY}` - never bespoke code. Our
per-panel anchor places each root from its OWN design gaps: right for a
screen-edge dock, WRONG for a sibling pair, because the game's native seat
between the two differs by resolution and per-panel scaling MULTIPLIES that
drift by f (measured: 1px apart at 2400x1600, 7px at 3840x2160 -> 21px at 3x).
(a) THE OFFSET LAW: measure the offset in the ANCHOR's scaled px at the
    user-confirmed f=2 tier and apply it as `offset * (f/2)` - identity at 2x by
    construction, so no tier needs a special case (law 53's shape).
(b) The table pays for itself immediately: making docking BORN-CORRECT took one
    predicate and every present and future row inherited it.

**56. PREFER A FIX THAT SELF-GATES ON THE DEFECT OVER ONE THAT GATES ON A TIER.**
The rating-arrow detour compares the LIVE position against the game's cached
seat and writes only when they differ, and it computes no coordinates of its own
(it writes the game's own cached value back). That is what made extending it
from 3x to 2x safe as an ARGUMENT rather than an assurance: a correctly-seated
arrow has live == cached, so there is nothing to write.
A tier gate protects the confirmed tier by NEVER RUNNING; a defect gate protects
it by having NOTHING TO DO. Only the second generalises.
(c) When a tier gate widens, its justifying COMMENT goes stale in the same edit
    - ours still said "THE f=2.00 PROOF". That is law 48 (your own comment is an
    instrument) and it must be fixed in the same commit.

**57 — A FIX THAT MUST RE-APPLY EVERY TICK IS A FIGHT, NOT A FIX.** If the
object you are changing is OWNED by a rebuild, change it INSIDE that rebuild.
#131 v2.80.0 resized region tile buffers from our own tick: it worked (9/9) and
the game restored them every frame — counter 9/18/27/36 unbounded, nothing
changed on screen, and CLICKING BROKE because a sibling buffer built during the
rebuild went stale. Hooking the builder (`sub_7AE3D0`) fixed all of it at once,
because every downstream step then inherits the new size. **Acceptance: the
counter must STOP CLIMBING. Verify that in the log BEFORE the user ever sees
the build.**

**58 — WHEN A SUBSYSTEM RESISTS TWO ATTEMPTS, DECOMPILE THE MODULE.** #131 cost
FIVE builds guessing one address at a time from prior reports; the whole region
screen was 197 functions / 52KB and one fan-out decompiled all of it. The fix
landed on the NEXT build. Three of our own claims were wrong and only the bytes
caught them: the vtable slot (right all along), the argument count (four dwords
+ `ret 0x10`, we passed three plus a pointer), and which buffer set the
on-screen rect. Cheaper to read the module once than to infer it seven times.

**59 — EVERY CONSUMER OF A SHARED HOOK NEEDS ITS OWN GATE, AND AN ANCHOR'S
LIFETIME IS PART OF THE DOCK.** (#137, 2026-08-05, three defects stacked in one
panel; user-confirmed at 2x and 3x.)
(a) **The eye-measured offset.** `kPanelDock` anchored the Graphs radio band to
    the CHART'S TOP by a delta read off a 2x screenshot (`+640`). The `.UI`
    design is BOTTOM-referenced. Proven by diffing the two scripts that SHARE
    band id `0x0A4A8176` — Graphs `I-6bc9065a` vs Data Views `I-ea2871aa`, the
    panel the user named as correct. **A wrong relationship scaled faithfully is
    wrong at every tier**, which is exactly why it reproduced identically at 2x
    and 3x and why no tier math ever found it. When two panels share a widget
    id and one renders right, DIFF THE DESIGNS — that is a free controlled
    experiment.
(b) **AN ANCHOR'S LIFETIME IS PART OF THE DOCK.** The next build anchored to
    `0x8A8B5B72`: right arithmetic, wrong window. Measured from the log, it
    opens ~19s AFTER its child, and `ApplyPanelDocks` bails on
    `!pAnchor->IsVisible()` — so it could not dock until the user clicked.
    Check WHEN an anchor appears relative to its child, not only where it is.
(c) **THE REAL ONE — law 41 again, and it hid two correct fixes.** #127's
    born-correct "dock at show" lived inside `ScaleOnShow`, which only runs at
    `gShowHookMode >= 2`. The shipped ini has `ShowHook=0`; the log says
    `SHOWHOOK installed ... (mode 0: log only)`. **The dock-at-show had never
    executed once since #127** — the tick always cleaned up after the first
    paint, which is the one-frame jump. Two CORRECT fixes shipped before anyone
    checked whether the path ran. ⚠ That same function already carried this
    warning for EARLYDOCK at v2.41.17 ("the trampoline now serves TWO
    consumers … would silently never run if this still keyed off it alone").
    Dock-at-show was the THIRD consumer, still keyed off the wrong flag.
    **Before improving behaviour behind a hook, prove its branch executes: read
    the mode from the LIVE ini and the "installed … (mode N)" line from the
    log, never the default in `Settings.h`.**
(d) A show detour fires on the 0→1 transition, so `IsVisible()` is still FALSE
    for the very window being shown. A dock called from there must gate on
    **geometry** (`w/h > 0`), not on the visible flag — otherwise the guard
    rejects precisely the case it exists to serve. (Same family as
    [[feedback-sc4-prescale-while-hidden]].)
(e) Do NOT revive a refuted mechanism to reach your code: `ShowHook=2` would
    have run the dock, and scale-at-show is recorded as refuted for the city
    HUD. Give the new consumer its own gate instead.

---

**60. THE 1.5x TIER SIGNATURE IS THE NULL HYPOTHESIS, NOT EVIDENCE.**
(2026-08-06, #148, ten failed theories.) "Broken at 1.5x, perfect at 2x and 3x"
feels like a fingerprint. It is not: `Upscale2x.cs::ScaleDim` returns early at
an integer factor and `ScaleRound` is exact there, so **EVERY** arithmetic
disagreement between two scalers is 1.5x-only *by construction*. Four separate
theories matched that pattern perfectly and all four were wrong. A candidate
earns nothing for matching the tier pattern; it must also survive a test that
could have refuted it.

**61. GZWinBtn STRETCHES — a state cell need NOT match its window.**
(2026-08-06, measured by `tools\uimap\emu\gate_btn_cell_vs_window.py`.) Across
all 281 scripts, buttons whose cell width differs from the edge-derived window
width: **1.5x 709, 2x 420, 3x 420** — and the integer tiers are user-confirmed
perfect, with extremes like a 24x6 sheet (cell 12) in a 996-wide window. So a
cell/window mismatch is normal engine behaviour and may **never** be used to
justify changing `ScaleDim` or `ScaleSubtree`. Corollary: `ScaleDim`'s
tie-break direction is near-irrelevant (ties-down 701 vs ties-up 709 of 868).

**62. BUILD THE INSTRUMENT THAT CAN *SEE* THE DEFECT CLASS, NOT ANOTHER ONE
THAT CAN ONLY COUNT.** (2026-08-06; second time — `MMGRID` for #146, now
`tools\uimap\emu\render_flyout.py` for the flyouts.) Every gate in `emu\` was
arithmetic — its own README says *"IT NEVER LOOKS AT A PIXEL"* — so ten
theories were checked against numbers instead of against an image. The
compositor (imagerect crop · `sheetW/states` cell · magenta punched to alpha ·
1:1 blit · green window boxes · any tier · either geometry rule) then killed two
theories in three minutes each, offline, with no build and no launch. When a
defect is about what something LOOKS like, render it.

**63. A REPAIR AIMED AT A SYMPTOM YOU CANNOT SEE WILL BREAK SOMETHING YOU CAN.**
(2026-08-06, #148 dead end 3.) The `imagerect` under-read was REAL arithmetic —
427 rects short at 1.5x, 0 at 2x/3x — and closing it damaged the thumbnail
flyouts TWICE (a tolerance widened small-atlas cells across two cells; the exact
1x test then widened the last cell of every strip, which legitimately ends at
the sheet edge). Meanwhile the reported defect never moved, because those
buttons carry no `imagerect` at all. **Before repairing a discrepancy, prove the
thing you are trying to fix actually READS the value you are changing.**

**64. GO FIND THE INSTANCE THAT HAS A SIBLING THAT WORKS.** (2026-08-06, #148 —
this one law replaced ten failed theories.) "The sun and the moon are wrong" is
consistent with a hundred mechanisms, so ten of them survived a day of testing.
"**ONE of these FIVE identical buttons is wrong**" is consistent with almost
none — and it named the cause in minutes: the five Landscape buttons are
identical 47x37 controls on identical 188x37 sheets, and the broken one is the
only one at an ODD left edge (69 vs 68). `ScaleSubtree` is edge-derived
(`newW = ScaleRound(l+w,f) - ScaleRound(l,f)`, deliberate, so abutting siblings
stay abutting), so at f=1.5 an odd `l` costs the window exactly one pixel while
the art cell keeps all 71. **When a defect resists, stop instrumenting the
broken instance and go hunting for a working sibling.** The pair is the
experiment; the broken one alone is only an anecdote.

Two more facts from the same defect, both worth keeping:
(a) **`ScaleDim`'s `CellUnit` is a GUESS** — it takes the LCM of every count in
    {2,3,4,6,8,12,16,24} that divides the width, so a 136px FOUR-state sheet
    gets snapped on 8 and lands at 208 (cell 52) when its button wants 51. And
    it snaps HEIGHTS, which a horizontal strip never needs. The upscaler runs
    over a directory and cannot know the consumer; **the builder parses the .UI
    and must not guess** — `sheetW = states * ScaleRound(w*f)`,
    `sheetH = ScaleRound(h*f)`.
(b) **Regenerate from the 1x source, never resample the upscaled sheet.**
    Double resampling compounds the error and smears the magenta colour key —
    the same failure that shipped a pink Mayor Rating bar.

**65. A FIX THAT *MOVES* THINGS IS JUDGED BY ITS DENSEST NEIGHBOURHOOD, NOT BY
THE CASE THAT REPORTED THE BUG.** (2026-08-06, #148, shipped and reverted the
same day.) Moving 177 buttons onto an even edge fixed the reverse L and was
**up to 2px at 1.5x**. On the Landscape flyout — five buttons, 50px of air
between them — invisible. In `aa1f1f57` ("Select A My Sim", 24 and 28 nudges,
the most of any script) twenty-one faces visibly slid inside their own frame;
the advisors went "left and high"; the budget rows and the bottom dock
misaligned. **Before shipping a positional change, find the tightest layout it
touches and judge it there.**

**66. EDITING GEOMETRY IN A `.UI` HAS THE SCOPE OF THAT `.UI`. EDITING *ART* HAS
THE SCOPE OF THE WHOLE GAME.** (2026-08-06, #148, the second same-day revert.)
Regenerating 61 state-strip sheets at exactly `states * window` was
arithmetically right, took the offline mismatch count to 0, reported **0
conflicts**, and broke the flyout thumbnails on hover — because **THE FLYOUT
STRIP ITEMS ARE CREATED AT RUNTIME AND APPEAR IN NO `.UI`** (item-create does
`SetArea(0,0,GetW(),GetH())`), yet they bind art **by TGI** like anything else.
The conflict check could only enumerate `.UI` consumers, so it was blind by
construction. A `.UI` edit cannot reach a window that is not in a `.UI`; an art
edit reaches every consumer that exists. **Do not change art dimensions until
you have an instrument that can enumerate the RUNTIME consumers of a TGI.**
(Also refuted in the same pass: "a stale `imagerect` elsewhere describes the old
size" — of 115 art-sized strips in scope, ZERO carry an imagerect.)

**67. WHEN THE SIZE IS WRONG, CHANGE THE SIZE — NOT THE POSITION, NOT THE ART.**
(2026-08-06, #148, the lever that finally worked.) `ScaleSubtree` is
edge-derived (`newW = ScaleRound(l+w,f) - ScaleRound(l,f)`) so abutting siblings
stay abutting — which makes the scaled SIZE depend on the POSITION, and at
f=1.5 an odd `l` costs exactly one pixel. The cure is to take **leaf** windows
(`GetChildCount() == 0`) SIZE-derived, `ScaleRound(w,f)`: nothing moves, the
size changes by at most 1px, and the art cell finally matches. **Leaves only** —
a window with children is a panel whose edges are load-bearing (that is what
edge-derived is protecting, and #143's white seams are the failure mode); a leaf
is a discrete icon with nothing butted against it. No-op at an integer factor by
construction, so 2x/3x need no re-proof.

**68. READ THE FORMAT OFF THE SHIPPED BYTES BEFORE WRITING A RECORD.**
(2026-08-06, #147.) The LTEXT header was written as a hardcoded `0x0008` and was
correct only by luck — the field is the CHARACTER COUNT
(`size = 4 + 2*count`; `0F..`=15 for "Total Garbage\r\n", `0A..`=10 for
"Exported\r\n", `08..`=8 for "Imported"). Dumping three real records also
settled a judgement call for free: `Imported` is the row DIRECTLY ABOVE ours in
the same legend and carries NO trailing CRLF, so omitting it matches our row's
own siblings instead of being a preference. **The neighbouring record is both
the format spec and the style guide.**

**69. "THIS WASN'T LIKE THIS BEFORE" IS A BISECTION BOUNDARY, NOT AN OPINION.**
(2026-08-06, #149.) Four defects — the My Sim face grid, the advisor portraits,
the Monthly Budget rows, the flyout thumbnails — were reported minutes after a
deploy, so both of that deploy's changes were reverted. **The reverts fixed
nothing**, because the cause was a change from EIGHT HOURS EARLIER. The user
then said *"these issues weren't there when we first started on 1.5x"* and that
sentence was the better instrument: it named a bisection boundary that the
timing coincidence had hidden. **Coincidence in time is not causation. When a
revert does not move the symptom, the attribution was wrong — stop reverting and
go bisect.**

**70. A "SAFE" OVER-APPROXIMATION IS STILL A CHANGE, AND IT IS PAID FOR IN
PIXELS.** (2026-08-06, #149 — the actual cause above.) `Upscale2x.cs::CellUnit`
snapped scaled dimensions to preserve the game's integer cell divides (#143,
correct). It was then widened to **the LCM of every count in
{2,3,4,6,8,12,16,24} that divides the width**, reasoning that a bigger common
multiple makes *any* divide safe. It does — and it makes every sheet whose width
merely happens to divide by a large number BIGGER THAN ITS CONSUMER'S WINDOW. A
200px FOUR-state sheet got `LCM(2,4,8)=8`, so 300 — already a clean multiple of
4 — was pushed to 304 and every cell came out a pixel too wide.

MEASURED over 255 art-sized 4-state buttons (cell != window):
`LCM{2,3,4,6,8,12,16,24}` **152** (shipped, and the worst option except doing
nothing) · `LCM{2,3,4}` 98 · **`LCM{3,4}` 34 (chosen)** · `{4}` 19 (rejected:
drops the NineSlice `/3`) · no snap 104.

`{3,4}` keeps the two divides that are load-bearing (NineSlice `img->Width()/3`
at ~~VA 0x00794100~~ — **VA corrected 2026-08-18: that is `cSC4WinAlertBorder`'s
own draw. For `.UI`-bound sheets the drawer is `GZWinBMP 0x009BC325`'s EDGE
branch (or `GZWinBtn 0x009B05E0`), which divides its own source rect and then
calls the blitter `0x008D8800`. The `/3` arithmetic is unchanged — see
`REGRESSION.md` §"RESOLVED 2026-08-18 — three addresses, three different
JOBS"** — and the four-state `width/4`); `/12` for the scrollbar still
falls out as their LCM. **LCM-of-everything is safe against CUTTING and unsafe
against FITTING — measure the overshoot before choosing a wider constraint.**

**71. A GATE THAT ONLY ASKS ABOUT YOUR OWN WORK CANNOT SEE WORK YOU NEVER
STARTED.** (2026-08-13, #154.) CAM's Village Hall info screen rendered at 1x
under 1.5x fonts for the ENTIRE life of the project, with every offline gate
green, because every gate asked *"is what we built still correct?"* and that
dialog was never built. `build_dialog_static.py`'s winner assert even asks the
adjacent question — *"has a mod taken over one of OUR targets?"* — and has never
asked its mirror, *"is a mod's OWN dialog scaled at all?"* **Run the census in
BOTH directions: enumerate what EXISTS and subtract what is handled.** The
instrument already existed and had been reporting the three unhandled CAM
scripts under a heading called "What to do" since the day it was written — the
#150 shape again, a correct report nobody read. Sibling of law 42.

**72. `blttype=normal` ART IS CLIPPED BY ITS WINDOW, NEVER STRETCHED TO IT — SO
ART AND WINDOW CANNOT BE THE SAME SIZE AT A FRACTIONAL FACTOR, AND MUST NOT BE
MADE SO.** (2026-08-13, #154.) A 285px strip upscales to 429 (CellUnit 3 snaps
427.5 up) while its window is edge-derived to 427 **or** 428 depending on the
parity of its left edge — two windows in the same dialog, one bitmap. The
overhang is structural, not a defect. A first gate asserting "no ink may be
clipped" reported **27 failures on a correct build**, and believing it would
have sent the next change into `Upscale2x` — law 70's mistake, on law 70's
lever. **The question that decides what the screen looks like is whether the
pixels the window cuts are a REPEAT of the last pixels it keeps** — and ask it
at 1x as well, because the mod crops several of its own strips on purpose.
`tools\uimap\emu\gate_tp_bmp_fit.py`, with a negative control that names the
22 of 31 bitmaps too uniform to be able to fail rather than counting them green.

**73. A BLIT HAS THREE NUMBERS — SOURCE, CROP, DESTINATION — AND SCALING ANY TWO
OF THEM IS NOT A PARTIAL FIX, IT IS A NEW DEFECT.** (2026-08-13, #154
correction, USER-REPORTED against the build that was meant to fix it.)
`GZWinBMP blttype=normal` slices `imagerect` out of the bitmap and blits that
slice at the window origin. v2.97.0 scaled the WINDOW (285→428) and the BITMAP
(285→429) and left `imagerect=(0,0,285,30)` alone, so every row stripe painted
285px of a 428px window and **143px of each row was bare panel**. The builder
skipped them because it scales a rect only when `art_plan` says that control's
art was scaled — and `art_plan` is computed from the STOCK store, so art the MOD
supplies (which we upscale via `thirdparty-art\`) is classified "left1x". The
mechanism for exactly this already existed as `RUNTIME_BOUND_2X`: *the ref does
not change but its PIXELS do, so the rect must scale with them.*
Scope it to the owning package — a rect may only scale when the scaled bitmap
ships in the SAME mod-gated dat, or removing that mod leaves a doubled crop over
1x art. Sibling of the coupled-pair law (#143); this names the third member.
**The build printed `rects2x=0` on a file with 24 imagerects and it was read
past** — law 54, again, in one line of my own output.

**74. WHEN A GATE CHECKS A BLIT, MAKE IT READ ALL THREE NUMBERS — AND IF IT
CANNOT, MAKE IT SAY WHICH ONE IT IS NOT READING.** (Same event.)
`gate_tp_bmp_fit.py` PASSED the build that shipped the defect above: it read the
window and it read the bitmap and never the crop between them. Two of three is
not "mostly covered", it is a gate that certifies the exact failure it cannot
see. And the first repair asked the wrong third question — *"does the rect still
cover the same fraction of the BITMAP?"* — which flags the m³ glyph (bitmap
snapped 20→32 by CellUnit, rect and window both 20→30: two transparent pixels
undrawn, nothing wrong). **The question that decides pixels is how much of the
WINDOW gets painted**, compared against 1x. Negative control must be the REAL
artefact: extracting the script back out of the DEPLOYED dat and feeding it to
the fixed gate produced 48 findings in plain language.

**75. WHEN A CURE LANDS IN ONE PATH, NAME EVERY OTHER PATH THAT NEEDS IT — AND
A GATE MAY NEVER EXCUSE A FINDING USING A REPAIR THAT DOES NOT RUN THERE.**
(2026-08-13, #155, USER-REPORTED.) #148's LEAF SIZE-DERIVED rule went into
`UiSpike::ScaleSubtree` (the RUNTIME sweep) in v2.94.1 and never into
`build_dialog_static.py`. Statically-served dialogs are **deliberately excluded
from that sweep** (`kNeverScale` — running both double-scales them), so nothing
downstream repaired them: the region city bubble's play button shipped 82px wide
over an 83px art cell and the leftover column drew as a tear. The same control
was 83 at runtime and 82 in a static dat — **two paths that must agree,
disagreeing silently, and invisibly at 2x/3x where both rules coincide.**
Worse, `gate_btn_undercover.py` — the gate written FOR this exact assertion —
excused the 1.5x residual with *"the parity class is repaired by the leaf
size-derived rule"*: true in `selective-safe\`, which it scanned, false in
`dialog-static\`, which it had never looked at. It now has a static half that
models nothing, reads the shipped `area=` verbatim and FAILS at every tier.
**Before a gate downgrades a finding to a residual, make it assert that the
repair it is relying on actually runs in the path it is looking at.**
Scope the cure by measurement: 47 art leaves moved at 1.5x, integer no-op
asserted in the builder, `DialogStatic` 262 -> 262 entries +0 -0 ~0.

**76. A HEURISTIC THAT IDENTIFIES A STRUCTURE IS SAFE FOR PROTECTING IT AND
UNSAFE FOR REWRITING IT.** (2026-08-14, #156, USER-CONFIRMED fixed.)
`Upscale2x::CellUnit` guesses "this width divides by 3 or 4, so it may be a
state strip". As a guard that only PRESERVES divisibility (#143) a wrong guess
costs nothing. Used to RE-TIME pixels it changed **1186 of 2206** sheets and
displaced an advisor frame's flood-filled aperture by a pixel - the #152 seat
guard caught it and the whole attempt was backed out (0 of 941 entries differed
after). The shipped version derives the list from the `.UI` scripts that BIND
each sheet (`tools\upscale\find_cell_strips.py`): **193** sheets, 77 changed at
1.5x, **0 at 2x and 3x**. **Count what a heuristic fires on before promoting it
from a guard to a transform, and get the real list from whoever actually knows.**

**77. ASSERT THE MEASUREMENT WITH A TOLERANCE, NEVER THE MODEL.** (Same event.)
A guard asserted a flood-filled aperture EQUALS `ScaleRound(offset)`. Per-cell
sampling scales a 55px cell to 83 rather than 82.5, so a source column
legitimately lands one pixel later - the art was right and the equality encoded
the OLD sampler's rounding. A guard that encodes one sampler's arithmetic fires
on every future sampler change whether or not anything is wrong. Bound it
(+/-1px here), keep it fatal beyond, and say in the comment which sampler the
bound assumes.

**78. THE DEFECT SIGNATURE THAT NAMES A CELL-BOUNDARY BUG:** clean at stock,
clean at 2x/3x, wrong at 1.5x ONLY, and the artefact sits hard against the
RIGHT EDGE of a repeated element. That is the next state's art bleeding into
the previous cell because `ScaleDim` snapped the sheet while the sampler still
mapped it globally. Read `int(out/factor)` at the cell boundary and compare it
to `src_cell*count` - the arithmetic answers in one line.

**79. WHEN TWO CANDIDATE CELL COUNTS DISAGREE, THE LCM IS NOT A COMPROMISE — IT
IS A THIRD ANSWER THAT IS WRONG FOR BOTH.** (#157, 2026-08-15.) A 180x180 dialog
frame is a 9-slice; the engine's cell is `img->Width()/3`, so at f=1.5 it wants
270. `CellUnit` returned `LCM{3,4}=12` and snapped to 276 — purely because 180
happens to divide by 4, which is arithmetic, not evidence of four states. The
cell became 92 where the `.UI` geometry was scaled for 90, the corner arc
stopped short of the window corner, and the straight edge ran past it as a
square block. USER-VISIBLE as *"the light blue interior box is overlapping"*.
**This is law 76 applied to SIZING rather than sampling** — #156 fixed the
sampler and left the same guess still resizing sheets. Cure: derive the role
from the `.UI` that BINDS the sheet (`find_nine_slice.py`), and make the derived
list EXCLUSION-BIASED so an unknown runtime consumer can be missed but never
broken. 6 of 30 sheets moved at 1.5x; 2206/2206 byte-identical at 2x/3x.

**80. FIX THE NUMBER THAT IS WRONG, NOT THE NUMBER THAT REPORTS IT.** (Same
event, and it cost a round trip.) The first cure made the `imagerect` follow the
art — correct as a general guard (law 73) and useless here, because the crop was
faithfully reporting an ART SIZE that was itself wrong. Making the report match
the bad input moved the defect without reducing it. Before adjusting a consumer
to match a producer, ask which of the two the DESIGN fixes: the `.UI` geometry
is scaled by `f`, so the art must be too — everything else follows.

**81. A DIFF THAT COMPARES NOTHING REPORTS AGREEMENT.** (Same event.) A 2206-file
before/after comparison printed "CHANGED 0" three times because the two sets used
different filename conventions (`--normalize-names` omitted), so 0 of 4413 names
matched. Only the `only-in-one` counter exposed it. Every set comparison must
print its INTERSECTION SIZE next to its verdict, and a non-zero symmetric
difference is a refusal to answer, not a clean bill of health.

**82. A CLIPPED RUNTIME STRING HAS TWO CONSTANTS: THE SURFACE AND THE ANCHOR.**
(#159, 2026-08-15.) The placement cost figure was rasterised into a 128x32
buffer AND right-aligned at x=124 (=128-4) inside it. Widening the buffer alone
made the box bigger and moved the text NOWHERE - so it still clipped, and the
box visibly slid left. **That shift was the evidence naming the second half:
when a size fix moves something without unclipping it, the remaining fault is an
ALIGNMENT constant measured from the OLD size.** Fix both or ship neither; a
half-fix reads as "no progress" while actually being progress you cannot see.

**83. A GZWinBMP'S WINDOW SIZE IS AN OUTPUT, NOT AN INPUT.** (Same event.)
GZWinBMP is dst-follows-src: the draw computes `dst = areaL,areaT + srcW,srcH`
and NEVER reads the window rect. So a wrong-sized GZWinBMP window is a SYMPTOM
of a wrong-sized source buffer. MEASURED: the game re-sized this window to
128x32 every time it showed it (caught parked off-screen carrying our 256x64,
reset 80ms later), our sweep fought it 4x and `ScaleRecord` tombstoned it as
"game-managed geometry" - correctly, and the fight also FLASHED. **Before
scaling any window, ask whether its size is computed FROM something; if it is,
scale that instead and the window follows for free.**

**84. WHEN A 3-BYTE `imm8` CANNOT HOLD THE SCALED VALUE AND THE NEIGHBOURS HAVE
NO SLACK, USE A CAVE - NEVER CLAMP.** (Same event; law 136's inverse.) `83 C3 7C`
must become 186/248/372, none of which fit a signed imm8, and the surrounding
instructions offered 7 bytes where 10 were needed. The honest move is a 5-byte
`jmp` over the 8 bytes spanning two instructions, into a cave that re-does BOTH
with a full `imm32` and returns. Clamping to 127 would have looked like a fix at
1.5x and failed at 3x.

**85. MODEL CALLEE-CLEANUP OR YOUR STACK SLOTS ARE FICTION.** (Same event.)
A frame-slot analysis that treats `call` as leaving `esp` unchanged is wrong from
the first `thiscall`/`stdcall` onward - it put the text origin in a slot nothing
ever wrote, and would have justified patching the wrong instruction. Model it
(callee pops its args unless an `add esp,N` follows), and sanity-check that every
slot you READ was WRITTEN somewhere.

**86. ⭐ THE SHEET'S ROLE DECIDES ITS SIZING RULE, AND THERE ARE THREE ROLES.**
(#160, 2026-08-15, completing #156 and #157.) Derived from the `.UI` that BINDS
each sheet, never guessed from the number:

| role | needs | evidence | list |
|---|---|---|---|
| N-state strip | `width/N` | window size == one cell | `cell-strips.txt` |
| 9-slice frame | `width/3` | `blttype=edge` / `edgeimage=yes` | `nine-slice.txt` |
| **tiled background** | **NOTHING** | `blttype=tiled` | `tiled.txt` |

A tiled sheet is src-follows-dst: the engine repeats the source across the
destination, so its ONLY contract is that the scaled sheet still equals the
scaled WINDOW - and the window scales by a plain round. Snapping it protects a
divide it does not have and desynchronises the pair. MEASURED on the god
toolbar rail `{46a006b0,14415876}`: 1x 74x351 == window; 2x 148x702 == window;
**1.5x art 528 vs window 527**, USER-REPORTED as "a break in the white line on
the left that is not in 2x or stock". Keep all three lists EXCLUSION-BIASED so
an unknown consumer can be missed but never broken.

**87. RULE OUT YOUR OWN LAST CHANGE FIRST, BY NAMING CONSUMERS - NOT BY
FEELING.** (Same event.) #157 had moved 6 sheets **at 1.5x only** hours before a
new 1.5x-only defect appeared: the same signature, the obvious suspect. The way
to clear it is to name every consumer of every sheet you touched (here: four
dialog frames + the timer panel + Graphs/Data Views - no toolbar), not to argue
from plausibility. Do this BEFORE investigating anything else; if it IS yours,
everything downstream is wasted.

**88. A MODEL THAT WOULD CONDEMN STOCK IS A BROKEN MODEL, NOT A FINDING.**
(Same event.) A quick check flagged three 9-slice sheets whose 1.5x width was
"not divisible by 3, SHORT BY 2". Wrong on both counts: a 9-slice tiles
`[0,cell] [cell,W-cell] [W-cell,W]` and covers ANY width exactly, and those
sheets are not divisible by 3 at **1x** either - so the model accused the
untouched stock game. **Before believing a defect report from a new instrument,
run it against 1x: anything it condemns there is the instrument's fault.**

**89. ROUND HALF UP EVERYWHERE, BECAUSE HALF-AWAY-FROM-ZERO LENGTHENS ANY SPAN
THAT CROSSES THE ORIGIN.** (#162, 2026-08-15.) `ScaleRound` was `std::llround`.
llround pushes a negative half value outward (-16.5 -> -17), so a window with a
NEGATIVE absolute design origin has both edges rounded outward and comes out one
pixel longer than the same span scaled as a LENGTH - the art gets 75, the window
gets 76, and the leftover row is a hairline. It also shifts a negative-origin
parent's whole subtree by a pixel against its own background. **Invisible at
every integer tier** (v*f is exact there, so the two rules are the same
function), which is exactly why the user saw it at 1.5x and never at 2x. Rule:
one rounding convention - `floor(v*f + 0.5)` - shared by the runtime sweep, the
art upscaler and the `.UI` builders. Two conventions in one pipeline is a
guaranteed off-by-one at fractional tiers, and it will only ever show up at the
tier nobody is looking at.

**90. THE FIX IS OFTEN ALREADY IN THE FILE, WRITTEN BY US, WITH A COMMENT
NAMING THE DEFECT.** (Same event.) `RoundHalfUp` sat at the top of
`UiSpike.cpp`; its comment already said it "differs from llround/ScaleRound only
at NEGATIVE half values" and that "the art pipeline convention wins". Five fixes
and three probes were spent reasoning from mechanisms before anyone read it.
**Before instrumenting a new theory, grep our own source comments for the
symptom's vocabulary** - here, "negative" and "rounding".

**91. A PROBE ON A LAZILY-INSTALLED HOOK IS A GUARANTEED NULL.** (Same event.)
`BltClassThunk` is patched in only by the disaster-flyout birth path, so two
capture runs with the probe armed logged NOTHING - and the silence was read as
"nothing draws through this class". Before spending a launch: name what installs
the hook, and confirm the user's actions will trigger it. If they will not, the
probe must install it itself. This is one step worse than
[[feedback-sc4-prescale-while-hidden]]'s installed-not-executed: never installed.

**92. A "KNOWN RESIDUAL" THAT EXISTS AT ONE TIER ONLY IS THE DEFECT.** (#162,
2026-08-15.) `gate_btn_undercover.py` printed `15x {(0,2):347}` / `2x none` /
`3x none` for weeks under a PASS line reading "the KNOWN ScaleDim cell-snap,
reported not failed". 347 buttons whose art cell was 2px taller than its window
at exactly the tier the user was complaining about. Six fixes were shipped past
it. When a gate reports a nonzero number it has chosen not to fail on, do not ask
whether it is tolerable - ask whether it VANISHES AT THE TIERS THAT WORK. If it
does, stop looking anywhere else. Related: [[feedback-check-our-previous-work-first]].

**93. ASK WHETHER THE ARTIFACT IS LIGHTER OR DARKER BEFORE BUILDING ANYTHING.**
(Same event.) Six fixes hunted an UNCOVERED GAP - abutting rects, art-vs-window
sizes, tiled and 9-slice rules, a rounding convention. The user was then asked
two one-word questions: lighter or darker, and how long. **Lighter** means
something PAINTED those pixels, which refutes the entire gap family in one
sentence; **short segment** rules out a window edge and a panel-wide tile seam.
Both answers cost the user five seconds and would have saved every one of those
builds. For any visual defect, establish sign (light/dark = painted/uncovered)
and extent before choosing a mechanism.

**94. THE RIGHT RULE AT THE WRONG SCOPE IS STILL A BUG, AND HAND-LISTS ARE HOW
IT HAPPENS.** (Same event.) #143's cell-divide snap is correct for a state
strip's WIDTH and wrong for its HEIGHT - a horizontal strip has no vertical
divide. #150 found that, and scoped the cure to a hand-written list of four TGI
groups; every strip outside those groups kept the bug. The cure is to key on the
DERIVED list (`cell-strips.txt`), never on a hand-list. And check EVERY consumer:
`build_dialog_static.py` was missing the flag as well as
`build_selective_safe.py`, so the first rebuild fixed only half the count
(law 59, every consumer of a shared rule needs its own wiring).

**95. AN INTEGER-TIER CONTROL IS WHAT STOPS A SELF-MEASURING METRIC SHIPPING.**
(Same event.) A new ridge-thickness gate probed a fixed +-2 rows at every factor;
once a ridge is f px thick that probe sits inside it and detection collapses, so
2x and 3x scored as "ragged" as 1.5x. The metric was measuring its own sampling
pattern. The mandatory "integer factors must read 0.000" control caught it before
it became fix number seven. **Any new fractional-tier metric must be run at 2x
and 3x first, and must read exactly zero there.**

**96. ⭐ A CURE HAS AS MANY PATHS AS THE GEOMETRY HAS PRODUCERS — AND THE THIRD
ONE IS THE ONE THAT SHIPS THE BUG.** (#170, 2026-08-16, USER-CONFIRMED.) #148's
leaf size-derived rule went into `ScaleSubtree` (v2.94.1), then into
`build_dialog_static.py` (#155), and NEVER into
`build_selective_safe.py::double_subtree_areas` - the DATA pre-scale path. The
seven advisor buttons x2 HUD scripts shipped an **82px window around an 83px art
cell** at 1.5x only, and the user saw a break on the RIGHT of every icon.
**Both earlier fixes were structurally incapable of touching it:** #167 patched
`ScaleSubtree`, but `0x6A15C767` is in `kDataScaledSubtreeIds` so
`ScalePanelRoot` RETURNS before the child loop - the log had been printing
`city panel 0x6A15C767 - 1 windows scaled` (ONE window) the whole time; and
#169's per-state art sampling changes nothing in the resting state (output col
82 samples src col 54 under both samplers). **Before fixing a panel, ask WHO
COMPUTES ITS GEOMETRY - the sweep, a static builder, or a data pre-scale - and
check the log line that says how many windows the sweep actually touched.**
Sibling of law 75; this is its third strike.

**97. A GATE THAT MODELS A RULE MUST FIRST PROVE THE RULE RUNS THERE.** (Same
event.) `gate_btn_undercover.py` scanned the selective-safe stage and MODELLED
the DLL's leaf rule for a subtree the DLL provably never walks, then counted the
advisors as "PARITY CLASS repaired". Its scope filter finished the job: it
required the 1x art cell to equal `r - l` read from the STAGED file, which for a
pre-scaled node is the SCALED width, so all fourteen fell out at `continue` and
were never even counted. It printed PASS over a user-visible tear for weeks.
Cure: pair staged nodes with their 1x design by DOCUMENT ORDER (ids collide -
the two HUD variants share every id), and judge a pre-scaled node VERBATIM.
Negative control on the old build: **146 mismatched at 1.5x, 0 at 2x, 0 at 3x**.
Then SPLIT THE VERDICT BY CAUSE or the gate blames the builder for the
upscaler's arithmetic: cell == `states * R(cell1x*f)` means the art is right and
the window rule is wrong (hard fail); cell != that means `ScaleDim` snapped the
sheet (law 70) and it is REPORTED, not failed.

**98. ⛔ DBPF FILE HASHES ARE NOT REPRODUCIBLE - COMPARE ENTRY PAYLOADS.** (Same
event.) Two builds of byte-identical source differ in exactly **2 bytes, at
offsets 25 and 29** - the header timestamp. A file-level sha256 reports a false
change on every rebuild, and it nearly aborted a correct fix on a bogus
"2x CHANGED - STOP" reading. The honest integer-tier control is per-entry:
parse the index and hash each entry's bytes by TGI. #170's controls read
**2x 655 entries / 0 differing payloads, 3x 655 / 0**, with 44 changed at 1.5x -
all `T-00000000` .UI scripts, no art. Law 40 said equal sizes prove nothing;
this is the converse - unequal hashes do not prove a change either.

**99. ⭐⛔ A `.rdata` CONSTANT SWEEP IS BLIND TO INLINE IMMEDIATES.** (#188, the
U-Drive-It offer balloon, 2026-08-18. Seventeen launches.) Every "the constant
is inert" verdict in that task was true and useless: we scaled the four CSI
floats in `.rdata`, the per-zoom pixel table, the effect instance scale and the
effect child scale, all with read-back proof, and the balloon never moved.
BOTH real levers were `imm32` fields **inside instructions** - eight
`mov [esp+disp32], imm32` (`C7 84 24 …`, imm at instruction+7) for the pin
quad, and one `mov eax, imm32` (`B8`, imm at +1) for the icon. A `find_imm`
over the whole file DOES see them; a sweep restricted to data sections does
not. **State explicitly whether inline immediates were scanned before calling
a constant hunt exhausted** - otherwise it is a FILTERED NULL of exactly the
kind law 42 and [[feedback-null-is-not-evidence]] forbid.

**100. ⭐ SUPPRESSION IDENTIFIES; SCALING DOES NOT.** (Same event.) Every
"make it bigger" probe returned an ambiguous *no change* that could mean wrong
constant, dead code path, or clamped downstream. The probe that made the
balloons VANISH named the drawer in ONE launch (`cSC4DispatchVehicleView::Draw`
0x0046D990, user: "THEY'RE GONE"). When you do not yet know WHO draws
something, ask it to STOP, never to grow. Growth tests are for after the owner
is known.

**101. ⭐ WHEN TWO ELEMENTS OVERLAP AT SIMILAR SIZES, 1.5x CANNOT SEPARATE
THEM - USE A FACTOR THAT NEEDS NO INTERPRETATION.** (Same event.) The balloon
is TWO quads - a 64x64 pin and a 35x35 icon. Three consecutive 1.5x launches
produced three CONTRADICTORY readings of which one had moved, including two
wrong calls by me off compressed screenshots. One 3x launch answered correctly
and instantly: the pin tripled, the icon did not. Exaggerate the probe, read
the answer, then dial back to the shipping factor.

**102. DO NOT JUDGE A SIZE RELATIONSHIP BY EYE FROM A LOSSY SCREENSHOT.**
(Same event.) I called the ±32 quad "the icon" and then "the backing" from two
zoom levels of the same JPEG, and was wrong both times. A screenshot proves
PRESENCE, COLOUR and GROSS CHANGE reliably; it does not measure ratios. If the
answer depends on relative size, change ONE element by a large factor and ask
which one moved - or ship a RULER (see law 104).

**103. A CONSTANT CAN BE LIVE AND STILL BE THE WRONG CONSTANT.** (Same event.)
`0x00A8819C = 42.0f` applied cleanly, read back correctly, and did nothing
visible - because it feeds the quad's TRANSLATION (`centre = x0 + 42/2`), not
its extent. It was quietly moving the balloon ~10 px the whole time. "Patch
applied, no visible change" therefore does NOT imply the patch is dead; it may
be alive and aimed at a property you were not watching. Say which PROPERTY a
constant feeds before concluding anything from its silence.

**104. ⭐ INSTRUMENT THE ART TO MEASURE, NOT ONLY TO COLOUR.** (Same event.)
Colouring the icons red proved the override wins but measured nothing. Filling
each cell edge-to-edge with a solid block + crosshair turned the DESTINATION
RECT into a number readable off one screenshot - that is what revealed the
drawn size is source-independent. Better still is a HOLLOW frame (3px border,
transparent centre, in a colour absent from the game's palette - magenta):
it measures the art's extent AND leaves whatever draws behind it visible, so
one shot shows both overlapping elements instead of hiding one. An opaque
instrument HIDES the thing you have not thought of yet.

**105. THE HIT BOX AND THE ART CAN SHARE ONE NUMBER - CHECK BEFORE YOU CELEBRATE
OR DESPAIR.** (Same event.) The CSI icon's width/height (`record +0xD0/+0xD4`,
both set from the single `35.0f` at 0x0046CC47) is ALSO what the click test
consumes - user-observed, "only the inner glyph is clickable, not the grey
around it". That is a gift when true (art and tap target cannot drift apart)
and a trap when false. For any in-world element the player CLICKS, find out
which it is: scaling art without the hit box ships a lie, and scaling the hit
box without the art ships an invisible button.


**106. ⭐ A THRESHOLD EXPRESSED AS A FRACTION OF THE SCALE FACTOR COLLAPSES
AT A FRACTIONAL TIER.** (#186, 2026-08-18.) The gauge draw suppressed its
dst-stretch when `m < 0.75f * scaleFactor`. Calibrated at 2x that reads 1.50 -
an enormous margin over the m ~= 1.0 that already-scaled art produces. At 1.5x
the SAME expression reads 1.125, which sits INSIDE the band of legitimate
rounding disagreement between cell-first art (cell 77) and an edge-derived
window (87). One gauge landed on 1.1299 and missed the snap by 0.005. This is
law 95 wearing different clothes: a tier-relative threshold MEASURES ITSELF.
Ask the absolute question instead - here "is this source still 1x?", which
1x art answers by construction (`R(cell*f) <= win`) while scaled art overshoots
by nearly the whole factor (want 116 vs win 87). Any guard whose constant is
multiplied by the factor is a candidate; check what it evaluates to at 1.5x
before trusting that it works because it works at 2x.

**107. A FRAME STRIP'S PITCH MUST DIVIDE EXACTLY, AND ONLY A FRACTIONAL TIER
CAN BREAK IT.** (#186.) The dial draw does `cell = img->Width() / count` with
an INTEGER divide. A 2805px 55-frame sheet (cell 51) sized total-first becomes
R(2805*1.5) = 4208; 4208/55 = 76 against a true pitch of 76.5, so the source
window slips half a pixel PER FRAME and is 27.5px - a third of a cell - into
the neighbouring frame by frame 54. On screen a dial "wraps around". Integer
tiers cannot show it: k*W is divisible by N whenever W is. So a strip defect
that appears at 1.5x and nowhere else is a PITCH defect, not a rendering one -
and the cure is law 86's cell-first sizing, `N * R(cell, f)`. The corollary
that cost this one weeks of invisibility: a derivation keyed on `.UI`
`image=` references is BLIND BY CONSTRUCTION to code-bound art (these strips
come from vehicle exemplar 0x2BE8E6CB), so the right rule sat in the codebase
at the wrong SCOPE (law 94). When a divisor is DATA rather than an immediate
it cannot be disassembled - MEASURE it (a needle strip is periodic with period
= cell) and gate the measurement on an independent control.


**108. ⭐ A PATCH THAT CANNOT EXPRESS ITS VALUE MUST REFUSE OR WIDEN - NEVER
SILENTLY TRUNCATE.** #189: the budget department popup "opened for a split
second then resized" at every tier, for months. Cause was one line of ours -
`if (bh > 127) bh = 127;` - clamping a create height to the `push imm8`
ceiling while the width beside it took the full factor. The window was
therefore BORN half-patched (450x127 instead of 450x150 at 1.5x) and something
later set the true height: that correction IS the flash. The clamp is a
constant while the target is not, so the jump GROWS with the tier - 23px at
1.5x, 73px at 2x, 173px at 3x - which is why no tier-specific model ever fit
and why "it happens at 2x and 3x as well" was the decisive clue, not a
complication. Forty lines away in the same file, `ApplyCostBoxScale` meets the
identical ceiling and REFUSES both sites rather than half-patch, saying so in
the log; that is the correct behaviour, and this site simply did not follow it.
Cure = the #159 cave (jmp + NOPs into a stub that pushes full-width imm32 and
returns), never a runtime pin - a pin corrects AFTER creation by construction,
which is the defect. Corollary, and the expensive half: **the value was in our
own summary line at every launch** (`bizbox 450x127`), and four instruments got
built to go and find it - three of them aimed at the wrong window entirely.
GREP YOUR OWN LOG FOR THE NUMBER BEFORE BUILDING A PROBE TO MEASURE IT.
