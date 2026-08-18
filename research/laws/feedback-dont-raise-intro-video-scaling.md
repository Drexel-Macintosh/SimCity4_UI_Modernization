---
name: feedback-dont-raise-intro-video-scaling
description: "USER ORDER 2026-08-05 — SC4 intro-video scaling (#138) is on the backlog. Do NOT mention it unless the user explicitly asks about the backlog. Same discipline as [[feedback-meetsurface-not-installing]]."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-05T21:19:04.752Z
---

**USER STANDING ORDER (2026-08-05):** *"Put it on the backlog and don't bring
it up until I ask about the backlog."*

Refers to **task #138, scaling the SimCity 4 intro video** so it fills the
screen instead of drawing ~768x384 centred.

# Do not raise it. Not in status summaries, not in "still open" lists, not as a suggestion.

Only discuss it if the user asks about the backlog, asks about the intro video,
or names #138. Same discipline as [[feedback-meetsurface-not-installing]].

**Why the order exists:** it was investigated to a clear stopping point and the
honest verdict is *expensive, possibly impossible*. The shipped container patch
executes perfectly (4/4 sites, verified in the log) and changes nothing on
screen, because the frame is blitted by the player class from decoder state, not
from its window rect. Fixing it properly means turning a 1:1 frame copy into a
stretch blit inside the MPEG decode path - different code, not a constant. For a
five-second skippable clip. The user does not want it resurfacing.

**Full technical state is in the task itself** - addresses, vtables, the
refutation, and the law-47 timing note. Do not duplicate it here and do not
re-derive it; read the task if the user opens the subject.

⚠ The shipped `#138` patch stays in `CodePatches::ApplyIntroVideoScale`. It is
NECESSARY-BUT-NOT-SUFFICIENT: safe, gated, and a precondition for any future
stretch, but it produces no visible change alone. **Never write it up as "the
intro video scales"** - that would be [[feedback-sc4-scaling-laws]] law 50, a
documented lever that does nothing.

Related: [[project-sc4-ui-scaling-northstar]],
[[reference-sc4-intro-dat-is-the-eighth-archive]].
