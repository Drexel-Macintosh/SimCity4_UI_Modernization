# SC4 UI-scaling asset packages (per-factor tiers)

Factor-tagged UI-scaling packages that feed the AutoScale tier system: a screen
resolution picks a factor, and the DLL enables the matching package by its
filename tag.

> **COUNTS REFRESHED 2026-08-03 — but this file is still not the authority.**
> The tables below were re-measured on 2026-08-03 by reading the DBPF index
> entry count (header offset `0x24`) directly out of the staged files in
> `packages\15x\` and `packages\3x\` and out of the 2x build outputs. No build
> was run and nothing was deployed to produce them. **The authority remains
> `_tests\Test-DatIntegrity.ps1`** (its `$EXPECTED` table), which asserts every
> *deployed* package's count and is updated deliberately whenever one changes;
> it agrees with every number below. Treat that script as the source of truth
> and this file as a description of it.
>
> Three things the 2026-07-29 note said that are now WRONG, not merely stale:
>
> - ~~**A tier is EIGHT tagged dats, not two or three.**~~ **CORRECTED 2026-08-16:
>   `ScaleTier::SyncStaticLayers` tier-syncs TEN tagged bases, not eight.**
>   `SelectiveArt`, `DialogStatic`, `ItemIcons`, `ItemIconsSub`, `ThirdPartyUI`,
>   `WarriorUI`, `SaveWarningUI`, `CamUI`, **`NamIcons` (#139)** and
>   **`UncoveredIcons` (#149)** — plus the loose `FontStyle-<tag>.ini`. NINE of the
>   ten ship on every install; **`UncoveredIcons` is the one install-conditional
>   package** — it exists only when this install has third-party icons no package of
>   ours covers, which is why `Test-DatIntegrity.ps1` gives it neither an entry count
>   nor a built-vs-deployed row (`_tests\Test-DatIntegrity.ps1:235`, `:382-390`) and
>   the deploy guards its copy with `Test-Path` (`_tests\Deploy-OnGameClose.ps1:112-113`).
>   Do not read "ten" as "count ten files on a clean machine".
>   **SEVEN** of the ten (`ItemIconsSub`, `ThirdPartyUI`, `WarriorUI`, `SaveWarningUI`,
>   `CamUI`, `NamIcons`, `UncoveredIcons`) deploy into the `zzz-SC4UIScale\` subfolder
>   to beat `150-mods\`; see the LOAD-ORDER LAW in the README. **FIVE** of those seven —
>   `ThirdPartyUI`, `WarriorUI`, `SaveWarningUI`, `CamUI`, `NamIcons` — are *gated* by
>   `ScaleTier` on their upstream mod still being installed, so "NOT FOUND (live or
>   gated)" from the integrity test is correct behaviour when the mod is absent, not a
>   regression. `ItemIconsSub` and `UncoveredIcons` are in `zzz-` but are NOT gated —
>   `UncoveredIcons` deliberately so: it holds only overrides keyed to a third-party
>   TGI, so with the lot gone the entry is inert rather than wrong.
>   Evidence: `src\ScaleTier.cpp:1803-1887` — the ten `SyncDat` calls, of which
>   `:1840`, `:1848`, `:1860`, `:1876`, `:1885` wrap `match` in `DepOkByName`;
>   `src\ScaleTier.cpp:184-241` — `kThirdPartyDeps`, five rows, the NamIcons row keyed
>   on `NetworkAddonMod_Controller.dat` at `:239-240`; `src\ScaleTier.cpp:250-260` —
>   `DepOkByName` returns true for any package with no row, so "no row" means ungated;
>   `src\ScaleTier.cpp:1825-1831` — UncoveredIcons "UNGATED, deliberately".
> - **`ItemIcons` / `ItemIconsSub` are no longer untagged.** They are built at
>   every tier since v2.24.0 (audit finding A1 — as `-2x` only, all ~356+130
>   menu icons silently reverted to 1x inside scaled cells at 1.5x/3x). The
>   only genuinely untagged/always-on packages left are `MenuFix` (6 entries)
>   ~~and `WebText` (3 entries); both are in the README's package table.~~
>   **CORRECTED 2026-08-16 — there are THREE, not two.** `MenuFix` (6 entries),
>   `WebText` (3 entries) and **`CamGraphLabels` (1 entry)**, the last added
>   2026-08-06 for #147 and documented in this file's own last section (line
>   445). Those are precisely the three untagged rows in `$EXPECTED`:
>   `_tests\Test-DatIntegrity.ps1:184` / `:194` / `:289`; every other row
>   carries a `-2x` / `-15x` / `-3x` tag.
>   `_tests\Deploy-OnGameClose.ps1:154` copies
>   `z_SC4UIScale_CamGraphLabels.dat` with no tier suffix and no
>   `.x1-disabled` twin, and `src\` contains **zero** references to it, so it
>   is gated by nothing and is always on. Measured DBPF index count at header
>   offset `0x24` = 1.
>   `MenuFix` and `WebText` are in the README's package table
>   (`README.md:263`, `README.md:267`); **`CamGraphLabels` is NOT, and should
>   be added there** — a package is not done until it is in the manifest.
> - ~~**Entry counts are NOT identical across factors any more.** `SelectiveArt`
>   is **655 / 655 / 651** at 1.5x / 2x / 3x — the project's only deliberate
>   per-tier data split. The four advice-row "X" glyphs stage only under
>   `FACTOR <= 2.0` because the 3x row-reserve constant (165) will not encode
>   in a sign-extended `imm8`; the builder's staging condition and
>   `ApplyAdviceRowScale`'s factor ceiling must agree or the X clips again. See
>   REGRESSION.md, "advice row". Any check that asserts tier-equality of counts
>   is asserting a falsehood.~~
>
>   ⚠ **CORRECTED 2026-08-16 — THE TIER SPLIT IS GONE, AND SO IS THE FACTOR CEILING.**
>   `SelectiveArt` is **655 at every tier** (1.5x / 2x / 3x), and so is every other
>   tier-paired package. #136 (v2.88.0) widened the ENCODING instead of clamping the
>   factor: `CodePatches::ApplyAdviceRowScale` branches on `s`, not on the tier — at
>   `s <= 127` it writes the original 3-byte `sub esi, imm8` at `0x0079388F`, and above
>   it re-encodes the 19-byte window at `0x0079388B` into `lea esi,[eax-imm32]`. So all
>   sixteen advice-row glyphs — including the four "X" (`…53/57/5B/5F`) that used to be
>   dropped at 3x — stage at every tier, and 3x went 651 -> 655.
>   Evidence: `src\CodePatches.cpp:3554-3566` ("THE TIER CEILING IS GONE … the X column
>   scales at EVERY tier", then `const bool xScaled = true;` at `:3565` and
>   `const long glyphX = glyph;` at `:3566`, both unconditional; the narrow/wide branch
>   is `:3577`, sites at `:412`/`:419`), `tools\selective-safe\build_selective_safe.py:523-531`
>   ("the `or FACTOR <= 2.0` tail is GONE" … `if True`), `_tests\Test-DatIntegrity.ps1:215`
>   and `:217` (both `entries = 655`, `# #136: was 651`), and the staged files' own DBPF
>   headers at offset `0x24` reading 655 at all three tiers.
>   See `_tests\REGRESSION.md`, "ADVICE ROW DISMISS X (#136)" (`:6070`) for the decode.
>   ⚠ The coupling is still hard, only its direction changed: if the wide re-encode is ever
>   removed, or logs `advice row wide re-encode REFUSED` (`src\CodePatches.cpp:3652`), the
>   row is left STOCK — and then the builder filter AND the 3x count must go back to 651 in
>   the SAME build, or the budget describes art that did not ship.
>
> **Rebuild all tiers together** — `--factor 2`, `--factor 1.5`, `--factor 3` —
> or the suite fails on mismatched counts, and 1.5x is where rounding bugs hide
> (2x hides them: exact doubling).

Historically each tier was TWO DBPF `.dat` files plus one loose `FontStyle` INI,
all derived from the same three generators used for the shipped 2x set, now
parameterized by a scale factor `N`. It has since grown to eight dats per tier
from FOUR dat builders (`build_selective_safe.py` → SelectiveArt +
ThirdPartyUI + WarriorUI; `build_dialog_static.py` → DialogStatic + CamUI +
SaveWarningUI; `stage_icons.py` → ItemIcons; `build_itemicons_sub.py` →
ItemIconsSub), plus the upscaler and the font generator.

**Building here does not touch a game folder — but these files are no longer
inert.** ⚠ CORRECTED 2026-08-03: this paragraph used to say "nothing here is
deployed to any game folder", and that is now misleading. `packages\15x\` and
`packages\3x\` are the BUILD side of a build→deploy pair:
`_tests\Test-DatIntegrity.ps1` hashes each file here against its deployed twin
in the Plugins tree and FAILS on a mismatch (see its `$BUILT_PAIRS` map, which
names `tools\packages\<tag>\...` as the built-side source for every tagged dat
and font INI). Editing or rebuilding a file here without redeploying turns
that check red; the correct sequence is rebuild → `_tests\Deploy-OnGameClose.ps1`.
The frozen shipped touch product (`dist\SC4TouchControls-v1.0.4\`) remains
untouched by anything here.

## Filename tag convention (the DLL relies on this)

The factor tag goes in the BASE name, immediately before the extension:

| Factor | Tag | Art dat | Dialog dat | Font INI |
|---|---|---|---|---|
| 1.5x | `15x` | `z_SC4UIScale_SelectiveArt-15x.dat` | `z_SC4UIScale_DialogStatic-15x.dat` | `FontStyle-15x.ini` |
| 3x   | `3x`  | `z_SC4UIScale_SelectiveArt-3x.dat`  | `z_SC4UIScale_DialogStatic-3x.dat`  | `FontStyle-3x.ini`  |

(The 2x tier keeps the original untagged names produced by the default generator
runs; it is not re-emitted here. `ScaleTier.cpp` carries the tag for every base,
so the same convention now applies to all ~~eight~~ **ten** tagged bases —
`SelectiveArt`, `DialogStatic`, `ItemIcons`, `ItemIconsSub`, `ThirdPartyUI`,
`WarriorUI`, `SaveWarningUI`, `CamUI`, **`NamIcons`**, **`UncoveredIcons`** —
not just the two in the table above.)

*(Corrected 2026-08-16: the list was two short. `src\ScaleTier.cpp` makes exactly
TEN `SyncDat` calls and passes `pkg.tag` to every one of them, including
`z_SC4UIScale_UncoveredIcons` at `:1832` and `z_SC4UIScale_NamIcons` at `:1885`;
`SyncDat` at `:328` builds the name as `base + tag + ".dat"`, which is this very
convention. The two added bases are NOT staged in `tools\packages\` — both are
built into `tools\itemicons\out\` (`build_uncovered_icons.py:664-665` emits
`z_SC4UIScale_UncoveredIcons-<tag>.dat`; NamIcons ships at all three tiers per
`_tests\Test-DatIntegrity.ps1:379-381`) — so do not expect to find them in
`packages\15x\` or `packages\3x\`; the tag convention still governs their names.)*

## Package contents

All entries/sizes below MEASURED 2026-08-03 from the staged files themselves
(DBPF header entry count at offset `0x24`; size = bytes on disk).
~~They match `_tests\Test-DatIntegrity.ps1` `$EXPECTED` exactly.~~

⚠ **CORRECTED 2026-08-16 — RE-MEASURED, AND THE TABLES HAD DRIFTED.** Three
entry claims below are wrong, and the size column was never test-backed at all.

* `DialogStatic` is **262** at every tier, not 261. `$EXPECTED` says 262 at
  2x / 1.5x / 3x (`_tests\Test-DatIntegrity.ps1:154,216,218`; the :154 comment
  records `261 -> 262 at v2.93.0, task #140`), and the staged dats measure 262
  at offset `0x24`. The 2x reference paragraph below is wrong the same way —
  and already contradicts itself two lines later by saying "262→262".
* `SelectiveArt-3x` is **655**, not 651 (`_tests\Test-DatIntegrity.ps1:217`,
  `#136: was 651`; staged file measures 655). That row's own note — "4 fewer
  than 1.5x/2x, the advice-row X split" — is therefore VOID: all three tiers
  are 655.
* `ThirdPartyUI-15x` / `ThirdPartyUI-3x` have **no `$EXPECTED` row at all**.
  Only the `-2x` form is entry-asserted (`_tests\Test-DatIntegrity.ps1:207`);
  the tagged pair is covered instead by `$BUILT_PAIRS`, which SHA256s the
  built file against the deployed one (`:370-371`). For those two rows the
  original sentence was not merely stale, it was never well-formed.

⛔ **`$EXPECTED` ASSERTS ENTRY COUNTS ONLY — it never asserts a byte size**
(the loop compares `$e.entries` and nothing else). So "match `$EXPECTED`
exactly" could never have covered the size column, and no test has ever
guarded these numbers. Re-measured 2026-08-16: **10 of the 18 size figures in
the two tables have moved** — every 1.5x dat except `SaveWarningUI`, plus
`SelectiveArt-3x`, `DialogStatic-3x` and `ItemIcons-3x`; the other 8 still
hold. `DialogStatic` moved furthest (1.5x 2,562,588 → 3,375,006; 3x
2,823,387 → 3,749,251). Treat every size here as indicative — measure the file.

`_tests\Test-DatIntegrity.ps1` remains the authority for entry counts; this
file describes it. Nothing is the authority for sizes.

### `packages\15x\` (factor 1.5)

| File | Entries | Size (bytes) | Notes |
|---|---|---|---|
| `z_SC4UIScale_SelectiveArt-15x.dat` | 655 | 10,810,635 | city-HUD selective art + edited scaled `.UI` |
| `z_SC4UIScale_DialogStatic-15x.dat` | ~~261~~ **262** | ~~2,562,588~~ **3,375,006** | region-screen + city dialogs, statically scaled — ⚠ CORRECTED 2026-08-16, see note below the 2x paragraph |
| `z_SC4UIScale_ItemIcons-15x.dat` | 356 | 4,703,778 | menu/picker item icons (per tier since v2.24.0) |
| `z_SC4UIScale_ItemIconsSub-15x.dat` | 130 | 1,406,606 | submenus-mod + other-plugin icons → `zzz-SC4UIScale\` |
| `z_SC4UIScale_ThirdPartyUI-15x.dat` | 2 | 72,566 | MoreBuildingStyles override → `zzz-`, gated |
| `z_SC4UIScale_WarriorUI-15x.dat` | 4 | 33,161 | warrior god-terraforming override → `zzz-`, gated |
| `z_SC4UIScale_SaveWarningUI-15x.dat` | 2 | 8,204 | cyclone-boom save-warning override → `zzz-`, gated |
| `z_SC4UIScale_CamUI-15x.dat` | **22** | 1,556,579 | CAM's six replaced scripts + **three CAM-ONLY dialogs** (#154) + 13 bitmaps → `zzz-`, gated |
| `FontStyle-15x.ini` | 90 styles | 23,016 | `[Font Styles]` sizes = round(1x × 1.5); file range **14..48** |

### `packages\3x\` (factor 3)

| File | Entries | Size (bytes) | Notes |
|---|---|---|---|
| `z_SC4UIScale_SelectiveArt-3x.dat` | ~~**651**~~ **655** | ~~16,007,730~~ 15,986,170 | ~~4 fewer than 1.5x/2x — the advice-row X split, see the warning above~~ **CORRECTED 2026-08-16: the same 655 as 1.5x/2x — there is no per-tier split any more, and the warning above is stale for the same reason. #136 (v2.88.0, 2026-08-05) widened the row-budget encoding (`sub imm8` → `lea imm32`, written only when S > 127), so the X column scales at EVERY tier: `src\CodePatches.cpp:3554` "THE TIER CEILING IS GONE", and :3565-3566 set `xScaled = true` / `glyphX = glyph` unconditionally. The mirrored `FACTOR <= 2.0` staging filter is gone from `build_selective_safe.py` in the same commit. `_tests\Test-DatIntegrity.ps1:217` asserts 655 ("#136: was 651"); entry count and size read from the DBPF header of the staged file (0x24 = 655, index 655x20 = 13,100 B ending exactly at EOF).** |
| `z_SC4UIScale_DialogStatic-3x.dat` | 261 | 2,823,387 | region-screen + city dialogs, statically scaled |
| `z_SC4UIScale_ItemIcons-3x.dat` | 356 | 5,815,662 | menu/picker item icons |
| `z_SC4UIScale_ItemIconsSub-3x.dat` | 130 | 1,755,386 | → `zzz-SC4UIScale\` |
| `z_SC4UIScale_ThirdPartyUI-3x.dat` | 2 | 91,151 | → `zzz-`, gated |
| `z_SC4UIScale_WarriorUI-3x.dat` | 4 | 40,271 | → `zzz-`, gated |
| `z_SC4UIScale_SaveWarningUI-3x.dat` | 2 | 8,214 | → `zzz-`, gated |
| `z_SC4UIScale_CamUI-3x.dat` | **22** | 1,709,678 | → `zzz-`, gated |
| `FontStyle-3x.ini` | 90 styles | 23,016 | `[Font Styles]` sizes = 1x × 3; file range **14..96** |

For reference, the 2x tier is built in place (untagged names, outside
`packages\`) and measures: SelectiveArt 655 / 11,712,063 B
(`selective-safe\`), DialogStatic 261 / 2,634,425 B (`dialog-static\`),
ItemIcons 356 / 4,993,394 B (`itemicons\`), ItemIconsSub 130 / 1,497,717 B,
ThirdPartyUI 2 / 76,670 B, WarriorUI 4 / 35,020 B, SaveWarningUI 2 / 8,210 B,
CamUI **22 / 1,647,827 B** (rebuilt 2026-08-13 for #154 — DialogStatic and
SaveWarningUI came out ENTRY-IDENTICAL across that rebuild, 262→262 and 2→2
with 0 changed, measured entry-level because `DbpfPack` is non-deterministic);
plus the always-on untagged MenuFix 6 / 864 B and
WebText 3 / 1,124 B. Its font table is `fonts\FontStyle.candidate.ini`
(90 styles, 23,016 B, sizes **14..64**).

⚠ CORRECTED 2026-08-16 — the DialogStatic figures above were stale in THREE
places, and the header claim at the top of this section was wrong with them.
Entries went 261 -> 262 at v2.93.0 (task #140, the startup splash):
`_tests\Test-DatIntegrity.ps1:216` asserts `entries = 262` for `-15x`, and
:154 / :218 assert the same for 2x / 3x. Independently corroborated in the
shipped bundles — `dist\SC4UIScale-v2.92.0\Plugins\z_SC4UIScale_DialogStatic-2x.dat`
= 261 / 2,561,841 B vs `...-v2.93.0\...` = 262 / 3,497,234 B.
RE-MEASURED 2026-08-16 by the method line 85 names (DBPF header `0x24`; bytes
on disk):
  * `-15x` (line 93): was 261 / 2,562,588 -> **262 / 3,375,006**
  * `-3x` (line 107): was 261 / 2,823,387 -> **262 / 3,749,251**
  * 2x reference (line 118): was 261 / 2,634,425 -> **262 / 3,497,234**
Note the size moved too, not just the count — a correction that fixes only
"261 -> 262" leaves two wrong sizes standing.
⚠ AND THE ROOT DEFECT: the paragraph at the top of this section
("All entries/sizes below MEASURED 2026-08-03 ... They match
`_tests\Test-DatIntegrity.ps1` `$EXPECTED` exactly") is FALSE as written —
it was the guarantee that let this rot unseen. On 2026-08-16 EVERY size in
both tables measured differently from the printed figure (e.g. SelectiveArt-15x
10,810,635 -> 10,718,552; ItemIcons-3x 5,815,662 -> 5,396,126), and
SelectiveArt-3x is additionally stale on ENTRIES (printed **651**, actual 655;
`Test-DatIntegrity.ps1:217` = "#136: was 651"). Only entry counts are asserted
by `$EXPECTED`; the sizes are asserted by nothing and will rot again. Treat
`_tests\Test-DatIntegrity.ps1` as the authority for entries and re-measure
sizes before quoting them.

Two things deliberately NOT claimed above, both unverified by me:
(a) I did not confirm that the +1 entry is specifically the splash resource —
only that the count moved at v2.93.0, which is task #140's version. The cause
attribution is carried from `Test-DatIntegrity.ps1:154`, not independently
measured.
(b) I did not chase why the -15x size (3,375,006) differs from the 2x
(3,497,234) beyond the expected tier difference. Do NOT "verify" any of this by
comparing dat FILE hashes — offsets 25 and 29 are a header timestamp and are
not reproducible; compare per-entry payload hashes instead.

The 90-style / 14..N figures are the post-v2.49.0 shape: 88 scaled styles from
the pristine table **plus** the two never-scaled HTML clone styles the
generator now emits itself (`MessageHeaderHtml` 16, `MessageBodyHtml` 14). The
unscaled 14 is why the range *floor* is 14 at every tier and not `round(10×N)`.
Pre-v2.49.0 files showing 88 styles / 22,396 B are the missing-clone
regression, not an older-but-valid build.

The `round(1x × N)` formula in those table rows has exactly **two** documented
exceptions, both in `make_fontstyle.py`: the two HTML clone styles are never
scaled at any tier, and `SIZE_SQUEEZE` multiplies the **`Legend`** style by an
extra 0.92 (13 pt → 18 / 24 / 36, not 20 / 26 / 39). `KEEP_STOCK` is currently
EMPTY — `ChartTickText` came off the pin at v2.53.2 once the plot-margin
geometry fix landed. Read the header comments in `make_fontstyle.py` before
reasoning about any of the three: the squeeze in particular does **not** do
what its name suggests — see "Font-table facts that constrain every text
calculation" below.

~~**Entry counts are equal across factors for every package EXCEPT
`SelectiveArt`** (655 / 655 / 651) — same TGIs otherwise, with only pixel
dimensions and layout coordinates differing.~~
**CORRECTED 2026-08-16: there is no exception left. Entry counts are equal
across factors for EVERY package, `SelectiveArt` included — 655 / 655 / 655 at
1.5x / 2x / 3x** — same TGIs at every tier, with only pixel dimensions and
layout coordinates differing. The split ended with #136 / v2.88.0, which
WIDENED the advice-row `imm8` encoding instead of clamping to it, so the four
dismiss-X glyphs now ship at 3x as well: `src\CodePatches.cpp:3554-3562` ("THE
TIER CEILING IS GONE ... 3x SelectiveArt therefore goes 651 -> 655 entries,
matching 1.5x/2x"), `_tests\Test-DatIntegrity.ps1:15` and `:145,215,217`.
MEASURED 2026-08-16, not read off the expectation table: the DBPF header entry
count at `0x24` is 655 on all three BUILT packages (`selective-safe\`,
`packages\15x\`, `packages\3x\`) and on all three DEPLOYED ones. Re-measured
the same way, every other package is tier-equal too — DialogStatic 262,
ItemIcons 356, ItemIconsSub 130, ThirdPartyUI 2, WarriorUI 4, SaveWarningUI 2,
CamUI 22, NamIcons 392.
⚠ STALE IN THE SAME WAY, FIXED IN THE SAME PASS 2026-08-16: the `packages\3x\`
table row above read **651** with the note "4 fewer than 1.5x/2x — the
advice-row X split", and the summary near the top of this file read "**655 /
655 / 651** at 1.5x / 2x / 3x — the project's only deliberate [split]". Both
were the pre-#136 shape, both were wrong, and both are struck above.
Each `.dat` can be re-verified
with `DbpfPack.exe --list` (entry count matches the staged file count); the
numbers above were taken from the DBPF headers, which is the same count without
unpacking anything.

## Scaling rule (shared by every generator)

Every generator uses round-half-up: `scaled = floor(v × N + 0.5)`. (There were
three when this was written; there are now six — the four numbered below plus
`itemicons\stage_icons.py` and `itemicons\build_itemicons_sub.py`.)

- For integer N (2, 3) this is exactly `v × N`, so the **N=2 path stays
  bit-identical** to the original build (verified: factor-2 upscaler output is
  byte-for-byte equal to the existing `preview\` set; factor-2 font sizes
  reproduce every `FontStyle.candidate.ini` size; `scale_len ≡ v×2` proven over
  0..4999).
- For N=1.5 the six odd 1x font sizes (11,13,15,17,19,21) land on `.5` and round
  UP (→ 17,20,23,26,29,32). Round-half-up (not Python banker's `round()`) is used
  so the **upscaler's PNG dimensions and the builders' `imagerect`/`area` scaling
  agree exactly** — a 9-slice inset scaled from source coord `r ≤ W` never exceeds
  the scaled image width `floor(W×1.5+0.5)` (monotonic). Verified end-to-end:
  **0 out-of-bounds `imagerect` across all staged 1.5x and 3x scripts.**

### ⚠ The rule governs GEOMETRY exactly. It does NOT govern TEXT FIT.

Round-half-up is exact for pixels, rects and image dimensions. It is **not** a
statement about how much text still fits. A text box scaled by `f` does **not**
hold the same string, because glyph advance does not scale linearly with point
size.

MEASURED 2026-08-03 (task #57) out of the game's own rendered pixels —
`tools\uimap\emu\emu_text_extent.py`, table `PAIRS_13_26`. Over 17 label
strings measured at **both** 13 pt and 26 pt, ink width grows by:

| statistic | value |
|---|---|
| mean per-string ratio | **2.130** (sd 0.026, n=17) |
| pooled total | 2080 px / 975 px = **2.133** |
| observed spread | 2.085 (`Air Pollution`) .. 2.188 (`Commute Time`) |

Individual examples: `Crime` 28→59, `Garbage` 42→88, `Income` 33→70,
`Population by Age` 87→185. **Never 2.00.** 26 pt Arta is roughly 6% wider per
point than 13 pt; the model attributes this to a measured per-glyph
advance-rounding loss (`DELTA = 0.70 px/glyph`) that costs proportionally more
at the smaller size.

Consequences, and they are general:

- A box of `round(stockBox × f)` **wraps more text than stock did.** Assuming
  "double the font ⇒ double the width" under-predicts a 2x label by ~6%.
- That ~6% is exactly the "Expense / s" shortfall that `SIZE_SQUEEZE` was
  invented to hide (see the font-table section below).
- **Size a text box from the FONT, not from `f`** — law L48 this session: the
  box is an input, not an output. The v2.55.0 Graphs-legend fix works that way:
  its right-margin strip is TABLED from the acceptance oracle
  (`f=1.5 → 178`, `f=2 → 240`, `f=3 → 371`; `f=1 → 108` = stock) and DECLINES
  any factor with no certified strip rather than computing `round(108 × f)`.
- ⚠ **INFERENCE, not measurement:** the 2.13 figure is a 13 pt → 26 pt result.
  Nothing has been re-measured at the 1.5x or 3x sizes (15/20/39 pt). That the
  same nonlinearity holds there is a model assumption; the ±3.8 px residual
  quoted below is established only at the two measured sizes.

## Font-table facts that constrain every text calculation

**The shipped faces cannot be measured by any external tool.** SimCity 4 ships
its fonts as Monotype MicroType Express containers — `<install>\Fonts\*.mxf`,
magic `MXFN`. There is **no `.ttf` or `.otf` anywhere** in the install or in
this repo, so PIL / FreeType / any font library cannot be pointed at the real
Arta. Substituting a look-alike face would have produced a metric table wrong
by an unknown amount, so every metric in `tools\uimap\emu\emu_text_extent.py`
is instead measured out of the game's own rendered pixels
(`_tests\captures\graphs-stock-ref.png` at 13 pt,
`_tests\captures\graphs-ours-2x.png` at 26 pt). **Stated residual: ±3.8 px**
max observed, on the three strings containing a space — the space advance
(~5.2 px at 26 pt) is the least well-measured entry in the table.

**`Arta (Bold).mxf` does not exist.** Arta ships regular + italic only, so a
style's `bold` flag cannot change its metrics. That is what lets the bold
`Legend` style and the non-bold chart-list style be pooled into one measured
metric set — both render `Garbage` at 42 px at 13 pt.

### `SIZE_SQUEEZE = {"Legend": 0.92}` is NOT about the Graphs chart legend

`fonts\make_fontstyle.py` squeezes exactly one style, by name: **`Legend`**,
GUID **`0xE9C86B5F`**. That style is the **DATA VIEWS** legend (fetched at exe
`0x007A0747`).

The **Graphs chart legend uses a different style — `ChartLabel`, GUID
`0xE9C86B5E`** — byte-verified at exe `0x0076DD91`, where the Graphs panel
builder pushes that GUID. Therefore:

> **The 0.92 squeeze has never applied to the Graphs chart at all.** The chart
> renders at `ChartLabel`'s RAW size — 20 / 26 / 39 pt at 1.5x / 2x / 3x — and
> not at the squeezed `Legend` size (18 / 24 / 36). Any calculation that
> reasoned about chart text using the squeezed number was using the wrong
> style, and under-stated the type by two points at 2x.

**Do not change the squeeze.** It remains correct for its real target, the Data
Views legend. The Graphs chart is fixed by GEOMETRY as of v2.55.0
(`CodePatches::ApplyGraphLegendBudgetScale` scales the panel builder's
six-constant right-margin budget so the column is born at `f`), not by
shrinking type. The comment attached to `SIZE_SQUEEZE` in `make_fontstyle.py`
has been corrected to say the same thing.

## 1.5x DIMENSIONS are snapped to keep the game's cell divide exact (#143)

⚠ **At a fractional factor, package art dimensions are NOT always
`round(v*f)`.** The game cuts art sheets into cells with an integer divide
baked into its own code:

    NineSlice          cell = (img->Width()/3, img->Height()/3)   VA 0x00794100
    four-state strip   cell = width/4    normal/hover/pressed/disabled

If the scaled dimension stops being divisible by that count, `cell*count` no
longer covers the sheet, the cells drift, and each draws a sliver of the next
state — a bright seam. Measured over the 2,206 extracted 1x sources:

| factor | `/3` broken | `/4` broken |
|---|---|---|
| **1.5** | **475 / 1534 (31.0%)** | **967 / 2256 (42.9%)** |
| 2.0 | 0 | 0 |
| 3.0 | 0 | 0 |

An integer factor preserves divisibility automatically, so this is
**structurally impossible at 2x and 3x** — which is exactly why it went
unnoticed until the first eyes-on pass at 1.5x. `Upscale2x.cs::ScaleDim` now
snaps a fractional factor's output to preserve the source's divisibility
(`CellUnit` = 12/4/3/1, ties up). Integer factors are untouched and their
output remains byte-identical (re-proven 2206/2206).

Builders need no change: `clamp_rect_to_art` reads the real PNG header and
clamps `imagerect` to the art that exists. `rebuild_namicons.py` has enforced
the same `/4` rule for NAM icons since #139 — this generalises it.

## 1.5x resampling — softness / fringing (judgment call)

The upscaler uses **nearest-neighbor for every factor, including 1.5**. This was
the deliberate choice for the non-integer factor:

- **No colorkey / alpha bleed — proven, not eyeballed.** Every output pixel is an
  exact copy of a source pixel, so no interpolated colors are introduced. Checked
  on sample art: the set of distinct ARGB values in each 1.5x (and 3x) output is
  *identical* to the 1x source (0 new colors). NN preserves alpha byte-for-byte,
  so there is categorically no edge fringe/halo.

  > ⚠ **CORRECTION 2026-08-06.** This paragraph used to add "SC4 UI transparency
  > is alpha-channel based (no literal magenta key was found in the sampled
  > art)". **That parenthesis was wrong, and the word doing the damage was
  > *sampled*.** SC4 uses BOTH: alpha on some art and a literal magenta
  > `0xFF00FF` COLOUR KEY on other art — `UiSpike.cpp`'s own blit paths
  > color-key magenta explicitly, and `derive_subring.py` depends on the ring
  > sprite's magenta hole. When `--hq` was briefly made automatic for fractional
  > factors, the Mayor Rating bar and the news-reader borders went visibly pink
  > within one launch: interpolation moved exact key pixels off `0xFF00FF`, the
  > key test missed them, and the key colour drew.
  >
  > The "0 new colors" result above is still correct and is in fact the whole
  > reason NN is safe — it just does not license the conclusion that there is no
  > key to protect. **A survey of SOME art cannot establish a property of ALL
  > art**; state the sample, and never let a sample's silence become a claim
  > about the population (law: null is not evidence). See `REGRESSION.md` #143.
- **Least-soft option.** NN performs zero blending, so it is the least-soft
  resampler possible; there is no added softness at 1.5x.
- **Residual artifact = pixel-grid unevenness, not softness.** At 1.5x each source
  pixel becomes either 1 or 2 output pixels per axis (a regular 2:1 stipple),
  visible as slightly chunky stair-stepping on curved/diagonal edges. The soft
  anti-aliasing already baked into the source art is preserved (blockily), so
  curves read a touch chunkier than the crisp integer factors but show **no blur
  and no new colors**. Validated by eye on a magnified 1.5x sample (the 180×180
  window-chrome 9-slice corner over a checkerboard): edges crisp, alpha boundary
  clean, no halo.
- A softer `--hq` bicubic path exists in the upscaler (and honors `--factor`) but
  is **not** used for these packages — bicubic would blend across the alpha edge
  and reintroduce fringe risk.

## Exact commands run

Paths are relative to ~~`...\SC4TouchControls\tools\`~~ **`...\SC4UIScale\tools\`** (this file's own project root).
*(corrected 2026-08-16: the projects split 2026-08-06 and no PROJECT ROOT named `SC4TouchControls\`
exists any more — the only surviving folders carrying that name are two dated snapshots
`_BACKUP_SC4TouchControls_2026-07-2{5,6}_*` and the release bundles under `..\SC4Touch\dist\`,
and none of them holds a `tools\` tree. The touch half is the sibling `..\SC4Touch\`, which has
no `tools\` directory at all and carries none of these generators — a name search of that whole
tree for `make_fontstyle.py`, `build_selective_safe.py`, `build_dialog_static.py`,
`Rebuild-Corpus.ps1` and `Upscale2x*` returns 0 hits. Every path in the block below resolves
under `SC4UIScale\tools\`, verified on disk. `START-HERE.md:34-37`,
`_tests\Test-DatIntegrity.ps1:337-338`. NB this header stays live even though the block is
called a historical record at the end of the section: it was re-edited 2026-08-16 for #170, and
that section's own instruction to "read the builders before quoting a command" cannot be obeyed
against a root that does not exist.)*
1x master PNGs live in
`dbpf\extracted\SimCity_1\` (extracted from the game `SimCity_1.dat`, read-only);
the pristine 1x font table is `fonts\FontStyle.default.ini` (byte-verified
identical to a fresh extraction of TGI `0x00000000,0x4A87BFE8,0x2A87BFFC`).

⚠ **From a cold clone, run `tools\Bootstrap-Corpus.ps1` before step 0.** None
of the builders' *inputs* are in the repo — the extracted archives, the PNG-TGI
csv, the `.UI` corpus, and the mod-owned scripts and bitmaps are all derived
from the player's own install, and until 2026-08-18 nothing derived them. Five
of nine builders refused on a fresh checkout for exactly that reason, every one
with a bare `FileNotFoundError`. `tools\itemicons\recover_sub_sources.py`
covers the ItemIconsSub 1x sources separately. Then check the whole set with
`_tests\Test-Builders.ps1`, which runs all nine **in dependency order** —
`selective-safe` emits what `dialog-static` and `stage_icons` read.

```
# 0. (one-time) compile the parameterized upscaler
powershell -NoProfile -ExecutionPolicy Bypass -File upscale\Build.ps1

# 1. Upscale the full 1x PNG set for each factor.
#    ⛔ USE THE SCRIPT. Do not hand-type the exe invocation - it needs THREE
#    derived list files, and the version documented here until 2026-08-16
#    carried NONE of them:
#        --cell-strips  #156 per-STATE sampling for N-state strips
#        --nine-slice   #157 CellUnit{3} for blttype=edge frames
#        --no-snap      #160 tiled backgrounds must not be snapped
#    Omitting them un-ships all three USER-CONFIRMED fixes at exit 0, with
#    every gate green - each gate measures the new tree against itself. The
#    script refuses to run if a list is missing or empty (#170).
powershell -NoProfile -ExecutionPolicy Bypass -File upscale\Rebuild-Corpus.ps1
#    (or one tier:  ... -File upscale\Rebuild-Corpus.ps1 -Factor 1.5)

# 2. Font tables (from the pristine 1x table; only the size field changes,
#    PLUS the two stock-size HTML clone styles the generator now emits itself)
#    ⚠ 2026-08-02: until today these two commands produced a file MISSING
#    MessageHeaderHtml/MessageBodyHtml, because those were hand-added to
#    candidate.ini after generation - and the DLL's popup retarget then
#    pointed at styles that did not exist at 1.5x/3x, failing silently.
#    The generator emits them now and FATALs if they are absent. Verify with
#    `python fonts\make_fontstyle.py --selfcheck` (byte-identical to
#    candidate.ini at factor 2).
#    ⚠ CORRECTED 2026-08-03: this note used to say "expect 64 style lines, not
#    62". That does NOT reproduce. MEASURED by counting [Font Styles] entries:
#    FontStyle.default.ini = 88; candidate.ini, FontStyle-15x.ini and
#    FontStyle-3x.ini = 90 each (88 + the two clones).
#    Do NOT read the counts off stdout: the generator prints
#      "(factor 1.5, 88 styles, size range 15..48)"
#    which is the SCALED styles only - the two clones are emitted verbatim and
#    never enter the change list, so the FILE has 90 styles and a range of
#    14..48 (MessageBodyHtml = 14, never scaled). 88/15 printed, 90/14 on disk.
#    Neither number was ever 64. Also verified 2026-08-03: re-running this
#    exact command reproduces the shipped packages\15x\FontStyle-15x.ini
#    BYTE-IDENTICALLY, and --selfcheck passes.
python fonts\make_fontstyle.py 1.5 packages\15x\FontStyle-15x.ini
python fonts\make_fontstyle.py 3   packages\3x\FontStyle-3x.ini

# 3. Selective city-HUD art dat  (emits refmap-<tag>.csv used by step 4)
python selective-safe\build_selective_safe.py --factor 1.5
python selective-safe\build_selective_safe.py --factor 3

# 4. Static region-dialog dat  (run AFTER step 3 of the same factor)
python dialog-static\build_dialog_static.py --factor 1.5
python dialog-static\build_dialog_static.py --factor 3
```

Default (no `--factor`) reproduces the original untagged 2x outputs and was
deliberately NOT run, to leave the shipped 2x `.dat`s (which embed a build
timestamp) untouched.

⚠ **These four steps no longer produce a whole tier.** They pre-date the other
four tagged dats now in each tier. `ItemIcons` / `ItemIconsSub` are built per
tier by `itemicons\stage_icons.py --factor` and
`itemicons\build_itemicons_sub.py --factor` (v2.24.0; see the note at
`_tests\Test-DatIntegrity.ps1` around the `ItemIcons-15x` entries). The four
mod-override packages are additional outputs of the two builders in steps 3
and 4 — VERIFIED 2026-08-03 by name search: `ThirdPartyUI` and `WarriorUI` are
emitted by `selective-safe\build_selective_safe.py`, `CamUI` and
`SaveWarningUI` by `dialog-static\build_dialog_static.py`, and no other builder
mentions them. **Not established this session:** whether those four need any
flag beyond `--factor`. The block above is a historical record of the 1.5x/3x
font and art generation, not a complete tier recipe — read the builders before
quoting a command, do not infer one from this file.

## Generator changes (all default to N=2 = original behavior)

- **`upscale\Upscale2x.cs`** — added `--factor N` (2/3 integer block-replicate
  nearest-neighbor; 1.5 fractional NN) and `--normalize-names` (rewrite SC4
  `T-/G-/I-` filenames to canonical `0x` form). Output dims use `floor(v×N+0.5)`.
  `--hq` bicubic now also honors `--factor`. N=2 output unchanged (byte-verified).
- **`upscale\Upscale2x.cs`** - `--cell-strips <file>` (v2.99.0, #156): sheets
  named in that file are sampled PER STATE, so a snapped sheet's cell boundaries
  cannot drift and let one state's art bleed into the next cell. The file is
  generated by `upscale\find_cell_strips.py` from the `.UI` bindings - 193
  sheets. Do NOT scope this by `CellUnit`: that guess moved 1186 of 2206 sheets
  and displaced an advisor aperture (REGRESSION.md #156). Proven no-op at integer
  factors: 2206 PNGs, 0 changed at 2x and 3x.
- **`fonts\make_fontstyle.py`** (new) — emits `FontStyle-<tag>.ini` from
  `FontStyle.default.ini`, changing only the `[Font Styles]` size field; CRLF and
  every other byte preserved. `--selfcheck` proves factor 2 reproduces
  `FontStyle.candidate.ini` exactly.
- **`selective-safe\build_selective_safe.py`** — `--factor` routes upscale dir,
  stage, `.dat` (→ `packages\<tag>\`), `refmap-<tag>.csv`, `package-list-<tag>.txt`;
  `imagerect` scales via `scale_len` (round-half-up). Clone-IID scheme
  (`iid ^ 0x53430001`) and font-GUID conversion unchanged.
- **`dialog-static\build_dialog_static.py`** — `--factor` routes upscale dir,
  reads `refmap-<tag>.csv`, stage, `.dat` (→ `packages\<tag>\`), report
  (`dialog-static\REPORT-<tag>.md`); `area`/`imagerect`/`rowheight`/`gutters`/etc.
  scale via `scale_len`; node-for-node `verify_doubled` runs at every factor.
  ⚠ **`imagerect` scales only where that control's ART scaled**, and the test
  reads `art_plan` — which is built from the **stock** upscale store alone.
  Mod-supplied art (`thirdparty-art\`) is therefore always `left1x` there, so
  it is routed through `RUNTIME_BOUND_2X` instead, scoped to the package that
  ships the scaled bitmap. Missing that is what shipped v2.97.0's half-width
  row stripes; see `_tests\REGRESSION.md` #154 CORRECTION.
  v2.97.1 additions: `TP_MOD_ONLY` (dialogs a mod ADDS — exemption from the
  stock-twin assert, **proven** by absence from the stock corpus) and
  `TP_ART_DANGLING` (refs proven absent everywhere; the bar is a null from an
  instrument that reads Plugins too, plus a positive control).

## Regeneration

Re-run the four numbered command blocks above for the desired factor. The
upscale dirs (`upscale\preview-15x\`, `upscale\preview-3x\`) and build
intermediates (`selective-safe\stage-<tag>\`, `dialog-static\stage-<tag>\`,
`selective-safe\refmap-<tag>.csv`, `package-list-<tag>.txt`) are regenerable and
are not part of the shippable package. To add another factor `K`, run the same
four steps with `--factor K`; the generators auto-derive the tag (`Kx`, or
`p_qx` for a non-integer like 2.5 → `2_5x`) and the output paths.

---

## z_SC4UIScale_CamGraphLabels.dat (#147, added 2026-08-06)

| | |
|---|---|
| **Built by** | `tools\itemicons\build_cam_graph_labels.py` |
| **Source of truth** | `tools\packages\shared\z_SC4UIScale_CamGraphLabels.dat` |
| **Deployed to** | `Plugins\zzz-SC4UIScale\z_SC4UIScale_CamGraphLabels.dat` |
| **Entries** | 1 |
| **Tier** | **NONE — tier-independent.** A string has no geometry, so there is no `-15x` / `-2x` / `-3x` triple and no `.x1-disabled` variant. ~~It is the only package in the project with a single untagged form.~~ **CORRECTED 2026-08-16: it is one of THREE untagged single-form packages — `MenuFix` (6 entries) and `WebText` (3 entries) are the others (`_tests\Test-DatIntegrity.ps1:184`, `:194`, `:289`; every other row in that `$EXPECTED` table carries a `-2x`/`-15x`/`-3x` tag, as do NamIcons and UncoveredIcons which sit outside it). The no-geometry *reason* is not unique either: `WebText` is 3 LTEXT entries of the SAME type `0x2026960B` (`tools\webtext\build_webtext.py:2,32`), untagged for exactly the same reason. Note `MenuFix` is asserted by the integrity test but deliberately NOT deployed — it rewrites CAM's gameplay submenu data (`_tests\Deploy-OnGameClose.ps1:135`).** |
| **Gate** | by LOCATION only: nothing except CAM binds the instance, so it is inert without CAM |
| **In deploy?** | ✅ `Deploy-OnGameClose.ps1` |
| **In integrity?** | ✅ `Test-DatIntegrity.ps1` (total 24 → 25 dats) |

**What it is:** the one LTEXT that CAM's Power and Water charts ask for and no
installed file provides — `{0x2026960B, 0x6A231EAA, 0xFF5D2E9F}` = `"Exported"`,
20 bytes. Without it the 4th legend row draws a checkbox and a swatch with no
caption. We ADD a resource; we never modify CAM's file.

⚠ **Deliberately without CAM's trailing CRLF.** `Imported` (`0xFF5D2E9E`), the
row directly above ours in the same legend, has none either; copying CAM's
`Exported\r\n` would render our row two lines tall.

**DELETE** this package, its builder, its deploy line and its integrity row if
CAM ever fixes the id upstream (reported: `UPSTREAM-CAM-REPORT.md` §4).
