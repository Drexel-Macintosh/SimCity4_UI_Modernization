# Code-created windows + non-city screens + caps — digest (2026-07-29 night)

Transcribed by main session (read-only agent). Full report in agent transcript.

## Code-created windows (no .UI anywhere)
- ⛔ REFUTED (2026-08-03 12:00, `coverage-matrix.md` §0.3): ~~0x2BA6BB97
  cSC4WinRegionView = THE REGION MAP, full-screen, 0 children — ALL tile
  labels/icons code-painted inside it. Untouched by design (9/10 gate).~~
  The `children=0` reading was a **STATE observation, not a structural
  fact**, and it was written up as "proven structurally unreachable".
  MEASURED: 13 descendants print at `snapshot.log:151-165` the moment a
  city tile is clicked. The window is **COVERED** — dialog-static on both
  bubble scripts, #72 user-confirmed. This is the project's own NULL IS NOT
  EVIDENCE rule: the probe never established it *could* have seen a child.
  Still UNDETERMINED, and unaffected by the refutation: do 2x fonts render
  the code-painted region tile labels coherently? → needs one 2400x1600
  region screenshot vs 1x.
- 0x00000043 Restore-Toolbars btn: pos(12,1572) size 42x38 → bottom 1610 >
  1600 ⇒ SUSPECTED ~10px clip. The 42x38 came from 2x art auto-sizing, no
  re-anchor ever ran. Verify: hide toolbars, screenshot.
- 0x42B7C351/54/55 scrollbar widget inside Data Views' Map View: frame swept
  to 1076x94 but its 24x25 buttons stay 1x, art has ZERO coverage.
  UNDETERMINED if reachable.
- ⛔ REFUTED (2026-08-01 intake for #90/#58): ~~Building-Styles mod: runtime
  tree has ~20 ids NOT in the shipped mod script (0x2BC619F1 etc.)~~ — the
  claim was an artifact of diffing against the STOCK script (the exact #44
  error). Measured: the exemplar 0x2BC619F1 IS in the shipped mod script
  (`thirdparty-ui/...I-6bc61f19.ui:57`), and both golden dumps diff to **0
  ids absent** (73 runtime windows == 73 script nodes). #58 therefore has NO
  standing mechanism — it starts measure-first, and only on v2.42.0+
  captures (v2.42.0 changed the panel's birth timing via
  kAlwaysScaleCityIds).
- 0x6A0AF41D (region, full-screen) and 0x4C30E4FA (6 instances 136x100,
  always vis=0): ZERO repo references — DPROBE to name them.
- GZWinListBox rows are code-sized from the FONT (no row-height attr) →
  2x FontStyle covers them automatically. GZWinGrid rows = drowheight (handled).

## Non-city screens
- REGION: all 9 panels covered (kRegionPanelIds = exactly the 9 non-full-
  screen children). Rest = full-screen layers, skipped by design.
- ⚠ LIVE TRAP: DockDialogs=1 would 4x the six region dialogs (runtime dock
  table + dialog-static now overlap on the SAME six). Keep DockDialogs=0 or
  remove one mechanism first.
- SPLASH: covered statically; never observed in tree (lives pre-tick).
- CITY LOADING/SAVING screen: NO .UI exists — 100% code-painted, untouched,
  full-screen so cosmetically fine at 1x proportions.
- Establish/Create/Import flows: all covered; Establish City correctly
  double-listed (static + kNeverScaleIds).
- 800x600 / G-08000600: provably irrelevant (tier 1 = DLL fully inert).

## Cap headroom
- ⚠ ChildSnapshot wins[96]: TIGHTEST — Taxes popup uses 76 (79%), and four
  installed ordinance/budget mods ADD ROWS to that exact family. On overflow:
  silent partial scale + verify-pass sees omitted children as DEAD.
  FIX QUEUED: raise to 256 + one-shot log (mirror PANELCAP).
- ⚠ gFgVt[kFgMax=6]: FULL (idx 0-5), idx 5 wasted on tip-layer class via
  blanket arming at :5505. Inert only while FlashGuard=0. Fix when touched.
- gReadyWins[16] / gFgWaitRoot[4] (5th root COLLIDES into slot 0): no logs,
  uninstrumented; FlashGuard-gated.
- panels[128]: 43/128 used — safe. kMaxWindows 1500: 866 max seen — safe.
- kMaxDepth 8: max observed 7 (proof: no depth-8 dump lines exist) — 1 level
  headroom, not self-concealing.
