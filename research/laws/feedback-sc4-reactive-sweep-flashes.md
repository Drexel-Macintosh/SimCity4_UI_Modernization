# The Reactive Sweep and the 1x Flash

At every mode transition — god mode, mayor mode, the Sims panel — the unscaled
1x menus paint for a split second before snapping to the scaled version. This
is architectural, not a per-panel bug, and it explains a whole class of
reported symptoms.

## Why the flash is structural

The runtime scaler is reactive. It sweeps the `cIGZWin` tree roughly four
times a second off a 16 ms subclass timer, and swept panels are deliberately
**born 1x**: the selective-safe builder edits art and `imagerect` only, never
`area=`, so shipped geometry stays stock. Every mode switch constructs or
re-imposes those windows, so a 1x paint lands in the 0-250 ms window before the
next tick claims them. Nothing is wrong with any individual panel; the timing
is the defect.

The corollary is what makes it feel like a regression as work progresses: the
flash count grows with coverage. Each newly scaled panel adds one more
transition that can flash, so the symptom reads as universal once most of the
UI is covered.

## The cure is "born scaled", never "hide the paint"

Two per-window mechanisms are proven, and each one deleted a half-working
runtime hack when it landed:

- **Data pre-scale.** Ship the subtree already scaled in the `.UI`
  (`double_subtree_areas` plus a root-only entry in `kDataScaledSubtreeIds`).
  This cured the advisor strip's quarter-zoomed faces with zero flash.
- **Pre-scale while hidden.** Via `kAlwaysScaleCityIds`, scale the window
  before it is ever shown — the route used for region flyouts, the news
  reader, and budget popups.

Generalising that timing means a scale-at-birth hook: post-construction of the
`.UI` tree, the mode-switch instantiation path, or the visibility setter at
vtable offset 0x10C.

## Paint suppression is permanently rejected

A guard that skipped paints to hide the 1x frame blanked HUD windows outright.
Suppressing draws trades a brief wrong frame for a permanently missing one; the
correct lever is always the construction timing, never the paint.

Two constraints follow from working inside the sweep:

- Never call `Plot` or any other draw entry point from a hook.
  `InvalidateSelf` is the safe "mark dirty" primitive.
- A birth-scaled window will still be revisited by the reactive sweep, so
  idempotency is mandatory: the scale map must recognise its own prior work,
  or a window scaled once at birth ends up scaled again on each subsequent
  tick.
