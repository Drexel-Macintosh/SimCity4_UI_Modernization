# Upstream report — CoriBoom's 36 Slot Building Styles UI (in `allow-more-building-styles-dll` 3.6.1)

This mod contains no defect and its own files are never modified. SC4UIScale
ships a compatibility layer so the panel renders correctly under UI scaling,
and the note exists because SC4UIScale overrides another mod's data: every
such override is recorded with a developer-facing callout.

## Summary

The mod's `.UI` script is a correct 1x layout. The interaction is with
SC4UIScale's 2x scaling stack, and the note below matters to the developer
only if the panel is ever to become resolution-aware.

## What the mod does

`CoriBoom's 36 Slot Building Styles UI - v0.46 Beta HA250411.dat` replaces the
stock Building Style Control layout script **wholesale**:

| | |
|---|---|
| TGI | `{0x00000000, 0x96A006B0, 0x6BC61F19}` (a `.UI` LEGACY layout script) |
| Panel root | `0xABC619D2` |
| Stock script | 1 root, `area=(388,261,919,667)` = 531x406 |
| Mod script | 1 root, `area=(388,49,920,689)` = 532x640, **73 windows** (36 style slots + the DLL's option checkboxes) |
| Ships in | `Plugins\150-mods\null-45.allow-more-building-styles-dll.3.6.1-1.sc4pac\` |

Art it references (all group `0x46A006B0`): `144161EA` (checkbox strip, 47
refs), `144161E9` (5), `14416241` (3), `144161E2` (2), `CBC3C2B9` (2),
`144161E0`, `82B99D9D`, `CBC3C2B8`.

## Why it interacts with SC4UIScale

SC4UIScale doubles the panel's windows at runtime (measured: 73 windows, root
532x640 → 1064x1280) and ships 2x replacement art plus rewritten copies of the
scaled stock scripts. Two of those pieces cannot meet:

1. **Load order.** In SimCity 4, files in the `Plugins` **root** load *before*
   files in **subfolders**, so a root package never overrides a subfolder
   package. The mod's script is in `150-mods\`, so it wins over any root
   package — as it should. A 2x edit of the *stock* script therefore has no
   effect on this panel at all.
2. The mod's script carries native `imagerect=` source rectangles and
   references the original art TGIs, which is correct for 1x. With 2x art
   replacing some of those TGIs in place, and other refs redirected to 2x
   clones only inside the rewritten stock scripts, the game draws 1x source
   rectangles and 1x art into windows that have been doubled.

Symptoms at 2400x1600: checkbox rows overlapping in the compact view; in the
expanded view the style list floating over a pale box with its second column
hidden, and the mod's own option checkboxes stranded over the terrain — all
consistent with background art covering only the top-left quarter of each
doubled window.

## The compatibility layer

`Plugins\zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-2x.dat` — one entry: the
**mod's own script**, taken as the source (never the stock one, which would
revert the 36-slot UI), with two mechanical transformations applied per scale
tier (1.5x / 2x / 3x):

- `imagerect=` scaled on the 3 controls whose art is replaced 2x-in-place
  (`CBC3C2B8`, `CBC3C2B9`);
- 11 art references redirected to SC4UIScale's 2x clone instances
  (`144161E0→470261E1`, `144161E2→470261E3`, `144161E9→470261E8`,
  `14416241→47026240`) so no unscaled dialog elsewhere is disturbed;

plus the usual `font=` name→GUID normalisation.

No geometry (`area=`) is changed — the panel's layout stays exactly as
CoriBoom designed it; only the art sampling follows the art. The folder name
`zzz-` sorts after `150-mods\`. Deleting the file restores stock behaviour
instantly.

## Addendum — the mod's own background art

The mod also ships its own copy of `{0x856DDBAC, 0x46A006B0, 0xCBC3C2B9}` at
**516x654**, taller than the stock 516x396 because 36 style slots need the
room. That copy is also in `150-mods\`, so it shadows the 2x replacement in
exactly the same way the script does. The compatibility layer therefore
upscales **the mod's own bitmap** (never the stock one — different dimensions)
and ships it in the same `zzz-SC4UIScale\` package, 2 entries total. Measured
before and after: the background window `0xEBC619DC` was already correctly
doubled to 1038x1308 while the drawn art covered only a 516x654 corner.

## Two observations the developer may care about

**1. The style PREVIEW pictures are gone.** The stock script draws four
160x77 preview images, one per style — windows `0x0BC61F6D`, `0xCBC3C2B9`,
`0x0BC61F7E`, `0xCBC61F8E` with art `{46A006B0, ABC3E0E5..E8}`, laid out 2x2
at (79,62), (295,62), (79,182), (295,182). The 36-slot replacement script
contains no preview windows and the dat ships none of that art, so the
expanded panel has a large empty pane where the pictures used to be. That is
reasonable — 36 previews would not fit that space — and SC4UIScale does not
reinstate them, which would mean inventing windows the DLL does not manage.
It is noted in case a per-selection preview is ever wanted; the stock art
instances above are still in the game's own dats.

**2. "Change style every" is sized from its rendered caption.** Its three
siblings are fixed 238x18 in the script; this one is 101x16 with
`autosize=no`, yet it measures 263x32 live before the scaler touches it: the
control is resized at runtime to fit its caption. That is fine in itself, but
it means the control is font-dependent while its siblings are not, so at
larger font sizes it grows and they do not, and its radio glyph stops lining
up with theirs. SC4UIScale special-cases it — scaling its position, never its
size. A fixed size, or the same treatment for the sibling rows, would make the
row font-independent.

## For the developer (optional)

Nothing needs fixing for normal 1x play. If resolution-independence is ever
interesting: the only scale-sensitive data in the script is the `imagerect=`
source rectangles, which are tied to the pixel size of the referenced art. A
layout that omits `imagerect` where possible — letting `GZWinBMP` draw at the
source's natural size, or letting `blttype=edge`/`tiled` 9-slice the frame —
survives art replacement at any scale without edits. That is why the rest of
the panel needs no changes from the compatibility layer.

## Keeping the layer current

The derived copy is built from the mod's own script, so a mod update means
re-extracting that script before rebuilding all three tiers; otherwise the
package ships a stale layout. `_tests\Test-DatIntegrity.ps1` confirms the
entry count of the rebuilt package.

The icon-side equivalent of this report is `UPSTREAM-CAM-REPORT.md`.
