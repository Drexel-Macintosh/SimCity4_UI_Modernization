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
> its own code — `cell = img->Width()/3` (NineSlice, VA `0x00794100`) and
> `width/4` (four-state strips). At 1.5 that divisibility broke for **31%** of
> `/3`-eligible and **43%** of `/4`-eligible dimensions, so cells drifted and
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

## Synthetic test set (Make-TestPngs.ps1 -> test\in\)

| file | purpose |
|---|---|
| `rgba_gradient_64x48.png` | 32bppArgb, deterministic per-pixel formula, 4 known corners incl. a HALF-ALPHA green premultiply canary and a fully-transparent pixel with non-zero blue |
| `indexed_pal_64x48.png` | hand-crafted colortype-3 palette PNG **with tRNS** (entry 0 fully transparent). GDI+ auto-expands pal+tRNS to 32bppArgb on load |
| `indexed_opaque_64x48.png` | same palette PNG **without tRNS** - loads as `Format8bppIndexed`, exercises the tool's manual palette-expansion path |
| `flat_opaque_32x32.png` | solid `FF4D90C9` - HQ no-color-shift / no-edge-bleed check |
| `flat_semi_32x32.png` | solid `80 28C85A` (alpha 128) - HQ premultiplication canary |
| `sub\0x856ddbac_...png` | odd size 5x7 in a subfolder, SC4-resource-ID-style name - recursion + name preservation + odd-dimension doubling |
| `notes.txt`, `fake_webp.png` | decoys: non-PNG extension + RIFF/WEBP bytes wearing a .png name |

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
