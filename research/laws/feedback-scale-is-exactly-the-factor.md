---
name: feedback-scale-is-exactly-the-factor
description: "USER RULE (SC4UIScale, 2026-08-18): every scaled element must end up EXACTLY factor x its 1x size — 1.5x means 1.5x, 2x means 2x. Compensating pins and workaround multipliers that make the product something else are wrong even when they look fine."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-19T01:00:58.764Z
---

**USER, 2026-08-18:** *"I think we overdid it with scaling on our UDriveIt
buttons. They should really scale directly with the rest of the UI. so 1.5X
should truly just be 1.5X, 2X=2X etc."*

The rule is the whole UI, not just that one family: **the drawn size must equal
`factor × the 1x size`, exactly.** Not "close", not "looks right", not "big
enough to read".

**Why:** the project had accumulated compensating hacks. The U-Drive-It bubble
art is PINNED at 96px = 3x design in *every* tier package (#100), while the
inline `.text` immediates that size the same balloon scale *with the tier*. The
on-screen result is `art × immediate`, so neither number alone is the factor and
the product is whatever falls out. #100 chose the pin to work around a
MULTIPLIER in the draw path ("flipping the flag alone predicts 8x at the 2x
tier"). A workaround that cancels an unknown multiplier is not a scale rule — it
is two errors arranged to look like none, and it breaks the moment either side
moves.

**How to apply:**
* When something is the wrong size, find **which path owns the scale** and make
  ONE path own it. Do not add a second compensating constant.
* A pin, clamp or fudge factor that exists to cancel another number is a signal
  the real multiplier was never found — go find it ([[feedback-sc4-scaling-laws]]
  law 108: a patch that cannot express its value must refuse or widen, never
  silently truncate; the same instinct applies to silently compensating).
* Acceptance is MEASURED against a 1x reference, never eyeballed — capture stock
  with `Set-StockCompare.ps1 -Mode Stock` (which since 2026-08-18 verifies it is
  actually stock) and compare the same element.
* Beware two-quad elements: the CSI/deployment balloon is pin + icon sized by
  separate immediates, and the icon's number is also its click box
  ([[reference-sc4-csi-indicator]]) — so "exactly the factor" has to hold for
  both quads or the halves come apart ([[project-sc4-15x-three-open-defects]]).

Related: [[feedback-sc4-measure-dont-infer]],
[[feedback-simulate-the-consumer-not-the-build]], [[feedback-sc4-scaling-laws]].
