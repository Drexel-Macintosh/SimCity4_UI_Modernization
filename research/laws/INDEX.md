# Engineering Notes

This folder holds the reference material accumulated while building a UI scaling
mod for SimCity 4 — a closed-source game whose interface was never designed to be
resized. Each note documents one mechanism, one measurement, or one rule about
how to investigate a closed engine, and each one was paid for by a defect that
reached the screen. The addresses, constants and formulas in them are byte-verified
against `SimCity 4.exe` 1.1.641 unless a note says otherwise.

## Method and evidence

- [A Null Needs a Positive Control](feedback-null-is-not-evidence.md) — how to tell a real absence from an instrument that was never capable of seeing the target.
- [Corroboration Requires Independent Failure Modes](feedback-blind-instruments-agreeing.md) — why two probes returning the same null can be one non-fact counted twice.
- [A Static-Data Defect Is a Hypothesis](feedback-static-defect-is-a-hypothesis.md) — why a defect visible only in shipped data needs an on-screen symptom before it is fixed.
- [Build the Instrument, Read the Number](feedback-sc4-measure-dont-infer.md) — the cost comparison between measuring a geometry value and inferring it from a screenshot.
- [Take Thresholds From the Known-Good Set](feedback-thresholds-come-from-controls.md) — deriving cutoffs from the population that is already correct rather than from reasoning.
- [Model the Consumer, Measure the Shipped File](feedback-simulate-the-consumer-not-the-build.md) — why a generator graded by its own output passes while the screen disagrees.
- [Gate on the Condition You Depend On](feedback-gate-on-the-condition-you-depend-on.md) — how attaching work to a convenient function makes it inherit an unrelated gate.
- [Byte-Scan the Compiled Artifacts](feedback-text-scanners-are-blind-to-binaries.md) — why a text scanner cannot see a wide string in a DLL, and how absolute build paths reach `.rdata`.
- [Exe Fingerprint Gates and the 4GB Patch](feedback-never-repin-a-fingerprint-without-reading-the-bytes.md) — what to re-verify when the large-address-aware bit moves a hash without moving any code.
- [Prize Versus Blast Radius](feedback-sc4-blast-radius.md) — quantifying both sides before rebuilding a mechanism that currently works.
- [Run the Coverage Census in Both Directions](feedback-scale-the-mods-own-dialogs.md) — finding windows that were never built for, not just verifying the ones that were.
- [Test Scenario Axes](reference-sc4-scenario-matrix.md) — the condition axes that produce distinct scaling regressions, and the trap on each.
- [Founding a City Changes the Window Set](feedback-sc4-founded-city-invalidates-notes.md) — which windows flip from inert template to live panel once a city exists.
- [SimCity 4 Exception Reports](reference-sc4-exception-reports.md) — the game's own crash report, its location, and the faulting EIP and registers it records.
- [Enumerate the DBPF Archives, Do Not List Them](reference-sc4-intro-dat-is-the-eighth-archive.md) — the nine archives in the install root and why a hard-coded list yields false negatives.

## Scaling rules

- [The SC4 UI Scaling Laws](feedback-sc4-scaling-laws.md) — the full rule set governing every widget, art sheet and geometry constant the mod touches.
- [One Path Owns the Scale Factor](feedback-scale-is-exactly-the-factor.md) — why a compensating pin or clamp is two errors arranged to look like none.
- [Offset Parity at Fractional Scale Factors](project-sc4-15x-three-open-defects.md) — the `q | d` rule that predicts which child windows drift at 1.5x and which do not.
- [Pre-Scale Windows While They Are Hidden](feedback-sc4-prescale-while-hidden.md) — scaling before first show so no stock frame is ever painted.
- [The Reactive Sweep and the 1x Flash](feedback-sc4-reactive-sweep-flashes.md) — the architecture behind the mode-transition flash and the born-scaled cure.
- [Born-Correct Flyouts](project-sc4-flash-subflyouts.md) — the creation-time hooks that make nested sub-flyouts arrive scaled, docked and promoted.
- [Sub-Flyout Bottom Anchor](project-sc4-flyout-bottom-anchor.md) — the shared, MEASURED `Place()` margin every sub-flyout's bottom edge must dock to, the two formulas that looked right and weren't, and the reusable method for extending the fix to other menu families.
- [The City Map Jump at City Load](project-sc4-city-map-jump.md) — the dock minimap's late snap and blank interval at the start of play.
- [Data Views Legend: Scale the Origin, Not the Step](project-sc4-dataviews-legend.md) — the single re-lay routine at `sub_007A04F0` and the eight patch sites inside it.
- [The Sub-Flyout Ring Law](reference-sc4-subflyout-ring-law.md) — the ring, stem and strip as one welded sprite, and the Y coordinate that seats it.
- [The Flyout Alignment-Marker Rule](reference-sc4-flyout-alignment-marker-rule.md) — the hidden `0x0000AAAA` child that determines where a flyout is placed.
- [Hit-Testing Clickable cGZWin Menus](reference-sc4-flyout-hittest-playbook.md) — the four layers of a menu and the instrument that identifies each one.
- [The GZWinBMP Draw Hook](reference-sc4-runtime-image-lever.md) — the lever for any bitmap the game supplies at runtime and draws at 1x.
- [cSC4WinMiniMap Terrain Bake](reference-sc4-minimap-bake.md) — the three live minimap instances and the power-of-two blit constraint on the terrain bake.
- [City Situation Indicator Geometry](reference-sc4-csi-indicator.md) — the two quads of the U-Drive-It offer balloon and the inline immediates that size them.

## Engine reference

- [The GZWin Boundary](reference-sc4-ui-sdk-boundary.md) — which on-screen elements a window-layer mod can reach and which are painted beyond it.
- [Where SC4 Parents Its Dialogs](reference-sc4-dialogs-live-under-main-window.md) — the root window ids for modal confirmations, and why a 3D-view traversal misses them.
- [The Region Screen](reference-sc4-region-screen.md) — the decompiled region screen, its precomputed pixel layout, and the levers available on it.
- [The Built-In HTML Text Engine](reference-sc4-html-text-engine.md) — the renderer behind all rich text, and why font mods cannot reach its size tables.
- [Calling Conventions When Detouring SC4](reference-sc4-thiscall-hook-rule.md) — proving convention and arity before a detour, and the two silent corruption modes.
- [Stored Window Pointers Need a Liveness Guard](feedback-liveness-guard-stored-window-pointers.md) — why a cached dialog pointer is valid from the main menu and dangling in a loaded city.
- [State, Derive, Diff, Commit](feedback-state-machine-derive-diff-commit.md) — the architecture for an in-game dialog: one state struct, a pure derive, diff-apply, commit at close.
- [The Display-Enumeration Freeze](feedback-selector-freeze-named-by-instrument.md) — the 3.3 s `EnumDisplaySettingsW` cost through dgVoodoo and the load-time warm-up that hides it.

## Installation, packaging and deployment

- [Scaling Third-Party UI and the Load-Order Law](project-sc4-thirdparty-patches.md) — TGI resolution order across the Plugins tree and what it means for overriding another mod's scripts.
- [SC4 Scans the Plugins Tree Recursively](feedback-sc4-plugins-scan-is-recursive.md) — the two ways to actually take a plugin out of play.
- [Deploying to a Running Game](feedback-sc4-deploy-on-close.md) — copying a new build into an install the game holds open, without killing the process.
- [Controlling Resolution and Renderer](reference-sc4-resolution-control.md) — `SC4GraphicsOptions.ini`, and the gap between the size requested and the size rendered.
- [Windowed Mode and the dgVoodoo Wrapper](reference-sc4-windowed-mode-dgvoodoo.md) — the wrapper settings that override the game's own window-mode request.
- [The Zoomed-In Fault Is DPI Virtualization](reference-sc4-zoom-is-windows-dpi-virtualization.md) — the registry reads that identify a magnified, soft-looking game before any UI analysis.
- [config.bmp Governs Which City Files Survive](feedback-sc4-region-needs-config-bmp.md) — the region tile-grid authority, and how to rebuild it from the coordinates inside surviving savegames.
