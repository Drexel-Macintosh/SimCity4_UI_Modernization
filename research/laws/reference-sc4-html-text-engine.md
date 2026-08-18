---
name: reference-sc4-html-text-engine
description: "SC4: ALL rich text (news ticker/reader, stories, advisor+message popups, tutorials, Credits) renders through the game's own HTML engine, whose SIZE=1..7 point tables live in .rdata and FontStyle.ini can NEVER reach — this is why the community's font mods report 'font size does not work for news'. Fixed by patching the two tables; three coupled parts."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-29T23:39:36.160Z
---

Found 2026-07-29 (SC4UIScale v2.19.0) while fixing the News Box. It explains a
long-standing community limitation, so it is worth keeping even outside this
project.

**THE FINDING.** News ticker roll, news-reader headlines, expanded story pages,
advisor/message popup toasts, the 189 tutorial pages and the Credits window all
render through **one built-in HTML renderer**, not through a FontStyle style.
The exe carries literal templates in `.rdata` (e.g. `<FONT FACE="Arta"
SIZE=3>`), and locale LTEXTs embed their own `<font size="N">`. `SIZE=1..7`
resolves through **two point-size tables**: fonts at `0xACD4A0`
`{8,10,12,14,18,24,36}` and `<H1>..<H7>` at `0xAB4AD0`
`{8,10,12,16,19,24,48}`. **FontStyle.ini never touches this path** — which is
exactly why DAT-based font mods hit the wall.

**THE FIX (three COUPLED parts — breaking one regresses the others):**
1. Scale both tables in place at `PostAppInit`
   (`CodePatches::ApplyHtmlSizeScale`, verify-before-write). Each rich window
   COPIES the tables at creation (setter `0x8FEEB8` → `this+0x1A8`), so one
   patch reaches every instance the game will ever build.
2. The popup builders derive their index from a *style's* size
   (`idx = (4*size+8)/18`), and our FontStyle DOUBLES those styles — so the
   builders' style GUIDs are retargeted at **stock-size clone styles**
   (`MessageHeaderHtml` 0x5c4b0914, `MessageBodyHtml` 0x5c4b0915) that every
   FontStyle tier file carries. **Those clones must stay at STOCK sizes at every
   tier** or popups compound to ~4x.
3. The Credits LTEXT size maps had to be re-calibrated, since the old per-factor
   bumps would compound against the now-scaled tables.

**Related engine fact:** `GZWinBMP`-family windows draw **dst = src size**, so
2x art scales the draw with no code hook — and a 2x `imagerect` over a 1x
bitmap draws only the corner that exists (the signature of a shadowed art
override).

Detail + trap signatures: `_tests\REGRESSION.md` → "NEWS BOX + NEWS TEXT = THE
HTML ENGINE"; the FontStyle limitation is closed out in
`tools\fonts\FONTSTYLE-RESEARCH.md`.

Related: [[feedback-sc4-scaling-laws]], [[project-sc4-ui-scaling-northstar]],
[[reference-sc4-scenario-matrix]]
