# Born-Correct Flyouts

Tool flyouts and their nested sub-flyouts must be **born correct** — scaled,
docked, and with their per-window draw state already promoted — rather than
corrected by the next sweep tick. Anything left to the sweep is visible on
screen for as long as the sweep takes to arrive.

## The three hooks

| what is made born-correct | where |
|---|---|
| nested sub-flyout geometry (scaled at creation) | detour on its `Place` at `0x0079AD00` |
| first-level tool flyouts, scaled and docked at open | one hook on the opener `sub_7E5C10` (arg 2 is the flyout id) |
| per-window chrome state (claim field + draw thunk) | `InstallSubFlyoutHooksNow`, from the same detour |

Live levers under `[Flyout]`, changeable without a rebuild: `SubBornScale`,
`SubBornDock`, `BornOnOpen`.

## Geometry at birth is only half

Scaling a flyout at creation while leaving its per-window draw state — the
promoted `[0xE0]` field, the latched `gClaimOrig`, the instance `SlotThunk` — to
the sweep produces a window that is born the right **size** with **1x chrome**.
Measured, the first sub-flyout of a session carries 1x chrome for 159 ms.
Subsequent opens look correct in 30–48 ms not because they are faster, but
because they **inherit** the already-latched state.

That timing signature generalises: **a defect that appears only on the first use
of a session is an uninitialised latch, not a race.** Look for the one-time
initialisation that the first consumer misses, not for a timing window.

## Order: promote the field before installing the thunk

`[0xE0]` is dual-use — it is both the hit-claim width and a Plot layout inset —
and `SlotThunk<88>` presents the 1x value to the draw group. If the field is
promoted before the thunk is installed, the game paints a **second orange bar**.
Container thunks go in first, always. A second bar is a symptom of wrong install
order, so the response is to revert the ordering, never to tune the values.

## Acceptance signals

- Every `+N win` line is followed by its `FLYOPEN` in the **same millisecond**.
- `SUBBORNHOOK` appears before the first `DCBUF` — 8 ms when correct, 159 ms
  when the chrome state is left to the sweep.
- `SUBCLAIM` count per session is **0**: the sweep finds everything already
  done, which is the idempotency proof.

## Two instruments in this area lie

- `SUBHOOK ... installed` prints on every **sweep**, not once per install, so it
  cannot distinguish "installed now" from "already installed". `SUBCLAIM` is the
  honest signal.
- `DCBUF` prints the incoming blit **request**, not the result, so a line such as
  `dst(205,..) src 53x3` still appears after the fix has landed and proves
  nothing about what was painted.

Neither line is evidence of what reached the screen. See
`tools\research\METHOD.md`, "your own instruments can lie".

## Target the window the player actually sees

A fix aimed at the nested container can fire **zero** times while the visible
jump persists, because the menus in question are the first-level flyouts. The
log states this plainly: a line like
`mayor flyout 0x699306ED ... +10 win (docked)` records 10 windows being scaled at
a moment when the flyout is **already on screen**. Read the instrument and
confirm which window a fix touches before believing it targets the right one.

Further detail: `tools\research\SC4-UI-ENGINE.md` §4.6b and §4.7 row 4. The
offline model `tools\uimap\emu\emu_subflyout.py` covers this family with 71
checks and predicts the n=7 / n=8 child counts that the running game produces.
