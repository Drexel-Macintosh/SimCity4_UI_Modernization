# Pre-Scale Windows While They Are Hidden

Two rules that close the "menu flashes stock or garbled before it resizes" class
of bug in the SimCity 4 UI scaling mod.

## 1. Pre-scale while hidden — never suppress paints

If a window is only scaled once `IsVisible()` returns true, the game gets to
paint one stock (or half-transformed) frame first. That frame *is* the flash.
The cure is to scale the window before it is ever shown:

- Run the subtree scale **unconditionally**, hidden windows included.
- Gate **only the reposition/dock move** on visibility. Docking a closed flyout
  can land it on top of another one, so that constraint is real — but it applies
  to the move, not to the resize.
- `ScaleSubtree` is idempotent via `scaleMap`, so pre-scaling a hidden window is
  a one-time cost, not repeated work every frame.

The same pattern already exists for the region screen: `IsRegionPanelId` is a
deliberate exception to the sweep's skip-invisible rule, commented "pre-scaled
while hidden so they appear already at 2x (no visible jump when a flyout
opens)". Any panel family that flashes on open is a candidate for the same
exception. When a UI bug looks new, check whether the region-screen pass already
solved it.

### The rejected approach: paint suppression

A "FlashGuard" that suppressed `Plot` for any descendant of the god-flyout
parent until the sweep marked the subtree ready does not work, for two reasons:

1. That parent is an ancestor of far more than the flyouts. Unrelated HUD
   windows — the bottom-left date panel, the City Name panel — went unpainted:
   black box, missing art.
2. It never removed the flash anyway, because the flash comes from the *content*
   being stock-sized, not from the paint happening early.

Blanking windows at paint time is the wrong layer. The code remains in-tree,
disabled behind `FlashGuard=0`, as a record of the dead end.

## 2. Static-dat dialogs inside the swept tree need both halves

A popup whose geometry is fixed by the DialogStatic dat *and* which also lives
inside the DLL's swept window tree must additionally have its root id added to
`kNeverScaleIds` in `UiSpike.cpp`. The three outcomes:

- **Static dat only** — the sweep scales the already-scaled dat geometry a
  second time, landing at roughly 4x. Observed in the log as
  `868x468 -> 1736x936`.
- **DLL only** — correct size, but the `GZWinText` nodes render in the wrong
  colour (purple) while TextEdit and button captions stay black.
- **Both** — correct. Proven on the Establish City dialog, root id `0x6A414973`,
  script `I-2a41436b`.

Diagnostic for deciding which case a given popup is in: if the popup already
renders larger than stock *before* the dat is touched, the DLL sweep owns it, so
it needs both halves. Confirm dialogs parented to the main window — query
panels, the can't-save-during-disaster box — sit outside the sweep and need the
dat only.

## Delivery constraint

Every fix must ship from the Plugins folder (DLL, ini, and dats). `SimCity
4.exe` is never modified on disk; runtime byte patches are applied in memory
only.
