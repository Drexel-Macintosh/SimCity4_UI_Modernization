---
name: project-sc4-dataviews-legend
description: "SC4 UI scaling — the Data Views legend jump is fixed in v2.37.0 by scaling the ORIGIN constants inside the game's own re-lay; the pitch is measured per row and must never be patched or written from a table."
metadata: 
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-31T14:43:40.251Z
---

**v2.37.0-dvorigin, shipped + USER-CONFIRMED 2026-07-31** (`8 of 8 sites`,
`DVPIN` 0 from a 198 baseline, two non-uniform legends preserved). The Data Views
legend jumped on every view switch. `sub_007A04F0` (`__thiscall`, `ret 4`,
arg = data-view id) re-lays it on each selection and is provably the ONE
choke point — the ids `0x8A909E00`/`0x8A909E10` appear at exactly 4 addresses
in the whole 7.87 MB image, all inside it. Cure = ENGINE §4.7 **row 3**: scale
its four origin constants (8 sites — each origin appears TWICE, the L/T write
and the `add`/`lea` computing R/B from `GetW()/GetH()`).

**THE LAW THIS TAUGHT — scale the ORIGIN, never the STEP.** The routine does
`edi += 18*ceil(h/18)` where `h` is the *measured* text height, so the pitch
already self-scales (36 at 2x). Two consequences:
1. patching the pitch would double-scale it;
2. a label that wraps to two lines gets a **72px slot**, so any correction that
   writes a *uniform table* flattens it. Measured: a nine-row view laid out
   `24,60,96,132,168,240,276,312,348` had eight windows dragged up 36px by our
   own `kDVPins` table — a persistent wrong layout, not a one-frame artifact.
   Fixing the origin fixes both, because the game's own deltas survive.

**A reactive pin can be worse than late — it can be WRONG.** `DVPIN` had been
purely reactive since v2.21.3, and `REGRESSION.md` + `RUN-SHEET §1.8` had
recorded its burst (`"a burst of DVPIN lines then silence"`) as the **PASS**
criterion. It was the defect. **An acceptance test that never looks at the
transient frame cannot see a transient defect** — both entries are rewritten.

**Instrument:** `DVLEG born=/rows=/chips=/rowY=[...]` is the positive control
for "zero DVPIN lines", which alone proves nothing (see
[[feedback-null-is-not-evidence]]). Escape hatch `[UiSpike]
DataViewLegendPatch=0` + restart.

Canonical: `_tests\REGRESSION.md` "DATA VIEWS LEGEND BORN CORRECT";
`SC4-UI-ENGINE.md` §4.7 (row 3 + the re-lay note).

Related: [[project-sc4-flash-subflyouts]], [[feedback-sc4-scaling-laws]],
[[feedback-sc4-measure-dont-infer]], [[project-sc4-ui-scaling-northstar]].
