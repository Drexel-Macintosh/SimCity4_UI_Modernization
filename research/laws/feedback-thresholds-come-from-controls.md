# Take Thresholds From the Known-Good Set

A threshold that is reasoned about rather than measured is a guess wearing a
number. Before asserting any cutoff — a percentage, a state index, a brightness
ratio — measure the population that is already correct on screen and take the
number from it. That population exists: the shipped art, the untouched icons,
the widgets nobody has complained about. It is on disk, and one command reads
it.

## Three guessed numbers, three wrong

A single icon-hover investigation produced three inferred constants, each of
which cost a launch before measurement replaced it. All three were answerable in
one command against a known-good set of 450 covered icons.

| Guessed | Measured truth |
|---|---|
| Hover border covers >= 90% of the icon perimeter | Every correct icon measures **81.8%**. A 90% gate fails all 450. |
| State 2 is the hover state | **State 3** is the hover state. State 2 is never drawn at all. |
| Hover is a 1.4x brightness rise | Hover is a **white border**. The luminance rise was the border's own pixels dragging the mean. |

These are durable facts about the button-strip art: hover is state 3, hover is
drawn as a white border occupying 81.8% of the perimeter, and state 2 is dead.

## Choose the statistic from what varies

A metric that is sensitive to the property which differs between samples cannot
measure anything else about them.

Strip alignment was first measured as sum-of-squared-error over column
luminance. The four states of a button strip differ in luminance *by design*, so
that metric bought a brightness match at the cost of a wrong lag — and was
confidently wrong twice. Correlating the **gradient** instead, which is blind to
a constant brightness offset, produced the correct lag immediately.

Pick the statistic that is invariant to the intended difference and sensitive to
the defect being hunted.

## A fixed search range is a silent clamp

A correlation or offset search bounded by a hard-coded range does not report
"out of range" — it reports the edge of the range as if it were the answer. A
search capped at span 10 returned `[0, 3, 9, 9]` for a genuine 12px drift, and
those clamped nines then failed a downstream linearity guard, sending the
investigation after a nonexistent nonlinearity.

Scale the search range with the quantity being measured, and treat any result
sitting exactly on a boundary as suspect rather than as data.

## When a gate fires, run it on the known-good set first

If a new gate rejects new output, the gate is on trial alongside the output. Run
it against the population that is known correct before believing it. A state-3
"drift" check fired on 92% of already-correct icons — the gate was wrong, not
the art.

A gate that would condemn the shipped, working set is broken by definition.

## Applying it

- Take thresholds from measurement of the correct population, not from
  reasoning about what the value ought to be.
- Report `min / median / p90` alongside the chosen threshold; the spread shows
  whether the metric is stable enough to gate on at all.
- Verify the metric is insensitive to the designed-in variation between samples.
- Scale every search window with its input, and distrust results pinned to a
  window edge.
- Validate every new gate against known-good inputs before applying it to new
  ones.
