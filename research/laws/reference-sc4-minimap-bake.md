# cSC4WinMiniMap Terrain Bake

Engine reference for `cSC4WinMiniMap` (clsid `0xCA318388`, iid `0xCA318385`),
byte-verified against `SimCity 4.exe` 1.1.641 Steam (7,876,608 bytes,
ImageBase `0x400000`).

Three instances are live at runtime: the HUD dock minimap (`0x0BC3B559` under
dock `0x0987B48F`), the Data Views map (`0x00004203` under page `0x8A2871C3`),
and the U-Drive-It dashboard's twin, which carries the **same id as the dock's**.
Parent-gate every lookup — the dock minimap and the dashboard twin are not
distinguishable by id alone.

## Field map

| offset | meaning |
|---|---|
| `+0xE4` | `blitSize` — the surface edge in px. Self-updates only through the class's `SetArea` override; `SetW`/`SetH` bypass it, and the resulting mismatch shows on screen as a stride tear (doubled image, interlaced rows) |
| `+0xF0` | display surface pointer (QI to `cIGZBuffer`) |
| `+0x104` | `zoom` (int32), `= -log2(blitSize / terrainDim)`. Unclamped — `-3` is stored without complaint |
| `+0xFD` / `+0xFE` | dirty flags the message handler consumes |
| `+0x114` / `+0x118` / `+0x11C` | raster base / width / height |
| `+0x120` | 16-byte dirty-tile mask, one bit per 16x16-cell tile |

The terrain dimension comes from the service at `[0xB43CEC]`, vtable `+0x174`.

## The chain: recompute is not paint

* **`0x7A7840` recompute** (`__thiscall`) reallocs the raster via `0x7A7570`,
  recomputes zoom by halving/doubling loops, does `memset(this+0x120, 0xFF, 0x10)`
  (all tiles dirty), and sets `fd`/`fe`. It paints nothing.
* **`0x7A8640` handler** (message-driven): if `fe` is clear, nothing happens. If
  `[this+0xF4]` is non-null and `[this+0xE0] & 8`, it takes a transfer-only fast
  path that **bypasses the bake entirely**. Otherwise, if `fd` is set, it calls the
  bake through `0x7A8721`.
* **`0x7A7FF0` bake** — the terrain-base painter, with exactly one caller
  (`0x7A8721`). Per dirty 16x16 tile it builds a colour tile on the stack (heights
  plus sun shading plus a 256-entry ramp), then dispatches a blitter. It clears the
  dirty mask and `fd` when done **whether or not anything was actually drawn**.
* **`0x7A66F0` / `0x7A67F0` transfer** — a 1:1 raster-to-surface copy that ORs in
  `0xFF000000`. Minimap black is therefore `0xFF000000`, not numeric zero; any
  blackness test must be alpha-insensitive.
* Data **cells** are a separate overlay handled at `0x7A882A` (shift = `zoom+4`)
  with no dispatch table and no bound. That is why cells still paint at zoom -3
  while the terrain base does not.

## The blitter dispatch excludes one zoom level

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

Table `0x7A8628` holds stubs `{0x7A858B, 0x7A8584, 0x7A857D, 0x7A8576, 0x7A856F}`,
reaching blitters x4-up `0x7A6EE0`, x2-up `0x7A6E60`, 1:1 `0x7A6A70`, /2 `0x7A6AD0`,
/4 `0x7A6BD0` — that is, zoom -2..+2. **There is no x8 entry.** The destination
arithmetic above it is fully general in zoom, so the missing entry is the only
thing stopping the bake at zoom -3: the unsigned compare turns -3 into
`0xFFFFFFFF` and the tile is skipped, leaving the terrain base unpainted while
the unbounded data-cell overlay still draws.

Blitter contract, read off the tail at `0x7A8590`:
`cdecl(dst, dstPitchBytes, src16x16, srcPitch=0x40, w, h)`.

Stock code can never reach zoom -3 (largest stock blit 256 divided by smallest
terrain 64 is -2); only an enlarged surface gets there.
`CodePatches::ApplyMiniMapX8Bake` re-points those 15 bytes at a 6-entry table in
the mod DLL — entry 0 is the new x8 blitter, entries 1..5 are the game's own
stubs. The patch is in-memory only and verifies the original bytes before
writing; a byte-level test gates it.

## Sizing constraint on the bake

The bake's addressing assumes **`blitSize == terrainDim << -zoom` exactly**.
Inexact sizes (384 or 768 against a 64-cell grid) overrun the raster in stock
code, including the data-cells loop. Any sizing policy must therefore select only
exact power-of-two multiples of `terrainDim`, which is why the minimap window edge
can only ever be 256, 512, or 1024 — never 384 or 768.

`CodePatches::MiniMapX8Clips()` is not a usable alarm for this. Its entire
clip-and-count body sits behind `dstPitch == rW`, so it engages only when
`blitSize` already equals the raster width — the one case in which clipping is
impossible. When the two disagree, which is the only way this bake can overrun,
the guard silently disables itself and the counter stays 0. A reading of
`clips == 0` proves nothing about safety; it is a structural null.

## Crash attribution: window versus surface, not blit size

The fractional-tier data-view crash is **not** caused by an inexact `blitSize`.
Measurement shows `blitSize` is exact at both crashing tiers (1.5x gives
256 = 64<<2, 3x gives 512 = 64<<3) and `clips` reads 0. The 384 and 768 figures
often quoted are the **window** size, not `blitSize`.

The real invariant is one level out: the window and the surface disagree.
Observed: 1.5x window 384 / surface 256 crashes; 2x 512 / 512 is fine; 3x
768 / 512 crashes. The window is sized `ScaleRound(256, f)` while the surface is
created at `blitSize`, and those agree only when the scale factor is itself a
power of two. The fix is to snap the window to the largest exact power-of-two
multiple of `terrainDim` that fits under the bake ceiling. The attribution was
settled from the game's own exception reports — five reports, one faulting EIP.

## Practical rules

1. Scaling any instance requires the destroy-and-recreate surface lever. The
   surface `Init` at vtable `+0xC` is one-shot, not a resize.
2. After a recompute, drive the bake directly (`0x7A7FF0`, same thread) while the
   window is still hidden. The message-driven paint otherwise lands after the
   panel is visible and the map is seen filling in.
3. `MiniMapX8Blits()` is the executed-counter — installed is not executed. For a
   64-cell city, expect exactly 16 tiles (4x4).
