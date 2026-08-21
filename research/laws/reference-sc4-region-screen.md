# The Region Screen

The region screen is fully decompiled. `tools\research\REGION-SCREEN.md` holds
197 functions of reconstructed code with field maps for six objects (screen,
view, item, tile buffer, tile cache, scroll window), three call-graph
walkthroughs, and a 17-row lever table giving each lever's blast radius and
whether the city view shares it. Read that document before touching anything
here; the notes below are the load-bearing conclusions.

## The region is laid out in precomputed pixels, not projected

Each tile carries float screen positions at `[item+0x10]` and `[item+0x14]`.
`sub_7B3030` only subtracts a pan offset, and it is bottom-anchored — it
subtracts the source height. Nothing projects the region through a camera at
draw time, which is why every camera-side lever fails: the pixels were decided
before the frame started.

## Size and position are two coupled halves

Both are required; either alone leaves the region visibly wrong.

**Positions** come from four `.data` basis floats at `0x00B0DBA4`, `0x00B0DBA8`,
`0x00B0DBAC`, `0x00B0DBB0` (+90.51, +18.75, −37.49, +45.25). `90.51 + 37.49 =
128.0` exactly: one region cell is 128 screen pixels at every resolution. Those
four numbers are the entire position basis.

**Size** comes from `sub_7AE3D0`, the per-buffer builder called inside
`sub_7AE510`. Hook it and grow its output before it returns.

### The second basis is not contiguous with the first

`0x00B0DBBC..0x00B0DBD0` holds a second basis — L1 divided by 1024 plus an
elevation term — read only by `sub_7B5430`, which projects the airport and
seaport overlays into tile space. Scaling the first basis without this one
leaves those overlays misplaced. The two blocks are separated: `0x00B0DBB4` and
`0x00B0DBB8` hold pointers, so writing twelve consecutive floats from
`0x00B0DBA4` corrupts memory. Write the two blocks independently.

## Zoom: trigger the rebuild, never resize in place

In-place resize of a built item is impossible. The click mask at `[item+0x44]`
is only ever rebuilt inside `sub_7AE510`, and clearing the dirty byte at
`[item+0x34]` regenerates `[item+0x38]` alone. Attempting the resize produces
access violations at `0x0082653B` inside `GetPixel`, which has no bounds check —
one on rebuild, one on the following mouse move.

The working sequence, per item:

1. Apply scaled positions **first** — `sub_7AE510` reads `[+0x10]/[+0x14]` and
   never reads the basis floats.
2. Restore the pristine art.
3. Call `sub_7AE510` through the trampoline.
4. Call `sub_7B5430`.
5. Deinit and null `[item+0x20]`.

Then, once for the screen: `sub_7AB7C0` to recompute the pan clamp (the game
computes it only at Init), scale the scroll offsets at `screen+0x178` and
`screen+0x17C` by the zoom ratio, then `sub_7B29E0`.

## The pristine snapshot is mandatory

Hook `sub_7AE510` and AddRef the four bitmaps on entry, keyed by **region cell**
— the item vector reallocates mid-build, so item pointers go stale. Three
independent reasons make this non-optional:

- `sub_7AE510` compounds: each call adds 2 px plus the applied factor to what is
  already there.
- `sub_7B13C0` nulls `[item+0x20]` after the first build, so a naive replay
  crashes inside `sub_7ABCD0`.
- `sub_7ABB80`, the obvious re-seed entry point, re-seeds from placeholder art
  and would erase every city's saved thumbnail.

## Tile buffer API (vtable `0x00AC1400`)

| Slot | Meaning |
| --- | --- |
| `vt+0x04` | AddRef |
| `vt+0x08` | Release |
| `vt+0x0C` | `Init(w, h, colorType, bpp)` — four dwords, `ret 0x10` |
| `vt+0x10` | Deinit |
| `+0x24` / `+0x28` | width / height |
| `+0x88` / `+0x8C` | bits pointer / stride |

`byte[buf+0x08]` is a ready latch: `Init` returns 0 on any already-initialised
buffer, and `FreeBits` does not clear the latch. A resize that only frees the
bits silently no-ops.

## Sharpness: the blur belongs to the game, not to the source art

`sub_7AE3D0` runs a two-tap tent filter (`sub_7AE160`) at scale 1.0 with phase
`fx = 1.0 - frac(pos)`, purely to grid-align at 1:1. At the base tier the phase
measures 1.00 on every tile in Y, which is the identity — sharp. Zoom switches
the blur on, because scaled positions land on arbitrary fractions: the blend
reaches 81%, and edges smear roughly 2.5 screen pixels at f = 3.125, doubling
the magnification blur.

The fix is to hand the tent a phase of exactly 1.0 (kernel `(0, 16384)`, which
is bit-exact over all 65536 pixel pairs) and re-apply the alignment as whole
**destination** pixels. Nearest-neighbour is already the sharpest possible
reconstruction here; every smooth kernel is strictly softer, so substituting
bilinear or bicubic makes the softness worse, not better.

All four buffers of an item must receive identical treatment. `sub_7AE510`
computes fx/fy once and passes the same pair to all four `sub_7AE3D0` calls, and
`sub_7ABCD0` stamps mask onto source pixel-for-pixel with no rectangle
intersection — a one-pixel drift between buffers shows up as a black rim down
one side of a city.

## Measured dead ends

- The region camera and its orthographic frustum: instrumented over 20 samples
  across 5 seconds, they held the written values and the screen did not change.
- Enlarging only the composite, or only the source.
- The game's own resampler `sub_7AE160` — a genuine 16.16 tent, hard-wired to
  scale 1.0.
- **Rotation is impossible.** Across all 197 functions there are zero references
  to rotate, angle, or yaw, verified against a positive control that proves the
  scan would have found them. Region tiles are baked at a fixed angle when a
  city is saved.

## Zoom range

Usable range is ±5 levels, and both limits turned out not to be real
constraints.

Zoom-out was capped at stock by a single comparison — a `<= 1.001` early-out in
the thunk. `GrowTileBitmap` always handled `f < 1`; that path was simply
unreachable. With the early-out lifted the size and position halves stay coupled
below stock, and zooming out is nearly free: one level below the base costs a
quarter of the pixels of one level above.

Zoom-in was bounded by a bookkeeping error rather than by memory. The byte
budget was computed without accounting for the executable being
LARGE_ADDRESS_AWARE (4 GB of address space, not 2), and it charged for the
transient alpha mask as though it persisted, over-counting by 50%. Measured over
48 cities from a pristine 260×160 region: +2 levels = 149 MB, +3 = 233 MB,
+4 = 363 MB. Practical limits by tier: 1.5 gives −5..+5, 2.0 gives −5..+4,
3.0 gives −5..+2.
