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

- **Compression directory (DIR): absent from what WE write, because we write nothing
  compressed.** The DIR record exists only to flag which entries are QFS-compressed. All
  our entries are uncompressed, so no DIR is written; the packer refuses to pack a file
  named with the DIR TGI.

  > **CORRECTION (2026-08-31).** This bullet previously claimed that `SimCity_1.dat`
  > "contains **no** DIR entry" and that its PNG payloads are all stored uncompressed, and
  > concluded that "uncompressed, no DIR" is how the game ships its own UI art. **All three
  > statements are false.** Measured against the retail archive:
  >
  > | claim | measured |
  > |---|---|
  > | SimCity_1.dat has no DIR | it has one, at TGI **{0xE86B1EEF, 0xE86B1EEF, 0x286B1F03}**, offset 142,598,197, 782,080 bytes |
  > | — | **48,880 of its 60,440 records (80.9%) are QFS-compressed** |
  > | its PNGs are all plain PNG | 2,280 PNG (0x856DDBAC) records, of which **188 are listed as compressed** |
  >
  > The DIR record's stride is **16 bytes** — four uint32: Type, Group, Instance,
  > decompressed size. 782,080 / 16 = 48,880 exactly; 12 does not divide it. Anything that
  > walks this table at stride 12 misaligns after the first record and can report a
  > compressed entry as "not listed" (`row15-probe/decode_exemplar.py` and `decode_s3d_plate.py` both
  > do this — see below). Positive control for the stride: at 16, **all 48,880 entries
  > resolve to a record that really exists in the index and every one declares a size
  > larger than its own on-disk size**; at 12, 48,879 of 65,173 name records that do not
  > exist. `row15-probe/dbpfcore.py: read_dir()` walks it correctly and asserts the stride.
  >
  > **What survives:** the packer's actual behaviour is still correct. An archive with no
  > compressed entries legitimately needs no DIR, so "we write all-uncompressed and emit no
  > DIR" remains right — it just is not what SC4 itself does, and must not be justified by
  > saying so.
  >
  > **What does not survive:** `DbpfPack.cs` line 44 guards on
  > `DirType = DirGroup = 0xE86B1EEE`. The real type SC4 uses is **0xE86B1EEF** (…EF, not
  > …EE). The guard at line 108 therefore does **not** catch a genuine DIR record handed to
  > the packer; a real DIR file would be packed straight through as an ordinary payload.
  > The comment at lines 28–29 carries the same wrong TGI. Not fixed here — changing the
  > constant means rebuilding `DbpfPack.exe`, which is a separate decision.
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
