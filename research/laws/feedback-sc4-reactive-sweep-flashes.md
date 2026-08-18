---
name: feedback-sc4-reactive-sweep-flashes
description: "SC4 UI scaling: the 1x FLASH at every mode transition is ARCHITECTURAL, not a panel bug — the sweep is reactive (4x/sec) and swept panels are born 1x, so flashes scale WITH coverage. Fix the TIMING (scale at birth: data pre-scale / pre-scale-while-hidden / a post-construction hook), never suppress paints."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-30T01:47:58.330Z
---

Raised by the user 2026-07-29 as **"our biggest issue"**: god mode, mayor
mode and My Sims all flash the unscaled 1x menus for a split second before
snapping to the scaled version.

**WHY IT IS STRUCTURAL.** The runtime scaler is REACTIVE — it sweeps the
cIGZWin tree ~4x/sec off a 16ms subclass timer — and swept panels are
deliberately **born 1x**: the selective-safe builder edits art and
`imagerect` only, never `area=`, so shipped geometry stays stock. Every mode
switch constructs or re-imposes those windows, so 1x paints in the 0-250ms
before the next tick. Nothing is wrong per panel; the TIMING is the defect.
**Corollary that makes this urgent: the flash count grows with coverage** —
each newly scaled panel adds a transition that can flash, which is why it
reads as universal once most of the UI is covered.

**THE CURE IS ALWAYS "BORN 2x", NEVER "HIDE THE PAINT".**
Two proven per-window mechanisms, both of which deleted a half-working
runtime hack when they landed:
- **DATA pre-scale** — ship the subtree pre-scaled in the `.UI`
  (`double_subtree_areas` + root-only `kDataScaledSubtreeIds`). Cured the
  advisor strip's quarter-zoomed faces with zero flash.
- **PRE-SCALE WHILE HIDDEN** — `kAlwaysScaleCityIds`: scale before the
  window is ever shown (region flyouts, news reader, budget popups).
The general fix is to generalise that timing into a **scale-at-birth hook**
(post-construction of the .UI tree, the mode-switch instantiation path, or
the visibility setter vt+0x10C). See `_tests\REGRESSION.md` → "SYSTEMIC #1"
for the ranked disasm targets, and task #50.

**PERMANENTLY REJECTED: paint suppression.** A `FlashGuard` that skipped
paints blanked HUD windows outright. It stays at 0 forever. Also never call
Plot or any draw entry point from a hook — `InvalidateSelf` is the safe
"mark dirty" primitive. And a birth-scaled window WILL be revisited by the
sweep, so idempotency (`scaleMap` recognising its own work) is mandatory or
you get 4x.

Related: [[feedback-sc4-prescale-while-hidden]], [[feedback-sc4-scaling-laws]],
[[reference-sc4-scenario-matrix]], [[project-sc4-ui-scaling-northstar]]
