# Batch A + run-sheet agent — progress checkpoint

Jobs: (1) BATCH A static dialogs 6b704690 / ca539343 / ebd0d36d → v2.24.1-batcha;
(2) _tests\RUN-SHEET-NEXT-SESSION.md.

## Status log
- 2026-07-29: START. Barrier NOT met on first read — SC4UIScaleDllDirector.cpp is at
  "2.23.3-lifecycle"; tier-math agent's checkpoint shows it is at Step 0 (survey) and has
  landed NO items yet (no Test-DatIntegrity edits so far). Polling every 60s, 45 min cap.
- Read tier-math-fixes.md + coverage-matrix.md. Starting Job 2 source reading while polling
  (run sheet touches no shared files).

## Barrier
- [x] CLEARED at poll 30 (~30 min): UISCALE_VERSION_STR == "2.24.0-tiermath" observed.
      Tier-math agent fully finished + deployed; it added 4 tier dats (suite header 11->15),
      DialogStatic counts untouched by it at 255 → my edits merged additively, its 4 new
      ItemIcons/ItemIconsSub entries (Test-DatIntegrity lines ~128-131) left intact and PASSING.

## Job 1 prep facts (read-only, gathered while waiting)
- All 3 target .ui scripts exist in tools\uiscripts\extracted (I-6b704690/I-ca539343/I-ebd0d36d).
- kNeverScaleIds currently does NOT contain 0x8A8DFCF5, 0x0A551C53 or 0x000A0000 → all three
  get ADDED (verified against the full array, UiSpike.cpp:2107-2178).
- Test-DatIntegrity.ps1 DialogStatic entries = 255 at all 3 tiers (lines 73/118/120 pre-merge).
- Deploy layout (Plugins = <PROJECT-ROOT> 4\Plugins):
  root holds z_SC4UIScale_DialogStatic-2x.dat (live) + -15x/-3x as .dat.x1-disabled + SC4UIScale.dll.
- Build: MSBuild = VS18 Community, project src\SC4UIScale.vcxproj → build\Release\SC4UIScale.dll.
- Python 3.12 at %LOCALAPPDATA%\Programs\Python\Python312.
- dialog-static outputs: 2x → tools\dialog-static\z_SC4UIScale_DialogStatic.dat (untagged);
  1.5x/3x → tools\packages\<tag>\z_SC4UIScale_DialogStatic-<tag>.dat.

## Job 1 — Batch A  (COMPLETE except DEPLOY — game was running)
- [x] TARGETS +3 in build_dialog_static.py (Batch A block after TEXT-SWEEP BATCH, with the
      id-sharing note): 6b704690 Label Tool, ca539343 bubble stub, ebd0d36d bridge sibling.
      Target-script count 158 -> 161.
- [x] kNeverScaleIds: grepped ALL of src\ first — NONE of the three ids existed anywhere
      (0x8A8DFCF5 was NOT already listed, contrary to the brief's "may already be"), so all
      three ADDED with comments after 0xCA5E6261. No duplicates created.
- [x] Rebuilt --factor 2 / 1.5 / 3 → 259 entries EACH (was 255; +4 = 3 scripts + 1 art that
      became referenced). Builder self-verify clean: all 3 "edited ... areas=N", left1x=0 each,
      zero FAIL/MISMATCH, "listing verified". Outputs: tools\dialog-static\...DialogStatic.dat,
      tools\packages\15x\...-15x.dat, tools\packages\3x\...-3x.dat.
- [x] Test-DatIntegrity.ps1: the 3 DialogStatic entries 255 -> 259, dated "Batch A, task #54"
      comment block on the 2x line + short tags on 15x/3x. ADDITIVE — tier-math's 4 entries
      untouched.
- [x] Version bump 2.24.0-tiermath -> "2.24.1-batcha"
- [x] MSBuild Release/Win32 CLEAN (8/1107 functions recompiled, LTCG incremental, no warnings)
      -> build\Release\SC4UIScale.dll
- [ ] DEPLOY **BLOCKED / NOT DONE**: tasklist shows "SimCity 4.exe" PID 23148 RUNNING.
      Per the hard rule nothing was copied. Plugins still hold the 255-entry dats + DLL
      v2.24.0-tiermath. The 4 copy commands are written out in REGRESSION.md's BATCH A
      section ("TO FINISH"). Artifacts are built and waiting.
- [x] Both suites run:
      Test-DatIntegrity → exit 1 with EXACTLY 3 FAILs, all three the same deploy-pending
        shape: "z_SC4UIScale_DialogStatic-{2x,15x,3x}.dat: 255 entries, expected 259".
        Nothing else failed (tier-math's new entries, font sources, DLLs, frozen-bundle
        hash all fine). NOT a regression — expectations describe the built artifacts.
      Test-ScaleTierDecide → "ALL PASS (14 named cases + 5000x2 random fit sweep)" exit 0.
- [x] REGRESSION.md: "## BATCH A — last three static dialogs (v2.24.1, 2026-07-29 night,
      task #54)" appended after the TIER MATH section — table of the 3 roots, both-halves
      rule, the id-sharing do-not-fix note, 255->259 (+4 why), the NOT-DEPLOYED warning with
      the 3 FAIL lines quoted, the 4 copy commands, trap signatures, run-sheet pointer.
- [x] Run sheet updated: 1.13 carries a ⚠ PREREQ (deploy + suite green before those items
      mean anything) and 1.2's bubble-stub check cross-references it.

## HANDOFF — the one open action
Close SimCity 4, run the 4 copies from REGRESSION.md "BATCH A / TO FINISH", re-run
Test-DatIntegrity.ps1 (must read "ALL PASS (15 dats + 3 font sources + 2 DLLs +
frozen-bundle hash)"), then the run sheet is fully actionable.

## Job 2 — run sheet
- [x] Source material read (coverage-matrix, codecreated-noncity, tier-generality-audit,
      tier-math-fixes, lifecycle-hardening, task49-grutzehaus, REGRESSION.md Pending +
      v2.21.x-v2.24.x, UiSpike ini/MCAL/DPROBE/DGP-OPEN code, kNeverScaleIds, dock table)
- [x] RUN-SHEET-NEXT-SESSION.md WRITTEN (2026-07-29): Part 1 Verify = 13 numbered item
      groups (splashes, region+bubble stub, flash task#50, My Sims family, U-Drive-It chain,
      Grutzehaus icons, Graphs frame, Data Views, news/toasts/credits, airports heal,
      tutorial, small transients, Batch A dialogs); Part 2 Measure = 6 steps (2 screenshots,
      Trip-Types, MCAL, StripDump/DGP-OPEN, DPROBE bands, cityA->region->cityB ptr= cycle);
      Part 3 = 3 known-broken groups; + before-launch block + restore-ini block.
      NOTE: 1.13 Batch A items assume Job 1 deploys — revisit if barrier times out.
- Facts pinned while writing: ini = Plugins\SC4UIScale.ini (DLL-sibling), log =
  SC4UIScale.log; MCAL fires only for kMayorFlyoutDock entries (U-Drive-It flyout has
  NONE yet — sheet says the absence is the finding); DPROBE walks 0x9A47B417 only,
  vis=1-only, band-gated; MPROBE covers main-window children (region layers); flash fix
  = v2.22.4 pre-scale list; My Sims = NINE roots incl. evict confirm 0xEA1F1E5E.
