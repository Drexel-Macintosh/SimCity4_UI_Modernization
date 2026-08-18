**Standing orders**
- [⭐ NORTHSTAR: GITHUB IS THE SOURCE OF TRUTH](feedback-github-is-the-source-of-truth.md) — USER ORDER. The `sc4uiscale` private repo is canonical; EVERY session ends with a commit+push. Ledger entry and commit are ONE action. An audit found the repo held 2.8% of files and was missing 3 of 8 package builders — measure, don't assume
- [⭐ NORTHSTAR: CHECK OUR PREVIOUS WORK FIRST](feedback-check-our-previous-work-first.md) — USER ORDER. Two questions: have we hit this before, and is that cure VIABLE HERE (if so PORT it). Cost 4 defects in one day
- [⭐ NORTHSTAR: no progress recaps](feedback-no-progress-recaps.md) — USER ORDER. No ledgers, no "what's shipped", no lists of confirmed fixes. Report the CURRENT problem only
- [⭐ NORTHSTAR: NEVER STOP TO REPORT](feedback-never-stop-to-report.md) — USER ORDER. In auto mode KEEP EXECUTING. A turn ends only when DONE or blocked on the user. Never end on "next I will…"; chain reads/builds/deploys, ledger in the same turn
- [NORTHSTAR: never offer to stop](feedback-never-offer-to-stop.md) — never propose banking wins or accepting a fixable defect; measured-safe + scoped = BUILD IT
- [NORTHSTAR METHOD: the docs are the SDK](feedback-docs-are-the-sdk.md) — our docs → vendor headers → live instruments → disassembler → shipped experiment. Document novelties the SAME session
- [NORTHSTAR: scratchpad is volatile](feedback-scratchpad-volatile.md) — wiped without warning; durable work goes in `<Project>\_tests\` / `_packaging\`
- [Instructions go at the BOTTOM](feedback-instructions-at-the-bottom.md) — anything the user must DO ends the message in one block
- [Keep pace — brief thinking](feedback-keep-pace-brief-thinking.md) — decide and move; rigor = fast instruments, not long thinking
- [No project/mission talk](feedback-no-project-mission-talk.md) — stay on the concrete task until lifted
- [Don't raise intro-video scaling](feedback-dont-raise-intro-video-scaling.md) — SC4 #138; never mention unless asked about the backlog
- [Don't raise MeetSurface](feedback-meetsurface-not-installing.md) — never being installed; don't mention it unless the user does
- [FROZEN: Simulator Workstation X64](feedback-simulator-workstation-x64-frozen.md) — never change that package without explicit approval

**Evidence laws (cross-project)**
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
- [Verify without stealing foreground](feedback-verify-without-stealing-foreground.md) — PrintWindow + UIA InvokePattern, never full-screen capture or synth-clicks

**Packaging / delivery laws**
- [A package isn't done until it's in the MANIFEST](feedback-a-package-is-not-done-until-its-in-the-manifest.md) — three packages rotted identically: hand-placed, absent from deploy+integrity scripts, everything green
- [USB bundles self-contained](feedback-usb-bundle-self-contained-readmes.md) — target machines can't run Claude Code; every dist bundle carries a README, RE-SYNCed each rebuild
- [Batch files need CRLF](feedback-batch-files-need-crlf.md) — Write emits LF; cmd.exe then jumps to the WRONG byte offset on call:/goto, silently
- [Production version history](reference-production-version-history.md) — three VERSION-HISTORY.txt files; keep all updated per release
- [Deployment-ready structure](reference-deployment-ready-structure.md) — START-HERE.txt, install order, `_not-for-deployment\`, Install-Apps.ps1
- [Original source files & Vista packages](reference-original-source-files.md) — pristine SDK/driver/prereq installers
- [Qwen thinking-proxy](reference-qwen-code-desktop-thinking-proxy.md) — 127.0.0.1:8787 Scheduled Task; Alibaba 5MB body cap
- [Agent-roles delegation](project-agent-roles-setup.md) — lane table + escalation ladder (currently SUSPENDED — work in Claude)

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
- [⛔ SC4 "zoomed in" = Windows DPI virtualization](reference-sc4-zoom-is-windows-dpi-virtualization.md) — HKCU shim, survives reinstalls; cure = HIGHDPIAWARE. Check the shim BEFORE the mod

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

**Surface 1.0 platform + driver**
- [Hydra/Milan driver port status](project_hydra_milan_driver_port.md) — Surface 1.0 vision-card Win11 x64 port; phase, HW facts, next step
- [HydraX64Beta driver](project-hydra-beta-driver.md) — side-by-side beta with WPP tracing; USB kit in dist\beta-kit
- [Hydra delta mask forbidden](feedback-hydra-delta-mask-forbidden.md) — NEVER re-enable the changed-cells mask; keep all-0xFF
- [Hydra parity frozen categories](feedback-hydra-parity-frozen-categories.md) — never change delta mask, identity/naming, signature+DriverVer+x64
- [Bump DriverVer per build](feedback-bump-driverver-per-build.md) — before restaging
- [Touch-injection safety](feedback-touch-injection-safety.md) — opt-in + 30s expire + flood cap + ESC kill (a flood forced a Windows reinstall)
- [PixelSenseToTouch bridge](project-pixelsensetouch-bridge.md) — the REQUIRED Surface-contacts→Windows-touch bridge
- [Integrated touch (Mode B)](project-hydra-touch-integrated-mode.md) — CUT 2026-07-15; shipping touch = Mode A only
- [Surface WiFi ZD1211B fix](project-surface-wifi-zd1211b-fix.md) — RETIRED; use a USB dongle
- [Launch the Simulator correctly](project-simulator-launch.md) — Start-Menu .lnk as admin, not the exe directly
- [Simulator on Win11 dev tools](project-simulator-win11-devtools.md) — Win11 Fix MSI: HKLM DPI shims + IL clean-exit patch
- [Surface SDK docs](reference-surface-sdk-docs.md) — ported-app layout wins on conflict
- [Surface Admin Guide + Mgmt Pack](reference-surface-admin-guide.md) — deployment CHM + SCOM .mp
- [Surface Shell registration](feedback-surface-shell-registration.md) — Shell empties the WHOLE launcher if one preview file is missing
- [Surface shell UX rules](feedback-surface-shell-ux-rules.md) — no scroll bars, no external windows, edge-anchored overlays
- [HP V14 brightness buttons](project-hp-v14-brightness.md) — dead buttons = monitor firmware; DDC/CI preset persists

**Surface apps (ports + originals)**
- [Community MSI fixes live in the binary](feedback-community-msi-fixes-live-in-binary.md) — ildasm the shipped binary before rebuilding; CLR2 via MSBuild v3.5
- [Base Defense .NET4→CLR2 fix](project-base-defense-net4-fix.md) — v4 exe vs XNA 3.1 CLR2 = won't launch
- [G-nome Surfer render-crash fix](project-gnome-surfer-render-fix.md) — unguarded worker + 3 dead menu genomes
- [Ribbons+Tiles MSAA fix](project-ribbons-tiles-msaa-fix.md) — check multisample first on any XNA CLR20r3 crash
- [MeetSurface restoration](project-meetsurface-config-path-fix.md) — rebuilt from decompiled source with original BAML re-embedded
- [Radial Panel port](project-radialpanel-port.md) — built from source + MSI; v1.0.1.0 carousel tile art
- [XPCardsHost Solitaire port](project-xpcardshost-solitaire.md) — **the ONE non-MSI app in Apps-x64**; any audit globbing `*.msi` misses it
- [Surface Tetris HD](project-surface-tetris-hd.md) — from-scratch 2P Surface Tetris; separate tile
- [Surface Casino / Milan Room](project-surface-casino.md) — NINE games (Sic Bo LOCKED); v1.1.0.0 packaged, NOT Simulator-tested; 21 audit bugs
- [Surface Arcade suite](project-surface-arcade-suite.md) — six LIVE table games + three SHELVED on SurfaceArcade.Common
- [Surface Arcade design laws](feedback-surface-arcade-design-principles.md) — symmetry (except Risk), one-studio branding
- [Contact state must be derived](feedback-contact-state-must-be-derived.md) — NEVER hand-track contact ids
- [SurfaceButton min size overflows](feedback-surfacebutton-min-size-overflows.md) — silently REASSIGNS which bet a finger places; audit with Audit-Layout.ps1
- [WPF 3.5 software-render limits](feedback-wpf35-software-render-limits.md) — no CacheMode; RenderCapability.Tier lies under forced software render
- [Vista has no symbol font → use vectors](feedback-vista-no-symbol-font-use-vectors.md) — Common\GlyphIcons; build Common FIRST
- [Image magic not extension](feedback-image-magic-not-extension.md) — a WebP named .png throws XamlParseException on Vista
- [Surface Suite / Concierge](project-surface-suite-concierge.md) — Suite.msi = Concierge+Music+Photos; Concierge SHELVED
- [Touch Pack on Win11](project-touch-pack-win11.md) — the web-installer WRAPPER is the problem; extract RCDATA\MSI03
- [Touch Pack install "hang"](project-touch-pack-install-hang.md) — kill ngen.exe not msiexec
- [Vista Games Pack](project-vista-games-pack.md) — slc.dll edition gate + missing CardGames.dll; 9/9 launch
- [Win16 games via otvdm](project-win16-via-otvdm.md) — 16-bit apps run as the real exe through winevdm/otvdm

**Other**
- [✅ SimCity Deluxe PLAYS on the Pixel Fold](project-simcity-deluxe-apk-64bit.md) — ours runs at 60fps under dynarmic; the original apk can't even install. Three of four blocking bugs were INVISIBLE OFFLINE — get on the hardware. Text entry goes through an EDK extension, not the keyboard API. `python port/tools/ship.py` is the one command
- [SimCity J2ME trio in KEmulator ✅](project-simcity-j2me-kemulator.md) — 3 jars + launchers; nojre asset = 32-bit trap, use kemnnx64
- [GM nav DVD (KIWI) rebuild](project-gm-nav-dvd-kiwi.md) — 2008 Avalanche Denso GE20 nav disc; workspace + Phase 0/1 status
- [Always run behavioral sim](feedback-always-run-behavioral-sim.md) — on any rebuilt GM-nav cell/disc
- [IntelliPoint+MKC coexist](project-intellipoint-mkc-coexist.md) — IP 8.2 patched MSI installs beside Mouse and Keyboard Center
