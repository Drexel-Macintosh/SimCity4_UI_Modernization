# The Built-In HTML Text Engine

Every piece of rich text in SimCity 4 renders through one built-in HTML
renderer, not through a FontStyle style. That single fact explains a
long-standing community limitation: DAT-based font mods can change most of the
UI but report that "font size does not work for news".

## What routes through the renderer

- The news ticker roll
- News-reader headlines
- Expanded story pages
- Advisor and message popup toasts
- The 189 tutorial pages
- The Credits window

The executable carries literal markup templates in `.rdata` (for example
`<FONT FACE="Arta" SIZE=3>`), and locale LTEXTs embed their own
`<font size="N">` tags.

## The two point-size tables

`SIZE=1..7` resolves through two tables of point sizes compiled into `.rdata`:

| Table | Address | Contents |
| --- | --- | --- |
| `<FONT SIZE=1..7>` | `0xACD4A0` | `{8, 10, 12, 14, 18, 24, 36}` |
| `<H1>..<H7>` | `0xAB4AD0` | `{8, 10, 12, 16, 19, 24, 48}` |

FontStyle.ini never touches this path. A font mod delivered as a DAT can only
reach styles the style system owns; these are constants inside the binary, so
no amount of style editing moves them. That is the wall the community hit.

## The fix: three coupled parts

The parts are coupled — changing one without the others regresses the others.

**1. Scale both tables in place at `PostAppInit`.**
`CodePatches::ApplyHtmlSizeScale` verifies the existing bytes before writing.
Each rich-text window *copies* the tables at creation time (setter `0x8FEEB8`
stores into `this+0x1A8`), so one patch applied before any such window exists
reaches every instance the game will ever build.

**2. Retarget the popup builders at stock-size clone styles.**
The popup builders do not read a size directly; they derive a table index from
a *style's* size, using `idx = (4*size + 8) / 18`. A FontStyle that doubles
those styles therefore doubles the derived index on top of the already-scaled
table, compounding to roughly 4x. The cure is to point the builders' style
GUIDs at clone styles held at stock sizes — `MessageHeaderHtml` (0x5c4b0914)
and `MessageBodyHtml` (0x5c4b0915) — which every FontStyle tier file carries.
**Those clones must stay at stock sizes at every tier**, precisely because
their only job is to feed a correct index into a table that is already scaled.

**3. Re-calibrate the Credits LTEXT size maps.**
The Credits window's per-factor size bumps predate the table patch and would
compound against the now-scaled tables, so they are recalibrated rather than
left in place.

## Related engine fact

`GZWinBMP`-family windows draw with `dst = src size`. Supplying 2x art
therefore scales the draw with no code hook at all. The corollary is a useful
diagnostic: a 2x `imagerect` over a 1x bitmap draws only the corner that
actually exists, which is the signature of an art override being shadowed by a
lower-priority 1x source.
