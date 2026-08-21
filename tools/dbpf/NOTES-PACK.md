# NOTES-PACK — DbpfPack.exe (DBPF v1.0 writer)

Writer half of the DBPF toolchain (sibling reader/extractor lives in this same folder).
Source: `DbpfPack.cs`, built with `csc.exe /optimize+` (.NET Framework 4, x64-agnostic AnyCPU).

## Usage

```
DbpfPack.exe <inDir> <out.dat>                pack folder of TGI-named files into a DBPF 1.0 archive
DbpfPack.exe --list <archive.dat>             dump header + full index of any DBPF 1.x archive
DbpfPack.exe --extract <archive.dat> <outDir> extract RAW payloads as T-…_G-…_I-….bin (no QFS decompression)
```

Input filenames must match `T-0x########_G-0x########_I-0x########.<ext>` (any extension;
hex case-insensitive) — the naming the sibling extractor produces. Non-matching files are
skipped with a warning. Duplicate TGIs across files are a hard error. File bytes are copied
verbatim (a PNG goes in as raw PNG — which is exactly how SC4 stores Type 0x856DDBAC).

## Header written (96 bytes, all fields uint32 LE)

Verified field-for-field against the retail `SimCity_1.dat` header on this machine.

| Offset | Value | Meaning |
|--------|-------|---------|
| 0x00 | `"DBPF"` | magic (bytes 44 42 50 46) |
| 0x04 | 1 | major version |
| 0x08 | 0 | minor version |
| 0x0C–0x14 | 0 | unknown/reserved (0 in retail file too) |
| 0x18 | unix time | date created (write time) |
| 0x1C | unix time | date modified (same value) |
| 0x20 | 7 | index major version |
| 0x24 | N | index entry count |
| 0x28 | offset | absolute offset of first index entry |
| 0x2C | N*20 | index size in bytes |
| 0x30–0x38 | 0 | hole count / hole offset / hole size (no holes written) |
| 0x3C | 0 | index minor version → index format **7.0** |
| 0x40–0x5F | 0 | reserved |

## Index version chosen: 7.0

20 bytes per entry, 5 uint32 LE: **TypeID, GroupID, InstanceID, file offset, file size.**
This matches `SimCity_1.dat` exactly: its header says count=60440, size=1208800, and
1208800 / 60440 = 20. (Index 7.1 would add a 6th dword and is not used by SC4's own data.)

## File layout produced

```
[96-byte header][payload 1][payload 2]…[payload N][index (N * 20 bytes)]
```

- Payloads are packed back-to-back starting at offset 0x60, no padding/alignment
  (the retail file has no alignment either; offsets are arbitrary).
- Index is written at the very end — same as `SimCity_1.dat` (its index offset + index
  size = its file size exactly).
- Entries are sorted by Type, Group, Instance for deterministic output. SC4 does not
  require any index order (the retail index is unsorted).

## Quirks / findings

- **Compression directory (DIR, TGI E86B1EEE/E86B1EEE/286B1F03): ABSENT, and must stay
  absent.** The DIR record exists only to flag which entries are QFS-compressed. All our
  entries are uncompressed, so no DIR is written; the packer actively refuses to pack a
  file named with the DIR TGI. Notably, `SimCity_1.dat` itself contains **no** DIR entry,
  and its Type 0x856DDBAC (PNG) payloads are stored as plain uncompressed PNG
  (`89 50 4E 47…` right at the index offset) — so "uncompressed, no DIR" is exactly how
  the game ships its own UI art.
- **Date fields**: retail file has real unix timestamps (0x3F4C65AE ≈ Aug 2003). We write
  current unix time to both. SC4 is not known to read them; they are informational.
- **Holes**: hole count/offset/size all zero; we never create holes (fresh sequential
  write). Retail file also has zero holes.
- **4 GiB limit**: offsets/sizes are uint32; the packer errors out rather than wrapping
  if the archive would exceed that (irrelevant for UI art overrides).
- `--extract` writes raw payload bytes with a `.bin` extension and does **not** QFS-
  decompress; it exists for byte-level roundtrip proof of archives this tool wrote.
  On third-party archives with a DIR record, extracted payloads may be QFS-compressed —
  use the sibling reader for real extraction.

## Roundtrip verification performed (2026-07-21, no game launch needed)

1. `--list` on retail `SimCity_1.dat` (144,589,077 bytes): parsed DBPF 1.0 / index 7.0,
   60,440 entries @ 0x88BCF35, 1,208,800-byte index — all figures agree with the raw
   header bytes and with index_offset + index_size = file_size.
2. Pulled 3 real PNG payloads (Type 0x856DDBAC) out of `SimCity_1.dat` byte-for-byte,
   named them per the TGI convention, added 1 synthetic file + 1 decoy with a
   non-matching name.
3. Packed: decoy skipped with warning, 4 entries written.
4. `--list` on the produced archive: all 4 TGIs, offsets and sizes correct
   (96 + Σ payloads = index offset; + 4*20 = file size).
5. `--extract` and byte-compared every payload against the original inputs:
   **4 / 4 byte-identical** — including the three genuine game PNGs, so the chain
   game archive → extracted file → packed archive → extracted file is lossless.
6. Header of the produced archive dumped dword-by-dword: structurally identical to the
   retail header (only dates/count/offset/size differ, as they must).

## SC4 override use

Drop the produced `.dat` in `<user>\Documents\SimCity 4\Plugins\`. SC4 loads plugins
alphabetically after its own .dats; a later definition of the same TGI wins, so
re-supplying a TGI with new (e.g. 2x-resolution) data overrides the original. Name the
file to sort late (e.g. `z_...dat`) if it must also beat other plugins.
