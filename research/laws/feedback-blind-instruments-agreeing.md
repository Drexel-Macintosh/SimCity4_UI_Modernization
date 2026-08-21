# Corroboration Requires Independent Failure Modes

Two instruments returning the same null corroborate each other only if their
failure modes are independent. When both are structurally incapable of seeing
the thing, their agreement is one non-fact counted twice — and it reads exactly
like confirmation.

## The shape of the mistake

The region rating bar was filed as unreachable — "outside the UI SDK, painted by
the exe itself" — on two pieces of evidence that agreed with each other and were
both empty:

1. A window-tree dump showed no window where the bar renders. The dumper stops
   one level above that bar; its inability to reach that depth was already
   documented, so the null was guaranteed before the probe ran.
2. Toggling the rating-arrow patch on and off changed nothing on screen. That
   patch drives a different subsystem, which the bar never touches, so the A/B
   could not have moved regardless of the diagnosis.

Neither instrument had a path to a positive result. The verdict that followed —
a wrong row in the UI SDK boundary table marking a reachable element as
renderer-owned — rested on nothing.

The bar was reachable the whole time. The actual defect was a single missing art
asset: the class computes its **source rect from the window width**, so art that
is smaller than the (scaled) window tiles instead of shrinking to fit. Supplying
correctly sized art fixes it; no engine patch is involved.

## The rule

State the positive control for each null separately, before treating two nulls
as one finding:

- What would this instrument have printed if the thing were present?
- Has it ever printed that, in any known-good case?

If both questions cannot be answered for both instruments, there is one piece of
evidence, not two. A positive finding can be wrong; a null can be simply empty,
and an empty null propagates into permanent conclusions because nothing later
contradicts it.

Two accompanying smells are worth acting on directly:

- When a defect's symptom matches a family of already-solved defects but the
  diagnosis says "unreachable", suspect the diagnosis rather than the family.
- An "unfixable" verdict resting entirely on nulls is a verdict resting on
  nothing. Unreachability is a positive claim and needs positive evidence — a
  live dump proving the element has no window at any depth, or a patch that
  provably executes and moves zero pixels.

This is the multi-instrument form of the single-instrument rule that a probe
finding nothing is not a fact until it is shown the probe could have seen the
thing.
