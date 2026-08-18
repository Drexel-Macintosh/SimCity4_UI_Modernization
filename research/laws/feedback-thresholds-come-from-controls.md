---
name: feedback-thresholds-come-from-controls
description: Never invent a threshold or pick a metric without measuring the known-good population first
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-15T13:47:15.015Z
---

SC4 #149, 2026-08-15 — three numbers were guessed and **all three were wrong**,
each costing a launch:

| guessed | truth, from measuring the known-good set |
|---|---|
| hover border >= 90% of perimeter | every correct icon measures **81.8%** — 90% fails all 450 |
| state 2 is hover | **state 3** is; state 2 is never drawn at all |
| hover = 1.4x brightness | it is a white BORDER; the luminance rise was the border's own pixels moving the mean |

Each was answered in ONE command by measuring the population that is already
correct on screen — 450 covered icons sitting right there on disk.

**Also: choose the STATISTIC from what varies.** Alignment was first measured
with SSE on column luminance, but the four states of a button strip differ BY
DESIGN in luminance, so the metric bought a brightness match with a wrong lag
and was confidently wrong twice. Correlating the GRADIENT — blind to a constant
brightness offset — got it right immediately.

**How to apply:**
- Before asserting a threshold, measure the known-good population and take the
  number from it. `min / median / p90` also tells you if the metric is stable.
- A metric sensitive to the thing that differs between your samples cannot
  measure anything else about them.
- A fixed search range is a SILENT CLAMP: it reported `[0,3,9,9]` for a 12px
  drift at span 10, which then failed a linearity guard. Scale the range with
  what is being measured.
- When a gate fires on your output, FIRST run it on the known-good set. If they
  fail too, the gate is wrong — not the output. (State-3 "drift" fired on 92%
  of correct icons.)

See [[feedback-simulate-the-consumer-not-the-build]],
[[feedback-null-is-not-evidence]], [[feedback-static-defect-is-a-hypothesis]].
