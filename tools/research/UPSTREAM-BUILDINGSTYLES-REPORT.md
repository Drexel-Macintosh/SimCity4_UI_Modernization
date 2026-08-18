# Upstream report — CoriBoom's 36 Slot Building Styles UI (in `allow-more-building-styles-dll` 3.6.1)

Written 2026-07-29 by the SC4UIScale project. **Nothing in the mod's own files
was modified.** This documents an override we ship so the panel renders
correctly under UI scaling, per our standing rule: any time we override
another mod's data, it gets written up and called out to the developer.

## Summary

Not a bug in the mod. The mod's `.UI` script is a perfectly good 1x layout.
The interaction is with our 2x UI-scaling stack, and the note below is only
useful to the developer if they ever want the panel to be resolution-aware.

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

## What went wrong on our side

Our scaler doubles the panel's windows at runtime (measured: 73 windows,
root 532x640 → 1064x1280) and ships 2x replacement art plus a rewritten copy
of each scaled script. Two of those pieces could never meet:

1. **Load order.** In SimCity 4, files in the `Plugins` **root** load *before*
   files in **subfolders**, so a root package can never override a subfolder
   package. Our rewritten script sat in a root `z_*.dat`; the mod's script is
   in `150-mods\`, so **the mod's script always won** — as it should. Our 2x
   edit of the *stock* script therefore never took effect at all.
2. The mod's script (correctly, for 1x) carries native `imagerect=` source
   rectangles and references the original art TGIs. Our 2x art had already
   replaced some of those TGIs in place, and other refs had been redirected to
   2x clones only inside *our* rewritten scripts. So the game drew 1x source
   rectangles and 1x art into windows we had doubled.

Reported symptoms at 2400x1600: checkbox rows overlapping in the compact view;
in the expanded view the style list floating over a pale box with its second
column hidden, and the mod's own option checkboxes stranded over the terrain —
all consistent with background art covering only the top-left quarter of each
doubled window.

## What we ship (deletable the moment it is unwanted)

`Plugins\zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-2x.dat` — one entry: the
**mod's own script**, taken as the source (never the stock one, which would
revert the 36-slot UI), with exactly two mechanical transformations applied per
scale tier (1.5x / 2x / 3x):

- `imagerect=` scaled on the 3 controls whose art we replace 2x-in-place
  (`CBC3C2B8`, `CBC3C2B9`);
- 11 art references redirected to our 2x clone instances
  (`144161E0→470261E1`, `144161E2→470261E3`, `144161E9→470261E8`,
  `14416241→47026240`) so no unscaled dialog elsewhere is disturbed;
- plus our usual `font=` name→GUID normalisation.

No geometry (`area=`) is changed — the panel's layout stays exactly as
CoriBoom designed it; only the art sampling follows the art. The folder name
`zzz-` is chosen purely so it sorts after `150-mods\`. Deleting the file
restores stock behaviour instantly.

## Addendum — the mod's own background art

The mod also ships its own copy of `{0x856DDBAC, 0x46A006B0, 0xCBC3C2B9}` at
**516x654**, taller than the stock 516x396 (it needs the room for 36 style
slots). That is entirely reasonable, and it is also in `150-mods\`, so it
shadowed our 2x replacement in exactly the same way the script did. We
therefore upscale **the mod's own bitmap** (never the stock one — different
dimensions) and ship it in the same `zzz-SC4UIScale\` package, 2 entries
total. Measured confirmation before and after: the background window
`0xEBC619DC` was already correctly doubled to 1038x1308 while the drawn art
covered only a 516x654 corner.

## Two observations the developer may care about

**1. The style PREVIEW pictures are gone.** The stock script draws four
160x77 preview images, one per style — windows `0x0BC61F6D`, `0xCBC3C2B9`,
`0x0BC61F7E`, `0xCBC61F8E` with art `{46A006B0, ABC3E0E5..E8}`, laid out 2x2
at (79,62), (295,62), (79,182), (295,182). The 36-slot replacement script
contains no preview windows and the dat ships none of that art, so the
expanded panel has a large empty pane where the pictures used to be. Entirely
understandable (36 previews would not fit that space), and we have not tried
to reinstate them — that would mean inventing windows the DLL does not
manage. Noting it in case a per-selection preview is ever wanted; the stock
art instances above are still in the game's own dats.

**2. "Change style every" is sized from its rendered caption.** Its three
siblings are fixed 238x18 in the script; this one is 101x16 with
`autosize=no`, yet it measured 263x32 live before our scaler touched it —
i.e. something (the DLL, we assume) resizes it to fit the caption. That is
fine in itself, but it means the control is font-dependent while its siblings
are not, so at larger font sizes it grows and they do not, and its radio
glyph stops lining up with theirs. We now special-case it (scale its position,
never its size). A fixed size, or the same treatment for the sibling rows,
would make the row font-independent.

## For the developer (optional, low priority)

Nothing needs fixing for normal 1x play. If resolution-independence is ever
interesting: the only scale-sensitive data in the script is the `imagerect=`
source rectangles, which are tied to the pixel size of the referenced art. A
layout that omits `imagerect` where possible (letting `GZWinBMP` draw at the
source's natural size, or letting `blttype=edge`/`tiled` 9-slice the frame)
survives art replacement at any scale without edits — that is why the rest of
the panel needed no changes from us.

Re-verify after any mod update:
`python tools\selective-safe\build_selective_safe.py --factor 2` (it re-reads
`tools\selective-safe\thirdparty-ui\`), then confirm the entry count in
`_tests\Test-DatIntegrity.ps1`. If the mod's script changes, **re-extract it
into `thirdparty-ui\` first** or we will be shipping a stale layout.

Related: `_tests\REGRESSION.md` → "BUILDING STYLE CONTROL"; the icon-side
equivalent is `UPSTREAM-CAM-REPORT.md`.
