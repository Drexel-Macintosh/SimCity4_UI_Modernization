---
name: feedback-simulate-the-consumer-not-the-build
description: A build reporting its own success is not evidence - model what the CONSUMER does and measure the shipped artefact
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-15T13:47:01.841Z
---

**SIX CONSECUTIVE "FIXED" CLAIMS WERE WRONG ON SCREEN** (SC4 #149, 2026-08-15).
Every one described what the BUILD did — "realigned", "residual [0,0,0,0]",
"packed 528x132", "registered=2". None described what the GAME WOULD DRAW.

The deadlock broke in one command, when a simulator reproduced the engine's own
crop (`SRC = state*stride, +stride`) and measured the DEPLOYED file. It found
the defect on its first run and kept finding the next one each round.

**Why:** A generator graded by its own restatement of its own intent will pass
while the screen disagrees. Two "aligned" metrics existed and disagreed —
mine said `[0,0,0,0]`, the consumer model said `[0,0,-1,-1]` — on the same file.

**How to apply:**
- Before claiming a fix, MODEL THE CONSUMER and run it against the SHIPPED
  artefact, not the build directory or an intermediate.
- Make the solver optimise the SAME function the gate asserts. One definition
  of correct, end to end.
- **The tell: a green instrument that does not move the screen means the
  instrument is on the wrong channel.** Next action is to prove the probe CAN
  see the subject — never to believe it.
- Keep the broken input as a POSITIVE CONTROL that must still fail; a gate
  where nothing can fail is not a gate.

See [[feedback-instrument-scoped-to-the-wrong-channel]],
[[feedback-null-is-not-evidence]], [[feedback-thresholds-come-from-controls]].
