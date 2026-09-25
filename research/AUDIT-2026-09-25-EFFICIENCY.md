# Efficiency and simplification audit (2026-09-25, v4.10.2)

The question was whether the plugin as a whole could be more efficient or simpler. **No code was changed.**

**How it was done.** Four independent Opus reviews, all read-only, each covering one slice:
- the per-tick sweep;
- `CodePatches.cpp`;
- dead code and duplication in `UiSpike.cpp`;
- startup, file I/O and background work.

Their claims were then checked against the source and the v4.10.2 retest log (2026-09-25 08:58-09:00, LogLevel=3).
- **✔** marks a claim re-checked by the integrating session.
- **VERIFIED** is the reviewer's own end-to-end read.
- **SUSPECTED** means not yet proven.

Line numbers are as of commit `b3ebfdd`.

The evidence scripts are in `tools/research/audit-2026-09-25/`:
- `tick_audit_sim.py`: tick lookup simulation over a logged tree dump.
- `zip_dups.py`: finds duplicate payloads in a bundle.
- `enumdisp.ps1`: display-mode enumeration outside the game. Run it under 32-bit PowerShell to match the game.

## STATUS (updated 2026-09-25, after the follow-ups) - read this first when resuming

**v4.10.3 build, not released. The ordered list is done** (items 1-9, 23 commits, `05343c7` to `d6358db`), **and so are the follow-ups it left** (10 commits, `6a163f6` to `ffb9383`). The first table was checked in the running game. The second has had a clang-cl build and link, the offline gates and the proof in its row, but has not run in the game or on Windows yet: see "Checks still to run".

**Checked in the game** (session of 12:29-12:43):

| Item | Commit | Evidence |
|---|---|---|
| A2: every-boot DialogStatic re-copy removed | `d70a139` | CommitArming has no migration line; 0 FAILED |
| A5: SUBGEO2 moved to Debug; BUBBLEFX "already ours" | `d70a139` | 0 NOT PRISTINE lines, 1 "already ours" |
| A6: region tile grow, one division per column | `d70a139` | REGIONZOOM grew 40 tiles, declined 0 |
| A11: CSIDRAW installs only for CsiKill or mode 3 | `d70a139` | CSIDRAW 0 |
| B6 (critical part): `.text` writes keep the page executable and flush the cache; the CsiCountPlate override no longer writes without VirtualProtect | `d70a139` | no errors; CSI patch applied |
| C1: `EarlyDock` default 2 | `d70a139` | two cities, dock scaled at +313 ms and +109 ms, no dock FLASHSET |
| A1: `tick.incr` PerfProbe scope; dead `mayorBtn1` lookup removed | `d70a139` | baseline **0.81 ms per tick** (1,385 ticks, max 9.4) |
| B1/B3 first pass: 29 dead definitions, 533 lines | `ca71cfc` | `.text` byte-identical to the tested DLL (`tools/dev/pe_section_diff.py`) |
| A1: probe-only geometry map skipped; ChildSnapshot clears only `count` | `155caa0` | see the timing below |
| A1: in-city region miss latched until Disarm | `155caa0` | region screen re-found after exiting the city |
| B4: ScaleRemap removed (619 lines) | `155caa0` | clean boot and shutdown |
| A1: one ApplyPanelDocks per city tick | `b42c5a2` | the user saw the Graphs and other panels in place |
| A10: STATE files written only on change | `b42c5a2` | rewritten once for the new header |

- **Timing after `b42c5a2`:** `tick.incr` = **0.68 ms per tick** (632 ticks, max 9.5), down from 0.81 ms (about 16% less). The two sessions differed, so this is a rough comparison.

**Done since, not yet run in the game or on Windows:**

| Item | Commit | Proof here |
|---|---|---|
| A3: the bundle seeds its live `.dat` files with the `.off` stub | `05343c7` | both scripts parse (pwsh 7.4); Build-Dist not run |
| A1: one walk per lookup list (HookRuntimeBmpsUnder, the flyout loops, kCityDialogIds); the `0x9A47B417` self-lookups return `pView`; the dashboard hook runs only after a UDMAP hit | `ce44600` | `run_idwalk_test.py`: 3,000 random trees against a model of the engine lookup; an in-game positive control logs `IDWALK` |
| B1/B3: never-assigned flags and never-read globals | `9d705c8` | per-function disassembly: only the functions edited on purpose changed |
| B1: retired paths removed: SubFlyoutBorn2x, DockDialogs, EarlyBake mode 2, the derived disaster dock, EdgeProbeTick, REGIONCAM/REGIONWATCH; the tests and docs that described them | `ed763e9` `7f53d8a` `df35266` `8310fd3` `3e9ed8b` `cf62285` `24a1a06` `9964f55` | build clean; gates unchanged; gate_patch_families PASS |
| A9: SpinProbe fix-only mode skips the diagnostics | `1dc0af6` | build |
| A4: the display-mode list is cached on disk | `24bc5c9` | save/load round trip, key mismatch, truncation and missing file, offline |
| B5: `HookVerified` for all 27 hooks; CSIDRAW's prologue pinned | `08a01e3` | gates; Test-PatchSiteBytes checks the new pin |
| B6: every write into the game image from CodePatches.cpp goes through `WithCodeWritable` / `WithDataWritable` | `f897536` | the only `VirtualProtect` calls left in CodePatches.cpp are the two in the helper. (This row said "every write into the game image": the UiSpike files' vtable-slot writes still call `VirtualProtect` themselves, see Follow-ups) |
| B8: the ini is parsed once (IniCache); SC4GraphicsOptions.ini in one reader | `d2e04b2` | `run_inicache_parity.py` under Wine: 271,638 comparisons, 0 mismatches |
| B9: duplicated tables and loops; one `RoundHalfUp`; one strip-geometry sum | `0790456` `88a3fae` | per-function diffs; every float in [0, 2^20) for the rounding; 164M cases for the geometry |
| B11: the selector and the region screen split out of UiSpike.cpp | `1d231a9` `661de3c` | pure moves: the function sets match the old object's |
| B10: 23 history blocks (447 lines) moved word for word to REGRESSION.md, `[CC-nn]` pointers left | `7d3bea8` | `UiSpike.obj` byte-identical |
| B12: one package list, `_packaging/PackageFiles.psd1`, for Deploy and Build-Dist | `2dd88d0` | the old scripts' file sets reproduced exactly (80 deploy rows, 77 bundle files); the new code run under pwsh on a fake tree in 3 scenarios; new gate Test-PackageFiles.py |
| A8: folder discovery lists each folder once, not 8 times | `d6358db` | under Wine: the Test-FolderDiscovery trees give old = new, and a 436-folder differential has 0 mismatches |
| A10: no stray `Plugins\010-SC4UIScale`; the boot TOTAL counts the walk once | `d6358db` | per-function diff |
| B7: the exe's base address is read once, by `ExeBase()` (`src/ExeBase.h`), at the 71 sites that called `GetModuleHandleW(nullptr)` (63 in CodePatches.cpp, 7 in UiSpike, 1 in ScaleTier.cpp) | `6a163f6` | per-function diff against the parent build: every function that called it changed and no other did, apart from two EH funclets that moved with their parents |
| Test-DatIntegrity takes its deployed==built pairs from `PackageFiles.psd1`, no third list. That adds 5 deployed files it never hashed: ItemIcons and ItemIconsSub at 1.5x and 3x, and CamGraphLabels | `eff0cbf` | the derivation, run under pwsh, reproduces all 71 old pairs. Test-PackageFiles.py checks that the suite reads the list. In the suite, a count row for a package the list does not deploy is red (negative control, run under pwsh). The suite itself needs a deployed tree |
| `scale_rules.py --selftest`: its RoundHalfUp tripwire had been red since `88a3fae` without anyone seeing it; it now reads `RoundHalfUp.h`, and Run-OfflineGates runs the selftest | `0db68df` `f189523` | 146,040 checks, 0 failed; a negative control fails. REGRESSION.md, "three gates went blind when code moved" |
| B11 second pass: the window-id tables to `UiSpikeIds.h`, the minimap to `UiSpikeMinimap.cpp`, and the flyouts (ScaleGodFlyouts, its draw hooks, the sub-flyouts) to `UiSpikeFlyouts.cpp` | `6c5c215` `005058e` `86a07fe` | id tables: `UiSpike.obj` byte-identical. Minimap and flyouts: `tools/dev/split_proof.py` on /Od /Gw builds, 1,988 of 1,988 and 1,888 of 1,888 symbols byte-identical, every relocation to the same target; its two negative controls fail. Every script that reads the source gives the same full output apart from line numbers and paths. Four of them stop at a missing game-derived input here, so their source-reading code was run by itself on both trees: the same lists, dock rows and source lines (REGRESSION.md, 2026-09-25) |
| The tools that read the UiSpike source read every `src/UiSpike*` file: Test-ProbeDerefGuards (the first split had dropped two files from its default scan), gate_patch_families CHECK C, Test-ShippingIniKeys, idcollide, and coverage_rederive, whose section 5 had lost 94 of the 354 ids it counts | `005058e` `86a07fe` `ffb9383` | positive controls planted in a split file are caught; the per-file counts add up to the totals before each split; coverage_rederive counts 322 of the 354 again (the other 32 went with deleted code and moved comments) |
| B10 second pass: 7 more blocks (96 lines), `[CC-24]` to `[CC-30]` | `3fb30d6` | `UiSpike.obj` and `UiSpikeFlyouts.obj` byte-identical |
| The audit's four dead links (ScaleRemap.cpp after B4, the A4 cache file) | `de03267` | `Test-NoDeadLinks.py --repo` is back to the 2 it had at `b3ebfdd`, see Follow-ups |

- **Size:** `src` went from 44,027 lines to 42,284 since `b3ebfdd` (41,939 after the ordered list; the three B11 splits added 440 lines of includes, shared declarations and pointer comments). UiSpike.cpp went from 22,134 lines to 7,446. Split out of it: the flyouts (`UiSpikeFlyouts.cpp`, 8,493 lines), the selector (1,929), the minimap (1,458), the region screen (586) and the id tables (`UiSpikeIds.h`, 983). `UiSpikeInternal.h` (226) holds what they share, and says for each file what the compiler asked for. B10 moved 543 lines of comments in two passes (447 + 96).
- **Tools:** `_tests/Run-OfflineGates.ps1` now also runs `run_idwalk_test.py`, `run_inicache_parity.py`, `Test-PackageFiles.py` and `scale_rules.py --selftest`. `tools/dev/find_cxx.py` finds a compiler for the C++ tests (MSVC through vswhere on Windows; MinGW + Wine elsewhere). `tools/dev/split_proof.py` checks that a split moved code without changing it; its docstring has the recipe.

**Checks still to run** (they need Windows and the game, which this container does not have):
1. Build with MSVC. The split files have only been compiled by clang-cl. `UiSpikeMinimap.cpp` must keep its UTF-8 BOM, like UiSpike.cpp: one log string has an em dash, and without a BOM MSVC reads the file in the ANSI code page, which changes that string's bytes (clang-cl cannot see this). Run `_tests/Run-OfflineGates.ps1`: `run_inicache_parity.py` must exit 0 on Windows (exit 2 means "not proven here"). Run `_tests/Test-FolderDiscovery.ps1` against a built bundle.
2. One play session at LogLevel=3, then read the log:
   - `IDWALK ... 0 disagreed`, and `tick.incr` against 0.68 ms;
   - the `boot phases` line: `discover` (15-19 ms before A8), and a TOTAL that counts the walk once;
   - `SELRES`: the enumeration on the first launch, the cache after it;
   - `prologue NOT PINNED ... live bytes` for REGIONTILE, REGIONZOOM, ARTFETCH, BALLOONKIND and BALLOONSPRITE, and the live bytes for VIEWOBJ, VIEWLIST and PICKPROBE: pin them from this log (B5);
   - no `VirtualProtect refused` line, and every patch family applies as before;
   - at shutdown with SpinProbe=0: the armed line says fix-only, with no FINAL tally, DumpLoopFields or StackScan;
   - panels, flyouts, sub-flyouts, dialogs, the selector, the region screen and both minimaps look as before (the flyouts and the minimap now come from their own files).
3. Deploy with the new `Deploy-OnGameClose.ps1`, then run Test-DatIntegrity.
4. With the game-derived inputs present (the extracted `.UI` corpus, `tools/uimap/_work/wincensus.json`, the game's Plugins folder), run the tools that stop without them here: `coverage_rederive.py`, `idcollide.py`, `id_collisions.py`, `art_coverage.py`, `lookup.py` and `check_marker_fit.py`. Expect coverage_rederive's section-5 counts to fall below its floors: B1's DockDialogs removal (`7f53d8a`) un-named the root ids of five stock dialogs that DialogStatic scales. Re-measure the floors from that run (REGRESSION.md, 2026-09-25, item 3).
5. At the release: Build-Dist.ps1, then `zip_dups.py` on the zip (expect no large duplicate payload) and Test-Sc4pacInstall. After a boot of an sc4pac install, there must be no empty `Plugins\010-SC4UIScale`.

**Follow-ups found on the way** (not started):
- **B10:** two passes are done. The second read the seven functions with the most version-cited comment text; almost all of it explains the current code and stays. 28 comments cite source lines by number (`:NNNN`, not counting SDK headers and log excerpts); after the splits 15 of them point past the end of their file, and the rest are unchecked. Name the function instead.
- **B11:** every split the audit listed is done; ScaleGodFlyouts, one of its three knots, moved whole into UiSpikeFlyouts.cpp. The other two, ScalePanelsUnder (1,870 lines) and IncrementalPass (1,232), stay in UiSpike.cpp. Shortening them means restructuring code, not moving it, so the byte-identical proof would not apply.
- **B6, the rest:** the UiSpike files' 5 vtable-slot writes (1 in UiSpike.cpp, 4 in UiSpikeFlyouts.cpp) still call `VirtualProtect` themselves, outside `WithDataWritable`.
- 8 packages that PackageFiles.psd1 deploys have no entry-count row in Test-DatIntegrity: NamIcons at 1.5x, 2x and 3x; ThirdPartyUI at 1.5x and 3x; WebButtonUI at 1.5x, 2x and 3x. Their counts need a measured build (Test-PackageFiles.py lists them).
- `Test-NoDeadLinks.py --repo` still reports 2, both already there at `b3ebfdd`: REGRESSION.md names a capture CSV under _tests/captures and the saved v4.10.1 release notes under dist, and both folders are gitignored. Track the files, or say in the prose that they are local.
- `86a07fe`'s message gets its seam arithmetic wrong (16 + 23 + 9 is not 46). `UiSpikeInternal.h` has the measured seam: UiSpike.cpp needs the 23 names of the flyout block, and the new file needs 9, of which 5 were new to the header.
- lookup.py's report attributes ScaleRound's comment, now in `UiSpikeInternal.h`, to the `LiveTuneIniPath` prototype above it: its owner heuristic stops only at a closing brace.
- `kCityDialogIds.designW` is read by no code (REGRESSION.md `[CC-23]`). Removing it rewrites every row of the table.
- Build-PublicRepo exports Deploy-OnGameClose.ps1 but not Convert-ToPayloadLayout.ps1, which Deploy calls.

**Deliberately not planned:**
- **A7** (icon index cache): a stale cache brings back the #149 doubled icons.
- **B2** (sub-flyout legacy fallback): it is the safety net for the just-fixed v4.10.2 path.
- **B13** (old migrations): they cost about 1 ms and still serve old installs.

## Recommended order

1. **Safe wins, one release:**
   - A2 (every-boot re-copy);
   - A5 (Info-level log floods);
   - the dead and self lookups in A1, plus the two timing scopes;
   - A3 (bundle size);
   - A11 (default-installed probe hook);
   - the `.text` writes in B6;
   - C1, but only after an eyes-on test.
2. **Measure the tick** with the A1 scopes (one session), then batch the id lookups.
3. **Cleanup with no behaviour change:** B1, B3, B5, B7-B11.
   - Gate: crash gate, the suites, and one play session.
   - Where a unit can be compared byte for byte, compare before and after.

## A. Efficiency

### A1. The per-tick sweep repeats whole-tree id searches (`UiSpike.cpp`)
- **Tick rate.** The tick runs at about **35 Hz, not 60.** HEARTBEAT counted 8,500 ticks in 245 s (`SC4UIScale-2026-09-23-155059.log`), which fits a `SetTimer(16)` rounding up to the timer resolution.
- **Cost per pass.** Replaying a logged 840-window city tree through the decompiled `cGZWin::GetChildWindowFromIDRecursive` (0x0099DEC4: post-order, children before self, no depth limit), one idle `IncrementalPass` costs about **46 whole-tree walks, roughly 38,700 window visits.** The deliberate reactive sweep accounts for only about 530 of those. A lookup that hits is no cheaper than a miss: the dock and the composite sit last in the view's child list, so finding them visits 796 and 826 of 837 windows.
- **Measured anchor.** SELPERF `sel.findDlg` = 34 µs average for a failed whole-tree search (290 calls, 9.8 ms).
- **Estimate.** **1-3 ms per pass**, about 3-10% of the game thread. This is **not measured**, so measure before changing anything.

**Timing first.** Two PerfProbe scopes feed the shutdown SELPERF table (22 of 32 slots are used):
- `:9492` `{ PerfProbe::Scope perf_("tick.incr"); IncrementalPass(); }`
- `:12311` `{ PerfProbe::Scope perf_("tick.godfly"); ScaleGodFlyouts(pRoot, f); }`

**Redundant lookups.**
- ✔ `mayorBtn1` (`:15132`) is looked up every tick and never read. This is the only reference.
- ✔ `:14690` and `:16499` search `pView` for `0x9A47B417`, which is `kGZWin_SC4View3DWin`, the view's own id. That is a full walk to get `pView` back. Use `pView`.
- ✔ `ApplyPanelDocks` runs twice per tick (`:12304` with pRoot, `:13927` with pView). Only two inactive probes run in between, so the second call never writes. Skip `:12304` when rootTag is not 'r'. Keep `:13927`, because OnFlyoutOpened needs it.
- `HookRuntimeBmpsUnder` makes 16 searches (`:10877`, two of them via `:18568`), and 5 of them miss. Nothing between iterations changes the tree, so look up all ids first. VERIFIED.
- Nine flyout lookups miss when no flyout is open (7 at `:15957`, 2 at `:16158`). Walk once, and walk again only after a found flyout was scaled. Leave the sub-flyout lookup at `:15214` as it is, per v4.10.2. VERIFIED.
- `kCityDialogIds` does six depth-8 walks from the main window (`:17550`). One walk that collects up to 4 matches per id, in the same order, gives identical results. VERIFIED.
- `RegionWatchTick` (`:19439`) searches the whole tree on every city tick for a region screen that cannot be in it. Latch the miss while continuous, until Disarm. VERIFIED.
- `0x4BCB938A` is looked up twice (`:12843` and `:10254`). When the first misses, nothing in between can change the answer. VERIFIED.

**The DPROBE comparison runs even with the probe off** (`:14682-15036`). VERIFIED.
- Every tick it does about 1,670 `prevGeom` map operations and zeroes a 1 KB snapshot per view window (about 860 KB per tick).
- Only a log line gated on `gProbeOn` reads the result, and the map grows as short-lived windows come and go.
- Stage 1: skip the map when the probe is off.
- Keep the walk itself. It swaps vtables at `:14665`, which the v2.69.3 note depends on.

**The main change.** One multi-id walk per tick, with a per-tick cache that is dropped on any resize or move (reuse the #117 count). That takes the pass to about 3-4 walks. Risk is medium because many call sites change, so run one session comparing its answers with the engine's own lookup.

**Small, SUSPECTED.** `ChildSnapshot x = {}` zero-fills 1,028 bytes about 950 times per tick, when only `count` needs clearing. First check all ~50 `.wins[` reads.

### A2. ✔ DialogStatic is re-copied on EVERY boot by a v2.x migration (`ScaleTier.cpp:1748-1807`, called at `:5140`)
Every boot, the same false "one-time" sequence runs:
1. `MigrateLegacyUntagged2x` renames the live `z_SC4UIScale_DialogStatic.dat` to `-2x.dat`. Since v4.5.0 that untagged name is the live armed file.
2. `MigrateRenamesToPayloads` copies `.2x.uipay` back (2.66 MB).
3. At 1.5x or 3x, `ArmOne` then copies the tier payload (2.85 MB).

Today's boot logged it:

    ScaleTier: migrated z_SC4UIScale_DialogStatic.dat -> -2x tag.
    ArmOne: migrated 1 pre-4.5.0 tier file(s) in this folder into .uipay payloads - no download needed.
    ArmOne: z_SC4UIScale_DialogStatic.dat <- .3x.uipay (armed)
    CommitArming: ... (after a one-time migration from the rename layout)

- **Precedent.** v4.0.3 removed SelectiveArt from this same function for exactly this fight (the comment at `:1750-1759`). DialogStatic needed the same removal when v4.5.0 moved every package to the stable name.
- **Cost.** 6-103 ms of boot, two file rewrites under a OneDrive-synced Documents folder, and a misleading log.
- **Fix.** Delete the function. Its font half is a no-op, because `FontStyle-2x.ini` ships in every release. Risk: very low.

### A3. ✔ The bundle ships the 2x payload twice: 22% of the download
- **Measured.** 13 packages ship `<Pkg>.dat` byte-identical to `<Pkg>.2x.uipay`. That is **27.6 MB of the 123.7 MB zip** (`zip_dups.py`).
- **Why nobody needs that copy.** The live copy is never used when the DLL runs. No STATE file ships, so `ArmOne` has no row on a fresh install and copies the chosen payload over every live `.dat` at first boot (`ScaleTier.cpp:1567-1600`). An upgrade misses the stamp the same way.
- **Fix.** Seed the bundle's live files with the `.off` stub instead of 2x, in `Build-Dist.ps1:359` (`Convert-ToPayloadLayout -Tier`). The 25 stubs total 4.6 KB.
- **Safer too.** When the DLL fails to load, the install becomes stock-looking (inert) instead of 2x art in 1x windows. That is ArmOne's own rule ("inert is the only safe wrong answer", `:1545`). It would also have turned the v4.5.0 sc4pac depth defect (`REGRESSION.md:17491`) from a mixed-factor screen into an inert one.
- **Check first.** Any Build-Dist or Test-DatIntegrity gate that assumes the live file equals 2x. Then regenerate the channel yaml.

### A4. The display-mode list takes about 6 s in the game (`UiSpike.cpp:20468-20532`; thread started at `SC4UIScaleDllDirector.cpp:353`)
- **Measured.** ✔ `SELRES display enumerated ONCE in 5901ms - 31 distinct mode(s)`.
- **What it walks.** About 655 `EnumDisplaySettingsW(NULL, i)` calls: the primary display, every refresh-rate and scaling variant.
- **Outside the game,** in a clean 32-bit process, the same calls take **37-101 ms** (`enumdisp.ps1`). The in-game slowdown (4-14 ms per call) is SUSPECTED to come from the exe's compatibility layers, dgVoodoo, or contention with boot. A `__COMPAT_LAYER` test did not reproduce it.
- **Player impact.** Only when Graphic Options opens within about 6 s of launch: it then waits in `Sleep(5)` (`:20480`), even in Borderless.
- **Fix.** Cache the list, the largest mode and the desktop mode, keyed by adapter and monitor device IDs plus the desktop mode. Read the desktop mode with one call. On a miss, start the thread at low priority. Do not stop early, because the largest mode needs the full list.

### A5. ✔ Two Info-level instruments flood the shipped log
- **SUBGEO2** (`UiSpike.cpp:15339-15350`) writes up to 40 lines per submenu open at **Info**: 384 of today's 2,657 lines (14%).
  - That breaks the LogLevel=1 budget in `REGRESSION.md:5407` ("no per-frame instruments"). The SUBPLACE and SUBANCHOR caps are 2000.
  - Fix: demote to Debug.
- **BUBBLEFX "NOT PRISTINE, skipped"** (`CodePatches.cpp:8925-8952`) is uncapped at Info: 106 lines in 21 s today and 1,141 in 12 min on 08-20.
  - The 106 were re-checked; the 1,141 figure is the reviewer's, from the 08-20 capture.
  - Every one shows `scale == tier factor`, which is **our own earlier write** on a recycled U-Drive-It effect.
  - Fix: treat `flag==0 && scale==gBubbleScale` as "already ours" and print a periodic count. Foreign scales stay uncapped. The write path is untouched.

### A6. ✔ Region-zoom tile grow divides once per pixel (`CodePatches.cpp:1591-1597`)
- `sx` depends only on x, so build one column table per call. Output is bit-identical.
- That is about 55M integer divisions in the logged 406 ms +5 zoom step (36 grows of about 1587x977).
- The saving is SUSPECTED; measure it.

### A7. The icon index is re-read on every boot (`ScaleTier.cpp:2968-3118`)
- It is 288 of today's 354 ms of boot, and it grows with the plugin count.
- A cache keyed on a digest of the boot index would remove it, but **risk is moderate**: a stale key brings back the #149 doubled icons. Not recommended yet.

### A8. Folder discovery lists each folder 8 times (`ScaleTier.cpp:262-289`, `322-383`)
- 768 `FindFirstFile` calls across 91 folders. One `z_SC4UIScale_*` listing per folder, matched in memory with the same order and first-match rule, takes 15-19 ms down to 4-7 ms.
- The `ItemIcons-*` marker is redundant.
- Re-run `Test-FolderDiscovery.ps1`. VERIFIED, small.

### A9. SpinProbe runs its full diagnostics at every shutdown in fix-only mode (`SpinProbe.cpp:1238-1465`; director `:1347-1354`)
- The shipped settings are `SpinProbe=0`, `SpinFix=1`.
- ✔ Today: `SPINPROBE armed for 30s at 20Hz - ... 40 thread(s)`.
- The partial reports, the #104ORDER walk, DumpLoopFields and StackScan still run, despite the director comment. That was 56-58 lines in 2 of the last 4 sessions.
- Fix: pass the mode into the sampler. Keep SampleOnce, the 3-sample spin test and SPINFIX, because the #104 fix lives in the sampler (`:1135`).
- About 900 of the file's 1,528 lines are diagnostic-only.

### A10. Small boot I/O (VERIFIED)
- `WriteArmState` (`ScaleTier.cpp:1620`) rewrites both STATE files every boot, inside OneDrive. Skip the write when nothing changed.
- `MigrateRootLooseFiles` calls `CreateDirectoryW` unconditionally (`:4157`), which creates an empty `Plugins\010-SC4UIScale` on every sc4pac boot.
- ArmOne stats the payload twice (`:1521`, `:1564`).
- The boot-phase TOTAL counts the walk twice, because the webbtn timer wraps the first `BootIndex::Ensure`.

### A11. The CSIDRAW probe hook installs by default (`CodePatches.cpp:9566`, `5165-5201`)
- It installs at MissionBubbleFx mode ≥ 2 (the default) on a draw that fires 23-98 times a second.
- It serves only the dev knob `CsiKill`, and it hooks without a prologue check.
- Fix: install it only when `CsiKill != 0` or mode ≥ 3. VERIFIED.

**Already cheap (no action).**
- The logger checks the level before formatting and flushes once per line. The SHUTDOWN trace depends on that flush.
- The default tick does no ini or file I/O. The LiveTune poll is off unless `LiveTune=1`.
- The crash-killer re-enumerates only after a change.
- `RatingUpdateDetour` fires about once a minute.
- Of the hot draw hooks, only CsiDraw, CreateEffect and RatingUpdate install with the shipped ini.
- Release build flags: /O2, LTCG, static CRT, COMDAT folding.

## B. Simplification

### B1. Dead code in `UiSpike.cpp` (about 1,500 lines)
✔ Reference counts were spot-checked for 17 of the symbols below. The rest are VERIFIED by the reviewer, with a comment-stripped grep of `src\`.

**Uncalled functions.**
- `SubPlaceLeft` (1209-1212).
- `SubSharedBottom` together with its only callees `SubBarClampsAt8Rows` and `SubContainerShiftPx` (1365-1521).
- `ScanRegion` and `RegionStats` (1692-1811).
- `LogBufCandidate` (1979-1999).
- `Abs32` (6402).
- `LiveDumpChildren` and `LiveSnap` (9542-9588, plus `UiSpike.h:214`).
- Unreferenced constants, typedefs and globals at 19092-19169.

**Flags never assigned.**
- `gCtxHalve`, ✔`gInitScale`, `gHideRing`, `gForceRecreate`, `gClassHalveRing`, `gRingScale`, `gDumpAtlas` and `gRing2xBlit` (2026-2131), plus `gBltScale` (3822).
- Their branches are dead: 2047-2058, 2978-2992, 3846-3855, 4766-4771, 4847-4853. `InitThunk` never installs.

**Globals never read.**
- `gMouseSlot`, `gStripForceX`, `gStripHitDX`, `gSubStripShiftRows`, `gSubContainerShiftRows`/`Fine`, `gReadoutLogs`, `gS20Rect`, `gTalSkip`, `gPaintHits`, `gGodFixLogs` and `gReqResIgnored`.
- `SetRequestedResIgnored` lost its only reader in commit 895efe6.

**Retired or rejected paths.**
- The disaster "derived dock" (7000-7102, `UiSpike.h:69-87`). `DisDockTarget` always returns false.
- SubFlyoutBorn2x (6609-6756, 8348-8357, director 1064-1067). `REGRESSION.md:2357` lists it as "ALL REVERTED".
- DockDialogs (18597-18737, 6379-6400). `Settings.h:402` says it "malforms".
- **EarlyBake mode 2** (9159-9170). It repeats the v2.41.15 crash shape and is one ini key away. **Delete it.**
- EdgeProbeTick (8101-8122, 8219-8321). Tasks #59 and #60 are closed.
- REGIONCAM/REGIONWATCH (18739-18935, 19171-19278). The #131 lever was MEASURED DEAD, yet these still run on every region visit.

**Update in the same change.**
- `Test-SubFlyoutPlacement.py` check 2 wrongly says `SubContainerShiftPx` is "still used by the disaster twin".
- `emu_subsharedbottom_model.py`.
- `research/laws/project-sc4-flyout-bottom-anchor.md:4`, which still says "NOT YET live-tested".

**SUSPECTED dead.** `ScaleMenuFlyouts` (19650-19748), `ScaleTarget` (20317-20349), and GODSHOW/GODFIX (8510-8531, 8658-8714), which logged nothing across 14 opens today.

**Keep.**
- `DumpTree`/`LiveViewDump`: they feed Audit-UnscaledWindows (`REGRESSION.md:273`).
- SELPERF.
- MMGRID/MMHIST (`:7238`, "permanently").
- SUBOWN.
- The DPROBE walk.

**Move rather than delete** (about 470 lines, all off by default): VisTrace, MPROBE and ICONPROBE.

### B2. The sub-flyout legacy target is unreachable in a normal configuration since v4.10.2
- The legacy target is `UiSpike.cpp:15436-15503` (`SubPlaceTop` with SUBSHIFT).
- `bornOwned` needs birth's record, which is set only at `:7732`. That requires:
  - the Place hook;
  - SubBornScale, SubBornDock and SubMath all on;
  - a tier above 1.01;
  - the return address 0x7EB196;
  - the container id 0x8A6E61E0.
- ✔ Today: SUBOWN 14, SUBSHIFT 0.
- The fallback runs only when one of these holds:
  - the Born flags are off;
  - `SubFlyoutBorn2x > 0`;
  - MinHook failed;
  - the height changed after birth (plausible only at 1.5x).
- Cutting it down to the constant offset saves about 130 lines.
- Side note: SUBSHIFT also runs when SubMath=0, so the "instant revert" note at `:1302` is no longer exact.
- **Leave the born path itself alone.** It is user-confirmed.

### B3. Dead code in `CodePatches.cpp` (about 300 lines)
- The `ApplyRegionCameraScale` tombstone: 2545-2650, constants 239-293, header 98-120 (`REGRESSION.md:5943`).
- Exports that nothing calls: `RegionCameraScaleApplied`, `RegionTileFactor`, `RegionTileSharp()`, `RegionIsoPatchedSites`, `RatingArrowAnchorArms`, `MissionBubbleFxHits`, `CheatDialogPatched` and `GraphLegendPatchedSites`. The header claims UiSpike reads the last one; it does not.
- The `kMarkerSizeWriteEnabled=false` branch (7605-7644) and `kInstFlagBits` (5052).
- `ApplySubFlyoutProviderScale` (3450), which `UiSpike.cpp:8354` calls the "DEAD constants path".
- Keep PIXTABLE (6074) until an A/B test.

### B4. ScaleRemap.cpp (619 lines) is the REJECTED whole-frame approach
- `Settings.h:127` records it, and it defaults to off.
- Removing it is a decision, not a cleanup.

### B5. One hook-install helper (`CodePatches.cpp`)
- 27 hooks are hand-rolled across 18 functions, with 26 `MH_Initialize` sites whose failures are handled three different ways.
- Six hooks skip the prologue byte check (1683, 2085, 5189, 8276, 8571, 8599). Three of them are live in the shipped config: 0x7AE3D0, 0x7AE510 and 0x46D990. That contradicts `CodePatches.h:6`.
- Replace them with `HookVerified(tag, va, stock, n, detour, orig)`, about 400 lines smaller. Read the six stock prologues from the exe first.
- A single table does not fit here, because the hooks install at four different moments.

### B6. One byte-write helper (`CodePatches.cpp`)
- 16 functions hand-roll verify, protect and write (34 of the 46 `VirtualProtect` calls) instead of calling `VerifiedWrite` (`:2706`), which uses PAGE_EXECUTE_READWRITE and flushes the instruction cache.
- ✔ The drift: `.text` immediates are written under **PAGE_READWRITE** with no flush (5755, 5968). That leaves the 4 KB code page briefly non-executable.
- ✔ The **CsiCountPlate override (5742-5752) writes `.text` with no `VirtualProtect` at all.** That is a boot crash if `[UiSpike] CsiCountPlate > 0`, a dev knob.
- `7449` and `7898` patch data pages, where PAGE_READWRITE is correct.
- Consolidating saves about 150 lines.

### B7. `GetModuleHandleW(nullptr)` appears 76 times (`CodePatches.cpp`)
- Examples: once per `CreateEffectDetour` spawn (8842), and in every probe detour.
- The exe is fixed-base 0x400000 (relocations stripped, no ASLR), and `ProbeSafe::Resolve` already caches the base.

### B8. The ini is parsed in about 100 places
- `UiSpike.cpp:13956-14182` (about 58), the director at `:173-217` (21), and CodePatches (24). `Settings.cpp` already parses it once.
- WindowMode is parsed in two places: the director `:438-451` and UiSpike `:20617-20629`.
- The code's comments record two past cases of drift between these readers.
- Parse once. Keep the BOM check (`ScaleTier.cpp:4540`).

### B9. Duplication in `UiSpike.cpp` (about 350 lines)
- Nine identical id-membership loops (5398-6515).
- Five copies of the liveness re-check (12114, 17190, 18684, 19690, 20285) could become one `StillChildOf()`.
- The 7-id parent table is written three times (7997, 15255, 15292).
- The sub-flyout geometry sum is written three times (1384, 7613, 15479). ⚠ This is on the v4.10.2 path, so take care.
- `gSpikeSelf` and `gSpikeForHook` hold the same pointer.
- 60 ini-read plus `atoi` pairs could be one table.
- Rounding bypasses `RoundHalfUp`: `std::lround` at 18140-18396 and `x*m+0.5f` at 10029-10442. Also, `ScaleTier.cpp:3161` defines a *different*, truncating `RoundHalfUp(float)` under the same name.

### B10. Comment bulk
- `UiSpike.cpp` has 8,876 comment lines out of 22,134 (40%). About 2,500-3,000 of them are version-history narrative.
- Of the 260 versions cited in comments, 137 are already in `REGRESSION.md`. **Move this text, don't delete it.**
- Examples: 12365-12440, 17587-17660, 864-932, and 3011-3030 (20 lines about deleted code).

### B11. Splitting `UiSpike.cpp`
- The selector comes first: 20351-22134, 1,784 lines. It shares only `SafeAbsRect`, `gReadoutW`/`H` and `settings` with the rest.
- Then:
  - region screen (18597-19648);
  - ID tables (5370-6608);
  - minimap (1616-2010, 4300-4640, 10967-11946);
  - flyout hooks (2010-5370);
  - sub-flyouts (940-1530, 6609-8100, 15201-15937).
- It needs one internal header for `gTierF`, `RoundHalfUp` and `ChildSnapshot`.
- The real knots are `ScaleGodFlyouts` (2,853 lines), `ScalePanelsUnder` (1,928) and `IncrementalPass` (1,371).

### B12. ✔ One package list for Deploy and Build-Dist
- `Build-Dist.ps1` regex-parses the 90 `Copy-Item` lines in `Deploy-OnGameClose.ps1`. Thirty of them are invisible to the regex and are hand-compensated (`:367`).
- The missing SelectorUI (`:94-106`) was that class of bug.
- One data file that both scripts read would remove the class.

### B13. Migrations that can retire later
- `MigrateRenamesToPayloads` (`:1660`) and PackageInstalled's legacy names (`:790-812`) serve the rename layout of v4.4.0 and earlier, at about 1 ms per boot.
- The Documents-mirror cleanup (`:5657`) serves builds from before 2026-08-30.
- Keep `MigrateRootLooseFiles`.

## C. Found along the way (behaviour, not efficiency)

### C1. ✔ Half of the #89 fix ships switched off
- #89 closed at v2.41.19 with the user's confirmation, tested with the dev ini at `EarlyDock=2`.
- The compiled default stayed **1 = LOG ONLY** (`Settings.h:307`, "SHIPPING DEFAULT"), and no shipped ini has ever set it.
- `REGRESSION.md:3042` says both halves are required.
- Today's log shows the shipped behaviour:

      EARLYDOCK would scale dock 0x0987B48F now - ... +328ms after arm ... LOG ONLY (EarlyDock=1)
      FLASHSET city 0x0987B48F scaled 25 window(s) ON SCREEN - THIS ONE FLASHED, +1125ms after city arm

- So in the public build the dock paints at 1x for about a second on every city open.
- **Decide:** ship 2 after an eyes-on test, or retire the claim.

### C2. Stale comments
- `:8575` and `:8807` say ShowHook ships at 0, but its default is 1.
- `CodePatches.h` says UiSpike reads `GraphLegendPatchedSites`; it does not.
