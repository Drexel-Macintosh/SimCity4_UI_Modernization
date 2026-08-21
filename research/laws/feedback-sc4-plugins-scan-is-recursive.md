# SC4 Scans the Plugins Tree Recursively

SimCity 4 loads `Plugins\` recursively — every subfolder, at any depth. A
"stash" or "disabled" folder created *inside* `Plugins\` disables nothing; its
contents keep loading exactly as before, including `.dat` archives, DLL plugins,
and SC4Lot/SC4Model/SC4Desc content.

There are only two ways to take a plugin out of play:

1. **Rename the extension** — `foo.dat` to `foo.dat.disabled`. The scan matches
   on extension, so a renamed file is skipped in place.
2. **Move it out of the Plugins tree entirely** — to a *sibling* of `Plugins`,
   for example `Documents\SimCity 4\_stock-stash\`, never to a child of it.

## Verifying a "stock" baseline

Any claim that the game is running stock must be backed by a recursive
enumeration, not a top-level directory listing. A shallow `Get-ChildItem` on
`Plugins\` reports an empty folder while a nested stash directory beneath it is
still fully live, so the listing looks like proof and is not.

The positive control is: enumerate `*.dat`, `*.dll`, and `*.sc4*` **recursively**
under **both** Plugins trees — `Documents\SimCity 4\Plugins` and
`<install>\Plugins` — and require both result sets to be empty. Both trees
matter; the game merges them, and clearing only one leaves the other loading.

## Execution proof beats folder layout

Third-party DLL plugins write their own log files. A fresh timestamp on
`SC4MoreBuildingStyles.log`, `SC4LuaExtensions.log`, or any equivalent
plugin log is direct evidence that the DLL ran during that launch, regardless of
what the folder layout suggests. Installed is not the same as executed, and the
logs are the only cheap way to tell the two apart. When a log timestamp and a
directory listing disagree, the log is the measurement.

Any UI capture or measurement taken while a nested stash was believed to be
"removed" is contaminated and must be retaken against a verified-empty tree.
The same "one more place than you think" trap appears elsewhere in the SC4
install — most notably the multiple `FontStyle.ini` locations that must all be
neutralised before a font-related baseline is trustworthy.
