---
name: feedback-check-our-previous-work-first
description: "⭐ NORTHSTAR (user order) — on EVERY diagnosis, first check whether we have hit this before AND whether the way we fixed it then is viable now; every win of 2026-07-31 came from the repo and every loss came from skipping it."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-06T16:45:26.749Z
---

**USER DIRECTIVE (2026-07-31, verbatim): "ALWAYS CHECK OUR PREVIOUS WORK FOR
THE ANSWER."** Execute this way from now on, on every project.

## ⭐ NORTHSTAR (user order, 2026-08-06) — TWO QUESTIONS, NEVER ONE

Verbatim: *"make it a northstar within projects like this for every issue on
diagnoses to check if we've encountered this before and see if the way we
resolved it before is viable"*.

So the intake step is **two questions, and the second one is the one that gets
skipped**:

1. **Have we hit this before?** — grep our docs, source comments and changelog.
2. **Is the way we fixed it then VIABLE HERE?** — and if it is, PORT THAT FIX
   rather than inventing a new one. If it is not, say why in one sentence
   before designing anything.

**Paid for four times in a single day (2026-08-06), all on the same project:**

| what was already written down | where | what skipping it cost |
|---|---|---|
| the HQ scaler was evaluated and **rejected** — "fringes the magenta colorkey" | `README.md`, the row for the very tool being edited | re-introduced it; the user's Mayor Rating bar and news-reader borders went pink within one launch |
| the "0-new-colors check" — nearest-neighbour introduces **no colour the source lacks** | `tools\upscale\VERIFY.md` | that one fact refutes the resampler as the cause of a WHITE line, with no launch and no instrument. Chased it anyway |
| the `width/4` cell-divide law, under a heading literally called *"Two rules that are not optional"* | `docs\BUILDING.md` | the law was right but scoped to menu icons and implemented in one builder; generalising it was the whole fix |
| the dock minimap "garbage" **is our own baked artwork**, cured by neutralizing it | `VERSION-HISTORY.txt` v2.73.0 (#126) | invented a window-shrink on top, which turned OFF the stretch blit that fills the recess. The user had to say *"you have fixed the map on 2x and 3x before, remember"* |

**The failure mode is specific and worth naming:** finding that a prior fix
EXISTS and then not asking whether it APPLIES here. In the minimap case the
prior cure was found, quoted, and still not ported — a new mechanism was
designed beside it. **Finding the precedent is not the deliverable; applying it
is.**

**Corollary — when a tier/variant/instance still misbehaves and a sibling was
confirmed fixed, the default hypothesis is "the known cure never reached this
one", NOT "this one needs a new cure."** Check the gate that decides who gets
the fix (a factor threshold, a mod gate, an id list) before writing code. The
1.5x minimap was exactly this: `DOCK_NEUTRALIZE_MIN_FACTOR = 2.5` excluded it
from a cure that already worked.

**RESTATED AS A MANDATORY TWO-ENDED LOOP (user order, same day, evening):**
*"when you get a bug to fix you first compare it against our lessons learned
and SDK and other documents"* — and *"after you fix each bug you update the
documentation."*

- **INTAKE (before any theory, agent or build):** run the SDK lookup on the
  id/art/script (`python tools\sdk\lookup.py <id>` — see
  [[reference-sc4-sdk-lookup]]), match the symptom to a solved family in the
  laws/TRIAGE, then check the generation + regression docs. Only then measure.
- **OUTTAKE (same session, before moving on):** VERSION-HISTORY (what changed
  and why, including what was refuted) → REGRESSION (expected lines,
  acceptance, trap, revert) → the mechanism doc → TRIAGE row / new law /
  HANDOFF → **and correct anything the fix proved wrong.**

A fix is not done when the code works; it is done when the next reader cannot
repeat the mistake. Full text of both ends: [[feedback-docs-are-the-sdk]].

**The evidence from one day, five shipped fixes, all measured:**

| the answer was already in the repo | what it cost to look / not look |
|---|---|
| region rating bar drew twice (#72) | the art was ONE missing `CODE_BOUND_TGIS` entry — the family had been fixed twice before (picker icons #55, Grutzehaus #49). Filed "outside the SDK" for a day on nulls our own **law 20** had already said were blind |
| pause border (#59) | THREE alert-border sheets exist; two were already in our own package **mislabelled "Mayor rating face state A/B"** with the middle one dropped. One line. It had been closed as "unfixable" |
| quit-confirm creep | `REGION-SWITCH.md:24` recorded the same bug (`342→684→1368`) and `UiSpike.cpp:7861` had the shipped cure |
| Exit/Quit static doubling | `UiSpike.cpp` already said the game **bypasses** it. A fresh decode claimed the opposite; the decode was wrong. **Two minutes of reading beat a 500 KB decode** |
| `ShowHook` for the quit confirm | `SC4-UI-ENGINE.md` §4.7 already recorded the anti-pattern ("cannot work for anything created on demand"). Measured true |

**THE ORDER, and it is an ORDER not a menu** (`METHOD.md` law 22):
our docs → `vendor\` SDK headers → live instruments → disassembler → a shipped
experiment. A shipped experiment is the most expensive move available and is
what gets reached for when the first four are skipped.

**The specific habits that worked:**
- **Match the symptom to a solved family FIRST** — `tools\research\TRIAGE.md`
  exists for this; it classified five defects on sight.
- **Grep our own source comments before believing any new analysis**, including
  a subagent's. Our comments are measured; a fresh decode is a hypothesis.
- **When a symptom matches a solved family but the diagnosis says
  "unreachable", suspect the DIAGNOSIS** — that reversed two "unfixable"
  verdicts in two days.
- **Verify the instrument before believing it, in BOTH directions.** A null
  needs a positive control; so does a positive (a watchdog's own false alarm
  and a claimed-but-never-added log line both bit on the same day).
- **Read the file before patching it.** Three failed whitespace-guessed patches
  vs one that worked after actually reading the lines.

**THE OTHER HALF OF THE ORDER — "we fixed that" does not mean THIS one was
fixed.** Checking previous work tells you the cure EXISTS; it does not tell you
this family received it. Fixes are applied to the family in front of us and
almost never back-ported, so an old family can sit on a superseded mechanism for
dozens of versions while its siblings are upgraded twice — and **its notes stay
frozen at the moment it was last touched, growing more confidently wrong**. One
audit found five stale claims still being quoted as fact, one of them about a
*different window* entirely, being used to justify a gate on this one. So when
something still misbehaves though "we fixed that": ask which GENERATION of the
fix it is on, and re-verify any note older than the last mechanism change before
reasoning from it. (SC4's version of this ledger:
`tools\research\MECHANISM-GENERATIONS.md`; see law 20 in
[[feedback-sc4-scaling-laws]].)

**Anti-pattern to refuse:** launching a large decode before reading the repo.
Twenty-three agents were spawned on 2026-07-31; the two decisive answers came
from `grep` on our own files, and one decode's central premise was refuted by a
single source comment.

Related: [[feedback-docs-are-the-sdk]], [[feedback-null-is-not-evidence]],
[[feedback-blind-instruments-agreeing]], [[feedback-sc4-measure-dont-infer]].

## ⛔ HARDENED 2026-08-14 (user order): GREP THE DOCS **FIRST**, NOT AFTER

**"We should not be figuring anything out from scratch at this point."**
On ANY new symptom, BEFORE building an instrument or forming a theory:

    grep the SYMPTOM (not your theory) in _tests\REGRESSION.md,
    src\*.cpp comments, toolsesearch\*.md, and the task list.

One session, THREE rediscoveries of things already written down:
1. The icon symptom was **#49 verbatim** (REGRESSION.md:1387) - GZWinBtn takes
   stateW = imageWidth/4, so THE COPY COUNT IS THE SCALE RATIO. I proposed two
   wrong mechanisms first.
2. "Hook slot 87, it never fires, try InvalidateSelfAndParents" is documented
   as a DEAD END at **UiSpike.cpp:96-99** - I repeated the whole experiment,
   including the invalidate, and burned two launches.
3. The same comment block gives the corrected slot table AND the rule that only
   ZERO-ARG slots may be thunked (__thiscall is callee-cleanup). I shipped a
   4-arg thunk on a slot I had not verified - a latent stack corruption.

COROLLARY - A SOURCE COMMENT CAN BE WRONG, AND THE GREP STILL WINS: the same
file claims "GZPaint is vtable INDEX 87". In build 1.1.641 slot 87 is
, a getter; the real draw is **slot 88 / 0x0079AA70**.
Grepping surfaced the claim; DISASSEMBLY settled it. Read the docs first, then
verify the load-bearing line against the bytes.
