---
name: feedback-sc4-prescale-while-hidden
description: SC4 UI scaling — kill an open-FLASH by PRE-SCALING the window while it is still HIDDEN (gate only the dock MOVE on visibility); never suppress paints. Plus the dialog rule — static-dat dialogs inside the swept tree need their root in kNeverScaleIds
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-29T00:29:13.041Z
---

**Two rules that closed the "menu flashes stock/garbled before it resizes" class
of bug (SC4 UI scaling, 2026-07-28, v2.11.28/29).**

## 1. Pre-scale while HIDDEN — never suppress paints

If a window is only scaled once `IsVisible()` is true, the game gets to paint
one stock (or half-transformed) frame first — **that frame IS the flash.** The
fix is to scale it *before it is ever shown*:

- run the subtree scale **unconditionally** (hidden windows included), and
- gate **only the reposition/dock MOVE** on visibility (docking a *closed*
  flyout can land it on top of another one — that constraint is real).
- `ScaleSubtree` is idempotent via `scaleMap`, so hidden pre-scaling is a
  one-time cost.

**The user pointed out this was already solved once on the REGION screen** —
`IsRegionPanelId` is a deliberate exception to the sweep's skip-invisible rule,
commented "pre-scaled while hidden so they appear already at 2x (no visible jump
when a flyout opens)". The god flyouts simply never got that treatment. **When a
UI bug feels new, check whether the region-screen pass already solved it.**

**WHAT NOT TO DO (cost a broken HUD):** a "FlashGuard" that suppressed Plot for
any descendant of the god-flyout parent until the sweep marked it ready. That
parent is an ancestor of far more than the flyouts, so unrelated HUD windows
(bottom-left date / City Name panel) went unpainted — black box, missing art —
and it never fixed the flash anyway. Blanking windows at paint time is the wrong
layer. Kept in-tree disabled (`FlashGuard=0`) as the record.

## 2. Static-dat dialogs inside the swept tree need BOTH halves

A popup fixed by the DialogStatic dat that ALSO lives inside the DLL's swept
tree must have its root id added to `kNeverScaleIds` in UiSpike.cpp:
- **static only** -> the sweep double-scales it (~4x; log showed
  `868x468 -> 1736x936`),
- **DLL only** -> right SIZE but the `GZWinText` nodes render the wrong colour
  (purple) while TextEdit/button captions stay black,
- **both** -> correct (proven on Establish City, root `0x6A414973`, script
  `I-2a41436b`).

Diagnostic that settles which case you are in: **if the popup already renders
LARGER than stock before you touch the dat, the DLL owns it.** Main-window-child
confirms (query panels, the can't-save-during-disaster box) are outside the
sweep and need the dat only.

Constraint that frames all of this: every fix must ship from the **Plugins
folder** (DLL + ini + dats). Never modify `SimCity 4.exe` — runtime byte patches
are in-memory only.

Related: [[project-sc4-god-flyouts]], [[project-sc4-ui-scaling-northstar]],
[[reference-sc4-flyout-hittest-playbook]], [[feedback-sc4-regression-net]]
