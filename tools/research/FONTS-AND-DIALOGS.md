# SC4 UI Scaling — font resolution (Q1) + transient dialog static-2x (Q2)

Q1 carries the control inventory, the ini cross-reference and the binary
font-resolution mechanism. Q2 carries the static-2x recipe for the
region-screen dialogs and popups.

Binary: `SimCity 4.exe` 1.1.641.0 Steam (x86, 4GB-patched), ImageBase 0x400000;
file offset = VA − 0x400000 (`.text` raw==RVA, per `DYNAMIC-CONTROLS.md`).
All analysis below is read-only; game files are untouched.

> **Style counts depend on which file is being counted.** Stock
> `FontStyle.ini` carries **88** styles, sizes **10..32**. Every generated
> table carries **90**: `make_fontstyle.py`'s `HTML_CLONE_BLOCK` appends
> `MessageHeaderHtml` and `MessageBodyHtml`, which stay at stock size at every
> tier because the game derives its HTML size index from them. Measured on the
> generated files: 2x table 90 styles / **14..64**,
> `packages\15x\FontStyle-15x.ini` 90 / **14..48**,
> `packages\3x\FontStyle-3x.ini` 90 / **14..96**; the 14 floor is the
> never-scaled HTML clone. The generator's own summary line reports
> "88 styles, size range 15..48" because the clones never enter its change
> list — that line counts the styles it scaled, not the styles on disk.

---

## Q1 — Which control uses which style, and what the 2x ini gives it

Controls observed in-game. `.UI` sources: the stock scripts of group **0x96A006B0**,
`T-00000000_G-96a006b0_I-*.ui`. The staged/shipped copies under
`tools\selective-safe\stage\` differ from them ONLY in `imagerect=` doublings,
shared-art clone IIDs and the `font=` GUID conversion below — **areas are identical**,
verified by diff.

### Region screen

| On-screen text | .UI file / line | Control clsid | Window id | font= name | Style GUID | 2x ini line | 2x size (stock) |
|---|---|---|---|---|---|---|---|
| Region name | I-aa920991 line 17 | **0xaa7cecfd** (`cSC4WinText`) | 0xea5bd179 | RegionRegionName | 0xaa8cdfb6 | 210 | 36 (18) |
| "Region" label | I-aa920991 line 21 | GZWinText | (no id) | RegionLabel | 0xaa8cdfb8 | 212 | 30 (15) |
| Region population | I-aa920991 line 25 | GZWinText | 0xc9e41918 | RegionPopulation | 0xaa8cdfb7 | 211 | 26 (13) |
| "Region Legend" title | I-abc0ed33 line 5 | GZWinText | 0x4bb0f5f7 | DataInsetHeader | 0xea909a66 | 147 | 32 (16) |
| Legend items (Highway/Road/…) | I-abc0ed33 lines 6–12 | GZWinText | 0x8bb0f5ff … | DataInsetLegend | 0xea909a67 | 148 | 26 (13) |
| Flyout checkboxes ("Show City Names" etc.) | I-aa920991 lines 56/57/67/68 | GZWinText | (no id) | GenBodyMedium | 0x4a809917 | 164 | 26 (13) |
| Tooltips | (tipres refs) | code-drawn | — | ToolTip / ToolTipTitle | 0xa85f1a83 / 0xe9c86c9d | 252 / 253 | 26 / 28 (13 / 14) |

A name-valued `font=` resolves for `RegionRegionName` and `DataInsetHeader`, whose
text draws at the doubled size straight from the ini. It does not resolve for
`RegionLabel` or `RegionPopulation`: their text draws at stock size until the
attribute carries a GUID. `GenBodyMedium` (0x4a809917) is fetched by code at
VA 0x77993d, so it follows the ini whatever the script says.

### City HUD

| On-screen text | .UI file / line | Control clsid | Window id | font= name | Style GUID | 2x ini line | 2x size (stock) |
|---|---|---|---|---|---|---|---|
| "City Opinion Polls" title | I-4bc906b5 line 18 | GZWinText | (no id) | MayorNeedsHeader | 0x4a835025 | 119 | 32 (16) |
| Poll bar labels (Environment/Health/…) | I-4bc906b5 lines 7–17 | GZWinText | (no id) | MayorNeedsBars | 0x4a835026 | 120 | 32 (16) |
| Funds readout | I-2bc90671 line 12 | GZWinText | 0x09e418fe | MayorFunds | 0x4a835024 | 114 | 26 (13) |
| City population | I-2bc90671 line 8 | GZWinText | 0xc9e41918 | MayorPop | 0x4a835023 | 113 | 26 (13) |
| Date | I-c973b411 line 13 | GZWinText | 0x00000001 | PUckDate (the typo is in BOTH the .UI and the ini, and they match) | 0x4a809912 | 80 | 22 (11) |
| City name | I-c973b411 line 8 | **0xaa7cecfd** (`cSC4WinText`) | 0x00000002 | PuckCity | 0xaa809919 | 79 | 32 (16) |
| RCI "R C I" letters | I-2bc90671 line 16 | GZWinText | (no id) | MayorRCI | 0x4a835021 | 111 | 32 (16) |
| Mayor Rating label | I-2bc90671 line 20 | GZWinText | 0x0a51201d | MayorMRating | 0x4a835022 | 112 | 28 (14) |

`MayorNeedsHeader`, `MayorNeedsBars`, `MayorFunds`, `MayorPop` and `PUckDate` are
plain `GZWinText` nodes carrying a name-valued `font=` that does not resolve; their
text draws at stock size until the attribute carries a GUID. `MayorRCI` and
`MayorMRating` are the same construction. The city name is on the custom class
**0xaa7cecfd**, the same class as the region name.

### Ini integrity

- The `FontStyle.ini` deployed at the install root matches the generated 2x table
  byte for byte.
- All 88 stock `[Font Styles]` lines parse cleanly (field-masked reparse: 88/88,
  no NOPARSE).
- No duplicate style names, no duplicate GUIDs.
- Line formatting does not track resolution: only `MayorRCI` has a trailing space
  after its GUID; every other name-bound line is byte-clean, and the two lines whose
  names resolve are formatted identically to their neighbours (`RegionRegionName`
  0xaa8cdfb6 resolves while its consecutive-GUID siblings 0xaa8cdfb7/b8 two lines
  below do not).
- `MayorNeedsHeader` (does not resolve) and `DataInsetHeader` (resolves) have
  **byte-identical face/size/params** — only name and GUID differ. The style
  DEFINITIONS are not what decides resolution.

### Binary mechanism

All VAs from disassembly of the shipped 1.1.641 exe (capstone, offline).

1. **One parse site only.** "Font Styles" / "Font Aliases" section names are referenced
   exactly once each (0x44de23 / 0x44dd7f), inside the font-init at **0x44db60**.
   No second font table load exists; there is no locale override path in code.
2. **Registration is unconditional.** Per-line callback 0x44d7f0 → 0x44d4d0: every ini
   line is parsed (helper 0x5c11b0), registered with the font system
   (singleton getter **0x913c72**, vtable **+0x18** = RegisterStyle(name, style, 0)), and
   its name→GUID pair is added to a private string dictionary (created at 0x44ddef,
   clsid 0xba2e7954, handed to the font system via **vtable+0x34** before the
   [Font Styles] parse at 0x44de1c). Every line of the deployed table lands in the font
   system at its scaled size.
3. **No code rebinding of the name-bound styles.** A full image scan finds ZERO immediate
   references to 0x4a835021–26, 0x4a809912, 0xaa8cdfb7 and 0xaa8cdfb8.
   The exe DOES fetch other styles by GUID (font system **vtable+0x14** =
   GetStyleByGUID): WindowTitle 0xe2b14587 @0x7eaca5, GenBodyMedium 0x4a809917 @0x77993d,
   GenButton 0x4a809919 @0x77ba93, MessageHeader/Body 0x4a809914/15 @0x52cce7 + 0x762f7e,
   AdvisorHeadline 0xaa0f4ab4 @0x7726b4 (the ticker), LoadScreenTitle 0x4a9c7970
   @0x777931 — **all of these are present and doubled in the ini**, consistent with the
   text that does scale by name.

   The chart and legend styles are three distinct styles rendered by two different
   panels, identified by the GUID each drawing site actually pushes:

   | style | GUID | push site | renderer | 1.5x / 2x / 3x pt (stock) |
   |---|---|---|---|---|
   | `ChartLabel` | `0xE9C86B5E` | **`0x0076DD91`** | the **GRAPHS** chart legend rows | 19 / 26 / 39 (13) |
   | `Legend` | `0xE9C86B5F` | **`0x007A0747`** | the **DATA VIEWS** legend — a different panel entirely | 17 / 24 / 36 (13) |

   `ChartTickText` (`0xE9C86B6E`) is the third style in that ini block: stock 10 pt,
   scaled to 15 / 20 / 30. `make_fontstyle.py`'s `SIZE_SQUEEZE = {"Legend": 0.92}`
   applies to the Data Views legend and to nothing else; the Graphs chart draws
   `ChartLabel` at its unsqueezed size, and the chart's layout is handled by geometry
   (`SC4-UI-ENGINE.md` §5.4.6).
4. **cGZWinText** (clsid token 0x592, ctor 0x9c19c8, object 0x114 bytes, cIGZWinText
   interface at +0xD8, main vtable 0xADFEB8, iface vtable 0xAE0118):
   - iface **+0x4C** (0x9c16fd) = SetFontStyleByGUID: stores the GUID at this+0xE0,
     resolves via GetStyleByGUID(+0x14) with fallback GUID **0x68963c4c ("Default")**.
   - New text windows are constructed bound to Default (creation helper 0x996e90 fetches
     0x68963c4c immediately after instantiation).
   - The .UI deserializer for GZWinText (**0x94e516**, registered at 0x951d29) handles
     `font=` two ways: a dictionary-resolved token value (type 6) → SetFontStyleByGUID;
     a raw string value (type 0x800E) → stored into the window's generic property map
     (property id 0xF000+0xFAA3BE85 = 0xFAA4AE85 via main vtable +0x1C8 = 0x99d7c8,
     which ONLY stores — no font side effect, and **no consumer of property 0xFAA4AE85
     exists anywhere in the image** (zero xrefs to 0xFAA4AE85 and to the inverse
     constant 0x055C417B)).
   - The font system exposes **+0x98** = GetStyleFromName(string); several OTHER control
     deserializers call it (0x94cf0a, 0x94f9e4, 0x950657, 0x950c94, 0x959491) — the
     GZWinText handler 0x94e516 does NOT.
5. **None of the 88 style names exist as strings in the exe** (scan: DataInsetHeader,
   RegionLabel, MayorNeedsBars, etc. — 0 hits), so name resolution can only go
   through the ini-fed dictionary of fact 2.

### Name resolution, and why the GUID form is the shipping rule

The controls whose text stays at stock size are plain GZWinText nodes bound by
`font=<name>`; their styles are registered at the scaled size and never fetched by
code, the GZWinText deserializer honours only a token-resolved (GUID-valued) font
attribute, and the string form dead-ends in a property nothing reads. The tokenizer
dictionary contains zero FontStyle style names, so no style name resolves through the
token path. The `<LEGACY>` tag handler is not in this path either: 0x94b995 is the
tag's registration site inside the 14-entry tag table, not a handler
(`SDK-GAPS.md` §5). Control class is not the discriminator either — `DataInsetHeader`
(×5) and `RegionLabel` (×1) are both on plain GZWinText. The custom SC4 text class
**0xaa7cecfd** (the two texts with ids 0xea5bd179 / 0x00000002) resolves through the
same GZWinText font code with only the painter swapped (`SDK-GAPS.md` §8.1); its font
renders at the scaled size in the same .UI file where GZWinText names do not resolve.

A GUID-valued `font=` resolves for every style, which is why both builders emit `font=`
in that form.

### The GUID rule in the shipped scripts

The GUID path runs end-to-end: deserializer type-6 token → SetFontStyleByGUID →
GetStyleByGUID → scaled ini style. The round-trip serializer at 0x95bc5f writes
`font=0x%08x` for styles without a resolvable name, so the parser accepts the
hex-GUID form, and that form is confirmed loading in-game.

In the shipped copy of `T-0x00000000_G-0x96a006b0_I-0xaa920991.ui`:

- line 21: `font=0xaa8cdfb8`  (RegionLabel)
- line 25: `font=0xaa8cdfb7`  (RegionPopulation)

Both are packed into `z_SC4UIScale_SelectiveArt.dat`. This binds the styles by GUID at
window creation, bypassing name resolution entirely, and the scaled ini then takes effect.
The same conversion covers the city HUD scripts (I-2bc90671, I-4bc906b5, I-c973b411 —
and their G-08000600 twins). Both builders convert every `font=NAME` to its GUID hex
literal, anchored on a leading letter so the numeric `font=4888` / `font=0x00001318`
tokens are left alone (`SDK-GAPS.md` §5).

---

## Q2 — "Load Region" dialog (0x4A5BA0E7) + region city-info bubble: static 2x recipe

Runtime docking of the region-screen dialog roots is off by default in
`src\UiSpike.cpp` (`DialogDockTick` over `kRegionDialogDocks` — Load Region
0x4A5BA0E7, Create Region 0xEA5BA0D1, Delete Region 0x6A5BA20C, Play Options
0x2A57DB82, Audio Options 0xEA53F5DB, Graphic Options 0x2A57CB82 — runs only with
`[UiSpike] DockDialogs=1`). These dialogs carry game-generated scrolling lists,
slider and radio-grid controls and content the game re-lays-out every frame, so
tree-scaling them at runtime fights the game's own per-frame layout. They are scaled
statically instead, by `tools\dialog-static\build_dialog_static.py` into
`z_SC4UIScale_DialogStatic`, which serves eleven region-screen dialogs and popups.

### Load Region dialog — `T-00000000_G-96a006b0_I-8a5ab1cc.ui` (root id 0x4a5ba0e7)

**Geometry is fully `area=`-driven, which is what makes the static 2x edit work.**
Key lines:
- L2 root: `clsid=GZWinGen id=0x4a5ba0e7 area=(171,103,501,291) image={46a006b0,144161ee}
  blttype=edge` — 330x188 dialog, 9-slice frame art **144161ee** (180x180, edge-blt).
- L4 title-bar BMP: `area=(14,6,314,34) image={1abe787d,144161e4} imagerect=(12,12,78,78)
  edgeimage=yes` — frame art **144161e4** (78x78) from mirror group **1abe787d**.
- L6 title text: `font=GenHeader caption="Load Region"`.
- L8 list frame: `image={1abe787d,144161ee} imagerect=(12,35,180,180) edgeimage=yes`.
- L10 list box: `clsid=GZWinListBox id=0x00001000 area=(0,0,310,114) font=GenBodyMedium`.
- Buttons OK/Cancel follow the same `area=`-driven pattern.

**The recipe:** double every `area=` and `imagerect=` tuple in I-8a5ab1cc.ui exactly as
the selective-safe builder does for panels (the root becomes area=(342,206,1002,582),
i.e. 660x376; children ×2), ship the edited .UI at its original TGI in the override dat,
and let the game centre/anchor the now-2x dialog itself — GZWinGen roots are positioned
by the game's dialog-open code, not from a fixed on-screen origin, which is the same
reason the runtime docker had to MOVE it.

**Art for the dialog:** 144161ee (180x180) and 144161e4 (78x78) are the shared 9-slice
dialog frames used by 59+ scripts. They are edge-blt frames whose slice geometry is
runtime-derived, so a doubled window over unchanged source art draws its borders at
source thickness. The builder isolates the doubled art behind a new IID via the
CLONE_XOR 0x53430001 mechanism (falling back to 0x53430002 on collision) and retargets
this dialog's refs at the clone, so the 59-script shared sheet is untouched. The 9-slice
cell arithmetic (`cell = (r/3 − l, b/3 − t)`, never an inset, so 2x art doubles all four
`imagerect` numbers) is in `SDK-GAPS.md` §2.1.

### Region city-info bubble

The bubble with a tail pointing at the clicked tile is the window `0x0A551C50`, a child
of the full-screen map layer `0x2BA6BB97` (`cSC4WinRegionView`). It is not code-drawn:
it comes from two `.UI` scripts selected in code at click time — `I-ca539340` (existing
city, 258x250) and `I-0a8cd184` (start new city, 216x165) — with a narrow stub variant
`I-ca539343` under a third id, `0x0A551C53`. The tail anchor is dynamic (position from
the game, size from the script), and the whole subtree is served by dialog-static at 2x,
every live rect exactly 2x its staged script. Because it hangs under a full-screen
layer, the runtime sweep cannot reach it; the static dat is its only lever. Full
architecture, child map and the Mayor Rating bar decode: `SDK-GAPS.md` §10 and §8.3.

### Q2 summary

- **Load Region dialog: static 2x** — pure `area=`/`imagerect=` geometry, the game
  self-centres a GZWinGen root, and the shared dialog frame is doubled behind an
  isolated clone IID.
- **City-info bubble: static .UI (dialog-static), not code-drawn** — two scripts under
  one window id, served at 2x, out of the runtime sweep's reach by construction.
