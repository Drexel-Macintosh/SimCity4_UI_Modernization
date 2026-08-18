---
name: project-sc4-15x-three-open-defects
description: "SC4UIScale 1.5x — the whole eyes-on defect family is CLOSED and user-confirmed (advisors + My Sim included). Carries the closed-form OFFSET-PARITY LAW that predicts which axis breaks on which panel, and the cure that worked."
metadata: 
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-17T01:06:12.212Z
---

**1.5x is user-confirmed CLOSED.** Every defect the first human look at this
tier produced has been fixed and confirmed on screen: flyout thumbnails,
Monthly Budget, menu icons, the reverse L, the CAM "Exported" caption, the
**advisor portraits** (#152) and the **"Select A My Sim" grid** (#153, both
2026-08-13). 2x and 3x were re-tested throughout and 2x served as the
**positive control** — 0 of 262 / 0 of 655 package entries changed.

## ⭐ #176 Mayor Rating bar CLOSED v3.0.1 (2026-08-16, user-confirmed) — THE LATCH LAW

**A latch computed from live geometry is a hidden consumer of that geometry.**
The game's `SetImage` stores a GZWinBMP source rect derived from the window's
size AT BIND TIME; a resize never refreshes it; the fill "healed" only when a
sim rating tick (~once per sim-month) re-ran SetImage. So during PLAY the bar
looked right and during paused defect-hunts it looked broken — at EVERY tier
(2x's old "half bar" was the same latch, 102/204). Neither art nor DLL deltas
were ever the cause; five attributions died because geometry probes read the
WINDOW (correct) while the latch stayed stale. When a widget draws at its old
size after a sweep, ask WHEN its content was BOUND, not what its geometry is.
Cure = RELATCH in ScaleSubtree: rewrite crops matching the latch's own
signature `(0,0,oldW,oldH)`, armed ONLY under kAlwaysScaleCityIds roots
(adversarial review: 577/877 authored .UI crops are full-area-at-origin, so
the signature alone is NOT unique — the staged-script root set is what makes
it safe). cSC4WinTrendBar (polls) is IMMUNE — reads art dims live per draw.
Full mechanism: `_tests\REGRESSION.md` #176 entries, VERSION-HISTORY v3.0.1.

## ⭐ THE OFFSET-PARITY LAW — keep this, it is the general result

> For `f = p/q` in lowest terms, edge-derived rounding preserves a child's 1x
> offset `d` from its frame **iff `q | d`**, because
> `round((t+d)f) - round(tf) == df` exactly when `df` is an integer, and
> otherwise depends on the **parity of the frame's own coordinate `t`**.
> At **f=1.5 (q=2): EVEN offsets always survive, ODD offsets are a lottery.**
> At an integer factor q=1 — which is why 2x and 3x never show this family.

It names the failing AXIS in advance, verified on three panels:
advisor faces (2,1) -> y odd -> "high" · My Sim (3,2) -> x odd -> "left" ·
advisor detail (2,2) -> both even -> correct at every tier.

The same law explains why art and window CANNOT be made the same size at
f=1.5: two windows in one dialog, one at an odd left edge and one at an even
one, scale to 427 and 428 from the same 285. One bitmap cannot be both. See
[[feedback-sc4-scaling-laws]] and #154.

## The cure — SEAT THE CHILD, NEVER NUDGE IT

Both builders gained `seat_faces_on_apertures`: place the child at
`frame + ScaleRound(offset)` instead of at its own independently-rounded edge.
**Translate only** — width and height are never touched, delta capped at 1px,
integer-factor no-op asserted at the call site.

- advisors (`build_selective_safe.py`): 14 windows, anchored on the frame's
  flood-filled art **aperture**, five fatal guards.
- My Sim (`build_dialog_static.py`): 22 windows, 21 move — the selected face
  is already correct and hits delta (0,0), a number hardcoded nowhere, so it
  is independent corroboration.

Rejected on measurement, not taste: an ungated anchored rule moves 456
dashboard windows; `floor()` positions move 373/531 budget+graphs.

**THE LAW THIS COST:** the My Sim fix was reverted once because a guard FATAL'd
with `id 0xAA243E23 occurs 0 times`. That was TRUE; the conclusion "so the
pairing is wrong" was FALSE. The real cause was a `\b` turned into a literal
backspace byte by machine-generating a regex through a string template.
**A guard that fires proves something is wrong; it proves nothing about what.**

See `_tests\REGRESSION.md` #152/#153, shipped in v2.96.0.
