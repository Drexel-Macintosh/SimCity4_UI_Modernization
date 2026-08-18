---
name: reference-sc4-scenario-matrix
description: "SC4 UI scaling: the TEST SCENARIO AXES every fix must be exercised across (scale tier, mod state, game mode, panel lifecycle, render mode, input) — lives in _tests\\SCENARIOS.md. Five bugs in one session were each caused by an untested axis, not bad code. Read with REGRESSION.md, not instead of it."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-29T23:39:12.276Z
---

User standing ask (2026-07-29): *"Everything we build we need to make sure we
can test in various scenarios in the future."* The answer lives in
`_tests\SCENARIOS.md` (SC4TouchControls repo) — written because five bugs in
one session were each caused by an **untested scenario axis**, not by bad code.

**REGRESSION.md = "is it still right?" · SCENARIOS.md = "right under WHAT
CONDITIONS?"** Read both.

**The axes** (each has its own gotchas in the file):
1. **Scale tier** 1x/1.5x/2x/3x — 1x must be TRUE STOCK (DLL fully inert);
   **1.5x is where rounding bugs hide because 2x is exact doubling**; always
   rebuild all three tiers together.
2. **Mod state** — full modded set / one override toggled off / vanilla. The
   LOAD-ORDER LAW lives here, and **when disabling a mod to test, OUR override
   of it must move too** or our copy keeps the mod's layout alive.
   `_tests\Toggle-BuildingStylesUI.ps1` is the pattern to copy.
3. **Game mode** — region / mayor / god pre-founding / god founded (different
   toolbar + pitch!) / sim (deferred). Never gate on a state test not verified
   in all three city states.
4. **Panel lifecycle** — city-load-while-hidden / **FIRST open per city load**
   (where the game BINDS things once) / re-open / compact vs expanded / after a
   city switch (windows are REUSED across cities) / region↔city. First-open
   bugs survive testing precisely because re-open works.
5. **Render mode** — DirectX fullscreen renders at MONITOR NATIVE (the request
   is ignored); windowed and software use the requested size.
6. **Input path** — mouse / frozen touch DLL / synthesized clicks. SC4 POLLS
   the physical cursor for drags and ignores posted messages.

**Environment gotchas that cost real time:** the game runs ELEVATED (a normal
shell cannot kill it; use the wait-for-close deploy loop); OneDrive holds
directory handles so `shutil.rmtree` fails on the rmdir (use a clear-contents
helper) and `find` is glacial (use Glob); `LiveDumpMs` left on wrote ~12 MB per
session; `[Probe]` is live-tunable but `LiveDumpMs` needs a restart; DPROBE
needs `BandL=900` or the news ticker floods it.

Still-missing scenarios are listed as TODOs in the file (vanilla-run toggle,
1.5x/3x eyes-on, stock-parity pixel pass, founded-city vanilla reference).

Related: [[feedback-sc4-scaling-laws]], [[feedback-sc4-regression-net]],
[[feedback-sc4-measure-dont-infer]], [[project-sc4-ui-scaling-northstar]],
[[feedback-sc4-founded-city-invalidates-notes]]
