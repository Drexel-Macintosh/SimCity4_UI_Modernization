# DBPF Extraction Notes — SimCity 4 UI Art (2026-07-21)

## Tool

`DbpfExtract.exe <archive.dat> <outDir> [typeIdHexFilter]`

- Source: `DbpfExtract.cs` (single file, no dependencies). Built with classic csc:
  `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /optimize+ /platform:anycpu /out:DbpfExtract.exe DbpfExtract.cs`
- Omit the filter to extract every entry. Filter used for this inventory: `0x856DDBAC` (PNG/UI images).
- Output names: `T-<type>_G-<group>_I-<instance>.png` (lowercase hex, raw decompressed bytes).
- Each run also writes a manifest CSV beside the output with columns
  `TypeID,GroupID,InstanceID,Offset,RawSize,Compressed,OutSize,PngMagic,File`.

## Format findings

- All seven archives are **DBPF v1.0, index version 7.0** (20-byte index entries:
  TypeID, GroupID, InstanceID, FileOffset, FileSize — all little-endian; header index
  minor version field at 0x3C reads 0). Hole count 0 everywhere.
- Every archive carries a **compressed-entry directory** (DIR, TGI `E86B1EEF/E86B1EEF/286B1F03`),
  16 bytes per record: TGI + decompressed size. The tool uses it and additionally
  falls back to per-entry QFS signature detection (`0x10FB` at offset 4 after the
  4-byte little-endian compressed-size prefix).
- **QFS/RefPack**: standard EA algorithm — 2/3/4-byte LZ control codes + literal-run
  (0xE0–0xFB) + stop (0xFC–0xFF), overlapping byte-wise history copies, 3-byte
  big-endian uncompressed size after the 0x10FB signature. All 188 compressed
  type-0x856DDBAC entries decompressed with zero failures, exact-length verified.

## Inventory results (filter 0x856DDBAC)

| Archive | Total entries | DIR-listed compressed | 0x856DDBAC matches | Extracted | QFS among them | True PNG magic |
|---|---|---|---|---|---|---|
| SimCity_1.dat | 60,440 | 48,880 | **2,280** | 2,280 | 188 | 2,206 |
| SimCity_2.dat | 15,238 | 13,661 | 0 | 0 | — | — |
| SimCity_3.dat | 7,495 | 6,600 | 0 | 0 | — | — |
| SimCity_4.dat | 9,797 | 8,810 | 0 | 0 | — | — |
| SimCity_5.dat | 5,619 | 4,896 | 0 | 0 | — | — |
| EP1.dat | 4,099 | 3,903 | 0 | 0 | — | — |
| SimCityLocale.DAT | 5,963 | 1,651 | 0 | 0 | — | — |

**All UI image art lives in SimCity_1.dat.** 2,280 entries, no duplicate TGIs,
zero extraction failures, ~31.3 MB total.

### Surprise: type 0x856DDBAC is not PNG-only

74 of the 2,280 entries are other image formats stored under the same type ID
(they still carry the `.png` extension from the naming rule — check magic bytes,
not extension):

- 41 × JPEG (`FF D8 FF E0` JFIF)
- 26 × EA SHPI (`SHPI` .fsh sprite/shape containers)
- 7 × BMP (`BM`)

The manifest's `PngMagic` column flags which is which.

### Validation

- All 2,206 PNG-magic files end with a proper `IEND` chunk (2,206/2,206).
- Decode spot-check via System.Drawing on the 10 largest: all load with sane
  dimensions — e.g. 800x600 splash, 3480x56 / 3304x58 / 1998x54 toolbar strips,
  518x399 dialog art. Toolbar strips are prime 2x-upscale targets.
- Group IDs `0x46a006b0` and `0x1abe787d` are near-mirrors: of 810 entries in
  group `0x46a006b0`, 743 have a byte-identical (MD5-verified) twin at the same
  instance ID in `0x1abe787d`, 0 differ, 67 have no twin — when re-injecting 2x
  art, both groups likely need the replacement.
