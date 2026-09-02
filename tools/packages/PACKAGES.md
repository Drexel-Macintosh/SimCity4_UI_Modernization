# SC4 UI-scaling asset packages (per-factor tiers)

Factor-tagged UI-scaling packages that feed the AutoScale tier system: a
screen resolution picks a factor, and the DLL enables the matching package by
its filename tag. The package set, tier behaviour and dependency gates are
described in [../../docs/PACKAGE-MANIFEST.md](../../docs/PACKAGE-MANIFEST.md);
this file is the per-package build-side reference.

**Authority.** `_tests\Test-DatIntegrity.ps1` (its `$EXPECTED` table) asserts
every *deployed* package's entry count and is updated deliberately whenever
one changes. Treat that script as the source of truth and this file as a
description of it. Byte sizes are indicative — nothing asserts them, and a
DBPF header carries a build timestamp, so compare per-entry payloads, never
file hashes.

**Rebuild all tiers together** — `--factor 2`, `--factor 1.5`, `--factor 3` —
or the suite fails on mismatched counts, and 1.5x is where rounding bugs hide
(2x hides them: exact doubling).

`packages\15x\` and `packages\3x\` are the build side of a build→deploy pair:
`_tests\Test-DatIntegrity.ps1` hashes each file here against its deployed
twin in the Plugins tree and fails on a mismatch (its `$BUILT_PAIRS` map names
`tools\packages\<tag>\...` as the built-side source for every tagged dat and
font INI). Editing or rebuilding a file here without redeploying turns that
check red; the correct sequence is rebuild → `_tests\Deploy-OnGameClose.ps1`.

## Filename tag convention (the DLL relies on this)

The factor tag goes in the BASE name, immediately before the extension:

| Factor | Tag | Art dat | Dialog dat | Font INI |
|---|---|---|---|---|
| 1.5x | `15x` | `z_SC4UIScale_SelectiveArt-15x.dat` | `z_SC4UIScale_DialogStatic-15x.dat` | `FontStyle-15x.ini` |
| 3x   | `3x`  | `z_SC4UIScale_SelectiveArt-3x.dat`  | `z_SC4UIScale_DialogStatic-3x.dat`  | `FontStyle-3x.ini`  |

The 2x tier keeps the original untagged names produced by the default
generator runs. `ScaleTier.cpp` carries the tag for every tier-paired base —
`SelectiveArt`, `DialogStatic`, `ItemIcons`, `ItemIconsSub`, `ThirdPartyUI`,
`WarriorUI`, `SaveWarningUI`, `CamUI`, `NamIcons`, `UncoveredIcons`,
`CsiIcons` — not just the two in the table above. `NamIcons` and
`UncoveredIcons` are built into `tools\itemicons\out\`, so do not expect to
find them in `packages\15x\` or `packages\3x\`; the tag convention still
governs their names. `CsiIcons` is built by
`tools\research\udriveit\build_csi_scaled.py` and staged into
`packages\<tag>\` like the rest.

## Package contents

Entry counts below are measured from the staged files' DBPF headers (offset
`0x24`) and agree with `_tests\Test-DatIntegrity.ps1` `$EXPECTED`. Entry
counts are equal across factors for every package — same TGIs at every tier,
with only pixel dimensions and layout coordinates differing.

### `packages\15x\` (factor 1.5)

| File | Entries | Size (bytes) | Notes |
|---|---|---|---|
| `z_SC4UIScale_SelectiveArt-15x.dat` | 696 | 17,589,383 | city-HUD selective art + edited scaled `.UI`; v4.8.0 (#203 straight-edge hybrid) — was 13,411,333 at v4.7.2, see below |
| `z_SC4UIScale_DialogStatic-15x.dat` | 266 | 2,912,173 | region-screen + city dialogs, statically scaled; v4.8.0 — was 2,655,005 at v4.7.2 |
| `z_SC4UIScale_ItemIcons-15x.dat` | 356 | 4,712,509 | menu/picker item icons (per tier since v2.24.0); byte-identical v4.7.2 → v4.8.0 |
| `z_SC4UIScale_ItemIconsSub-15x.dat` | 130 | 1,410,334 | submenus-mod + other-plugin icons → `zzz-SC4UIScale\`; byte-identical v4.7.2 → v4.8.0 |
| `z_SC4UIScale_ThirdPartyUI-15x.dat` | 2 | 72,566 | MoreBuildingStyles override → `zzz-`, gated |
| `z_SC4UIScale_WarriorUI-15x.dat` | 4 | 33,161 | warrior god-terraforming override → `zzz-`, gated |
| `z_SC4UIScale_SaveWarningUI-15x.dat` | 2 | 8,204 | cyclone-boom save-warning override → `zzz-`, gated |
| `z_SC4UIScale_CamUI-15x.dat` | 22 | 1,556,558 | CAM's six replaced scripts + three CAM-only dialogs + 13 bitmaps → `zzz-`, gated |
| `z_SC4UIScale_CsiIcons-15x.dat` | 16 | 323,698 | U-Drive-It offer-balloon icons → `zzz-` |
| `FontStyle-15x.ini` | 90 styles | 23,016 | `[Font Styles]` sizes = round(1x × 1.5); file range **14..48** |

### `packages\3x\` (factor 3)

| File | Entries | Size (bytes) | Notes |
|---|---|---|---|
| `z_SC4UIScale_SelectiveArt-3x.dat` | 696 | 16,168,796 | city-HUD selective art + edited scaled `.UI` |
| `z_SC4UIScale_DialogStatic-3x.dat` | 265 | 2,844,102 | region-screen + city dialogs, statically scaled |
| `z_SC4UIScale_ItemIcons-3x.dat` | 356 | 5,815,662 | menu/picker item icons |
| `z_SC4UIScale_ItemIconsSub-3x.dat` | 130 | 1,755,386 | → `zzz-SC4UIScale\` |
| `z_SC4UIScale_ThirdPartyUI-3x.dat` | 2 | 91,151 | → `zzz-`, gated |
| `z_SC4UIScale_WarriorUI-3x.dat` | 4 | 40,271 | → `zzz-`, gated |
| `z_SC4UIScale_SaveWarningUI-3x.dat` | 2 | 8,214 | → `zzz-`, gated |
| `z_SC4UIScale_CamUI-3x.dat` | 22 | 1,709,678 | → `zzz-`, gated |
| `z_SC4UIScale_CsiIcons-3x.dat` | 16 | 934,370 | U-Drive-It offer-balloon icons → `zzz-` |
| `FontStyle-3x.ini` | 90 styles | 23,016 | `[Font Styles]` sizes = 1x × 3; file range **14..96** |

For reference, the 2x tier is built in place (untagged names, outside
`packages\`) by the same builders; its font table is
`fonts\FontStyle.candidate.ini` (90 styles, sizes **14..64**). The untagged
always-on packages — `MenuFix` (6 entries), `WebText` (3 entries) and
`CamGraphLabels` (1 entry) — are described in the manifest and in the
CamGraphLabels section below.

The 90-style / 14..N figures are the post-v2.49.0 shape: 88 scaled styles
from the pristine table **plus** the two never-scaled HTML clone styles the
generator emits itself (`MessageHeaderHtml` 16, `MessageBodyHtml` 14). The
unscaled 14 is why the range *floor* is 14 at every tier and not
`round(10×N)`. Files showing 88 styles / 22,396 B are the missing-clone
regression, not an older-but-valid build.

The `round(1x × N)` formula in those table rows has exactly **two**
documented exceptions, both in `make_fontstyle.py`: the two HTML clone styles
are never scaled at any tier, and `SIZE_SQUEEZE` multiplies the **`Legend`**
style by an extra 0.92 (13 pt → 18 / 24 / 36, not 20 / 26 / 39). `KEEP_STOCK`
is currently empty — `ChartTickText` came off the pin at v2.53.2 once the
plot-margin geometry fix landed. Read the header comments in
`make_fontstyle.py` before reasoning about any of the three: the squeeze in
particular does **not** do what its name suggests — see "Font-table facts
that constrain every text calculation" below.

Each `.dat` can be re-verified with `DbpfPack.exe --list` (entry count
matches the staged file count); the numbers above were taken from the DBPF
headers, which is the same count without unpacking anything.

## Scaling rule (shared by every generator)

Every generator uses round-half-up: `scaled = floor(v × N + 0.5)`.

- For integer N (2, 3) this is exactly `v × N`, so the **N=2 path stays
  bit-identical** to the original build (verified: factor-2 upscaler output
  byte-for-byte equal to the existing set; factor-2 font sizes reproduce
  every `FontStyle.candidate.ini` size; `scale_len ≡ v×2` proven over
  0..4999).
- For N=1.5 the six odd 1x font sizes (11,13,15,17,19,21) land on `.5` and
  round UP (→ 17,20,23,26,29,32). Round-half-up (not Python banker's
  `round()`) is used so the **upscaler's PNG dimensions and the builders'
  `imagerect`/`area` scaling agree exactly** — a 9-slice inset scaled from
  source coord `r ≤ W` never exceeds the scaled image width
  `floor(W×1.5+0.5)` (monotonic). Verified end-to-end: **0 out-of-bounds
  `imagerect` across all staged 1.5x and 3x scripts.**

### The rule governs GEOMETRY exactly. It does NOT govern TEXT FIT.

Round-half-up is exact for pixels, rects and image dimensions. It is **not**
a statement about how much text still fits. A text box scaled by `f` does
**not** hold the same string, because glyph advance does not scale linearly
with point size.

MEASURED out of the game's own rendered pixels —
`tools\uimap\emu\emu_text_extent.py`, table `PAIRS_13_26`. Over 17 label
strings measured at **both** 13 pt and 26 pt, ink width grows by:

| statistic | value |
|---|---|
| mean per-string ratio | **2.130** (sd 0.026, n=17) |
| pooled total | 2080 px / 975 px = **2.133** |
| observed spread | 2.085 (`Air Pollution`) .. 2.188 (`Commute Time`) |

Individual examples: `Crime` 28→59, `Garbage` 42→88, `Income` 33→70,
`Population by Age` 87→185. **Never 2.00.** 26 pt Arta is roughly 6% wider
per point than 13 pt; the model attributes this to a measured per-glyph
advance-rounding loss (`DELTA = 0.70 px/glyph`) that costs proportionally
more at the smaller size.

Consequences, and they are general:

- A box of `round(stockBox × f)` **wraps more text than stock did.**
  Assuming "double the font ⇒ double the width" under-predicts a 2x label by
  ~6%.
- That ~6% is exactly the "Expense / s" shortfall that `SIZE_SQUEEZE` was
  invented to hide (see the font-table section below).
- **Size a text box from the FONT, not from `f`** — the box is an input, not
  an output. The Graphs-legend fix works that way: its right-margin strip is
  TABLED from the acceptance oracle (`f=1.5 → 178`, `f=2 → 240`, `f=3 → 371`;
  `f=1 → 108` = stock) and DECLINES any factor with no certified strip rather
  than computing `round(108 × f)`.
- **Scope of the measurement:** the 2.13 figure is a 13 pt → 26 pt result.
  Nothing has been re-measured at the 1.5x or 3x sizes (15/20/39 pt); that
  the same nonlinearity holds there is a model assumption, and the ±3.8 px
  residual quoted below is established only at the two measured sizes.

## Font-table facts that constrain every text calculation

**The shipped faces cannot be measured by any external tool.** SimCity 4
ships its fonts as Monotype MicroType Express containers —
`<install>\Fonts\*.mxf`, magic `MXFN`. There is **no `.ttf` or `.otf`
anywhere** in the install or in this repo, so PIL / FreeType / any font
library cannot be pointed at the real Arta. Substituting a look-alike face
would produce a metric table wrong by an unknown amount, so every metric in
`tools\uimap\emu\emu_text_extent.py` is instead measured out of the game's
own rendered pixels (`_tests\captures\graphs-stock-ref.png` at 13 pt,
`_tests\captures\graphs-ours-2x.png` at 26 pt). **Stated residual: ±3.8 px**
max observed, on the three strings containing a space — the space advance
(~5.2 px at 26 pt) is the least well-measured entry in the table.

**`Arta (Bold).mxf` does not exist.** Arta ships regular + italic only, so a
style's `bold` flag cannot change its metrics. That is what lets the bold
`Legend` style and the non-bold chart-list style be pooled into one measured
metric set — both render `Garbage` at 42 px at 13 pt.

### `SIZE_SQUEEZE = {"Legend": 0.92}` is NOT about the Graphs chart legend

`fonts\make_fontstyle.py` squeezes exactly one style, by name: **`Legend`**,
GUID **`0xE9C86B5F`**. That style is the **DATA VIEWS** legend (fetched at
exe `0x007A0747`).

The **Graphs chart legend uses a different style — `ChartLabel`, GUID
`0xE9C86B5E`** — byte-verified at exe `0x0076DD91`, where the Graphs panel
builder pushes that GUID. Therefore:

> **The 0.92 squeeze has never applied to the Graphs chart at all.** The
> chart renders at `ChartLabel`'s RAW size — 20 / 26 / 39 pt at 1.5x / 2x /
> 3x — and not at the squeezed `Legend` size (18 / 24 / 36). Any calculation
> that reasoned about chart text using the squeezed number was using the
> wrong style, and under-stated the type by two points at 2x.

**Do not change the squeeze.** It remains correct for its real target, the
Data Views legend. The Graphs chart is fixed by GEOMETRY
(`CodePatches::ApplyGraphLegendBudgetScale` scales the panel builder's
six-constant right-margin budget so the column is born at `f`), not by
shrinking type.

## 1.5x DIMENSIONS are snapped to keep the game's cell divide exact

**At a fractional factor, package art dimensions are NOT always
`round(v*f)`.** The game cuts art sheets into cells with an integer divide
baked into its own code:

    NineSlice          cell = (img->Width()/3, img->Height()/3)
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
unnoticed until the first eyes-on pass at 1.5x. `Upscale2x.cs::ScaleDim`
snaps a fractional factor's output to preserve the source's divisibility,
per the sheet's ROLE (derived from the `.UI` that binds it, never guessed):

| role | sizing rule | derived list |
|---|---|---|
| N-state strip | preserve `width/N` | `find_cell_strips.py` → `cell-strips.txt` (193 sheets) |
| 9-slice frame | preserve `width/3` alone | `find_nine_slice.py` → `nine-slice.txt` (30) |
| tiled / 1:1 window-bound | **no snap at all** | `find_no_snap.py` → `no-snap.txt` (121) |

Integer factors are untouched and their output remains byte-identical
(re-proven 2206/2206). Builders need no change: `clamp_rect_to_art` reads
the real PNG header and clamps `imagerect` to the art that exists.

## 1.5x resampling — a per-sheet policy chain, straight-edge hybrid by default (v4.8.0, #203)

**Integer factors (2, 3) are nearest-neighbour, an exact N×N block copy, and
every rule below is a no-op there** — the `--hybrid` dispatch refuses an
integer factor and the exe FATALs if it ever fires at one. Re-proven at
v4.8.0: 0 of 2206 sheets changed at 2x and 3x (sha1 of every preview PNG
against the pre-rebuild manifest; the run summary reads
`hybrid: 0 sheet(s) ... 2206 integer factor`).

**At 1.5 no single resampler survived the screen.** A copy cannot be even at
3/2: source columns get multiplicity 2,1,2,1, so a 1px stroke renders 1px or
2px by the parity of its origin (measured on the advisor sheet: 1px runs ×106
/ 2px runs ×110, where 2x and 3x are uniform). The area average that #200
(v4.3.0) had removed as the default was "soft"; the nearest it put in its
place was "ragged / uneven edges" (#203). Both horns were rejected on screen,
so the shipped policy is decided **per sheet, then per block**, in this
order — the order is `Upscale2x.cs`'s dispatch, and `Rebuild-Corpus.ps1` is
the only place the stock corpus's flag set lives (the third-party lanes
carry their own, see below):

| # | sheet class | flag / list (derivation) | 1.5x resampler |
|---|---|---|---|
| 1 | any sheet, integer factor | — | nearest (exact block copy; the hybrid refuses) |
| 2 | tick ladders and N-state strips | `--even-strips even-strips.txt` (`research\sharp15\make_even_strips.py`: the 89 measured tick ladders ∪ `cell-strips.txt`) | `--supersample`: lossless ×3 then area reduce — even by construction (GH5), kept only where ticks exist (#200) |
| 3 | sheets a builder MEASURES pixel-by-pixel (advisor frames, `seat_faces_on_apertures`) | `--no-smooth no-smooth.txt` (`make_no_smooth.py` from `ADVISOR_FACE_SEATS`, #175) | nearest |
| 4 | item-icon thumbnails (lot / building pictures) | `--thumbnails thumbnails.txt` (`find_thumbnails.py`: every PNG the ItemIcons + ItemIconsSub packages carry, 485 TGIs, all group `6a386d26`) | nearest |
| 5 | sheets whose colour key is 1–2 px STRUCTURE (`HasExactColorKey && MinKeyRun < 3`, #175) | built into the exe, no list | nearest |
| 6 | everything else | `--hybrid thin` | straight-edge hybrid (`UpscaleHybrid`) |

The refusal counters for rows 1–5 are printed in the run summary
(`hybrid: N sheet(s) ... integer factor / even-strips / measured /
thumbnails / fine key`), so a refusal can never be mistaken for coverage.

**What the hybrid does (row 6).** Per 2×2 output block: a block with a
3-of-4 majority copies; a tie that CONTINUES in the neighbouring block along
the edge (a straight edge) takes the edge-claim copy, so a salient stroke
renders at one consistent width (`thin` gives an odd-width stroke's tie block
away, `bold` takes it; `thin` shipped); every other block — a staircase step,
a curve, a picture — takes the key-aware 2:1 area average. Straight chrome
stays a crisp copy at one width; curves get the anti-aliasing a vector UI
renders at 150%. MEASURED on the shipped 1.5x corpus, v4.7.2 → v4.8.0
(`_tests\Test-15xEdgeQuality.py`, integer tiers as its positive control):
stroke-width CV per source width cv1 0.319 → 0.232, cv3 0.109 → 0.095, swc
0.2997 → 0.2237; invented pixels 1,270,876 → 6,197,630 (blends at curves —
the price); soft_frac 0.419 → 0.564. The cv2 rise (0.022 → 0.133) is largely
the metric reading the exact-colour core of a 2px run whose one edge blended.

**Why thumbnails are a binding fact, not a pixel fact (row 4).** Round 1 on
screen: "It all looks a lot better. Maybe the thumbnails still don't look as
sharp though." No pixel predicate separates a lot thumbnail from a glossy
mode button (the ramp and stroke censuses over 2204 sheets - lab
instruments under `research\sharp15\`, not shipped: ramp_frac
0.74–0.99 vs 0.47–0.86, stroke density 0.05–0.08 vs 0.08 — both are
anti-aliased art). What differs is what the picture DEPICTS, so the class is
derived from what the engine binds the art as. Catmull-Rom and Lanczos were
measured for the soft branch and rejected (edge_w 1.66 either way, no sharper
than the box on photoreal art). Round 2: "Thumbnails are sharp."

**The colour key is still nearest's — proven, not eyeballed.** SC4 uses BOTH
alpha and a literal magenta `0xFF00FF` COLOUR KEY (the blit paths in
`UiSpike.cpp` colour-key magenta explicitly, and `derive_subring.py` depends
on the ring sprite's magenta hole). Under the hybrid the transparency MASK is
nearest's prediction and only the colour inside it is the hybrid's: where
nearest says key the pixel is nearest's pixel verbatim (colour and alpha); where nearest says colour
but the average landed on the key by coverage, the pixel takes the
key-excluded average of its block. `gate_key_integrity.py` PASSes at 1.5 / 2
/ 3 with zero exemptions added; `key_near` 10,251 and `key_moved` 2,059 are
unchanged from v4.7.2 corpus-wide. **Never make `--hq` automatic**:
`Graphics.DrawImage` interpolation moves exact key pixels off `0xFF00FF`, the
key test misses them, and the key colour draws — the Mayor Rating bar and the
news-reader borders turned pink within one launch when this was tried, and
#175's `--smooth-keyed` painted a pink block behind Options for the mirror
reason (a legitimate key result nudged to `FF01FF`). `--hq` remains in the
exe for a deliberate side-by-side only.

**The port is the same function, proven not argued.** The user judged
packages built by the Python reference (`research\sharp15\x3_candidates.py`
`thin_h`, via `build_variant_tree.py`); what ships is the C# `UpscaleHybrid`.
`upscale\gate_hybrid_parity.py` holds them pixel-equal (decoded RGBA; the PNG bytes differ by encoder) — 2206 of 2206 sheets,
dimensions included — and its reference tree keeps the even-strips /
no-smooth / thumbnails / fine-key sheets as the shipped bytes, so rows 2–5
are a free regression control for the dispatch.

**Package growth is PNG bytes, not pixels.** `SelectiveArt-15x` 13,411,333 →
17,589,383 B and `DialogStatic-15x` 2,655,005 → 2,912,173 B at v4.8.0 (2x
SelectiveArt is 11,885,116 B, 3x 16,168,796 B): blended curves compress worse
than a 2,1,2,1 copy pattern, and the exe's GDI+ encoder is not an optimising
one — the SAME pixels packed by PIL in the round-2 packages were 14,807,918 B.
No entry was added or removed; the two icon packages are byte-identical to
v4.7.2.

**Left on the old policy, deliberately.** The third-party lanes (CamUI, NAM
icons, Web Button, Carbon skin art) still run the exe with their own flag
sets and take nearest at 1.5x — none of them was on the screen the user
judged, and a resampler change the user has not seen does not ship. Wire them
when they can be looked at.

## Exact commands

Paths are relative to `...\SC4UIScale\tools\`. 1x master PNGs live in
`dbpf\extracted\SimCity_1\` (extracted from the game `SimCity_1.dat`,
read-only); the pristine 1x font table is `fonts\FontStyle.default.ini`
(byte-verified identical to a fresh extraction of TGI
`0x00000000,0x4A87BFE8,0x2A87BFFC`).

**From a cold clone, run `tools\Bootstrap-Corpus.ps1` first.** None of the
builders' *inputs* are in the repo — the extracted archives, the PNG-TGI csv,
the `.UI` corpus, and the mod-owned scripts and bitmaps are all derived from
the player's own install. `tools\itemicons\recover_sub_sources.py` covers the
ItemIconsSub 1x sources separately. Then check the whole set with
`_tests\Test-Builders.ps1`, which runs all nine builders **in dependency
order** — `selective-safe` emits what `dialog-static` and `stage_icons` read.

```
# 0. (one-time) compile the parameterized upscaler
powershell -NoProfile -ExecutionPolicy Bypass -File upscale\Build.ps1

# 1. Upscale the full 1x PNG set for each factor.
#    USE THE SCRIPT. Do not hand-type the exe invocation — it needs THREE
#    derived list files:
#        --cell-strips  per-STATE sampling for N-state strips
#        --nine-slice   CellUnit{3} for blttype=edge frames
#        --no-snap      tiled backgrounds must not be snapped
#    Omitting them un-ships all three fixes at exit 0, with every gate green
#    — each gate measures the new tree against itself. The script refuses to
#    run if a list is missing or empty.
powershell -NoProfile -ExecutionPolicy Bypass -File upscale\Rebuild-Corpus.ps1
#    (or one tier:  ... -File upscale\Rebuild-Corpus.ps1 -Factor 1.5)

# 2. Font tables (from the pristine 1x table; only the size field changes,
#    PLUS the two stock-size HTML clone styles the generator emits itself).
#    The generator FATALs if the clones are absent. Verify with
#    `python fonts\make_fontstyle.py --selfcheck` (byte-identical to
#    candidate.ini at factor 2). The file holds 90 styles, range floor 14
#    (MessageBodyHtml, never scaled); the generator's stdout prints the
#    scaled styles only (88) — read the file, not stdout.
python fonts\make_fontstyle.py 1.5 packages\15x\FontStyle-15x.ini
python fonts\make_fontstyle.py 3   packages\3x\FontStyle-3x.ini

# 3. Selective city-HUD art dat  (emits refmap-<tag>.csv used by step 4)
python selective-safe\build_selective_safe.py --factor 1.5
python selective-safe\build_selective_safe.py --factor 3

# 4. Static region-dialog dat  (run AFTER step 3 of the same factor)
python dialog-static\build_dialog_static.py --factor 1.5
python dialog-static\build_dialog_static.py --factor 3
```

Default (no `--factor`) reproduces the original untagged 2x outputs.

**These four steps do not produce a whole tier.** `ItemIcons` /
`ItemIconsSub` are built per tier by `itemicons\stage_icons.py --factor` and
`itemicons\build_itemicons_sub.py --factor`; the mod-override packages are
additional outputs of the two builders in steps 3 and 4 (`ThirdPartyUI` and
`WarriorUI` from `selective-safe`, `CamUI` and `SaveWarningUI` from
`dialog-static`). The block above is the font-and-art core of tier
generation — read the builders before quoting a command, do not infer one
from this file.

## Generator behaviour (all default to N=2 = original behaviour)

- **`upscale\Upscale2x.cs`** — `--factor N` (2/3 integer block-replicate
  nearest-neighbor; 1.5 fractional, resampler chosen per sheet by the policy
  chain above) and `--normalize-names` (rewrite SC4 `T-/G-/I-` filenames to
  canonical `0x` form). Output dims use `floor(v×N+0.5)`. `--hq` bicubic
  also honours `--factor`. N=2 output unchanged (byte-verified).
- **`upscale\Upscale2x.cs`** — `--hybrid thin|bold` (v4.8.0, #203): the
  fractional-factor straight-edge hybrid, `UpscaleHybrid`. Straight edges
  copy at one consistent stroke width by the edge-claim rule (`thin` gives an
  odd-width stroke's tie block away, `bold` takes it; `thin` ships); curves,
  diagonals and pictures take the key-aware 2:1 area average, with the
  transparency mask held to nearest's prediction. Dispatched AFTER the even
  reduce and BEFORE nearest; refuses integer factors (FATAL if it fires at
  one — 2x/3x stay byte-identical), even-strips, no-smooth, thumbnails and
  fine-key (1–2 px) sheets, each counted in the run summary. Held
  pixel-identical to the Python reference (`research\sharp15\x3_candidates.py`
  `thin_h`) by `upscale\gate_hybrid_parity.py <csharp_tree> <reference_tree>`
  — 2206 of 2206 sheets, dimensions included; `--selftest` proves the gate
  can fail; exit 0 parity / 1 mismatch / 2 inputs missing.
- **`upscale\Upscale2x.cs`** — `--thumbnails <file>`: sheets named in that
  file keep NEAREST under `--hybrid` — a rendered lot/building picture wants
  hard pixels, and the 2x/3x block copy is the user's reference for "sharp".
  DERIVED, never hand-listed: `upscale\find_thumbnails.py` reads the DBPF
  index of `packages\15x\z_SC4UIScale_ItemIcons-15x.dat` and
  `ItemIconsSub-15x.dat` directly (any tier carries the same TGIs) and writes
  `upscale\thumbnails.txt` — 485 TGIs, all group `6a386d26`, the engine's
  own item-icon bindings at second hand. `Rebuild-Corpus.ps1` refuses to run
  if the file is missing or holds fewer than 300 entries.
- **`upscale\Upscale2x.cs`** — `--cell-strips <file>`: sheets named in that
  file are sampled PER STATE, so a snapped sheet's cell boundaries cannot
  drift and let one state's art bleed into the next cell. The file is
  generated by `upscale\find_cell_strips.py` from the `.UI` bindings — 193
  sheets. Do NOT scope this by `CellUnit`: that guess moved 1186 of 2206
  sheets and displaced an advisor aperture. Proven no-op at integer factors:
  2206 PNGs, 0 changed at 2x and 3x.
- **`fonts\make_fontstyle.py`** — emits `FontStyle-<tag>.ini` from
  `FontStyle.default.ini`, changing only the `[Font Styles]` size field;
  CRLF and every other byte preserved. `--selfcheck` proves factor 2
  reproduces `FontStyle.candidate.ini` exactly.
- **`selective-safe\build_selective_safe.py`** — `--factor` routes upscale
  dir, stage, `.dat` (→ `packages\<tag>\`), `refmap-<tag>.csv`,
  `package-list-<tag>.txt`; `imagerect` scales via `scale_len`
  (round-half-up). Clone-IID scheme (`iid ^ 0x53430001`) and font-GUID
  conversion unchanged.
- **`dialog-static\build_dialog_static.py`** — `--factor` routes upscale dir,
  reads `refmap-<tag>.csv`, stage, `.dat` (→ `packages\<tag>\`), report
  (`dialog-static\REPORT-<tag>.md`); `area`/`imagerect`/`rowheight`/
  `gutters`/etc. scale via `scale_len`; node-for-node `verify_doubled` runs
  at every factor. **`imagerect` scales only where that control's ART
  scaled**, and the test reads `art_plan` — which is built from the **stock**
  upscale store alone. Mod-supplied art (`thirdparty-art\`) is therefore
  always `left1x` there, so it is routed through `RUNTIME_BOUND_2X` instead,
  scoped to the package that ships the scaled bitmap. `TP_MOD_ONLY` covers
  dialogs a mod ADDS (exemption from the stock-twin assert, proven by
  absence from the stock corpus) and `TP_ART_DANGLING` covers refs proven
  absent everywhere.

## Regeneration

Re-run the numbered command blocks above for the desired factor. The upscale
dirs (`upscale\preview-15x\`, `upscale\preview\`, `upscale\preview-3x\` —
produced by `upscale\Rebuild-Corpus.ps1`) and build intermediates
(`selective-safe\stage-<tag>\`, `dialog-static\stage-<tag>\`,
`selective-safe\refmap-<tag>.csv`, `package-list-<tag>.txt`) are regenerable
and are not part of the shippable package. To add another factor `K`, run the
same steps with `--factor K`; the generators auto-derive the tag (`Kx`, or
`p_qx` for a non-integer like 2.5 → `2_5x`) and the output paths.

---

## z_SC4UIScale_CamGraphLabels.dat

| | |
|---|---|
| **Built by** | `tools\itemicons\build_cam_graph_labels.py` |
| **Source of truth** | `tools\packages\shared\z_SC4UIScale_CamGraphLabels.dat` |
| **Deployed to** | `Plugins\zzz-SC4UIScale\z_SC4UIScale_CamGraphLabels.dat` |
| **Entries** | 1 |
| **Tier** | **NONE — tier-independent.** A string has no geometry, so there is no `-15x` / `-2x` / `-3x` triple and no `.x1-disabled` variant. It is one of three untagged single-form packages — `MenuFix` (6 entries) and `WebText` (3 entries) are the others; every other row in the `$EXPECTED` table carries a tier tag, as do NamIcons, UncoveredIcons and CsiIcons which sit outside it. `MenuFix` is asserted by the integrity test but deliberately NOT deployed — it rewrites CAM's gameplay submenu data |
| **Gate** | by LOCATION only: nothing except CAM binds the instance, so it is inert without CAM |
| **In deploy?** | yes — `Deploy-OnGameClose.ps1` |
| **In integrity?** | yes — `Test-DatIntegrity.ps1` |

**What it is:** the one LTEXT that CAM's Power and Water charts ask for and
no installed file provides — `{0x2026960B, 0x6A231EAA, 0xFF5D2E9F}` =
`"Exported"`, 20 bytes. Without it the 4th legend row draws a checkbox and a
swatch with no caption. We ADD a resource; we never modify CAM's file.

**Deliberately without CAM's trailing CRLF.** `Imported` (`0xFF5D2E9E`), the
row directly above ours in the same legend, has none either; copying CAM's
`Exported\r\n` would render our row two lines tall.

**DELETE** this package, its builder, its deploy line and its integrity row
if CAM ever fixes the id upstream (reported: `UPSTREAM-CAM-REPORT.md` §4).
