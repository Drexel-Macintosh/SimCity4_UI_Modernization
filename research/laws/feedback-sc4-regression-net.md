---
name: sc4-regression-net
description: "STANDING ORDER for the SC4 UI-scaling project: maintain regression tests + durable reference points (compaction-proof); this is a major project going to completion, and launch must be flawless"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-22T05:54:28.803Z
---

User directive (2026-07-22, verbatim intent): "We're doing a fairly big lift here so I
want to make sure you start developing regression tests / create reference points for
when you compact the conversations etc. Treat this as a major project that we're going
to see to completion no matter the amount of time it takes us. But when we get near the
end we want to make sure what we launch is flawless."

**Why:** conversation compaction loses working context; the project's truth must live in
the repo, executable, so ANY future session can re-verify the whole stack without chat
history. Launch bar = flawless.

**How to apply:**
- The regression net lives in `SC4TouchControls\_tests\` (durable, excluded from
  shipping bundles per the deployment convention; NEVER in the session scratchpad).
- Core suites: `Test-ScaleTierDecide.ps1` (offline fit-function assertions),
  `Test-DatIntegrity.ps1` (package entry counts + hashes), `Test-BootMatrix.ps1`
  (live boot cycles per resolution asserting tier decisions, layer gating on disk,
  and 9/9 region panels at scaled tiers; restores native at the end).
- Golden references in `_tests\golden\`: blessed captures + logs with a MANIFEST.md
  saying what each proves and its hash. Add a new golden whenever a milestone is
  user-accepted; never overwrite a golden silently.
- `_tests\REGRESSION.md` is the runbook: how to run everything, what PASS looks
  like, current expected values (dat entry counts, tier table). UPDATE IT whenever
  packages/tiers change - stale expected values are the failure mode.
- Run the full suite before ANY deploy the user will test, and after structural
  changes (new packages, tier logic, DLL splits). Log-based assertions work even
  when the screen is locked; captures are best-effort extras.
- Every session that materially changes the stack ends by updating the northstar
  memory checkpoint AND the runbook's expected values - those two are the
  compaction-proof reference points.
