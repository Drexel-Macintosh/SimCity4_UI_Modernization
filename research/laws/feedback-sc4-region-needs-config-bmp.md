---
name: sc4-region-needs-config-bmp
description: SC4 DELETES .sc4 city files at region load if config.bmp is missing/mismatched; how to reconstruct config.bmp from savegame coordinates
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4a5a3d38-5382-4675-9304-a2708591f1f0
---

SimCity 4 deletes city files silently: on region load, any `.sc4` whose position/size doesn't match a tile in `config.bmp` is DELETED from disk (no recycle bin). A region folder restored without `config.bmp` gets pruned to whatever fits the game's improvised default grid — same survivor set every time. This gutted the restored Fairview region twice (2026-07-19) before diagnosis.

**Why:** `config.bmp` is the region's tile-grid authority; the `.sc4` files are only tenants.

**How to apply:**
- Never restore or hand-build an SC4 region folder without `config.bmp`; verify every region backup includes it (Fairview's backup was missing it — now fixed, copy added to `OneDrive\Projects\Game Backups\SimCity 4\Regions\Fairview`).
- Reconstruction recipe (proven, 100% match on 7 regions / 477 cities): each `.sc4` is a DBPF; index count @0x24, index offset @0x28, 20-byte entries (TGI+offset+size). Region View Subfile TGI = `0xCA027EDB / 0xCA027EE1 / 0x00000000`; QFS-compressed if bytes 4-5 = `10 FB` (RefPack, 3-byte big-endian uncompressed size at offset 6). Decompressed subfile: tile X @0x04, Y @0x08, sizeX @0x0C, sizeY @0x10 (units of small tiles: 1/2/4).
- `config.bmp` mapping: 24bpp bottom-up BMP; image row 0 (top) = city Y=0; the size channel is whichever RGB channel **equals 255 exactly** (R=small, G=medium, B=large) — Maxis' shipped configs use pastel colors, NOT pure red/green/blue, so classify by channel==255, and write pure R/G/B when generating.
- Overlapping duplicate city files at the same tile are legal (Maxis ships Timbuktu that way) — don't "clean them up".
- Working parser/generator: `SC4Region.cs` (C# via Add-Type) — rebuildable from this recipe; validate on Berlin/Timbuktu/San Francisco (known-good config.bmp) before trusting output.

Related: [[sc4-cam-install-status]]
