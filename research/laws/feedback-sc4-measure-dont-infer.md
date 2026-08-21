# Build the Instrument, Read the Number

When a geometry value in SC4's UI is unknown, building a temporary instrument
that prints it is almost always cheaper than one wrong build cycle. Across the
Mayor-mode scaling work the cost split was unambiguous: every value that was
*measured* landed on the first build; every value *inferred from a screenshot*
took two to three builds, and two of them broke a working feature on the way.

## Measured values landed first try

- A dock-position probe that logged a flyout's native position alongside its
  spawn button's position gave the Landscape dock offset exactly.
- The alignment-marker rule, once derived from logged marker coordinates,
  reproduced three locked god-mode docks to the pixel.
- A window-class probe on a sub-flyout proved it was the same class as an
  already-solved panel, so the existing fix applied verbatim and no further
  reverse engineering was needed.
- A blit trace found a status-bar defect in one pass after three
  screenshot-driven builds had missed it.
- A ring-geometry trace settled whether the artifact was painted art or window
  art, which was the question that decided the fix.
- Container-dock arithmetic reduced to `btn + (-33,-110)` and was correct for
  every item in the container, because the per-button term cancelled.

## Inferred values cost builds and caused regressions

- A terraform panel shifted twice because the mode test driving it had only been
  verified in two of its three states.
- A minimap went dark because a panel was moved on an assumption. That same
  change had already failed to fix the bug it was written for, so it should have
  been reverted before it was allowed to cause a second defect.
- Three consecutive builds adjusted a bar constant against screenshot pixels
  without converging.

## Practice

1. When a value is unknown, build the instrument — an ini-gated log line — and
   read the number.
2. Never gate behaviour on a state test that has not been verified in every
   state it will run in. For SC4 that means pre-founding god mode, founded god
   mode, and mayor mode.
3. If a change does not fix the bug it was written for, revert it immediately.
   Leftover speculative edits are the source of the second, unrelated defect.
4. If two symptoms contradict each other — "centre it here" versus "attach it
   there" — the work is happening one layer too low. Move up a level. A
   sub-flyout ring that seemed to need centring and attaching at once was never
   the thing that should move; its container was. That reframe ended the thrash
   in a single build.
5. Prefer live-tunable ini levers, so a wrong guess costs a file save rather
   than a rebuild and relaunch.

## Audit the instrument before believing it

An instrument is a claim about the code, and it decays as the code changes.
Three distinct ways a log line lies:

- **A line that logs a *state* lies about *when*.** A sweep that printed
  "subhook installed" printed it on every sweep while a menu was open (194 times
  in one session) because the install itself was gated separately, above the
  print. Read as timing, it suggested a 159 ms install gap; the real event was
  the claim change, which fired only on an actual write.
- **A line that logs an *input* does not report the *output*.** A blit-buffer
  trace printed the incoming request, so a line reading `dst(205,..) src 53x3`
  looked like proof the bar drew at 1x — and kept printing, unchanged, after the
  bug was fixed.
- **A line can report a sub-walk rather than what the function did.** A helper
  that hooked a root window and then walked its children logged
  `if (installed > 0)`, where `installed` counted only children. An id that
  *was* the target and had no children hooked silently, so the log denied a fix
  that was visibly working on screen.

Before timing or concluding anything from a log line, read its printf and
confirm it sits inside the branch that actually does the thing. And note that an
instrument which walks one root is blind to windows parented under another: an
edge probe that walked the 3D view missed its own prime suspects, which lived
under the main window.

## First-use-only defects are latches, not races

A defect that appears only on the first use in a session is almost always an
uninitialised latch. Later uses look clean because they inherit warmed state,
not because they are faster. The first sub-flyout opened in a city waited 159 ms
for its chrome state; opens after that took 30-48 ms and were invisible.
