# Scaling Third-Party UI and the Load-Order Law

SimCity 4 resolves every DBPF resource by TGI, and the last plugin to claim a
TGI in load order wins. Plugins under `Plugins\150-mods\` outrank packages sitting
at the root of `Plugins\`; a `zzz-`-prefixed subfolder outranks everything. Every
consequence below follows from that one rule.

## The load-order law

**A plugin can replace a stock `.UI` script wholesale, and a root-level package can
never win against it.** A scaled copy built from the *stock* script is then dead
data: the game never loads that script, so the panel renders at 1x — or worse,
renders the mod's layout with stock-derived geometry laid over it.

The cure is always the same shape: build the scaled copy from **the mod's own
script**, not the stock one (using the stock script reverts the mod's features),
and ship it from `zzz-SC4UIScale\` so it outranks the mod.

Confirmed instances:

- **CoriBoom's 36 Slot Building Styles UI** replaces the Building Style Control
  script `{0, 0x96A006B0, 0x6BC61F19}` from `150-mods\`. The panel was never
  scaled and rendered corrupted. The derived package scales `imagerect`s and
  retargets shared art to local clones; `area=` is left untouched.
- **The cyclone-boom save-warning mod** replaces both in-city quit/exit confirm
  scripts, `{0, 96A006B0, 6A553AA4}` and `{0, 96A006B0, 0A55161D}`, so the
  root-level dialog copies never won and both dialogs opened at stock 1x. The
  derived package doubles `area=`.
- **warrior's *God Terraforming in Mayor Mode* 1.0** replaces two stock flyout
  scripts — the mayor LANDSCAPE flyout `{0, 96A006B0, 09923283}` (window
  `0x49923239`) and SIGNS & LABELS `{0, 96A006B0, CB95403E}` (window
  `0xAB954023`) — *and* ships its own 1x copies of two art TGIs already shipped at
  2x, `{46A006B0, 14215E27}` and `{46A006B0, EB7C4D3B}`. Its 1x data beat the
  root-level 2x data, which is why the terraform ring came undocked and the green
  strips drew unscaled. Both of the mod's scripts carry the `0x0000AAAA` marker,
  i.e. the mod is correctly authored; the defect was entirely on the scaling side.
- **CAM 4.0.1** replaces nine stock `.UI` scripts, six of which were static-dialog
  targets. Doubled copies of scripts the game never loads shipped for several
  releases (generic popup 300x166 versus CAM's 500x175; the startup splash; four
  building-query panels, one of them growing 21 nodes to 45).

**A mod that replaces a stock `.UI` usually also ships the art that script
references.** Check both. Fixing the script alone leaves 1x art winning, which
reads on screen as a half-fix. The replacement art must be upscaled from **the
mod's** bitmap, never the stock lookalike — the building-styles mod, for example,
ships its own taller 516x654 background.

## Two cheap diagnostics

**If a live rect matches neither the stock script nor the staged copy, a third
file owns that TGI.** A stock-versus-staged diff is structurally blind to it. Run
`python tools\dbpf\who_owns_tgi.py <instance...>`, which prints every holder in
load order and names the winner. In one case the winner differed from stock by a
single pixel (270x162 versus 270x161), which is easy to read as a rounding
artefact rather than a different file.

**If a panel's live window count or root size does not match the stock script
being edited, a plugin has replaced that script.** Grep `Plugins\**\*.dat` for the
TGI before editing anything else.

An override that appears to be ignored is almost never the engine bypassing DBPF
overrides. That conclusion was recorded once and held for days while the real
cause — a third file owning the TGI — went unchecked. Establish who owns the TGI
first.

## Gate every derived package on its owning mod

A copy of another mod's data is only correct while that mod is in play. Left
active after the mod is removed, the copy sits in `zzz-` (which outranks
everything) and **keeps the removed mod's UI alive**: measured with the
building-styles mod deleted, the derived copy (532x640) still beat the stock
script (531x406).

`ScaleTier::kThirdPartyDeps` enables each derived package only while its owning
mod is installed. Lookup is by **file name, searched recursively** — sc4pac folder
names carry the mod version (`cyclone-boom.save-warning.1.0.sc4pac`), so a
hard-coded relative path breaks the moment an uncontrolled mod updates. The search
has a depth-4 budget from `Plugins\` and skips the mod's own subfolder, so a
package can never satisfy its own dependency.

Two gate modes, chosen by what the package hard-codes:

- **Exact name + size**, when the package hard-codes the mod's rects. A mod update
  *must* disable the package: falling back to runtime scaling is correct-with-a-flash,
  while stale geometry is visibly wrong. Current rows:
  `SaveWarning_Disable_Exit_Quit.dat` at 2408 bytes; CAM's
  `CAM_Extended_Essentials.dat` at 2817430 plus `CAM_Intro.dat` at 1001294 (both
  required — the six scripts come from two of CAM's files, so one stale file makes
  the set half stale); warrior's `UI_Compact.dat` at 8702 plus
  `Mayor_Sign_Menu.dat` at 5766. Verify filenames are unique tree-wide, so no
  other mod can satisfy the gate.
- **Presence only, no size check**, when the package supplies art at the mod's own
  TGIs and hard-codes no geometry. A mod update then makes the art merely
  stale-looking, never mis-geometried, and gating on size would disable hundreds of
  good icons on every patch release. Used for the building-styles art (prefix
  match) and for the NAM icons, gated on `NetworkAddonMod_Controller.dat` — a name
  constant across every controller variant and version.

**Look a gate up by package name, never by index.** An index-keyed form was live
briefly and was already wrong: inserting a row mid-table shifted one package from
`[1]` to `[2]` while its call site still read `depOk[1]`, which would have gated
one mod's package on a different mod's presence. A package with no declared
dependency is ungated.

## One package per mod

The builder is multi-group: `thirdparty-ui\<Name>\` plus `thirdparty-art\<Name>\`
build to `z_SC4UIScale_<Name>.dat`. A single shared package would gate every mod's
copy on every other mod's presence.

Adding a mod means, **in the same change**: the new source subfolder, its
`kThirdPartyDeps` row, its deploy lines, and its integrity count/hash rows. A
package that is built but absent from the deploy and integrity scripts rots
silently.

## Derived copies go stale silently

The building-styles package once sat out of the deploy script for four days. The
deployed dat froze at an older clone-reference epoch; once icon classification
moved to 2x-in-place, its radio rows drew as bare grey bars and the panel's header
title bands went empty. Stale and fresh builds were **identical in size**, so only
a DEPLOYED==BUILT hash comparison detects this class — that is what the deployed
hash section of `_tests\Test-DatIntegrity.ps1` is for.

For the same reason, **re-extract a mod's source after any update to that mod**,
or a stale layout ships.

## Patching another mod's data without touching its files

Another mod's dat or DLL is never modified on disk. Corrections ship as surgical
runtime overrides from `Plugins\zzz-SC4UIScale\`, each deletable once fixed
upstream, and each documented for the upstream author.

- **`z_SC4UIScale_MenuFix.dat`** — six exemplar-patch cohorts (resource-loading-hooks
  format: Cohort `0x05342861`, group `0xB03697D1`, targets prop `0x0062E78A`) that
  inject a corrected Item Submenu Parent (`0xAA1DD399`) into ten CAM 4.0.1
  exemplars: nine police/fire buildings shipped with `parent={0x00000000}` — Police
  Kiosk, the precincts, Jail, Prison and three fire stations, all unreachable in
  game — plus the Lifeguard Tower pointing at undefined submenu `0x1C3780E4`.
  Built by `tools\itemicons\build_menu_patches.py`. The unreachable set is found
  by parsing both binary and text exemplars, and should be re-derived after any
  plugin change.
- **`z_SC4UIScale_ItemIconsSub-2x.dat`** — 125 entries of 2x icons owned by other
  mods: 55 from the submenus mod, 69 CAM and Maxis-landmark icons, plus the
  submenus DLL's Missing Thumb `0x144161EC`. That last one is never exemplar-bound,
  so an exemplar-driven scan of the icon pool misses it entirely; five CAM items
  have no icon art anywhere and wear it.
- **`z_SC4UIScale_NamIcons.dat`** — the Network Addon Mod ships 381 ItemIcon strips
  of its own at `{856DDBAC, 6A386D26, *}`, so the transport flyouts are almost
  entirely NAM's. With no 2x copy, each strip is a left-aligned 1x multi-state strip
  inside a doubled cell: the button shows two states side by side, and hovering
  indexes past the end of the art and draws nothing. The copies are upscaled from
  NAM's own bitmaps, never from a stock lookalike.

These are data defects and icon-pool gaps in the upstream mods, not scaling bugs;
they ship as overrides because the goal is a working install.

## Verifying a replaced panel both ways

Toggling the Building Style panel between the mod's 36-slot layout and the stock
four-style-with-previews panel is done by renaming files only, never editing them,
and it **must move the derived `zzz-` package too**, or the local copy of the mod's
script keeps the mod layout alive and the "stock" state is a fiction. The same
holds for the quit/exit confirms.

Note that the 36-slot layout has no style previews at all, where the stock panel
has four 160x77 pictures. That is the mod's design, not a scaling defect.
