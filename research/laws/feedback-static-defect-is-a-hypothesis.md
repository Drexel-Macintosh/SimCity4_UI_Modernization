---
name: feedback-static-defect-is-a-hypothesis
description: "A defect found only in STATIC DATA is a hypothesis until something ON SCREEN disagrees - shipping one broke the user's UI (SC4 #98)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-03T18:21:53.821Z
---

**A defect found only in STATIC DATA is a HYPOTHESIS until something ON SCREEN
disagrees.** Do not fix it. Get an eyes-on symptom first, or prove the runtime
is not already handling it.

**The incident (SC4 #98, 2026-08-03).** A static census said the Trip Types
legend root shipped "2x art in a 1x box", and printed a positive control for
four absences (SCALED_WINDOW_IDS, kNeverScaleIds, kDataScaledSubtreeIds,
dialog-static) - so the null looked MEASURED. I shipped the data fix. It broke
the user's UI: the legend rendered at 4x. The runtime was ALREADY scaling those
windows via a FIFTH list the census never checked (kRegionPanelIds), proven
afterwards by one grep of the live log:
`panel 0x0BB0F5E7 (152x203) -> (304x406)`. The user had never reported the
legend as wrong, because it never was.

**Why the offline gate did not save me.** The adjudicator I built checked the
data against ITSELF (area == imagerect, pitch >= art height) and passed at all
three tiers. A gate that measures data against itself cannot detect "the data
was already fine". It proves internal consistency, never necessity.

**The three rules that follow:**
1. A null is only MEASURED if the positive control covers EVERY path. Four of
   five lists is a structural null wearing a measurement's clothes.
2. Before any data-side scaling fix, `grep` the live log for the window id.
   If the runtime already moved it, a data fix DOUBLES it.
3. "Absent from every id list" proves nothing either - the sweep is
   STRUCTURAL (tree-walking), so windows get scaled with no id anywhere.

**The counter-example that shows the good path (SC4 #101, same day).** The 1.5x
dashboard bug started from a SCREENSHOT, was traced to a measured shear
(-256px), was checked against a stock control, and its fix was replay-verified
as a no-op at the working tier before shipping. Same rigour, opposite outcome,
because the evidence started on screen.

See [[feedback-null-is-not-evidence]], [[feedback-sc4-scaling-laws]],
[[feedback-check-our-previous-work-first]], [[feedback-blind-instruments-agreeing]].
