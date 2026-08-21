# Upstream note — the save-warning mod and SC4UIScale

The mod is correct and no defect is reported against it. This note records
exactly which of its data SC4UIScale overrides, why the override is required,
and what would remove the need for it.

## What the mod does

`SaveWarning_Disable_Exit_Quit.dat` (2408 bytes, sc4pac package
`cyclone-boom.save-warning`) replaces two stock `.UI` scripts so the "save on
exit" options are disabled:

| TGI | dialog | what the mod changes |
|---|---|---|
| `{0, 96A006B0, 6A553AA4}` | Exit to Region confirm | first button → `"Option Disabled"`, greyed, `winflag_enable=no`; root 1px taller |
| `{0, 96A006B0, 0A55161D}` | Quit confirm | same, and the body is re-laid to the Exit confirm's 270x162 (stock is 330x157) |

It also ships its own LTEXT captions. SC4UIScale leaves those untouched.

## What SC4UIScale does, and why it is required

SC4UIScale renders the UI at the selected scale factor on high-resolution
displays. Stock dialogs get a pre-scaled copy of their `.UI` script so they are
*born* at the right size — without that, a dialog appears at 1x for a frame or
two and then snaps, which is visible as a flash.

The pre-scaled copies ship from the `Plugins` **root**. SC4 loads root files
**before** subfolders, so a root file can never override one in `150-mods\`.
Without a further override, these two dialogs are the only ones in the game
that still flash.

The cure ships a scaled copy of **the mod's own script** (never the stock one —
that would silently re-enable the very button the mod disables) from
`Plugins\zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-<tier>.dat`, which sorts
after `150-mods\`. Only pixel geometry and the font-name → GUID substitution
change; captions, colours and `winflag_enable=no` are preserved verbatim.

```
mod root  : area=(332,232,602,394)      270x162
2x tier   : area=(664,464,1204,788)     540x324   (exactly 2x, nothing else moved)
```

## The gate — so uninstalling the mod really uninstalls it

A frozen copy of another mod's script is only correct while that script is the
one in play. `ScaleTier` therefore enables the package **only** when
`SaveWarning_Disable_Exit_Quit.dat` is present **and still 2408 bytes**:

- **mod removed** → the package is renamed to `.x1-disabled`, and the stock
  dialog (scaled by the root package) comes back, fully enabled. Removing the
  mod removes the mod.
- **mod updated** → the size check fails, the package disables itself, and the
  dialog falls back to runtime scaling — correct, with the flash back. Nothing
  breaks; the frozen layout is simply no longer assumed.

No file belonging to the mod is ever read, written, renamed or deleted. The
only files renamed are SC4UIScale's own.

## What would make this unnecessary

Nothing on the mod author's side. The override is a consequence of SC4's load
order combined with the decision to pre-scale scripts, and it is carried
entirely on the SC4UIScale side.

When the mod's layout changes, re-extract into
`tools\dialog-static\thirdparty-src\`, update the fingerprint in
`ScaleTier.cpp` (`kThirdPartyDeps`) and rebuild all three tiers. Until then the
gate keeps the stale copy out of the way.

## Related

- `UPSTREAM-BUILDINGSTYLES-REPORT.md` documents the same pattern for the
  36 Slot Building Styles UI.
- `tools\dbpf\who_owns_tgi.py` reproduces the load-order evidence at any time.
