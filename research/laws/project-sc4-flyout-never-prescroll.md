# NEVER pre-scroll a field to fix flyout docking

**Law:** a mis-anchored flyout is NEVER fixed by writing its list's
scroll/first-visible field. The dock arm lands where the *geometry* puts it.
Scroll changes WHICH content is visible under the arm, not where the assembly
sits — and it silently breaks the player's own scrolling and gets reset by
the open flow anyway.

## Evidence — Build Park, 2026-08-22 (three failed attempts in one day)

Symptom: mayor-mode Build Park pill (shared sub-flyout `0x8A6E61E0`, Civic
column parent) attaches its connector at mid-strip; stock attaches 25% down
at row 7 ("Tourist Trap").

1. **Birth write of firstVisible=2** (`[SubFlyout] InitScroll`) — written via
   the Place detour on the outer strip object. The mod-synthesized open flow
   finishes AFTER our detour and resets the field before first paint.
2. **Per-Plot enforcement for 2.5s** — re-stamped it every frame. The value
   then stuck (DSCROLL read back 2), and the screen STILL didn't match
   stock — because scroll was never the defect.
3. User verdict, verbatim: "REVERT… completely incorrect… Make a law to
   never pre-scroll a field."

## What actually fixes this class

The disaster-arc pattern, applied one level up:

- **The dock/ring never moves.** It wraps its button by the game's own law.
- **The strip window (and its icons) shifts inside the container** so the
  correct row meets the connector: `[SubFlyout] StripShiftRows`, design rows
  × 49 px, applied as an absolute per-sweep set against the game's own
  centred `stripTop`.
- Derivation stays at **1×**: count the rows between the game-native attach
  point and the stock attach point (Build Park: native row 3, stock row 7 →
  shift −4). Measure once from the reference, scale by f at use.

## Corollaries

- A birth-time write into a live open flow loses. If a field must be held,
  enforce per-Plot/sweep with an expiry AND a shape guard — but first ask
  whether the field is geometry at all.
- Fields that wobble with hover (`win[0xEC]` = selection index, −1 = none)
  are not scroll. Identify scroll by clicking the arrows while dumping, not
  by assuming addresses across families.
