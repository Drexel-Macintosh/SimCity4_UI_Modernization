# Item Icons 2x Override — Build Report (2026-07-22)

Self-contained package that supplies **2x versions of the exemplar-bound toolbar picker /
flyout item icons** at their original TGIs, so those icons stop rendering 1x inside doubled
button slots. Advances the city-interior 2x work. Companion research:
`tools/research/ITEMICONS.md`.

## What was built

`tools/itemicons/z_SC4UIScale_ItemIcons.dat`

| Field | Value |
|---|---|
| Entries (icons) | **266** |
| Type / Group (all) | `0x856DDBAC` / `0x6A386D26` |
| DBPF / index | 1.0 / 7.0, no DIR (all uncompressed) |
| File size | **3,484,798 bytes** (~3.32 MB) |
| Index | 266 entries @ 0x3517B6 (5,320 bytes) |
| Art geometry | every PNG **352x88** = four 88x88 four-state cells (2x of the stock 176x44) |

## Derivation of the 266 (not guessed — reproduced from the game data)

Per `ITEMICONS.md`, the Item Icon TGI is assembled in the exe as
`{type 0x856DDBAC, group 0x6A386D26, instance = <property 0x8A2602B8 value>}`; only the
instance lives in the exemplar.

1. Extracted all exemplars (type `0x6534284A`) from the read-only game
   `SimCity_1.dat` with `tools/dbpf/DbpfExtract.exe` -> **8,957** binary EQZB exemplars,
   0 failures.
2. Parsed the binary EQZB format (`parse_exemplars.py`, following the .md appendix) and
   read property **`0x8A2602B8` (Item Icon)**:
   - 8,957 / 8,957 parsed cleanly (matches the .md)
   - **278** exemplars carry `0x8A2602B8` (matches the .md)
   - **266 distinct** instance values (matches the .md)
3. For each of the 266, the override TGI = `{0x856DDBAC, 0x6A386D26, <instance>}`; the 2x
   art was taken from `tools/upscale/preview/SimCity_1/`
   (`T-0x856ddbac_G-0x6a386d26_I-0x<inst8>.png`, lowercase). **266 / 266 present**, all 352x88.

This is the entire ItemIcon pool that populates the left-toolbar menu tree (zoning,
utilities, transport, parks, rewards, water, power, education, health, safety pickers).
The group `0x6A386D26` PNG pool holds 356 images; only these 266 are actually bound as
Item Icons, so shipping exactly 266 (not all 356) is correct.

## Staged / excluded

| Result | Count |
|---|---|
| Staged into the .dat | **266** |
| Excluded | **0** |
| Missing 2x preview art | **0** |

No icon had to be excluded. Every distinct Item Icon instance had matching 2x art and
passed all collision guards below.

## Collision / coexistence checks (all clean)

This dat is an **in-place override at the original TGI** (the same selective-safe
"exclusive / 2x-in-place" mechanism), valid here because item-icon art in group
`0x6A386D26` is exemplar-bound and not shared with any unscaled `.UI` context.

- **refmap collision guard** — `tools/selective-safe/refmap.csv` contains **0** references
  in group `0x6A386D26` (the 431 `.UI`-referenced PNGs live in groups 0x46A006B0 /
  0x1ABE787D / 0x22DEC92D / 0x00000001 / 0x4C06F888 / 0x82B9B75B). No item icon is
  referenced by an unscaled `.UI` file, so none needed cloning or exclusion.
- **Full-TGI-set overlap** (index-parsed from each packed .dat):
  - `ItemIcons` vs `z_SC4UIScale_SelectiveArt.dat` (214 entries): **0 overlap**
  - `ItemIcons` vs `z_SC4UIScale_DialogStatic.dat` (37 entries): **0 overlap**
  - The other two dats use only groups 0x46A006B0 / 0x1ABE787D / 0x96A006B0 / 0x08000600;
    none touch 0x6A386D26. Overlap is structurally impossible by group and confirmed 0
    entry-for-entry.

The three dats coexist with **zero TGI collisions**.

## DLL follow-up needed (recommendation only — src/ NOT edited)

To actually surface these 2x icons, the two exemplar-icon flyout columns must be allowed to
scale. In `src/UiSpike.cpp`, `kNeverScaleIds` (~line 70) currently pins them at 1x:

    const uint32_t kNeverScaleIds[] = {
        0x69923479, // zoning flyout column    <-- REMOVE (icons now 2x)
        0xE992F711, // utilities flyout column <-- REMOVE (icons now 2x)
        0x698894D3, // My Sims strip            <-- KEEP
    };

- **Remove `0x69923479` and `0xE992F711`** so the zoning and utilities flyout columns
  scale; with this dat in Plugins, their item slots double and the icons now fill them at 2x.
- **Keep `0x698894D3` (My Sims strip).** Per `ITEMICONS.md` Q3 this cannot be fixed by data
  alone — it needs the portrait slot-pitch constant (~135px) doubled in code plus 2x
  portrait art; a wider container alone just tiles MORE 1x portraits.
- After removing the two ids, table-re-test the zoning and utilities pickers open.

Deployment is the user's responsibility; this dat was NOT copied into any game folder, and
`dist/SC4TouchControls-v1.0.4/` was not touched.

## Package contents (`tools/itemicons/`)

- `z_SC4UIScale_ItemIcons.dat` — the override (266 icons)
- `stage/` — the 266 staged 2x PNGs (package inputs, TGI-named)
- `parse_exemplars.py` — EQZB exemplar parser (Item Icon enumeration)
- `stage_icons.py` — preview lookup + collision guard + staging
- `_work/item_icons.csv`, `_work/item_icons_distinct.txt` — the derived 278 occurrences /
  266 distinct instance list (derivation evidence)
- `REPORT.md` — this file

Rebuild: re-extract exemplars from the read-only game `SimCity_1.dat` via
`tools/dbpf/DbpfExtract.exe <dat> _work/exemplars 0x6534284A`, then
`python parse_exemplars.py _work/exemplars _work/item_icons.csv`, then
`python stage_icons.py`, then `../dbpf/DbpfPack.exe stage z_SC4UIScale_ItemIcons.dat`.

## 2026-07-29 extension — submenus-mod icons (266 -> 321)

The memo.submenus-dll 2.1.0 package (`Plugins\150-mods\memo.submenus-dll.2.1.0.sc4pac`)
binds **55 Item Icon instances of its own** (property 0x8A2602B8 in its dats' exemplars;
55 of 56 exemplars distinct). Un-overridden they render DUPLICATED in the doubled cells:
the game slices the 4-state strip by the 2x 88px cell, so a 1x 176x44 resource shows two
stock states per cell. All 55 sources ship in the package's own dats (176x44, group
0x6A386D26) — none among the stock 266.

Recipe (repeat for any future submenu pack that adds icons):
1. `DbpfExtract.exe` every dat in the package (+ submenu-essentials.dat).
2. Parse exemplars with `parse_exemplars.py`; collect 0x8A2602B8 instances not already
   in the shipped dat.
3. Collect their 1x PNGs -> `_work/submenus-1x/` (canonical 0x names).
4. `Upscale2x.exe _work/submenus-1x _work/submenus-2x` (default NN factor 2 = the
   preview-set method). All outputs must be 352x88.
5. Combine `stage/` (266) + `_work/submenus-2x/` (55) -> `_work/pack-321/`,
   `DbpfPack.exe _work/pack-321 z_SC4UIScale_ItemIcons-2x.dat` -> **321 entries**.
6. Deploy to Plugins root; bump the count in `_tests\Test-DatIntegrity.ps1`.

Built + deployed 2026-07-29 (md5 ce9dcdece2862a6bc5bc6b0c86f8bd2b), DatIntegrity green.

### 2026-07-29 correction — the 321 root dat DID NOT WORK; zzz subfolder package

Deployed 321-in-root and the icons stayed duplicated. **Load-order law (proven live):
within Documents Plugins, root FILES load BEFORE subfolders**, so a root dat can never
override the mod's `150-mods\` dats. Final layout:

- `Plugins\z_SC4UIScale_ItemIcons-2x.dat` — back to **266** (stock pool; overrides
  install-dir resources, which root files DO beat).
- `Plugins\zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat` — the **55** submenus-mod
  icons ("zzz-SC4UIScale" sorts after "150-mods", so it wins under any ordering rule).
  Tier-gated by ScaleTier (v2.17.1) like the root packages.

Step 5-6 of the recipe above therefore change to: pack ONLY `_work/submenus-2x` ->
`z_SC4UIScale_ItemIconsSub-2x.dat`, deploy into `zzz-SC4UIScale\`, expected counts
266 + 55 in `_tests\Test-DatIntegrity.ps1`.

### 2026-07-29 landmarks pass — zzz package 55 -> 124

"Build Landmarks" (and other menus) still showed duplicated icons for NON-submenu items.
Cause: more plugins bind their own Item Icons. Full sweep of every Documents-plugin dat
(119 dats, exemplar type 0x6534284A) found **74 further un-covered instances**:

- CAM System Integration Module (050-load-first): 73 (Submenu_Extended + DLC/Maxis
  landmark buildings). **GOTCHA: ~half of CAM's exemplars are TEXT format** — the
  binary-only EQZB parse found just 45 of them; a text-format scan for
  `0x8A2602B8...{0x...}` found the other 30. ALWAYS parse both formats.
- Maxis Buildings landmark plugins: one each (Longfellow Castle, Globe Arena, Grand
  Central, Parthenon, ...).

69/74 had 176x44 source art in their own dats (or the stock pool); upscaled 2x NN and
added to `zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat` -> **124 entries**.
5 instances have NO icon art installed anywhere (0d1d6acb, 2d1e7a9e, 2d217719,
4d50ba18, ed2174a0): the submenus DLL replaces them with its Missing Thumb icon —
pre-existing condition. Note: game dats other than SimCity_1 contain ZERO exemplars,
so the stock 266 remains complete. Sources: `_work/plugins-1x|-2x/`.

## 2026-07-29 tier pass — both packages at every tier (audit A1/A2, v2.24.0)

`stage_icons.py` now takes `--factor` (build_selective_safe.py conventions: tag
derivation, `preview-<tag>` input, tagged refmap/package collision guards, pack
to `tools\packages\<tag>\z_SC4UIScale_ItemIcons-<tag>.dat`; `--factor 2` =
the original stage-only behaviour, bit-identical). NEW `build_itemicons_sub.py
--factor` replicates the pack-sub recipe per tier: the 129 1x sources
(submenus-1x + plugins-1x + lots-icons-1x) upscaled with `Upscale2x.exe
--factor --normalize-names`, plus the Missing Thumb 0x144161EC taken from the
tier's stock preview set, name-set-verified against the shipped `_work/pack-sub`
before packing (so a tier package can never silently diverge from the
user-confirmed 2x contents). Built + deployed GATED (`.x1-disabled`, ScaleTier
flips them): ItemIcons-15x/-3x (266 each), ItemIconsSub-15x/-3x (130 each).
Counts asserted in `_tests\Test-DatIntegrity.ps1`.
