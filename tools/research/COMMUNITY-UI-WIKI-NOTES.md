# Community `.UI` article — vetted deltas for our open unknowns

**Source:** "UI", SC4D Encyclopaedia (https://wiki.sc4devotion.com/index.php?title=UI,
last edited 2019-08-08, itself copied from SimsWiki; CC Attribution). Captured
2026-08-23. The page flags itself as *not reviewed for technical accuracy* — treat
every line as a LEAD, never a fact. Nothing here enters `SC4-UI-ENGINE.md` without
byte verification, per the standing rule.

## ⚠ Where the wiki is measurably WRONG (do not import)

- It gives `area=` and `imagerect=` as `(x,y,width,height)`. **Refuted by our own
  measurement**: both are corner form `(l,t,r,b)` — see `SC4-UI-ENGINE.md`
  (button-row and `14015545` proofs). This is the reference case for why this page
  is a leads file.
- It spells the button tip-offset attribute **`tipsoffset`**. **No such token
  exists in the exe** (2026-08-24 tokenizer trace): the real attribute is
  **`tipoffsets`**, GZWinBtn-only. The wiki's own per-control parts list spells it
  correctly — the attribute *table* entry is the typo.
- Its `gutters=` note says the optional second pair is general. **Measured:
  Btn/Grid only** — GZWinText takes a signed byte pair, GZWinTextEdit a dword
  pair, and non-matching arities are silently dropped.

## Deltas that feed open unknowns (research/UNKNOWNS-AND-NEXT-TARGETS.md)

### → #11 Resolution-as-GID — ✅ LEAD CONFIRMED AND CLOSED 2026-08-24
The wiki stated the authoring convention generally: a resolution-specific `.UI` is
shipped with *the screen resolution as its GID*, digits literal (800×600 →
`08000600`). **The exe agrees exactly.** The loader computes it per load:
`sprintf(buf, "0x%.4u%.4u", mainWinW, mainWinH)` (format string `.rdata 0xAD50AC`,
pushed @`0x94B279`) then hex-parses it into the GROUP slot and `TestForKey`s it,
restoring the caller's group on a miss. So the rule is literally *decimal digits
re-read as hex nibbles*, and **arbitrary resolutions are first-class** — the wiki
line was the single most valuable thing on the page. Full chain in the register
(#11) and `SC4-UI-ENGINE.md`. This is the page's win: a community sentence that
predicted a mechanism, and the mechanism was there.

### → B#2 winflag map (the attribute-name side)
Wiki-attested `.UI` flag-attribute names **absent from our measured 13-flag map**:
- `winflag_delayedplot` — the bit exists in our docs (`WinFlag_DelayedPlot`, seen
  in the slot-95 buffer-resolution walk) but we never had its `.UI` attribute name.
- `winflag_premulalpha` — "premultiply alpha for control window". New name, no bit.
- `winflag_container` — listed by the wiki itself as an unknown property.
These three are the expected-name seed list for the register's probe #2 (read the
name→bit table in the attribute dispatch near `0x94B995`/`0x94E516`).

### → #13 gutters / textoffsets / tipoffsets consumers — ✅ CLOSED 2026-08-24
The wiki's semantics were broadly right and are now backed by consumer VAs, with
two corrections (see the WRONG section above: the `tipsoffset` spelling, and the
optional second pair being Btn/Grid-only). Notably the wiki could not have known
the load-bearing part: **`tipoffsets` is inert on stock art**, because its only
consumer gates on a `tipflag=` bit whose default leaves it clear. Full field map
and reader VAs in the register (#13) and `SC4-UI-ENGINE.md`.

## Corroborations (already measured on our side)

- Class inventory matches and extends our named set: `GZWinFileBrowser` (= our
  `0x9AEDEF7C` image file browser, closed 2026-08-23), `GZWinTextTicker` (= the
  `0xAA12F33C` marquee), `GZWinScrollbar2` (attribute set `thumbimage` /
  `containerimage` / `arrowsimage` — candidate match for the generic scrollbar
  family `0x42B7C35x`), plus `GZWinFolders`, `GZWinOptGrp`, `GZWinLineInput`,
  `SC3WinGen`.
- Non-XML quirks (unterminated `<LEGACY>`, `#` comments, unquoted attributes,
  multiple roots) — matches our lenient parser's assumptions exactly.
- `blttype=tiled|normal|edge`, align enumeration (11 tokens incl. `leftbottom`,
  `leftcenter`) — matches our deserializer-verified tokens.

## Breadth we do NOT currently carry (candidate SDK appendix, verify-first)

The wiki tabulates ~150 attributes we have never cataloged (sounds `btnclicksnd`/
`btnupsnd`, the `comments*` pre-tooltip family, per-control "standard parts"
lists, the full style enumeration, grid/treeview/optgrp/filebrowser attribute
sets, `dbgdrawarea`, alternate font colors `colorfont*`). If the SDK reference
ever grows a full attribute appendix, this page is the checklist to verify
against the deserializers — not a table to copy.
