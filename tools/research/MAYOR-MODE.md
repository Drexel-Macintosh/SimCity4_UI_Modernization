# ═══ SESSION STATE 2026-07-29 NIGHT (v2.23.3-lifecycle) — READ THIS FIRST ═══

Deployed v2.23.3. **Full state, open bugs and the five audit digests are in
`HANDOFF.md` and `tools\research\_checkpoints\` — read those, not this block,
for anything current.** Next in-game session is scripted in
`_tests\RUN-SHEET-NEXT-SESSION.md`.

Shipped since the v2.20.4 block below: Data Views (2.21.0-.3), U-Drive-It
status panel + bubble + dashboard + gauges (2.21.4/.5, 2.23.2), My Sims all
nine roots + AdviceList guard (2.22.0/.2), sub-flyout crash guard (2.22.1),
the mode-transition flash fix (2.22.4 — the cause was the VISIBILITY GATE, not
sweep latency), the coverage-audit art bug (2.22.3), twelve text-sweep dialogs
(2.23.1), Grutzehaus + 4 landmark icons (2.23.2), second-city lifecycle
hardening (2.23.3).

**Open, ranked:** #55 picker icons (our regression — LEFT1X art in a doubled
frame), #48 U-Drive-It dock AND sub-flyout hooks (user asked twice; measure the
strip before opting into kParents — widening that gate is what crashed the
game), #47 runtime-painted images (portraits/chips/chart; gauges DONE and are
the model), #53 silent caps, Graphs background + Building Style boxes (one
measurement each), #52 tier math (in flight), #54 the last ~6%.

**New laws this session:** for a SHARED container the right class is not the
right window; auto-discovery rules can enrol unchecked parentage; a deferred
window in a scaled ecosystem tears apart; an art sweep must scan `.SC4Lot`
containers; LEFT1X art inside a doubled frame is a bug; the flash is the
visibility gate; latches must clear in `Disarm` or city 2 breaks.

# City-mode UI scaling backlog

# ═══ SESSION STATE 2026-07-29 NIGHT (v2.21.4-udriveit) — READ THIS FIRST ═══

## U-Drive-It (task #46): v2.21.4 DEPLOYED, awaiting eyes-on

Two fixes, both DPROBE/disasm-measured (`_tests\REGRESSION.md` →
"U-DRIVE-IT"): the driving status panel was a **4x double-scale we shipped
ourselves** — `discover_query_family()` auto-enrolled the eleven
0x10000005-marked U-Drive-It scripts into the static dat, but their root
0x10000006 parents at the 3D VIEW so the sweep doubled it again; fixed via
kNeverScaleIds (the Establish City rule) + a parentage warning in
build_dialog_static.py. The tiny mission bubble = code-bound art
{46a006b0,094ac89a} + the 15-glyph mission table at VA 0x44DEC7 → CODE_BOUND_TGIS,
SelectiveArt 358 → 367 (two glyphs conflict-skipped by the classifier:
46a006a4/a6). NOTE for testing: mission bubbles are ONE-SHOT — each can
only be selected once, so verification needs an unused bubble.

## Data Views panel (task #45): ✅ USER-CONFIRMED at v2.21.3

Closed after three builds the same night. THREE coupled parts (breaking one
regresses it): sweep+art (root 0xAA32BCE6, SelectiveArt 358), DVMAP surface
recreate (the crash preventer — map child 0x00004203 is a second
cSC4WinMiniMap), and DVPIN (v2.21.3): the game re-lays the legend on every
view select with 1x origins + 2x font-derived pitches, so a pin-back pass
re-imposes scaled design geometry each sweep while the page is visible
(the RCI treatment; DPROBE-measured targets). Full stock A-B sweep of the
panel deferred to regression testing (Set-StockCompare.ps1). Details:
`_tests\REGRESSION.md` → "DATA VIEWS PANEL".

## v2.21.2 history (superseded by the block above)

The v2.21.0 crash is SOLVED by disassembly: the expand path is pure
show/hide (no moves); the killer was the map child **0x00004203 — a second
cSC4WinMiniMap instance** (GetClassID 0x7A6580 → clsid 0xCA318388) whose
one-shot display surface stayed 256 while the data-view renderer
sub_7A2F60 built window-sized 512 buffers (rect read 0x7A301E, buffer
create 0x7A3094). v2.21.2 re-lands the panel scaling + runs the
dock-minimap surface-recreate lever on 0x4203 (DVMAP block). COUPLING
RULE: SelectiveArt 358 without the DVMAP block = the crash build.
Expected log: `DVMAP 2X win 512x512 blitSize=512` + `recompute 0x7A7840
ok`. Eyes-on checklist: expand, pick a view, check the 512 map; DPROBE
the "small shift" (stock shifts 3px between states by design). Full
write-up: `_tests\REGRESSION.md` → "DATA VIEWS PANEL".

## Superseded that same night — v2.21.0/v2.21.1 history

The panel opened as a crushed 1x sliver because the city sweep SKIPPED root
0xAA32BCE6 by id (`kGZWin_MenuContainer`, an early-spike label wrongly
claiming "plop-menu machinery"; the dump proves the subtree is purely the
Data Views fold-out panel). v2.21.0 removed the skip + shipped 2x art:
**compact panel user-confirmed good at 2x — but EXPAND shifted the panel
right and crashed the game** (silent native death, no WER event). v2.21.1
reverted BOTH sides (skip back + art out, 358 → 345 all tiers; deployed,
suites green). The "shifted right" proves the expand handler repositions
with 1x metrics; prime crash suspect is the code-painted 256x256 data-map
child 0x00004203 (minimap-surface problem class). **Next step is OFFLINE:
disassemble the expand handler** (playbook workflow) — full plan + trap
signatures in `_tests\REGRESSION.md` → "DATA VIEWS PANEL". Facts that
survive the revert: live script = **I-2bc9060f** (rect-matched;
I-ea287193 / I-0b72f276 stale copies, same root id); on re-land 140155ec +
14416264 go shared-clone (Audio Options I-ca53f06e keeps 14416264 at 1x —
never force in-place).

**LAWS LEARNED:** skip lists written in an earlier project phase are a
scenario axis — re-audit every surviving id-skip when its subtree's real
owner becomes known. And the scenario matrix's *panel lifecycle* axis
includes EXPAND: a fix confirmed on the compact state only is half-tested.

# ═══ SESSION STATE 2026-07-29 END OF DAY (v2.20.4) ═══

Assume no chat context. **Read `_tests\SCENARIOS.md` before believing any fix
is done** — five bugs this session were caused by an untested scenario axis,
not by bad code.

## Everything closed today, and the law each one taught

| Area | Fix | The generalisable law |
|---|---|---|
| News/ticker/stories/tutorials/Credits text | v2.19.0 HTML size tables patched | **All rich text is the game's HTML engine, not FontStyle** — explains the community's "font size doesn't work for news" |
| Ticker headline wrapping | v2.19.1 design width in the shipped `.UI` | The game re-imposes init-cached geometry → **fix it in DATA** |
| Budget black areas / toasts crushed | v2.20.0/.2 art pass + static dialogs | An art-pass gap looks like a geometry bug; measure before assuming |
| Advisor faces quarter-zoomed | v2.20.0 subtree pre-scaled in DATA | **Runtime is structurally too late** when the game binds at city load |
| Advisors box mis-docked | v2.20.1 skip `0x0000AAAA` | **Alignment markers are positioning data — never scale, anywhere** |
| Building Style corrupted | v2.20.2 mod's script + mod's art in `zzz-` | **LOAD-ORDER LAW**: a plugin can replace a script AND its art |
| "Change style every" + year spinner | v2.20.3/.4 `kFontSizedIds` | **Never scale a control sized from its own caption or art** |

Both Building Style states are user-verified at 2x: the mod's 36-slot layout
AND (via `_tests\Toggle-BuildingStylesUI.ps1 -Off`) the STOCK 4-style panel
with its four previews — the first real vanilla data point for the roadmap's
vanilla pass. The mod's layout has NO style previews at all; that is its
design, not a scaling bug.

## Where to look next

- Task #31 stock-parity PIXEL pass (geometry already verified clean).
- Vanilla verification pass — see the TODO in `_tests\SCENARIOS.md` (needs a
  whole-`Plugins` toggle script; copy the Building-Styles toggle pattern, and
  remember it must move OUR override too or our copy keeps the mod alive).
- 1.5x / 3x eyes-on (they build and pass offline; rounding is the risk).
- My Sims panel remains DEFERRED (`kNeverScaleIds`, Sim Mode).

## v2.20.2-stylepanel DEPLOYED — Building Style Control (task #44)

**NEW FAILURE CLASS, worth recognising on sight:** a plugin can REPLACE a
stock .UI script wholesale, and our root package can never override it
(load-order law). CoriBoom's 36 Slot Building Styles UI replaces the
Building Style Control script from 150-mods\, so that panel had NEVER been
scaled — the sweep doubled the mod's 73 windows over its 1x imagerects.
RECOGNITION RULE: **if a panel's live window count / root size doesn't
match the stock script you're editing, a plugin replaced that script**
(here: live 532x640 + 73 windows vs stock 531x406). Fix: build from the
MOD's script into `zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI[-tag].dat`
(new `thirdparty-ui\` builder input, synced by ScaleTier, 1 entry).
Detail + traps: REGRESSION.md "BUILDING STYLE CONTROL"; developer callout
in UPSTREAM-BUILDINGSTYLES-REPORT.md.
EYES-ON: Building Style Control compact + expanded (list, both style
columns, the mod's three checkboxes, Collapse button).

## v2.20.1 advisors — CONFIRMED WORKING by the user (faces + dock + no flash)

## v2.20.0-advdata DEPLOYED — the advisor ROOT FIX

**THE LAW THIS ADDED (generalizable):** when the game reads a child
window's geometry BEFORE our first sweep can run — 3D head framing bound
at city load, ticker marquee init caches — runtime scaling is structurally
too late. Ship that geometry PRE-SCALED IN THE .UI and make the parent
root-only in the DLL. Two instances now: the advisor strip subtree
(kDataScaledSubtreeIds + double_subtree_areas) and the ticker marquee
width. Both were first "fixed" with runtime hacks that only half-worked;
the data fix deleted the hack.

v2.20.0 pre-scales the strip subtree in data (20 area= edits per script,
all 3 factors, VERIFIED 16/16 against live 2x values) so the heads are
framed from 2x buttons at bind time. No injected input, no flash.
`[Flyout] AdvisorHeal=0` is now only an escape hatch. Traps:
REGRESSION.md "ADVISORS".
EYES-ON: open Advisors first thing on a fresh city load — faces correct
immediately, no flash, and the strip's buttons/title NOT oversized or
overlapping (that would mean double-scaling).

## v2.19.5-advclick (superseded, kept as fallback)

v2.19.3 fixed the briefing pages (user-confirmed) but NOT the first-open
faces: LIVE 3D HEAD RENDERS whose framing is created ONCE (head binder
exe 0x41DE20, slot reuse on later entries) and re-derived only on an
advisor VIEW SWITCH - v2.19.4's window Hide+Show fired but proved
visibility is not the trigger. v2.19.5 synthesizes the user's manual
workaround (real clicks: face 1 -> Return) once per city load on the
strip's first scaled visible sighting; [Flyout] AdvisorHeal=0 off;
briefing flashes ~250ms once. Detail: REGRESSION.md "ADVISORS".
EYES-ON: advisor faces on very first open of a fresh city load (expect
one brief briefing flash, then correct faces).

## v2.19.3-advisors DEPLOYED (on top of v2.19.2 below)

USER-CONFIRMED from v2.19.2: toasts fixed, budget fixed, Credits good.
Then four advisor defects reported and fixed in v2.19.3: quarter-zoomed
faces on first open (strip 0x6A15C767 had 2x art but no hidden pre-scale),
corrupted briefing page + expanded view (0xAA15EF06/0x2A1D96B1 were never
in the art pass), and their AdviceLists 0x0010010x guarded never-recurse
preemptively. SelectiveArt 345 all tiers. Detail: REGRESSION.md
"ADVISORS". EYES-ON: advisor strip first open, briefing page, expanded
speech box, ticker one-line scroll, one tutorial page, airports
first-open.

## v2.19.2-budget-toasts DEPLOYED (on top of v2.19.1 below)

Two more user reports fixed in one build: the expanded BUDGET's black
areas (art-pass gap - geometry was already perfect 2x; added 0xAA3AC001
expanded + 0xAA3AC002 Taxes + 0xCA4C332D Loan to SCALED_WINDOW_IDS ->
SelectiveArt 339, budget-art conflicts resolved; Taxes/Loan also into
kAlwaysScaleCityIds, they measured 1x-while-hidden) and the CRUSHED
ADVISOR TOASTS (five message-box scripts I-4a5a89d4/d5, I-2bb16d50,
I-0bbc06b6, I-4bbc080f into dialog-static -> DialogStatic 220 all tiers).
Detail + trap signatures: REGRESSION.md "BUDGET PANEL + ADVISOR TOASTS".
EYES-ON CHECKLIST: expanded budget clean, Taxes + Loan dialogs, toast at
2x, ticker one-line scroll, Credits look, one tutorial page, airports
first-open.

## NEWS BOX + NEWS POP-UP (task #42): v2.19.1-tickerwidth DEPLOYED

**USER-CONFIRMED from v2.19.0 screenshot:** reader headlines 2x, expanded
story text 2x with working links, popup-style body text right. ONE defect
reported: the ticker headline wrapped ("Eye" on a second line) - the game
re-imposes the marquee's init-cached 1x geometry every roll tick, so the
runtime width-scale was undone within a frame. v2.19.1 ships the marquee
DESIGN width scaled inside the edited .UI (SelectiveArt I-2a2aed99;
676->1352 / 484->968) and the DLL never touches the marquee at all
(kAdviceListNeverTouchIds). Remaining eyes-on: ticker one-line scroll,
pop-up toast, Credits look, one tutorial page, airports first-open.

**THE FINDING: all news text is HTML.** Ticker roll, reader headline rows,
story pages, advisor/message popups, tutorials, Credits - one rich-text
engine (item clsid 0xaa12e5f5; both AdviceList instances - ticker marquee
0xAA12F33C and reader list 0x6A231531 - are cSC4WinAdviceList 0xca1492ac
whose items host it). Exe templates in .rdata carry literal SIZE=2/SIZE=3;
189 locale LTEXTs embed their own <font size="N">; SIZE resolves through
two .rdata point tables (FONT 0xACD4A0 {8,10,12,14,18,24,36}, H1..H7
0xAB4AD0). FontStyle.ini NEVER reaches this path - the community's "font
size does not work for news" limitation, now explained and fixed.

**The fix ships as v2.19.0 (full detail + trap signatures: REGRESSION.md
"NEWS BOX + NEWS TEXT = THE HTML ENGINE"):**
1. `ApplyHtmlSizeScale` scales both tables x factor + retargets the popup
   builders' Message* style GUIDs at stock-size clones
   MessageHeaderHtml/MessageBodyHtml 0x5c4b0914/15 (in all six FontStyle
   files) - THREE COUPLED PARTS, see the runbook before touching any.
2. AdviceList geometry: reader list scale-self-never-recurse; marquee
   WIDTH-only (height = 3*lineHeight from the 2x font, Y animates);
   ticker root-only rule REMOVED (BMP + clip strip now scale normally).
3. SelectiveArt 271 -> 328 (all tiers): exe news page art 0x140155b4..f7 +
   sc4://image LTEXT art (html-image-refs.txt). Deliberate hole:
   html_TextBG 14416264 stays 1x (three HUD panels 9-slice it).
4. Credits LTEXT size maps re-calibrated (build_dialog_static.py) - the
   old bumps would compound against the scaled tables.

**EYES-ON CHECKLIST (next session start):** reader headlines ~24pt + row
geometry sane; click a story -> 2x text on 2x newspaper art; ticker text
2x scrolling through a 2x strip; trigger a disaster/story -> the POP-UP
TOAST (never yet measured - if its FRAME is 1x, MPROBE it, it is likely
one of the 0x443FCA/0x76A183/0x78CE12 rich-item creation sites' windows);
Credits from Play Options (approved look preserved); one tutorial page;
airports first-open self-heal (v2.18.6, also still unconfirmed).

# ═══ (superseded) SESSION STATE 2026-07-29 EVENING (v2.18.6) ═══

Deployed + USER-CONFIRMED as of v2.18.6:

## What the 2026-07-29 marathon fixed (each with its runbook entry)

| # | Fix | Version | Mechanism |
|---|---|---|---|
| 1 | SubRingDX/DY derived (25,-6), not dialled | ini | keyring hole (25,26) onto off-centre button ellipse (21,15); tools/flyout-sim/derive_subring.py |
| 2 | Rails & depots + 4 more transport menus dock | 2.16.0 | THE PLACEMENT LAW: nativeY = btnCentreY − ringBltY − 29; ringBltY recorded at blit time |
| 3 | Freight (258x206) ring/dock | 2.17.1 | destIsSubContainer = EXACT width 258, h>=100 (height-only gates failed twice) |
| 4 | Submenus-mod icons duplicated | zzz dat | LOAD-ORDER LAW: root files load BEFORE subfolders; overrides of other mods go in zzz-SC4UIScale\ (ItemIconsSub-2x.dat, 125 icons) |
| 5 | CAM landmarks duplicated (Grutzehaus=missing-thumb) | zzz dat | full-plugin icon scan incl. TEXT exemplars; +69 +Missing Thumb 0x144161EC |
| 6 | CAM's 10 unreachable items (police/fire/jail/lifeguard) | MenuFix.dat | exemplar-patch cohorts (0x05342861/G-B03697D1/prop 0x0062E78A); UPSTREAM-CAM-REPORT.md |
| 7 | Back arrow = click the physical button | 2.17.0 | ArrowClick claim+forward (container slot-121 + strip 62/136); mod source proves the gesture |
| 8 | Emergency flyout ring/pictures | SelectiveArt 271 | GZWinBMP draws dst = src size -> 2x art = 2x draw; it was the LAST missed art pass |
| 9 | Tooltip wrap 250 -> 500 | 2.18.0 | TooltipWrapPatch byte patch (push 0xfa x2 in tip Plot 0x798710); tip layer 0x2AAB8CC1 class 0x00AB6770 code-paints ALL of it |
| 10 | Tooltip torn fill / clipped corners | 2.18.2/.3 | OUR bar transform was eating tip buffers via size heuristics; bar block now mode-split: god->disaster(200-400w,>500h), mayor->sub(w==258) |
| 11 | Pill cap square shoulders | 2.18.4 | caps NEVER y-doubled (x-widen only, = approved disaster look) |
| 12 | First-open 1x items (airports) | 2.18.6 | sweep INVALIDATES when strip fields still 1x; NEVER writes fields (2.18.5 wrote them, poisoned the Plot hook's one-shot natural capture = 4x pitch everywhere) |

## Standing hazards (cost a regression each - do not relearn)

- Plot-hook naturals are captured ONCE; any other writer that runs first
  poisons them. Sweep-side = invalidate only.
- Size heuristics cannot identify windows whose size follows CONTENT
  (tooltips!). Positive ID: exact width, mode splits, or class+id.
- The alpha guard is `0 < a < 128` NEVER `a < 128` (stock art is a==0).
- Root z_*.dat files CANNOT override subfolder dats (load-order law).
- Parse BOTH exemplar formats (binary EQZB + text) - CAM is ~half text.

# ═══ (superseded) SESSION STATE 2026-07-29 (v2.15.3) ═══

Assume no chat context. This section is the current truth; everything below it
is history kept for mechanism detail.

## What works now (user-confirmed in game)

| Item | State |
|---|---|
| Founded-city GOD MODE | ✅ all 4 tools (Obliterate/Reconcile/Disaster/Day-Night) |
| Terraform (pre-founding god) | ✅ unchanged through ~20 rebuilds |
| Minimap dock | ✅ |
| Disaster flyout | ✅ still good after sharing its machinery with sub-flyouts |
| Landscape flyout dock | ✅ (22,344) |
| Zone flyout dock + 2x ring | ✅ (22,344) |
| SUB-FLYOUT (zone density, road types...) | ✅ position, 2x bar, seated icons, 2x circle, LEFT-HALF CLICKS |
| SelectiveArt | ✅ 264 entries, stray untagged package retired |
| Offline suites | ✅ Test-DatIntegrity + Test-ScaleTierDecide ALL PASS |

Derived-but-NOT-yet-eyes-on: Transportation (22,444), Utilities (22,544),
Civic (22,344), Emergency (22,542 - its marker is PREDICTED from the script,
never measured).

Deferred: **My Sims** - in kNeverScaleIds, needs a code-level slot-pitch hook
plus 2x portraits. It is SIM MODE, which the section plan puts after Mayor.

## ✅ CLOSED 2026-07-29: SubRingDX / SubRingDY are now DERIVED

`[Flyout] SubRingDX=25  SubRingDY=-6` — derived by
`tools\flyout-sim\derive_subring.py` (re-runnable; needs `tools\dbpf\extracted`).
The 2026-07-29 eye-dial was (26,-4); the derivation confirmed it to 1-2px and
replaced it. **Nothing in the project is hand-dialled any more.** Needs one
eyes-on confirm next session (a 1px right + 2px down shift vs the approved
look).

**The padding theory recorded here earlier was WRONG.** No in-game dump was
needed either — the atlas is plain DBPF art. What the measurements showed:

1. The source atlas is **292x53**, on disk as
   `T-856ddbac G-1abe787d I-14215ed0..ed5` (six colour variants, ONE identical
   magenta mask; matches the live `DCTX area=(0,0,292,53)` trace).
2. The 80x53 sprite is a **KEYRING, not a padded circle**: an annulus on the
   left whose magenta **hole** (31x21 ellipse, centre exactly **(25,26)** by
   flood fill) frames the selected button, merging into a full-height connector
   wedge with **zero right padding** — so "close the right gap from padding"
   could never have worked.
3. The flyout button's visible **ellipse is off-centre in its 47x37 cell**:
   luminance bbox (1,0)..(41,30), centre **(21,15)** vs cell centre (23.5,18.5)
   (art `G-46a006b0 I-14215e40..42`, 4 states each, all identical). THIS
   (-2,-3) offset — not sprite padding — is why box-centre math was 4-5px off
   and the eye read the ring as "low".
4. Align **hole centre == ellipse centre** (all 2x screen px, buffer==screen;
   the 2x-pixel +0.5s cancel):

   ```
   SubRingDX = 2*ex - (nx + SubDockDX + rx + 2*hx) = 42 - (20-53+ 0+50) = 25
   SubRingDY = 2*ey - (ny + SubDockDY + ry + 2*hy) = 30 - (-86-24+94+52) = -6
   ```
   with (hx,hy)=(25,26) hole, (ex,ey)=(21,15) ellipse, (nx,ny)=(20,-86) the
   game's native container offset (SUBDOCK log), (rx,ry)=(0,94) ring dst (RCAL
   log). SubDock appears in the formula: **re-run the script after any SubDock
   change**.

Note: `I-14215edd` (same 292x53 dims) is a DIFFERENT sprite with no enclosed
hole — not the ring; if a menu ever draws its ring from it, re-measure.

## v2.16.0 (2026-07-29): THE SUB-FLYOUT PLACEMENT LAW (rails & depots fix)

**Symptom (user):** zones sub-flyouts perfect; Transportation fine until
"Build Rails & Depots" — its popout no longer circles the button. Log showed 5
distinct transport menus stuck at native while zones/roads docked.

**Diagnosis chain (measure, don't infer):** the failing containers sat at
native offsets from their buttons of −11/−37/−60/−82… — NOT the assumed −86.
One live RingCal pass on the rails menu gave ring dst **(0,119)** where zones
has **(0,94)**, and both menus then satisfied, with residual ZERO:

```
nativeY = buttonCentreY − ringBltY − 29        nativeX = buttonAbsX + 20
```

zones: 274 = 397−94−29 ✓   rails: 549 = 697−119−29 ✓

The game centres each menu's **1x ring sprite** on the button; ringBltY varies
per menu, so a constant native offset can never match them all. −86 was the
law evaluated at ringBltY=94. **Corollary: the dock delta (−53,−24) is
menu-invariant** — native and target both shift with ringBltY, so their
difference cannot depend on it. Nothing about the approved look changes.

**Code (three deltas, v2.16.0-sublaw):**
1. The sub-flyout ring 2x draw records `gSubRingBltX/Y` + buffer W×H.
2. The dock computes `natT = btnCentreY − gSubRingBltY − kSubPlaceBias(29)`
   instead of `bt − 86`, gated on the record matching the container's current
   size (blits fire every frame vs the 4×/sec sweep, so stale self-corrects).
3. `destIsContainer` height gate 300 → **260**: one transport menu is 258x286
   and below 300 its ring never got the 2x draw at all.

**Expected log:** `SUBDOCK 0x8A6E61E0 btn=0x… abs(…) ringY=119 native(178,549)
-> target(125,525)` — ringY new in the line. NOT yet eyes-on-verified.

## v2.17.0 (2026-07-29): SUBMENUS-MOD INTEGRATION (memo.submenus.dll 2.1.0)

The deep submenu system is a third-party DLL plugin
(`Plugins\memo.submenus.dll`, open source: github.com/memo33/submenus-dll,
cloned to `tools\research\submenus-dll-src`). Two 2x defects, both fixed
WITHOUT touching the mod (our DLL + art override only):

**1. Duplicated item icons** (e.g. the rails preview tiles). The mod binds
**55 Item Icon instances of its own** (property 0x8A2602B8 in its dats'
exemplars; all icons 176x44 4-state strips in the same dats) - outside the
stock 266 our ItemIcons-2x package covers. Un-overridden, the game slices the
1x strip by the DOUBLED 88px cell, so each cell shows TWO 1x states side by
side = "duplicated instead of stretched". Fix: extracted all 55, upscaled 2x
NN (the preview-set method) -> shipped as
**`Plugins\zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat` (55 entries)**,
tier-gated by ScaleTier like the root packages (v2.17.1).

**THE LOAD-ORDER LAW (proven live 2026-07-29, cost one failed deploy):**
within Documents Plugins, **root FILES load BEFORE subfolders** - a root
`z_*.dat` can NEVER override a dat inside a subfolder (the first attempt put
the 55 in the root ItemIcons dat = 321 entries; icons stayed duplicated with
it deployed). Overriding another Documents mod requires a FOLDER that sorts
after the target's folder ("zzz-SC4UIScale" beats "150-mods"). The root
packages still work because they override INSTALL-dir resources only. Root
ItemIcons-2x is back at **266** (stock pool only).
Rebuild recipe + sources: `tools\itemicons\_work\submenus-1x|-2x\`,
REPORT.md. Any future submenu pack with NEW icons repeats this recipe.

**3. (v2.17.1) 2-item nested menus missed by the size gate.** The "Freight
Train" sub-sub-menu's container is **258x206** - under both the original
`h>300` and the first widening to `h>260`, so its ring got no 2x, no blit
record, no law dock (1x disconnected circle). The sub-flyout path now keys on
the container's EXACT width: `destIsSubContainer = (selfW == 258 && selfH >=
100)`; the disaster path keeps the old heuristic untouched. Sizes observed so
far: 258 x 206/286/384/482/580/678/776/874.

**2. Dead back arrow.** The mod's "back" action is A CLICK ON THE PHYSICAL
MENU BUTTON (`Hook_HandleButtonActivatedReopen` in its source); the red
arrow is baked into its five 292x53 menu-frame atlases (0xAC581B70..74,
essentials dat) inside the ring-box wedge, measured (52,14)..(62,38) at 1x.
At 1x arrow art and button overlap - clicking the arrow WAS clicking the
button. Our 2x ring draw pushes the visible arrow just past the button's
right edge into dead space (proven: a whole session of arrow-clicking fired
DHIT136 twice). Fix (`[Flyout] ArrowClick=1`): claim the drawn arrow's rect
through the verified routing chain (container slot 121 `ContPt121Thunk` ->
strip slot 62) and at the strip's commit handler (136) synthesize a REAL OS
click (SetCursorPos + posted down/up, the touch DLL's proven input style) at
the selected button's centre. The centre is structurally outside the arrow
zone (btn+47 vs zone start btn+80), so no recursion. NOT yet eyes-on.

Also: `[0xe0]` must NEVER be widened for this (dual-use: claim width AND a
draw-side-halved Plot inset) - that is why the claim extension is a slot-121
thunk, not a field write.

## ✅ SOLVED 2026-07-29: EMERGENCY = the missed-art-pass case, NOT new hooks

The disasm of class 0x00ADF6A0's Plot (0x9BC325) ended the mystery: it is
**GZWinBMP**, and it draws its image with **dst = origin + srcWxH** (the
3-state branch divides src by 3 then draws via helper 0x8D8800). The draw
size FOLLOWS THE SOURCE IMAGE - so 2x art = 2x draw, no code hook. The
"panel" 0x2992FD21 is the flyout's ring/frame BITMAP
(image={46a006b0,14215e2c}, imagerect 114x270) - and Emergency was simply
the LAST mayor flyout never added to the selective-safe builder (identical
symptom + identical fix as Zones/Transport/Utilities on 07-28: "1x art + 1x
imagerect inside a correctly-placed 2x window draws the ring at half size
in the wrong band"). FIX: 0x0992FD17 added to SCALED_WINDOW_IDS ->
SelectiveArt regenerated at all three factors = **271 entries** (+7).
LESSON, again: before treating a flyout bug as a NEW mechanism, check
whether the window ever got its art pass. NOT yet eyes-on.

## (superseded by the above) probe notes from the same day

`0x0992FD17` (mayor Emergency Tools, 308x840, docks at (22,542) via predicted
marker (3,234) — live marker confirmed (6,468) 100x80). Its picture panel
`0x2992FD21` (496x636 at (0,2)) is **class vtable 0x00ADF6A0** — NOT the
disaster container (0x00AB6AA8), NOT the strip (0x00AB6D88); EBLT proved ZERO
blits through the hooked buffer class (0x00AC1400) while open, so it paints
through a DIFFERENT buffer path. Buttons (5x 94x74, class 0x00ADDAF0) scale
fine. Symptoms: 1x dithered dispatch pictures in the panel; its thin red ring
drawn far from the Emergency toolbar button. FIX PATH: the offline-disasm
playbook on class 0x00ADF6A0 (vtable from the exe on disk): enumerate slots,
find the draw group + buffer + blit, then hook like the disaster strip.
Instruments: ini `[Flyout] EmergLog` (EVTP child-class dump + EBLT blit log).

**Vtable seed for the disasm (dumped from the exe 2026-07-29, imagebase
0x400000, vtable file offset 0x6df6a0).** The class follows the FAMILY SLOT
LAYOUT — same lever slots as the disaster classes:
- slot 87 GZPaint = 0x0099BE4C (base), **slot 88 Plot = 0x009BC325 (OVERRIDE)**
- slots 136/138 mouse = 0x009BC2D0 / 0x009BC27C (overrides, the click-fix slots)
- slot 121 = 0x0099C8F5 (base), slot 133 = 0x0093878E, slot 149 = 0x0099BBBE
- draw group 87..97: 0099be4c 009bc325 0099ba07 0099dce4 0099becc 0099bed1
  0099bef9 0099befd 0099c6f8 0099d57e 0099cf6a
- Plot 0x009BC325 calls: 005e5620 008d8800 0093878e 0099bc31 0099bdf3
  0099be0a 0099c2c3 0099cf49 0099d938 0099db6b 009bc2fa 009bc447; refs its
  own vtable cluster 0x00ADF63C/66C/6A0. NO buffer-class constant in its
  first 0x500 bytes -> buffer comes via the shared base helpers (0x0099cf49 /
  0x0099d938 / 0x0099db6b are the candidates). EBLT proved the buffer is NOT
  the hooked class 0x00AC1400 (gEmergLog active from DLL load; panel painted
  at open; zero hits).
- PLAN (the lessons, in order): (1) capstone the Plot + the three helpers to
  find the buffer class + its Blt slot; (2) permanent class-Blt patch on THAT
  class (BltClassThunk pattern, gated by panel size 496 wide); (3) Plot-hook
  force-recreate via a THIRD vtable copy (gVtCopy3) on 0x00ADF6A0 slot 88;
  (4) item-field doubling if pictures unseat (DSCROLL-style field dump
  first); (5) ring = intercept its ring blit in the new Blt hook (the thin
  red circle), derive offsets from art the way the sub-flyout ring was done;
  (6) every lever ini-gated, defaulting to today's behaviour.

Also OPEN: tooltip boxes size for 1x text while the font is 2x (text clips/
overflows). New surface — the transient tooltip window; find via DPROBE while
hovering. (Task #41.)

## The sub-flyout, fully explained (every value has a cause)

Container `0x8A6E61E0`, shared by EVERY tool's second-level menu (seen at
258x482, 258x384, 258x874, 258x776, 258x580 - it resizes per content, so it must
never get a per-tool constant).

| Symptom | Cause | Fix |
|---|---|---|
| Wrong position | generic sweep took `ScalePanelRoot`'s left/top edge branch and DOUBLED its coords from the screen origin (178,274)->(356,548) | `IsSubFlyoutId` skips it in the sweep |
| Not tracking the selected item | - | game places it at `selectedButtonAbs + (20,-86)` (MEASURED: btn(158,560)+(20,-86) = live (178,474)) |
| Ring not on the button | 2x ring needs the whole assembly moved | dock to `btn + (-33,-110)` = native + (-53,-24), derived: `ring centre = container + (0,94) + (80,53) = btn + (100,61)`, `button centre = btn + (47,37)` |
| Bar 1x | stale 1x paint buffer | `gForceRecreate` (Disaster's fix - SAME class) |
| Icons not seated | strip item fields 1x | `gStripFieldScale=2` (Disaster's fix) |
| Bar clipped to a sliver | `gBarDX=-53` is GENERIC not disaster-specific: bar art is 53 wide drawn FLUSH RIGHT (buf 258, dst x 205..258); widening 2x without the shift overruns by 53 | never gate `gBarDX` |
| Circle 1x | Disaster's ring upscale tests `sw > 80`; this sprite is EXACTLY 80 wide so it missed by one pixel | range widened to 70..140 x 35..100, gated `!gDisasterDrawTuning` |
| Circle moved when scaled | v2.15.0 scaled the ring ORIGIN too | scale SIZE only; origin stays, plus SubRingDX/DY |
| Only right half clickable | container's custom `IsPointInMe` claims only rightmost `[this+0xe0]` px, still 1x | `ClaimScale=2` + `SelForce=1` - the gates INTERSECT, both required |

`gDisasterDrawTuning` gates ONLY the disaster-measured ring offsets
(RingDX/RingDY). It must NOT gate `gBarDX`/`gBarWiden`, which are generic.
It is set 0 when the sub-flyout container is hooked and 1 for disaster; they are
never live simultaneously (god vs mayor mode).

**Class identity (SVT probe):** sub-flyout container = `0x00AB6AA8` and its strip
child = `0x00AB6D88` - byte-identical to the Disaster flyout, which is why all of
Disaster's fixes applied verbatim and no new reverse-engineering was needed.
Sharing `gVtCopy`/`gVtCopy2` is safe here BECAUSE the class is identical; the
"one window only" warning in the code is about hooking DIFFERENT classes.

## Instruments built this session (all ini-gated, all still in the build)

| Log tag | ini key | What it answers |
|---|---|---|
| `MCAL` | `[Flyout] MayorDock=0` | flyout native pos, spawn-button abs, derived R, target |
| `SCAL` | (automatic) | sub-flyout vs open parent flyout and every button in it |
| `SVT` | (automatic) | concrete class vtables - is this the Disaster class? |
| `SBLT` | `[Flyout] SubBltLog=1` | EVERY blit into the sub-flyout buffer, unmodified src/dst |
| `RCAL` | `[Flyout] RingCal=1` | ring-sized blits + dest buffer - painted art or window art? |
| `DPROBE` | `[Probe] Enabled=1` + band | change-triggered geometry, catches transient windows |
| - | `_tests\Audit-UnscaledWindows.py` | finds every missed/double-scaled window from data |

## THE METHOD THAT WORKED (and the one that did not)

**Every time a value was MEASURED it landed first try:** the `MCAL` dock pass,
the alignment-marker rule, the `SVT` class probe, the `SBLT` bar trace, the
`RCAL` ring identification, the container-dock arithmetic.

**Every time a value was inferred from a screenshot it cost 2-3 builds**, and
twice it broke something that already worked (terraform shifted twice by a mode
test verified in only 2 of 3 states; the minimap was covered by a panel moved on
an assumption). The project notes already said this - "~15 build cycles",
"burned many hours and never converged" - and it repeated anyway.

**Practical rule:** if two symptoms contradict (centre it here / attach it
there), you are at the wrong LAYER - move up one level. That is exactly how the
sub-flyout ring resolved: the ring was never what should move, the container was.

# City-mode UI scaling backlog (2026-07-23 user pass)

## ★★ THE ALIGNMENT-MARKER RULE (2026-07-28) — how SC4 places EVERY flyout

The single most useful thing found in this phase. It ends offset-guessing.

**Every tool-flyout .UI script contains a hidden child `id=0x0000AAAA` whose
size equals its SPAWN BUTTON's size.** The game positions the flyout as:

```
flyoutPos = spawnButtonAbs - markerOffset
```

so once we have scaled the subtree to 2x, the correct dock target is:

```
target = spawnButtonAbs - markerOffset(LIVE, already scaled)
```

Equivalently, with `R = nativePlacement - spawnButtonAbs` ( = -marker at 1x ):

```
target = spawnButtonAbs + f*R        <- what kMayorFlyoutDock stores
```

**Why it is trustworthy — three independent confirmations:**
1. It reproduces ALL THREE locked, hand-tuned GOD docks to the pixel:
   terraform (22,262), terrain-fx (22,502), day/night (22,742). Those took
   ~15 build cycles to find by eye; the rule gets them first try.
2. It predicted the game's native mayor placement exactly: Landscape marker
   (3,27), button abs (28,398) -> (25,371) = what MCAL measured in game.
3. Two separate derivations agreed on (22,344) for Landscape - `button + 2R`
   and `button - marker2x`.

**It also explains the one thing the constant table needed a special case for:**
the shared window 0xCA35CBED needs two offsets (terrain-fx 40 / day-night 160)
because swapping SCRIPT moves its marker. The rule handles that automatically.

**TRAP: one window id can have TWO scripts.** `0x49923239` is god/terraform
(125x291 -> 250x582, marker (4,90)) AND mayor/Landscape Tools (125x249 ->
250x498, marker (3,27)). A single fixed offset can never serve both - the
mayor-mode gate is what separates them.

### The mayor toolbar map (measured, buttons identified by POSITION)

The live dump enumerates children in REVERSE of .UI add order
(CITY-DOCK-OVERLAP.md 1.2), so NEVER identify a button by enumeration order -
use its y position. Toolbar root 0x69E40A1F, live (8,364) 314x976.

| # | Button | live abs | Flyout | Flyout id | marker(1x) | derived target |
|---|---|---|---|---|---|---|
| 1 | 0x8991EE08 | (28,398) | Landscape | 0x49923239 | (3,27) | (22,344) ✅ |
| 2 | 0x0991EE13 | (28,498) | Zones | 0x69923479 | (3,77) | (22,344) ✅ |
| 3 | 0xA994824D | (28,598) | Transportation | 0xC99237A0 | (3,77) | (22,444) ⬜ |
| 4 | 0xE991EE2F | (28,698) | Utilities | 0xE992F711 | (3,77) | (22,544) ⬜ |
| 5 | 0x0991EE39 | (28,798) | Civic | 0x699306ED | (3,227) | (22,344) ⬜ |
| 6 | 0xE999C820 | (28,922) | Bulldoze | (none) | - | - |
| 7 | 0x6991EE42 | (28,1010) | Emergency | 0x0992FD17 | (3,234)* | (25,776)* |

✅ user-verified   ⬜ derived + shipped, not yet verified   * predicted, never
opened in any capture.

Note 1+2 both land at (22,344): each flyout's marker sits lower by exactly the
button pitch, cancelling out. That is the rule being self-consistent.

### The SHARED sub-flyout container 0x8A6E61E0 (second-level menus)

The strip that opens when you pick a tool INSIDE a flyout (zone density, road
types...). Facts, all measured:

- It is a **direct child of the 3D view**, not of the flyout that spawned it,
  so it inherits nothing from that flyout's dock.
- It is **SHARED by every tool** - seen at 258x482, 258x874, 258x776, 258x384,
  258x580, resizing per content. NEVER give it a per-tool anchor: that fixes one
  tool's sub-menu and breaks the other four.
- It has **NO 0x0000AAAA marker**, so the marker rule cannot supply an offset.
- **Position:** the game places it correctly from LIVE window positions (it
  already accounts for our docked parent). Our only error was the generic sweep
  DOUBLING its coordinates from the screen origin (178->356, 274->548). Fix =
  skip it in the sweep, size it, do NOT move it. USER-CONFIRMED correct.
- **Class:** container = 0x00AB6AA8 and its strip child = 0x00AB6D88 - the SAME
  concrete classes as the DISASTER flyout (proved by the SVT probe). So the
  disaster draw fixes apply verbatim: `gForceRecreate` (stale 1x buffer) and
  `gStripFieldScale` (item size/spacing). No new RE was needed.

**`gBarDX = -53` is GENERIC, not a disaster tweak** - the SBLT blit trace
settled this after three failed screenshot iterations. The bar art is 53px wide
and the game draws it FLUSH AGAINST THE RIGHT EDGE of the container buffer
(sub-flyout: buf 258 wide, bar dst x = 205..258). Widening 2x without shifting
puts it at 205..311, i.e. 53px past the buffer end, so the bar clips to a sliver
and the icon strip (x 160..248) no longer overlaps it. Shifting left by exactly
one bar width keeps it flush: 152 + 106 = 258. Do NOT gate this per-window.

**STILL OPEN on this container (2026-07-28):** bar reads slightly too far left
and the ring/circle is not 2x-covering. Next step is NOT another constant tweak
- re-enable `[Flyout] SubBltLog=1` and read the SBLT trace, which gives every
src/dst rect in call order. Three screenshot-driven builds failed here; one
trace found the real cause immediately.

### Two code paths, know which one a flyout uses

- **Landscape 0x49923239** is in `kGodToolFlyoutIds`, so the sweep skips it and
  `ScaleGodFlyouts`'s god loop handles it; the mayor entry overrides the anchor
  while `mayorModeActive`.
- **Zones / Transport / Utilities / Civic** reach NEITHER the god loop nor
  `ScaleMenuFlyouts`. They fall through to `ScalePanelRoot`'s **CENTER-ANCHOR**
  branch (fires when gapT and gapB both exceed frameH/4), which repositions them
  with no reference to the spawn button - zones landed at y=241 because
  `421 + 180 - 360 = 241`. They are flagged `mayorOnly` so the sweep skips them
  and the mayor loop docks them.

### Measuring a new flyout (do this, do not eyeball)

1. ini `[Flyout] MayorDock=0` - mayor flyouts are scaled but never MOVED.
2. Open the flyout in game, quit.
3. Read the `MCAL` line: it prints native pos, spawn-button abs, the derived
   `R`, and the target that `R` would produce.
4. Paste `R` into `kMayorFlyoutDock`, set `derived=true`, `MayorDock=1`.

## ⚠️ 2026-07-28 (v2.12.x) — MAYOR MODE PHASE OPENED. READ THIS FIRST.

God mode (pre-founding) is COMPLETE - see HANDOFF-god-mode-flyouts.md. The
FOUNDED-CITY paths are a different, largely untested surface, and the first
thing found there was a hard blocker.

### ✅ FOUNDED-CITY GOD MODE FIXED (v2.12.2, USER-CONFIRMED 2026-07-28)

"god mode loads correctly now - tested all 4 fields and they all worked."
TWO separate windows had to be fixed, and BOTH had the SAME root cause.

**THE PATTERN (expect it again - this is the Mayor-mode trap):** every
"hidden" / "never-visible" / "frozen template" / "docking it changes nothing"
note in the god-mode research was measured BEFORE a city was founded. Several
of those windows BECOME LIVE once a city exists. A note that was accurate when
written is not evidence about the founded-city path.

**#2 - `0x0A78827A` = THE FOUNDED-CITY GOD TOOLBAR** (Obliterate City /
Reconcile Edges / Disaster / Day-Night).
- **Symptom:** god mode showed only clipped fragments at the far left edge.
- **The code said, in as many words:** "a HIDDEN god sub-tool strip ...
  Docking/scaling it changes nothing on screen. **Do not re-add this id.**"
  It was in `kGodToolFlyoutIds`, which makes the city sweep SKIP it outright,
  so it rendered at dead stock 74x291 at (5,1071) - and (5,1071)..(79,1362) is
  exactly where the "fragments" were.
- **What identified it:** a STOCK founded-city capture via
  `_tests\Set-StockCompare.ps1`. Stock god mode is COLLAPSED BY DEFAULT (so
  that is NOT a bug), and its expand tab reveals exactly four tools -
  Obliterate/Reconcile/Disaster/Day-Night - which is precisely the button list
  in `0x0A78827A`'s script `I-aa53e3ea`. The four buttons NAMED the window.
- **FIX:** removed from `kGodToolFlyoutIds`, added to `kGodPanelIds`.
- Dock target was already on record from 2026-07-24 ((5,1071)->(10,542)) and the
  panel transform reproduces it: 2*5=10, 2*1071-1600=542. Log confirms
  `panel 0x0A78827A (5,1071 74x291) -> (10,542 148x582)`.

**LESSON - `_vanilla-reference/FINDINGS.md` HAS NO FOUNDED-CITY DATA.** It was
captured pre-founding at 1280x1024. When a founded-city window misbehaves and
there is no stock reference, RUN `Set-StockCompare.ps1` FIRST. It cost one
relaunch and answered three questions at once (is it stock behavior / does the
control work in stock / what does correct look like). Guessing from
screenshots burned far longer and produced two wrong theories.

### FIXED v2.12.1 - "God Mode never loads, the entire UI stays crushed"

- **Symptom:** in a FOUNDED city, switching to god mode showed almost no UI -
  a few clipped fragments at the left edge, no tool rail.
- **How it was identified (geometry layer, one log line):**
  `id=0xABB26B0E pos(3,1045) size(314x976) vis=0`. Stock rect is
  (3,1045) 157x488, i.e. BOTTOM-anchored. It had been doubled to 314x976 but
  never moved, so it ran y=1045..2021 on a 1600px screen - **421px below the
  bottom edge**. What rendered was the sliver that fit.
- **Root cause = a stale ASSUMPTION, not broken machinery.** The id sat in
  `kSizeOnlyIds` (scale, never move) because a 2026-07-24 note called it "a
  frozen hidden template at Y1045" that day/night merely rode on. That is TRUE
  before a city is founded and FALSE afterwards, when 0xABB26B0E is the panel
  god mode actually shows (its two live 148x116 god buttons are in the dump).
- **FIX:** moved to `kGodPanelIds` (bottom-anchored panel transform + scaled BY
  ID even while it reports vis=0, the twin quirk) and REMOVED from
  `kGodToolFlyoutIds`, which had been making the city sweep skip it entirely.
  `kSizeOnlyIds` and its loop are deleted.
- **Why that target is right (derived, not eyeballed):** the panel transform
  `y' = f*y - (f-1)*frameH` gives 2*1045-1600 = 490 -> **(6,490)**, which is
  exactly the dock position recorded for this same id on 2026-07-24. Its twin
  0x69E40A1F has the IDENTICAL stock size (157x488) and already renders right
  through this path.
- **LESSON (expect more of these):** every "hidden/never-visible/template"
  claim in the god-mode notes was established PRE-FOUNDING. Re-verify each one
  against a founded city before trusting it.

### Open, diagnosed, not yet fixed (from the same session)

| Item | Evidence | Layer | Planned fix |
|---|---|---|---|
| News reader `0xAA231508` renders 1x + visual error | `pos(260,348) size(880x456)` = dead stock, but **vis=0 while visibly drawing** -> the sweep's visibility gate skips it | window tree (+ art mismatch) | scale by id even while hidden (the `kGodPanelIds`/`kRegionPanelIds` lesson); the "visual error" is 2x art in a 1x frame and should resolve with it |
| News ticker `0xCA2AEDC0` content stays 1x | container `1514x86` = EXACTLY 2x of stock 757x43 (root-only scale worked), but child `0x6A2AEDCA` is still `757x43` | draw/child layout | the `kRootOnlyScaleIds` premise (cSC4WinAdviceList re-lays children to the container each frame) does NOT hold for that child - needs a look at who owns its size |

## SECTION-BY-SECTION PLAN (user directive 2026-07-23)
Finish each MODE completely before moving on, exactly like the region screen:
**GOD MODE (now) -> MAYOR MODE -> SIM MODE (My Sims) -> OPTIONS -> ...**
When God mode is SOLVED, the mechanics carry to every other page.

## THE METHOD (user, verbatim intent, 2026-07-23) - governs all city-mode work
NORTHSTAR = EVERYTHING SCALES. No stock "baselines" as an end state - stock
is only ever a temporary dev step. Work in THREE ordered phases per section:
  1. FOUNDATION / MECHANICS - make it scale to 2x at all (the machinery).
  2. FLOW - make it all POSITION/anchor correctly (dock flyouts to buttons,
     no overlap, right place) - the Region kRegionDialogDocks lesson.
  3. LOOK - make it PERFECT (2x art for every button/icon; no 1x-in-2x).
Do NOT jump to art before the mechanics+flow are right. Do NOT ship stock as
"done". Draw directly on the REGION solution (whitelist scale + flyout
docking + pre-scale-hidden + center/clamp anchoring + static dialogs).

## GOD-MODE EXECUTION (this is the active work)
- Confirm/message boxes: DONE (static-double; Obliterate + Reconcile x3).
- Tool UI (toolbar 0xC991EDA8 + flyouts 0xCA35CBED terraform / 0x49923239
  terrain-fx / 0x0A78827A disaster / day-night / water / trees):
  Phase 1 FOUNDATION - they DO scale via the sweep (proven: 74x351->148x702
    toolbar, etc.). So re-ENABLE scaling (remove the temporary kNeverScaleIds
    baseline for these) - the machinery exists.
  Phase 2 FLOW - the sweep's edge-anchoring mis-positions the flyouts
    (day/night "right size wrong place"). BUILD god-mode flyout DOCKING:
    after scaling, anchor each flyout to its scaled spawn button (the toolbar
    button that opens it), like kRegionDialogDocks. Need flyout->button map.
  Phase 3 LOOK - the round tool-button art is code-bound 1x in 2x slots
    ("not a circle"). Same-TGI 2x art overrides (ItemIcons-style).



First city-mode review after the region screen was completed. The user
walked the whole city HUD at 2x (native 2400x1600) and surfaced the issues
below. This is the working backlog for task #36. Categorized by FIX
MECHANISM (the region-screen work proved which mechanism each class needs).

Base state: SC4UIScale v2.7.5-windowed, tier 2.00 active. City HUD runtime
scaling was PARTIALLY deployed during the region phase (v2.5.x: kRegion*,
ItemIcons, code-bound art, rating patch) but never iterated to completion --
that is this task.

## The "jump" / "loading time" signature == runtime scaler catching late

Several reports ("loading time between pages", "Route Query does the jump",
"day/night has a weird loading jump when first selected") are ALL the same
root cause: the floating window appears at 1x, then the ~250ms UiSpike tick
runs ScaleSubtree and doubles it -- the user SEES the 1x->2x pop. The
region-screen CURE was to STATIC-double the .UI script so the game builds it
pre-doubled (no runtime scaling, no jump). Applying that cure to the
city-mode floating windows removes both the jump AND the wrong size at once.

## Backlog items

| # | Report | Mechanism | Script / control | Status |
|---|---|---|---|---|
| 1 | Mini map broken | code-bound custom draw | cSC4WinMiniMap clsid 0xca318388 | RESEARCH |
| 2 | Loading time clicking between toolbar Pages; + on FIRST city open the HUD/menus are absent/tiny until forced to redraw (user 2026-07-23) | runtime scaler late / arm timing | toolbar page panels + initial HUD arm | RESEARCH (tick/arm) |
| 3 | My Sims screen a mess | CODE slot-pitch hook | 0x698894D3 (ITEMICONS.md Q3) | RESEARCH/HOOK |
| 4 | Mayor info/query box small + floating | static .UI dialog | building query (Make Historical) | **DONE** (whole 117-panel family) |
| 5 | God-mode boxes small, border box too small | static .UI dialog | god tool panels | TODO |
| 6 | Disaster Window a mess | static .UI dialog | disaster picker | TODO |
| 7 | Day/Night window misaligned (blue ring off the circle) + jump | static + art | aura/day-night control | TODO |
| 8 | Query Clicker compressed | == #4 (same building query) | building query | **DONE** (== #4) |
| 9 | Route Query does the jump | static .UI dialog | Trip Types / route query | TODO |
| 10 | Minimized panel restore button (btm-left) super small | runtime scale / art | restore/minimize control | RESEARCH |

## Candidate scripts found (grep, 2026-07-23)

- Obliterate confirm: I-2a41436c, I-aa53e3ea (aa53e3ea also matches
  day/night grep -> likely a god-mode tool cluster script)
- Boundary "already match" msg: I-0a4d0c43 (this is the generic message box
  path already doubled? verify -- the screenshot showed it 2x-ish)
- Building query (Make Historical): I-2a567dc1, I-4a5672bf, I-ca56783a
  (three sizes/variants -- residential/commercial/civic query panels)
- Trip Types / route query: I-0b72f276, I-2bc9060f, I-abb0120f
- Disaster: I-0a41be3e, I-0a41be3f, I-4a89b3f2, I-69e3d347, I-899302fc,
  I-a991ed83 (+ 08000600-group 800x600 twins)
- Day/night / aura: I-69e3d347, I-aa356502, I-aa53e3ea
- 81 scripts total contain a "Close" button (many are query panels)

## Fix order (proposed)

1. STATIC-DOUBLE the floating query/tool windows (proven region pipeline):
   building query (#4/#8), route query (#9), disaster (#6), god tools (#5).
   This kills the size AND the jump together. Verify each variant.
2. Day/night (#7): static-double + check the blue-ring art (code-bound
   aura BMP may need a 2x override like the rating groove).
3. Mini map (#1), My Sims (#3), restore button (#10): code-bound /
   code-hook -- research pass (disasm), likely byte patches like the
   Mayor-rating imul and the My-Sims slot pitch in ITEMICONS.md Q3.

## ARCHITECTURE FINDING (2026-07-23, from UiSpike.cpp + script census)

The city-mode scaler (`ScalePanelsUnder(pView,"city")`, UiSpike.cpp ~449)
walks the DIRECT VISIBLE CHILDREN of SC4View3DWin (0x9A47B417) and runs
ScalePanelRoot on each. So the runtime path DOES reach the floating query/
tool windows -- which is why they "jump" (born 1x, next ~250ms tick doubles
them). But in the screenshots they look COMPRESSED/SMALL, not cleanly 2x ->
the runtime scale is reaching the frame but NOT producing a correct result
(the query CONTENT is code-repopulated with live data, likely fighting the
scaler the way the ticker/AdviceList did -- DYNAMIC-CONTROLS.md).

CONSEQUENCE: the region-screen static-double recipe does NOT drop in cleanly
here, because:
  1. The building query family shares ONE template root id 0x10000005 across
     **117 scripts** -- can't exclude by id from the runtime sweep.
  2. If a script is static-doubled AND the city sweep still catches its root,
     it gets DOUBLE-scaled (2x -> 4x). Region dialogs avoid this because the
     region pass is WHITELIST-ONLY (isRegionPass && !IsRegionPanelId ->
     skip); the CITY pass is the opposite -- it scales everything visible
     that isn't explicitly excluded.

So city-mode floating windows need EITHER:
  (a) a city-pass exclusion mechanism (scale nothing that a static dat
      already doubled -- e.g. tag by a sentinel, or a kCityStaticDialogIds
      list checked in ScalePanelsUnder), THEN static-double the scripts; OR
  (b) FIX the runtime ScalePanelRoot so it doubles the query panels
      correctly (handle the code-repopulated value fields) -- no dat needed.

Option (a) is the proven-mechanism path (matches region) and is more
predictable; (b) is less data but re-opens the runtime-scaling-quality
rabbit hole. LEANING (a).

RESOLVED 2026-07-23 by the LiveDumpMs diagnostic (SC4UIScale v2.7.6): the
building query panel is a child of the MAIN WINDOW (parent 0x00000000), a
SIBLING of the app window -- NOT under the view and NOT under the app window
(app window holds ONLY the view). So the city sweep NEVER reaches it: it
renders at pure 1x stock (root 292x334, rows 175x18). That makes
static-doubling COLLISION-FREE (option (a)), and the earlier double-scaling
fear is void. The whole 117-panel query family (root 0x10000005 + 0x89e1567c
container) is auto-discovered by build_dialog_static.py:discover_query_family
and static-doubled -> DialogStatic 195 entries. Residential query
("Stone Chateau") user-confirmed 2x clean 2026-07-23.

The live-dump diagnostic (LiveDumpMs=6000) is STILL ON for diagnosing the
remaining buckets (god tools, disaster, day/night, mini-map, My Sims,
restore). Turn it to 0 before the final city-mode ship.

## GOD-MODE + NEWS findings (2026-07-23 live dump)

| Panel | Runtime id | Script(s) | Parent | State | Fix |
|---|---|---|---|---|---|
| Obliterate City / Reconcile Edges confirm | 0x27DF05BE (339x200) | I-2a41436c, I-6a9455c9 | MAIN window | 1x stock | STATIC-DOUBLE (main-window child, sweep-safe, like queries). NOTE: a SEPARATE msg-box template from the generic ea8cc3c6 - that's why doubling ea8cc3c6 didn't fix these. |
| Disaster picker flyout | 0x0A78827A | I-aa53e3ea | VIEW child | **IS scaled 2x** (log: 74x291 -> 148x582, 7 windows) - NOT a sweep-skip. The "mess" must be the disaster THUMBNAIL ART at 1x in the 2x button slots (code-bound art, like ItemIcons/TrendBar) OR strip layout. FIX: find disaster preview art TGIs -> 2x overrides. Confirm with user what's "messy". |
| Day/Night control | 0xEBB16D71 (450x450) | I-2bb16d50 | MAIN window | 1x | verify parent; if main-window -> static-double + check the blue-ring aura art (code-bound). |
| News window (reader) | 0xAA231508 (880x456) | I-2a2aed99 | VIEW child | 1x | cSC4WinAdviceList (code-populated rows, DYNAMIC-CONTROLS.md) - root-only scale + font, NOT a plain static-double. The ticker strip 0xCA2AEDC0 is the sibling marquee. |

So the god-mode/news bucket splits: the CONFIRM box (0x27DF05BE) is a clean main-window static-double (fixes Obliterate + Reconcile at once); the disaster flyout / day-night / news window are VIEW-level and need runtime-sweep work (why does the city sweep leave these visible view-children at 1x?).

## ✅ GOD TOOLBAR SOLVED (2026-07-24, USER: "GOOD JOB!!! That also fixed
## the art for every Clickable menu")

The complete causal chain, for reuse on every later section:
1. TWINS: the god toolbar always double-draws (0x69E40A1F stock-layout
   panel + 0xC991EDA8 tile strip, both from scripts I-a991ed83/I-69e3d347
   sharing root id 0xC991EDA8). Roots report vis=0 while children draw ->
   the visibility gate skipped them -> scale BY ID even while hidden
   (kGodPanelIds, the kRegionPanelIds lesson). v2.7.14.
2. FLYOUT ROOTS have the same vis=0-quirk -> ScaleGodFlyouts drops the
   IsVisible gate; DOCK = toolbarLive + f*(flyoutStock - toolbarStock)
   using the toolbar's ScaleRecord origL/T (v2.7.15). Disaster + day/night
   dock EXACTLY ((5,1071)->(10,542), (3,1045)->(6,490)).
3. GHOST SUN = end-cap art {46a006b0,14415870} on window 0x00000001: the
   WINDOW scaled correctly; the ART was 1x anchored top-left because the
   god scripts weren't in selective-safe's SCALED_WINDOW_IDS (shared art
   got cloned for the flyout, ORIGINAL left 1x). Fix: add 0xC991EDA8 +
   0x49923239 + 0xABB26B0E to SCALED_WINDOW_IDS -> god cluster art 2x in
   place (SelectiveArt 215->240, all factors). This ALSO fixed the art of
   every clickable god menu (user-confirmed).
DIAGNOSTIC that cracked it: the 1s live full-tree WATCHER + user toggling
the menu (diff consecutive dumps), + abs-position queries. Also caught: the
game RESETS UI to stock on every mode/menu toggle (status bar 476x43 ghost,
toolbar pages 40x36) and the sweep re-scales ~1s later = the "loading
time" / "first-open small" bugs (fix idea: tighten sweep interval or hook
the toggle).

REMAINING in god mode: terraform 0xCA35CBED + terrain-fx 0x49923239 dock
fires on MID-ANIMATION captures ((26,352)->(52,-896) = off-screen) ->
guard: skip dock when target lands outside the frame; catch the resting
frame instead. Then full god-mode verification pass.

## GOD-MODE TOOL UI: BASELINE = STOCK (v2.7.7, user choice 2026-07-23, superseded)

The runtime sweep scaled the god-mode tool UI to 2x but its HUD-panel
edge-anchoring MOVED the flyouts to the wrong place and distorted the round
tool buttons (user: "not a circle / duplicated / wrong place", day/night
"right size wrong place"). Per user "correct baseline first", these roots
are now in kNeverScaleIds -> render STOCK (correct-but-small):
  0xC991EDA8 god toolbar, 0xCA35CBED terraform flyout, 0x49923239
  terrain-effect flyout, 0x0A78827A disaster flyout, 0xEBB16D71 day/night.
Confirmed by log: sweep was doing 74x351->148x702 (toolbar), 125x231->
250x462 (terraform), 125x291->250x582 (terrain fx), 74x291->148x582
(disaster) with wrong re-anchor.

PROPER FIX (deferred, follow-up): region-style flyout DOCKING (scale SIZE +
anchor each flyout to its spawn button, like kRegionDialogDocks) PLUS 2x
tool ART (below). The confirm/message boxes stay fixed (main-window
static-double); only the TOOL flyouts/toolbar are baselined to stock.
NOTE: if any god-mode flyout still mis-scales (water/trees tools not yet
seen), grab its root id from the live dump and add to kNeverScaleIds.

## GOD-MODE TOOL FLYOUTS = frame scaled, ART is 1x (the "mess") — 2026-07-23

The god-mode terraform / disaster / day-night TOOL flyouts (left toolbar)
are a distinct bucket from the confirm boxes. Live dumps show the FLYOUT
FRAMES ARE scaled 2x by the runtime sweep (disaster 0x0A78827A: 74x291 ->
148x582; terraform flyout 0xCA35CBED: 250x462), but the BUTTON ART inside
(terrain-pattern tiles, grayscale disaster thumbnails, sun/moon icons, brush
tools) renders at 1x -> small/garbled art in doubled slots = the user's
"mess". This is the SAME class as the toolbar ItemIcons and the TrendBar
art: code-bound button art that a plain frame-scale can't touch.

FIX (a research + generation pass, like ITEMICONS.md, NOT a quick win):
  1. Disasm the god-mode tool-button art binding (which art group/TGIs the
     terraform/disaster/day-night buttons load). Expect a pattern like the
     ItemIcon `{0x856DDBAC, <group>, <inst>}` assembly.
  2. Confirm 2x upscales exist (the upscale preview set may already cover
     them) and pack an override dat at the same TGIs.
  3. Re-test; the doubled slots then show doubled art.
The god-mode tools are the most art-dense UI in the game -> treat as its own
focused sub-effort within task #36.

CONFIRM BOXES (main-window children) - fixed incrementally as found:
  Obliterate (2a41436c), Reconcile x3 (0a4d0c43/ca4d0b22/8a4d0a17). The
  Reconcile "highlighted areas" variant was squished because only one of the
  three root-0x6a4d0a59 variants had been doubled; all three now done.

DAY/NIGHT (0xEBB16D71): flyout scaled but blue selection RING art likely
code-bound (aura-style) - same 2x-art fix + verify the ring registration.

## Notes

- City HUD .UI scripts are group 0x96a006b0 (+ 0x08000600 800x600 twins).
- The god-mode tool windows + disaster picker MAY be transient dialogs
  parented off the god toolbar (NOT pView) -> if so the city sweep misses
  them and they ARE clean region-style static-doubles. Verify parentage per
  window before choosing mechanism.
- Day/night "blue ring off the circle": the ring is almost certainly
  code-bound aura art (like the Mayor-rating groove) -- 2x override its TGI,
  don't just scale the frame.
