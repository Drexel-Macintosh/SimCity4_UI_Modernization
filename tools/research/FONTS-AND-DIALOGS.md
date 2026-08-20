# SC4 UI Scaling — Font Inconsistency (Q1) + Transient Dialog Static-2x (Q2)

Q1 carries the control inventory, the ini cross-reference and the binary
font-resolution mechanism; Q2 carries the static-2x recipe for the region
transients. The one remaining open mechanism (why some `font=NAME` values
resolve and others do not) is filed in `SDK-GAPS.md` §13 (G10); the
operational rule — ship every `font=` as a GUID hex literal — is unaffected
by it and is what both builders do.

Research date: 2026-07-21. Binary: `SimCity 4.exe` 1.1.641.0 Steam (x86, 4GB-patched),
ImageBase 0x400000; file offset = VA − 0x400000 (`.text` raw==RVA, per DYNAMIC-CONTROLS.md).
Deployed FontStyle.ini at the install root verified **byte-identical** to
`tools\fonts\FontStyle.candidate.ini` (88 styles, all sizes doubled). Game files untouched;
read-only analysis.

> **Note — the two style counts are both right about different things.**
> 88 is the **stock** count
> (`FontStyle.default.ini` — measured). Every **generated** file — `candidate`,
> `packages\15x\FontStyle-15x.ini`, `packages\3x\FontStyle-3x.ini` — carries
> **90**, because `HTML_CLONE_BLOCK` adds `MessageHeaderHtml` +
> `MessageBodyHtml` (landed with the v2.52.x font-package repair). The
> generator still *prints* "88 styles, size range 15..48" because clones never
> enter its change list, so **88/15 is what it printed and 90/14 is what is on
> disk** — both are right about different things, but say which. Measured size
> ranges: **14..48 / 14..64 / 14..96** at 1.5x/2x/3x; the 14 floor is the
> never-scaled HTML clone. `tools\packages\PACKAGES.md:100/:114/:123` has these
> right; `README.md` and `SCALING-AXES.md` quote the stock 88.

---

## Q1 — Which control uses which style, and is it in the deployed 2x ini?

Controls from live screenshots (2026-07-21). `.UI` sources:
`tools\uiscripts\extracted\T-00000000_G-96a006b0_I-*.ui` (the staged/shipped copies in
`tools\selective-safe\stage\` differ ONLY in `imagerect=` doublings and shared-art clone
IIDs — **font attributes and areas are identical**, verified by diff).

### Region screen (TOP PRIORITY)

| On-screen text | .UI file / line | Control clsid | Window id | font= name | Style GUID | In 2x ini? | ini size (was) | Renders |
|---|---|---|---|---|---|---|---|---|
| "Kanto Tokai Region" (region name) | I-aa920991 line 17 | **0xaa7cecfd** (custom SC4 text class) | 0xea5bd179 | RegionRegionName | 0xaa8cdfb6 | YES (line 210) | 36 (18) | **2x — CORRECT** |
| "Region" label | I-aa920991 line 21 | GZWinText | (no id) | RegionLabel | 0xaa8cdfb8 | YES (line 212) | 30 (15) | **1x — BROKEN** |
| Population "0" | I-aa920991 line 25 | GZWinText | 0xc9e41918 | RegionPopulation | 0xaa8cdfb7 | YES (line 211) | 26 (13) | **1x — BROKEN** |
| "Region Legend" title | I-abc0ed33 line 5 | GZWinText | 0x4bb0f5f7 | DataInsetHeader | 0xea909a66 | YES (line 147) | 32 (16) | **2x — CORRECT** |
| Legend items (Highway/Road/…) | I-abc0ed33 lines 6–12 | GZWinText | 0x8bb0f5ff … | DataInsetLegend | 0xea909a67 | YES (line 148) | 26 (13) | not reported |
| Flyout checkboxes ("Show City Names" etc.) | I-aa920991 lines 56/57/67/68 | GZWinText | (no id) | GenBodyMedium | 0x4a809917 | YES (line 164) | 26 (13) | not reported; GUID **is** fetched by code (VA 0x77993d) so expected 2x |
| Tooltips | (tipres refs) | code-drawn | — | ToolTip / ToolTipTitle | 0xa85f1a83 / 0xe9c86c9d | YES (252/253) | 26/28 (13/14) | not reported |

### City HUD (deprioritized per 2026-07-21 direction)

| On-screen text | .UI file / line | Control clsid | Window id | font= name | Style GUID | In 2x ini? | ini size (was) | Renders |
|---|---|---|---|---|---|---|---|---|
| "City Opinion Polls" title | I-4bc906b5 line 18 | GZWinText | (no id) | MayorNeedsHeader | 0x4a835025 | YES (line 119) | 32 (16) | **1x — BROKEN** |
| Poll bar labels (Environment/Health/…) | I-4bc906b5 lines 7–17 | GZWinText | (no id) | MayorNeedsBars | 0x4a835026 | YES (line 120) | 32 (16) | **1x — BROKEN** |
| Funds "$1,000,000" | I-2bc90671 line 12 | GZWinText | 0x09e418fe | MayorFunds | 0x4a835024 | YES (line 114) | 26 (13) | **1x — BROKEN** |
| Population "0" (city) | I-2bc90671 line 8 | GZWinText | 0xc9e41918 | MayorPop | 0x4a835023 | YES (line 113) | 26 (13) | **1x — BROKEN** |
| Date | I-c973b411 line 13 | GZWinText | 0x00000001 | PUckDate (sic — typo is in BOTH .UI and ini, they match) | 0x4a809912 | YES (line 80) | 22 (11) | **1x — BROKEN** |
| City name (for reference) | I-c973b411 line 8 | **0xaa7cecfd** | 0x00000002 | PuckCity | 0xaa809919 | YES (line 79) | 32 (16) | not reported; same class as the WORKING region name |
| RCI "R C I" letters | I-2bc90671 line 16 | GZWinText | (no id) | MayorRCI | 0x4a835021 | YES (line 111) | 32 (16) | presumed broken (same pattern) |
| Mayor Rating label | I-2bc90671 line 20 | GZWinText | 0x0a51201d | MayorMRating | 0x4a835022 | YES (line 112) | 28 (14) | presumed broken (same pattern) |

### Ini integrity — ruled OUT as the cause

- Deployed root `FontStyle.ini` == `FontStyle.candidate.ini` byte-for-byte (diff clean).
- All 88 `[Font Styles]` lines parse cleanly (field-masked reparse: 88/88, no NOPARSE).
- No duplicate style names, no duplicate GUIDs.
- No trailing-junk correlation: only `MayorRCI` has a trailing space after its GUID; every
  other broken line is byte-clean, and the two working lines are formatted identically to
  broken neighbors (`RegionRegionName` 0xaa8cdfb6 works while consecutive-GUID siblings
  0xaa8cdfb7/b8 two lines below fail).
- `MayorNeedsHeader` (BROKEN) and `DataInsetHeader` (WORKS) have **byte-identical
  face/size/params** — only name+GUID differ. The style DEFINITIONS are not the problem.

### Binary mechanism — what is PROVEN so far

All VAs from disassembly of the shipped 1.1.641 exe (capstone, offline).

1. **One parse site only.** "Font Styles" / "Font Aliases" section names are referenced
   exactly once each (0x44de23 / 0x44dd7f), inside the known font-init at **0x44db60**.
   No second font table load exists (no locale override path in code).
2. **Registration is unconditional.** Per-line callback 0x44d7f0 → 0x44d4d0: every ini line
   is parsed (helper 0x5c11b0), registered with the font system
   (singleton getter **0x913c72**, vtable **+0x18** = RegisterStyle(name, style, 0)), and
   its name→GUID pair is added to a private string dictionary (created at 0x44ddef,
   clsid 0xba2e7954, handed to the font system via **vtable+0x34** before the
   [Font Styles] parse at 0x44de1c). All 88 styles land in the table with doubled sizes.
3. **No code rebinding of the broken styles.** A full image scan finds ZERO immediate
   references to the broken GUIDs (0x4a835021–26, 0x4a809912, 0xaa8cdfb7, 0xaa8cdfb8).
   The exe DOES fetch other styles by GUID (font system **vtable+0x14** =
   GetStyleByGUID): WindowTitle 0xe2b14587 @0x7eaca5, GenBodyMedium 0x4a809917 @0x77993d,
   GenButton 0x4a809919 @0x77ba93, MessageHeader/Body 0x4a809914/15 @0x52cce7+0x762f7e,
   ChartLabel/Legend/ChartTickText @0x76d63e/0x76dd8a, AdvisorHeadline 0xaa0f4ab4
   @0x7726b4 (ticker, known), LoadScreenTitle 0x4a9c7970 @0x777931 — **all of these are
   present and doubled in the ini**, consistent with the text that DOES scale.

   > **Correction (2026-08-03, task #57) — the `ChartLabel/Legend/ChartTickText
   > @0x76d63e/0x76dd8a` entry above conflates THREE styles across TWO
   > addresses, and it implies `Legend` is a chart style. It is not.**
   > Byte-verified:
   >
   > | style | GUID | verified push site | who renders it |
   > |---|---|---|---|
   > | `ChartLabel` | `0xE9C86B5E` | **`0x0076DD91`** | the **GRAPHS** chart legend rows |
   > | `Legend` | `0xE9C86B5F` | **`0x007A0747`** | the **DATA VIEWS** legend — a different panel entirely |
   > | `ChartTickText` | `0xE9C86B6E` | unverified — what `0x0076D63E` actually pulls was never re-checked; do not cite it as measured |
   >
   > **Consequence, and it invalidated weeks of reasoning:**
   > `tools\fonts\make_fontstyle.py`'s `SIZE_SQUEEZE = {"Legend": 0.92}` **has
   > never applied to the Graphs chart at all.** The chart renders at
   > `ChartLabel`'s raw 20/26/39 pt at 1.5x/2x/3x, never the squeezed
   > 18/24/36. Any note reasoning from "24 pt in the chart" is wrong at the
   > premise. The squeeze is untouched — it is correct for Data Views — and
   > the chart was fixed by geometry instead. See
   > `tools\research\SC4-UI-ENGINE.md` §5.4.6 and the v2.53.0–v2.55.0 entry in
   > `VERSION-HISTORY.txt`.
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
   RegionLabel, MayorNeedsBars, etc. — 0 hits), so working name-resolution can only go
   through the ini-fed dictionary of fact 2.

### The one open mechanism (reference gap)

What is proven: broken controls are plain GZWinText bound by `font=<name>`; their styles
are registered (doubled) and never fetched by code; the GZWinText deserializer only honors
a token-resolved (GUID-valued) font attribute, and the string form dead-ends in an unread
property. What is NOT proven is the tokenizer step that decides which `.UI` font names
resolve to their GUID (making e.g. `DataInsetHeader` work) and which do not (RegionLabel,
RegionPopulation, Mayor*, PUckDate). The `<LEGACY>` tag handler (registration at
0x94b995) has been ruled out — that address is the tag's registration site inside the
14-entry tag table, not a handler (`SDK-GAPS.md` §5). The tokenizer dictionary contains
zero FontStyle style names, so no style name can resolve through the token path; the
"different class" escape is also closed, since `DataInsetHeader` (×5) and `RegionLabel`
(×1) are both on plain GZWinText. This is filed as `SDK-GAPS.md` §13 gap G10. The custom
SC4 text class **0xaa7cecfd** (used by the two texts with ids 0xea5bd179 / 0x00000002)
resolves through the same GZWinText font code with only the painter swapped
(`SDK-GAPS.md` §8.1); its font renders 2x in the same .UI file where GZWinText names fail.

### Region fix — the shipped recipe

The GUID path is proven end-to-end (deserializer type-6 → SetFontStyleByGUID →
GetStyleByGUID → doubled ini style; the round-trip serializer at 0x95bc5f writes
`font=0x%08x` for styles without a resolvable name, so the parser accepts hex-GUID form).
Therefore, in the SHIPPED (staged) copy of `T-0x00000000_G-0x96a006b0_I-0xaa920991.ui`:

- line 21: `font=RegionLabel`      → `font=0xaa8cdfb8`
- line 25: `font=RegionPopulation` → `font=0xaa8cdfb7`

and repack `z_SC4UIScale_SelectiveArt.dat`. This binds the styles by GUID at window
creation, bypassing name resolution entirely; the doubled ini then takes effect. The same
edit pattern extends to the city HUD scripts (I-2bc90671, I-4bc906b5, I-c973b411 — and
their G-08000600 twins). Hex-literal `font=` acceptance is confirmed on the live game —
both builders convert every `font=NAME` to its GUID hex literal, anchored on a leading
letter so the numeric `font=4888` / `font=0x00001318` tokens are left alone
(`SDK-GAPS.md` §5).

---

## Q2 — "Load Region" dialog (0x4A5BA0E7) + region city-info bubble: static 2x recipe

Load Region dialog located and characterized below; the city-info bubble is resolved in
`REGION-SWITCH.md` §0.5 (it is `0x0A551C50`, hanging under the map layer `0x2BA6BB97`,
served by dialog-static on both bubble scripts `I-ca539340`/`I-0a8cd184`). Runtime
context: `src\UiSpike.cpp` scales+docks 0x4A5BA0E7 at runtime via `DialogDockTick`
(kRegionDialogDocks[0], plus 5 sibling dialogs Create/Delete Region, Play/Audio/Graphic
Options at ids 0xEA5BA0D1, 0x6A5BA20C, 0x2A57DB82, 0xEA53F5DB, 0x2A57CB82). The static
approach removes these from runtime scaling.

### Load Region dialog — `T-00000000_G-96a006b0_I-8a5ab1cc.ui` (root id 0x4a5ba0e7)

**Geometry is fully `area=`-driven → STATIC 2x edit is viable.** Key lines:
- L2 root: `clsid=GZWinGen id=0x4a5ba0e7 area=(171,103,501,291) image={46a006b0,144161ee}
  blttype=edge` — 330x188 dialog, 9-slice frame art **144161ee** (180x180, edge-blt).
- L4 title-bar BMP: `area=(14,6,314,34) image={1abe787d,144161e4} imagerect=(12,12,78,78)
  edgeimage=yes` — frame art **144161e4** (78x78) from mirror group **1abe787d**.
- L6 title text: `font=GenHeader caption="Load Region"`.
- L8 list frame: `image={1abe787d,144161ee} imagerect=(12,35,180,180) edgeimage=yes`.
- L10 list box: `clsid=GZWinListBox id=0x00001000 area=(0,0,310,114) font=GenBodyMedium`.
- Buttons OK/Cancel follow the same `area=`-driven pattern.

**Recipe (static 2x, no runtime fight):** double every `area=` and `imagerect=` tuple in
I-8a5ab1cc.ui exactly as the selective-safe builder already does for panels (root becomes
area=(342,206,1002,582) i.e. 660x376; children ×2), ship the edited .UI at its original
TGI in the override dat, and let the game center/anchor the now-2x dialog itself (GZWinGen
roots are positioned by the game's dialog-open code, not by a fixed on-screen origin —
same reason the runtime docker had to MOVE it). Then remove 0x4A5BA0E7 from
kRegionDialogDocks so runtime no longer touches it.

**Art edit set for the dialog:** 144161ee (180x180) and 144161e4 (78x78) are the shared
9-slice dialog frames used by **59+ scripts** (per UISCRIPTS.md §c) — they are edge-blt
frames whose slice geometry is runtime-derived, so at a doubled window with UNCHANGED
source art the borders draw at source thickness (thin relative to the big dialog). Whether
that reads acceptably or needs 2x frame art is an eyes-on judgement (UI-ART-BINDING.md
flags edge-blt-under-2x as verify-in-game). If a global swap is too risky for a 59-script
shared sheet, the builder's CLONE_XOR 0x53430001 mechanism isolates this dialog behind a
new IID. The 9-slice cell arithmetic (`cell = (r/3 − l, b/3 − t)`, never an inset) is in
`SC4-UI-ENGINE.md` §4A.7 and `SDK-GAPS.md` §2.1.

### Region city-info bubble — resolved

The bubble with a tail pointing at the clicked tile is the window `0x0A551C50`, a child
of the full-screen map layer `0x2BA6BB97` (`cSC4WinRegionView`). It is NOT code-drawn:
it comes from two `.UI` scripts selected in code at click time — `I-ca539340` (existing
city, 258x250) and `I-0a8cd184` (start new city, 216x165) — with a narrow stub variant
`I-ca539343` under a third id `0x0A551C53`. The tail anchor is dynamic (position from the
game, size from the script), but the whole subtree is served by dialog-static at 2x and
every live rect is exactly 2x its staged script. Because it hangs under a full-screen
layer, the runtime sweep can never reach it; the static dat is its only lever. Full
architecture, child map and the Mayor Rating bar decode: `REGION-SWITCH.md` §0.5 and
`SDK-GAPS.md` §8.3.

### Q2 bottom line

- **Load Region dialog: STATIC 2x is the right call** — pure `area=`/`imagerect=` geometry,
  game self-centers a GZWinGen root, art is the shared dialog frame (verify edge-blt at 2x).
- **City-info bubble: static .UI (dialog-static), not code-drawn** — two scripts under one
  window id, served at 2x, unreachable by the runtime sweep by construction.
