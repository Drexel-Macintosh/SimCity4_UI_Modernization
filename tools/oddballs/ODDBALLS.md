# ODDBALLS — the 74 non-PNG Type-0x856DDBAC UI resources (SimCity_1.dat)

2026-07-21. Of the 2,280 Type `0x856DDBAC` UI image resources extracted from `SimCity_1.dat`
(`..\dbpf\extracted\SimCity_1\`), 2,206 are true PNGs (handled by the main upscale pipeline)
and **74 are not PNG despite the `.png` extension**. This folder converts those 74 to 2x.
Classification here was done by **magic bytes** (fresh re-scan by `OddballConvert.exe`, not
trusting extensions or the manifest); the result agrees with `extract-manifest.csv`'s
`PngMagic=no` rows exactly: **41 JPEG/JFIF, 26 EA SHPI (FSH), 7 BMP, 0 unknown.**

## Outputs

| Folder | Contents |
|--------|----------|
| `converted2x\` | All 74 as **2x nearest-neighbour PNG** (`T-0x…_G-0x…_I-0x….png`). Reference set / for a PNG-pipeline experiment. |
| `native2x\` | All 74 at 2x **in their ORIGINAL format** — 41 `.jpg` (re-encoded quality 95), 7 `.bmp` (uncompressed 24bpp), 26 `.fsh` (rebuilt SHPI container, same bitmap code). **This is the set to pack** — the game presumably expects each resource in its shipped format. |
| `oddball-report.csv` | Machine-readable per-file log (TGI, format, dims, action, notes). |

Naming is the `DbpfPack.exe` convention: `T-0x########_G-0x########_I-0x########.<ext>`
(lowercase hex). The packer accepts **any extension** (TGI comes from the name, bytes are
packed verbatim), so `.jpg`/`.bmp`/`.fsh` pack fine and keep the folder self-describing.

Upscale is exact 2x2 pixel replication (LockBits), identical in spirit to the main
`Upscale2x.exe` nearest-neighbour path. No resampling, no filtering.

## What the 74 actually are

- **41 JPEG** — all group `0xCA133ECB`: tutorial screenshot pages (UI captures with
  highlight arrows), 40 at 125x195 plus one at 160x138. 24bpp JFIF, no trailing data
  after the EOI marker.
- **26 FSH** — all group `0x46A006B0`: dispatch/tutorial overlay sprites with alpha
  (fire-dispatch map pins, MySim dispatch portraits, big orange tutorial arrows —
  directory entry names `1431`, `0000`, `1441`, `2bb1`, `4bb0`, `rail`, `cb78`, `ea3e`).
- **7 BMP** — all group `0x6A1EED2C`: tiny 16x16 (one 15x15) 24bpp uncompressed
  icon/thumbnail bitmaps.

## FSH findings (all 26 files)

Format refs: SC4D Encyclopaedia "FSH Format", fshtool, and the FshFormat Photoshop
plugin source (BGRA plane order, `code & 0x80` = QFS-compressed entry).

- Every file is a single-entry SHPI container; **the only bitmap code present is `0x7D`
  (32-bit A8R8G8B8, stored B,G,R,A per pixel, rows top-down)**. No DXT1 (`0x60`), no
  DXT3 (`0x61`), no palettized (`0x7B`), no QFS-compressed entries — so full native
  re-encode was possible for all 26; the DXT "decode-only, report and skip" path was
  never needed.
- Directory ids seen: `G352` (14 files), `G264` (6), `G290` (6). By directory entry
  name: `1431` 4, `0000` 6, `1441` 1, `2bb1` 1, `4bb0` 1, `rail` 6, `cb78` 1, `ea3e` 6.
- Bytes 24..31 (between the 8-byte directory and the entry header) are the EA writer
  filler string `"Buy ERTS"` — preserved verbatim.
- 20 files carry a trailing **`0x70` name-attachment block** (e.g.
  `14315E00_fire_dispatch_atstation`); the 6 `G264` (`0000`) files have block-size 0 and
  no attachment. Attachments and the block-size-0 convention are preserved verbatim.
- The four misc uint16 fields (center x/y, pos x/y) are **all zero** in every file, so no
  question of whether to double them arose; they are copied verbatim.

### FSH rebuild method

Output = original bytes `[0 .. pixelStart)` + new 2x pixel data + original
`[pixelEnd .. EOF)`, with exactly four patches: SHPI file-size field, entry block-size
(`16 + newPixelBytes`, or kept 0 where it was 0), width, height. Every output was
re-parsed and pixel-compared against the in-memory 2x source (exact), and the attachment
tail byte-compared (exact).

## Per-file table

TGI = Type/Group/Instance. All 74 have both a `native2x\` and a `converted2x\` output;
none failed.

| TGI | Real format | Dimensions | Action |
|-----|-------------|------------|--------|
| `0x856DDBAC/0x6A1EED2C/0x2A1F0276` | BMP | 16x16 → 32x32 | 2x BMP 24bpp (native, exact) + 2x PNG |
| `0x856DDBAC/0x6A1EED2C/0x6C3568C4` | BMP | 16x16 → 32x32 | 2x BMP 24bpp (native, exact) + 2x PNG |
| `0x856DDBAC/0x6A1EED2C/0x6C3568C5` | BMP | 16x16 → 32x32 | 2x BMP 24bpp (native, exact) + 2x PNG |
| `0x856DDBAC/0x6A1EED2C/0x6C3568C6` | BMP | 16x16 → 32x32 | 2x BMP 24bpp (native, exact) + 2x PNG |
| `0x856DDBAC/0x6A1EED2C/0x6C3568C7` | BMP | 15x15 → 30x30 | 2x BMP 24bpp (native, exact) + 2x PNG |
| `0x856DDBAC/0x6A1EED2C/0x6C3568C8` | BMP | 16x16 → 32x32 | 2x BMP 24bpp (native, exact) + 2x PNG |
| `0x856DDBAC/0x6A1EED2C/0x6C3568C9` | BMP | 16x16 → 32x32 | 2x BMP 24bpp (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x14315E00` | FSH G352/'1431'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x14315E10` | FSH G352/'1431'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x14315E20` | FSH G352/'1431'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x14315E30` | FSH G352/'1431'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x14315E40` | FSH G264/'0000'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x14315E50` | FSH G264/'0000'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x14315E51` | FSH G264/'0000'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x144161A0` | FSH G264/'0000'/code 0x7D | 64x64 → 128x128 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x144161A1` | FSH G264/'0000'/code 0x7D | 64x64 → 128x128 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x144161A2` | FSH G264/'0000'/code 0x7D | 64x64 → 128x128 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x144161A3` | FSH G352/'1441'/code 0x7D | 64x64 → 128x128 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x2BB12D1F` | FSH G352/'2bb1'/code 0x7D | 64x64 → 128x128 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x4BB0ECF3` | FSH G352/'4bb0'/code 0x7D | 64x64 → 128x128 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x6BE09921` | FSH G352/'rail'/code 0x7D | 128x128 → 256x256 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x6BE09922` | FSH G352/'rail'/code 0x7D | 128x128 → 256x256 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x6BE09923` | FSH G352/'rail'/code 0x7D | 128x128 → 256x256 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x6BE09924` | FSH G352/'rail'/code 0x7D | 128x128 → 256x256 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x6BE09925` | FSH G352/'rail'/code 0x7D | 128x128 → 256x256 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0x6BE09926` | FSH G352/'rail'/code 0x7D | 128x128 → 256x256 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0xCB783D3A` | FSH G352/'cb78'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0xEA3EE100` | FSH G290/'ea3e'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0xEA3EE110` | FSH G290/'ea3e'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0xEA3EE120` | FSH G290/'ea3e'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0xEA3EE130` | FSH G290/'ea3e'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0xEA3EE140` | FSH G290/'ea3e'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0x46A006B0/0xEA3EE150` | FSH G290/'ea3e'/code 0x7D | 256x256 → 512x512 | 2x FSH 0x7D (native, exact) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x00000003` | JPEG | 160x138 → 320x276 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x0A5E3EB6` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x0A5E3EC8` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x0A5E3ED8` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x2A5E3EA4` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x2A5E3EBE` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x2A5E3EC2` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x2A5E3EE6` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x2A5E3F04` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x2A5E4EC4` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x2A5E53EB` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x4A5E4EAE` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x4A5E4EB9` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x4A5E4EC9` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x4A5E53C7` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x4A5E53EF` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x4A5E53F6` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x6A5E3ED2` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x6A5E3EDC` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x6A5E3EF6` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x6A5E4EB4` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x6A5E53E0` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x6A5E53FB` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x8A5E4EA2` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0x8A5E53DC` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xAA5E3EE2` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xAA5E3F0B` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xAA5E522A` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xAA5E53CE` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xAA5E53D5` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xAA5E53D8` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xAA5E53F3` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xCA39EFDD` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xCA5E3ECD` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xCA5E3EEB` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xCA5E4EBF` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xCA5E53CB` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xEA39E645` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xEA5E4EA8` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xEA5E53D2` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |
| `0x856DDBAC/0xCA133ECB/0xEA5E53E7` | JPEG | 125x195 → 250x390 | 2x JPEG q95 (native) + 2x PNG |

## Files that could NOT be 2x'd natively

**None.** All 74 have a native-format 2x output. The only qualitative loss:

- **JPEG re-encode is lossy by nature** (the 41 `.jpg`). Encoded with GDI+ at quality 95
  (GDI+ uses 4:2:0 chroma subsampling). Nearest-neighbour-doubled JPEG content then
  re-compressed at q95 loses very little visibly, but it is not bit-exact the way the
  BMP/FSH outputs are. If bit-exact JPEG content ever matters, the fallback is packing
  the `converted2x\` PNGs instead — IF the game's loader sniffs content rather than
  trusting an internal format assumption (unproven; see risks).

## Risk notes (read before packing)

1. **Format acceptance is unproven in-game.** These resources shipped as JPEG/FSH/BMP
   inside a "PNG" type id; whether SC4's loader sniffs magic per resource (likely, given
   the mixed formats under one type id) or hardwires a decoder per TGI is unknown until
   a table/game test. The `native2x\` set minimizes this risk by keeping every resource
   in its shipped container format with the same bitmap code.
2. **Dimension acceptance is unproven** — same caveat as the whole 2x experiment: the
   game may scale-to-fit (good), clip, or misrender resources that changed size. The
   FSH sprites are dispatch/tutorial overlays, so a quick dispatch-screen / tutorial
   check will show whether 2x here helps or must be excluded from the pack.
3. **FSH `0000`/G264 files have block-size 0** in the entry header (last-block
   convention); the rebuilt files keep 0 there, matching the originals, and the other
   20 keep `16 + pixelBytes`. Both observed conventions are preserved as found.
4. **JPEG q95 outputs are ~3-6x the original byte size** (tiny in absolute terms).
   DBPF has no per-entry size ceiling below 4 GiB; irrelevant, noted for completeness.
5. **Not yet in any .dat.** Nothing here overrides anything until the files are packed
   (e.g. added to the `z_SC4UIScale_Art_2x` input set) with `DbpfPack.exe`. Also note
   the current 2x preview .dats were built PNG-only, so these 74 TGIs are absent there.

## Rebuild / rerun

```
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /target:exe /platform:anycpu /optimize+ ^
    /reference:System.Drawing.dll /out:OddballConvert.exe OddballConvert.cs

OddballConvert.exe ..\dbpf\extracted\SimCity_1 .
```

Idempotent (outputs simply overwritten). The tool self-verifies every output: BMP and
FSH are reloaded and pixel-compared exactly; JPEG reloaded and dimension-checked; FSH
size field, entry header, and attachment tail byte-compared. Run summary from this
build: `native2x ready: 74 / 74, errors: 0`.
