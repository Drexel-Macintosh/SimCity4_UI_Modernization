---
name: project-sc4touchcontrols-independence
description: "SC4TouchControls — the quarantine was LIFTED by the user on 2026-08-09 and the DLL is back in Plugins. It is now a LIVE VARIABLE in every SC4 UI-scaling observation, because it is the one component never made independent of UI scaling. Ask \"is touch loaded?\" during scaling triage."
metadata: 
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-14T15:57:45.190Z
---

⚠ **RE-QUARANTINED 2026-08-13 — supersedes the 08-09 lift.** As of 13-Aug 14:21
`SC4TouchControls.dll` is back OUT of `Plugins\` and sits in
`Documents\SimCity 4\_touch-QUARANTINE-do-not-reinstall\` again (dll+ini+log).
The user's stated reason (14-Aug): *"There are issues in this Plugin so we've
isolated it as the other coding models were not smart enough to solve it."*
So touch is currently NOT a live variable in scaling observations — but
**verify the folder before assuming either way; this flag has flipped twice.**
Do not reinstall it into `Plugins\` without asking.

(Historical: quarantine was LIFTED 2026-08-09 by user order and the DLL ran in
`Plugins\` until 13-Aug. `_tests\Test-DatIntegrity.ps1` reports its presence
rather than gating on it — a red line for a file this project does not own is
the "trained to ignore a failure" problem.)

`_tests\Test-DatIntegrity.ps1` no longer fails on its presence — the absence
assertion was retired **in the same change as the reinstall**, which is what
that file's own comment demanded. It is **reported, not gated**: a red line for
a file this project does not own is the "trained to ignore a failure" problem.

⛔ **WHAT THIS COSTS.** SC4TouchControls was quarantined because it was never
rebuilt independent of UI scaling, and its ini still carries dead pre-split
scaling keys the touch-only DLL never reads (see [[feedback-sc4-scaling-laws]]
law 50). It is therefore **a live variable in every UI-scaling observation**.

**Put "is touch loaded?" on the scaling triage list.** When a scaling defect is
reported and the cause is not immediately obvious, its mod state is an axis —
[[reference-sc4-scenario-matrix]] AXIS 2. Do not silently assume a clean
measurement environment the way this project could before 2026-08-09.

The original independence work ([[project-sc4-touch-controls]], task #133)
remains **unfinished** — the rebuild never happened; the quarantine was simply
lifted. If touch is ever implicated in a scaling defect, that task is the fix,
not another workaround.
