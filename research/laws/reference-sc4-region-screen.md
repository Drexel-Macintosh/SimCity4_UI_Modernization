---
name: reference-sc4-region-screen
description: "SC4 region screen — the whole module is decompiled to REGION-SCREEN.md; the tile pipeline, the levers that scale AND zoom it, and the measured dead ends."
metadata:
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-05T12:19:53.896Z
---

**THE REGION SCREEN IS FULLY DECOMPILED.**
`SC4TouchControls\tools\research\REGION-SCREEN.md` — 197 functions / 52KB of
code: field maps for six objects (screen, view, item, tile buffer, tile cache,
scroll window), three call-graph walkthroughs, a **17-row LEVERS table** with
blast radius and city-view sharing per lever, DEAD ENDS, and **20 corrections
to things the repo believed**. **Read it before touching the region screen.**

**THE REGION IS LAID OUT IN PRECOMPUTED PIXELS, NOT PROJECTED.** Tiles carry
float screen positions at `[item+0x10]/[+0x14]`; `sub_7B3030` only subtracts a
pan (and is BOTTOM-ANCHORED — it subtracts the source height). That is why
every camera lever failed.

**#131 CLOSED v2.81.1 — TWO COUPLED HALVES, both required:**
1. **Positions** — four `.data` basis floats `0x00B0DBA4/A8/AC/B0`
   (+90.51/+18.75/−37.49/+45.25). `90.51+37.49 = 128.0` EXACTLY: one region
   cell is 128 screen px at *every* resolution — the defect in four numbers.
2. **Size** — MinHook on **`sub_7AE3D0`**, the per-buffer builder inside
   `sub_7AE510`; grow its output before it returns.

⚠ **THERE IS A SECOND BASIS and #131 shipped without it.** `0x00B0DBBC..D0` =
L1/1024 plus an ELEVATION term, read only by `sub_7B5430` to project the
airport/seaport overlays into TILE space. Fixed v2.83.0. **NOT contiguous with
L1** — `0xB0DBB4`/`0xB0DBB8` between them hold POINTERS, so a 12-float block
write corrupts memory.

**#132 ZOOM CLOSED v2.83.0 — TRIGGER THE REBUILD, NEVER RESIZE.** Two crashes
(`0xC0000005` at `0x0082653B` in `GetPixel`, no bounds check; the 2nd on MOUSE
MOVE) proved in-place resize impossible: the **click mask `[item+0x44]`** is
only ever rebuilt inside `sub_7AE510`, and clearing `byte[+0x34]` regenerates
`+0x38` alone. Per item: **scaled positions FIRST** (`sub_7AE510` reads
`+0x10/+0x14` and never reads the basis) → restore pristine art →
`sub_7AE510` **via the trampoline** → `sub_7B5430` → deinit/null `+0x20`.
Then once: `sub_7AB7C0` (pan clamp — the game computes it ONLY at Init),
scroll `screen+0x178/+0x17C` × ratio, `sub_7B29E0`.

**THE PRISTINE SNAPSHOT IS MANDATORY, not an optimisation** — hook
`sub_7AE510` and AddRef the four bitmaps ON ENTRY, keyed by **region cell**
(the item vector reallocs mid-build, so pointers go stale). Three reasons:
`sub_7AE510` compounds (+2 px and our factor per call); `sub_7B13C0` **nulls
`item+0x20`** after the first build so a naive replay crashes in `sub_7ABCD0`;
and `sub_7ABB80` — the obvious fix — re-seeds from **placeholder art** and
would erase every city's thumbnail.

**Tile buffer API (vtable `0x00AC1400`):** `vt+0x04` AddRef, `vt+0x08` Release,
`vt+0x0C` `Init(w,h,colorType,bpp)` — FOUR dwords, `ret 0x10`; `vt+0x10`
Deinit; `+0x24/+0x28` W/H; `+0x88/+0x8C` bits/stride.
⛔ **`byte[buf+0x08]` is a READY LATCH** — `Init` returns 0 on any initialised
buffer. `FreeBits` does NOT clear it. This cost FIVE builds.

**#131b SHARPNESS CLOSED v2.84.0 — the blur was the GAME's, not the source.**
`sub_7AE3D0` runs a 2-tap tent (`sub_7AE160`) at scale 1.0 with phase
`fx = 1.0 - frac(pos)`, purely to grid-align at 1:1. MEASURED: at the base tier
the phase is **1.00 on every tile in Y** (identity — sharp); **ZOOM switches
the blur on**, because scaled positions land on arbitrary fractions — blend to
**81%**, edges smear **~2.5 screen px** at f=3.125, doubling the magnification
blur. Fix: hand the tent phase **1.0** (kernel `(0,16384)` — asserted BIT-EXACT
over all 65536 pixel pairs) and re-apply alignment as whole **DEST** pixels.
⚠ **Nearest-neighbour is already the SHARPEST reconstruction** — every smooth
kernel is strictly softer, so "use bilinear/bicubic" would make softness WORSE.
⚠ All four buffers of an item must get IDENTICAL treatment: `sub_7AE510`
computes fx/fy once and passes them to all four `sub_7AE3D0` calls, and
`sub_7ABCD0` stamps mask→source pixel-for-pixel with **no rect intersection**,
so a one-pixel drift = a black rim down one side of a city.

**MEASURED DEAD — do not retry:** the region camera + ortho frustum (held OUR
values, 20 samples/5s, screen unchanged); enlarging only the composite, or only
the source; the game's resampler `sub_7AE160` (real 16.16 tent, hard-wired to
scale 1.0). **ROTATION IS IMPOSSIBLE** — 0 refs to rotate/angle/yaw across 197
functions against a positive control; tiles are baked at a fixed angle at city
SAVE time.

**RANGE ±5 (v2.85.0, was ±2).** Both directions were limited by something that
was not a real constraint. **Zoom-OUT was capped at stock by ONE COMPARISON** —
the thunk's `<= 1.001` early-out; `GrowTileBitmap` always handled `f < 1`, that
path was just unreachable. Lift it and the pair stays coupled below stock.
Zoom-out is nearly free: a level below the base costs a QUARTER the pixels of
one above. **Zoom-IN was bounded by our own bookkeeping** — the byte budget was
set without checking that the exe is **LARGE_ADDRESS_AWARE** (4 GB, not 2), and
it charged for the transient alpha mask as if it persisted (+50% over-count).
MEASURED, 48 cities, pristine 260×160: +2 = 149 MB, +3 = 233 MB, +4 = 363 MB.
Usable: tier 1.5 −5..+5, tier 2.0 −5..+4, tier 3.0 −5..+2.

Related: [[feedback-sc4-scaling-laws]], [[feedback-sc4-measure-dont-infer]],
[[feedback-docs-are-the-sdk]], [[reference-sc4-ui-sdk-boundary]].
