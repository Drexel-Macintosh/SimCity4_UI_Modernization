# SC4 UI-Scaling — TEST SCENARIO MATRIX

Written 2026-07-29 after a session where **five separate bugs were each caused
by an untested scenario axis**, not by bad code. This file exists so the next
session tests the axes instead of rediscovering them.

`REGRESSION.md` = the suites and per-fix expectations ("is it still right?").
**This file = the SCENARIOS those suites must be run under** ("right under
what conditions?"). Read both before believing a fix is done.

---

## Why this file exists — the five that bit us

Every one of these passed in the scenario it was built in, and failed in
another:

| Bug | Passed in | Failed in |
|---|---|---|
| God-mode flyout offsets | pre-founding god mode | **founded city** (different toolbar, 100px vs 120px pitch) |
| Advisor faces quarter-zoomed | any RE-open of the panel | **first open per city load** (3D heads framed at bind time) |
| Airport strip icons 1x | second and later opens | **first open** of that menu |
| Submenu icons duplicated | our root package alone | **another mod present in a subfolder** (load order) |
| Building Style Control corrupted | stock script | **a mod replacing that script AND its art** |
| Ticker headline wrapped | one sweep after scaling | **the next frame** (game re-imposes cached geometry) |
| Disaster thumbnails tiny (v2.39.0) | every window still owned by the sweep | **the one window we moved to born-at-Place** — it silently inherited item metrics from the sweep it no longer visits |
| Picker icons duplicated GAME-WIDE (v2.39.1) | the panel we were working on | **every other panel in the game** — one window's birth wrote a scaled value into a SHARED latch |

The pattern: **the scenario axis, not the code, was the variable.** Test the
axes below.

---

## ⛔ THE MOST EXPENSIVE AXIS SO FAR: 1.5x IS NOT "2x BUT SMALLER"

Added 2026-08-06, after the first eyes-on pass at 1.5x found **four** real
defects in one session that every automated gate had passed at all three tiers
for weeks.

They share one shape. **An INTEGER factor preserves properties that a
fractional factor destroys**, so a rule that is provably correct at 2x and 3x
can be silently wrong at 1.5x — and the integer tiers cannot express the defect
at all, so they can never catch it:

| what breaks at 1.5x | why 2x/3x can't see it | issue |
|---|---|---|
| font point sizes | `round(7*2)` is exact; `round(7*1.5)` overshoots and clips | #142 |
| the game's `width/3` and `width/4` **cell divides** | `N \| v` implies `N \| k*v` for integer `k` — divisibility is preserved for free. At 1.5x: **31%** and **43%** of dimensions break | #143 |
| text box widths | same family as the font rounding | #142 |

**THE RULE THIS BUYS: any change justified by "it is exact" must name the
factors it is exact FOR, and must be exercised at a FRACTIONAL tier before it
is believed.** Law 53 ("unproven until a THIRD tier sees it") is not about
breadth — for this whole class, the fractional tier is the *only* tier with the
power to disagree.

⚠ Two instrument failures rode along, both worth testing for directly:

- `Set-Tier.ps1 -Status` reported **all nine packages "dependency-gated off"
  while all nine were loading** (#144). A duplicated `.dat` / `.dat.x1-disabled`
  slot overwrote the active entry. **Check that your tier instrument agrees with
  `Get-ChildItem` before trusting a tier claim.**
- A `--hq` revert was written as a *comment* and the statement was left in
  place; the tool kept printing `Mode : high-quality` and rebuilt the whole tier
  wrong a second time. **The printed mode line is the test, not the source
  edit.**

Cheap tier-sanity check that needs no game: **a 1.5x package must be SMALLER
than the 2x one** (2.25x the source pixels vs 4x). When bicubic was wrongly
enabled, `SelectiveArt-15x` went 10.5 MB → 20.5 MB against 2x's 11.4 MB. A
package size moving the wrong way is a free regression detector.

---

## AXIS 1 — Scale tier (1x / 1.5x / 2x / 3x)

The tier is chosen from the RENDER resolution by `ScaleTier::Decide`, and it
gates which package set is live (`-2x` active, others `.x1-disabled`).

| Tier | How to force | Must be true |
|---|---|---|
| 2x (primary) | native 2400x1600 | everything in REGRESSION.md |
| 1x = STOCK | `[UiSpike] AutoScale=1` at a small res, or `AutoScale=0` + `ScaleFactor=1.0` | **DLL fully INERT**: no sweep, no patches, all dats renamed `.x1-disabled`, FontStyle moved aside. The game must be indistinguishable from a no-DLL install |
| 1.5x / 3x | change resolution so `Decide` picks the tier | packages exist at the right entry counts (the suite checks all three tiers), and `scale_len` = `floor(v*N+0.5)` — **1.5x is where rounding bugs hide, 2x hides them (exact doubling)** |

### ⚠ THERE IS NO TEXT AXIS, AND THAT IS A DECISION (2026-08-03, #97)

**UI scale and TEXT scale ship LOCKED 1:1.** Settled by the user 2026-08-03:
text is **not** a user-facing setting, shipping UI values are **1.5 / 2 / 3
only**, and above 3x is BACKLOG, not supported. So this matrix deliberately has
**no text-scale axis** — and if one is ever proposed, **adding it here is part
of the change, not a follow-up.**

The justification is measured, not stylistic: `tools\research\SCALING-AXES.md`
§2.2 catalogues **26 places** where a box is sized by its text or a text is
wrapped to its box. At `t ≠ u` each of those pairs silently unpairs — and
#57 is the worked example of what that costs, because the one pair we *did*
split (a Python-side font squeeze against a C++-side box widen) went four
builds without anyone noticing it had never applied to the panel it was
written for.

**The one axis that CAN move independently is the U-Drive-It mission bubble**
(`B ≤ 2 × UI`; drawn 96/128/192 px at UI 1.5/2/3). Its ceiling is set by the
**art**, not by clipping — the marker's parent is the full-screen 3D view, so a
big bubble structurally cannot overflow it. Today at 2x it is nearest-neighbour
replication of 64px art: right size, missing sharpness (#100).

**GOTCHAS.**
- Anything hardcoded for 2x is invisible at 2x. Every constant added must be
  expressed via `FACTOR`/`scale_len`, never `*2`.
- ⚠ **A box that must contain RENDERED TEXT is not a `FACTOR` constant**
  (law 48, #57). Ink grows ×2.13 per doubling, not ×2.00, so `round(stock × f)`
  is ~6 % too narrow and wraps *more* than stock. Size it from the font
  (`tools\uimap\emu\emu_text_extent.py`). This is a tier-axis trap that
  **passes at 1x and fails at every shipped tier**.
- ⚠ **1.5x and 3x are VERTICALLY UNVERIFIED for anything font-driven.**
  `lineHeight` has never been measured at those tiers, so the #57 oracle
  SKIPS 2914 of its 10708 checks there rather than assume. One capture per
  tier clears it (`tools\uimap\emu\measure_lineh_tier.py`).
- The three tiers are BUILT from the same generators — always rebuild all three
  (`--factor 2`, `--factor 1.5`, `--factor 3`) or the suite fails on entry counts.
- `Test-DatIntegrity.ps1` accepts a package live **or** gated, so a tier flip
  does not fail it. It will NOT catch a package renamed with a
  non-`.x1-disabled` suffix (e.g. the `.uiscale-testoff` the toggle script
  uses) — that reads as NOT FOUND, which is deliberate.

## AXIS 2 — Mod state (this is the axis that hurt most)

| State | How | Why it matters |
|---|---|---|
| Full modded set (default) | as installed | the state the user plays |
| One override disabled | `Toggle-BuildingStylesUI.ps1 -Off` / `-On` | proves whether a defect is ours or the mod's |
| Quit/exit confirms unmodded | `Toggle-SaveWarningUI.ps1 -Off` / `-On` | the two states must BOTH be flawless (task #79c) |
| Vanilla | ~~*no script yet — see TODO below*~~ **`Set-StockPlugins.ps1`** / `-Restore` / `-Status` — corrected 2026-08-16 | the roadmap's vanilla verification pass |

**`Set-StockPlugins.ps1` — corrected 2026-08-16.** The "no script yet" note
above was stale: the script landed 2026-08-05/06 and this file was edited after
it. It is BROADER than `Set-StockCompare.ps1` (which disables only OUR layer,
`Set-StockCompare.ps1:8-12`): it stashes every loadable file in the Plugins
root (`*.dll`, `*.dat`, `FontStyle.ini`) and every content subfolder — NAM,
CAM/Maxis, the null45 + memo DLL families, MoreBuildingStyles, thumbnail and
texture fixes, **and our own `z_SC4UIScale_*.dat` + `zzz-SC4UIScale\`**
(`Set-StockPlugins.ps1:179-197`). The rule is by SHAPE, not a hand-list, so a
plugin we have never heard of is still caught. It also takes the INSTALL-tree
`FontStyle.ini` copies — `<install>\Plugins`, `<install>`, `<install>\Apps`
(`:199-220`) — the exact three-probe contaminant that made earlier "stock"
captures Franken-captures (REGRESSION.md:6320-6334). Nothing is deleted; a
manifest drives an exact `-Restore` (`:17-20`, `:222-238`, `:129-150`). It also
sets a windowed resolution, default 1024x768, `-Width`/`-Height` (`:41-42`,
`:240-243`).

⛔ **The stash is a SIBLING of `Plugins\`, never a child** — `Documents\SimCity
4\_stock-stash` (`:50`, `:61-62`, banner `:22-23`). SC4's plugin scan is
RECURSIVE: the first version of this script stashed INSIDE `Plugins\` and 132
dats (98 MB) + 30 DLLs stayed live through a whole stock-baseline
investigation (`:53-60`). Do not "tidy" it back inside, and do not hand-roll a
replacement that repeats the bug.

⛔ **`SC4TouchControls` is NOT kept.** It is stashed on every run — it is not in
`$KeepNames` (`:68`, `:181`, `:183`) — and `-Restore` REFUSES it by name
(`$Quarantined`, `:80`, `:141-144`) under the 2026-08-05 quarantine order.
`-IncludeTouch` is **not** an escape hatch (`:78`) and is read nowhere in the
stash logic; its only live use is the closing summary string (`:246`), which
still prints a stale "KEPT ON PURPOSE ... + SC4TouchControls" — ignore that
line, and ignore the script's own header at `:29-31`, which the quarantine
block at `:70-80` overrode and which was never updated.

DELIBERATELY KEPT: `SC4GraphicsOptions.dll`/`.ini` (`:26-28`, `:68`) — this IS
the resolution lever — and dgVoodoo's `DDraw.dll` in the GAME INSTALL dir,
which is not touched at all (`:32-34`): SC4 on Win11 needs it to start, so
removing it risks not launching rather than launching stock.

**THE LOAD-ORDER LAW (proven live, cost two failed deploys).** Files in the
`Plugins` **root** load BEFORE files in **subfolders**, so a root `z_*.dat` can
never override a dat in a subfolder. Overrides of another mod must live in a
folder that sorts AFTER the target (`zzz-SC4UIScale\` beats `150-mods\`).

**⚠ AN OVERRIDE BUILT FROM ANOTHER MOD'S DATA MUST BE GATED ON THAT MOD**
(v2.38.0). Otherwise removing the mod does NOT remove it: our frozen copy sits
in `zzz-` and outranks everything, so the mod's UI stays on screen. Measured
2026-07-31 — with CoriBoom's mod deleted, our copy (532x640) still beat the
stock script (531x406). `ScaleTier::kThirdPartyDeps` now enables each such
package only while its owning mod is installed (and, where our copy hard-codes
the mod's exact rects, unchanged). **When you add a package built from someone
else's data, add its dependency row in the same change.**

Reproduce the load order for any resource with
`python tools\dbpf\who_owns_tgi.py <instance...>` — it prints every holder in
load order and names the winner.

**GOTCHAS.**
- A plugin can replace a stock **.UI script**, its **art**, or both. Check for
  both. CoriBoom replaced the Building Style script AND shipped its own taller
  background art; fixing only the script left the art 1x.
- **Recognition rule:** if a panel's LIVE window count or root size does not
  match the stock script you are reading, a plugin has replaced that script.
  (Live 532x640 / 73 windows vs stock 531x406 was the tell.) Grep
  `Plugins\**\*.dat` for the TGI before touching anything.
- Build third-party overrides from **the MOD's** script/art, never the stock
  one — different dimensions, and using stock silently reverts the mod's
  features (would have dropped 36 style slots back to 4).
- **When disabling a mod to test, our own override of it MUST move too.** Our
  `zzz` package carries a copy of the mod's script at the same TGI and
  outranks the root, so disabling only the mod's file leaves the mod's layout
  alive via our file. The toggle script moves both; any new toggle must too.
- Wrong text COLOUR was a symptom of the wrong SCRIPT being loaded — not a
  font or colour bug. Suspect load order before suspecting colours.
- Re-extract the mod's source script/art after any mod update or we ship a
  stale layout (`tools\selective-safe\thirdparty-ui\` + `thirdparty-art\`).

## AXIS 3 — Game mode / screen

Verified distinct behaviour in each; a fix in one proves nothing about another.

| Mode | Setup | Notes |
|---|---|---|
| Region view | launch → region | separate scaling path (`ScaleRegion`, timer-polled: no city message fires) |
| City, MAYOR mode | found a city | mayor toolbar `0x69E40A1F`, 100px button pitch |
| City, GOD mode **pre-founding** | new city, don't found | terraform dock LOCKED here |
| City, GOD mode **founded** | founded city → god | **different toolbar (`0xC991EDA8`), 120px pitch.** Several windows measured "hidden/inert" pre-founding go LIVE once a city exists |
| Sim mode / My Sims | enter Sim mode, open the My Sims catalog AND a Sim detail page (profile / actions / find-sim) | ~~DEFERRED (`kNeverScaleIds`); needs a code-level slot-pitch hook~~ **CORRECTED 2026-08-16: FULLY LIVE — a real axis, not out of scope.** The family left `kNeverScaleIds` in v2.22.0 (`src\UiSpike.cpp:4782`, comment-only there now) and carries four mechanisms: 2x art via `SCALED_WINDOW_IDS` — which lives in **`tools\selective-safe\build_selective_safe.py:239-241`**, not in UiSpike (`UiSpike.cpp:5472-5473`); pre-scale while hidden via `kAlwaysScaleCityIds` (`UiSpike.cpp:5234` decl, roots `:5256-5258`); dashboard design-x via `kCityHudFamilyIds` (`UiSpike.cpp:5718` decl, `:5720`); and the GZWinBMP runtime-portrait draw hook via `kBmpxCityRoots` (`UiSpike.cpp:11110-11111`), which is what ANSWERED the old "slot-pitch code hook" concern — that concern was the portraits tiling inside doubled slots (`UiSpike.cpp:4793-4796`), closed as task #47 in v2.42.4, user-confirmed. **Test BOTH halves:** script I-aa1f1f57 has NINE marker-composed top-level roots, not three (`UiSpike.cpp:5259`); v2.22.0 covered the CATALOG side only and left the whole DETAIL side (`:5264-5268`) 1x against 2x siblings |

**GOTCHA.** Never gate on a state test not verified in ALL THREE of
{pre-founding god, founded god, founded mayor}. The `en=1` mayor-button test
passed in two and was wrong in the third. The verified gate is "mayor HUD
`0xE9889775` visible".

## AXIS 4 — Panel lifecycle (the sneakiest axis)

| Phase | Why it differs |
|---|---|
| **City load, while HIDDEN** | our pre-scale runs here (`kAlwaysScaleCityIds`). Windows the vis-gate skips get caught only if listed |
| **FIRST open per city load** | the game BINDS things once here: 3D advisor heads framed from the then-current geometry, strip fields captured once. **Our sweep cannot run earlier than this bind** — so anything bound at city load must be fixed in DATA |
| Re-open | usually correct even when first-open is broken — which is exactly why first-open bugs survive testing |
| Compact vs EXPANDED | different child subtrees, often different art (Building Style, Budget) |
| After a city SWITCH | **the game REUSES window objects across cities** — scale records must never be cleared between cities |
| Region ↔ city switch | re-entry paths differ; check both |

**HOW TO TEST FIRST-OPEN PROPERLY:** exit to region, re-enter the city (or
restart), and open the panel as the *very first* interaction. Re-opening after
any other panel visit invalidates the test.

### The sub-axis that cost two builds on 2026-07-31: BORN vs SWEPT

Moving a window to **born-at-Place** does not just make it earlier — it takes
it **off the sweep entirely**, so it stops receiving everything the sweep was
quietly doing for it. Before promoting any window, enumerate what the sweep
does for it today (size, dock, item metrics, chrome/hook state, repaint) and
port **all** of it — a promotion is a migration, not an optimisation.
That miss produced quarter-size disaster thumbnails in v2.39.0.

Then check the reverse direction: **what does the birth path WRITE that is
shared?** If a value lands in a game-wide latch (`gStripBase*`), the blast
radius is every panel in the game, not the one you are testing. Prime a shared
latch from the **stock** argument, never from the scaled one — v2.39.1
duplicated picker icons everywhere and regressed the previous day's fix.

**So every born-at-Place change has two mandatory scenario checks beyond its
own panel:** (a) the promoted window itself with the path OFF (its ini kill
switch — verify the key name matches *exactly*, not by substring), and (b) one
UNRELATED panel of the same family opened afterwards in the same session.

## AXIS 5 — Render mode / resolution

`Decide` uses the RENDER resolution, which is NOT the requested one:

| Driver + mode | Render res |
|---|---|
| DirectX + FullScreen/Borderless | **monitor native** (wrapper ignores the request) |
| DirectX + Windowed | the requested window size |
| Software (any mode) | the requested size |

**GOTCHAS.** Only real display modes work in fullscreen (wrapper-emulated
exotic modes garble). SC4's partial redraw garbles under dgVoodoo at
non-desktop modes — `ForceDrawOnScroll=true` fixes it.

## AXIS 6 — Input path

Mouse vs touch (the frozen `SC4TouchControls.dll` v1.0.4) vs our synthesized
clicks. **SC4 POLLS the physical cursor for drags** and ignores posted mouse
messages for panning, so anything driving input must use
`SetCursorPos` + real buttons for drags. Synthesized clicks (ArrowClick) do
work for button activation.

---

## Standing gotchas that are not axes (they bite in every scenario)

**The game reads some geometry BEFORE our sweep can run.** Then runtime
scaling is structurally too late and the fix belongs in DATA (pre-scaled
`.UI`), with the parent made root-only so children are not scaled twice.
Two proven instances: advisor strip subtree (3D heads bound at city load) and
the ticker marquee width (init-cached, re-imposed every roll tick).

**Some things must NEVER be scaled:**
- **Alignment markers** (`id=0x0000AAAA`) are POSITIONING DATA. The game
  places a panel at `anchor − markerOffset` in NATIVE units. Scaling one
  shifted the whole Advisors box by exactly `−(229,63)`. Not at runtime, and
  not in shipped data either.
- **Font-sized / art-sized controls** — a control whose size is computed from
  its rendered caption or its own art is ALREADY correct once fonts/art are
  2x. Scaling it again doubles it (`kFontSizedIds`: the "Change style every"
  row went 2x too tall; the year spinner overflowed its parent and lost its
  down arrow).
- **AdviceList children** — items are game-sized to the container; recursing
  double-scales them.
- Never suppress paints to hide a flash (a "FlashGuard" blanked HUD windows).
  Pre-scale while HIDDEN instead.

**Skip/exclusion lists from an earlier project phase are a scenario axis.**
The city sweep skipped 0xAA32BCE6 for WEEKS under a spike-era label ("plop-menu
machinery") that a tree dump disproves in one read — it is the Data Views
panel, and the skip left it 1x among the 2x HUD (task #45). When a
subtree's real owner becomes known, re-audit every id-skip that touches it;
an exclusion is a claim about the tree and claims rot. Sibling rule: when one
window id has SEVERAL script copies, identify the LIVE one by rect-matching
against a runtime dump (I-2bc9060f won on all seven probe rects; two stale
copies share its root id) — the I-898897de lesson, now proven twice.

**The panel-lifecycle axis includes EXPAND, and it can CRASH, not just look
wrong.** The v2.21.0 Data Views fix was perfect in the compact state and
killed the game the first time the user pressed Expand (the handler
repositions with 1x metrics, then native death — suspect the code-painted
data-map child; v2.21.1 reverted both sides). A fix confirmed on one
lifecycle state is half-tested, and the untested half of THIS panel family
carries code-painted surfaces where mixed 1x/2x metrics are fatal.

**Plot-hook natural captures are ONE-SHOT.** Any other writer that runs first
poisons them (writing strip fields from the sweep captured 88 as natural →
forced 176 → 4x pitch everywhere). Sweep-side code may INVALIDATE, never write.

**Size heuristics cannot identify content-sized windows.** Tooltips are sized
by their text, so "width 200-400 and height > 500" caught tip buffers too.
Identify positively: exact width, class + id, or a mode split.

**Alpha guard shape is `0 < a < 128`, never `a < 128`** — stock magenta-keyed
art has `a == 0` everywhere.

**Parse BOTH exemplar formats** (binary EQZB/CQZB *and* text) — CAM is ~half
text; a binary-only parse silently missed 30 icons.

---

## Environment gotchas (cost real time this session)

- **The game runs ELEVATED.** A non-elevated shell cannot kill it
  (`Access is denied`). Never kill it anyway — use the wait-for-close deploy
  loop. If it hangs with no window, Steam refuses to relaunch ("Game already
  running") and the user must end it from an elevated Task Manager.
- **Deploy pattern:** poll `tasklist` for `SimCity 4.exe`, copy on exit. The
  game holds the dats and DLL open while running.
- **OneDrive holds directory handles** — `shutil.rmtree` deletes the files then
  fails with `WinError 5` on the rmdir. Use `fresh_dir()` (clear contents,
  keep the folder). Same reason `find` over the tree is glacial: use Glob.
- **`LiveDumpMs` left on = ~12 MB of log per session** and constant disk I/O
  during play. Leave it 0; turn on only while measuring.
- ~~**`[Probe] Enabled` is live-tunable** (ini re-read every 20 sweeps) — no
  restart needed.~~ **CORRECTED 2026-08-16 — NOT live-tunable on a default
  install.** v2.69.0 put the whole ini re-read behind `[UiSpike] LiveTune`,
  which ships **0** (`_packaging\SC4UIScale.ini:85`, section header `:26`):
  the block runs ONCE on the first sweep and then never again (rationale at
  `UiSpike.cpp:11961-11966`, guard `if (firstPass || (s_liveTune > 0 &&
  ++s_poll >= 20))` at `:11972`). Every `[Probe]` key — `Enabled` (`:12030`),
  `BandL/R/T/B` (`:12032-12038`), `Max` (`:12040`), `EdgeDump`/`VisTrace`/
  `EdgeBlt`, `ThinBlt` (`:12066`) and the `Icon*` family (`:12086-12097`) — is
  read inside it; the block closes at `:12167`. The statics are function-level
  in `ScaleGodFlyouts` (`:11914`), so this is once per **game launch**, not per
  city. **`LiveTune` is itself latched on that same first pass** (`if
  (s_liveTune < 0)`, `:11978-11982`) — flipping it mid-session does nothing
  either. So: set `[UiSpike] LiveTune=1` **before** launching to restore the
  20-sweep poll, otherwise restart the game after editing `[Probe]`.
  ⚠ This is the instrument-null trap: arm a probe mid-session, see no lines,
  and conclude the code path never runs. But `LiveDumpMs` is read once at
  startup (`Settings.cpp:50`, consumed at `UiSpike.cpp:7924`) and DOES need a
  restart.
- **DPROBE band:** `BandL=900` excludes the news ticker marquee
  (`0xAA12F33C`, abs x=534), which scrolls 1px per frame and floods the log,
  burying the panel you are actually measuring.
- Log files are share-locked while the game runs — read with a
  `FileStream` + `FileShare.ReadWrite`, not `Get-Content`.

---

## MEASURE, DON'T INFER (the rule that decided every fix today)

Every measured value landed first try. Every screenshot-inferred one cost
2-3 builds and twice broke something that worked. Today's proof:

- The advisor faces: screenshots suggested art scaling; the LOG proved the
  strip was already 2x and the framing was bound earlier. Two wasted builds
  before measuring.
- The Building Style background: I had a confident `imagerect` theory; DPROBE
  proved the window was **exactly 2x (1038x1308)** and killed it. The real
  cause was the mod's own art.
- The spinner: the probe gave 60x72 inside a 98x44 parent — the clipping was
  arithmetic, not opinion.

**If two symptoms contradict each other, you are at the wrong LAYER — move up
one.** Build the instrument, then read it.

---

## TODO — scenarios we still cannot set up cheaply

- ~~**Vanilla (no plugins) run** — the roadmap's verification pass. Needs a
  script that moves the whole user `Plugins\` aside except our own packages
  (and a way back). `Toggle-BuildingStylesUI.ps1` is the pattern to copy.~~
  **Corrected 2026-08-16 — this is DONE, do not write it again.**
  `_tests\Set-StockPlugins.ps1` (2026-08-06) stashes the whole tree, ours
  included, with a manifest-backed `-Restore` and a `-Status`
  (`Set-StockPlugins.ps1:4-20`); the narrower "everything except ours" state is
  `Set-StockCompare.ps1 -Mode Stock` / `-Mode Ours`. What is still owed here is
  the eyes-on RUN, not the tooling. See the AXIS 2 note above before using it —
  especially the sibling-stash rule and the touch quarantine.
- ~~**1.5x / 3x live verification** — packages build and pass offline, but no
  eyes-on run at those tiers yet; rounding is the risk.~~
  **DISCHARGED 2026-08-16 — both tiers have been run live on screen, and this
  entry contradicted this file's own §"THE MOST EXPENSIVE AXIS SO FAR".**
  1.5x: first user run 2026-08-04 at 1920x1080 then 1600x1200,
  both booting tier 1.50 (`VERSION-HISTORY.txt:2051-2052`), followed by the
  2026-08-06 eyes-on pass that found four real defects every automated gate had
  passed. 3x: run at 3840x2160 with `ScaleTier::Decide` picking tier 3.00
  (`VERSION-HISTORY.txt:1992`, `:2043-2045`; `src\ScaleTier.cpp:1651`).
  The rounding risk was real and is now a measured defect family: #157, #161
  and #170 are CLOSED and USER-CONFIRMED at 1.5x, and #158 is closed but was
  never visible so never had an eyes-on (`_tests\REGRESSION.md:9293-9296`).
  Still open **at 1.5x only** — #162 (`REGRESSION.md:9585`, mechanism found,
  kill test negative at `:10007`), #165 (`REGRESSION.md:9976`, live in the
  deployed `z_SC4UIScale_SelectiveArt-15x.dat`), #171 and #174.
  **What remains is not "first eyes-on" but a standing re-check at the
  fractional tier after any geometry change.**
- **Stock-parity pixel pass** (task #31) — geometry verified clean; the pixel
  comparison still needs an unlocked screen.
- **Founded-city vanilla reference** — every "hidden/inert" god-mode note was
  measured PRE-FOUNDING and several are wrong once a city exists. Run
  `Set-StockCompare` on a founded city before trusting those notes.

---

## AXIS 9 — LAYOUT DENSITY (added 2026-08-06, #148 — cost four regressions)

**A geometry change is not one test. It is one test PER DENSITY.**

The same edit — move 177 buttons up to 2px onto an even edge — produced:

| layout | density | result |
|---|---|---|
| Landscape flyout (`09923283`) | 5 buttons, ~50px apart | **invisible** — reported as fixed |
| Advisors strip | 7 portraits in fitted boxes | "sitting slightly left and high in their boxes" |
| Monthly Budget rows | ~20 rows, tight gutters | misaligned |
| Bottom dock + options row | anchored, adjacent | "sitting too high" |
| **Select A My Sim** (`0a243d80`) | **21 faces in a 7x3 grid, every column on an ODD left edge** | **whole grid slid left inside its own frame** |

⚠ **ID CORRECTED 2026-08-16.** This row used to read `aa1f1f57`. The panel name
and the grid are right; the **script id was wrong**, and so was pinning the
nudge counts to this panel. `I-aa1f1f57` is captioned **"My Sims"** — the
nine-root catalog/detail family (`src\UiSpike.cpp:5253`) — and its densest
button row holds **four** buttons, not twenty-one. The 21-face grid is in
`I-0a243d80`, `caption="Select A My Sim"` (`build_dialog_static.py:389`;
`tools\uiscripts\extracted\T-00000000_G-96a006b0_I-0a243d80.ui`): 22 buttons of
50x49, of which 21 sit at columns x=59,111,163,215,267,319,371 and rows
y=36,86,136 — the 22nd, at (68,243), is the selected-sim preview. **All seven of
those columns are ODD and all three rows EVEN**, so the reverted parity nudge
(q=2 at 1.5x) moved all 21 faces sideways and none vertically — exactly the user
report at `build_selective_safe.py:1157`, "all the faces are shifted to the
left". In `aa1f1f57` only 2 of its 6 face buttons have odd lefts and there is no
grid, so it cannot show that symptom.

~~the most-edited script at 24+28 nudges~~
The **24 and 28** counts are real but belong to a **different script**:
`I-aa1f1f57`, which ships as two group copies (`G-08000600` and `G-96a006b0`),
hence two numbers (`build_selective_safe.py:1159`). `I-0a243d80` exists as a
single file and cannot produce a pair. **The most-nudged script and the panel
that showed the defect are not the same window** — testing on either one alone
is the mistake this axis exists to prevent. The upstream comment at
`build_selective_safe.py:1146-1163` conflates the two the same way and should be
read with this correction.

The flyout that reported the bug was the *least* dense thing the fix touched, so
it was the worst possible place to judge it.

**Test procedure for any positional change:**

1. Sort the affected scripts by number of edits. The top one is the test case,
   not the one in the bug report.
2. Look at anything with a **frame around a grid** — a 1px shift is invisible in
   free space and obvious against a border.
3. Prefer a lever that changes SIZE over one that changes POSITION; leaf sizes
   are bounded by 1px and move nothing.

## AXIS 10 — WHO CREATED THE WINDOW (added 2026-08-06, #148)

**Not every window is in a `.UI`.** Flyout strip items are created at RUNTIME
(item-create does `SetArea(0, 0, GetW(), GetH())` on the container) and still
bind their art **by TGI**.

| change | reaches scripted windows | reaches runtime-created windows |
|---|---|---|
| edit `area=` in a `.UI` | ✅ | ❌ (nothing to edit) |
| edit ART dimensions | ✅ | ✅ **← the trap** |

An art-dimension change therefore has a blast radius the builder **cannot
enumerate**, and a conflict check built from `.UI` consumers will report clean
and be wrong. It did: 0 conflicts, 61 sheets rebuilt, thumbnails broken.

**Test any art-dimension change against a runtime-created consumer** — the
disaster flyout thumbnails, hovered — before believing an offline gate.

## AXIS 11 — WHOSE DIALOG IS IT? (added 2026-08-13, #154)

AXIS 2 asks whether a mod **replaced** something of the game's. This axis asks
the question underneath it: **whose window is this in the first place?**

| kind | in `TARGETS`? | stock twin? | who scales it today |
|---|---|---|---|
| stock dialog | ✅ | — | `DialogStatic` (or the runtime sweep) |
| stock dialog a mod REPLACED | ✅ | ✅ | `TP_TARGETS`, built from the mod's script, mod-gated |
| **a dialog the mod ADDED** | ❌ | ❌ | **nothing, until someone notices** |

The third row is invisible to every check in `build_dialog_static.py`: it is in
no target list, there is no stock twin to diff it against, and `verify_doubled`
never sees it because it is never built. CAM's Village Hall info screen sat in
that row for the **entire life of the project**, rendering at 1× under 1.5×
fonts with every gate green.

**When testing with a content mod installed, open the dialogs that mod ADDS,
not only the ones it changes.** For CAM that means: query a Village Hall / Town
Hall / City Hall (the info screen), and query a school and a library (the two
query panels). All three are now scaled — but the next content mod's own
windows start in row three again.

**The offline instrument for this axis already exists:**
`tools\uiscripts\winning_corpus.py`, which resolves the true load-order winner
of every `.UI` TGI across every archive. Run it after ANY plugin change and
read the third-party count. It should be **0**.
