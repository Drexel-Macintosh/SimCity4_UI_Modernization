# `_tests\` — the suite reference (read before running anything here)

Written 2026-07-30 after a script was run without knowing what it did: it
killed the game, rewrote the resolution, and left the ini at 800x600. Nothing
in the repo warned about that. This file is the warning.

**The rule this encodes:** *a script's danger is part of its API.* Every entry
below states whether it touches the running game or on-disk config.

---

## 🟢 SAFE — offline, run any time, no game needed

| script | what it asserts | typical runtime |
|---|---|---|
| `Test-DatIntegrity.ps1` | every shipped dat's entry count + the 3 font sources + both DLLs + the FROZEN bundle hash + **20 DEPLOYED==BUILT content hashes** (added 2026-08-02, #58: a package left out of Deploy-OnGameClose.ps1 rots silently — stale and fresh dats can have IDENTICAL sizes/counts, only hashes catch it). **The one to run after any data change OR deploy.** Update its expected counts AND add a hash pair for any new package in the same commit. Note it FAILS between build and deploy by design — deploy, re-run. | ~1 min |
| `Test-ScaleTierDecide.ps1` | the AutoScale fit function: 14 named resolutions + a 5000x2 random sweep, asserting the chosen tier always fits. | seconds |
| `Test-UiMapDiff.ps1` | the offline model vs the live log vs the stock captures at f=1/1.5/2/3. **Needs a full, healthy session log** — a truncated or stock-tier log produces false STOCK-1X failures (that happened 2026-07-30). | seconds |
| `Audit-UnscaledWindows.py` | sweeps a log for windows we never scaled. | seconds |
| `Test-BornCorrectCoverage.ps1` | every id in `SCALED_WINDOW_IDS` (python AST) has a born-correct route or a LABELED own mechanism in UiSpike.cpp. **Run after touching SCALED_WINDOW_IDS or any born-correct/flyout id list.** Would have caught #90. | seconds |
| `Test-SubRingLock.ps1` | the sub-flyout ring PIN: ring absolute Y identical under the model+Auto and under the legacy constant, ring centred on its button, f=1 reducing to the game's own native top, birth/sweep anchor identity, and the payoff case (8 items on a low button overflows under the legacy constant, fits under the model). **Run before every sub-flyout change.** Its scope is the RING — `emu_subflyout`'s 32/32 models the CONTAINER only, which is exactly how v2.45.0 shipped green and still slid the ring off (law 42). | seconds |

Also offline and safe, with their exact invocations (measured 2026-08-02):
- `python tools\uimap\emu\emu_subflyout.py` → `PASS - 71 checks` (runs the
  game's own `sub_79AD00` under Unicorn).
- `python tools\flyout-sim\check_marker_fit.py` → `ALL FIT (16 placements
  checked at f=2.00, view 2400x1600)`. The OTHER flyout family (mayor
  marker-docked), asked whether any of them lands off-screen — stock AND
  WarriorUI. Run after touching `kMayorFlyoutDock` or any marker constant.
  Its `R != -marker` notes for the `G-08000600` rows are EXPECTED (the
  marker really does move per resolution group — that is why the live-marker
  rule exists), not failures. Zero placements checked exits non-zero: the
  first version of it indexed every window's CLASS id (`clsid=0x…` contains
  `id=0x…`), matched nothing, and printed "ALL FIT" over an empty run.
- `python tools\uimap\emu\emu_layout.py --selftest --fresh` → `5 pass, 0 fail`.
  ⚠ **Use `--fresh`, not `--resume`**: with `--resume` the cached run reports
  `0 pass, 0 fail, 5 skipped`, which is a NULL, not a pass — it looks green at
  a glance and asserts nothing (null-is-not-evidence).
- `python tools\uimap\placement.py --selftest` → `ALL PASS` (3 measured
  births + an exe byte check).

## 🟡 TOUCHES ON-DISK CONFIG — reversible, but know what it changes

| script | what it changes | how to undo |
|---|---|---|
| `Set-StockCompare.ps1` | stages the STOCK (1x) configuration so a panel can be captured for parity work. | re-stage the 2x config; see `STOCK-REFERENCE.md` |
| `Toggle-BuildingStylesUI.ps1` | enables/disables the third-party Building Styles UI override. | run again to toggle back |
| `Restore-StockPark.ps1` | restores a stock park/lot file that testing replaced. | n/a — it *is* the restore |

## 🔴 DANGEROUS — TOUCHES THE RUNNING GAME

### `Deploy-OnGameClose.ps1` — the standing deploy mechanism
**This is how the DLL ships. Nothing else.** The game runs **ELEVATED** and
holds `SC4UIScale.dll` and the tier dats open, so it is **never killed**: the
script polls every 5 s, then copies the DLL + SelectiveArt + DialogStatic for
all three tiers and asserts the DLL size matches.

    cd _tests ; .\Deploy-OnGameClose.ps1

Run it in the background (or detached) with a window long enough for a real
play session, and **confirm the `deployed ... at HH:MM:SS` line and hash-verify
against `build\Release` before claiming anything shipped**. A watcher armed
*before* a later build will ship whatever is in `build\Release` when the game
closes — check the hash, not the intent.

### ⛔ `Test-BootMatrix.ps1` — NOT A ROUTINE CHECK
**It launches and KILLS the game once per matrix entry and rewrites
`SC4GraphicsOptions.ini`** (800x600 → 1920x1080 → 1600x1200 → 2400x1600),
restoring native resolution only if it runs to completion. ~10 minutes.

- **Never** run it as part of a normal "run the suites" pass.
- **Never** run it while the user may be playing.
- If it is interrupted it leaves the resolution wherever it died. Restore
  `WindowWidth=2400` / `WindowHeight=1600` immediately — **by byte-exact
  `Copy-Item` from `_working-backup\GOLDEN-2x-DirectX-2026-07-23\`**, never by
  `Set-Content`, which writes a UTF-8 BOM that makes
  `SC4GraphicsOptions.dll` abandon the whole file and boot windowed.

---

## The routine verification pass

1. `Test-DatIntegrity.ps1` + `Test-ScaleTierDecide.ps1` (+ the `emu\` drivers
   for anything geometric).
2. Build, then `Deploy-OnGameClose.ps1`; hash-verify the deployed DLL.
3. Read the log for the acceptance line you decided on **before** the build.
4. Eyes-on the specific panel, plus the standing regression watch in
   `REGRESSION.md`.

**Never** substitute `Test-BootMatrix.ps1` for step 1.

## Instruments (ini-gated, in `SC4UIScale.ini`)
`[Probe] Enabled` DPROBE geometry changes · `EdgeDump` full-screen window set ·
`VisTrace` full-depth visibility + creation trace · `EdgeBlt` thin edge blits
(⚠ **cannot see the screen surface** — see
`captures\2026-07-30-BORDER-HUNT-README.md`).
All ship at 0. They are re-read live, so flipping one needs no rebuild.

**Before trusting any instrument's null result, read its printf and confirm it
sits in the branch that does the thing.** Six probes on 2026-07-30 returned
nulls that were really blind spots — one root, two levels, flips-only, unarmed
hook, wrong surface. `METHOD.md` "YOUR OWN INSTRUMENTS CAN LIE".
