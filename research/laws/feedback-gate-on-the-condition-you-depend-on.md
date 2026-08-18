---
name: feedback-gate-on-the-condition-you-depend-on
description: "Attaching a subsystem to a convenient neighbour makes it inherit that neighbour's gate, silently"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-15T14:44:49.781Z
---

SC4 #149, 2026-08-15. The uncovered-icon scan was folded into
`SyncStaticLayers` because that was "already the boot point that decides which
art the game sees". But `SyncStaticLayers` only runs on the **AutoScale** path —
manual tier mode places its packages by hand — so the scan inherited that gate.

With `AutoScale=0`, **a supported user setting**, the scan never ran, the count
came back 0, and stage 2 logged *"nothing uncovered, no work to do."* The entire
cure was off and the log looked healthy.

**Why it is nasty:** a scan that never runs reports zero findings, which is
byte-identical to a clean result. Same shape as
[[feedback-null-is-not-evidence]].

**How to apply:**
- Gate a subsystem on the condition **it** depends on, nothing else. This one
  depended only on `factor > 1`; it never cared how the factor was chosen.
- When adding work to an existing function, ask what that function is gated on
  and whether your work shares that condition. If not, it needs its own entry
  point.
- Suspect this whenever a feature works in the default configuration and
  vanishes in a supported alternative one (manual mode, a flag, a second
  monitor, a clean install).

Two sibling defects surfaced in the same hour, both from assuming the common
case: the deploy **hard-copied** a package that legitimately does not exist on a
clean install, and an integrity gate asserted a **fixed count** of something
that varies per user. See [[feedback-a-package-is-not-done-until-its-in-the-manifest]].
