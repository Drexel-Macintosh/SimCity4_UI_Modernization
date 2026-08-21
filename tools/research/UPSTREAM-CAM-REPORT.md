# Upstream report — broken submenu and graph data in CAM / SIM 4.0.1

Findings from a full offline scan of every installed plugin dat (119) on
SimCity 4 Deluxe 1.1.641 (Steam, Windows 11) running CAM 4.0.1 + Submenus DLL
2.1.0. These are DATA defects in the shipped SIM package, reproducible with no
other mods installed.

## 1. Nine buildings with a null submenu parent (items unreachable in game)

`2 CAM Building\CAM_Police_Fire_Buildings.dat` ships these building exemplars
with **Item Submenu Parent (0xAA1DD399) = {0x00000000}** — a menu id that does
not exist, so with the Submenus DLL installed the items cannot be reached:

| Exemplar name | Group | Instance |
|---|---|---|
| CV9X7_PoliceKiosk_PIMxD | 0x07BDDF1C | 0x5D621FE4 |
| CV24X24_4carLocalPrecinct_PIMxD | 0x07BDDF1C | 0xD1CE0B65 |
| CV32x28_36carLocalPrecinct_PIMxD | 0x07BDDF1C | 0x468FD65F |
| CV40x36_DeluxePrecinct_PIMxD | 0x07BDDF1C | 0xACCCDC74 |
| CV38x48_Jail_PIMxD | 0x07BDDF1C | 0xA2B88DC7 |
| RW64x64_Prison_PIMxD | 0x8A3858D8 | 0x21483528 |
| CV12x14_2engineStationHouse_PIMxD | 0x07BDDF1C | 0x640875EE |
| CV32x32_4engineStationHouse_PIMxD | 0x07BDDF1C | 0xD7C564C4 |
| CV19x15_DeluxeFireStation_PIMxD | 0x07BDDF1C | 0xA3DB5600 |

Suggested fix: point them at the existing submenus (police-small 0x65D88585,
police-large 0x7D6DC8BC, police-deluxe 0x8157CA0E) or at the physical menu
roots (police 0x37, fire 0x38), or drop the property so occupant-group
auto-categorisation applies.

## 2. One item pointing at an undefined submenu

`CAM_Park_Buildings.dat`: **PZPark3x6x5_Lifeguardtower_1DDD_PIM-Xd**
(G 0x358BADF0, I 0x6387BEB8) has Item Submenu Parent = {0x1C3780E4}; no
installed plugin defines a submenu button with that id.

## 3. Power and Water graphs: a dangling LTEXT id leaves the 4th legend row with no caption

**File:** `1 CAM Core\CAM Locale\` + `CAM_Extended_Graph.dat` (1,117 bytes,
sha256 `5a0dccc2bc564a7638c47fa32ad81825a2128007c3dd5e855c3821eb5eaab02b`)
**Reproduced:** SC4D 1.1.641 + CAM 4.0.1, at every UI scale, on a fresh city.
**On screen:** open **Graphs → Power** (or **Water**). The legend shows four
rows — `Capacity`, `Current Usage`, `Imported`, and a **fourth row with a
working checkbox and a cyan swatch but NO CAPTION**. The series itself is real;
its line draws along y=0 until the city exports.

### The defect

`CAM_Extended_Graph.dat` overrides four chart-definition exemplars in
T=`0x6534284A` G=`0xCA4AD545` (`I=6` Power, `I=7` Water, `I=0A` Garbage,
`I=0E` Demands). Stock Power/Water declare **two** series; CAM declares four.

Decoding CAM's `I=6` (Power), the two parallel arrays are:

```
0x6A4AEE40  (data ids)   n=4   AA11F7CE  AA11F7D2  AA11F837  AA11F83A
0x6A4AEEDC  (label LTEXTs) n=4 0A5D2E9D  0A5D2E9E  FF5D2E9E  FF5D2E9F
                                Capacity  CurrentUsage Imported   ???
```

**`0xFF5D2E9F` does not exist.** An index of **118,896 records across 107 DBPF
files** (all nine install archives plus both Plugins trees) returns zero hits.
Positive controls in the same scan — `0x0A5D2E9D`, `0xFF5D2E98`, `0xFF5D2E9E` —
were each found exactly once, so the scan resolves ids of that form.

Water (`I=7`) carries the identical label array.

### Why it renders as a blank row rather than dropping the row

The row **count** comes from a *different* property (`0x6A4AEE40`) than the
labels (`0x6A4AEEDC`), and the game bounds-checks each array independently
(`0x0076DF79`). With `n=4` on both, index 3 resolves TGI
`{0x2026960B, 0x6A231EAA, 0xFF5D2E9F}`, the lookup fails, and the row is
assigned an **empty string** — full-height row, working checkbox, no caption.

### The valid id for that slot

`0xFF5D2E98` = **`"Exported"`**, which CAM already ships in
`CAM_Locale_en.dat` and uses at the same slot in its own **Garbage** chart.
`…9F` and `…98` differ by a single nibble.

### Related: two CAM legend strings carry a trailing CRLF

`0xFF5D2E97` `"Total Garbage\r\n"` and `0xFF5D2E98` `"Exported\r\n"` both end
in CRLF, which makes those two rows render two lines tall in the Garbage
legend. Stripping the CRLF alongside the id correction keeps a corrected
Power/Water chart from inheriting the double-height row.

### The compatibility resource SC4UIScale ships for this

`Plugins\zzz-SC4UIScale\z_SC4UIScale_CamGraphLabels.dat` — one 20-byte LTEXT at
`{0x2026960B, 0x6A231EAA, 0xFF5D2E9F}` = `"Exported"`, **without** the trailing
CRLF that `0xFF5D2E98` carries. It ADDS the missing resource at the id CAM
already asks for; **CAM's own files are untouched.** The dat becomes redundant
the moment the id is corrected upstream.

## 4. A `.UI` image reference that exists nowhere

Same class as the `0xFF5D2E9F` label above.

`CAM_Extended_Essentials.dat`, script `{0x00000000, 0x96A006B0, 0x12121205}`
(the school / civic query panel) contains:

```
<LEGACY clsid=GZWinBMP area=(15,242,48,275) image={46a006b0,b5cfffff}
        imagerect=(0,0,33,33) transparentbkg=yes ... >
```

**`{0x46A006B0, 0xB5CFFFFF}` is not supplied by anything.** Two independent
scanners agree, with a positive control in the same run:

| instrument | scope | result |
|---|---|---|
| `tools/dbpf/who_owns_tgi.py` | 9 game archives **+ the entire Plugins tree** | NO HOLDER FOUND |
| `tools/dbpf/find_tgi.py` | 9 game archives, any type | not present |
| positive control, same run | the 12 image refs of `9b868f68` | resolved to 17 holders |

Consequence in game: that 33x33 slot draws nothing. It is cosmetic — the window
is `transparentbkg=yes`, so there is no visible artefact, just an empty space
where an icon belongs.

Suggested fix: ship the intended bitmap under that TGI, or drop the `image=`
attribute so the node stops referencing a resource that does not exist.

## The submenu-parent patch (optional override; NOT shipped in releases)

`z_SC4UIScale_MenuFix.dat` is an **optional local override only — SC4UIScale
release bundles do NOT include it**, because rewriting another mod's gameplay
data is a decision for that mod's author, not for this mod. It is documented
here so the defects in §1 and §2 can be fixed at the source; once a CAM/SIM
update fixes the data, the override becomes redundant and can be deleted. If
built locally (`tools/itemicons/build_menu_patches.py`) it produces
`Plugins\zzz-SC4UIScale\z_SC4UIScale_MenuFix.dat` — six Exemplar Patch cohorts
(sc4-resource-loading-hooks format: Cohort 0x05342861, group 0xB03697D1,
targets in 0x0062E78A) that inject corrected 0xAA1DD399 values into the ten
exemplars in §1 and §2.

---

## Informational: CAM replaces nine stock `.UI` scripts

No defect is reported against CAM here. This section records an override of
another mod's data: what it covers, why it exists, and what would make it
unnecessary.

Resolving the real load-order winner per `.UI` TGI shows CAM Core supplies
**nine** stock scripts, **six of them targets the dialog-static builder
doubles**:

| TGI | CAM dat | stock | CAM (the winner) |
|---|---|---|---|
| `{0,96A006B0,CA8CBF0F}` generic 1-button popup | `CAM_Extended_Essentials.dat` | 300x166 | **500x175** |
| `{0,96A006B0,8AA9AA14}` startup splash | `CAM_Intro.dat` | 768x600, 4 nodes | 768x600, **6 nodes** |
| `{0,96A006B0,2A554F6D}` building query | `CAM_Extended_Essentials.dat` | 292x284, 21 nodes | **300x480, 45 nodes** |
| `{0,96A006B0,AA8B999E}` building query | `CAM_Extended_Essentials.dat` | 292x134, 8 nodes | **404x346, 21 nodes** |
| `{0,96A006B0,CA8B8564}` building query | `CAM_Extended_Essentials.dat` | 292x194 @(246,202) | **292x287 @(570,200)** |
| `{0,96A006B0,EA565970}` building query | `CAM_Extended_Essentials.dat` | 292x275, 22 nodes | **304x297, 24 nodes** |

(The other three — `12121201`, `12121205`, `9B868F68` — are CAM's own scripts,
listed for completeness.)

### Why this affects SC4UIScale and not CAM

SC4UIScale pre-scales dialog scripts so they are *born* at the right size on a
high-resolution display. Its copies ship from the `Plugins` **root**, and SC4
loads root files **before** subfolders — so anything in `050-load-first\` wins
over them. Doubling the STOCK version of a script CAM replaces therefore makes
that dialog render CAM's 1x script instead. That is entirely SC4UIScale's
problem: CAM's replacement of those scripts is legitimate.

### What SC4UIScale ships

`Plugins\zzz-SC4UIScale\z_SC4UIScale_CamUI-<tier>.dat` — 2x copies of **CAM's
own** scripts (never the stock ones, which would revert CAM's layouts). Only
pixel geometry and the font-name → GUID substitution change; every caption,
colour and flag is preserved verbatim.

**It is gated on CAM.** `ScaleTier::kThirdPartyDeps` enables the package only
while BOTH `CAM_Extended_Essentials.dat` (2,817,430 bytes) and `CAM_Intro.dat`
(1,001,294 bytes) are present and unchanged. Remove CAM and the package
disables itself, so the stock dialogs come back. Update CAM and the size check
fails, the now-stale copies disable themselves, and the dialogs fall back to
runtime scaling — correct, just with the open flash back.

No CAM file is read for writing, renamed or deleted. The only files renamed are
SC4UIScale's own.

### CAM's three added scripts are scaled too

The three `.UI` scripts CAM **adds** rather than replaces:

| TGI | what it is |
|---|---|
| `{96a006b0,9b868f68}` | city info screen — the Village Hall / Town Hall query, captioned "MZ v1" |
| `{96a006b0,12121201}` | civic query panel |
| `{96a006b0,12121205}` | school query panel |

plus nine of CAM's own bitmaps that the info screen draws. Same package, same
gate, same rules as the six replaced scripts: **CAM's own script is the source,
never the stock lookalike; only pixel geometry and the font-name → GUID
substitution change; no CAM file is read for writing, renamed or deleted.**
Remove CAM and the gate disables these copies — and unlike the six overrides,
these three simply cease to exist, because they are CAM's dialogs.

### What would make this unnecessary

Nothing on CAM's side. If CAM's dialog layouts change, the scripts are
re-extracted from CAM's own dats, the two fingerprints in `src\ScaleTier.cpp`
are updated, and all three tiers are rebuilt. Until then the gate keeps stale
copies out of the way.

Nothing in this section is a request on CAM's side. It is recorded so that if
CAM's layouts change, whoever re-syncs knows exactly which scripts are
mirrored.
