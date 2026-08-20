# SC4 REGION SCREEN — module reference

**Target** `SimCity 4 Deluxe 1.1.641`, 32-bit x86, image base `0x400000`, `fileOffset = VA − 0x400000`.
**Module span** `0x007A9000 .. 0x007B6240` (197 functions in `tools\uimap\funcs.json`, plus 6 real
functions that file is missing — see [§9](#9-funcsjson-gaps)).

**Provenance.** Everything here was read out of the shipped exe with
`tools\research\scripts\disasm.py`, `tools\uimap\fn.py`, or a raw little-endian byte scan.
The eight decompile slices in `tools\research\regionmap\slice-1.md … slice-8.md` are the long form;
this file is the index. Claims carry a VA. Claims that are **inference** rather than measurement are
tagged **Unverified** or **Inferred**.

Read [§7 LEVERS](#7-levers) and [§8 DEAD ENDS](#8-dead-ends) before touching anything.

---

## Table of contents

1. [Architecture](#1-architecture)
2. [Field map — `cSC4WinRegionScreen`](#2-field-map--csc4winregionscreen-clsid-0xea659793)
3. [Field map — `cSC4WinRegionView`](#3-field-map--csc4winregionview-clsid-0x2ba6bb97)
4. [Field map — the region ITEM (0x80 bytes)](#4-field-map--the-region-item-0x80-bytes)
5. [Field map — the tile BUFFER (vtable `0x00AC1400`)](#5-field-map--the-tile-buffer-vtable-0x00ac1400)
6. [Call graphs — BUILD / TILE / CLICK](#6-call-graphs)
7. [LEVERS](#7-levers)
8. [DEAD ENDS](#8-dead-ends)
9. [funcs.json gaps](#9-funcsjson-gaps)
10. [Corrections to earlier ground truth](#10-corrections-to-earlier-ground-truth)

---

## 1. Architecture

### 1.1 The object graph

```
cSC4WinRegionScreen              clsid 0xEA659793  vtable 0x00AB9260   (a cGZWin at offset 0)
 │  Init  = sub_7B1900   (vt+0x10, byte @0xAB9270)
 │  Shut  = sub_7B0F60   (vt+0x14, byte @0xAB9274)
 │  Tick  = sub_7AC830   (vt+0x160)          ← per-frame; the ONLY thing that moves the map
 │  Msg   = sub_7AB9F0   (vt+0x0C)
 │  dtor  = sub_7B2320   (vt+0x250)
 │
 ├── +0xE0  cSC4WinRegionView    clsid 0x2BA6BB97  vtable 0x00AB9658   ctor sub_7B4090 (@0x7B1BC8)
 │            ├── +0xD8  painter interface   vtable 0x00AB9644, one real method 0x007B4150
 │            ├── +0x100/104/108  vector<item*>       (stride 4)
 │            ├── +0x10C tile cache          vtables 0x00AB9630 / 0x00AB9618, 0x44 bytes
 │            │            └── +0x0C vector<{IGZBuffer* buf; uint8 dirty;}> stride 8
 │            │                 cols=(W-1)/256+2, rows=(H-1)/256+2, tiles 256x256   (sub_7B5EF0)
 │            ├── +0xE0  background wallpaper PNG {0x856DDBAC,0x6A1EED2C,0x4A2805FF}
 │            └── +0x11C vector<IGZBuffer*>{airport, seaport}   table 0x00AB9594
 │
 ├── +0xE4  cloud particle layer   window id 0x6A0AF41D, vtable 0xAB88C0, 0x140 bytes
 │            ctor sub_7A9AE0 (@0x7B1EFF), Draw sub_7A9D60, cosmetic only
 │
 ├── +0x118/11C/120  vector<item> (stride 0x80)  — THE items, owned by the SCREEN
 │
 ├── +0x154  cIGZGraphicSystem    (copied from [0x00B43C9C] at 0x7B1AA9)  ← the bitmap factory
 ├── +0x158  cSC4AnimationTickManager  clsid 0xA9C73857  (0x7ACCBD)
 ├── +0x15C  cSC4EffectsManager        clsid 0x49822F75  (0x7AD0FD, mirror [0xB43D1C])
 ├── +0x160  renderer                  clsid==iid 0xE9C6262A (0x7ACDB7)
 ├── +0x164  cSC4CameraControl         clsid 0xC9C628EC (0x7ACE41)          ← see DEAD ENDS
 ├── +0x168  scene                     new(0x2E8) sub_7C9B10 (0x7ACF70, mirror [0xB43DD0])
 ├── +0x16C  region terrain grid       new(0x28)  sub_7AACE0 (0x7ACD80, mirror [0xB43CF8])
 └── +0x174  auto-scroll window        vtable 0x00AB8CD0, 0x138 bytes, ctor sub_7AAE10 (@0x7B1E38)
```

**Two orthogonal render systems live on this screen and they do not talk to each other.**

| system | what it draws | how |
|---|---|---|
| **3-D scene** (`+0x160` renderer, `+0x164` camera, `+0x168` scene, `+0x16C` grid) | the flat ground/water quad and 3-D props | `sub_7AB630` emits ONE quad sized `cellSize*width × cellSize*height` from the grid; the camera is driven by `sub_7AC1A0` |
| **2-D tile cache** (`view+0x10C`) | **every city thumbnail, every label, every overlay icon, the wallpaper** | 256×256 `IGZBuffer` cells, painted by `sub_7B4150`, blitted by `sub_7B2770` |

The thing users call "the region map" — the city tiles — is **entirely** the 2-D path.
The camera never touches it. That is why the camera experiment failed ([§8](#8-dead-ends)).

### 1.2 Coordinate spaces (get these wrong and nothing else parses)

| space | definition | who uses it |
|---|---|---|
| **region cells** | integer city-plot grid | `item+0x08/+0x0C`; `sub_7AB7C0`; `sub_7B13C0` |
| **content px** | `cellX*90.51 + cellY*(−37.49)` etc. — the unpanned isometric plane. **One region cell = exactly 128 × 64 px** (`90.51+37.49=128.0`, `18.75+45.25=64.0`) | `item+0x10/+0x14`; the tile cache is addressed here |
| **screen px** | `content − pan`. Pan is `view+0xE8/+0xEC` (ints) | `sub_7B3030` output; the final cell blit at `0x7B27F8..0x7B2819` |
| **cell-local px** | `content − cellOrigin`, inside one 256×256 cache cell | everything inside `sub_7B4150` |

`sub_7B3030` (`0x007B3030`) subtracts the pan; `sub_7B3110` (`0x7B312F`/`0x7B3137`) and
`sub_7B5CA0` (`0x7B5CC5`/`0x7B5CD8`) add it straight back — **the tile cache is addressed in
unpanned content coordinates**, and the pan only selects which cells are visible.

### 1.3 Lifecycle

```
Init  sub_7B1900 (0x7B1900)
  0x7B1920  post "region screen opening" notification        (sub_7ABB00)
  0x7B1AA9  this+0x154 = [0x00B43C9C]                        (cIGZGraphicSystem)
  0x7B1BB5  new(0x128) + sub_7B4090  -> this+0xE0            (the VIEW)
  0x7B1DA1  Init(1,1,{9,0x20}) on a BRAND-NEW 1x1 buffer     (the only Init in the module)
  0x7B1E2A  new(0x138) + sub_7AAE10 -> this+0x174            (scroll window)
  0x7B1EEC  new(0x140) + sub_7A9AE0 -> this+0xE4             (clouds)
  0x7B1F8B  sub_7A9980(clouds, 90.51f, 18.75f)               (wind = the iso X row)
  0x7B1FA6  sub_7B13C0(this)                                 (THE TILE BUILDER)
  0x7B1FAD  sub_7ABF10(this)                                 (exemplar tuning)
  0x7B21A3  sub_7B0470(this)                                 (chrome: two .UI scripts)
  tail      pan := centre of the region bbox, or restored from prefs
Shutdown sub_7B0F60 (0x7B0F60)  -> sub_7AC380 releases +0x158..+0x16C
dtor     sub_7B1200, reached through vt+0x250 = sub_7B2320
```

`sub_7ACC90` (`0x7ACC90`) is the scene/services builder: terrain grid = `min(regionSpan,32)*16`
samples per axis (one height sample per 4×4 game cells, hard-clamped at 32), camera world
extent = `span*1024`.

---

## 2. Field map — `cSC4WinRegionScreen` (clsid `0xEA659793`)

`cGZWin` base is at **offset 0 with no adjustment** (QueryInterface `sub_7AA640` returns `this`
for both `1` and `0x22BA0121`). `this+0xD8` is the `cIGZWinMessageFilter` sub-object
(`GZIID 0xC6AE7085`, `cIGZWinMessageFilter.h:28`); `this+0xDC` is a `cIGZMessageTarget2`.

| off | type | meaning | evidence VA |
|---|---|---|---|
| `+0x00` | vptr | `0x00AB9260` | `0x7B1205` |
| `+0x44` | ptr | cGZWin child list | `0x0099DE74` |
| `+0x4C` | ptr | cGZWin notification target | `0x0099BE42` |
| `+0x74` | ptr | cGZWin cursor | `0x0099B993` |
| `+0xA8..+0xB7` | int[4] | cGZWin rect L,T,R,B | `0x0099C81B` |
| `+0xC8` | u32 | cGZWin flags | `0x0099DB6B` |
| `+0xD8` | vptr | `cIGZWinMessageFilter` sub-object | `sub_7AA640` |
| `+0xDC` | vptr | `cIGZMessageTarget2` sub-object | `sub_7B0AF0` |
| `+0xE0` | ptr | **`cSC4WinRegionView*`** | `0x7B1BB5`, `0x7ACA73` |
| `+0xE4` | ptr | cloud particle layer | `0x7B1EFF`, `0x7ACAA8` |
| `+0xEC/+0xF0/+0xF4` | ptr[3] | the three view-mode PANELS | `sub_7ABDF0` |
| `+0xF8/+0xFC/+0x100` | ptr[3] | the three view-mode sub-windows | `sub_7ABDF0` |
| `+0x108` | ptr | object with `vt+0x28` used by msg `0x1B` | `0x7ABA6E` |
| `+0x118/+0x11C/+0x120` | vector | **`vector<item>` `{_Myfirst,_Mylast,_Myend}`, stride `0x80`** | `sub_7B0BB0`, `sub_7B0E60` |
| `+0x124..+0x150` | ptr[12] | **default tile art: 6 PAIRS `{RGB, ALPHA MASK}`, stride 8.** Table A `+0x124` (3 size classes), table B `+0x13C` (mode 1) | `sub_7ABB80`; ctor zero-fill; Shutdown `0x7B1163..0x7B118D`; dtor `mov ebx,0xC` @`0x7B12C7`; instance table `0xAB8B40` |
| `+0x154` | ptr | **`cIGZGraphicSystem`** — the bitmap factory. **NOT `+0x158`.** | `0x7B1AA9`, `0x7AE6B2` |
| `+0x158` | ptr | `cSC4AnimationTickManager` clsid `0xA9C73857` | `0x7ACCBD` |
| `+0x15C` | ptr | `cSC4EffectsManager` clsid `0x49822F75` | `0x7AD0FD` |
| `+0x160` | ptr | renderer (clsid==iid `0xE9C6262A`) | `0x7ACDB7` |
| `+0x164` | ptr | `cSC4CameraControl` clsid `0xC9C628EC` | `0x7ACE41` |
| `+0x168` | ptr | scene, `new(0x2E8)` + `sub_7C9B10` | `0x7ACF70` |
| `+0x16C` | ptr | region terrain grid, `new(0x28)` + `sub_7AACE0` | `0x7ACD80` |
| `+0x174` | ptr | **auto-scroll window** (vtable `0x00AB8CD0`) | `0x7B1E38`, `sub_7AB790` |
| `+0x178` | float | scroll/pan X (content px) | `0x7AC8AF`, `0x7ABA2E` |
| `+0x17C` | float | scroll/pan Y | `0x7AC8BF`, `0x7ABA3E` |
| `+0x180/+0x184` | int | pan clamp **min** X/Y | `sub_7AB7C0` @`0x7AB98C` |
| `+0x188/+0x18C` | int | pan clamp **max** X/Y | `sub_7AB7C0` |
| `+0x198` | int | **layout X margin** (exemplar prop `0xCA383CA5`) | `sub_7ABF10`, `sub_7AB7C0` |
| `+0x19C` | int | **layout Y margin** (exemplar prop `0xCA383CA6`) | `sub_7ABF10`, `sub_7AB7C0` |
| `+0x1A0` | byte | "suppress hover / click armed" latch | `0x7ACAD8`, `sub_7AB760` |
| `+0x1A1/+0x1A2` | byte | exemplar bools, mirrored to `[0xB217B0]`/`[0xB217B4]` | `sub_7ABF10` |
| `+0x1A4` | int | **current region index** | `0x7ACCE1`, `sub_7AB7C0` |
| `+0x1A8` | int | selection mode (0/1/≥2) | `sub_7AC110` |
| `+0x1B0/+0x1B4` | u32 | exemplar props `0xCA383CAB` / `0xCA383CAC` | `sub_7ABF10` |
| `+0x1B8` | obj | frame stopwatch | `0x7AC85E` |
| `+0x1D0` | obj | double-click stopwatch | `0x7ACB16` |
| `+0x1E8` | int | countdown; at 0 → `SetFlag(0x200000,0)` | `0x7AC838` |
| `+0x1EC` | float | exemplar `0xCA383CB0` | `sub_7ABF10` |
| `+0x1F0` | float | exemplar `0xCA383CAF` | `sub_7ABF10` |
| `+0x1F4/+0x1F8` | float | smooth-scroll TARGET X/Y | `0x7AC8A9`, `0x7AC8B9` |
| `+0x1FC` | byte | "scrolling to target" flag | `0x7AC89D` |

**Vtable `0x00AB9260` overrides**
`+0x00` `sub_7AA640` QI · `+0x0C` `sub_7AB9F0` DoMessage · `+0x10` `sub_7B1900` Init ·
`+0x14` `sub_7B0F60` Shutdown · `+0x160` `sub_7AC830` GZPaint/tick · `+0x218` `sub_7ACAD0`
MouseDownL · `+0x21C` `sub_7AB790` MouseDownR · `+0x228` `sub_7AB760` MouseMove ·
`+0x234` `sub_7AA600` · `+0x238` `sub_7ABB60` MouseExit · `+0x250` `sub_7B2320` dtor.

**Messages handled by `sub_7AB9F0`** — `0x8A4BAC53` scroll BEGIN, `0x8A4BAC5B` scroll END,
`0xAAA1CDF2` scroll DELTA (1/256 px fixed point; `[0xAA6E60] = 1/256`), `0x1B` UI event.

### 2.1 The auto-scroll window (`+0x174`, vtable `0x00AB8CD0`, 0x138 bytes)

| off | type | meaning | evidence |
|---|---|---|---|
| `+0xD8` | u32 | current cursor id | `sub_7AAF20` |
| `+0xDC/+0xE0` | int | drag anchor x,y | `sub_7AAF20` |
| `+0xE4/+0xE8` | float | velocity accumulator | `sub_7AB130` |
| `+0xEC/+0xF0` | float | damping | `sub_7AB130` |
| `+0xF4/+0xF8` | float | **drag velocity X/Y** | `sub_7AAF20`, `sub_7AB130` |
| `+0xFC/+0x100` | float | **command-driven scroll bias X/Y** | `sub_7AF720` @`0x7AF76A` |
| `+0x104` | float | edge-scroll step, default **300.0f** | ctor `0x7AAE10` |
| `+0x108/+0x109` | byte | in-scroll / armed latches | `sub_7AB130` |
| `+0x10C` | ptr | the anchor marker image | `sub_7AC620` |
| `+0x110` | int | dead-zone radius, default **10** (exemplar `0xCA383CA4`) | ctor; `sub_7ABF10` |
| `+0x114` | int | max drag radius, default **32** (exemplar `0xCA383CA3`) | ctor; `sub_7ABF10` |
| `+0x118` | float | velocity scale **5.0f** | ctor |
| `+0x11C` | float | speed-ramp divisor **3.0f** (exemplar `0xCA383CA7`) | ctor; `sub_7ABF10` |
| `+0x120` | obj | elapsed-time timer | `sub_7AB130` |

Overrides: `+0x10` `sub_7AA520`, `+0x14` `sub_7AA570`, `+0x160` `sub_7AB130` (the integrator,
hung on **GZPaint**, not a timer), `+0x21C` `sub_7AD3B0`, `+0x224` `sub_7AAEC0`,
`+0x228` `sub_7AAF20`, `+0x250` `sub_7AC5C0`.
Nine-entry direction cursor table at **`0x00AB8F2C`** (index `row*3+col`, row 0 = up);
index 4 (`0xC2A676AC`) is the neutral cursor and is also hard-coded at `0x7AB061`.
The scroll anchor marker child window id is **`0x48E945B4`** (`sub_7AC620`) — the SAME id our
`UiSpike.cpp` calls the "EDGE bubble / U-Drive-It marker". Any id-keyed rule on it fires in
both screens.

### 2.2 The region terrain grid (`+0x16C`, ctor `sub_7AACE0`, vtables `0xAB8C00`/`0xAB8BE8`)

`+0x0C` float base height **270.0f** · `+0x14` width cells · `+0x18` height cells ·
`+0x1C` **stride = width+1** · `+0x20` float cell size **64.0f** · `+0x24` byte flag.
Normal is hard `(0,1,0)` (`sub_7AADF0`, occupying three vtable slots) — **the region terrain
is a flat plane.** `sub_7AB630` draws its single quad, colour dword `0xFF400000`.

---

## 3. Field map — `cSC4WinRegionView` (clsid `0x2BA6BB97`)

ctor `sub_7B4090` · Init `sub_7B6060` (vt+0x10, `[0xAB9668]`) · Shutdown `sub_7B53A0`
(vt+0x14, `[0xAB966C]`) · dtor `sub_7B5C40` · scalar dtor `sub_7B5E70`.

| off | type | ctor default | meaning | evidence VA |
|---|---|---|---|---|
| `+0x00` | vptr | `0x00AB9658` | primary | `0x7B40A4` |
| `+0x4C` | ptr | — | cGZWin notification target, read via `vt+0x15C` | `0x0099BE4C` |
| `+0xD8` | vptr | `0x00AB9644` | **embedded painter interface** (`vt+0x0C` → `0x007B4150`) | `0x7B40AA` |
| `+0xDC` | u32 | 0 | region / city-set key handed to `app->vt+0x2C` | `0x7B5520` |
| `+0xE0` | ptr | 0 | background wallpaper PNG | `0x7B618F`, `0x7B415B` |
| `+0xE4` | ptr | 0 | **hover / selected `item*`** | `sub_7B5DD0` |
| `+0xE8/+0xEC` | int | 0 | **pan X / pan Y** | `0x7B4A86/0x7B4A92` write; `0x7B3047/0x7B3068` read |
| `+0xF0/+0xF4` | u32 | 0 | item-window `.UI` instance + guid; **`+0xF0 == 0` disables city plaques** | `sub_7B5E20`, `0x7B5A6C` |
| `+0xF8` | u32 | 0 | 4th arg (tint colour) to `sub_7B3300` | `0x7B42DB` |
| `+0xFC` | u32 | 0 | tint colour for the hover frame | `0x7B4A28` |
| `+0x100/+0x104/+0x108` | vector | 0 | **`vector<item*>` `{begin,end,capEnd}` stride 4.** dtor frees `+0x100` with a RAW `free` (`sub_90CF63`) | `sub_7B5D50`, `0x7B5D5F` |
| `+0x10C` | ptr | 0 | **the 256×256 tile cache** | `0x7B611F`, `sub_7B53A0` |
| `+0x110` | byte | 0 | "is scrolling" latch, set by msg `0x8A4BAC53` | `sub_7AB9F0` |
| `+0x111` | byte | **1** | build a plaque window for EVERY item | `0x7B4110`, `0x7B5A72` |
| `+0x112` | byte | 0 | build even when the cell has no city | `0x7B5ACF` |
| `+0x113` | byte | **1** | pass `item+0x50` tint block to the compositor | `0x7B42BC` |
| `+0x114` | byte | 0 | draw label even when the city fails `vt+0x10C`/`vt+0xAC` | `0x7B44B9` |
| `+0x115` | byte | 0 | draw the label for the HOVERED item | `0x7B44AA` |
| `+0x116` | byte | **1** | alternate art for the player's current city | `0x7B411C`, `0x7B5A32` |
| `+0x118` | dword | 0 | **VIEW MODE**: `==1` composite from `item+0x24`; `!=0` run the overlay-icon pass | `0x7B42CA`, `0x7B4818`; setter `sub_7B30F0` |
| `+0x11C/+0x120` | vector | 0 | `vector<IGZBuffer*>` overlay icons `[0]=airport, [1]=seaport` | `0x7B619A`; table `0x00AB9594` |

**`vt+0x160` (GZPaint) is `0x00648F00` = `B0 01 C3` (`mov al,1; ret`).** The view's cIGZWin
draw slot paints nothing — but the view is *not* inert: it paints through the tile cache.
`0x00648F00` is a **shared engine default stub with 302 little-endian references image-wide**;
this module also installs it as the renderer's shutdown (`0x007AC414`). Never treat
"slot X == `0x648F00`" as evidence about one class.

### 3.1 The tile cache (0x44 bytes, vtables `0x00AB9630` / `0x00AB9618`)

| off | meaning | evidence |
|---|---|---|
| `+0x0C/+0x10/+0x14` | `vector<{IGZBuffer* buf; uint8 dirty;}>` **stride 8** | `sub_7B5E90` (`sar …,3`) |
| `+0x18/+0x1C` | grid origin in TILE units (`tileX`,`tileY`) | `0x7B4056/0x7B4067` |
| `+0x20/+0x24` | sub-tile pixel offset (`pan − tileIndex*tileSize`) | `0x7B4064/0x7B406A` |
| `+0x28/+0x2C` | tile width / height — **256 / 256**, immediates at `0x007B60FF` / `0x007B6104` | `sub_7B5EF0` |
| `+0x30/+0x34` | cols = `(W−1)/tw + 2`, rows = `(H−1)/th + 2` | `0x7B5F22/0x7B5F2E` |
| `+0x38/+0x3C` | total content W/H = the VIEW's client rect | `0x7B5F19/0x7B5F1C` |
| `+0x40` | the painter (`view+0xD8`), AddRef'd | `0x7B5F46`; released `sub_7B5300` |

Tile index = `tileY * cols + tileX` (`0x7B2740..0x7B274E`).
`sub_7B3E80` re-anchors the grid as a **torus** — cells that fall off one edge reappear on the
other with their pixels intact, and only wrapped cells are marked dirty.

**Warning — game defect (not ours).** `sub_7B5E90` grows the vector with an 8-byte element but zeroes
only the first dword (`mov dword ptr [esp+8],0` @`0x7B5EA7`); `sub_7B51D0` reads `[edi+4]`, the
dirty byte, so **every appended tile gets an uninitialised `dirty` flag**, and `sub_7B5EF0`
never writes it. Relevant to any first-frame / stale-tile symptom.

---

## 4. Field map — the region ITEM (0x80 bytes)

Derived three ways independently: dtor `sub_7ADA00`, copy-assign `sub_7ADFA0`,
copy-ctor `sub_7AE7B0`. Stride confirmed by `sar/shl 7` in `sub_7B0E60`.

| off | size | type | meaning | evidence VA |
|---|---|---|---|---|
| `+0x00/+0x04` | 8 | int | cell extent used for the `config.bmp` check `((max+1)*64+1)` | `sub_7AEDD0` |
| `+0x08/+0x0C` | 8 | int | **region grid cell X / Y** (`<<6` → game tiles) | `0x7B445C/0x7B4462` |
| `+0x10` | 4 | float | **content-space X** | written `0x007B15D8` |
| `+0x14` | 4 | float | **content-space Y — this is the BOTTOM edge** | written `0x007B15EF` |
| `+0x18` | 1 | u8 | **log2 size class ∈ {0,1,2}**: span = `1<<c` cells (`0x7AEAF9`), = `0x100>>(2−c)` game tiles (`0x7AF14C`) | `sub_7ABB80` |
| `+0x1C` | 4 | refptr | **source thumbnail** — drives the screen RECT and the bottom anchor | everywhere |
| `+0x20` | 4 | refptr | **ALPHA MASK bitmap** — feeds `sub_7ABCD0` and all three `sub_7AD400` run-lists | `sub_7ABB80`, `0x7AE72B` |
| `+0x24` | 4 | refptr | alternate thumbnail, used when `view+0x118 == 1` | `0x7B42D0` |
| `+0x28` | 4 | refptr | alternate mask (paired with `+0x24` via `sub_7ABCD0` @`0x7AE76F`) | `sub_7AE510` |
| `+0x2C` | 4 | refptr | **composite buffer** — the actual blit source | `0x7AE6D2`, `0x7B42AE` |
| `+0x30` | 4 | ptr | the per-city plaque `cIGZWin*` | `0x7B4AB3`, `0x7B5B9A` |
| `+0x34` | 1 | u8 | **"composite built" flag** — clear it to force a rebuild | `0x7B42B5/0x7B42F8`; cleared `0x7B5445` |
| `+0x38` | 12 | vector\<u32\> | **format-A run list consumed by the screen blit `sub_7B2A30`**; built by `sub_7B3670` from the COMPOSITE | `0x7B42EB/0x7B4301` |
| `+0x44` | 12 | vector\<u32\> | run list from `sub_7AD400(bmp=+0x20, shift=0, values=0)` — **also the per-pixel CLICK MASK** read by `sub_7B3A80` | `0x7AE739`; `0x7B3B07/0x7B3AFD` |
| `+0x50` | 12 | vector\<u32\> | `sub_7AD400(+0x20, shift 0x10, values 1)` | `0x7AE757` |
| `+0x5C` | 12 | vector\<u32\> | `sub_7AD400(+0x20, shift 8, values 1)` | `0x7AE748` |
| `+0x68/+0x6C` | 8 | int | **label anchor offset** relative to the tile top-left; alpha-weighted centroid from `sub_7AA6A0` | `0x7AE781`; `0x7B44EB/0x7B44F8` |
| `+0x70` | 4 | list | intrusive circular list of prop/model instances | `0x7B5463..0x7B54B8` |
| `+0x74/+0x78/+0x7C` | 12 | vector | `{int sx, int sy, IGZBuffer* icon}` **stride 0x0C** — projected airport/seaport icons | `0x7B4888`; produced by `sub_7B5430` |

**Two run-list FORMATS exist.**
*Format A* — boundary pairs only, 8 bytes per run: `[open, close, …]`, position packed
`(row<<16)|col`. Producer `sub_7B3670`, consumer `sub_7B2A30`, plus the click mask at `+0x44`.
*Format B* — 8-byte header + one dword of weight per pixel:
`[open, close, w0 … w(n−1), …]`, `n = closeX − openX`
(stride proof `0x7B2EE5`: `add eax,4 / sub ebx… / lea eax,[eax+ebx*4]`).
Consumers `sub_7B2DD0` (full dword as a 0..255 weight) and `sub_7B3300` (low byte `>>1`, so its
tint tops out at ~50 %). **Unverified:** no producer of format B was located in any slice.

---

## 5. Field map — the tile BUFFER (vtable `0x00AC1400`)

The object carries a **secondary vtable `0x00AC13EC` at `+0x04`** which is the same table
shifted by 5 slots (`0x00AC13EC + 0x14 == 0x00AC1400 + 0x00`).

### 5.1 Head layout (all measured from the slot bodies)

| off | type | meaning | evidence VA |
|---|---|---|---|
| `+0x00` | vptr | `0x00AC1400` | — |
| `+0x04` | vptr | `0x00AC13EC` (secondary base) | QI `0x00825D24` returns `this+4` for iid `0x86D72B57` |
| `+0x08` | **u8** | **INITIALISED GATE.** Init early-outs on non-zero; `vt+0x10` clears it | `0x008269B3`, `0x00825CEB` |
| `+0x0C` | u32 | pixel FORMAT (arg3 of Init; 9 = 32-bit ARGB, 4 = 16-bit) | `0x008269E7` |
| `+0x10` | u32 | **bpp** (arg4 of Init; `0x20` or `0x10`) | `0x008269E2` |
| `+0x14/+0x18` | int | rect.left / rect.top — **Init forces both to 0** | `0x008269DA/0x008269DD` |
| `+0x1C` | int | rect.right == **WIDTH** | `0x008269CC`; `GetWidth` = `mov eax,[ecx+0x1C]` |
| `+0x20` | int | rect.bottom == **HEIGHT** | `0x008269D3`; `GetHeight` = `mov eax,[ecx+0x20]` |
| `+0x2C` | int | **REFCOUNT** (AddRef `inc`, Release `dec`; at 1 → `vt+0xA0(1)`) | `0x00825D60`, `0x00825D70` |
| `+0x30` | int | modification / generation counter (bumped by alloc and by `Lock(flags&0x8000)`) | `0x00826A89`, `0x00826AAF` |
| `+0x38` | u16 | **lock depth** (`inc word` on Lock, `dec word` on Unlock) | `0x00826AB7`, `0x0082649B` |
| `+0x3A` | u8 | bytes per pixel (`bpp>>3`) | `0x00826A8B` |
| `+0x3C` | ptr | **the pixel bits** (`operator new`; freed by `vt+0xB0`) | `0x00826A7D` |
| `+0x40` | int | **row PITCH in BYTES** = `align4(width * bpp/8)` | `0x00826A86` |
| `+0x44` | u32 | accumulated OR of every live lock's flags | `0x00826AB2`, `0x00826497` |
| `+0x48` | ptr | attached parent surface (set by `vt+0x98`) | `0x00826954` |

### 5.2 Vtable `0x00AC1400` — every slot resolved in this pass

| slot | target VA | signature (measured) | notes |
|---|---|---|---|
| `+0x00` | `0x00825D00` | `bool QueryInterface(u32 iid, void** out)` `ret 8` | iids `1`, `0x20732180` → `this`; `0x86D72B57` → `this+4` |
| `+0x04` | `0x00825D60` | `void AddRef()` `ret` | `++[this+0x2C]` |
| `+0x08` | `0x00825D70` | `void Release()` `ret` | at 1 → `[+0x2C]=0`, `vt+0xA0(1)` |
| **`+0x0C`** | **`0x008269B0`** | **`bool __stdcall Init(int w, int h, u32 fmt, u32 bpp)` `ret 0x10`** | **see [§8.1](#81-why-init520320-on-a-live-buffer-returns-0)** |
| **`+0x10`** | **`0x00825CE0`** | **`bool __thiscall Deinit()` `ret` (NO args)** | `vt+0xB0()` then `[this+8]=0`; **this is the resize unlock** |
| `+0x14` | `0x00825CE0` | same function as `+0x10` | duplicate slot |
| `+0x18` | `0x00826AA0` | `bool Lock(u32 flags)` `ret 4` | fails if `[+0x3C]==0` |
| `+0x1C` | `0x00826490` | `bool Unlock(u32 flags)` `ret 4` | `[+0x44] &= ~flags; --word[+0x38]` |
| `+0x20` | `0x008268B0` | `bool IsLocked()` | `word[+0x38] != 0` |
| `+0x24` | `0x00808620` | `int GetWidth()` | `[this+0x1C]` |
| `+0x28` | `0x004ED900` | `int GetHeight()` | `[this+0x20]` |
| `+0x2C` | `0x008268D0` | `void GetRect(RECT* out)` | copies 4 dwords from `[this+0x14]` |
| `+0x30` | `0x008268C0` | `const RECT* GetRect()` | `lea eax,[ecx+0x14]` — **returns a pointer, not a copy** |
| `+0x44` | `0x00826910` | `int GetBytesPerPixel()` | `[this+0x10] >> 3` |
| `+0x48` | `0x00991950` | `bool FillRect(const RECT*, u32 colour)` (2 args) | arity by stack balance @`0x7B41A8/0x7B41C4` |
| `+0x54` | `0x00826510` | `u32 GetPixelRGB(int x, int y, u8* r, u8* g, u8* b)` | 5 args |
| `+0x58` | `0x00826560` | `void SetPixel(int x, int y, u32 native)` | |
| `+0x74` | `0x00826AD0` | `bool Blit(IBuffer* src, const RECT* srcRect, const RECT* dstRect, const RECT* clip)` `ret 0x10` | **CANNOT STRETCH** — recomputes `dst.right = dst.left + srcW`, `dst.bottom = dst.top + srcH` at `0x00826B07`/`0x00826B0B` |
| `+0x78` | `0x00825DA0` | `u32 MakeColor(u8 r, u8 g, u8 b)` | channel order inferred |
| `+0x88` | `0x008265C0` | `void* GetBits()` | `[this+0x3C]` |
| `+0x8C` | `0x0068D1B0` | `int GetPitch()` — **BYTES per row** | `[this+0x40]` |
| `+0x98` | `0x00826950` | `bool AttachTo(IBuffer* parent)` | swaps `[this+0x48]` with refcounting |
| `+0x9C` | `0x008264B0` | `bool IsInitialised()` — `mov al,[ecx+8]; ret` | **free runtime probe** |
| `+0xA0` | `0x00827340` | scalar deleting destructor | called by Release |
| `+0xA8` | `0x00826350` | `bool AllocBits()` — calls `vt+0xAC`; on false `[this+0x3C]=0` | called by Init |
| `+0xAC` | `0x00826A50` | the real allocator: `pitch = align4(w * bpp/8); bits = operator new(pitch*h)` | **always returns true** |
| `+0xB0` | `0x00826370` | `bool FreeBits()` — `operator delete([this+0x3C]); [this+0x3C] = 0` | called by `vt+0x10` |
| `+0xB4` | `0x00826390` | format/palette setup, return value discarded | |
| `+0xB8` | `0x00826B80` | the clipped, format-converting copy worker behind `vt+0x74`. 1:1; dispatches through a converter table at `0x00B105A0` | |

> **Note:** the other buffer vtable `0x00ADB418` shares `+0x0C` (= the same `0x008269B0` Init) but
> `+0x10` is a DIFFERENT function (`0x00991A60`)** — a device-surface teardown that releases four
> sub-objects at `+0x74/+0x78/+0x7C/+0x84` and clears `[+8]` and `[+0x50]`. Calling it on a
> memory bitmap is wrong. Always read the slot off the object's own vptr at runtime.

---

## 6. Call graphs

### 6.1 Flow A — REGION SCREEN BUILD

```
cSC4WinRegionScreen::Init                                       sub_7B1900   0x7B1900
 ├─ sub_7ABB00                       post "opening" notification            0x7B1920
 ├─ [0x00B43C9C] -> this+0x154       cIGZGraphicSystem                      0x7B1AA9
 ├─ new(0x128) + sub_7B4090 -> +0xE0 cSC4WinRegionView ctor                 0x7B1BB5/0x7B1BC8
 │    └─ (later, on window Init)  cSC4WinRegionView::Init      sub_7B6060   0x7B6060
 │         ├─ SetID(0x2BA6BB97)                                             0x7B6072
 │         ├─ new(0x44) tile cache -> view+0x10C                            0x7B608C
 │         ├─ TileCache::Configure(W=vt+0xA4, H=vt+0xA8, 256,256, view+0xD8)
 │         │                                                    sub_7B5EF0  0x7B611F
 │         │     ├─ fmt = (mode.depth > 16) ? 9 : 4              jumptable  0x7B6038
 │         │     ├─ tiles.resize(cols*rows)                      sub_7B5E90 0x7B5F8A
 │         │     └─ per tile:  Release  ->  gs->vt+0x0C(&buf)  ->  buf->vt+0x0C(tw,th,{fmt,bpp})
 │         │                                        0x7B5FA6 / 0x7B5FB6 / 0x7B5FF9
 │         ├─ [0xB43DD0]->vt+0x80(cache, 0, 1000)   register as a draw layer (inferred)
 │         └─ load wallpaper + region_airport/region_seaport PNGs           0x7B618F/0x7B619A
 ├─ Init(1,1,{9,0x20}) on a BRAND-NEW buffer                                0x7B1DA1
 ├─ new(0x138) + sub_7AAE10 -> +0x174   scroll window                       0x7B1E38
 ├─ new(0x140) + sub_7A9AE0 -> +0xE4    clouds; wind := (90.51, 18.75)      0x7B1EFF/0x7B1F8B
 ├─ BuildCityItems                                              sub_7B13C0  0x7B1FA6
 │    ├─ per city: push_back a 0x80 item; write cell rect {maxX,maxY,minX,minY}
 │    ├─ screenX(+0x10) = minX*90.51 + (minY+span)*(−37.49)                 0x007B15D8
 │    ├─ screenY(+0x14) = (minX+span)*18.75 + (minY+span)*45.25             0x007B15EF
 │    ├─ sub_5DDA40(path, &it+0x1C, &it+0x20, &it+0x24, &it+0x28)   savegame thumbnails
 │    ├─ sub_7ABB80(it)   default art pair when the savegame has none       0x7B15FE/0x7B17EE
 │    ├─ sub_7AE510(it)   THE ITEM BUILDER (see 6.2)                        0x7B185B
 │    ├─ view->AddItem(it)                                      sub_7B5D50  0x7B18B7
 │    ├─ view->SetItemWindowResource(inst, guid)                sub_7B5E20  0x7B18CE
 │    └─ RecomputePanBounds                                     sub_7AB7C0  0x7B18D5
 │          contentW = |90.51|*W + |37.49|*H + 2*[this+0x198]
 │          contentH = |18.75|*W + |45.25|*H + 2*[this+0x19C]
 │          -> pan clamp +0x180/+0x184 (min), +0x188/+0x18C (max)
 │          -> clouds SetBounds                                  sub_7A9C20 0x7AB9DB
 ├─ LoadTuning (exemplar T=0x6534284A G=0x690F693F I=0xAA383BFE) sub_7ABF10 0x7B1FAD
 └─ BuildChrome (two .UI scripts, group 0x96A006B0,
                 instances 0xAA920991 / 0xABC0ED33)              sub_7B0470 0x7B21A3
```

`sub_7ACC90` (`0x7ACC90`) builds the 3-D side on demand: terrain grid `sub_7AACE0` (`0x7ACD75`),
renderer (`0x7ACDB7`), camera (`0x7ACE41`), scene (`0x7ACF70`), world extent `span*1024`.

### 6.2 Flow B — TILE BUILD and TILE DRAW

**B1 — build (once per item, or after an overlay change)** `sub_7AE510` `0x7AE510`

```
fx = 1.0 − frac(item+0x10);  fy = 1.0 − frac(item+0x14)            0x7AE548
sub_7AE3D0(old20, &item+0x20, fx, fy)                              0x7AE5B9
sub_7AE3D0(old1C, &item+0x1C, fx, fy)                              0x7AE5EA
   └─ sub_7AE3D0: gs->CreateBitmap(out); Init(srcW+2, srcH+2, {9,0x20})   0x7AE439/0x7AE43C/0x7AE443
      then sub_7AE160(dstBits,dstPitch, srcBits,srcPitch, dstW,dstH, srcW,srcH, dx,dy)  0x7AE4DC
      ── a real 16.16 filtered resampler, tent kernel sub_7AA0E0, BUT SCALE IS HARD 1.0
if (item+0x24 && item+0x28) same treatment                         0x7AE65D / 0x7AE68E
composite:  gs=this+0x154; CreateBitmap(&item+0x2C)                0x7AE6B2 / 0x7AE6D2
            r = item[0x1C]->GetRect();  Init(r.w, r.h, {9,0x20})   0x7AE6DE / 0x7AE706
                ==> composite size == ORIGINAL SOURCE + (2,2)
sub_7ABCD0(item+0x1C, item+0x20)   stamp mask alpha into the source 0x7AE726
sub_7AD400 x3 -> item+0x44, +0x5C, +0x50   (all from item+0x20)     0x7AE739/48/57
sub_7AA6A0 -> item+0x68/+0x6C   alpha-weighted centroid             0x7AE781
```

**B2 — draw (every frame, every dirty cache cell)**

```
cSC4WinRegionScreen::OnTick                                  sub_7AC830  vt+0x160
 ├─ integrate smooth scroll; clamp to +0x180..+0x18C
 ├─ UpdateCamera                                             sub_7AC1A0  0x7ACA01
 ├─ view->SetPan( +round(cam.x) − W/2 , −round(cam.y) − H/2 ) sub_7B4A60  0x7ACA8C
 │     ── the Y INVERSION lives at 0x7ACA24 (fadd) vs 0x7ACA42 (fsub), bias [0xAB8BE0]
 │     └─ reposition every plaque window, then TileCache::SetOrigin  sub_7B3E80  0x7B4B6B
 └─ clouds SetPan                                            sub_7A98A0  0x7ACAA8

TileCache paint  (vtable 0xAB9630 + 0x0C)                    sub_7B28B0
 └─ PaintGrid                                                sub_7B2770
      per cell:
        if (dirty) painter->vt+0x0C( cell.buf,
                                     (tileX+col)*tileW,      ← CONTENT-space origin
                                     (tileY+row)*tileH )                0x7B282F..0x7B2842
                                  ==> sub_7B4150
        dst->Blit(cell.buf, cell.buf->GetRect(), cellRect, clip)  vt+0x74  0x7B2868
        cellRect = (col*tileW − cache+0x20, row*tileH − cache+0x24)  ⇒ screen = content − pan

sub_7B4150  (0x7B4150, 2320 bytes) — THE TILE PAINT CALLBACK
 0. wallpaper: sub_8D8BC0(dst, view+0xE0, srcRect, dstRect, −(pan+cell), −(pan+cell), 0)  0x7B41A0
    else dst->FillRect(NULL, dst->MakeColor(0,0,0))                                       0x7B41C4
 1. THUMBNAILS  per item:
      sub_7B3030(view, it, &px,&py)                                                0x7B41FB
      px += panX − cellX ;  py += panY − cellY
      dstR = { px, py, px + it[0x1C]->GetWidth(), py + it[0x1C]->GetHeight() }
                                     vt+0x28 @0x7B4233, vt+0x24 @0x7B4250, on [edi+0x1C]
      cull = *it[0x1C]->GetRect()  ← untranslated; the screen rect is never tested (0x7B4275..0x7B429E)
      if (!it[0x2C]) continue
      if (!it[0x34]) {                                    ← the rebuild gate
          src = (view+0x118 == 1 && it[0x24]) ? it[0x24] : it[0x1C]                 0x7B42CA
          sub_7B3300(src, it[0x2C], tint, view+0xF8)      1:1 rep-movsd copy        0x7B42E3
          sub_7B3670(it[0x2C], &it[0x38])                 build format-A run list   0x7B42F0
          it[0x34] = 1                                                              0x7B42F8
      }
      sub_7B2A30(&dstR, it[0x2C]->GetRect(), dst, it[0x2C], &it[0x38])              0x7B4313
 2. LABELS per item (with a REAL translated cull at 0x7B4436):
      style1 = textSvc->vt+0x14( 0x8A8CC984 − 2*it[0x18] )                          0x7B4515
      style2 = textSvc->vt+0x14( 0x8A8CC985 − 2*it[0x18] )                          0x7B452E
      colour = dst->MakeColor(0xDE,0xE8,0xE3)                                       0x7B4556
      wrap width = thumbnailWidth * 4 / 3                                           0x7B4665
 3. OVERLAY ICONS (only if view+0x118 != 0):
      svc2 = GetSystemService(0x0AE6320E, 0x2AE63219)                               0x7B485A
      svc2->vt+0x98(icon, &srcRect, &dstRect)   ← the ONLY call in the whole path
                                                  that takes independent src+dst rects 0x7B493F
 4. HOVER FRAME: sub_7B2DD0(&r, dst, &it[0x5C], view+0xFC)                          0x7B4A47
```

**Invalidation.** `sub_7B5CA0` (one item) → `sub_7B2620` marks the overlapped cells dirty
(content space) → `sub_7B59B0` rebuilds the plaque. `sub_7B29E0` and `sub_7B5430`
(`0x7B54D0`/`0x7B54F7`) mark **every** cell dirty and un-build **every** composite — a whole-map
invalidate for one item's change.

### 6.3 Flow C — CLICK → CITY

```
cSC4WinRegionScreen  vt+0x218  GZOnMouseDownL                sub_7ACAD0  0x7ACAD0
 ├─ item = sub_7B3A80(view, x, y)                                        0x7ACAEF
 │     ├─ walk view+0x100..+0x104 (item* array, stride 4)
 │     ├─ rect from sub_7B3110 (content space, size from item+0x1C)
 │     └─ PER-PIXEL mask: binary-search item+0x44/+0x48 for key ((dy<<16)+dx+1),
 │        accept on an ODD index (`test dl,4` @0x7B3B37)                  0x7B3B07/0x7B3AFD
 ├─ single click  -> select; sub_7ABDF0 / sub_7AC110 update the panels    0x7ACBD8
 └─ double click (stopwatch at +0x1D0) -> enter the city
       regionMgr->GetCityAt(item+0x08, item+0x0C)                         0x7ACC13/0x7ACC19
       -> sub_7AF4B0 finds/creates and launches
Hover: vt+0x228 -> sub_7AB760 -> sub_7B5DD0 (same hit test), vt+0x238 -> sub_7ABB60 -> sub_7B5DB0
Right-drag scroll: vt+0x21C -> sub_7AB790 -> [this+0x174]->vt+0x21C (sub_7AD3B0)
       -> sub_7AAF20 sets velocity + cursor -> sub_7AB130 integrates and PostMsgs
          0x8A4BAC53 / 0xAAA1CDF2 / 0x8A4BAC5B back to the screen (sub_7AB9F0)
```

**Warning:** the click mask at `item+0x44` is built from `item+0x20` (the alpha mask bitmap), not from
the composite.** Anything that changes the drawn size without changing `+0x20` will make the
picture and the hit box disagree.

---

## 7. LEVERS

Everything a mod can change to affect the region's appearance. "Shared" = also reachable from
the city view.

| # | Lever | VA / key | Current value | Effect | Blast radius | Shared with city view? |
|---|---|---|---|---|---|---|
| L1 | **Isometric basis** (4 floats) | `.data 0x00B0DBA4`, `0x00B0DBA8`, `0x00B0DBAC`, `0x00B0DBB0` | `+90.51`, `+18.75`, `−37.49`, `+45.25` | Region cell pixel size. `90.51+37.49 = 128.0`; `18.75+45.25 = 64.0` ⇒ 1 cell = **128×64 px** | **Exactly 3 code refs each, ALL in this module**: `0x7AB829/33/4E/5E/81/8DA` (`sub_7AB7C0`), `0x7B15C3/D0/E1/E9` (`sub_7B13C0`), `0x7B1F8D/93` (cloud wind). Changing them moves item positions AND the pan clamp AND the cloud wind vector | **NO** — byte-scan shows zero references outside `0x7AB8xx–0x7B1Fxx` |
| L2 | **Isometric basis ÷1024 copy + elevation column** | `0x00B0DBBC`=`+0.08838835`, `0x00B0DBC0`=`+0.01830583`, `0x00B0DBC4`=`0.0`, `0x00B0DBC8`=`−0.08285339`, `0x00B0DBCC`=`−0.03661165`, `0x00B0DBD0`=`+0.04419417` | exactly L1/1024 | Projects airport/seaport icons and 3-D props into tile space | 2 refs each, only `sub_7B5430` (`0x7B5580..0x7B5670`). **Change L1 without L2 and the overlay icons de-register from the thumbnails** | NO |
| L3 | **Layout margins** | exemplar `T=0x6534284A G=0x690F693F I=0xAA383BFE`, props `0xCA383CA5` (X), `0xCA383CA6` (Y) → `screen+0x198/+0x19C` | data-driven | The only *tunable* terms in `sub_7AB7C0`'s size law: `contentW += 2*X`, `contentH += 2*Y` | Pan clamp only — does not change tile size | NO |
| L4 | **Scroll feel** | same exemplar: `0xCA383CA4` dead-zone (10), `0xCA383CA3` max drag (32), `0xCA383CA7` ramp divisor (3.0) | see §2.1 | Right-drag scroll response | scroll window only | NO |
| L5 | **Edge-scroll step** | `screen+0x174 +0x104` (ctor immediate `0x43960000` at `sub_7AAE10`) | `300.0f` | Edge-scroll speed | scroll window only | NO |
| L6 | **Smooth-scroll speed / cap / epsilon** | `[0xA84D28]=5.0f`, `[0xAB91B8]=1200.0f`, `[0xA8825C]=2.0f` | — | `speed = min(5*dist, 1200)` px/s | `0xA84D28` and `0xA8825C` are generic float pool entries — **check refcounts before patching** | likely YES for the pooled floats |
| L7 | **Default tile art** (placeholder thumbnails) | `screen+0x124..+0x150`; instance table `0x00AB8B40` — 6 PAIRS: `(0x6A231946,0x6A231947) (0xEA23195D,0xEA23195E) (0x0A2312D9,0x0A2312D8) (0x6A6CA89E,0x6A6CA89F) (0x6A6CA6DF,0x6A6CA6DE) (0x0A6CAB89,0x0A6CAB88)` PNG `T=0x856DDBAC G=0x6A1EED2C` | — | The art used when a city has no savegame thumbnail. Size class picks the pair; `+0x13C` table is used when region mode == 1 | **Art-only, no code patch.** Second element of each pair is the ALPHA MASK and MUST match the RGB size (`sub_7ABCD0` bounds the loop by the MASK alone — bytes at `0x7ABD06`) | NO |
| L8 | **Region label fonts** | style GUIDs `0x8A8CC984 − 2*sizeClass` (city) and `0x8A8CC985 − 2*sizeClass` (mayor); `sizeClass 0 → {84,85}`, `1 → {82,83}`, `2 → {80,81}` | — | Region city/mayor label size. Selected by GUID — **no art change needed** | `sub_7B4150` label pass only. Line 2 is placed at `y1 + h2` (`0x7B4770`) — it offsets by line TWO's height, so unequal line heights overlap or gap | font styles come from a shared table; confirm the GUIDs are not used elsewhere |
| L9 | **Label wrap width** | `0x7B4665` `imul 0x55555556` | `thumbnailWidth * 4 / 3` | Text wrap column | label pass only | NO |
| L10 | **Tile cache cell size** | immediates `0x100` at `0x007B60FF` and `0x007B6104` | 256×256 | Cell granularity; cols/rows derive from it | Memory ×(cols*rows); a *bigger* cell means fewer, larger buffers | NO |
| L11 | **Cache pixel format** | jump table `0x007B6038`, branch `0x7B5F6E..0x7B5F89` | fmt 9/bpp 0x20 when mode depth > 16, else fmt 4/bpp 0x10 | 32 vs 16-bit cells | region view only | NO |
| L12 | **Composite over-size** | `add eax,2` / `add ecx,2` at `0x007AE439` / `0x007AE43C` | +2 px each axis | Every shifted source and therefore every composite is `original + (2,2)` | Every region item. Changing it alone does NOT scale — the resampler still runs at 1.0 (see [§8.4](#84-the-games-own-resampler-cannot-scale)) | NO |
| L13 | **Wallpaper** | PNG `{0x856DDBAC, 0x6A1EED2C, 0x4A2805FF}` → `view+0xE0` | — | The region backdrop | Art-only. Inferred: the `−2*cellOrigin` residue vanishes only if the wallpaper width divides `2*256 = 512`; a non-divisor will seam | NO |
| L14 | **Overlay icons** | table `0x00AB9594`: `{0x856DDBAC, 0x46A006B0, 0xEBABB1B0}` = `region_airport`, `…B1B1` = `region_seaport` | — | Airport/seaport markers | Art-only; positions come from L2 | NO |
| L15 | **Per-city plaque window** | `.UI` group `0x96A006B0`, instance `view+0xF0` (or `0xCA539343` / guid `0x0A551C53` for the player's own city); child ids `0x4A552000` name, `…001` mayor, `…002` "no city", `…003/4/5` numerics, `…006` population, `0x4A553000` rating bar (typed `0x4A5D1208`) | — | **The plaque is a real `cIGZWin` built from a UI script** — it IS reachable by the normal window-tree scaling machinery, unlike the tile bitmaps | Setting `view+0xF0 = 0` (`sub_7B5E20`) turns plaques off entirely | NO |
| L16 | **View mode** | `view+0x118` via `sub_7B30F0` | 0 | `==1` composites from `item+0x24`; `!=0` enables the overlay-icon pass | region view only | NO |
| L17 | **Cloud sprite size / density** | `[0x00AB7E10] = 128.0f`; density `[0xAB8B20] = 1/16384` (one sprite per 128×128 block) | — | Cosmetic cloud layer at `screen+0xE4` | **Warning:** `0x00AB7E10` has **8 refs**, incl. `0x0079E36B` and `0x0098A790` **outside** this module — patching it hits more than clouds | **YES (partially)** |

### 7.1 Nothing in the region tile path scales with a UI factor

Byte-checked absence of any scale term:
`sub_7B13C0` — four `fmul`s against L1 and nothing else (`0x7B15C3..0x7B15EF`).
`sub_7AB7C0` — L1 plus the two exemplar margins.
`sub_7B5EF0` — tile grid from the window's own client rect (`vt+0xA4` = `[+0xB0]−[+0xA8]`,
`vt+0xA8` = `[+0xB4]−[+0xAC]`), so it scales with the WINDOW, never with a factor.
`sub_7B4150` — every blit rect is `{px, py, px+srcW, py+srcH}`.
That triple is the mechanism behind **#131 "region map unusably small at 2x/3x"**.

---

## 8. DEAD ENDS

Measured not to work. Do not retry.

### 8.1 Why `Init(520,320)` on a live buffer returns 0

`vt+0x0C` = **`0x008269B0`**, read off `0x00AC1400` itself. First six bytes:

```
008269B0  56              push esi
008269B1  8B F1           mov  esi, ecx           ; this
008269B3  8A 46 08        mov  al, [esi+8]        ; the INITIALISED flag
008269B6  33 D2           xor  edx, edx
008269B8  3A C2           cmp  al, dl
008269BA  0F 85 3D 00 00 00  jne 0x8269FD         ; -> xor al,al / pop esi / ret 0x10
```

`[this+8] != 0` ⇒ **immediate `return false`, nothing written, no exception.** That is exactly
the measured symptom on all 9 tiles. The only other early-outs are `width == 0` (`0x8269C0`)
and `height == 0` (`0x8269C8`). The game itself never re-Inits a live buffer: its two Init call
sites (`0x007B1DA1`, `0x007B5FF9`) both run on a buffer created a dozen instructions earlier,
with any previous occupant Released first (`0x7B5FA6..0x7B5FAE`).

### 8.2 The camera and its ortho frustum

`cSC4CameraControl` at `[regionScreen+0x164]` (clsid `0xC9C628EC`, created `0x7ACE41`) —
we set our scale, **the projection and the device frustum both took OUR values and held steady
for 20 samples over 5 s, and the screen never changed.** Mechanism now understood: the camera
drives only the 3-D scene (`+0x160`/`+0x168`/`+0x16C`), whose entire visible contribution is
`sub_7AB630`'s one flat ground quad. Every city thumbnail, label and icon is drawn by the
**2-D tile cache** (`view+0x10C` → `sub_7B4150` → `sub_7B2A30`), which never consults the
camera. `sub_7AC830` reads the camera back only to derive an **integer pan**
(`0x7ACA24`/`0x7ACA42`) — a translation, never a scale.
Corollary: `sub_7AC1A0` (`0x7AC1A0`) is the only sanctioned way to re-centre the region view.

### 8.3 `vt+0x74 Blit` cannot stretch

`0x00826AD0` recomputes the destination extent from the source rect before doing anything else:

```
00826B07  2B C3    sub eax, ebx     ; srcRect.right - srcRect.left
00826B09  03 C2    add eax, edx     ; + dstRect.left
00826B0B  2B CD    sub ecx, ebp     ; srcRect.bottom - srcRect.top
00826B0D  03 CF    add ecx, edi     ; + dstRect.top
```

Only `dstRect`'s top-left is honoured; its width/height are discarded. The worker behind it
(`vt+0xB8` = `0x00826B80`) likewise takes its extent from a single rect and dispatches through
a format-converter table at `0x00B105A0`. **There is no stretch blit on this interface.**

### 8.4 The game's own resampler cannot scale

`sub_7AE160` (`0x7AE160`) IS a genuine 16.16 filtered resampler with a unit-tent kernel
(`sub_7AA0E0` = `max(0, 1−|x|)`, address taken at `0x7AE1EB`). But every scale term is a
literal immediate:

* `push 0x3F800000` (**1.0f**) at `0x7AE186` and `0x7AE1FD` — the scale handed to the kernel
  builder `sub_7AA860` on both axes.
* `push 0x46800000` (16384.0f) — the weight normaliser.
* `mov dword ptr [esp+0x2C], 2` at `0x7AE191` — a hard **2-tap** filter.
* `add ecx, 0x10000` at `0x007AE385` (outer) and `0x007AA274` (inner, `sub_7AA110`) —
  the 16.16 step is a hard-coded **exactly one source pixel per output pixel**.

So `sub_7AE160` can only **shift** by a sub-pixel offset, never resize. It is not a usable
upscaler without patching four immediates in two functions.

### 8.5 Other measured negatives

| Thing | Why it fails | Evidence |
|---|---|---|
| Hooking `cSC4WinRegionView`'s cIGZWin draw slot | `vt+0x160` is the shared no-op `0x00648F00` (`B0 01 C3`); the view paints through the tile cache instead | `[0x00AB97B8]`; painter `0x00AB9650` |
| Treating `0x00648F00` as a class-specific fact | It is a shared engine default with **302** little-endian refs image-wide; this module also uses it as the renderer's shutdown | byte scan; `0x007AC414` |
| Patching `[0x00AB7E10] = 128.0` to resize tiles | That literal is the **cloud sprite edge length**, not the region cell. The 128.0 cell size is *derived* (`90.51+37.49`) and lives in L1 | `sub_7A98E0`, `sub_7A9C20`, `sub_7A9D60` |
| Enlarging **only** the composite (`item+0x2C`) | `sub_7B4150` sizes `dstR` from `item+0x1C` (`vt+0x28` @`0x7B4233`, `vt+0x24` @`0x7B4250` on `[edi+0x1C]`); `sub_7B2A30`'s clip steps 7–8 then shrink `srcRect` to fit `dstRect` against the cell | see §6.2 |
| Enlarging **only** `item+0x1C` | `sub_7B3300` copies exactly `srcW × srcH` into the composite (`min()` of two reads of the SOURCE's own rect, bytes at `0x007B3334`) — if the composite is smaller, **that is a buffer overrun**, not a clip | §5, `0x7B33EA` |
| Relying on `dstR` to clip pass 1 | Pass 1's cull rect is `it[0x1C]->GetRect()` **untranslated** (`0x7B4275..0x7B429E`); the screen rect at `[esp+0x34..0x40]` is never tested. All clipping is inside `sub_7B2A30` | measured |
| Forcing an Init failure inside `sub_7AE3D0` | Its failure path at `0x007AE44A` Releases `*ppDst` **without nulling it**, and `sub_7AE510` then calls `vt+0x30` on the freed pointer at `0x007AE6DE` — **use-after-free** | measured |
| Assuming `0x00ADB418` slot `+0x10` matches | It is `0x00991A60`, a device-surface teardown, not `FreeBits` | §5.2 |
| `0x48E945B4` as a city-view-only id | The region scroll anchor uses the same id (`sub_7AC620` creates, `sub_7AAEC0` destroys) | measured |

---

## 9. `funcs.json` gaps

Six real functions live inside other functions' spans and are absent from
`tools\uimap\funcs.json`. Any pass that iterates `starts[]` silently skips them.

| VA | size | what it is | how it is reached |
|---|---|---|---|
| `0x007A9300` | 56 | `cSC4WinRCI` scalar deleting dtor | thunk `0x7A92E0`, vtable `0xAB8878` |
| `0x007AA0E0` | 35 | **the tent filter kernel** `f(x)=max(0,1−|x|)` | address taken `push 0x7AA0E0` @`0x7AE1EB` |
| `0x007AAB10` | 146 | recursive Btn/OptGrp child walker | address taken @`0x7AAB7F` |
| `0x007AAD30` | 48 | terrain-grid scalar deleting dtor | swallowed by `sub_7AACE0`'s span |
| `0x007AB600` | 48 | dtor of the `0xAB8CB8`/`0xAB8CA0` MI pair | swallowed by `sub_7AB5E0`'s span |
| `0x007B5300` | 80 | tile-cache scalar deleting dtor | `[0x00AB9624] = 0x007B3E70` → `sub ecx,4; jmp` |

`sub_7B51D0`'s recorded end (`0x7B5350`) is wrong: it returns at `0x7B52FD` (`ret 0xC`), so it
is 304 bytes, and `0x7B5300..0x7B5350` is the separate function above.

---

## 10. Corrections to earlier ground truth

| Old statement | Correction | Evidence |
|---|---|---|
| "`cSC4WinRegionView`'s slot-88 draw `0x00648F00`" | Slot **index** 88 decimal = **offset `+0x160`** (GZPaint). Offset `+0x88` is `0x0099DE74`, the inherited `GetChildWindowFromID`. Say "offset `+0x160`" or the next person patches the wrong dword | `[0x00AB9658+0x160]` vs `[+0x88]` |
| "IT PAINTS NOTHING" | True only of the cIGZWin draw slot. The view owns a 256×256 tile cache at `+0x10C` and paints every region pixel through the painter interface at `+0xD8` | `sub_7B6060`, `sub_7B4150` |
| "`+0x158` service" | The **bitmap factory** used to create tile buffers is **`+0x154`** (`mov esi,[ecx+0x154]` @`0x007AE6B2`). `+0x158` is `cSC4AnimationTickManager` | measured |
| "`+0x124..` default tile images" | Exactly **12 slots = 6 PAIRS** `{RGB, ALPHA MASK}`, stride 8, two tables (`+0x124` default, `+0x13C` mode 1), 3 size classes each | ctor zero-fill; Shutdown `0x7B1163..0x7B118D`; dtor `mov ebx,0xC` @`0x7B12C7` |
| "`+0x118/+0x11C` an item array" (screen) | Correct **for the screen** — a 3-field `vector<item>` `{+0x118,+0x11C,+0x120}`, stride `0x80`. **Wrong for the view**: `view+0x118` is the VIEW MODE dword; the view's item array is `+0x100/+0x104/+0x108` | `sub_7B0BB0`; `sub_7B30F0` |
| "`+0x168` scene (ctor `sub_7C9B10`)" | Confirmed — but `sub_7B1900` never writes `+0x168`; the scene is created in `sub_7ACC90` (`0x7ACF70`). `sub_7B1900` builds `+0xE0` (view, ctor `sub_7B4090`), `+0xE4` (clouds) and `+0x174` (scroll) | measured |
| "`sub_7B3030` = item → screen point (no multiply)" | It also `floor()`s both components (`0x009EFF60`) and **subtracts `item[0x1C]->GetHeight()` from Y** (`fsubr` @`0x7B3090`, `vt+0x28` @`0x7B307B`), treating the height as unsigned (`fadd [0x00A80AA8]` @`0x7B308A`). **Items are BOTTOM-anchored** — a taller source moves the tile UP | measured |
| "`sub_7B3110` = item → screen RECT" | It is a **content-space** rect: `sub_7B3030` subtracts the pan and `sub_7B3110` adds it straight back (`0x7B312F`/`0x7B3137`). Size comes from `item+0x1C`, never `+0x2C` | measured |
| "`sub_7B3300` composites 1:1 / `sub_7B2A30` blits 1:1 / NEITHER RESAMPLES" | Both statements hold, but the module-level "nothing resamples" is wrong: `sub_7AE160` is a real resampler — it is just hard-wired to scale 1.0 (§8.4). Also `sub_7B2A30` is not purely per-pixel: an opaque run (first pixel `>= 0xFF000000`, `0x7B2C49`) is issued as a whole-run rect Blit | measured |
| "`sub_7B3300` … the composite is sized verbatim from the source" | `sub_7AE510` has ALREADY replaced `item+0x1C` with `sub_7AE3D0`'s `+(2,2)` copy by the time `0x007AE6D9` runs ⇒ **composite == originalSource + (2,2)** | `0x007AE439/0x007AE43C` |
| "`[item+0x38..]` a packed uint16 alpha run-list" | Element size is **4 bytes** (`sar ecx,2` @`0x00462F12`), and there are **four** such vectors: `+0x38`, `+0x44`, `+0x50`, `+0x5C`. `+0x38` is the screen-blit list (format A, built by `sub_7B3670` from the **composite**); `+0x44` doubles as the **click mask**; `sub_7AE510` fills only `+0x44/+0x50/+0x5C` from `item+0x20` | measured |
| "`[item+0x1C]` source, `[item+0x2C]` composite" (only two buffers) | The item owns **six** refcounted buffers: `+0x1C`, `+0x20` (alpha mask), `+0x24`, `+0x28`, `+0x2C` (composite), `+0x30` | dtor `sub_7ADA00`, copy-assign `sub_7ADFA0` |
| Tile-buffer head "`+0x2C=1 +0x30=3 +0x34=FFFFFFFF +0x38=00040001`" | Those were live *values*, not constants. `+0x2C` = **refcount** (`0x00825D60`), `+0x30` = **modification counter**, low word of `+0x38` = **lock depth**, `+0x44` = OR of live lock flags. **`+0x40` = row pitch in bytes** was missing entirely. `+0x08` is the **initialised gate**, `+0x14`/`+0x18` are rect.left/top forced to 0 by Init | §5.1 |
| "`+0x1C` width `+0x20` height" + "slot `+0x30` GetRect" listed separately | They are the same record: `GetRect` = `lea eax,[ecx+0x14]`, so width/height are `rect[2]`/`rect[3]` | `0x008268C0` |
| "one region cell = 128.0 px" | Also **64.0 px in Y** (`18.75 + 45.25`), independently sighted in `sub_7AB7C0`. One cell = **128 × 64** | `0x7AB84E`/`0x7AB8DA` |
| `sub_7B2480` / `sub_7B24B0` / `sub_7B24FA` "region code" | Shared COM-singleton getter (`clsid 0xC2C2EB0F`, `iid 0x22C2EB1F`, literals at `0x007B249F`/`0x007B2495`) called from 15+ sites image-wide. The clsid literal sits in the GETTER; the create sites reach the class through the singleton's runtime dispatch table, so a literal-clsid create census still cannot see them (`SDK-GAPS.md` §4) | byte scan |
| `SC4-UI-ENGINE.md:249` "SetID `+0xFC`", "Show `+0x110`" | `+0xFC` = `0x0099BE66` is the **getter**; `+0x100` = `0x0099BE5C` is the setter. `+0x110` = `0x0099DB6B` is the generic `SetFlag(u32 flag, bool)` | bytes |
| `vendor/gzcom-dll/.../cIGZWin.h` | Missing exactly **one** virtual between header slot 30 and slot 63: `EnumChildren` is header `+0x074` → real `+0x080` (delta `0x0C`), while `SetFlag` `+0x100`→`+0x110`, `SetNotificationTarget` `+0x148`→`+0x158`, `GZPaint` `+0x150`→`+0x160` are all delta `0x10`. **Any real offset in `+0x078..+0x0FC` is ambiguous by one slot** | `0x7B2392`, `0x7B2351`, `0x7B2374` |
| `cIGZGDriver.h` | Real vtable = header slot **+ 0x0C** (`cIGZUnknown`'s three slots). Verified at five sites in `sub_7A9D60`. Residual, unresolved: real `+0xE8` (header `SetTexture(u32,u32)`) is called with **one** argument at `0x7AA075` | measured |

---

### Appendix — globals this module touches

| Global | Contents | Evidence |
|---|---|---|
| `[0x00B43C94]` | the SC4 app singleton; `vt+0x88` → region manager, `vt+0x44` SavePreferences, `vt+0x98` GetPreferences. Named `cISC4App` by inference | setter `0x00601C04` |
| `[0x00B43C9C]` | **`cIGZGraphicSystem`** (`kGZGraphicSystem_SystemServiceID = 0xC416025C`) — copied to `screen+0x154` | `0x00602384`, `0x7B1AA9` |
| `[0x00B43CA0]` | graphic system used by the cloud draw (`vt+0x0C` → `cIGZGDriver`) | `0x7A9DF9` |
| `[0x00B43CA8]` | resource / properties service (`vt+0x0C(key,iid,out,0,0)`) | `sub_7ABF10` |
| `[0x00B43CCC]` | `cIGZMessageServer2` | `sub_7ABB00` |
| `[0x00B43CD8]` | prefs object; byte `+0xF09` gates edge-scroll; `+0xEFC/+0xF00` hold the saved pan ×256 | `sub_7AB130`, `sub_7AC2D0` |
| `[0x00B43CF8]` | region terrain grid (mirror of `screen+0x16C`) | `sub_7AC380` |
| `[0x00B43D1C]` | `cSC4EffectsManager` (mirror of `+0x15C`) | `0x7AD0FD` |
| `[0x00B43DD0]` | scene / paint manager (mirror of `+0x168`); `vt+0x50` request repaint, `vt+0x60`/`vt+0x68` bracket a paint, `vt+0x80`/`vt+0x84` register/unregister a draw layer. Class not pinned | `0x7AC3BC`, `0x7AD0EB`, `0x7B6145` |
| `[0x00B4E1C0/C4/C8]` + flag `[0x00B4E1CC]` | three exemplar tunables (`0xCA383CAA/A9/A8`) | `sub_7ABF10` |
| `[0x00B217B0]`, `[0x00B217B4]` | two exemplar bools | `sub_7ABF10` |
| `[0x00B628C0]` / `[0x00B628C4]` | cached `cIGZWinMgr` / region-window-factory singletons | `0x00913C46` / `0x00913C72` |
