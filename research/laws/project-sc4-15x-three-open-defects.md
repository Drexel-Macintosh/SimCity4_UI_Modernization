# Offset Parity at Fractional Scale Factors

Fractional scale factors produce a defect family that integer factors cannot.
At 2x and 3x every child window lands where arithmetic says it should; at 1.5x
some children drift one pixel off their frame and others do not, and which ones
drift is fully predictable in advance.

## The offset-parity result

For `f = p/q` in lowest terms, edge-derived rounding preserves a child's 1x
offset `d` from its frame **iff `q | d`**, because

```
round((t + d) * f) - round(t * f) == d * f
```

holds exactly when `d * f` is an integer. When `d * f` is not an integer the
difference depends on the **parity of the frame's own coordinate `t`**, so the
same child offset survives under one parent and shifts under another.

At `f = 1.5` (`q = 2`) this reduces to a simple rule: **even offsets always
survive, odd offsets are decided by the parent.** At an integer factor `q = 1`,
so `d * f` is an integer for every `d` and every offset survives, which is why
the family is invisible at 2x and 3x.

The law names the failing **axis** before any measurement. Verified on three
panels:

| Panel | Child offset `(x, y)` | Prediction | Observed |
|---|---|---|---|
| Advisor faces | `(2, 1)` | y odd -> vertical drift | portrait sits high |
| Sim selection grid | `(3, 2)` | x odd -> horizontal drift | face sits left |
| Advisor detail | `(2, 2)` | both even -> clean | correct at every tier |

The same arithmetic explains why art and window **cannot** be made the same
size at `f = 1.5`. Two windows in one dialog that share a 1x width of 285 but
sit at left edges of opposite parity scale to 427 and 428. One bitmap cannot be
both, so no single staged image satisfies both consumers; the geometry has to
be corrected instead of the art.

## The cure: seat the child, never nudge it

Place the child at `frame + ScaleRound(offset)` rather than at its own
independently rounded edge. This makes the child's position a function of the
parent's already-rounded coordinate, which removes the parity dependence
entirely.

Constraints that make the transform safe:

- **Translate only.** Width and height are never touched.
- Delta capped at 1 px — a larger correction means the pairing is wrong, not
  that the rounding is worse.
- Integer-factor no-op asserted at the call site, so 2x and 3x are provably
  untouched.

Implemented as `seat_faces_on_apertures` in both static-dialog builders:

- `build_selective_safe.py` — 14 advisor windows, anchored on the frame's
  flood-filled art **aperture**, with five fatal guards on the pairing.
- `build_dialog_static.py` — 22 sim-selection windows, 21 of which move. The
  already-selected face computes a delta of `(0, 0)`; that zero is hardcoded
  nowhere, so it is independent corroboration that the anchor is right.

Two broader variants were rejected on measurement rather than taste: an ungated
anchored rule moves 456 dashboard windows, and `floor()` positioning moves
373 of 531 budget and graph windows. Scope the rule to the panels whose
children are actually frame-relative.

## The bind-time latch law

**A latch computed from live geometry is a hidden consumer of that geometry.**

The engine's `SetImage` stores a `GZWinBMP` source rectangle derived from the
window's size **at bind time**. A later resize updates the window and never
refreshes the stored rect, so the widget keeps drawing through a crop sized for
its old self. Symptoms are intermittent in a way that defeats normal
attribution: a rating bar looked correct during play, because a periodic data
tick re-ran `SetImage` at the new size, and looked broken during paused
inspection. It reproduced at every tier, not only at fractional ones.

Consequences for diagnosis:

- When a widget draws at its old size after a sweep, ask **when its content was
  bound**, not what its geometry currently is. Geometry probes read the window,
  which is correct, and stay blind to the stale latch.
- Widgets that read art dimensions live on every draw are immune. A trend-bar
  class that polls its source each frame never exhibits the defect.

Cure: re-latch during the subtree scale pass by rewriting crops that match the
latch's own signature `(0, 0, oldW, oldH)`. The signature alone is **not**
unique — 577 of 877 authored `.UI` crops are full-area-at-origin — so the
rewrite must be armed only under a known root set (the staged-script roots),
which is what keeps it from touching authored full-area crops elsewhere.

## A guard that fires proves something is wrong; it proves nothing about what

A pairing guard once failed with `id 0xAA243E23 occurs 0 times`. The message
was true and the inferred conclusion — that the child-to-frame pairing was
wrong — was false. The real cause was a `\b` word boundary turned into a
literal backspace byte by generating the regex through a string template, so
the search could never match. Treat a guard failure as evidence that the run is
invalid, then find the cause independently; do not let the guard's wording
choose the hypothesis.
