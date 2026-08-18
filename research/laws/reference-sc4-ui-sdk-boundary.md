---
name: reference-sc4-ui-sdk-boundary
description: SC4 UI scaling — some on-screen elements are NOT drawn by the GZWin UI system and no lever in this project can reach them; the triage test and the two known cases.
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-31T03:14:55.598Z
---

**Not everything on screen is a window.** The whole SC4UIScale toolkit —
window sweep, `.UI` data pass, art overrides, buffer/draw hooks — only reaches
the **cIGZWin / GZWin** UI. Some elements are painted in the **render/present
path** and are unreachable by any of it.

**THE STRUCTURAL FACT (measured 2026-07-30):** *the UI buffer class never
composites to the screen.* With the class-Blt hook armed, EVERY destination was
PANEL-sized — 258x482, 383x156, 360x156, 340x148, 323x156, 317x148, 280x148 —
and **none screen-sized**. So a blit-level hook on our buffer class can never
see a full-screen element, and a zero from one is **structural, not evidence**.

**TRIAGE TEST — apply before spending a session.** If an element
(a) never appears as a window in a FULL-DEPTH dump (test both visibility flips
AND newly-created windows), (b) has no art in any dat, and (c) spans or
overlays the 3D view — **stop, it is outside the SDK.** Write the negatives
down and move on.

**Known outside the boundary:**
- **the paused / sim-speed screen-edge border + corner badge** (task #59,
  SKIPPED): draws in raw screen pixels (~2-3 px frame, ~24 px badge) at every
  tier. Six probes + an offline decode; all evidence saved in
  `SC4TouchControls\_tests\captures\2026-07-30-BORDER-HUNT-README.md`.
- **the region city-select bubble's Mayor Rating bar drawn twice** (task #72):
  A/B proved it is the exe's own painter.

**Only foothold if either is ever resumed:** hook the **DirectDraw primary
surface** `Blt`/`BltFast` — everything visible must pass through it. New
subsystem for this project, runs through dgVoodoo (which the working 2x setup
depends on), so gate it off by default, log-only, with a revert path. Weigh it
against the prize: for #59 that prize is a 2 px line.

Canonical: `SC4-UI-ENGINE.md` §0 "THE BOUNDARY OF THIS SDK".

Related: [[feedback-null-is-not-evidence]], [[reference-sc4-runtime-image-lever]],
[[project-sc4-ui-scaling-northstar]].
