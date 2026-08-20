---
name: feedback-liveness-guard-stored-window-pointers
description: "SC4: with a city loaded the game DESTROYS Graphic Options on Accept (the main menu only hides it). A stored dialog pointer re-read at close faulted — crash, no exception report, no SELCLOSE line. Cure = pass the pointer found THIS pass; null means destroyed: skip the re-read, zero the filters without RemoveMessageFilter on dead windows. Also: geometry from clip arithmetic (a GZWinBMP area is l,t,r,b; children clip to the local rect), never from screenshots — and the engine's combo drop-list paints the stock list colour regardless of .UI flags: the one colour reachable is the stock colour; join it, don't fight it."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-20T00:00:00.000Z
---

**THE CRASH.** User report: city loaded, Graphic Options opened, NOTHING
changed, Accept → dead. The log tail is the measurement: Accept click
14:41:55.971; the tree-watch instrument saw the dialog LEAVE the main-window
tree at 14:41:56.049; the log ends 14:41:56.127 — **no SELCLOSE line, no
shutdown dump, and NO exception report on disk** (the game's handler never
wrote one for this shape). The close handler's control re-read ran against a
**stored dialog pointer** on the strength of "hidden, not destroyed" — true
for every main-menu close ever measured, FALSE with a city loaded, where
Accept DESTROYS the dialog. The pointer dangled and the re-read faulted.

**Law 1 — "hidden, not destroyed" is a main-menu fact, not an engine law.**
A stored window pointer is a claim with an expiry you did not set. The close
branch must pass the pointer **it found THIS pass**: non-null = still in the
tree (hidden) → re-read + detach exactly as before; **null = destroyed →
skip the re-read** (the staged values the periodic tick already collected
stand) **and zero the button filters WITHOUT RemoveMessageFilter on windows
that no longer exist.** Structurally safe under both outcomes — the cure is
a guard shape, not a bet on which outcome happens.

**Law 2 — a crash that writes nothing is still diagnosable from the
absences.** No exception report + no SELCLOSE line + a tree-watch line
showing the dialog LEAVING 78 ms after the click is a complete measurement.
Do not wait for the game's crash artefacts; the log's missing lines are
artefacts too.

**Law 3 — geometry comes from clip arithmetic, never from screenshots.**
The same dialog shipped a row CUTOFF at the bottom one build earlier because
the panel `GZWinBMP`'s area `(15,37,479,393)` was read as (l,t,w,h) — it is
**(l,t,r,b)**, so children clip at 464 wide × 356 tall LOCAL, and a frame
bottom at 364 was 8 px past the clip ("29 px inside the parent" was the
wrong model). Derive every rect from the stock script's numbers — rails
from the sibling label's x0, rows from the free band between clip edges —
and assert the rects in the builder's paired gate so a future reshape fails
loud instead of shipping half-done. User direction that ended the class:
*"never read pixels, compute."*

**Law 4 — engine-owned chrome keeps its stock colour; join it, don't fight
it.** The combo's internal drop-list child paints the engine's STANDARD list
colour as its background **whatever the flags** — the stock grammar
(transparent + white fill) opens the same way. The open list's row area
follows `fillcolor` when opaque, which produced a two-tone "square in a
square"; an all-white open list cannot be produced from `.UI` at all (it
would be a game-wide byte patch of the shared listbox colour). **The one
colour reachable is the stock colour** — setting `fillcolor` to it on all
three combos makes closed field, open rows and surround one colour: the
stock control's exact look.

**How to apply:** any handler that outlives the window it serves (close,
commit, detach) must re-acquire the window in its own pass and branch on the
null; any rect you draw must be derivable from the script's own arithmetic;
and before fighting an engine chrome attribute, establish whether ANY `.UI`
value can change it — if none can, the stock look is the design target.

Related: [[feedback-state-machine-derive-diff-commit]],
[[reference-sc4-dialogs-live-under-main-window]],
[[reference-sc4-exception-reports]], [[feedback-sc4-measure-dont-infer]]
