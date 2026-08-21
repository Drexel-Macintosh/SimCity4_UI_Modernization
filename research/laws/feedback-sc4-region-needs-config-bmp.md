# config.bmp Governs Which City Files Survive

SimCity 4 deletes city files silently. On region load, any `.sc4` whose tile position or size does not match a tile in that region's `config.bmp` is deleted from disk — no recycle bin, no prompt, no log line. `config.bmp` is the region's tile-grid authority; the `.sc4` files are only tenants of the grid it defines.

A region folder restored or hand-assembled without `config.bmp` is therefore not merely incomplete: the game improvises a default grid on first load and prunes the folder down to whatever happens to fit it. The failure is deterministic, so the same survivor set appears every time, which makes it look like a partial-restore problem rather than an active deletion.

The operational rule: never restore or hand-build a region folder without `config.bmp`, and verify that every region backup includes it before relying on that backup. Any test matrix that swaps regions in and out is one load away from destroying the cities it was supposed to preserve.

## Reconstructing config.bmp from savegames

If `config.bmp` is lost, it can be rebuilt from the coordinates already stored inside the surviving `.sc4` files. The recipe below has been validated to a 100% match against seven regions totalling 477 cities.

**Reading a `.sc4`.** Each city save is a DBPF archive:

- Index entry count at offset `0x24`
- Index offset at `0x28`
- Index entries are 20 bytes each: TGI (12 bytes) + file offset + file size

**Locating the coordinates.** The Region View Subfile carries the tile placement. Its TGI is:

```
Type  0xCA027EDB
Group 0xCA027EE1
Inst  0x00000000
```

The subfile is QFS/RefPack-compressed when bytes 4–5 of its payload are `10 FB`; in that case the uncompressed size is a 3-byte big-endian value at offset 6. After decompression, the fields are:

| Offset | Field |
| ------ | ----- |
| `0x04` | tile X |
| `0x08` | tile Y |
| `0x0C` | size X |
| `0x10` | size Y |

Sizes are in units of small tiles: 1 (small), 2 (medium), 4 (large).

**Writing config.bmp.** The file is a 24bpp bottom-up BMP. Image row 0 — the top row as displayed — corresponds to city Y = 0. City size is encoded by which RGB channel equals 255 exactly: R for small, G for medium, B for large.

Classify by the channel-equals-255 test, not by "looks red/green/blue". The configs shipped with the game use pastel colors whose non-size channels are large but non-saturating, so a nearest-color or dominant-channel heuristic misreads them. When generating a new `config.bmp`, write pure R/G/B so the encoding is unambiguous.

**Duplicates are legal.** Overlapping city files occupying the same tile are valid — at least one shipped Maxis region does this — so a reconstruction pass must not "clean them up".

**Validation.** Before trusting a generated `config.bmp` on real data, run the parser and generator against regions that ship with a known-good `config.bmp` (Berlin, Timbuktu, and San Francisco are convenient because they cover all three tile sizes) and require a byte-for-byte match on the tile classification.
