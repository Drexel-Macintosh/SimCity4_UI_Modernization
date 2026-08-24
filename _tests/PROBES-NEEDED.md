# PROBES NEEDED — what we cannot answer offline

**Written 2026-08-15 (night), against v3.0.0 / DLL built 20:37 / tier forced 1.5×.**

The user runs the game; the engineer does not. Every launch is expensive, and
tonight several were spent on probes that **could never have fired** — the
`ThinBlt` capture logged nothing twice because its hook is installed only by the
disaster-flyout birth path, and the silence was read as data.

This file is the antidote. It lists only questions that a **live run** can settle,
each one with the ini keys, the YES shape, the NO shape, and — the part that was
missing before — **the positive control that proves the probe could have fired at
all**. Grouped so one launch answers as many as possible.

> **THE RULE THIS FILE EXISTS TO ENFORCE.** *NULL IS NOT EVIDENCE.* A silent log
> is a finding only when a control line in that same log proves the instrument
> was installed, executing, and reading the key you set. Every entry below either
> names such a line or is marked **UNSAFE TO ASK FOR**.

---

## 0. PRE-FLIGHT — five checks, each of which has personally wasted a launch

Run these with the game **closed**. Any one of them failing makes the whole
launch worthless.

| # | Check | Why | How |
|---|---|---|---|
| **P0** | **The DLL is OLDER THAN ITS SOURCE right now.** `build\Release\SC4UIScale.dll` = **20:37**, `src\UiSpike.cpp` = **21:01**. | Anything edited into `UiSpike.cpp` after 20:37 — including possibly the `ThinBlt` self-arming block — **is not in the running binary**. This is the `installed ≠ executed` failure (#47, standing rule 7) one level lower down: *not even compiled*. | `msbuild src\SC4UIScale.vcxproj -p:Configuration=Release -p:Platform=Win32`, then `_tests\Deploy-OnGameClose.ps1`. If you choose not to rebuild, **strike L-A2 (ThinBlt) from the run** — you cannot tell its null apart from a missing feature. |
| **P1** | The install is actually **ours**, not stock-compare. | `START-HERE.md §6` warns the tree was left mid-experiment. Right now `Documents\SimCity 4\Plugins` carries **both** `…-15x.dat` **and** `…-15x.dat.x1-disabled` for SelectiveArt / DialogStatic / ItemIcons — the live `.dat` wins and the mod IS on, but the state is ambiguous. | `_tests\Set-StockCompare.ps1 -Mode Ours` then `_tests\Test-DatIntegrity.ps1`. |
| **P2** | `[Logging] LogLevel` is **2 or 3**. | `DPROBE` and `EBLT` print at **Debug**. At LogLevel 1 they are silently dropped and the log looks like a clean null. | Live ini line 234 currently reads `LogLevel=3`. Leave it. |
| **P3** | **Copy the previous `SC4UIScale.log` out before launching.** | The log is **recreated every launch**. The run-14 spin capture was lost to exactly this. (`SC4UIScale-104.csv` beside it is append-only and safe.) | `copy "…\Plugins\SC4UIScale.log" _tests\captures\<date>-pre.log` |
| **P4** | Keys go in the **existing** `[Probe]` / `[Disaster]` / `[Flyout]` sections of `Documents\SimCity 4\Plugins\SC4UIScale.ini`. | `GetPrivateProfileString` reads the **FIRST** matching section only. A second `[Probe]` block appended at the bottom **orphans every key above it** — the ini already carries this warning in-line and it has bitten before. | Edit in place at lines 373 (`[Probe]`), 470 (`[Disaster]`), 236 (`[Flyout]`). No BOM, ever. |

### P5 — THE GATE ABOVE ALL PROBE KEYS (verified in source this session)

Every `[Probe]`, `[Disaster]` and `[Flyout]` key is read by **one block inside
`UiSpike::ScaleGodFlyouts`** (~~`src\UiSpike.cpp:11662–11858`~~ **2026-08-16:
`src\UiSpike.cpp:11967–12168`** — the live-tune scope, `{` at `:11967`, last key
`AdvisorHeal` at `:12166`, closing `}` at `:12168`). That function spans
~~`:11609–13974`~~ **`:11914–14279`** and is called from exactly three places:

```
ScalePanelsUnder(pView, "city")          UiSpike.cpp:8200     ← city load
ScalePanelsUnder(pView, "incremental")   UiSpike.cpp:14638    ← the per-tick sweep
ScalePanelsUnder(pRegion, "region")      UiSpike.cpp:16963    ← EXCLUDED
```

…and `ScalePanelsUnder` guards it with `if (rootTag[0] != 'r')` (~~`:10052`~~
**`:10357`**, gating the `ScaleGodFlyouts(pRoot, f)` call at `:10359`).

*(2026-08-16: all five line numbers re-pinned against current source. The
structure — one block, three call sites, region excluded — is unchanged and
verified: all 57 `GetPrivateProfileStringA` reads of `[Probe]`/`[Disaster]`/
`[Flyout]` fall inside `:11967–12168`, zero outside. The old numbers were not
wrong when written — they match `_working-backup\PRE-OVERNIGHT-2026-08-15-2145\
src\UiSpike.cpp` exactly; the file grew 17113→17535 lines. Re-pin by symbol,
not by memory of the offset.)*

Two consequences, both absolute:

1. **You must ENTER A CITY.** In the region screen, the city picker, the main
   menu or the loading screens, **not one probe key is ever read** and not one
   probe line can ever print. A launch that never reaches a city view answers
   nothing at all.
2. **The block runs ONCE, on the first city-view pass.** Editing the ini
   mid-session does nothing unless `[UiSpike] LiveTune=1` (which restores 20-sweep
   polling, ~144 ini reads/sec). **Set every key before launching.**

---

## 1. HOOK EAGERNESS — read this before asking for any probe

Verified against `src\UiSpike.cpp` this session, not quoted from memory.

| Key | Where it is consumed | Hook install | Fires in an ordinary session? |
|---|---|---|---|
| `[UiSpike] SpinProbe` | `SpinProbe::Arm`, end of `PreAppShutdown` | none — `Settings::Load` at director init | ✅ **EAGER, before any city.** The only probe here that is. |
| `[Probe] Enabled` + `BandL/R/T/B` + `Max` | DPROBE walk, `:12297` | none — runs in the sweep walk | ✅ EAGER *(city view only, per P5)* |
| `[Probe] EdgeDump` / `VisTrace` | ~~`EdgeProbeTick :6703` / `VisTraceTick :6684`, called at `:11622–23`~~ **`EdgeProbeTick :7008` / `VisTraceTick :6989`, called at `:11927–28`** *(re-pinned 2026-08-16; the old cites matched `_working-backup\PRE-OVERNIGHT-2026-08-15-2145`, +305 lines of drift since)* | none | ✅ EAGER *(one sweep late: the tick is called ~40 lines **before** the ini block, which opens at `:11967` — the `[Probe]` keys themselves are read at `:12042/:12044` — so the value takes effect from pass 2; irrelevant at 60 Hz)* |
| `[Probe] IconProbe` | class census, `:12047` | none | ✅ EAGER — **and it carries an unconditional positive-control line.** The model every other probe should copy. |
| `[Probe] IconHook` | `:12079`, window `0x8A2CAD8B` | none | ⚠ EAGER but **conditioned on that menu existing** — null unless the menu column is open. |
| **`[Probe] ThinBlt`** | `BltClassThunk :1974–2100`, buffer-class **vtable slot 29** | `EnsureBufferClassBltHook()` | ⚠ **LAZY BY DESIGN — NOW SELF-ARMING.** ~~`:11759–11773`~~ **`:12066–12082` (re-pinned 2026-08-16)** calls `EnsureBufferClassBltHook()` the moment `ThinBlt>0` — key read `:12066`, `if (gThinBlt > 0)` `:12068`, `s_thinArmed` latch `:12070`, the arm call `:12074`, the arm log `:12075–12080`. ~~**Conditional on P0**~~ **The arm IS in the deployed DLL (verified 2026-08-16).** Verify the arm line appears. |
| **`[Probe] EdgeBlt`** | `BltClassThunk :2111` — the **same slot-29 thunk** | `EnsureBufferClassBltHook()` | ⛔ **LAZY AND NOT SELF-ARMED. DO NOT ASK FOR IT ALONE.** See §5. |
| **`[Probe] IconFit` / `IconCover` / `IconCentreOff`** | `BltStripThunk` (`:2901`) — ~~`:2999/:3081/:3120`~~ **`IconFit :3041` / `IconCover :3123` / `IconCentreOff :3162`** **and** ~~`SlotThunk :3935`~~ **`SlotThunk2<88>` (`:4324`)** | instance vtable swap at ~~`:4137`~~ **`:4429–4439`**, gated `IDX == 88 && gStripProbe > 0`; `SlotThunk2<88>` itself installed only by `InstallSubFlyoutHooksNow` (~~`:6476`~~ **`:6781`**, gated on one of **seven** god-flyout parents being visible — `kHookParents`, 7 ids at `:6787–6788`) or by the disaster-strip size+class match at ~~`:12484`~~ **`:12776`** | ⛔ **DOUBLY LAZY. UNSAFE TO ASK FOR** in a general session. `gStripProbe` starts at 24 (`:2576`) and is **decremented to 0 by ordinary logging at** ~~`:2957`~~ **`:2999`** (the DSTRIP branch opened at `:2997`), so a probe armed late in a session sees nothing even with a flyout open — the only re-arm is `gStripProbe = 8` at `:4419`, itself gated on `gStripDump` (`:4378`). *(2026-08-16: line numbers re-pinned against `src\UiSpike.cpp` — the whole row was uniformly +42 stale in the `BltStripThunk` region, so the old `:2999` was `gIconFit`, not the decrement it now collides with. Verdict unchanged and re-verified.)* |

*(2026-08-16 `ThinBlt` re-pin, evidence: `src\UiSpike.cpp:11759` is now
`cIGZWin* aRow = pPage->GetChildWindowFromIDRecursive(0x8A909E00);` — the
Data-Views row/chip pin block, closing at `:11771` and feeding the `kDVPins`
loop at `:11773`. It has no `EnsureBufferClassBltHook()` call. The arm moved to
`:12066–12082`; note `:12053` is only a comment line inside the ⛔ warning
paragraph, **not** the key read, so do not pin to it. `:11759` is stale
everywhere it appears in this file — the ThinBlt positive-control note, the ⛔
two-launches warning and §5 as well. `BltClassThunk :1974` and the `EdgeBlt`
branch at `:2111` are still correct.)*

*(2026-08-16, P0 narrowed — NOT cleared: `build\Release\SC4UIScale.dll` =
**11:13:34**, `src\UiSpike.cpp` = **13:12:39**, so P0's DLL-older-than-source
condition still holds for anything edited after 11:13. It is cleared **for this
probe only**: an ASCII byte-scan of the deployed
`…\SimCity 4\Plugins\SC4UIScale.dll` (SHA256 `861C1FFE…7133`, byte-identical to
the build output) finds the literal `THINBLT armed`, and that string occurs at
exactly one site in source, `:12076`. So a missing arm line means the ini key
was not read — it can no longer mean "the build lacks the arm".)*

**The single-sentence version:** *only `SpinProbe` fires before a city; `Enabled`,
`EdgeDump`, `VisTrace`, `IconProbe` fire in any city view; `ThinBlt` fires only
because it arms its own hook; everything else needs a god-mode flyout open and is
not worth a launch slot.*

---

## 2. LAUNCH A — the 1.5× city session

**This is the launch to do.** Eight questions, one session, ~15 minutes of play.
The tier is already 1.5× (`AutoScale=0 ScaleFactor=1.5`), which is the only tier
that can express the whole fractional defect family.

### Ini for Launch A — set ALL of this before starting

```ini
[UiSpike]
SpinProbe=10          ; was 0

[Probe]
ThinBlt=40            ; was 0   (omit this line if you did NOT do P0)

[Logging]
LogLevel=3            ; already correct
```

Nothing else changes. Leave `IconFit`, `IconCover`, `IconCentreOff`, `IconHook`,
`EdgeBlt`, `Enabled` and `IconProbe` at **0** — §1 explains why each would be a
null, and the noise would bury the lines that matter.

---

### L-A1 ⭐ THE #162 KILL TEST — free, decisive, no ini, no build

**Question.** Are the two phantom hairlines at 1.5× caused by
`sy = (int)(oy / 1.5)` giving **even** source rows multiplicity 2?

**Why offline cannot answer it.** The art is already proven innocent — every
1.5× pixel is a byte-exact copy of its 1× source (0/24840 and 0/20412 mismatches,
with a differ positive-controlled at 3215 differing pixels on a known-different
pair). `gate_art_vs_window.py` was re-run tonight and reports **0 new shortfalls
at f=1.5** (output in §6). So the defect is not a size mismatch and not a
resampler artefact: it is a **perceptual** consequence of which rows got doubled,
and no arithmetic gate in this repo has ever looked at a pixel, let alone judged
one. The mechanism does, however, make a falsifiable prediction about a state the
user can reach with the mouse.

**The prediction.** The two affected sheets each carry one isolated 1px-tall
bright run at **src row 2 (EVEN → doubled)** in cell 1. The **PRESSED** cell
(state 2) carries the same run one row lower, at **src row 3 (ODD → multiplicity
1)**.

**The two buttons, named from the `.UI` that binds them**
(`tools\uiscripts\extracted\T-00000000_G-96a006b0_I-c973b411.ui`):

| art TGI | window id | tooltip / on-screen name |
|---|---|---|
| `{46a006b0,14015555}` | `0xc988bc79` | **Mayor Mode** — the mayor's-hat button |
| `{46a006b0,13f15230}` | `0x4988bc6a` | **My Sim Mode** — the "people" button |
| `{46a006b0,14415860}` | `0x2988bc85` | **God Mode** — the CONTROL, see below |

**IN-GAME ACTION.** In the city view, on the round mode-selector cluster at the
top-left: **press and HOLD the left mouse button on the Mayor Mode (hat) button.
Do not release. Look at the button for three seconds.** Then repeat on My Sim
Mode. (`triggerondown=off`, so the action fires on release — drag the cursor off
the button before letting go if you would rather not switch modes. Switching is
harmless either way.)

* **YES (mechanism confirmed):** the short bright line **disappears while held**
  and comes back on release. On both buttons.
* **NO (candidate is dead):** the line is still there while held. **Nothing in
  the "centre-aligned NN" proposal should then be built** — it would be the exact
  shape of the re-phasing that broke the "?" button at 21:07 tonight.

**POSITIVE CONTROL — and this one is unusually strong.** The **God Mode** button
`{46a006b0,14415860}` carries the *identical* doubled feature (cell 1, row 2,
len 7, contrast 78) and is **clean on screen**, because its `area=(26,-6,90,44)`
puts its top 6 rows above the parent's origin so the doubled row is clipped away
and never drawn. So the control is built into the test: **the mechanism predicts
2 broken of 3, with the God Mode button the clean one — which is exactly the
pattern the user already reported before anyone knew why.** If all three look the
same to you at rest, you are not looking at the feature this test is about, and
the hold test will not mean anything.

**Report back:** for each of Mayor / My Sim — "line visible at rest? yes/no",
"line visible while held? yes/no".

---

### L-A2 — #162: is the hairline DRAWN, or is it an uncovered GAP?

**Question.** Does anything blit a ≤3px-thin destination rect through the shared
UI buffer class where the hairline appears?

**Why offline cannot answer it.** Runtime blit tuples exist only at runtime.
`render_dialog.py` composites **state 0 only**, no text, no runtime draws, no
edge/tiled blits — its own header says a clean result is not proof the screen is
clean. Nothing offline enumerates what the engine actually draws.

**INI:** `[Probe] ThinBlt=40` **(requires P0 — see below)**

* **YES:** `UiSpike: THINBLT dst(…) 1x7  src(…)  destBuf=…` lines naming a thin
  destination. Those coordinates locate the drawer.
* **NO (a real null, and it is an answer):** heartbeat lines with a large seen
  count and `0 thin`, e.g.
  `THINBLT heartbeat - 40000 blit(s) seen, 0 thin so far` — meaning the hairline
  is **not drawn through this buffer class** and the next instrument must look
  somewhere else.

**POSITIVE CONTROL — two lines, both mandatory:**

1. `UiSpike: THINBLT armed - buffer-class slot 29 hooked (orig=0x…)` — proves
   the key was read **and** the hook was installed. Printed once, from
   `:11759`.
2. `UiSpike: THINBLT heartbeat - 1 blit(s) seen, 0 thin so far` — the **first
   blit**, proving the thunk is executing. Then every 2000 blits.

> ⛔ **THIS IS THE PROBE THAT BURNED TWO LAUNCHES.** `BltClassThunk` lives on the
> buffer-class vtable and is installed only by `EnsureBufferClassBltHook()`,
> called from the disaster/emergency flyout birth path (~~`:6152`, `:6274`~~
> **`:6444` and `:6579` — re-pinned 2026-08-16; both are in `SubPlaceDetour`
> (`:6213`), whose disaster branch returns at `:6282`, which is why `:6444`
> exists at all. The function itself is defined at `:6119`.**) and the
> container's own Plot detour. **A session that never opens a god flyout never
> patches slot 29.** The self-arming block at `:11759` fixes that — *if it is in
> the binary you are running.* **`UiSpike.cpp` is 24 minutes newer than the
> deployed DLL (P0).** If **neither** control line appears, the correct
> conclusion is *"this build does not have the arm"* — **not** *"there are no
> thin blits"*. In that case, rebuild and redo, or fall back: open the **Disaster
> flyout once** at the start of the session, which arms slot 29 the old way.

**Honest cost of arming it:** `ThinBlt>0` installs the class Blt hook earlier
than it otherwise would be. The transforms inside `BltClassThunk` are gated on
`destIsContainer` / `destIsSubContainer` size heuristics that the ordinary UI does
not match, so this should be visually inert — but it is a hook that would not
otherwise be present, and that is not literally zero risk. If anything looks
wrong that did not before, set `ThinBlt=0` and relaunch before reporting it as a
defect.

**IN-GAME ACTION:** none beyond L-A1 — just be in the city view with the mode
cluster on screen for ~30 seconds. Do L-A1 and L-A2 together.

---

### L-A3 — #160: did the tiled-background cure actually land on screen?

**Question.** User: *"There's a break in the white line on the left that is not in
2× or stock"* — the god-mode tool column at 1.5× only. Is it gone?

**Why offline cannot answer it.** Offline says the arithmetic is now right, and
offline has said that before while the screen disagreed (#154, #155, #162 twice).
I verified the shipped art this session: the god toolbar rail
`{46a006b0,14415876}` is now **111×527** in `preview-15x`, matching the window's
plain-round 527 instead of the old `CellUnit` snap to 528. But "art and window
agree in a Python model" and "the rail is unbroken on the panel" are different
claims — that is exactly the gap rule 14 was written for.

**INI:** none.

**IN-GAME ACTION.** City view. Look at the **left-hand god-mode tool column** —
the vertical white rail down its left edge. Follow it top to bottom.

* **YES (fixed):** the white line is continuous top to bottom, as at 2× and stock.
* **NO (still broken):** a visible break/step partway down.

**POSITIVE CONTROL.** Compare against 2× or stock **in the same sitting** — the
defect is *defined* as "present at 1.5×, absent at 2× and stock", so a 1.5×-only
look cannot distinguish "fixed" from "I am not seeing it". Cheapest control:
photograph/describe the same rail, then run `_tests\Set-Tier.ps1 -Tier 2` on a
later launch. Do **not** treat a single clean 1.5× glance as closure.

**PRE-REGISTERED CONTINGENCY, so nobody re-investigates from scratch.** I checked
tonight: `preview-15x` also contains a **group-`1abe787d` twin** of the same
instance at **111×528** (un-cured, because no `.UI` binds it and the derived lists
are keyed on `.UI` bindings). **It is NOT packaged** — `package-list-15x.txt`
ships only `0x856DDBAC 0x46A006B0 0x14415876`. So the twin is **ruled out** as a
cause and should not be chased. If the break survives, the next place to look is
the *window* side, not the art.

---

### L-A4 ⭐ U1 — measure `lineHeight` at 1.5× (the cheapest open item in the project)

**Question.** What is `lineH(pt)` at the 1.5× tier?

**Why offline cannot answer it.** The fonts are `.mxf`. FreeType cannot read
them; there is no font API to query offline. Every glyph metric in this suite was
back-solved from **rendered pixels**, and `lineHeight` has only ever been measured
at **1× and 2×**. Two points do not determine the pt→px rule, so
`prove_chart_legend.py` — the acceptance oracle — **SKIPS 2914 of its 10708
checks (27%)**, almost all vertical, at the two tiers we ship alongside 2×. A
skip is never a pass. One capture per tier clears it permanently.

**INI:** none. **Instrument:** `tools\uimap\emu\measure_lineh_tier.py`.
**Full procedure:** `tools\research\_incoming\lineh-tier-capture-procedure.md`.

**IN-GAME ACTION (~2 minutes).**
1. Load your usual test city.
2. Click **Graphs** in the left-hand mayor-mode button column.
3. Click **`Population by Age`** (middle column of the grid). Nine legend rows
   read `1-10` … `81-90`. **Say "captured?" and wait** — the capture is taken
   with `tools\capture\CaptureWindow.exe` (PrintWindow; it never steals your
   foreground and never takes a full-screen shot).
4. Click **`Garbage`** (middle column). Nine Garbage rows. Wait for capture 2.
5. **Do not move or resize the Graphs window between the two clicks.**

* **YES (usable):** the script prints
  `CLEAN: every row renders exactly ONE line` and emits a `lineH` for the tier.
* **NO (unusable):** any row shows 2 ink bands; below three usable row pairs the
  script **refuses outright** rather than reporting a number.

**POSITIVE CONTROL — the wrap counter is proven non-blind.** Run against the
existing 1× Garbage capture it prints `[1,1,1,1,1,1,1,2,2]` — it finds exactly the
two labels the repo independently records as `STOCK_WRAPS` ("Waste to Energy",
"Garbage Pollution"), which it was never told about. A row of all-1s from a
counter that *can* see a 2 is a measurement; from a counter that cannot, it is
nothing.

**Second control, in the log, and it is load-bearing.** Before capturing, confirm
`SC4UIScale.log` carries
`CodePatches: graph legend budget x1.50 (8 of 8 sites) - strip …`.
If that patch declined, the legend is laid out in the stock 72px box, the by-Age
labels are no longer guaranteed one line, and the number would be filed under the
wrong point size.

**Free with the same launch:** the log's `CHARTGEO` line prints `WIN[0xA8]` at
1.5× — that is exactly what unknown **U8** asks for, and its origin decides **U6**.
Keep the log.

---

### L-A5 — #123: does the disaster ring seat correctly at 1.5×?

**Question.** After v2.71.8's seat-scaling, does the disaster flyout's ring/bar
assembly sit on its button at 1.5×?

**Why offline cannot answer it.** `emu_subplace_model.py` validates the
*placement arithmetic* against the game's own `sub_79AD00`, and
`flyout-sim\gate_subnative.py` is green at all three tiers. Both are arithmetic.
The ring, the strip and the bar are **one welded shape** whose junction seam is a
pixel relationship between three separately-blitted sprites — the sub-flyout RING
LAW. No gate here composites them.

**INI:** none (defaults are correct — `SubRingDX`/`SubRingDY` are deliberately
commented out so the DLL derives 19/−4 at 1.5×).

**IN-GAME ACTION.** City view → **God Mode** button → open the **Disaster**
flyout. Leave it open ~5 seconds, then hover across two or three of its
thumbnails.

* **YES:** the keyring's hole frames the selected button, and the ring→bar
  junction has no seam or step.
* **NO:** the ring sits off the button, or a 1–2px seam shows at the junction.

**POSITIVE CONTROL.** The very same flyout at **2×** must be clean — the whole
family is user-confirmed there. A defect that also shows at 2× is a *different*
defect and must not be filed under #123.

**BONUS — this also arms L-A2 the old way.** Opening the Disaster flyout calls
`EnsureBufferClassBltHook()` at ~~`:6152`/`:6274`~~ **`:6444`/`:6579`
(re-pinned 2026-08-16; defined at `:6119`, both calls inside `SubPlaceDetour`
`:6213`)**. **If you skipped P0, do L-A5
FIRST**, then the `ThinBlt` capture has a hooked slot 29 regardless of whether the
self-arming block is in the binary.

---

### L-A6 — #155 residual: 347 art cells 2px taller than their window at 1.5×

**Question.** Of the 460 static-dialog buttons, 347 have an art cell **2px taller**
than their window at 1.5× (`CellUnit` snapping the *height* of a *horizontal*
four-state strip — a 20px sheet, `20 % 4 == 0`, so 30 became 32). Does any of that
show?

**Why offline cannot answer it.** The known lever, `--height-exact-group`, is
**not** applied to the stock art group, and applying it globally would move 791 of
2280 sheets and put #143's white-seam fix back in play. That is a measured
decision to take deliberately — and it can only be taken if we know whether the
residual is *visible*. Tonight's `--height-exact-strips` experiment is the
cautionary precedent: arithmetically defensible, and it broke the "?" button.

**INI:** none.

**IN-GAME ACTION.** Open the static dialogs where these buttons live and look at
the **bottom edge** of each button for a 2px tear, dark line, or missing row:
the **region bubble** (the play button), the **Establish City** dialog, and any
**budget detail** dialog.

* **YES:** a thin tear or mismatched row along a button's bottom edge.
* **NO:** buttons look identical to 2×.

**POSITIVE CONTROL.** Same buttons at 2×, where the residual is **structurally
zero** (an integer factor makes the snap a provable no-op). If they look
identical at both tiers, the residual is invisible and stays a documented
non-defect. **Do not "fix" it on arithmetic alone.**

---

### L-A7 — #141: is the first city open disk-bound, CPU-bound, or page-faulting?

**Question.** The first city open of a session costs ~54 s with a large plugin
set. The one outstanding measurement is the **user-vs-kernel CPU split**.

**Why offline cannot answer it.** It is a wall-clock property of a live process.

**INI:** none. **Instrument:** `_tests\Trace-CityOpen.ps1` — it **only reads
counters** and never touches the game.

**IN-GAME ACTION.** Start the script *before* launching. Open a city
(**OPEN #1**), go back to the region, open a **different** city (**OPEN #2**).
That pair is the whole experiment.

* Disk-bound → `ReadTransferCount` climbs hard, CPU flat.
* CPU-bound → `UserModeTime` climbs, disk quiet. *(`SC4CPUOptions` pins the game
  to one core, so 100% of one core reads as ~6% on a 16-thread machine — do not
  misread that as idle.)*
* Page-faults → `PageFaults` climbs.

**POSITIVE CONTROL.** OPEN #2 is the control for OPEN #1. If #2 costs the same,
this is not a first-open warm-up at all and the whole framing is wrong.

**Cost: zero in-game time.** It rides along with everything above.

---

### L-A8 — #104/#105/#107: the shutdown spin

**Question.** After the game window closes, the process sometimes survives with
one core at 84–94%. What is the spinning thread executing — and **how often** does
it happen?

**Why offline cannot answer it.** Two reasons. (a) It is a thread's live EIP.
(b) **It is intermittent**: on 2026-08-03 two runs with byte-identical patch
configuration and identical user actions produced opposite outcomes (17:16 SPUN;
17:27 exited clean). That is fatal to how the bug was bisected — runs 6–13 gave
each config **one** trial, so every "CLEAN" in that truth table is a coin flip.
Deciding this needs **rates**, and rates come only from launches.

**INI:** `[UiSpike] SpinProbe=10` (seconds; hard-capped at 120).

**IN-GAME ACTION.** **Quit the game normally.** Never kill it — it runs elevated
and holds our DLL and dats open. Then look at Task Manager: did `SimCity 4.exe`
linger, and did a core stay pinned?

* **YES (a spin was captured):** `SPINPROBE … >>> HOT THREAD tid N: X of its Y
  samples were in the GAME IMAGE`, followed by a ranked `GAME-EIP` list. **One
  address ends the argument.**
* **NO (clean exit):** the process is gone within ~1 s and the CSV shows a
  `pending` row with no later `spun` row. Per `RecordShutdown`, *"a pending row
  with NO later 'spun' row means the process exited on its own = CLEAN"* — a real
  data point for the rate, not a wasted run.

**POSITIVE CONTROL — the probe reports its own.** If it saw nothing it says so,
explicitly, and refuses to be read as "nothing spun":

```
SPINPROBE … STRUCTURAL NULL - 0 samples from N sweeps (threads seen …,
opened …, open-failed …, ctx-failed …). This says the PROBE could not see,
NOT that nothing spun.
```

There is a second one for the framing: if samples exist but none land in the game
image, it prints *"the spin is in a LIBRARY, not in the game's own code — which
would refute #104's framing"*.

**Also note:** `SpinProbe=0` disables the `SC4UIScale-104.csv` telemetry
entirely (v2.67.0 made it opt-in), so a row written with the probe off is marked
`unknown` and **must not be counted as a clean exit**. Leaving `SpinProbe=10` set
across ordinary play is how #107 accumulates rates at no extra cost.

---

## 3. LAUNCH B — the 3× tier (CONDITIONAL — read the blockers first)

**Do not run this until the two blockers below are cleared.** As staged it would
test packages that are three defect-generations old, and the result would be
uninterpretable.

**BLOCKER B1 — the 3× ItemIcons pair is stale.**
`z_SC4UIScale_ItemIcons-3x.dat` is **Aug 3** and `ItemIconsSub-3x.dat` is
**Jul 29**, ~~while every other 15x/3x dat is **Aug 15 21:26**. That pair predates
**#149, #156, #157 and #160**. Rebuild them before any 3× eyes-on, or any icon
finding is a finding about August 3rd.~~

> **2026-08-16 — RE-MEASURED, AND THIS BLOCKER IS AN MTIME ARTIFACT. B1 DOES NOT
> BLOCK LAUNCH B.**
>
> **(a) The "every other" clause was false.** Exactly ONE of the fourteen tagged
> dats reads Aug 15 21:26. Measured from `tools\packages\{15x,3x}\`:
> SelectiveArt / ThirdPartyUI / WarriorUI **Aug 16 12:16** (both tiers);
> CamUI / SaveWarningUI **Aug 16 11:42** (15x) / **11:43** (3x);
> DialogStatic **Aug 15 21:26** (15x) / **21:27** (3x); and
> `ItemIcons-15x` + `ItemIconsSub-15x` **Aug 14 10:03**.
>
> **(b) An mtime is not evidence of stale ART.** Per #170, a DBPF file hash
> carries a header timestamp at offsets 25/29 and moves on every build, so the
> only honest comparison is PER-ENTRY PAYLOADS. Run against today's corpus
> (`preview-15x`/`preview-3x` regenerated **Aug 16 11:41/11:42**):
>
> | dat | entries | vs today's source |
> |---|---|---|
> | `ItemIcons-15x` (Aug 14) | 356 | **356 byte-identical** |
> | `ItemIcons-3x` (Aug 3) | 356 | **356 pixel-identical** |
> | `ItemIconsSub-15x` (Aug 14) | 130 | **130 byte-identical** |
> | `ItemIconsSub-3x` (Jul 29) | 130 | **130 byte-identical** |
>
> The 3x ItemIcons bytes differ *only* in deflate size (I-0x00000001 is 1068×174
> in both, 27,260 B in the dat vs 30,584 B in the corpus): that stage dir was run
> through `tools\dbpf\optimize_png.py`, whose whole job is "re-deflate staged PNGs
> at maximum compression" — pixel-preserving by construction. The Sub rows were
> proved by re-running today's `Upscale2x.exe` (Aug 15 21:03) over the 129 1x
> sources in `tools\itemicons\_work\` and diffing against the extracted dat; the
> 130th entry is the `MISSING_THUMB` I-0x144161ec, also byte-identical.
>
> **(c) Why nothing moved, structurally.** `grep -c 6a386d26` is **0** in all four
> derived lists (`cell-strips.txt`, `nine-slice.txt`, `no-snap.txt`, `tiled.txt`),
> and `build_itemicons_sub.py:107` calls the upscaler with `--factor` and
> `--normalize-names` and nothing else. #156/#157/#160 cannot reach an item icon.
> #149 is a runtime boot scan, not a dat rebuild. So "predates #149, #156, #157
> and #160" was true as a DATE and irrelevant as a CAUSE.
>
> **(d) The mirror-image error to avoid.** A draft of this correction argued that
> `ItemIcons-15x`/`ItemIconsSub-15x` (Aug 14) are "ALSO STALE" because they
> predate `nine-slice.txt` (Aug 15 11:25) and `no-snap.txt` (Aug 15 18:32), and
> that this poisons Launch A. Those two mtimes are real; the inference is not —
> it is the same mtime-for-content substitution, and row 1 of the table above
> kills it. Launch A's 1.5× icons are current.
>
> **Standing instruction.** Re-stage the four icon dats whenever convenient so
> the mtimes stop raising this alarm, but do **not** gate a 3× eyes-on session on
> it. If a future rebuild is ever claimed to matter, prove it the way (b) does —
> extract and diff the entries — never by reading a timestamp or a file hash.

**BLOCKER B2 — this panel cannot select tier 3 honestly.**
`ScaleTier::Decide` needs `880×3 = 2640 ≤ width` and `height/600 ≥ 3`, i.e.
**≥ 2640×1800**. Tonight's log reads:
`AutoScale: DirectX FullScreen - render res = monitor 2400x1600 (requested
3840x2160 ignored by wrapper)`. So 3× must be forced by hand
(`AutoScale=0`, `ScaleFactor=3.0`, manual dat + `FontStyle-3x.ini` staging in
**both** Plugins folders) — see §2b of the lineh procedure, which also names the
hazard this creates: a missed font copy renders the legend at 26 pt inside a 3×
box and files the number under the wrong point size, silently.

**What Launch B is worth once unblocked, in priority order:**

1. **U1 at 3×** — same Graphs capture as L-A4. Together with the 1.5× number it
   closes the oracle's 2914 skipped checks permanently. Mitigation for B2: copy
   the live `FontStyle.ini` next to the capture and pass it as `--fontstyle`, which
   turns the point size from an assumption into evidence.
2. **Our layer at 2400×1800 windowed** — never launched. START-HERE is explicit
   that the windowed-border finding does **not** exonerate our layer: the wrapper
   setting and our layer both changed between the failing and working cases.
   Expect any 3× breakage **at the BOTTOM (the dock)** first — height is the
   binding constraint and 1800 overhangs 1600 by 200px.
3. **L-A3 / L-A6 as integer-tier controls.** Every metric in this file is
   *required* to read zero at an integer factor. A 3× session is where that gets
   proved on screen rather than in Python.

---

## 4. THE INTEGER-TIER CONTROL, restated because it is the house law

> **An integer factor (2×, 3×) is structurally immune to most fractional-tier
> defects.** Edge-derived rounding is exact, `CellUnit` snaps are provable
> no-ops, `q | d` holds for every offset at `q = 1`. Therefore **any metric or
> observation in this file MUST read exactly zero at 2× and 3×, or it is
> measuring itself.**

Tonight a metric failed exactly this way and is recorded so nobody quotes it
again: *"band-mean luminance excess vs 1×: hat +13.7, people +12.6, and EXACTLY
0.000 at 2× and 3×"* looked like a clean integer-tier control. A verifier then ran
the control the finder never did — **40 random bands on 40 random sheets, no
defect selection: 0.000 at 2× in 40/40, at 3× in 40/40, and nonzero at 1.5× in
29/40.** That signature is a property of *all* fractional nearest-neighbour, not
of this defect. **The mechanism survived; that number is worthless as evidence
for it.**

The same discipline applies to every eyes-on item above: **the 2× look is not
optional politeness, it is the control.**

---

## 5. THE ONE-LINE FIX THIS AUDIT FOUND — a PROPOSAL, not applied

`[Probe] EdgeBlt` lives in the **identical** hook as `ThinBlt` —
`BltClassThunk`, buffer-class vtable slot 29 — but received **no arming block**
when `ThinBlt` got one at `:11759`. Setting `EdgeBlt=N` in a session that never
opens a god flyout is therefore a **guaranteed null**, and nothing in the log says
so. It is the same defect that burned two launches this week, still armed, one
key over.

**Proposed (behavioural — NOT applied here, per the standing order that every
behavioural change in this project requires eyes-on):** mirror the `ThinBlt`
block immediately after the `EdgeBlt` read at ~~`src\UiSpike.cpp:11744`~~ **`src\UiSpike.cpp:12046-12047`**, with its
own `s_edgeArmed` latch, calling `EnsureBufferClassBltHook()` and logging an
`EDGEBLT armed - buffer-class slot 29 hooked (orig=%p)` control line.

**2026-08-16: re-pinned and re-verified. The `EdgeBlt` ini read is at
`src\UiSpike.cpp:12046-12047`; the old `:11744` is unrelated Data Views legend
code. The `ThinBlt` block to mirror is the arming latch at
`src\UiSpike.cpp:12068-12082` (its ini read is `:12066-12067`). Finding still
UNFIXED: `EnsureBufferClassBltHook()` has only three call sites —
`:6444`, `:6579` (flyout birth / container Plot detour) and `:12074` (inside
`s_thinArmed`) — and no `s_edgeArmed` symbol exists in the file, so nothing
arms slot 29 for `EdgeBlt`.**

**Until that ships, the workaround is in this file:** `EdgeBlt` is only
meaningful in a session where `ThinBlt>0` **or** a god flyout has been opened.

⚠ And note what the ini already records about `EdgeBlt`'s ceiling even when it
*is* armed: measured 2026-07-30 with the hook live, **every destination through
this buffer class is PANEL-sized** (258×482, 383×156, 340×148 …), never
screen-sized. A zero from `EdgeBlt` is therefore **not evidence about a
full-screen element**. It is a panel-edge instrument only. This is the
"instrument scoped to the wrong channel" law, already paid for once.

---

## 6. GATE OUTPUT RUN THIS SESSION — the offline state the launch starts from

`gate_art_vs_window.py`, run 2026-08-15 while writing this file. Quoted because
L-A1 and L-A3 both lean on it, and because its integer-tier control is the point:

```
566 sheets priceable at 1x/1.5x/2x (of 566 shipped at 2x)
f=1.0   1579 image-bound nodes checked, 1038 SHORT
f=2.0   1579 image-bound nodes checked, 1038 SHORT
f=1.5   1575 image-bound nodes checked, 1034 SHORT

short at f=1 (STOCK, subtracted)      : 1038
NEW at f=2 (must be 0 - the control)  : 0
NEW at f=1.5 (the defect)             : 0

No 1.5x-only shortfall. The shipped art covers every shipped window at 1.5x
under this model, so the hairline is NOT an art-vs-window size mismatch - the
next instrument must look somewhere else.
```

**Read that correctly.** `NEW at f=2 = 0` is the control reading zero, exactly as
the house law demands. `NEW at f=1.5 = 0` is the finding: the offline art-vs-window
hypothesis for #162 is **refuted**, which is *why* L-A1 and L-A2 are the next
instruments and why they must be live ones.

Two gates are **RED** going in, both offline work, neither a reason to delay the
launch:
* `gate_namicons.py` — 392 orphans + 1 losing icon (`0xD6482A2C` ←
  `DBSSY_Notre_Dame_de_Paris_2025`). Task #152.
* `gate_patch_families_combined.py` — 5 unregistered tables
  (`kCostBoxHeightSite`, `kCostBoxWidthSite`, `kCostOriginBack`,
  `kCostOriginSite`, `kCostOriginStock`): the #159 cost-box family shipped
  without being added to the gate's `WIDTHS` map, so the gate is silently blind
  to a whole patch family — the exact gap #106 was built to close.

---

## 7. WHAT IS **NOT** WORTH A LAUNCH

Listed so they are not re-proposed. Each fails the "only a live run can settle
it" test.

| Item | Why not |
|---|---|
| `[Probe] IconFit` / `IconCover` / `IconCentreOff` | Doubly lazy (§1). Needs a god flyout open **and** `gStripProbe > 0`, which ordinary logging drains to zero. A null would be uninterpretable. |
| `[Probe] EdgeBlt` alone | Guaranteed null (§5), and panel-scoped even when armed. |
| `[Probe] Enabled` (DPROBE) with no aimed band | The bottom query panels animate every frame and drown the signal; the news ticker at abs x=534 scrolls 1px/frame. Aim `BandL/R/T/B` at a named window or do not arm it. |
| `gate_namicons` / `gate_patch_families_combined` red | Offline defects with offline fixes. No launch involved. |
| #124 (DVMAP snap consolidation), #125 (Data Views fill at 768) | Refactor and design decisions, not measurements. |
| Region rotation, message-queue tricks during city load, in-place render-surface resize, growing a game-owned buffer from our tick | **Measured dead.** See START-HERE §6 "Known dead — do not retry". |

---

## 8. RUN SHEET — everything the user has to do, in order

**Before launching (game closed):**

1. Rebuild and redeploy the DLL — `msbuild src\SC4UIScale.vcxproj -p:Configuration=Release -p:Platform=Win32` then `_tests\Deploy-OnGameClose.ps1`. *(If you skip this, drop step 6 below and do step 8 first instead.)*
2. `_tests\Set-StockCompare.ps1 -Mode Ours`, then `_tests\Test-DatIntegrity.ps1` — must be ALL PASS.
3. Copy `Documents\SimCity 4\Plugins\SC4UIScale.log` somewhere safe. It is deleted on the next launch.
4. In `Documents\SimCity 4\Plugins\SC4UIScale.ini`, **inside the sections that already exist** (no new section headers, no BOM): set `[UiSpike] SpinProbe=10` and `[Probe] ThinBlt=40`. Leave everything else at 0.
5. Start `_tests\Trace-CityOpen.ps1`, then launch the game.

**In the game (~15 minutes, one city session):**

6. Open a city. **You must reach the city view — no probe key is read anywhere else.** This is OPEN #1.
7. On the top-left mode cluster: **press and HOLD** the **Mayor Mode** (hat) button for 3 seconds, then the **My Sim Mode** (people) button. Report, for each: line visible at rest? line visible while held? Also say whether the **God Mode** button shows the line at rest — it should not.
8. Open the **Disaster** flyout (God Mode → Disaster). Leave it ~5 seconds, hover two or three thumbnails. Report whether the ring frames the button and whether the ring/bar junction has a seam.
9. Look down the **left edge of the god-mode tool column**: is the white rail continuous, or is there a break?
10. Open **Graphs** → click **`Population by Age`**, say **"captured?"** and wait; then click **`Garbage`** and wait again. Do not move or resize the window between clicks.
11. Open the **region bubble**, **Establish City**, and one **budget detail** dialog. Look along the **bottom edge** of the buttons for a 2px tear.
12. Go back to the region, open a **different** city — that is OPEN #2, the control for the load-time measurement.
13. **Quit the game normally. Never kill it** — it runs elevated and holds our DLL and dats open. Then check Task Manager: did `SimCity 4.exe` linger, and did one core stay pinned?

**After (game closed):**

14. Hand back `SC4UIScale.log`, `SC4UIScale-104.csv`, and the `Trace-CityOpen` CSV.
15. Set `SpinProbe` back to `0` **only if** you do not want the per-launch CSV row; leaving it at 10 is what accumulates the #107 rates from ordinary play, at no cost.

---

# ═══ SECTION 9 — THE 2026-08-24 OPEN SET (v4.0.41) ═══

**Everything above this line was written 2026-08-15 against v3.0.0 and its
per-defect entries are HISTORY — several of those defects shipped fixes long
since. The pre-flight in §0 and the hook-eagerness law in §1 still apply
verbatim; re-read both before any launch.**

After the offline unknowns sweep (register rows #3, #5, #8, #9, #11, #12, #13,
#18, #27 + the lower tier all closed), exactly this much is left that a live
run — and only a live run — can settle. Ordered cheapest-first.

## 9.0 What is ALREADY armable vs what needs a build

| Probe | Build needed? | Why |
|---|---|---|
| **A. Zot zoom pair** | **NO** | pure screenshots + a cheat |
| **B. Dispatch-indicator eyes-on** | **NO** | pure observation |
| **C. #16 hairlines at 1.5×** | **NO** | external capture only |
| **D. #22/#23 view-object differential** | **YES — one small lever** | `VIEWLIST` fires **once at frame 400** (`CodePatches.cpp:7321`), so it cannot do a before/after diff. Needs a `[Probe] ViewListRepeat=N` key re-running the existing enumerator every N frames, log-only, default 0. Nothing else changes |
| **E. #24 purple GZWinText** | **YES — one small lever** | needs a dump of `[this+0xE0]` (the font-style GUID slot, `SC4-UI-ENGINE.md` §Fonts) on a purple vs a black sibling |
| **F. #5 font-registry remainder** | **YES** | detour spec + arities already written (run journal, `wf_6e2e24df-377`) |
| **G. #4 draw-call census** | **YES** | spec is being produced by the running lane |

**Do A–C first.** They cost one launch, need no rebuild, and B/C are pure
"look at the screen" — the cheapest evidence in the project.

## 9.1 PROBE A — the zot zoom pair (closes row 23's grade, PARTIAL → DOCUMENTED)

The offline decode says zots are **world-anchored props sized by S3D vertex
metres**, so they must scale with the camera exactly like a building. That
prediction has never been checked on screen.

- **Setup:** any city with a powered building. Type the cheat **`TastyZots`**
  (registered `0x7E9A09`) — or simply bulldoze a power line and wait for the
  no-power balloon.
- **Do:** with a zot on screen, screenshot at one zoom level, then press the
  zoom-in key **once** and screenshot again **without moving the camera**.
- **YES (world-anchored, as predicted):** the zot roughly **doubles** in pixels
  between the two shots, like the building under it.
- **NO (refutes the whole row):** it stays the same pixel size — that would mean
  a pixel-fixed path we did not find, and row 23 must reopen.
- **NEGATIVE CONTROL, in the same two frames:** a **route-query signpost**
  (census row 16) is pixel-derived and must **NOT** double. If both double, or
  neither does, the comparison is broken, not the theory.

## 9.2 PROBE B — the seven dispatch indicators (eyes-on for row #8)

All seven categories were decoded offline; six are named. This confirms the
naming and settles the census-row-5 contradiction on screen.

- **Do:** cause a **fire** (and separately a **police** call) and look at the
  marker over the responding vehicle; then start a **U-Drive-It** mission and
  look at both the offer balloon and the marker over the car you drive.
- **Report, per marker:** does it show a **NUMBER** or a **PICTURE**?
- **Predicted:** fire (cat 0) and police (cat 1) draw a **number**; the MySim
  bubble (3) and the CSI offer balloon (4) draw a **picture**; the driving
  bubble (5) and the white **plumb bob** over your vehicle (6) are their own art.
- **Why it matters:** the number-vs-picture split is the load-bearing half of the
  offline decode, and it is visible without any instrument.

## 9.3 PROBE C — #162's two phantom hairlines, 1.5× only

Eight hypotheses are refuted (§D.1) and **every offline explanation is
exhausted**; the one live signal is an 18×2 band tiled 19× along the bottom edge
of a 340×155 buffer — 1× nine-slice geometry inside a scaled frame.

- **Setup:** force **tier 1.5×** (`_tests\Set-Tier.ps1 -Tier 1.5`), then launch.
- **Do:** photograph the **mayor's-hat** button and an **advisor portrait** with
  an **external camera or a second machine** — ⚠ **an in-process capture cannot
  see this** (the composited surface is GPU-only; nine builds proved it, §C).
- **Also capture the SAME two elements at 2×** in a second launch as the control:
  the hairlines are 1.5×-only, so their absence at 2× is what makes the 1.5×
  image evidence rather than a photo of a button.

## 9.4 PROBE D — the view-object differential (#22 in-world data-view tint, #23 underground/pipe views)

The instrument mostly exists: `VIEWLIST` already enumerates the renderer's four
pass lists (`renderer+0x188/0x18C/0x190/0x194`) — offsets independently
re-confirmed by this session's `cISC4ViewObject3D` reconstruction. It just fires
**once**, so it cannot diff.

- **Lever to add (small, house-style, log-only, default off):**
  `[Probe] ViewListRepeat=N` → re-run the existing enumeration every N frames.
- **Do:** with it armed, capture a baseline in the plain city view, switch to a
  **Data View** (and separately the **underground/pipe** view), and let it
  enumerate again.
- **The answer is the DIFF:** any object class present only while the view is on
  is that view's drawable. If the lists are identical, the tint is **not** a view
  object — that is a real answer too, and it points at the terrain/material path.
- **POSITIVE CONTROL:** the enumeration must print a non-zero `GRAND TOTAL` in
  both captures. A zero total means the enumerator did not run and the diff is
  meaningless — do not read an empty diff as "no difference".

## 9.5 PROBE E — why GZWinText renders purple under runtime-only scaling (#24)

- **Lever to add:** dump `[this+0xE0]` (GZWinText's font-style GUID, written by
  `SetFontStyleByGUID`; see §Fonts) for a **purple** control and a **black**
  sibling in the same window, log-only.
- **Predicted:** purple = the fallback GUID `0x68963C4C` (i.e. the style lookup
  missed), black = a real style. If both carry the same GUID the cause is not the
  style binding and the row must be rewritten.

## 9.6 The standing law for all of the above

Every one of these entries names its positive control **because a null without
one is a refusal, not a finding** — the rule §1 of this file exists to enforce,
and the rule this session broke once more: an archive scan reported "zero plugin
archives" purely because it looked at a path that does not exist on this machine
(Documents is OneDrive-redirected). **A scan of nothing returns a confident
zero.** Before believing any negative below, quote the line that proves the
instrument ran.

---

## 9.7 RESULTS — the 2026-08-24 launches

**PROBE A (zot zoom pair) — ✅ CLOSED, prediction confirmed.** Zots scale with
the camera; census row 23 is now **DOCUMENTED**. ⭐ The run delivered a better
negative control than the one specified: the **blue dispatch balloons appear in
both frames at the same pixel size** while the zots grow, so a single image pair
proves *world-anchored* for zots and *pixel-fixed* for the dispatch family, each
acting as the other's control. Full account in
`tools/research/overlays/row-23-zots.md` §5.

**PROBE D (view-object differential) — ✅ INSTRUMENT WORKS, drawable NAMED.**
13 view objects in the plain city view → **15** after switching to a data view.
The added class is vtable **`0x00ABB614`**, absent from the baseline: a five-slot
`cISC4ViewObject3D` (Draw `+0x0C` = `0x007DC9F0`, default Pick `+0x10` =
`0x00735290`, `+0x14` null) constructed at `0x7DCC10` with **16.0f** cell
constants and a packed half-alpha colour `0x80C000C0`. Still open: which view owns
which instance — one more capture toggling views **one at a time**.

> ⚠⚠ **THE FIRST ATTEMPT AT PROBE D PRODUCED A SILENT NULL AND COST A LAUNCH.**
> `[Probe] ViewListRepeat` was read, but the probe that honours it installs only
> under `MissionBubbleFx >= 3`, so the log had no `VIEWLIST` line and **nothing
> said why**. This is verbatim the defect §D.2 of the register already recorded
> against `[Probe] EdgeBlt` — *"lazy and not self-armed — a guaranteed null with
> no warning"* — written into a NEW probe one day after that entry was read.
> **THE RULE, now enforced in code: a probe key MUST arm its own probe.** When
> adding a probe, trace the install chain to its gate before asking for a launch,
> and make the arming line print its own positive control.

**PROBE B (dispatch indicators) — ✅ CLOSED 2026-08-24. NO DEFECT; the
number-vs-picture split is CONFIRMED, and the suspected regression did not
reproduce.**

The 1x control was run and the pins **do** carry numbers — a purple pin reading
**4** and a yellow pin reading **5** (with a fire-helmet glyph above the digit),
plus a plain red helmet pin carrying **no** number, and a `4 available` tooltip.
Crucially the 2x capture **also** showed a numbered pin (a white **4** over the
dispatch district), so numbers are present at BOTH tiers and the earlier
"numbers went away" impression is **not** a scaling defect. What the pair
actually demonstrates is the decoded behaviour itself, on screen:

- some pins draw a **NUMBER** (the deployed-unit count over the station) —
  register #8 categories 0/1/2, rendered via `rec+0x10` through `'%d'` at
  `.rdata 0xA8281C`, gated on record flag bit 1;
- others draw a **PICTURE** only (the helmet / car / portrait glyph families).

Both kinds are visible simultaneously in the same frame at both tiers, which is
exactly what the offline decode predicts and is the observation that closes the
grade debt. ⚠ Still NOT settled by this pair: which *category id* owns which pin
colour — the colours seen (purple, yellow, red) do not map cleanly onto the
decoded art table (fire = red `0x144161A1`, police = blue `0x144161A2`, MySim =
purple `0x144161A3`), and a dark screenshot is the wrong instrument for a colour
claim. Treat the colour→category mapping as OPEN.

**Original hypothesis, retained as a refuted lead:**
The numbered pin (a "4") sits over the dispatch **station**, showing units
deployed — consistent with categories 0/1/2 drawing a NUMBER. But the user
reports numbers **missing from the pins** at 2x. That is a scaling-defect
hypothesis, not a grade confirmation, and it needs the 1x control:

- **At 1x**, open the Fire dispatch tool and look at the pins over deployed units.
- **YES (defect real):** numbers visible at 1x, absent at 2x ⇒ the number draw
  (rec+0x10 through `'%d'` at `.rdata 0xA8281C`, gated on record flag bit 1) is
  being lost at scaled tiers — a NEW open defect, and the first one this arc.
- **NO:** numbers absent at 1x too ⇒ nothing is broken; the pins simply only
  carry a count in some states.
- **CONTROL:** the "4" over the station must be visible in BOTH captures — if it
  is missing at 1x as well, the comparison is void.


---

## 9.8 RESULTS — the all-data-views capture (2026-08-24)

### ⛔ NEGATIVE RESULT that kills the follow-up plan (#22/#23)

24 enumerations across a session in which the user cycled **every** data view.
Totals: 13 → (one void walk) → 13 ×8 → **14** → 14 for the remaining fourteen
dumps. **Exactly ONE change in the whole session**: `0x00ABB614` +1 at 11:38:28.
It never disappeared, never re-added, and **no other view produced any delta at
all**. Eight distinct vtables were seen; seven are in 23/23 dumps.

**Therefore counting view objects CANNOT identify which view owns which
drawable, and the plan in §9.4 ("one capture toggling views one at a time") is
dead.** Two readings survive and the count cannot separate them:

1. `0x00ABB614` is ONE overlay object, created lazily on first data-view use and
   then **re-parameterised** per view — which fits its constructor exactly (a
   packed colour at `[+0x2C]`, 16.0f cell constants). Every later view reuses it,
   so the population never changes.
2. The in-world tint is **not a view object at all**, and `0x00ABB614` is an
   unrelated one-shot.

**The discriminator is no longer a count — it is the COLOUR FIELD.** Next probe
must log `[obj+0x2C]` (and ideally `[obj+0x1C..0x28]`) for every `0x00ABB614`
instance on each enumeration. If that dword changes as the view changes,
reading 1 is proven and the row closes; if it never changes, reading 2 is proven
and the hunt moves to the terrain/material path. **Do not ask for another
counting capture.**

### ⚠ LIVE DEFECT CONFIRMED — the deployment count overlaps the hat at 2x

User-supplied 2x crop: on the fire-dispatch pins the **helmet art and the count
digit overlap**; the digit should sit BELOW the hat. At 1x the same pins render
correctly (helmet above, digit below, clearly separated).

**This is not a new discovery and that is the important part** — the project
already diagnosed it, and the fix is ALREADY APPLIED AND LIVE. `kCsiQuad` carries
`{ 0x0046CB09, 14.0f, "count plate height (text categories)" }`, whose own
comment reads *"at 2x the glyphs are twice as tall inside a quad that is still 14
— and the number under the deployment hat disappears"*, and the live log confirms
it ran: `CSI indicators x2.00 … count plate height 14.0 -> 28.0 px (text types)`,
11 immediates applied. That entry also carries a `WHY THIS IS BACK AFTER BEING
REVERTED` note, so it has been wrong at least once before.

⇒ **Scaling the plate HEIGHT is necessary and not sufficient.** The height now
matches the glyphs, but the plate's PLACEMENT relative to the icon is still
stock, so the taller plate grows upward into the helmet. Candidate levers, read
this session from the text-category setup:

```
0x0046CAF0  fild [esp+0x48]          ; MEASURED text width  -> +0xD0
0x0046CB03  mov  [esi+0xD4], 14.0f   ; plate height         -> ALREADY SCALED
0x0046CB0D  mov  [esp+0x24], 0.3f    ; <-- CANDIDATE: normalised placement
0x0046CB15  mov  [esp+0x20], 0.0f    ; <-- its partner
0x0046CB1D  mov  [esp+0x7C], 0xA80810
```

**Do NOT patch `0.3f` on this reading alone.** Two facts must come first: what
consumes `[esp+0x20]/[esp+0x24]`, and whether the overlap is the plate moving up
or the *icon* growing down (the category-3 icon immediate is also scaled, 32→64).
The 1x/2x pair already in hand is the control for any candidate fix.


## 9.9 CLOSED 2026-08-24 — the emergency-pin digit (v4.1.0)

Eleven launches end-to-end, closed by measurement: DISPATCHQUAD captured the
pin/digit quads at both tiers, the subtraction named two stock immediates
(box 14 / seat 9 in `0x5F1D00`), `ApplyPinDigitScale` ships them ×f coupled to
SIGNPOST-applied. User-confirmed. Probes disarmed in the live ini
(`DispatchQuad=0`, `ViewListRepeat=0`, `CsiCountPlate=0`); all three levers
remain in the DLL for future sessions. The five silent-null launches and the
two flooded captures along the way are written into REGRESSION.md as laws.
