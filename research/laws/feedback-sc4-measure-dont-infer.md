---
name: feedback-sc4-measure-dont-infer
description: "SC4 UI scaling: EVERY value that was measured landed first try; every value inferred from a screenshot cost 2-3 builds and twice broke working features. Build the instrument, read the number. Also: if two symptoms contradict, you are at the wrong LAYER — move up one."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-31T02:31:37.575Z
---

The clearest pattern across the whole Mayor-mode phase (2026-07-28/29), and it
repeated even though the project's own notes already warned about it ("~15 build
cycles", "burned many hours and never converged").

**Measured → landed FIRST TRY, every time:**
- `MCAL` dock pass (flyout native pos vs spawn button) → Landscape dock exact.
- The alignment-marker rule → reproduced 3 locked god docks to the pixel.
- `SVT` class probe → proved the sub-flyout IS the disaster class, so its fixes
  applied verbatim and no reverse-engineering was needed at all.
- `SBLT` blit trace → found the bar bug in ONE pass after three screenshot
  builds had missed it.
- `RCAL` ring trace → settled "painted art vs window art", which decided the fix.
- Container-dock arithmetic → `btn + (-33,-110)`, correct for every item because
  the `btn` term cancelled.

**Inferred from a screenshot → 2-3 builds each, and twice a regression:**
- Terraform shifted TWICE by a mode test verified in only 2 of its 3 states.
- The minimap went dark because a panel was moved on an assumption — and that
  change had already failed to fix the bug it was written for, so it should have
  been reverted immediately rather than left in.
- Three consecutive builds adjusting a bar constant against pixels.

**How to apply:**
1. When a value is unknown, BUILD THE INSTRUMENT (an ini-gated log line) and
   read the number. It is almost always faster than one wrong build cycle.
2. Never gate behaviour on a state test not verified in EVERY state it will run
   in (for SC4: pre-founding god, founded god, mayor).
3. If a change does not fix the bug it was written for, REVERT IT in the same
   session.
4. **If two symptoms contradict each other — "centre it here" vs "attach it
   there" — you are working at the wrong LAYER. Move up one level.** The
   sub-flyout ring was never what should move; the container was. That single
   reframe resolved days-old-feeling thrash in one build.
5. Prefer live-tunable ini levers so a wrong guess costs a file save, not a
   rebuild + relaunch.
6. **AUDIT THE INSTRUMENT BEFORE YOU BELIEVE IT — ours lied twice in one night
   (2026-07-30).** (a) A line that logs a **state** will lie about **when**:
   the sweep's `SUBHOOK ... installed` prints every sweep while a menu is open
   (194x in one session) because the install is gated separately above it, so
   it read as a 159 ms *install* gap when the real event was the claim change
   (`SUBCLAIM`, which fires only on a real write). (b) A line that logs an
   **input** will not tell you the **output**: `DCBUF` prints the incoming blit
   request, so `dst(205,..) src 53x3` looks like "the bar drew 1x" and still
   prints, unchanged, after the bug is fixed. **Before timing anything from a
   log line, read its printf and confirm it sits inside the branch that DOES
   the thing.** Same family as the FLASHSET blind spot: an instrument is a
   claim about the code, and it decays.
6b. **THREE shapes now, all in one night — the third: a line that reports a
   SUB-WALK, not what you DID.** `HookRuntimeBmpsUnder` hooked the root and
   then logged `if (installed > 0)`, where `installed` counted only children.
   An id that IS the target (no children) hooked **silently**, so the log
   DENIED a fix the user could see working. Report what the function did, not
   what a helper happened to do. And: **an instrument that walks one ROOT is
   blind to windows under another** — the edge probe walked the 3D view and
   missed its own prime suspects, which lived under the main window (the
   FLASHSET blind spot again, two turns after writing it up).
7. **A defect that appears only on the FIRST use of a session is almost always
   an uninitialised LATCH, not a race.** Later uses look clean because they
   inherit state, not because they are quicker — first sub-flyout of a city
   waited 159 ms for its chrome state; opens #2+ took 30-48 ms and were
   invisible, because they were pre-warmed.

Related: [[reference-sc4-flyout-alignment-marker-rule]],
[[feedback-sc4-founded-city-invalidates-notes]],
[[reference-sc4-flyout-hittest-playbook]], [[project-sc4-ui-scaling-northstar]]
