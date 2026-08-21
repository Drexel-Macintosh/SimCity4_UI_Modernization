# One Path Owns the Scale Factor

Every scaled element must end up **exactly `factor × its 1x size`**. 1.5x means
1.5x, 2x means 2x. Not "close", not "looks right", not "big enough to read".

## The failure this rule prevents

Scaling defects attract compensating hacks, and a compensated element passes
every eyeball check while being wrong by an unknown amount.

The U-Drive-It offer balloon is the worked example. Its art is **pinned at 96px
— the 3x design size — in every tier package**, while the inline `.text`
immediates that size the same balloon **scale with the tier**. The on-screen
result is `art × immediate`: neither number alone is the factor, and the drawn
size is whatever the product happens to be.

The pin was introduced to cancel a multiplier already present in the draw path
(letting the draw path scale unmodified predicts roughly 8x geometry at the 2x
tier). That is not a scale rule. **A pin, clamp, or fudge factor whose only job
is to cancel another number is two errors arranged to look like none**, and it
comes apart the moment either side moves — a new tier, a package rebuild, or a
change to the draw path.

## How to apply it

- When something is the wrong size, find **which path owns the scale** — the
  data/package pre-scale, the runtime sweep, or a code immediate — and make
  **one** path own it. Never add a second compensating constant.
- Treat a pin or clamp as a signal that the real multiplier was never located.
  Go find the multiplier. The related principle: a patch that cannot express
  its value must refuse or widen, never silently truncate — and the same
  instinct applies to silently compensating.
- Acceptance is **measured against a 1x reference**, never eyeballed. Capture
  the stock element (`Set-StockCompare.ps1 -Mode Stock`, which verifies the
  install is actually stock before capturing) and compare the same element at
  the scaled tier.
- Beware **multi-quad elements**. The U-Drive-It balloon is a pin quad and an
  icon quad sized by separate inline immediates, and the icon's number is also
  its click box. "Exactly the factor" has to hold for every quad independently,
  or the halves separate on screen and the hit region stops matching the art.

## Diagnostic question

For any element that is the wrong size, ask: *how many numbers multiply into
the drawn size?* If the answer is more than one, the scale factor has no single
owner and the element is un-auditable until it does.
