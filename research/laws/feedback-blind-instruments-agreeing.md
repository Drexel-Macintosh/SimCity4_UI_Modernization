---
name: feedback-blind-instruments-agreeing
description: "Two instruments returning the same null is NOT corroboration unless their failure modes are independent — two structural nulls agreeing sent an SC4 defect to the \"unfixable\" pile for a day."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-31T15:42:52.820Z
---

**Earned 2026-07-31 (SC4 region rating bar, task #72).** A defect was filed as
*"not ours — outside the SDK, the exe's own painter"* on two pieces of evidence
that **agreed with each other and were both worthless**:

1. a tree dump showed **no window** where the bar renders — but the dumper
   stops one level above it, and our own law 20 had **already written down that
   this exact bar was skipped**;
2. an A/B toggling the rating-arrow patch changed nothing — but that patch
   drives a *different subsystem* the bar never touches.

Two structural nulls. Their agreement *felt* like corroboration. It was one
piece of non-evidence counted twice, and it cost a day plus a wrong row in our
own SDK's boundary table. The real fix was **one missing art asset** — the
class computes its SOURCE rect from the WINDOW width, so under-sized art tiles
instead of shrinking.

**THE RULE: corroboration only counts between instruments with INDEPENDENT
failure modes.** State the positive control for each null *separately* — what
would this instrument have printed, and has it ever printed it? If you cannot
answer that for both, you have one piece of evidence, not two.

**Two smells that should have triggered it earlier:**
- the user said *"we've fixed this countless times"* — when a defect's symptom
  matches a solved family but the diagnosis says "unreachable", **suspect the
  diagnosis, not the family**;
- an "unfixable" verdict resting entirely on nulls is a verdict resting on
  nothing. A positive finding can be wrong; a null can be *empty*.

Sibling: [[feedback-null-is-not-evidence]] (the single-instrument form).
Related: [[reference-sc4-ui-sdk-boundary]] (the table this corrected),
[[feedback-sc4-measure-dont-infer]], [[feedback-docs-are-the-sdk]].
