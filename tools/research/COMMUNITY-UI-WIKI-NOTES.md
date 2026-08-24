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

## Deltas that feed open unknowns (research/UNKNOWNS-AND-NEXT-TARGETS.md)

### → #11 Resolution-as-GID
The wiki states the authoring convention generally: a resolution-specific `.UI` is
shipped with *the screen resolution as its GID*, digits literal (800×600 →
`08000600`). Consequence: the encoding rule is **decimal digits read as hex
nibbles**, so the GID for any target resolution is derivable — 2400×1600 →
`0x24001600`, 1024×768 → `0x10240768`. The register's one-test-dat experiment can
be built without first finding the exe's formatter. Open half unchanged: whether
the engine *computes* the current resolution's GID (arbitrary resolutions work) or
consults a fixed set (only 0x08000600 exists in the corpus).

### → B#2 winflag map (the attribute-name side)
Wiki-attested `.UI` flag-attribute names **absent from our measured 13-flag map**:
- `winflag_delayedplot` — the bit exists in our docs (`WinFlag_DelayedPlot`, seen
  in the slot-95 buffer-resolution walk) but we never had its `.UI` attribute name.
- `winflag_premulalpha` — "premultiply alpha for control window". New name, no bit.
- `winflag_container` — listed by the wiki itself as an unknown property.
These three are the expected-name seed list for the register's probe #2 (read the
name→bit table in the attribute dispatch near `0x94B995`/`0x94E516`).

### → #13 gutters / textoffsets / tipsoffset consumers
Wiki-stated intended semantics (consumers still unverified):
- `gutters=` — reserved space around a control, `(hor,vert[,hor1,vert1])`; first
  pair top/left, optional second pair bottom/right, "used for buttons".
  Consistent with our arithmetic proof that gutters ≠ 9-slice inset.
- `textoffsets=` — position offset of the caption text on the control, `(x,y)`.
- `tipsoffset=` — offset the tip text appears at, `(x,y)` (per-control-parts list
  spells it `tipoffsets` on GZWinBtn — the name may vary by deserializer).
This upgrades #13 from "meaning unknown" to "spec stated, consumer VAs unknown".

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
