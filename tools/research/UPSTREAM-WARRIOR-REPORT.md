# Upstream note — warrior, "God Terraforming in Mayor Mode" 1.0

**Status: FYI only. No defect in this mod.** We ship a compatibility layer
for it; the author needs to do nothing. Written 2026-08-02 per our standing
order: whenever we override another mod's data, we record it and prepare a
developer-facing callout.

## What the mod does (as measured, not assumed)

`warrior.god-terraforming-in-mayor-mode.1.0.sc4pac` ships three dats:

| file | contents |
|---|---|
| `UI_Compact.dat` | replaces the mayor **Landscape flyout** script `{0, 0x96A006B0, 0x09923283}` — 14 elements, root 178x273, window id `0x49923239` — plus its own copy of art `{0x46A006B0, 0x14215E27}` |
| `Mayor_Sign_Menu.dat` | replaces the **Signs & Labels** column script `{0, 0x96A006B0, 0xCB95403E}` — 8 elements, root 224x95, window id `0xAB954023` — plus its own copy of art `{0x46A006B0, 0xEB7C4D3B}` |
| `Locales.dat` | 12 LTEXT string pairs (untouched by us) |

Both replacement scripts are **correctly authored**: each carries the
`0x0000AAAA` hidden alignment-marker child that SC4's flyout docking reads,
sized to match its spawn button. Nothing here is a bug.

## Why it interacts with our project

`SC4UIScale.dll` renders SimCity 4's UI at 2x (or 1.5x/3x) on
high-resolution displays. Part of that is shipping doubled copies of stock
`.UI` scripts and art. SC4's load order puts **root `Plugins` files before
subfolders**, so a mod in `Plugins\150-mods\` legitimately outranks our root
packages. With this mod installed, its 1x scripts and 1x art won over our 2x
copies, which showed up on our side as:

- the terraform ring docking against **stock** geometry (visibly undocked),
- the green tool strips drawing at 1x inside correctly-doubled windows.

**Both symptoms are ours, not the mod's.** With our layer disabled the mod
renders exactly as intended.

## What we did

We build 2x/1.5x/3x copies of **this mod's own scripts and bitmaps** (never
the stock ones — that would revert the mod's compact layout) and ship them
from `Plugins\zzz-SC4UIScale\`, which sorts after `150-mods\`. The
transformation is the same one we apply to the stock versions: window
`area=` is left alone (our runtime scaler handles geometry), `imagerect=`
is scaled with the art, and font names are converted to the GUID form our
2x FontStyle uses.

The package is **gated on this mod's presence and exact file
fingerprints** (`UI_Compact.dat` 8702 bytes, `Mayor_Sign_Menu.dat` 5766
bytes). If the mod is removed, or updated to a version whose rects differ,
our copy disables itself automatically and the game falls back to stock
handling — we never leave a frozen copy of someone else's UI on screen.

## The only thing that would help us

If a future release changes either script's geometry, our fingerprint check
will disable our copy (safe, but the flyouts lose 2x until we rebuild). A
heads-up on UI-layout changes — or a version-stamped resource we could key
on instead of file size — would let us keep up without guessing. Entirely
optional.

Contact: this is a personal high-DPI project (SC4UIScale); no redistribution
of your files is involved — our package contains derived, upscaled copies
only, and only functions while your mod is installed.
