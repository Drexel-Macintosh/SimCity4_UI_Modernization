# Upstream note — warrior, "God Terraforming in Mayor Mode" 1.0

This mod contains no defect. SC4UIScale ships a compatibility layer for it and
the mod author needs to take no action. The note exists because SC4UIScale
overrides another mod's data, and every such override is recorded with a
developer-facing callout.

## What the mod does

`warrior.god-terraforming-in-mayor-mode.1.0.sc4pac` ships three dats:

| file | contents |
|---|---|
| `UI_Compact.dat` | replaces the mayor **Landscape flyout** script `{0, 0x96A006B0, 0x09923283}` — 14 elements, root 178x273, window id `0x49923239` — plus its own copy of art `{0x46A006B0, 0x14215E27}` |
| `Mayor_Sign_Menu.dat` | replaces the **Signs & Labels** column script `{0, 0x96A006B0, 0xCB95403E}` — 8 elements, root 224x95, window id `0xAB954023` — plus its own copy of art `{0x46A006B0, 0xEB7C4D3B}` |
| `Locales.dat` | 12 LTEXT string pairs, left untouched by the compatibility layer |

Both replacement scripts are correctly authored: each carries the
`0x0000AAAA` hidden alignment-marker child that SC4's flyout docking reads,
sized to match its spawn button.

## Why it interacts with SC4UIScale

`SC4UIScale.dll` renders SimCity 4's UI at 2x (or 1.5x/3x) on
high-resolution displays. Part of that is shipping doubled copies of stock
`.UI` scripts and art. SC4's load order puts root `Plugins` files before
subfolders, so a mod in `Plugins\150-mods\` outranks the SC4UIScale root
packages. With this mod installed, its 1x scripts and 1x art win over the 2x
copies, producing two symptoms in the scaled UI:

- the terraform ring docks against stock geometry and sits visibly undocked,
- the green tool strips draw at 1x inside correctly-doubled windows.

Both symptoms belong to the scaling layer, not to the mod. With the scaling
layer disabled the mod renders exactly as its author intended.

## The compatibility layer

SC4UIScale builds 2x/1.5x/3x copies of this mod's own scripts and bitmaps —
never the stock ones, which would revert the mod's compact layout — and ships
them from `Plugins\zzz-SC4UIScale\`, which sorts after `150-mods\`. The
transformation matches the one applied to the stock versions: window `area=`
is left alone because the runtime scaler handles geometry, `imagerect=` is
scaled with the art, and font names are converted to the GUID form the 2x
FontStyle uses.

The package is gated on this mod's presence and exact file fingerprints
(`UI_Compact.dat` 8702 bytes, `Mayor_Sign_Menu.dat` 5766 bytes). If the mod
is removed, or updated to a version whose rects differ, the derived copy
disables itself automatically and the game falls back to stock handling, so a
frozen copy of another author's UI never stays on screen.

## Keeping the layer current

If a future release changes either script's geometry, the fingerprint check
disables the derived copy — safe, but the flyouts lose 2x until the layer is
rebuilt. A heads-up on UI-layout changes, or a version-stamped resource to key
on instead of file size, keeps the layer current without guessing. It is
entirely optional.

SC4UIScale is a high-DPI project and redistributes none of the mod's files:
the compatibility package contains derived, upscaled copies only, and
functions only while the mod itself is installed.
