**Standing orders**
- [⭐ NORTHSTAR: GITHUB IS THE SOURCE OF TRUTH](feedback-github-is-the-source-of-truth.md) — USER ORDER. The `sc4uiscale` private repo is canonical; EVERY session ends with a commit+push. Ledger entry and commit are ONE action. An audit found the repo held 2.8% of files and was missing 3 of 8 package builders. ⭐ PRESENCE IS NOT EXECUTION: a later audit passed all builders as *present*, then a cold-clone test RAN them and 5 of 9 refused on inputs nothing derived. Run it, don't check the file exists
- [⭐ NORTHSTAR: CHECK OUR PREVIOUS WORK FIRST](feedback-check-our-previous-work-first.md) — USER ORDER. Two questions: have we hit this before, and is that cure VIABLE HERE (if so PORT it). Cost 4 defects in one day
- [NORTHSTAR METHOD: the docs are the SDK](feedback-docs-are-the-sdk.md) — our docs → vendor headers → live instruments → disassembler → shipped experiment. Document novelties the SAME session
- [NORTHSTAR: scratchpad is volatile](feedback-scratchpad-volatile.md) — wiped without warning; durable work goes in `<Project>\_tests\` / `_packaging\`
- [Don't raise intro-video scaling](feedback-dont-raise-intro-video-scaling.md) — SC4 #138; never mention unless asked about the backlog

**Evidence laws**
- [NULL IS NOT EVIDENCE](feedback-null-is-not-evidence.md) — a probe finding nothing isn't a fact until you prove it COULD have seen the thing; state the positive control
- [Instrument scoped to the wrong CHANNEL](feedback-instrument-scoped-to-the-wrong-channel.md) — a TRUE null proves nothing if the API never routes through your hook. When a feature is INERT, find the GUARD, not the handler
- [⭐ SIMULATE THE CONSUMER, not the build](feedback-simulate-the-consumer-not-the-build.md) — 6 straight "fixed" claims were wrong on screen; each described what the BUILD did. Model the consumer, measure the SHIPPED file
- [GATE ON THE CONDITION YOU DEPEND ON](feedback-gate-on-the-condition-you-depend-on.md) — bolting work onto a convenient neighbour makes it inherit that neighbour's gate SILENTLY; AutoScale=0 disabled a whole cure and the log looked clean
- [THRESHOLDS COME FROM CONTROLS](feedback-thresholds-come-from-controls.md) — 3 guessed numbers, 3 wrong (90% vs 81.8%, state 2 vs 3, brightness vs border). Measure the known-good set; if a gate fails THEM, the gate is wrong
- [TWO BLIND INSTRUMENTS AGREEING = ONE](feedback-blind-instruments-agreeing.md) — corroboration counts only between INDEPENDENT failure modes
- [STATIC DEFECT = HYPOTHESIS](feedback-static-defect-is-a-hypothesis.md) — not a defect until something ON SCREEN disagrees
- [Text scanners are BLIND to binaries](feedback-text-scanners-are-blind-to-binaries.md) — byte-scan raw AND NUL-stripped; zero items scanned is a REFUSAL
- [SC4 measure, don't infer](feedback-sc4-measure-dont-infer.md) — measured values land first try; inferred ones cost 2-3 builds
- [⛔ SC4 ships NINE archives, not 7](reference-sc4-intro-dat-is-the-eighth-archive.md) — a written-down inventory fails silently, and only in the case you needed. DISCOVER, don't list
- [Never re-pin a fingerprint without reading the bytes](feedback-never-repin-a-fingerprint-without-reading-the-bytes.md) — bypass → run every byte-level assertion → re-pin only if all pass

**Packaging / delivery laws**
- [A package isn't done until it's in the MANIFEST](feedback-a-package-is-not-done-until-its-in-the-manifest.md) — three packages rotted identically: hand-placed, absent from deploy+integrity scripts, everything green
- [Batch files need CRLF](feedback-batch-files-need-crlf.md) — Write emits LF; cmd.exe then jumps to the WRONG byte offset on call:/goto, silently

**SC4 — status + process**
- [⭐ #176 CLOSED v3.0.1 — the LATCH LAW](project-sc4-15x-three-open-defects.md) — a SetImage-latched crop is a hidden consumer of bind-time geometry; resizes never refresh it; ask WHEN content was BOUND. RELATCH armed per staged root. #149 also closed (auto custom lots)
- [SC4 1.5x CLOSED + ⭐the OFFSET-PARITY LAW](project-sc4-15x-three-open-defects.md) — **`q | d` or the child's offset dies at f=1.5**; predicts WHICH AXIS breaks per panel (advisors "high", My Sim "left"). Whole eyes-on family user-confirmed as of v2.96.0. Cure = SEAT the child, never nudge
- [⭐ Scale the MOD'S OWN dialogs, not just our targets](feedback-scale-the-mods-own-dialogs.md) — CAM's windows sat at 1x for the project's whole life with EVERY GATE GREEN. Run the census in BOTH directions; `blttype=normal` art is clipped, never stretched, and the `imagerect` CROP is a third number that does not scale itself
- [SC4 projects SPLIT + START-HERE.md](project-sc4-projects-split-and-entry-point.md) — `SC4UIScale\` and `SC4Touch\` share ZERO files; START-HERE.md is the entry point
- [SC4UIScale publish route](project-sc4uiscale-github-publish.md) — rebuild via `_packaging\Build-PublicRepo.ps1` gated by `Test-NoForeignContent.py`
- [SC4 scaling LAWS](feedback-sc4-scaling-laws.md) — **THE 105 LAWS; READ THE FILE before touching UiSpike.cpp, CodePatches.cpp or a .UI generator.** Most-used: ⛔99 a `.rdata` constant sweep is BLIND to INLINE IMMEDIATES — #188's two levers were `imm32` inside instructions, so every data-section null was FILTERED · ⭐100 SUPPRESSION IDENTIFIES, SCALING DOES NOT — ask an unknown drawer to STOP, never to grow · ⭐101 two overlapping elements at similar sizes need a 3x probe, not 1.5x (three contradictory readings vs one correct) · 103 a constant can be LIVE and still be the WRONG constant (42.0f fed translation, not extent) · ⭐96 ask WHO COMPUTES THE GEOMETRY (sweep / static builder / data pre-scale) — #170's advisors sat behind `kDataScaledSubtreeIds` so two fixes aimed at `ScaleSubtree` were dead code, and the log said `1 windows scaled` the whole time · 97 a gate that MODELS a rule must prove the rule RUNS there · ⛔98 DBPF file hashes are NOT reproducible (2-byte header timestamp at offsets 25/29) — compare ENTRY PAYLOADS · ⭐92 a "known residual" that exists at ONE TIER ONLY is the defect, not a residual — 347 of them sat under a PASS line for weeks · ⭐93 ask LIGHTER or DARKER before building anything (light=painted, dark=uncovered; six fixes hunted the wrong family) · 94 the right rule at the wrong SCOPE — hand-lists rot, key on the DERIVED list, and wire EVERY builder · 95 any new fractional-tier metric must read exactly 0 at 2x/3x first or it is measuring itself · ⭐89 ONE rounding convention `floor(v*f+0.5)` across sweep+upscaler+builders · 90 the fix is often already in the file with a comment naming it · 91 a probe on a lazily-installed hook is a guaranteed null · ⭐86 the sheet's ROLE decides its sizing rule — strip /N, 9-slice /3, tiled NOTHING · 87 rule out your own last change first by NAMING CONSUMERS · 88 a model that would condemn stock is broken · 83 a GZWinBMP's window size is an OUTPUT — scale the source buffer, not the window · 82 a clipped runtime string has TWO constants, surface AND anchor · 79 two cell counts disagreeing ⇒ the LCM is wrong for BOTH · 80 fix the number that's wrong, not the one REPORTING it · 76 a heuristic that IDENTIFIES is safe for protecting, unsafe for resizing · 73 a blit has THREE numbers — source, CROP, destination · 71 a gate that only asks about YOUR work can't see work you never started · 69 a revert that doesn't move the symptom means the attribution was wrong · 64 find the instance with a SIBLING THAT WORKS · 66 a .UI edit is scoped to that .UI, an ART edit to the WHOLE GAME · 59 every consumer of a shared hook needs its OWN gate · 54 no log line = did not run · 42 a gate is only as honest as its SCOPE
- [SC4 blast radius + ripples](feedback-sc4-blast-radius.md) — state PRIZE vs BLAST RADIUS; simulate offline in tools\uimap first
- [SC4 regression net STANDING ORDER](feedback-sc4-regression-net.md) — maintain _tests\ suites + goldens + REGRESSION.md
- [SC4 test SCENARIO MATRIX](reference-sc4-scenario-matrix.md) — 5 bugs in one session came from an untested axis
- [SC4 founded-city invalidates old notes](feedback-sc4-founded-city-invalidates-notes.md) — run Set-StockCompare FIRST
- [SC4 deploy = wait-for-close](feedback-sc4-deploy-on-close.md) — the game runs ELEVATED and holds the DLL/dats open; NEVER kill it
- [⛔ SC4 Plugins scan is RECURSIVE](feedback-sc4-plugins-scan-is-recursive.md) — a stash INSIDE `Plugins\` disables NOTHING; enumerate BOTH trees before believing any "stock" claim
- [⛔ SC4 "zoomed in" = Windows DPI virtualization](reference-sc4-zoom-is-windows-dpi-virtualization.md) — HKCU shim, survives reinstalls; cure = HIGHDPIAWARE. Check the shim BEFORE the mod. A non-DPI-aware resolution query reports the SCALED-DOWN logical size, not true native pixels — GetDeviceCaps(DESKTOPHORZRES/VERTRES) after SetProcessDPIAware() is the only reliable read

**SC4 — engine references**
- [SC4 hooking: never guess a calling convention](reference-sc4-thiscall-hook-rule.md) — 2 crashes in one session; __thiscall detour = __fastcall(self,edx), unknown arity = naked tail jmp, and slot 87 is NOT GZPaint
- [SC4 SDK LOOKUP — run it FIRST](reference-sc4-sdk-lookup.md) — `python tools\sdk\lookup.py <id|tgi|script>`; step 0 of TRIAGE
- [SC4 CRASH? read the game's OWN exception report FIRST](reference-sc4-exception-reports.md) — faulting EIP + registers; Windows WER is a structural null here
- [SC4 REGION SCREEN — fully decompiled](reference-sc4-region-screen.md) — 197 fns, 17-lever table; #131/#132 CLOSED, #133 rotate IMPOSSIBLE
- [⭐ SC4 CSI = the U-Drive-It offer balloon](reference-sc4-csi-indicator.md) — TWO quads (pin 64 + icon 35), both sized by INLINE .text immediates; the icon's number is ALSO its click box; art exists twice in two groups
- [SC4 UI SDK boundary](reference-sc4-ui-sdk-boundary.md) — renderer-drawn elements are unreachable; triage test first
- [SC4 runtime-image lever](reference-sc4-runtime-image-lever.md) — GZWinBMP draw hook fixes any runtime-supplied image drawing 1x
- [SC4 minimap terrain bake](reference-sc4-minimap-bake.md) — blit MUST be an exact power-of-two multiple of terrainDim
- [SC4 rich text = HTML engine](reference-sc4-html-text-engine.md) — SIZE tables live in .rdata; FontStyle.ini can never reach them
- [SC4 flyout alignment-marker rule](reference-sc4-flyout-alignment-marker-rule.md) — flyoutPos = buttonAbs − marker
- [SC4 flyout hit-test playbook](reference-sc4-flyout-hittest-playbook.md) — router first-claim-wins, two-gate hit model
- [SC4 terraform = the dock model](reference-sc4-terraform-dock-is-the-model.md) — dock offset (6,160)
- [⭐ SC4 WINDOWED MODE = dgVoodoo's FullScreenMode](reference-sc4-windowed-mode-dgvoodoo.md) — `WindowMode=Windowed` alone does NOTHING; the wrapper overrides it. Also the tier minimums (3x needs 2400x1800) and `Set-Tier` has no 1x
- [SC4 resolution control](reference-sc4-resolution-control.md) — SC4GraphicsOptions.ini. ⚠ NEVER write it with a BOM
- [SC4 GOLDEN working backup](reference-sc4-golden-backup.md) — ⚠ THREE FontStyle.ini probe sites; miss one and "stock" keeps our fonts

**SC4 — UI scaling + touch**
- [SC4 UI Scaling NORTHSTAR](project-sc4-ui-scaling-northstar.md) — native high res + UI ELEMENTS enlarged; whole-frame upscaling = wrong turn
- [SC4 sub-flyout RING LAW](reference-sc4-subflyout-ring-law.md) — ring+strip+bar are ONE WELDED shape; seat with the DOCK, never a nudge
- [SC4 pre-scale while hidden](feedback-sc4-prescale-while-hidden.md) — gate on GEOMETRY; a show detour fires BEFORE the visible bit
- [SC4 1x flash = reactive sweep](feedback-sc4-reactive-sweep-flashes.md) — cure = born-2x, NEVER suppress paints
- [SC4 open-jump FIXED v2.36.2](project-sc4-flash-subflyouts.md) — a first-use-only defect = an uninitialised LATCH
- [SC4 Data Views legend v2.37.0](project-sc4-dataviews-legend.md) — scale the ORIGIN inside the game's own re-lay, never the step
- [SC4 #89 minimap ✅ + #91](project-sc4-city-map-jump.md) — EARLYDOCK; #91 NOT-A-BUG — run the STOCK CONTROL before porting a cure
- [SC4 god-mode flyouts](project-sc4-god-flyouts.md) — ✅ COMPLETE v2.11.30, user-confirmed
- [SC4 third-party patches STANDING ORDER](project-sc4-thirdparty-patches.md) — EVERY override gets a memory + UPSTREAM report
- [SC4 CAM install status](project-sc4-cam-install-status.md) — CAM 3.1.1+SIM+Ordinances verified in; 3 open decisions
- [SC4 regions need config.bmp](feedback-sc4-region-needs-config-bmp.md) — the game DELETES .sc4 files at region load when it's missing
- [SC4 Touch Controls](project-sc4-touch-controls.md) — SHIPPED v1.0.4/v1.0.5; **dist\ FROZEN**
- [⛔ SC4 dialogs live under the MAIN WINDOW](reference-sc4-dialogs-live-under-main-window.md) — not the 3D view, and drawn INSIDE the DirectX hwnd. Touch only holds view3d ⇒ blind to every dialog/popup; ids 0xAA921F4F / 0x6AAEEC4A
- [SC4TouchControls — RE-QUARANTINED 2026-08-13](project-sc4touchcontrols-independence.md) — flag has flipped twice; **check the quarantine folder, don't assume**. Never reinstall to `Plugins\` without asking
