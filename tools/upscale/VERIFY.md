# Upscale2x - verification evidence

Batch nearest-neighbor PNG upscaler for SimCity 4 UI art. Verified 2026-07-21 on
the dev box (Win11, .NET Framework 4, csc.exe v4.0.30319, PowerShell 5.1).

> **2026-07-22 update — factor parameter.** The tool now takes `--factor N`
> (default 2; 2/3 = integer block-replicate NN, 1.5 = fractional NN) and
> `--normalize-names` (rewrite SC4 `T-/G-/I-` filenames to the canonical
> `T-0x..._G-0x..._I-0x....png` form). Output dims use round-half-up
> `floor(dim*N+0.5)`, matching the DAT builders' `imagerect`/`area` scaling.
> The default `--factor 2` path is byte-for-byte identical to the original
> (re-verified: factor-2 output equals the shipped `preview\` set). `--hq`
> bicubic honors `--factor` too. See `tools\packages\PACKAGES.md` for the 1.5x
> (no colorkey/alpha bleed — proven by a 0-new-colors check) and 3x usage.

> ## ⛔ 2026-08-06 — TWO CORRECTIONS. READ BOTH BEFORE TOUCHING THIS TOOL.
>
> **1. `--hq` IS NEVER AUTOMATIC. NEAREST IS THE DEFAULT AT EVERY FACTOR.**
> On 2026-08-06 `--hq` was made automatic for fractional factors, on the theory
> that 1.5's uneven row duplication caused white seams. It did not, and the
> rejected option failed in the way `README.md` had documented for weeks:
> magenta `0xFF00FF` is the game's **transparency key**, interpolation moves an
> exact key pixel to `0xFE01FE`, the key test misses it, and the key colour
> DRAWS. The user's Mayor Rating bar went pink within one launch.
>
> ⚠ **The "0-new-colors check" cited two paragraphs above is the whole
> argument.** Nearest-neighbour only COPIES source pixels, so it introduces no
> colour the source lacks — which means a white line absent from the 1x art can
> never be an NN artifact. That check already existed here and already proved
> the resampler innocent. It was not read.
>
> **2. OUTPUT DIMS ARE NO LONGER ALWAYS `floor(dim*N+0.5)` AT FRACTIONAL
> FACTORS.** The game cell-divides art sheets with an integer divide baked into
> its own code — `cell = img->Width()/3` (NineSlice — the `.UI`-bound drawers
> are `GZWinBMP`'s slot-88 draw `0x009BC325` (EDGE branch) and `GZWinBtn`
> `0x009B05E0`; each divides its own source rect, then calls blitter
> `0x008D8800`, which contains no divide. `0x00794100` is
> `cSC4WinAlertBorder`'s own draw and appears in no `.UI` — see
> `tools\research\SC4-UI-ENGINE.md` §4.6c; attribution corrected 2026-08-30)
> and `width/4` (four-state strips). At 1.5 that divisibility broke for **31%**
> of `/3`-eligible and **43%** of `/4`-eligible dimensions, so cells drifted and
> each drew a sliver of the next state — the actual white seam. `ScaleDim` now
> snaps a fractional factor's output to preserve the source's divisibility
> (`CellUnit` = 12/4/3/1, ties up), and `UpscaleNearest` maps output→source by
> the real ratio `ox*w/ow` so a snapped target still resamples the whole image.
>
> **Integer factors are returned untouched and stay byte-identical** — re-proven
> 2206/2206 against the pre-change `preview\` set. That gate is what makes the
> change safe to ship without re-verifying 2x and 3x on screen; run it again
> after any edit to `ScaleDim` or `UpscaleNearest`.
>
> Builders are unaffected: `build_selective_safe.py::clamp_rect_to_art` reads
> the REAL PNG header (`png_wh`) and clamps `imagerect` to the art that exists,
> logging every clamp. Full write-up: `_tests\REGRESSION.md` #143.

## Usage

    Upscale2x.exe <inDir> <outDir> [--hq]

- Recurses `inDir`, mirrors the directory structure into `outDir`, preserves the
  exact filenames (they encode game resource IDs).
- Default mode = **nearest-neighbor 2x**: every source pixel becomes a 2x2 block
  with identical ARGB bytes (pure LockBits copy, no Graphics, no resampling).
  Crisp and byte-exact - the safe choice for pixel art.
- `--hq` = **HighQualityBicubic** with the alpha-safe recipe:
  `CompositingMode.SourceCopy` + `PixelOffsetMode.Half` +
  `ImageAttributes.SetWrapMode(TileFlipXY)` (edges mirror instead of sampling
  transparent black outside the image - no dark fringes).
- Skips non-`.png` extensions; a `.png` NAME whose bytes are not PNG
  (checked by magic `89 50 4E 47 0D 0A 1A 0A`) is listed as `BADMAGIC` and NOT
  processed (archive lesson: image magic, not extension).
- Output is always 32bppArgb PNG. Indexed/palette sources are expanded exactly:
  1/4/8bpp via manual palette lookup, everything else via a pixel-exact
  SourceCopy conversion. Exit code 0 = no failures.

Files in this folder: `Upscale2x.cs` (source), `Upscale2x.exe`, `Build.ps1`,
`Make-TestPngs.ps1` (synthetic test set), `Verify-Upscale.ps1` (checker),
`test\` (synthetic in/out), `preview\` (real batch output).

## Synthetic test set (`Make-TestPngs.ps1` -> `test\`)

**The corpus is generated, never committed.** `tools\upscale\test\` is
gitignored, so none of the names below is a file in the repo — run
`Make-TestPngs.ps1` and it writes all eight into `test\in\`. They are listed
here as fixture names, not as links.

| file | purpose |
|---|---|
| **rgba_gradient_64x48.png** | 32bppArgb, deterministic per-pixel formula, 4 known corners incl. a HALF-ALPHA green premultiply canary and a fully-transparent pixel with non-zero blue |
| **indexed_pal_64x48.png** | hand-crafted colortype-3 palette PNG **with tRNS** (entry 0 fully transparent). GDI+ auto-expands pal+tRNS to 32bppArgb on load |
| **indexed_opaque_64x48.png** | same palette PNG **without tRNS** - loads as `Format8bppIndexed`, exercises the tool's manual palette-expansion path |
| **flat_opaque_32x32.png** | solid `FF4D90C9` - HQ no-color-shift / no-edge-bleed check |
| **flat_semi_32x32.png** | solid `80 28C85A` (alpha 128) - HQ premultiplication canary |
| **sub\0x856ddbac_...png** | odd size 5x7 in a subfolder, SC4-resource-ID-style name - recursion + name preservation + odd-dimension doubling |
| **notes.txt**, **fake_webp.png** | decoys: non-PNG extension + RIFF/WEBP bytes wearing a .png name |

## Results - `Verify-Upscale.ps1`: ALL 49 CHECKS PASSED (exit 0)

### Nearest-neighbor (default)

- Both runs exit 0; report shows `Processed: 6, Skipped: 1 (non-.png),
  Bad magic: 1 (fake_webp.png)`, decoys absent from output.
- Dimensions exactly doubled for all 6 images (64x48->128x96, 32x32->64x64,
  5x7->10x14).
- **Full byte-for-byte proof**: every source pixel equals its entire 2x2 output
  block exactly - 0 mismatches across all 11,299 source pixels (3072+3072+3072
  +1024+1024+35). This is stronger than a spot check: alpha, RGB, indexed
  expansion and edge pixels are all covered with zero tolerance.
- Corner spot checks (src -> out, hex AARRGGBB):
  - opaque red (0,0): `FFFF0000 -> FFFF0000`
  - half-alpha green (63,0): `8000FF00 -> 8000FF00` (no premultiplication:
    G=255 survived under alpha 128)
  - transparent-with-blue (0,47): `000000FF -> 000000FF` (RGB under alpha 0
    preserved, not zeroed)
  - opaque white (63,47): `FFFFFFFF -> FFFFFFFF`
  - palette entry 0 (0,0): `00000000 -> 00000000`; entry 10 (63,47):
    `FFA05F46 -> FFA05F46` (both indexed variants)
- Alpha histogram: all 256 bins satisfy `out == 4 x src` exactly
  (samples: a=0: 12->48, a=128: 13->52, a=255: 14->56).

### High-quality (--hq)

- Dimensions exactly doubled for all 6 images.
- Flat opaque: all 4096 output pixels exactly `FF4D90C9` - **zero color shift
  on opaque pixels and zero edge bleed** (edges/corners included, thanks to
  TileFlipXY; without it bicubic samples transparent black outside the border).
- Flat semi-transparent canary: `80 28C85A` round-trips with max per-channel
  deviation 1 (GDI+ internal rounding; no premultiply darkening).
- Gradient alpha roughly preserved: mean alpha 127.596 -> 127.603
  (delta 0.006); alpha-histogram L1 distance (out/4 vs src) = 7.4% of pixels
  (bicubic legitimately redistributes neighbouring alpha values).

## Real batch - extracted\SimCity_1 -> preview\SimCity_1 (default NN mode)

    Processed : 2206      (output count on disk confirmed: 2206)
    Skipped   : 1  (non-.png extension)
    Bad magic : 74 (.png name but NOT PNG data - refused, listed by name)
    Failed    : 0         elapsed ~9.4 s

- The 74 bad-magic files are mislabeled non-PNG resources from the extractor:
  inspected headers show EA `SHPI`/FSH sprite containers (e.g.
  `T-856ddbac_G-46a006b0_I-14315e00.png`), JPEG/JFIF
  (`T-856ddbac_G-ca133ecb_I-00000003.png`), and BMP
  (`T-856ddbac_G-6a1eed2c_I-2a1f0276.png`). They need format-specific handling
  upstream, not PNG upscaling.
- Spot validation on real outputs (same full 2x2 byte-exact check as above):
  - `T-856ddbac_G-46a006b0_I-362b8543.png` 24bppRgb 800x600 -> 1600x1200,
    0/480,000 mismatches (exercises the non-indexed conversion fallback)
  - `T-856ddbac_G-1abe787d_I-0c0729aa.png` 32bppArgb 3480x56 -> 6960x112,
    0/194,880 mismatches, mean alpha 173.10 -> 173.10 (mixed-alpha UI strip)
  - `T-856ddbac_G-46a006b0_I-14416242.png` 32bppArgb 16x16 -> 32x32,
    0/256 mismatches (fully transparent placeholder, alpha kept at 0)

## Repro

    powershell -NoProfile -ExecutionPolicy Bypass -File .\Build.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File .\Make-TestPngs.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File .\Verify-Upscale.ps1

## 2026-09-01 - v4.8.0 straight-edge hybrid (`--hybrid thin --thumbnails`)

Full write-up: `_tests\REGRESSION.md` #203. At f=1.5 a copy cannot be even:
source columns get multiplicity 2,1,2,1, so a 1px stroke renders 1px or 2px by
the parity of its origin (advisor sheet 14015571, measured 2026-08-16: column
runs 1px x106 / 2px x110; 2x is 2px x216, 3x 3px x216, uniform). #200 had
already flipped the 1.5x default from the area average ("soft") to nearest, so
both horns were rejected on screen. `UpscaleHybrid` decides per 2x2 tie block:
a 3-of-4 majority copies; a tie that continues along the edge in the
neighbouring block (a straight edge) takes the edge-claim copy at one
consistent stroke width; every other block (staircase step, curve, picture)
takes the key-aware 2:1 area average. The transparency MASK is nearest's:
where nearest says key the pixel is exact `0xFFFF00FF`; where nearest says
colour but the average landed on the key by coverage, the pixel takes the
key-excluded average of its block. Dispatch order inside the exe: integer
factor (refused, FATAL if it ever fires), even-strips, no-smooth, thumbnails,
fine key (1-2px), then the hybrid. `thumbnails.txt` is DERIVED
(`find_thumbnails.py`: the 485 TGIs the ItemIcons + ItemIconsSub packages
carry, all group 6a386d26) and keeps nearest - user round 2: "Thumbnails are
sharp."

Evidence, all green at release:

- **Odd/even theorem** - `tools\research\sharp15\theorem_check.py` PASS. On
  synthetic strokes at every phase the edge-claim copy rule gives 1/3/4/6
  output px for source widths 1/2/3/4 (net 1.5w exact for even widths, thin
  policy for odd) with 0 invented colours; nearest gives 1|2 / 3 / 4|5 / 6
  (phase-dependent), the box average invents many.
- **Port parity** - `gate_hybrid_parity.py <csharp_tree> <reference_tree>`:
  **2206 of 2206** sheets byte-equal against the Python reference
  (`tools\research\sharp15\x3_candidates.py` thin_h), dimensions included.
  The lab result the user judged transfers to the shipped file only because
  the port is provably the same function. Even-strips / no-smooth /
  thumbnails / fine-key sheets are shipped bytes in the reference tree, so on
  those the gate is C# nearest against itself - a free dispatch control.
- **Integer control (law 95)** - 2x and 3x: **0 changed of 2206** sheets each
  (sha1 of every preview PNG against the pre-rebuild manifest). The exe's own
  summary at those factors reads `hybrid: 0 sheet(s) ... 2206 integer factor`;
  the dispatch refuses itself at an integer factor and the build FATALs if it
  ever fires there.
- **Colour key** - `gate_key_integrity.py` PASS at 1.5, 2 and 3 with zero
  exemptions added. `key_near` 10,251 -> 10,251 and `key_moved` 2,059 -> 2,059,
  unchanged from the v4.7.2 corpus. The nearest-key-mask rule replaced the 9
  hand-reverted keyed sheets of launch round 1.
- **Edge quality** - `_tests\Test-15xEdgeQuality.py` (integer tiers as its
  positive control, exit 2 = instrument fault; `--selftest` proves it can go
  red), shipped 1.5x corpus, v4.7.2 -> v4.8.0:

  | metric | v4.7.2 (nearest) | v4.8.0 (hybrid) | 2x / 3x control |
  |---|---|---|---|
  | swc (stroke-width consistency) | 0.2997 | 0.2237 | 0 |
  | cv1 (1px strokes) | 0.319 | 0.232 | 0 |
  | cv2 | 0.022 | 0.133 | 0 |
  | cv3 | 0.109 | 0.095 | 0 |
  | invented px | 1,270,876 | 6,391,698 | 0 |
  | soft_frac | 0.419 | 0.564 | 0 |
  | edge_w | 1.179 | 1.370 | 1.001 |

  The cv2 rise is largely the metric reading the exact-colour core of a 2px
  run whose one edge blended; the invented pixels are the blends at curves,
  the price of the AA branch. The baseline
  (`_tests\golden\15x-edge-quality-baseline.json`) was refreshed to v4.8.0
  as a deliberate act.
- Also run: `Test-DatIntegrity`, `Test-Builders -Factor 1.5`.

Be exact about what was judged on screen: launch 2 ran the round-1 tree with
the thumbnail sheets returned to shipped bytes. Two reference changes landed
after launch 2 (the straight-tie test no longer wraps at a cell edge; the
nearest-key-mask rule) and were verified by the gates above, not by a third
launch; their scope is the first/last block row or column of a cell and those
9 keyed sheets (SelectiveArt: 159 PNGs differ by 2-20 px each vs the round-2
dats; DialogStatic: 10 differ by 4-20 px). Third-party lanes (CamUI, NAM
icons, Web Button, Carbon skin art) still take nearest at 1.5x - not on the
screen the user judged, so not wired.
