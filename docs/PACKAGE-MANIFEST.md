# SC4UIScale — SimCity 4 UI Scaler

**Makes SimCity 4's interface usable on a high-DPI screen.** The game's UI was
designed for 1024×768; on a modern monitor the world still looks fine but the
buttons, panels and text shrink to the point of being unreadable. This plugin
draws the **UI elements** larger at 1.5×, 2× or 3× while the game keeps
rendering the world at your native resolution.

It is **not** whole-frame upscaling. The world stays sharp.

For **SimCity 4 Deluxe 1.1.641** on Windows 8+, implemented as a gzcom-dll
plugin (`SC4UIScale.dll`) — the same mechanism as SC4Fix, memo's DLLs and the
null45 mod family. It loads from `Documents\SimCity 4\Plugins\` (the
install-dir `Plugins\` works too).

> **Installing?** Grab the ready-built bundle from
> [Releases](../../releases) — the repository itself ships the *generators*,
> not the artwork. See [Building the packages](#building-the-packages) below.

~~This repository also contains `SC4TouchControls`, a separate multi-touch camera plugin from the same work. It is currently **not built or shipped** — see `VERSION-HISTORY.txt` — and is being rewritten to be independent of UI scaling.~~

⚠ **CORRECTED 2026-08-16 — THE PROJECTS SPLIT ON 2026-08-06, AND THE TOUCH PLUGIN DID SHIP.**
`SC4TouchControls` is not part of this repository. It is the sibling project `..\SC4Touch\`
(`..\SC4Touch\src\SC4TouchControls.sln`), split out of this working tree on 2026-08-06
(`START-HERE.md:34-37`, `..\SC4Touch\README.md:5`) because the shared tree repeatedly leaked
touch content into this project's public release — `_packaging\Test-NoForeignContent.py:36-38`
now flags `SC4TouchControls|TouchInputHandler|GestureEngine|CameraController` as a LEAK here.
The two trees reference no file in each other: the touch `.vcxproj` builds against its own
`..\SC4Touch\vendor\`, and the only overlap is byte-identical *copies* of `Logger.*` and
`SC4VersionDetection.*`. `src\SC4UIScale.sln` here declares exactly one project,
`SC4UIScale.vcxproj`. Nor was it "not built or shipped" — v1.0.4/v1.0.5 shipped frozen and the
line has reached v1.0.13 in `..\SC4Touch\dist\`; this sentence contradicted line 27 of this
same file. Two **pre-split** touch binaries do still sit in the working tree, at
`build\Release\SC4TouchControls.dll` and under `_working-backup\` — both trees are gitignored
(`.gitignore:26-27`) and neither is a source or a build path. Do not reintroduce a dependency
on the touch project.

⚠ The rest of this README's touch material was stale for the same reason. Corrected in place
below, each with its own dated note: the *Touch controls* item, the frozen-bundle sentence,
the repository-layout list (`src\`, `dist\`), the Files list, the msbuild command and the
Deploying section. **Still UNCORRECTED — no verified replacement yet:** the two
`SC4TouchControls.dll` / `.ini` rows in the *Deployment map* table below, which name
`dist\SC4TouchControls-v1.0.4\` and `src\` as sources in this project. Neither path exists
here; treat those two rows as void until they are re-derived from `..\SC4Touch\`.

Two feature families, **now in two separate DLLs** (split by user order so the
shipped touch product can never be destabilised by scaling work):

1. **Touch controls** — `SC4TouchControls.dll` **v1.0.4, SHIPPED, FROZEN.**
   One finger = the mouse, two-finger pan, pinch zoom, twist rotate.
   ~~The frozen bundle is `dist\SC4TouchControls-v1.0.4\`; its DLL hash is asserted by `_tests\Test-DatIntegrity.ps1` so scaling work cannot silently touch it.~~

   ⚠ **CORRECTED 2026-08-16.** Neither half is true any more. The frozen bundle lives in the
   sibling project (`..\SC4Touch\dist\SC4TouchControls-v1.0.4\`), not in this repo's `dist\`,
   which holds only `SC4UIScale-*` bundles — and **this project's test suite asserts nothing
   about it**: the frozen-bundle hash assertions were deleted on 2026-08-06 because a suite that
   fails when a *different* project's files move is not testing this project
   (`_tests\Test-DatIntegrity.ps1:336-341`). The freeze still stands; it is `SC4Touch`'s to
   assert. All this suite still does about that DLL is *note* whether a foreign copy is sitting
   in the `Plugins\` folder we deploy into — a bare `Write-Host`, reported and never gated
   (`_tests\Test-DatIntegrity.ps1:332-335`, rationale at 325-328). Do not read that note as a
   guard.

   See *Touch controls* below.
2. **UI scaling** — `SC4UIScale.dll` ~~**v2.97.1** (2026-08-13)~~ ~~v3.0.0 (2026-08-15)~~ **v3.0.2** (2026-08-17, #182 manual-tier sync + probe hardening; `src\SC4UIScaleDllDirector.cpp:49` now reads `"3.0.2"`).
   ⚠ *This line has gone stale repeatedly — it sat at v2.81.1 through
   seven shipped releases (v2.86.0–v2.92.0), then at v2.92.0 through five
   more (v2.93–v2.97), and the previous warning here had itself decayed
   into quoting the same number as two different past values.*
   **`UISCALE_VERSION_STR` in `src\SC4UIScaleDllDirector.cpp` is the only
   source of truth** — check it there, not here, and treat any mismatch as
   this line being wrong. ⚠ And check the **shipped binary**, not just the
   source: v2.96.0's release notes claimed the string had been corrected
   while the macro still read `2.93.1`, so three releases logged a version
   that was not running (fixed for real in v2.97.0, verified by finding the
   literal `SC4UIScale v2.97.1` in the deployed DLL's bytes).
   The game
   renders at **native high resolution** while the **UI elements are drawn
   larger**. Not whole-frame upscaling (tried in v2.0.x and rejected — it
   blurs the world too). Owns `SC4UIScale.ini` + `SC4UIScale.log`.
   See *UI scaling* below.

   **Shipping scale factors are 1.5, 2 and 3 only, and UI scale and TEXT scale
   are LOCKED 1:1** — settled by the user 2026-08-03 (#97). Text is **not** a
   user-facing setting, and above 3x is BACKLOG, not supported. The one axis
   that can move independently is the U-Drive-It mission bubble (ceiling
   `B ≤ 2 × UI`). The justification is the 26-entry MIXED risk register in
   `tools\research\SCALING-AXES.md` §2.2: 26 named places where a box is sized
   by its text or a text is wrapped to its box, any of which unpairs silently
   if the two factors diverge.

## Licence and dependencies

**This project's own code is PUBLIC DOMAIN — CC0 1.0, no rights reserved, no
attribution required.** Copy it, change it, sell it, ship it closed-source.
None of that needs permission or credit. `SPDX-License-Identifier: CC0-1.0`

**It statically links exactly two third-party libraries, and you must honour
their terms if you redistribute a build:**

| Component | Licence | Obligation on you |
|---|---|---|
| [**gzcom-dll**](https://github.com/nsgomez/gzcom-dll) — Nelson Gomez | **LGPL-2.1-or-later** | Ship its source and let recipients relink. Publishing this project's full source satisfies it. Changes to gzcom-dll itself stay LGPL. |
| **MinHook** — Tsuda Kageyu | **BSD-2-Clause** | Reproduce its copyright notice and disclaimer in your distribution. |

That is the complete list. This project does **not** use
`0xC0000054/sc4-resource-loading-hooks`, any other `sc4-*` plugin,
`memo33/*`, or `nsgomez/scgl` — verified by search across `src\`, zero
matches, and the only third-party `<ClCompile>` entries in the vcxproj are the
two above.

SimCity 4 and its assets belong to **Electronic Arts**; this is an unofficial,
unaffiliated mod containing no EA code. The scaled art and font files it
generates are derived from a user's own installation, are not covered by the
CC0 dedication, and are excluded from the published source.

→ **Full detail, pinned commits and exact obligations:
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md)** · dedication text:
[`LICENSE`](LICENSE)

### Read these first (they are the project's executable memory)

| Doc | What it is |
|---|---|
| **`HANDOFF.md`** | **Start here after any break** — current deployed state, what shipped and the law it taught, how to verify, what is open, and the standing constraints |
| **`tools\research\METHOD.md`** | **The method northstar** — the docs are the SDK, decompile for instructions, document the novel. Carries the instruction hierarchy (docs → SDK headers → live instruments → disassembler → experiment), the canonical PRE-FLIGHT checklist, the doc-routing table (where a new fact goes), the decompilation playbook, and the write-back contract |
| `_tests\REGRESSION.md` | The runbook: suites, per-fix expected log lines, and the trap signature that means each fix regressed |
| `_tests\SCENARIOS.md` | **The scenario matrix** — the axes every fix must be tested across (tier, mod state, game mode, panel lifecycle, render mode, input) and the gotchas that live on each. Five bugs in one session were caused by an untested axis, not by bad code |
| `tools\research\TRIAGE.md` | **START HERE for any new UI defect.** Symptom → mechanism → lever, with the precedent for each; the first five (cheap) measurements in order; the null checklist; what each lever can and cannot reach; and the dead ends never to retry. It exists to cut the time from "user reports a symptom" to "the plan is written" — every row was paid for by a shipped fix |
| `tools\research\SC4-UI-ENGINE.md` | **The engine model** — an SDK-style reference to SC4's GZWin UI: the window tree and the parentage rule, the widget catalogue with each class's scaling rule, the `.UI` format, the four art-binding paths, the HTML text engine, the placement/timing laws, and every exe VA this project has identified. Read it before predicting how an unseen panel will behave |
| `_tests\RUN-SHEET-NEXT-SESSION.md` | **The next in-game session as one ordered script** — what to verify (with what "correct" looks like), what to measure (with the exact ini keys and expected log lines), and what is known-broken so you don't re-report it |
| `tools\research\_checkpoints\` | **Audit digests + bug intake** — the five 2026-07-29 audits (coverage matrix, code-created/non-city, tier generality, lifecycle, plus two disassembly trails) and the triaged user-report intake. Also where every agent checkpoints its work in progress |
| `tools\research\MAYOR-MODE.md` | Current session state + the city-mode backlog, newest block first |
| `tools\research\UPSTREAM-*.md` | Developer callouts for every third-party mod whose data we override (standing order) |

---

## Touch controls

### Gestures

| Touch | Result |
|---|---|
| One finger | The mouse, unchanged: tap = click, drag = draw with the active tool, press-and-hold = right-click (all via stock Windows touch promotion) |
| Two-finger drag | Pan via the game's **own right-button-drag pan**: the plugin drives the real cursor + right button, so speed and feel are exactly the native mechanics |
| Pinch out / in | Zoom in / out one step (SC4's 5 discrete zoom levels), max ~4 steps/sec |
| Two-finger twist ±25° | Rotate the view 90°, with a settle window between snaps |
| Second finger lands mid tool-drag | The in-progress drag is cancelled safely (ESC only fires if a drag is actually captured), then the gesture starts |

A two-finger gesture does exactly **one** thing: an intent classifier compares
how much the fingers move together (pan) vs relative to each other (pinch/twist,
split radial-vs-arc), and the first intent to win owns the gesture until a
finger lifts.

Mouse, keyboard, and pen input are never intercepted. In the region view and
menus the touch layer is dormant (stock behavior). If anything misbehaves, set
`Enable=0` in the ini or delete the DLL — the game is untouched without it.

### Architecture (one paragraph each)

- **SC4TouchControlsDllDirector** — gzcom plugin director. On `PostAppInit` it
  subscribes to PostCityInit/PreCityShutdown, resolves the game HWND via
  `cIGZFrameWorkW32::GetMainHWND()`, and installs the touch subclass. Each city
  load it walks `cISC4App::GetMainWindow()` → child `0x6104489A` → child
  `0x9A47B417` QI `cISC4View3DWin` (the chain memo33's 3d-camera DLL uses on
  1.1.641). Every step is guarded: any failure logs and leaves the game stock.
- **TouchInputHandler** — `SetWindowSubclass` on the game window. Touch
  `WM_POINTER*` events are fed to the gesture engine; its verdict either forwards
  the message (Windows promotes single-finger touch to mouse) or consumes it
  (multi-finger gestures). Pointer APIs are `GetProcAddress`-resolved.
- **GestureEngine** — pure-logic state machine (`Idle → SinglePassthrough →
  Gesture → GestureCooldown`). Contact state is rebuilt from
  `GetPointerFrameTouchInfo` on every event — a missed POINTERUP cannot wedge it —
  plus a 700 ms stale timeout as the final net. Pan is always live; the first of
  pinch/twist to fire owns the discrete channel for that gesture (no crosstalk).
- **CameraController** — `ZoomIn/ZoomOut/RotateLeft/RotateRight` for steps. Pan
  (default `PanMode=2`) drives the game's native right-drag pan with the REAL
  cursor and button (`SetCursorPos` + `SendInput`, foreground-guarded, button
  always released on every exit path) — required because SC4 POLLS the physical
  cursor during its pan and ignores posted mouse messages (verified empirically;
  a pure `PostMessage` right-drag does nothing). Being in-process, `SetCursorPos`
  and the game's `GetCursorPos` share one DPI context, so coordinates always
  agree. `PanMode=1` (closed-loop `PickTerrain`/`SetScrolling` anchor) and
  `PanMode=0` (velocity) remain as fallbacks.

### Tuning / calibration

All knobs are in `SC4TouchControls.ini` (documented inline). The ones that may
need a first-run calibration on new hardware:

- Pan direction wrong → flip `InvertPanX` / `InvertPanZ`.
- Pan too slow/fast or oscillating → adjust `PanGain` (closed loop) or switch
  `PanMode=0` and tune `PanSpeed`.
- Rotation backwards → `SwapRotateDirection=1`.
- For diagnosis set `LogLevel=2` (gesture steps) or `3` (every pointer event).

---

## UI scaling

**The product northstar:** run the game at the display's native resolution and
draw the **UI elements** at 2x — more world on screen, UI readable at arm's
length. **The method northstar** (`tools\research\METHOD.md`): the docs are
the SDK, the exe is the manual, and novel work is documented the same session.
This had never been done for SimCity 4; the whole-frame alternative (render
small, stretch the frame) was tried first (v2.0.x) and rejected because it
scales the world too.

### Custom lots you install later are handled automatically (#149, v3.0.0)

This mod scales the menu strip's state cell, so **any custom lot installed
after our art packages were built** would otherwise draw its menu icon doubled
at rest and blank on hover. That is not a limitation we inherited - it is
caused by the scaling, confirmed by a stock control (our layer off: one icon,
visible on hover; our layer on: two icons that vanish).

**As a player you do not have to do anything.** At every boot the DLL indexes
every DBPF under `Plugins` - index reads only, no pixels, ~50-190ms - works out
which menu icons no package of ours covers, and enlarges those to the active
tier *before* any menu asks for them. Confirmed on real Simtropolis downloads
at both 2x and 1.5x.

Two things worth knowing:

* **A broken upload can still look wrong**, and it is the upload, not the
  scaler. Some lots ship a strip whose four states sit at a fractional pitch
  while the game reads `imageWidth / 4`, or ship no hover-border state at all.
  For those, `tools\itemicons\build_uncovered_icons.py` rebuilds a proper
  override package from the mod's own art. It rediscovers the set from YOUR
  Plugins folder, so it never goes stale - re-run it after adding lots.
* **A cardboard box is a missing dependency, not a scaling bug.** If a lot
  plops as a brown crate, its 3D model was not in the download. Check the
  listing's dependency list.

`tools\uimap\emu\sim_itemicon_states.py` will tell you, offline and before you
launch, whether a newly installed mod's icons are well-formed.

### The FOUR layers

The scaling stack is four cooperating layers (the fourth, exe byte patches,
was added once it was proven that some geometry exists only as immediates in
the code). Each is independently removable; together they produce a coherent
2x UI. **Everything ships as the DLL + ini + Plugins files — no game file is
ever modified.**

1. Runtime `cIGZWin`-tree scaler (`UiSpike.cpp`) — geometry.
2. **Data layers** — 2x art + edited `.UI` scripts, in tier-tagged packages.
3. 2x fonts (`FontStyle.ini`, whole-file replacement).
4. **Exe byte patches** (`CodePatches.cpp`) — for hardcoded constants:
   ~~the mayor-rating arrow reveal (7px/point), the tooltip 250px wrap width,
   and the HTML engine's font-size tables.~~
   **CORRECTED 2026-08-16: those three are real and still shipping**
   (`src\CodePatches.cpp:1025` `ApplyRatingArrowScale`, `:1080`
   `ApplyTooltipWrapScale`, `:3493` `ApplyHtmlSizeScale`) **but they are no
   longer the whole layer, and this is the only place in this README that
   describes layer 4 — reading it as the list is how a reader concludes "no
   patch exists here" where one does.** `CodePatches.cpp` now defines **19
   `Apply*` entry points — 18 patch families plus the shared
   `ApplyInsetSiteArray` helper** (`src\CodePatches.cpp:1025, 1080, 1135, 1275,
   1584, 1990, 2359, 2455, 2646, 2714, 2754, 2789, 2939, 2973, 3065, 3339,
   3493, 3540, 3816`; `:2714` is the helper, called from `:2761` and `:2770`).
   `START-HERE.md:19` puts the constant count at "~30 byte-patched layout
   constants". The `[UiSpike]` table below likewise documents only three of the
   **nine** patch toggles; the other six are `CostBoxPatch`, `AdviceRowPatch`,
   `BudgetButtonPatch`, `OrdinanceInsetPatch`, `BudgetDeptPatch` and
   `DataViewLegendPatch` (`src\Settings.cpp:79, 82, 83, 84, 85, 97`), all
   defaulting **on** (`src\Settings.h:165, 178, 189, 193, 196, 237`).
   **Enumerate the `Apply*` functions in `CodePatches.cpp` — never triage
   "is this constant patched?" against a list written in a doc.**
   All verify-before-write: an unexpected byte pattern skips that patch and
   logs, so a different exe build degrades instead of corrupting
   (`src\CodePatches.cpp:1048`, `:3511`).

### AutoScale tiers

`ScaleTier::Decide` picks the factor from the **render** resolution and
enables the matching package set (`-2x` live, the others renamed
`.x1-disabled`). Tier 1 = **true stock**: every scaling subsystem off, all
dats gated, FontStyle moved aside — the DLL must be indistinguishable from a
no-DLL install (isolation-tested). Tiers: 1x / 1.5x / 2x / 3x.

**Render resolution is not the requested resolution:** DirectX +
FullScreen/Borderless renders at the **monitor's native** mode (the wrapper
ignores the request); DirectX + Windowed and Software use the requested size.

### The three original layers, in detail

1. **Runtime cIGZWin-tree scaler** (in the plugin, `UiSpike.cpp`, configured
   by `[UiSpike]` in the ini). Walks the game's live `cIGZWin` window tree and
   scales the geometry of every city-view HUD panel subtree by `ScaleFactor`,
   re-anchoring each panel to its nearest screen edge. Safety engineering, all
   learned the hard way:
   - **Idempotent per-window scale records** — every scaled window is recorded
     and never scaled twice; records are **never cleared between cities** (the
     game reuses window objects across city loads).
   - **Tombstones** for game-managed dynamic controls — windows the engine
     creates/destroys itself are marked and left alone once identified.
   - **Liveness re-verification before every mutation** — a window is re-proven
     alive in the current tree before it is touched; stale pointers are never
     dereferenced.
   - **Throttled sweeps** — re-scans run on a timer budget, not per-frame.
   - **Deferred execution** — the tree is **never walked during PostCityInit**;
     all work is queued and runs after the engine settles.
2. **Data packages** — built by generators under `tools\`, deployed to
   `Documents\SimCity 4\Plugins\`, all tier-tagged. Entry counts are asserted
   by `_tests\Test-DatIntegrity.ps1`; **changing one is a deliberate act that
   requires updating that suite.** Current set (~~2026-07-29~~ **2026-08-16**):

   | Package | Entries | What it is |
   |---|---|---|
   | `z_SC4UIScale_SelectiveArt-2x.dat` | ~~345~~ **655** | 2x art + edited `.UI` scripts for every runtime-scaled window. Exclusive art is replaced **in place**; art SHARED with things that must stay 1x is **cloned** at `IID XOR 0x53430001` and only the scaled consumer is retargeted; `imagerect` extents are doubled wherever the art doubled |
   | `z_SC4UIScale_DialogStatic-2x.dat` | ~~220~~ **262** | Fully static-doubled dialogs (`area=` included) — the query/confirm/options family, which lives at main-window level and is never touched by the city sweep |
   | `z_SC4UIScale_ItemIcons-2x.dat` | ~~266~~ **356** | Toolbar picker icons (stock pool) |
   | `zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat` | ~~125~~ **130** | Icons owned by OTHER mods (submenus mod + CAM/Maxis landmarks) |
   | `zzz-SC4UIScale\z_SC4UIScale_MenuFix.dat` | 6 | Exemplar patches fixing CAM 4.0.1's broken submenu parents |
   | `zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-2x.dat` | 2 | A 2x copy of a **mod's own** `.UI` script + its own art, where a mod replaces a stock panel wholesale (CoriBoom Building Styles) |
   | `zzz-SC4UIScale\z_SC4UIScale_WarriorUI-2x.dat` | 4 | Same pattern for warrior's god-terraforming-in-mayor-mode scripts (mayor LANDSCAPE flyout + SIGNS & LABELS column) plus the mod's own two art assets (#94) |
   | `zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-2x.dat` | 2 | Same pattern for the two in-city quit/exit confirms, which the cyclone-boom save-warning mod replaces (v2.81.1) |
   | `zzz-SC4UIScale\z_SC4UIScale_CamUI-2x.dat` | ~~6~~ **22** | Same pattern again for the six dialog-static targets **CAM** replaces — plus CAM's own three dialogs (city info / civic / school query) and their bitmaps: 9 scripts + 13 art (#154, v2.97.0) |
   | `zzz-SC4UIScale\z_SC4UIScale_NamIcons-2x.dat` | **392** | NAM's own ItemIcon strips, upscaled from NAM's OWN bitmaps, never a stock lookalike (#139). Presence-gated on `NetworkAddonMod_Controller.dat`, no size check |
   | `zzz-SC4UIScale\z_SC4UIScale_CamGraphLabels.dat` | **1** | The one LTEXT (`0xFF5D2E9F`) CAM's Power/Water charts ask for and no installed archive provides (#147). Untagged and tier-independent — a string has no geometry |
   | `zzz-SC4UIScale\z_SC4UIScale_UncoveredIcons-2x.dat` | **varies** | Icons a custom LOT ships that no package of ours covered (#149). The count is **not** a constant of the project — it is however many this install has — so the suite deliberately asserts no number for it, and the package is simply absent when nothing is uncovered |
   | `z_SC4UIScale_WebText.dat` | 3 | Always-on LTEXT overrides matching the dead-link redirect |

   *(Counts corrected 2026-08-16 against `_tests\Test-DatIntegrity.ps1:145,154,155,178,184,194,207,212,257,285,289`;
   the 2026-07-29 figures were stale by four releases. FOUR packages were missing
   from the table — WarriorUI, NamIcons, CamGraphLabels and UncoveredIcons; the first
   three are deployed by `SyncDat` at `src\ScaleTier.cpp:1876/1885` and `:1832`.
   NamIcons carries no suite assertion, so its 392 was measured directly:
   `tools\dbpf\DbpfPack.exe --list tools\itemicons\out\z_SC4UIScale_NamIcons-2x.dat`
   = 392, same at -15x and -3x, and `tools\itemicons\nam-1x\` holds exactly 392 PNGs.
   The "381" in the `src\ScaleTier.cpp:233` comment is itself stale — do not copy it here.)*

   **The `zzz-` folder is not cosmetic.** See the LOAD-ORDER LAW below.

   ⚠ **~~The two~~ FIVE `zzz-` packages are DEPENDENCY-GATED** (`ScaleTier::kThirdPartyDeps`) —
   `SaveWarningUI`, `CamUI`, `ThirdPartyUI`, `WarriorUI` and `NamIcons`.
   *(Corrected 2026-08-16: `src\ScaleTier.cpp:184-241`, five rows — `:188`, `:197`,
   `:204`, `:218`, `:239`. Not all are `.UI` packages — `NamIcons` is pure art at
   NAM's own TGIs, `src\ScaleTier.cpp:232-233`. Other `zzz-` packages are NOT
   dep-gated: `ItemIconsSub` (`src\ScaleTier.cpp:1812-1813`) and `UncoveredIcons`
   (`src\ScaleTier.cpp:1832-1833`, rationale `:1825-1831`) call `SyncDat` with
   `match` alone, and `MenuFix` has no reference in `src\` at all.)*
   They contain copies of *another mod's* data, so `SyncStaticLayers` enables
   them only while that mod is installed — and, where our copy hard-codes the
   mod's exact rects, only while it is unchanged. Without that gate, uninstalling
   the mod would not uninstall it: our copy sits in `zzz-` and outranks
   everything, so the mod's UI would stay on screen. Measured 2026-07-31.
   **Any new package built from another mod's data needs its dependency row in
   the same change.** Reproduce the load order with
   `python tools\dbpf\who_owns_tgi.py <instance...>`.
3. **2x fonts** — `FontStyle.ini`, all **88 styles** at 2x point sizes (plus
   two stock-size `*Html` clone styles that exist only as HTML size-index
   sources — so the file on disk holds **90** lines; measured 2026-08-03, and
   the generator prints "88" because clones never enter its change list).
   Whole-file replacement, not a merge — every style must be
   present. The game probes `<install>\Plugins\`, then the install root, then
   falls back to the DBPF copy — proven by exe disassembly. Note this reaches
   `GZWinText`/button captions only: **rich text goes through the HTML engine
   instead** (see the FACTS below).

### Ini reference — `[UiSpike]`

~~All keys default OFF; the shipped touch layer never enables any of them.~~
**CORRECTED 2026-08-16: FALSE — many `[UiSpike]` keys default ON. Read the Default
column below and the LIVE ini, never this sentence.** Default-ON in `src\Settings.h`:
`AutoScale` (:134); **eight** byte-patches — `RatingArrowPatch` (:139),
`TooltipWrapPatch` (:156), `CostBoxPatch` (:165), `HtmlSizePatch` (:171),
`AdviceRowPatch` (:178), `BudgetButtonPatch` (:189), `OrdinanceInsetPatch` (:193),
`BudgetDeptPatch` (:196); plus `RegionZoom` (:88), `RegionTileSharp` (:117),
`ParentFrameRounding` (:158), `SpinFix` (:199), `WebRedirect` (:205), `ShowHook` (:254),
`EarlyDock` (:261), `EarlyBake` (:292), `PopupWrap` (:352), `SubFlyoutBornScale` (:225),
`SubFlyoutBornDock` (:232), `DataViewLegendPatch` (:237), `FlyoutBornOnOpen` (:247); and
the value keys `ScaleFactor = 2.0f` (:44), `CenterLeafMaxPx = 48` (:126),
`RegionZoomLevels = 5` (:106). Only the *scaling* switches (`ScaleAll` :45,
`ScaleRegion` :48, `MenuFlyouts`, `CenterSmallLeaves`, `DumpTree`, `ScaleWindowID`,
`LiveDumpMs`) default off.
⚠ **The table below is not an inventory** — it documents 13 of the ~39 keys
`src\Settings.cpp:49-98` parses. Neither is the header the shipped state: the shipped
`_packaging\SC4UIScale.ini` deliberately turns the scaling switches on —
`ScaleAll=1` (:33), `ScaleRegion=1` (:37).
*(The touch clause is a leftover from before the DLL split, but it is not false and must
not be rewritten to say the touch layer is gone: `[UiSpike]` is parsed by SC4UIScale's own
`src\Settings.cpp:48`, not by `SC4TouchControls.dll`. See the dated correction at the top
of this file for where the touch project now lives.)*

| Key | Default | Effect |
|---|---|---|
| `ScaleAll` | 0 | Master switch: scale every visible city-view HUD panel subtree by `ScaleFactor` and re-anchor to its nearest screen edge (idempotent per window) |
| `ScaleRegion` | 0 | Extend `ScaleAll` to the region screen (window `0x2AAB8CC1`, timer-polled with a settle delay — no city message fires on the region). Only active when `ScaleAll=1` |
| `MenuFlyouts` | 0 | Size-scale transient flyouts appearing under the fold-out menu container `0xAA32BCE6` (in place, no root move); the container and its persistent base strip are never touched. Only active when `ScaleAll=1` |
| `ScaleFactor` | 2.0 | The scale multiplier |
| `CenterSmallLeaves` | 0 | Small leaf windows keep their 1x size, centered in the 2x slot (for 1x art that cannot grow); flyout scaling always does this |
| `CenterLeafMaxPx` | 48 | "Small" threshold (original width AND height) |
| `DumpTree` | 0 | Dump the full cIGZWin tree to the log at city init (research/diagnosis) |
| `ScaleWindowID` | 0 | Single-window spike: scale just this window ID (hex accepted); 0 = off |
| `AutoScale` | 1 | Pick the factor from the render resolution and gate the package set to match (see *AutoScale tiers*). 0 = honour `ScaleFactor` manually and leave the layers alone |
| `RatingArrowPatch` | 1 | Byte-patch the mayor-rating arrow reveal (hardcoded 7px per rating point → `7*factor`) |
| `TooltipWrapPatch` | 1 | Byte-patch the tooltip's hardcoded 250px wrap width → `250*factor` |
| `HtmlSizePatch` | 1 | Scale the HTML engine's two point-size tables and retarget the popup builders' style GUIDs at the stock-size `*Html` clones. **This is what makes all news/story/tutorial/Credits text scale**; the three parts are coupled — read the runbook before touching any of them |
| `LiveDumpMs` | 0 | Diagnostic: dump every visible view child + subtree every N ms. **Leave 0** — at 1000 it wrote ~12 MB per session and hammers the disk during play |

Diagnostic sections used while measuring (all default off, see
`_tests\SCENARIOS.md`): `[Probe]` (the change-triggered DPROBE geometry probe —
**live-tunable, no restart**, unlike `LiveDumpMs`), and the `[Flyout]` /
`[Disaster]` instrument switches (`SubBltLog`, `RingCal`, `EmergLog`,
`StripDump`). `[Flyout] AdvisorHeal` is a superseded fallback, default 0.

The separate `[Scaling]` section is the **input remap for wrapper-scaled
rendering** (the superseded v2.0.x whole-frame approach: dgVoodoo presents a
small internal frame stretched to the panel; the plugin converts mouse
coordinates and hooks the game's cursor + screen-metrics APIs). It is identity
— no effect — when the presented size equals the internal size, so it is safe
to leave `Enabled=1`.

### Deployment map — which file goes where

| File | Source in this project | Destination |
|---|---|---|
| `SC4TouchControls.dll` (frozen v1.0.4) | `dist\SC4TouchControls-v1.0.4\` | `Documents\SimCity 4\Plugins\` |
| `SC4TouchControls.ini` | `src\` | `Documents\SimCity 4\Plugins\` (beside the DLL) |
| `SC4UIScale.dll` | `build\Release\` | `Documents\SimCity 4\Plugins\` |
| `SC4UIScale.ini` | (edited in place) | `Documents\SimCity 4\Plugins\` (beside the DLL) |
| `z_SC4UIScale_SelectiveArt-<tier>.dat` | `tools\selective-safe\` (2x) / `tools\packages\<tag>\` | `Documents\SimCity 4\Plugins\` |
| `z_SC4UIScale_DialogStatic-<tier>.dat` | `tools\dialog-static\` / `tools\packages\<tag>\` | `Documents\SimCity 4\Plugins\` |
| `z_SC4UIScale_ItemIcons-2x.dat` | `tools\itemicons\` | `Documents\SimCity 4\Plugins\` |
| `z_SC4UIScale_ItemIconsSub-2x.dat`, `MenuFix.dat`, `ThirdPartyUI-<tier>.dat` | `tools\itemicons\`, `tools\selective-safe\` | `Documents\SimCity 4\Plugins\zzz-SC4UIScale\` — **the subfolder is required** (load-order law) |
| `FontStyle-<tier>.ini` | `tools\fonts\` / `tools\packages\<tag>\` | beside the DLL; `ScaleTier` copies the active tier to the probed `FontStyle.ini` |

`ScaleTier` manages the tier gating itself at startup — it renames the
non-active tiers to `.x1-disabled` and copies the right font into place, so
deploying means dropping all tiers in and letting the DLL choose.

**Deploy while the game is CLOSED.** It holds the DLL and dats open, and it
runs **elevated** — a normal shell cannot kill it, and it must never be killed
anyway. The established pattern is a wait-for-close loop: poll `tasklist` for
`SimCity 4.exe`, copy on exit.

**The release bundle is built, not assembled by hand:** run
`_packaging\Build-Dist.ps1` and it produces `dist\SC4UIScale-v<version>\`
with a `Plugins\` tree you copy straight in, plus `README.txt`, `Install.ps1`,
`LICENSE.txt`, `THIRD-PARTY-NOTICES.md` and `SHA256SUMS.txt`.

It derives its file list **by parsing `_tests\Deploy-OnGameClose.ps1`** rather
than keeping a second copy. That is deliberate: a hand-maintained duplicate of
"what a working install contains" is what caused #58 (ThirdPartyUI frozen at an
old build epoch) and #116 (ItemIcons/ItemIconsSub never deployed at all). One
manifest, one failure mode.

`dist\SC4UIScale-preview\` was a hand-made July bundle carrying a months-old
DLL; **deleted 2026-08-05** so nobody downloads the wrong thing. Everything in
it was either regenerable or v2.5.5-era prose with stale figures.
~~The shipped touch-only bundle remains `dist\SC4TouchControls-v1.0.4\` — **frozen, hash-asserted by the test suite.**~~
**CORRECTED 2026-08-16: it is not in this project's `dist\`, and this suite does not assert
it.** The touch plugin became a separate project on 2026-08-06 (`START-HERE.md:35` — "Both
folders were one tree until 2026-08-06") and its bundles moved with it to `..\SC4Touch\dist\`
(`SC4TouchControls-v1.0.4` through `-v1.0.13`). The frozen-bundle hash assertions were deleted
in the same move; the tombstone is at `_tests\Test-DatIntegrity.ps1:336-344`. The freeze itself
still stands — it is that project's to assert, not ours. What this suite still does keep is the
foreign-DLL note at `_tests\Test-DatIntegrity.ps1:332-335`, which only REPORTS that
`SC4TouchControls.dll` is sitting in the `Plugins\` folder we deploy into. `dist\` here holds
only the `SC4UIScale-v*` release bundles.

### LAWS — the rules that decide every fix

These are the generalisable ones, each paid for with at least one bad build.
`_tests\SCENARIOS.md` has the full gotcha list; `_tests\REGRESSION.md` has the
per-fix detail and trap signatures.

**THE DOCS ARE THE SDK — READ BEFORE YOU REACH FOR THE DISASSEMBLER, AND
NEVER BEFORE A SHIPPED EXPERIMENT.** Maxis shipped no UI SDK, so this repo is
it. Consult in order: **our docs → the SDK headers in `vendor\gzcom-dll\` →
the live dump instruments → the disassembler → a shipped experiment.** The
last one costs a build plus a user's test session, and it is what gets
reached for when the first four are skipped (three failed ordinance-popup
builds, 2026-07-30, while the answer sat in our own anatomy doc and the
wrap API sat in `cIGZFont.h`). Full method: `tools\research\METHOD.md`.

**DOCUMENT THE NOVEL IN THE SAME SESSION.** Anything invented — a decoded
function, a new mechanism, a failure with a real mechanism behind it — is
written back before the session ends, in the file `METHOD.md` §3 routes it
to, with evidence, mechanism, and what the wrong models cost. Failed attempts
without their mechanism just get retried in a different order.

**A BLIT HAS THREE NUMBERS — SOURCE, CROP, DESTINATION — AND SCALING ANY TWO
OF THEM IS NOT A PARTIAL FIX, IT IS A NEW DEFECT.** v2.97.0 scaled a dialog's
windows (285→428) and its bitmaps (285→429) and left every `imagerect` crop at
285, so each row stripe painted two thirds of its row and the rest was bare
(#154). The rule was already written in `SC4-UI-ENGINE.md` §3.3; knowing it did
not help, because the code path that broke it never asked the question — the
builder's "did this control's art scale?" test read a plan built from the
**stock** art store alone, so mod-supplied art was permanently classified
unscaled there. **Enumerate a mechanism's inputs, then tick off the ones you
changed.** And when a test asks "did X happen?", check it can see every way X
happens.

**A GATE THAT MEASURES A SUBSET OF A MECHANISM'S INPUTS DOES NOT PARTIALLY
COVER IT — IT CERTIFIES THE FAILURE IT CANNOT SEE.** The gate written for that
same fix read the window and the bitmap and never the crop, and passed the
build that was wrong on screen. Make a gate read every input, or print which
one it is not reading. Its negative control should be **the artefact that
actually shipped** — extracting the script back out of the deployed package
produced 48 findings — not a hand-broken copy of the current build.

**A GATE THAT ONLY ASKS ABOUT YOUR OWN WORK CANNOT SEE WORK YOU NEVER
STARTED.** CAM's Village Hall info screen rendered at 1× under scaled fonts for
the entire life of this project with every gate green, because every gate asked
*"is what we built still correct?"* and that dialog was never built. Run the
census in the other direction too: enumerate what EXISTS and subtract what is
handled. `tools\uiscripts\winning_corpus.py` had been reporting it, unread,
since the day it was written.

**MEASURE, DON'T INFER.** Every measured value landed first try; every
screenshot-inferred one cost 2-3 builds and twice broke something that already
worked. Build the instrument (`[Probe]` DPROBE, `LiveDumpMs`, the blit traces),
read it, then act. If two symptoms contradict each other you are at the wrong
LAYER — move up one.

**A CONSTANT MEASURED AT ONE TIER IS A HYPOTHESIS, AND THE COMMENT SAYING
"FACTOR-INDEPENDENT" IS PART OF THE BUG.** `kSubNativeDX = 20` carried that
exact comment for months. It is really `btnW/2 - 27` — 20 at f=2, **43** at
f=3 — and the comment is what kept anyone from checking (#134, v2.86.0). The
tell is structural, not numeric: a constant that describes *the game's* layout
must scale with whatever the game scales. Before writing "factor-independent",
evaluate it at a second tier and say which tier it was measured at.

**AND WHEN TWO PATHS APPLY THE SAME LAW, A STALE CONSTANT DESYNCS THEM
SILENTLY.** Born (`SUBBORN2`) docks from the game's REAL native position; the
sweep predicts that native from the constant. At f=2 they agreed, so 2x was
always right and nothing looked wrong. At f=3 they differed by 23px — so the
sweep matched **neither** `atNative` nor `atTarget`, declined every 3x
sub-flyout, and took `gSubArrowAbs` (the back-arrow click zone, assigned ONLY
inside that sweep) with it. A visible 23px offset and an invisible dead hit
box, one cause. **If a sweep can decline, log the decline** — `SUBCAND` had to
be added before the gate precisely because `SUBGEO` sat after it and a
declining sweep logged nothing at all.

**EVERY CONSUMER OF A SHARED HOOK NEEDS ITS OWN GATE.** `SetFlagDetour`
serves three things; the third keyed off `ShowHook`, which ships at 0 - so the
Graphs band's born-correct dock **never executed once** between #127 and #137,
and two correct fixes in a row changed code on that dead path before anyone
checked whether it ran. The function already carried this exact warning for
EARLYDOCK at v2.41.17. **Before improving behaviour behind a hook, prove the
hook's branch executes** (law 47 again): read the mode from the LIVE ini and the
"installed ... (mode N)" line from the log, never the default in `Settings.h`.

**AN ANCHOR'S LIFETIME IS PART OF THE DOCK.** A dock that bails on
`!anchor->IsVisible()` is only as early as its anchor. #137 briefly anchored a
panel to a window that opens 19 seconds later - perfect arithmetic, guaranteed
jump. Check WHEN the anchor appears relative to its child, not only where.

**LOAD-ORDER LAW.** Files in the `Plugins` **root load BEFORE subfolders**, so
a root `z_*.dat` can NEVER override a dat inside a subfolder. Overriding
another mod requires a folder that sorts after it (`zzz-SC4UIScale\` beats
`150-mods\`). A plugin may replace a stock **script**, its **art**, or both —
check for both, and build the override from **the mod's** files, never the
stock ones. Recognition rule: **if a panel's live window count or root size
does not match the stock script you are reading, a plugin has replaced it.**

**RUNTIME IS SOMETIMES STRUCTURALLY TOO LATE.** Where the game reads geometry
before our first sweep can run — 3D advisor heads framed when bound at city
load, the ticker marquee's init-cached width — no amount of runtime timing
wins. Ship that geometry **pre-scaled in the `.UI` data** and make the parent
root-only so children are not scaled twice (`kDataScaledSubtreeIds`).

**THINGS THAT MUST NEVER BE SCALED.**
- **Alignment markers** (`id=0x0000AAAA`): positioning DATA. The game places
  a panel at `anchor − markerOffset` in NATIVE units, so scaling a marker
  displaces the whole panel by exactly that offset. Not at runtime, not in
  data.
- **Font-sized / art-sized controls** (`kFontSizedIds`): a control sized from
  its rendered caption or its own art is already correct once fonts/art are
  2x — scaling it again doubles it. Scale position only.
- **`cSC4WinAdviceList` children**: items are game-sized to the container.
- Never suppress paints to hide an open-flash (a "FlashGuard" blanked HUD
  windows). **Pre-scale while the window is still HIDDEN** instead.

**IDENTIFY WINDOWS POSITIVELY, NEVER BY SIZE HEURISTIC.** Tooltips are sized
by their content, so a "200-400 wide, >500 tall" test also caught tip buffers.
Use exact width, class + id, or an explicit mode split.

**ONE-SHOT CAPTURES ARE FRAGILE.** The Plot hook captures strip fields once;
any other writer that runs first poisons it (a sweep-side write captured 88 as
"natural" and forced 176 → 4x pitch everywhere). Sweep-side code may
INVALIDATE, never write.

**STATE GATES MUST BE VERIFIED IN ALL THREE STATES** — pre-founding god,
founded god, founded mayor. A gate that passes in two and fails in the third
is the single most expensive class of bug here. Founding a city makes several
"hidden/inert" windows go live, invalidating any note measured pre-founding.

**ONE NUMBER, ONE GATE** (law 47). Two green gates certifying *different*
targets are worse than one gate: whichever runs last decides what ships. The
#57 byte gate was written against `round(108*f)` while the acceptance oracle
had certified the tabled strip and rejects `round(108*f)` outright. Reconcile
the gates onto one number **before** building, and make the loser's target
unreachable — table it, and DECLINE any factor the table does not cover.

**A TEXT BOX IS SIZED BY THE FONT, NOT BY `f`** (law 48). Where a control's
box is a constant and the FONT is what scaled, `round(stockBox * f)` **wraps
more than stock**: measured out of the game's own pixels, ink grows **x2.13**
(n=17, mean 2.130, sd 0.026; pooled 2.133; *corrected 2026-08-03 - the figure
2.121 quoted elsewhere is one string's ratio, `Income` 33->70, not the mean*)
per doubling, not x2.00 (26 pt Arta is ~6 % wider per point than 13 pt). The
box is an INPUT — SC4's wrap call reads `left`/`right` and returns only a
height. Tier-math general form still governs geometry and art; it does not
govern a box that must contain rendered text.

**WHEN A FAMILY SURVIVES A SECOND FIX, DISASSEMBLE THE BUILDER** (law 49). A
constant that no instrument ever prints is still a constant. Four Graphs-legend
patches rewrote output rects inside a 110 px right-margin budget nobody had
read, because every probe printed resulting RECTS and none printed the
builder's INPUTS. Probe the output twice; after that, read the code that
computes it.

**HAND-ENCODED BYTES GET A CAPSTONE ROUND-TRIP IN A DURABLE ARTIFACT** (law
50). The first draft of the #57 patch put an `imm32` one byte inside the
preceding instruction — a crash, not a layout bug, and invisible to every
layout gate. The emitter is diffed against the gate's own `--emit` output;
a session transcript is not an artifact.

### FACTS — hard-won engine knowledge

Engine behavior proven during this work. Re-learn nothing; read this first.

- **All rich text is the game's own HTML engine, not FontStyle.** News ticker,
  news reader, story pages, advisor/message popups, tutorials and the Credits
  all render through it. `SIZE=1..7` resolves via two point-size tables in
  `.rdata` (`0xACD4A0` fonts, `0xAB4AD0` headings) that `FontStyle.ini` never
  reaches — which is exactly why the community's font mods report "font size
  does not work for news". Each rich window COPIES the tables at creation, so
  patching them at `PostAppInit` reaches every instance. Popup builders derive
  their size index from a *style's* size (`idx = (4*size+8)/18`), so those
  GUIDs must point at STOCK-size styles or the result compounds.
- **`GZWinBMP`-family windows draw dst = src size** — so 2x art scales the
  draw with no code hook, and an `imagerect` must be doubled whenever its art
  doubles. Corollary: a 2x source rect over a 1x bitmap draws only the corner
  that exists (this is what a shadowed art override looks like).

- **`GZWinMoveTo` is RELATIVE** — it moves by a delta in parent space, not to
  an absolute position.
- **MSVC reverses the vtable order of overloaded virtuals** — adjacent
  overloaded pairs like `GetArea`/`SetArea` land in reversed slots vs the
  header, making those pairs unusable through naive vtable indexing.
- **`.UI` scripts are plain text** stored as DBPF type `0x00000000`.
  `area=` and `imagerect=` are corner-format (`left,top,right,bottom`)
  **absolute pixels**; images are referenced as `image={gid,iid}`.
- **Group `0x08000600` is the engine's own 800x600 per-resolution layout
  override set** — the game already ships resolution-specific layout variants
  under per-resolution groups.
- **Art groups `0x46a006b0` and `0x1abe787d` are near-mirror twins** — most
  IIDs exist in both with identical or near-identical art; overriding one
  without the other produces mixed-scale UI.
- **SC4 partial redraw garbles under dgVoodoo at non-desktop modes** —
  the plugin's `ForceDrawOnScroll=true` (full redraw per scroll) fixes it.
- **Only real display modes work in fullscreen** — modes the panel does not
  natively expose (wrapper-emulated exotic modes) garble.

### Tools directory guide (`tools\`)

Research/build tooling for the scaling stack. Everything here is dev-side
only; nothing under `tools\` deploys except the two files named in the
deployment map.

| Folder | What it is |
|---|---|
| `dbpf\` | `DbpfExtract` / `DbpfPack` — DBPF (.dat) unpacker/packer pair, roundtrip-proven; plus the full-art `z_SC4UIScale_Art_2x*.dat` experiments and the extracted-art TGI index |
| `upscale\` | `Upscale2x` — the image upscaler (any factor). **Nearest-neighbor is the default at EVERY factor and the right answer**; the HQ scaler was rejected (blurs pixel art, fringes the magenta colorkey). ⛔ Do not make `--hq` automatic — that was tried on 2026-08-06 for fractional factors and turned the Mayor Rating bar and the news-reader borders pink within one launch, exactly as this row predicted. Magenta `0xFF00FF` is the game's transparency key; interpolation moves it off `0xFF00FF`, the key test misses, and the key colour draws. At a FRACTIONAL factor `ScaleDim` also snaps output dimensions to preserve the source's divisibility by 3 and 4, because the game cell-divides sheets with `width/3` (NineSlice) and `width/4` (four-state strips) — see #143. Verify scripts + comparison sets included |
| `oddballs\` | `OddballConvert` — converter for the 74 non-PNG art entries (FSH/JPEG/BMP) so they could round-trip through the 2x pipeline |
| `uiscripts\` | 330 extracted `.UI` layout scripts + analysis (`UISCRIPTS.md`) — the map of which script references which art |
| `fonts\` | `FontStyle.default.ini` (stock, **88** styles), `FontStyle.candidate.ini` (those 88 at 2x **+ the two never-scaled `*Html` clones = 90 on disk**; this is what deploys, renamed `FontStyle.ini`), research notes. *Style counts measured 2026-08-03 — see item 3 of "What ships" above; the generator's stdout still prints 88.* |
| `selective\` | First-generation per-group override dats (superseded by selective-safe) |
| `selective-safe\` | The **shipping art builder**: `build_selective_safe.py --factor N` + `refmap.csv` + `package-list.txt` → `z_SC4UIScale_SelectiveArt.dat` — **655 entries = 89 edited `.UI` scripts + 566 art**, the same 655 at every tier. At 1.5x/3x only the **dat** moves to `tools\packages\<tag>\z_SC4UIScale_SelectiveArt-<tag>.dat`; `refmap-<tag>.csv` / `package-list-<tag>.txt` stay **here** in `selective-safe\`. Not a single-output builder: it also emits one mod-override package per group found under `thirdparty-ui\` — currently `z_SC4UIScale_ThirdPartyUI.dat` (loose scripts) and `z_SC4UIScale_WarriorUI.dat` (subfolder). ~~(93 exclusive + 30 XOR-cloned + 23 edited .UI scripts)~~ *(Corrected 2026-08-16: all three numbers are long stale — measured 305 EXCLUSIVE / 12 clone+retarget / 89 edited scripts. Evidence: `tools\selective-safe\refmap.csv` classification column; `package-list.txt:4` "655 entries" and 655 files in `stage\` (89 `T-0x00000000` + 566 `T-0x856ddbac`); `_tests\Test-DatIntegrity.ps1:145`, `:215`, `:217`. Output paths: `build_selective_safe.py:64-65`, `:83-95` — factor 2 keeps the UNTAGGED filename, the `-2x` suffix is a deploy-side rename (`_tests\Test-DatIntegrity.ps1:357`). Extra packages: `build_selective_safe.py:2217-2237`, `:2372-2382`; `_tests\Test-DatIntegrity.ps1:369`, `:372`.)* |
| `capture\` | `CaptureWindow.exe` — PrintWindow screenshot harness for verifying the game without stealing foreground |
| `research\` | `UI-ART-BINDING.md` — how UI scripts bind art, per-resolution groups, probe orders |
| `review\` | `UISPIKE-REVIEW.md` — code review of the runtime scaler |

---

## Files

- Game side (`%USERPROFILE%\Documents\SimCity 4\Plugins\`):
  - ~~`SC4TouchControls.dll` — the plugin (x86)~~
  - ~~`SC4TouchControls.ini` — config (all keys documented inside; defaults are sane)~~
  - ~~`SC4TouchControls.log` — recreated every launch; first stop when diagnosing~~
  - ~~`z_SC4UIScale_SelectiveArt.dat` — 2x UI art (scaling stack)~~

    *Corrected 2026-08-16 — those four bullets survived the 2026-08-06 project split.
    They name ANOTHER project's files (`src\` contains only `SC4UIScale.sln` /
    `SC4UIScale.vcxproj`; `_tests\Test-DatIntegrity.ps1:332-335` treats
    `SC4TouchControls.dll` as a foreign file that is merely REPORTED, never deployed,
    and :336-344 records that its bundle assertions moved to `..\SC4Touch\`) plus the
    pre-tier art dat name. `z_SC4UIScale_SelectiveArt.dat` is the BUILDER's output
    name only — `_tests\Test-DatIntegrity.ps1:357` maps it to the deployed
    `z_SC4UIScale_SelectiveArt-2x.dat`. What this project actually installs:*
  - `SC4UIScale.dll` — the plugin (x86; `src\SC4UIScale.vcxproj:6` is `Win32` only).
    Its presence is the one DLL assertion in the suite
    (`_tests\Test-DatIntegrity.ps1:329-330`)
  - `SC4UIScale.ini` — config. It documents **only the player-facing keys**; the DLL
    reads many more development levers that are deliberately absent
    (`_packaging\SC4UIScale.ini:14-17`). `ScaleAll` and `ScaleRegion` are the only
    two keys that must never be deleted — both default OFF in the DLL
    (`_packaging\SC4UIScale.ini:8-12`)
  - `SC4UIScale.log` — recreated every launch; first stop when diagnosing
    (`_tests\Deploy-OnGameClose.ps1:40`)
  - `z_SC4UIScale_*-2x/-15x/-3x.dat` here, plus more of the same set in
    `zzz-SC4UIScale\` — the tier-tagged package set. Non-active tiers ship as
    `<name>.dat.x1-disabled`; `ScaleTier::SyncDat` renames the chosen tier live and
    stashes the others at boot (`src\ScaleTier.cpp:326-327`), because SC4 loads any
    `*.dat` in `Plugins\` and an inactive tier must not end in `.dat`
  - `z_SC4UIScale_WebText.dat` — the one UNtagged dat that ships
    (`_tests\Deploy-OnGameClose.ps1:132-134`)
  - `FontStyle-2x.ini` / `FontStyle-15x.ini` / `FontStyle-3x.ini` — the per-tier font
    SOURCES (`_tests\Deploy-OnGameClose.ps1:213-215`); `ScaleTier::SyncFont` copies the
    active tier's file over `FontStyle.ini` at boot and never deploys `FontStyle.ini`
    itself (`src\ScaleTier.cpp:440-444`, `_tests\Deploy-OnGameClose.ps1:206-208`)
- Game install root: `FontStyle.ini` — 2x fonts (scaling stack)
- This folder:
  - `src\` — sources + ~~`SC4TouchControls.sln`/`.vcxproj`~~ **`SC4UIScale.sln`/`.vcxproj`** (Win32/x86 only) *(corrected 2026-08-16 — `src\SC4UIScale.sln:6` and `src\SC4UIScale.vcxproj:16-17,33` (`ProjectName`/`TargetName` = `SC4UIScale`); `START-HERE.md:27`. The touch plugin is a separate project in the sibling tree — `..\SC4Touch\src\SC4TouchControls.vcxproj` — split out of this one on 2026-08-06 per `START-HERE.md:34-35`. The only `SC4TouchControls.vcxproj` left under this root is the superseded copy in `_archive\_HANDOFF-SimCity4-Complete\source\`.)*
  - `vendor\gzcom-dll\` — pinned framework snapshot (see `VENDOR-PIN.txt`)
  - `build\` — build output (not checked in anywhere)
  - `tools\` — scaling research/build tooling (see the tools guide above)
  - `dist\` — deployable bundles ~~(`SC4TouchControls-v1.0.4`, `SC4UIScale-preview`)~~
    **(`SC4UIScale-v<version>\`, one per cut, produced by `_packaging\Build-Dist.ps1`;
    as of 2026-08-16: v2.85.0, v2.92.0, v2.93.0, v2.93.1, v3.0.0, plus
    `SC4UIScale-v2.93.1.zip`)** *(corrected 2026-08-16 - neither named bundle is here:
    `SC4UIScale-preview` was deleted 2026-08-05, see the note above at README.md:357,
    and `SC4TouchControls-v1.0.4` moved to `..\SC4Touch\dist\` at the 2026-08-06 split,
    `_tests\Test-DatIntegrity.ps1:336-338`. The bundle name is built from the DLL's own
    version, `_packaging\Build-Dist.ps1:39-40`)*

## Building

Requirements: VS 2026 (v145 x86 toolset) and Windows SDK 10.0.26100 (this
machine has 22621/26100/28000 installed under
`C:\Program Files (x86)\Windows Kits\10`; the vcxproj pins
`WindowsTargetPlatformVersion` to 10.0.26100.0 — edit that one property to
build against a different SDK).

```
"C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe" ^
  src\SC4UIScale.vcxproj -p:Configuration=Release -p:Platform=Win32
```
*(Corrected 2026-08-16: this said `src\SC4TouchControls.vcxproj`, which does not exist here —
the touch project is the sibling `..\SC4Touch\`. Matches `START-HERE.md:43`.)*

## Deploying

~~Touch only: copy `build\Release\SC4TouchControls.dll` + `src\SC4TouchControls.ini` into `Documents\SimCity 4\Plugins\`. Full scaling preview: follow the deployment map above, or use `dist\SC4UIScale-preview\` + its INSTALL.txt.~~

⚠ **CORRECTED 2026-08-16.** Touch is a **separate project** in the sibling folder
`..\SC4Touch\`, which builds and deploys on its own terms — see its own README
(`..\SC4Touch\README.md`, "Deploy targets"). Nothing here deploys it.
`src\SC4TouchControls.ini` no longer exists in this tree (`src\` holds only
`SC4UIScale.sln`/`.vcxproj` and SC4UIScale sources), and the
`build\Release\SC4TouchControls.dll` still sitting in the build folder is a
**stale pre-split artifact — do not deploy it.** `_tests\Test-DatIntegrity.ps1:331-341`
records that this project stopped asserting that bundle on 2026-08-06 because its
artifacts moved to `..\SC4Touch\dist\`.

For this project: run **`_tests\Deploy-OnGameClose.ps1`**, which waits for the game
to exit (it runs elevated and holds the DLL and dats open — never kill it), copies
`build\Release\SC4UIScale.dll` plus every tier dat, then prove the install with
`_tests\Test-DatIntegrity.ps1` (and `_tests\Test-ThirdPartyGates.ps1`). The
`dist\SC4UIScale-preview\` bundle was deleted 2026-08-05 (see README.md:357); the
current release bundle is `dist\SC4UIScale-v<version>\` from `_packaging\Build-Dist.ps1`.

Launch the game and check **`SC4UIScale.log`** (created beside the DLL —
`src\SC4UIScaleDllDirector.cpp:101`) starts with the `SC4UIScale v<version>` header
(`:107`). The game must be restarted to pick up a new DLL or ini changes. Note: the
log is opened `_SH_DENYWR` (`src\Logger.cpp:38`), so read it with
`[System.IO.FileStream]` + `FileShare.ReadWrite`, not `Get-Content`.

## Surface 1.0 table note

The table's PixelSenseToTouch bridge injects genuine Windows pointer input
(`InjectTouchInput`), which is indistinguishable from a touchscreen at the
WM_POINTER level this plugin consumes — the same DLL is expected to work there
unchanged once SC4 is installed on the table. Validate on the table before
declaring it done.

## ⚠ PRE-FLIGHT (2026-07-30)

**Canonical copy: `tools\research\METHOD.md` §2.** Short form —
before fixing ANY UI element: re-read its section in
`tools/research/BUDGET-DETAIL-ANATOMY.md` and `SC4-UI-ENGINE.md`,
check the failed-attempts table, confirm a STOCK capture of that
exact element exists, measure the live rects with the dump
instruments, and express the fix as `round(stock x f)`. The full
checklist and why it exists (a real discipline lapse, user-flagged)
is at the top of HANDOFF.md. Laws 14-21 are in _tests/REGRESSION.md.

## The two geometry scalers (2026-08-06, #148)

Worth knowing before touching any layout code, because reaching for the wrong
one of these cost four regressions in an afternoon.

**`ScaleSubtree` is EDGE-DERIVED** (`src/UiSpike.cpp`):

```
newW = ScaleRound(l + w, f) - ScaleRound(l, f)
```

Deliberate: panels that are flush before scaling stay flush after. Rounding the
width directly drifts abutting edges apart at a fractional factor, which is
exactly the #143 white-seam failure.

The consequence is that **the scaled size depends on the position**. At f = 1.5,
`l * 1.5` is integral only for even `l`, so an odd-`l` control comes out one
pixel narrower — 70 against a 71-pixel art cell — and the uncovered right column
and bottom row draw as a **reverse L**. Invisible at 2× and 3×, where
`ScaleRound(l * 2)` is exact for every `l`.

**The cure:** a **leaf** window (`GetChildCount() == 0`) takes its size
**size-derived**, `ScaleRound(w, f)`. Nothing moves; the change is ≤1px;
containers keep edge-derived rounding so the seams cannot return. A `LEAFSIZE`
log line reports each one, capped at 8 per city.

### The two levers that were tried first, and reverted

| lever | why it failed |
|---|---|
| move the control onto an even edge (`.UI`, build time) | up to 2px at 1.5×; invisible on a 5-button flyout, visibly wrong in a 21-icon grid, the advisors, the budget rows and the dock |
| resize the art to match the window | **runtime-created strip items appear in no `.UI` and still bind art by TGI**, so the builder's conflict check was blind by construction — 0 conflicts reported, thumbnails broken |

**Editing geometry in a `.UI` is scoped to that `.UI`. Editing art is scoped to
the whole game.** Full detail: `_tests/REGRESSION.md` #148.
