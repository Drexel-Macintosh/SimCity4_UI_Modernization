---
name: project-sc4-flash-subflyouts
description: "SC4 UI scaling task #50/#76 — the flyout open-jump family, FIXED and user-confirmed at v2.36.2 by making windows BORN correct (geometry AND draw-hook state) instead of correcting them a tick later."
metadata: 
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-31T01:58:39.247Z
---

**STATE 2026-07-30: DONE, user-confirmed, deployed v2.36.2-bornhook.**
Three fixes, one principle: **make the window born correct instead of
correcting it a tick later.** Nothing pending, nothing awaiting eyes.

| ver | what | hook |
|---|---|---|
| v2.36.0 | nested sub-flyout born SCALED | detour on its `Place` `0x0079AD00` |
| v2.36.1 | first-level tool flyouts scaled+docked at OPEN | one hook on the opener `sub_7E5C10` (arg2 = flyout id) |
| v2.36.2 | their CHROME STATE born too (claim + draw hooks) | `InstallSubFlyoutHooksNow`, same detour |

**⚠ THE TARGETING LESSON (cost a whole build):** v2.36.0 fixed the NESTED
container, fired **zero** times, and the user still saw the jump — the menus
they meant were the FIRST-LEVEL flyouts. The log had said so all along:
`mayor flyout 0x699306ED ... +10 win (docked)` = 10 windows scaled at the
moment it was **already on screen**. **Read the instrument before believing a
fix targets the right window.**

**⚠ GEOMETRY AT BIRTH IS ONLY HALF.** v2.36.1 left the per-window draw state
(promoted `[0xE0]`, latched `gClaimOrig`, instance `SlotThunk`) to the sweep, so
the first sub-flyout of a city was born the right SIZE with **1x chrome** for
159 ms. Opens #2+ looked perfect because they **inherit** the latch, not
because they are faster (30-48 ms). **A defect that only appears on the FIRST
use of a session is almost always an uninitialised latch, not a race.**

**⚠ ORDER = the safety argument.** `[0xE0]` is dual-use (hit-claim width AND a
Plot layout inset); `SlotThunk<88>` presents the 1x value to the draw group.
Promote the field before installing the thunk → the game paints a **SECOND
orange bar** (v2.11.24). Container thunks first, always. A second bar = revert,
don't tune.

**Acceptance facts to re-check on any regression:** every `+N win` line
followed by its `FLYOPEN` in the SAME ms; `SUBBORNHOOK` before the first
`DCBUF` (8 ms, was 159); **`SUBCLAIM` count per session = 0** (the sweep finds
everything already done — the idempotency proof).

**⚠ TWO OF OUR OWN INSTRUMENTS LIE** (both bent a diagnosis that night):
`SUBHOOK ... installed` prints every SWEEP, not per install — **`SUBCLAIM` is
the honest signal**; `DCBUF` prints the incoming blit REQUEST, so
`dst(205,..) src 53x3` still appears after the fix. See METHOD.md "YOUR OWN
INSTRUMENTS CAN LIE".

Live levers, no rebuild (`[Flyout]`): `SubBornScale`, `SubBornDock`,
`BornOnOpen`. Detail: `_tests\REGRESSION.md` (v2.36.0/.1/.2 blocks),
`SC4-UI-ENGINE.md` §4.6b + §4.7 **row 4**, `tools\uimap\emu\emu_subflyout.py`
(71 checks; predicted n=7/n=8 before they were ever measured).

Related: [[feedback-sc4-blast-radius]], [[feedback-sc4-measure-dont-infer]],
[[feedback-docs-are-the-sdk]], [[project-sc4-ui-scaling-northstar]].
