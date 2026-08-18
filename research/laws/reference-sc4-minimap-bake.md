---
name: reference-sc4-minimap-bake
description: "SC4 cSC4WinMiniMap terrain bake - the field map, the recompute/handler/bake chain, the 5-entry blitter dispatch at 0x7A8560 that excludes zoom -3 (the #121 defect, fixed by a 15-byte in-memory extension to x8), and the HARD sizing constraint blit == terrain << -zoom EXACTLY. NOTE: that constraint is NOT the #109 crash - #109 is window-vs-surface disagreement, corrected 2026-08-04 - and the clips counter cannot detect an overrun at all."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-04T20:33:44.445Z
---

Engine knowledge for **cSC4WinMiniMap** (clsid `0xCA318388`, iid `0xCA318385`),
byte-verified against `SimCity 4.exe` 1.1.641 Steam (7,876,608 bytes,
ImageBase `0x400000`). Three live instances: the HUD dock minimap
(`0x0BC3B559` under dock `0x0987B48F`), the **Data Views map** (`0x00004203`
under page `0x8A2871C3`), and the U-Drive-It dashboard's twin (same id as the
dock's — parent-gate every lookup, they are NOT distinguishable by id).

## Field map

| offset | meaning |
|---|---|
| `+0xE4` | `blitSize` — the surface edge in px. **Only self-updates through the class's `SetArea` override**; `SetW`/`SetH` bypass it (that mismatch is a stride tear: doubled image + interlaced rows) |
| `+0xF0` | display surface pointer (QI to `cIGZBuffer`) |
| `+0x104` | `zoom` (int32), `= -log2(blitSize / terrainDim)`. **Unclamped** — `-3` is stored happily |
| `+0xFD` / `+0xFE` | dirty flags the message handler consumes |
| `+0x114` / `+0x118` / `+0x11C` | raster base / width / height |
| `+0x120` | 16-byte dirty-tile mask (one bit per 16×16-cell tile) |

Terrain dimension comes from the service at `[0xB43CEC]`, vtable `+0x174`.

## The chain — recompute ≠ paint

* **`0x7A7840` recompute** (`__thiscall`): reallocs the raster via `0x7A7570`,
  recomputes zoom by halving/doubling loops, `memset(this+0x120, 0xFF, 0x10)`
  (all tiles dirty) and sets `fd`/`fe`. **It paints nothing.**
* **`0x7A8640` handler** (message-driven): if `fe` is clear, nothing happens; if
  `[this+0xF4]` is non-null and `[this+0xE0]&8`, it takes a transfer-only fast
  path that **bypasses the bake**; otherwise if `fd` is set it calls the bake at
  `0x7A8721`.
* **`0x7A7FF0` bake** — the terrain-base painter, **exactly one caller**
  (`0x7A8721`). Per dirty 16×16 tile it builds a colour tile on the stack
  (heights + sun shading + a 256-entry ramp) then dispatches a blitter. Clears
  the dirty mask and `fd` when done **whether or not anything was drawn.**
* **`0x7A66F0` / `0x7A67F0` transfer** — 1:1 raster→surface copy with
  `or eax,0xFF000000`. **This is where the measured "black is `0xFF000000`,
  not numeric 0" comes from** — test blackness alpha-insensitively.
* Data **cells** are a separate overlay in the handler (`0x7A882A`,
  shift = `zoom+4`) with **no table and no bound**, which is why cells paint at
  zoom −3 while the terrain base does not.

## The dispatch — the #121 defect

```
0x7A852C  mov edx,[ebx+0x104]   ; zoom
0x7A853D  lea ecx,[edx+4]       ; dest math is FULLY GENERAL in zoom:
0x7A8540  sar eax,cl            ;   destY = cellY*16 >> (zoom+4)
0x7A855E  sar eax,cl            ;   tile side = 256 >> (zoom+4)
0x7A8560  lea ecx,[edx+2]       ; index = zoom+2
0x7A8563  cmp ecx,4             ; 5-entry table
0x7A8566  ja  0x7A85B0          ; UNSIGNED -> zoom -3 = 0xFFFFFFFF -> SKIP TILE
0x7A8568  jmp [ecx*4+0x7A8628]
```

Table `0x7A8628` → stubs `{0x7A858B, 0x7A8584, 0x7A857D, 0x7A8576, 0x7A856F}`
→ blitters ×4-up `0x7A6EE0`, ×2-up `0x7A6E60`, 1:1 `0x7A6A70`, ÷2 `0x7A6AD0`,
÷4 `0x7A6BD0` — i.e. zoom −2..+2. **No ×8 entry.** Blitter contract (from the
tail at `0x7A8590`): `cdecl(dst, dstPitchBytes, src16x16, srcPitch=0x40, w, h)`.

Stock can never need −3 (max stock blit 256 ÷ min terrain 64 = −2); only a
resized surface reaches it. `CodePatches::ApplyMiniMapX8Bake` re-points those
15 bytes at a 6-entry DLL table (entry 0 ours, 1..5 the game's own stubs) —
in-memory only, verify-before-write, gated by `_tests\Test-MiniMapX8Bake.py`.

## ⚠ CORRECTED 2026-08-04 — this constraint is REAL but it is **NOT** #109

The sizing rule below is genuine and still binds the bake. But for two weeks this
file (and every doc in the repo) also blamed it for the fractional-tier data-view
CRASH, and that was **wrong**. Measured: `blitSize` is EXACT at both crashing tiers
(1.5× 256 = 64<<2, 3× 512 = 64<<3) and `clips` reads 0. The 384/768 figures
everyone quoted are the **WINDOW** size, not `blitSize`.

**#109's actual invariant is one level out: the WINDOW and the SURFACE disagree.**
1.5× 384/256 CRASH · 2× 512/512 fine · 3× 768/512 CRASH. The window is
`ScaleRound(256, f)`; the surface is created **at blitSize**. They agree only when
f is itself a power of two. Fixed in v2.72.0 by snapping the window to the largest
exact power-of-two multiple of `terrainDim` within the bake ceiling. Settled by
[[reference-sc4-exception-reports]] — five reports, one EIP.

## ⚠ HARD CONSTRAINT — real, and it binds the BAKE (not the crash)

The bake's addressing assumes **`blitSize == terrainDim << -zoom` EXACTLY**.
Inexact sizes (1.5×'s 384, 3×'s 768 against a 64-cell grid) overrun the raster
**in stock code**, including the data-cells loop. **Any sizing policy must select
only exact power-of-two multiples of `terrainDim`** — v2.72.0's snap does exactly
that, and it is why the window can only ever be 256/512/1024, never 384 or 768.

⚠ **`CodePatches::MiniMapX8Clips()` is NOT a usable alarm for this.** Its whole
clip-and-count body sits behind `dstPitch == rW` — i.e. it only engages when
blitSize already equals the raster width, the one case in which no clipping is
possible. When they disagree (the only way this bake can overrun) the guard
silently disables itself and the counter stays 0. **`clips == 0` proves nothing
about safety.** It is a structural null; see [[feedback-null-is-not-evidence]].

## Practical rules

1. Scaling any instance requires the destroy-and-recreate surface lever — the
   surface `Init` at vtable `+0xC` is one-shot, not a resize.
2. After a recompute, **drive the bake yourself** (`0x7A7FF0`, same thread)
   while the window is hidden; the message-driven paint otherwise lands after
   the panel is visible and the user sees it fill in.
3. `MiniMapX8Blits()` is the executed-counter — installed ≠ executed. For a
   64-cell city expect exactly **16** tiles (4×4).

See [[feedback-sc4-scaling-laws]] laws 51/52, `_tests\REGRESSION.md`
(*DATA VIEWS MAP: THE ZOOM CLIFF*), and `SC4-UI-ENGINE.md`.
