---
name: feedback-scale-the-mods-own-dialogs
description: "SC4UIScale — a gate that only asks \"is what we built still correct?\" is blind to \"is there something we never built?\". CAM's own dialogs rendered at 1x for the life of the project with every gate green. Run the census in the other direction."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-13T20:35:05.140Z
---

**A GATE THAT ONLY ASKS ABOUT YOUR OWN WORK CANNOT SEE WORK YOU NEVER STARTED.**

CAM's Village Hall / Town Hall info screen `{96a006b0,9b868f68}` rendered at
**1x under 1.5x fonts for the entire life of SC4UIScale** — labels cut
mid-word, values printed over them — and **every offline gate stayed green**.

**Why:** `build_dialog_static.py` has a good winner assert. It asks *"is one of
OUR targets owned by a plugin?"* It has never asked the mirror question,
***"is a PLUGIN'S OWN dialog scaled at all?"*** A mod-ADDED window is in no
TARGETS list, has no stock twin to diff against, and is never built — so every
verifier is structurally blind to it. Same family as [[feedback-sc4-scaling-laws]]
law 42 (a gate is only as honest as its SCOPE).

**How to apply:** for any coverage question, run the census in BOTH directions.
"Is what we built still correct?" AND "enumerate what EXISTS, subtract what is
handled, name the remainder." In this project that instrument already existed:
`tools\uiscripts\winning_corpus.py` had been listing the three CAM-only scripts
as unhandled third-party holders, under a heading literally called "What to
do", since the day it was written. **The report was right and unread for
weeks** — the same shape as the #150 gate that was red for two hours.
Now at 0 third-party winners.

**⛔ SECOND FINDING, AND IT COST A SECOND USER REPORT: the CROP is a third
number and it does not scale itself.** `blttype=normal` slices `imagerect` out
of the bitmap and blits that slice at the window origin. v2.97.0 scaled the
window (285→428) and the bitmap (285→429) and left `imagerect=(0,0,285,30)`
alone — every row stripe painted 285px of a 428px window. The builder scales a
rect only when `art_plan` says that art was scaled, and `art_plan` knows the
STOCK store only, so **mod art is always classified "left1x" there**. Reuse
`RUNTIME_BOUND_2X` ("the ref is unchanged but its pixels are scaled"), scoped
to the owning package. The build printed `rects2x=0` on a file with 24
imagerects and it was read past. See [[feedback-sc4-scaling-laws]] laws 73/74.

**Third:** when a mod supplies its own `GZWinBMP` art,
`blttype=normal` means the bitmap is drawn at its OWN size and CLIPPED by the
window — never stretched. So art and window do not scale to the same number and
CANNOT (see the offset-parity law in
[[project-sc4-15x-three-open-defects]]: 285 becomes 427 or 428 depending on the
parity of the left edge). Do not "fix" the upscaler. The question that decides
what the screen looks like is whether **the pixels the window cuts are a repeat
of the last pixels it keeps** — and it must be asked at 1x too, because the mod
crops several of its own strips on purpose.

Third: **CAM's data has dangling TGI refs** — `{46a006b0,b5cfffff}` (nowhere in
9 archives or the whole Plugins tree) after the `0xFF5D2E9F` graph-label typo.
Before ever calling a ref dangling, get the null from an instrument that reads
**Plugins too**, with a positive control from the same run — see
[[feedback-null-is-not-evidence]]. A stock-only null already shipped one visible
defect here (the 2x2-tiled splash).

**CLOSED v2.97.1, USER-CONFIRMED "perfect", 2026-08-13** — but it took two
builds, and the second defect (the unscaled crop) was the more instructive one.
Detail in `_tests\REGRESSION.md` #154 and its CORRECTION section.
