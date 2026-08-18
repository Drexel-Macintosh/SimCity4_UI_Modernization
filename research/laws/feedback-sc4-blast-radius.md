---
name: feedback-sc4-blast-radius
description: State the PRIZE and the BLAST RADIUS before writing code and refuse upside-down trades; a constant is never alone (ripples); use the offline model before touching the game.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-31T00:27:08.440Z
---

**Earned 2026-07-30 night: two user-visible breakages, zero flashes fixed.**
The user, watching working menus break twice: *"You know we're trying to fix
just the flash on the flyouts right? I don't understand why everything is
broken again."*

**1. PRIZE vs BLAST RADIUS — say both out loud before writing code.**
The prize was a **1-2 frame flash (20-36ms)**. The change was **rebuilding how
working menus are constructed**. That trade is upside-down however well it is
engineered. Ask, in order: what exactly does the user get (quantify it); what
breaks if I am wrong (cosmetic residual, or a menu that no longer opens); is
there a SMALLER mechanism that already exists (prefer tightening a proven path
over building a new one); can the offline model answer it first.

**2. A CONSTANT IS NEVER ALONE.** Moving one `push imm8` drove a value 200
bytes away in another subsystem negative:
`[+0xEC] = artHeight − 2×[+0xE8]` → stock 3, constants-only **−47** (renders
as a sliver), art-only 56, both 6. Before changing any constant ask the model
what READS it and what is COMPUTED FROM it. If a fix has two halves computed
from each other they ship together or not at all — and if shipping both still
fails, a third term exists: stop and find it offline.

**3. THE GAME IS SIMULATED — model first, game last.**
`SC4TouchControls\tools\uimap\` is a working offline model: `census.py` /
`constants.py` (which builder, which constants, encodings + twins),
`emu\emu_layout.py` (runs the game's own layout code under Unicorn, predicts
rects at any factor), `diff\` + `_tests\Test-UiMapDiff.ps1` (predicted vs live
vs stock at f=1/1.5/2/3). Every "what if I change this?" has an offline answer
costing minutes that cannot break anything. A shipped experiment costs a
build, a deploy, the user's play session, and sometimes their working UI.

**4. TREAT THE DOCS AS A UI SDK YOU ARE WRITING** (user's framing). An SDK
author doesn't guess an API's behaviour, doesn't change a shared primitive
without enumerating its callers, documents failure modes beside the feature,
and re-reads the reference before every change — **including the parts they
wrote themselves**. Three times in one evening the answer was already in these
files and went unread.

**5. "It worked for panel X" is not evidence about panel Y.** Pick the cure
from the window's CONSTRUCTION TYPE (`SC4-UI-ENGINE.md` §4.7), never by
analogy: data pre-scale cured the advisor strip and broke the composed city
HUD.

Canonical text: `tools\research\METHOD.md` §6A; laws 29-33 in
`_tests\REGRESSION.md`.

Related: [[feedback-docs-are-the-sdk]], [[project-sc4-flash-subflyouts]],
[[feedback-sc4-measure-dont-infer]], [[feedback-sc4-scaling-laws]].
