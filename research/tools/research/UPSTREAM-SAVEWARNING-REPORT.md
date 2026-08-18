# UPSTREAM NOTE — cyclone-boom "save warning" mod + SC4UIScale

**Status: informational. No bug is being reported against the mod — it does
nothing wrong.** This exists because of our own standing order: every time we
override another mod's data, we write down exactly what we override, why, and
what would make it unnecessary.

## What the mod does

`SaveWarning_Disable_Exit_Quit.dat` (2408 bytes, sc4pac package
`cyclone-boom.save-warning`) replaces two stock `.UI` scripts so the "save on
exit" options are disabled:

| TGI | dialog | what the mod changes |
|---|---|---|
| `{0, 96A006B0, 6A553AA4}` | Exit to Region confirm | first button → `"Option Disabled"`, greyed, `winflag_enable=no`; root 1px taller |
| `{0, 96A006B0, 0A55161D}` | Quit confirm | same, and the body is re-laid to the Exit confirm's 270x162 (stock is 330x157) |

It also ships its own LTEXT captions. **We do not touch those.**

## What we do, and why we have to

SC4UIScale renders the UI at 2x on high-resolution displays. Stock dialogs get a
pre-scaled copy of their `.UI` script so they are *born* at the right size —
without that, a dialog appears at 1x for a frame or two and then snaps, which
is visible as a flash.

Our pre-scaled copies ship from the `Plugins` **root**. SC4 loads root files
**before** subfolders, so a root file can never override one in `150-mods\`.
The result: these two dialogs were the only ones in the game still flashing.

Our fix ships a 2x copy of **this mod's own script** (never the stock one — that
would silently re-enable the very button the mod disables) from
`Plugins\zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-<tier>.dat`, which sorts
after `150-mods\`. Only pixel geometry and the font-name → GUID substitution
change; captions, colours and `winflag_enable=no` are preserved verbatim.

```
mod root : area=(332,232,602,394)      270x162
ours     : area=(664,464,1204,788)     540x324   (exactly 2x, nothing else moved)
```

## The gate — so uninstalling the mod really uninstalls it

A frozen copy of someone else's script is only correct while that script is the
one in play. `ScaleTier` therefore enables our package **only** when
`SaveWarning_Disable_Exit_Quit.dat` is present **and still 2408 bytes**:

- **mod removed** → our package is renamed to `.x1-disabled`, and the stock
  dialog (scaled by our root package) comes back, fully enabled. Removing the
  mod removes the mod.
- **mod updated** → the size check fails, our package disables itself, and the
  dialog falls back to runtime scaling — correct, with the flash back. Nothing
  breaks; we just stop claiming to know its layout.

We never read, write, rename or delete any file belonging to the mod. The only
files we rename are our own.

## What would make this unnecessary

Nothing the mod author needs to do. This is a consequence of SC4's load order
plus our decision to pre-scale scripts, and it is our problem to carry.

If the mod's layout changes, we re-extract `tools\dialog-static\thirdparty-src\`,
update the fingerprint in `ScaleTier.cpp` (`kThirdPartyDeps`) and rebuild all
three tiers. Until then the gate keeps the stale copy out of the way.

## Provenance

- Diagnosed 2026-07-31, task #79c. `_tests\REGRESSION.md` → "QUIT /
  EXIT-TO-REGION CONFIRM"; `VERSION-HISTORY.txt` → v2.38.0.
- Sibling report for the same pattern: `UPSTREAM-BUILDINGSTYLES-REPORT.md`
  (CoriBoom's 36 Slot Building Styles UI, task #44).
- `tools\dbpf\who_owns_tgi.py` reproduces the load-order evidence at any time.
