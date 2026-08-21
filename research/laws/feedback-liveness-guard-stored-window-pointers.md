# Stored Window Pointers Need a Liveness Guard

A stored pointer to an engine window is a claim with an expiry the storing code
does not control. In SimCity 4 the lifetime of the Graphic Options dialog
depends on where the game is: from the main menu, Accept only *hides* the
dialog, so the pointer stays valid; with a city loaded, Accept **destroys** it.
Any handler that re-reads its controls at close time on the strength of
"hidden, not destroyed" reads a dangling pointer and faults the process.

## The guard shape

The close branch must use the pointer it locates **in that pass**, not one
cached at open time, and branch on the result:

- **Non-null** — the dialog is still in the main-window tree (hidden). Re-read
  the controls and detach message filters exactly as normal.
- **Null** — the dialog has been destroyed. Skip the control re-read entirely
  (the values staged by the periodic tick are the committed state), and zero
  the button filter slots **without** calling `RemoveMessageFilter` on windows
  that no longer exist.

This is structurally safe under both outcomes. It is a guard shape, not a bet
on which lifetime the current game state happens to have. The general rule:
any handler that outlives the window it serves — close, commit, detach — must
re-acquire the window in its own pass and branch on the null.

## A crash that writes no artefact is still diagnosable

This fault produces nothing on disk: the game's exception handler does not
write a report for this shape, and the mod log simply stops. The absences are
the measurement. A close click at `14:41:55.971`, a tree-watch line showing the
dialog leaving the main-window tree at `14:41:56.049`, and the log ending at
`14:41:56.127` with **no** close-handler line pin the fault to the close path
78 ms after the click, without a single crash artefact. Missing log lines are
evidence; do not wait for a dump that the handler will never write.

## Geometry comes from clip arithmetic, not from screenshots

A `GZWinBMP` panel's `area` is `(left, top, right, bottom)` — **not**
`(left, top, width, height)` — and its children clip to the resulting *local*
rect. A panel declared `area=(15,37,479,393)` therefore clips children at
464 x 356 in local coordinates, so a child frame whose bottom sits at 364 is
8 px past the clip edge and its last row is cut off. Reading the numbers as
width/height produces the plausible-but-wrong conclusion that the frame ends
29 px inside the parent.

Derive every rect from the script's own numbers — rails from a sibling label's
`x0`, rows from the free band between clip edges — and assert those rects in
the generator's paired gate, so a future reshape fails loudly instead of
shipping a clipped row.

## Engine-owned chrome keeps its stock colour

The combo box's internal drop-list child paints the engine's standard list
colour as its background regardless of the `.UI` flags set on it; the stock
grammar (transparent plus white fill) opens exactly the same way. Only the
open list's *row* area follows `fillcolor` when that colour is opaque, which is
what produces a two-tone "square in a square" when the two differ. An all-white
open list is unreachable from `.UI` at all — it would require a game-wide byte
patch of the shared listbox colour.

The one colour reachable is the stock colour. Setting `fillcolor` to that
colour on every combo makes the closed field, the open rows and the surround a
single colour, which is the stock control's exact look. Before fighting an
engine chrome attribute, establish whether *any* `.UI` value can change it; if
none can, the stock appearance is the design target.

See also: [state machines derive, diff, commit](feedback-state-machine-derive-diff-commit.md),
[dialogs live under the main window](reference-sc4-dialogs-live-under-main-window.md),
[the game's own exception reports](reference-sc4-exception-reports.md),
[measure, don't infer](feedback-sc4-measure-dont-infer.md).
