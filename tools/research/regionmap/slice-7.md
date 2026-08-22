# Region-screen module — SLICE 7 of 8 — `0x007B3D30 .. 0x007B59B0`

Scope: every `starts` entry in `tools/uimap/funcs.json` in `[0x7B3D30, 0x7B5430]` inclusive
(14 entries; the last one, `sub_7B5430`, runs to `0x7B59B0`). **Plus one function
`funcs.json` is missing** — `sub_7B5300`, which lives inside the range `funcs.json`
attributes to `sub_7B51D0` (see [Corrections](#corrections-to-funcsjson-and-to-ground-truth)).

Everything here belongs to one of three owners:

* **`cSC4WinRegionView`** (clsid `0x2BA6BB97`, primary vtable `0x00AB9658`) — the ctor,
  the pan setter, the item-window filler, the overlay-sprite builder.
* **the embedded painter interface at `view+0xD8`** (vtable `0x00AB9644`) — `sub_7B4150`,
  **the tile paint callback**, which is where every pixel of the region map is actually put down.
* **the private tile cache** (primary vtable `0x00AB9630`, secondary `0x00AB9618` at `+0x04`)
  — `sub_7B3E80` (scroll/re-anchor), `sub_7B5350` (shutdown), `sub_7B51D0`/`sub_7B5300`,
  and the two STL helpers `sub_7B3D30`/`sub_7B3D80`.

---

## Table of contents

| # | VA (start..end, bytes) | owner | one line |
|---|---|---|---|
| 1 | [`sub_7B3D30`](#sub_7b3d30) (0x7B3D30..0x7B3D80, 80) | STL | `vector<{IUnknown*,uint8}>::erase(first,last)` — Release each, move tail |
| 2 | [`sub_7B3D80`](#sub_7b3d80) (0x7B3D80..0x7B3E60, 224) | STL | `vector<{IUnknown*,uint8}>::insert(pos, n, value)` with reallocation |
| 3 | [`sub_7B3E60`](#tiny-thunks) (0x7B3E60..0x7B3E70, 16) | thunk | `sub ecx,4; jmp 0x7B23E0` — tile-cache secondary-base QueryInterface |
| 4 | [`sub_7B3E70`](#tiny-thunks) (0x7B3E70..0x7B3E80, 16) | thunk | `sub ecx,4; jmp 0x7B5300` — tile-cache secondary-base scalar-deleting dtor |
| 5 | [`sub_7B3E80`](#sub_7b3e80) (0x7B3E80..0x7B4090, 528) | tile cache | **`TileCache::SetOrigin(px,py)`** — torus re-anchor of the cell grid, marks wrapped cells dirty |
| 6 | [`sub_7B4090`](#sub_7b4090) (0x7B4090..0x7B4140, 176) | RegionView | **`cSC4WinRegionView::cSC4WinRegionView()`** — the constructor; every field default |
| 7 | [`sub_7B4140`](#tiny-thunks) (0x7B4140..0x7B4150, 16) | thunk | `sub ecx,0xD8; jmp 0x682050` — painter-iface QueryInterface adjustor |
| 8 | [`sub_7B4150`](#sub_7b4150) (0x7B4150..0x7B4A60, **2320**) | painter iface | **THE TILE PAINT CALLBACK** — wallpaper, thumbnails, city/mayor labels, overlay icons, hover frame |
| 9 | [`sub_7B4A60`](#sub_7b4a60) (0x7B4A60..0x7B4B80, 288) | RegionView | **`RegionView::SetPan(x,y)`** — repositions every item window, then `TileCache::SetOrigin` |
| 10 | [`sub_7B4B80`](#sub_7b4b80) (0x7B4B80..0x7B51D0, 1616) | RegionView | **`RegionView::FillItemWindow(item, cityRecord)`** — positions and populates one city's tooltip window |
| 11 | [`sub_7B51D0`](#sub_7b51d0) (0x7B51D0..**0x7B5300**, 304) | STL | `vector<{IUnknown*,uint8}>::insert(pos, n, value)` — 3-arg front-end |
| 12 | [`sub_7B5300`](#sub_7b5300) (0x7B5300..0x7B5350, 80) | tile cache | scalar deleting destructor (**absent from `funcs.json`**) |
| 13 | [`sub_7B5350`](#sub_7b5350) (0x7B5350..0x7B53A0, 80) | tile cache | `TileCache::Shutdown()` — vt+0x10 on every cell buffer, clear vector, release painter |
| 14 | [`sub_7B53A0`](#sub_7b53a0) (0x7B53A0..0x7B5430, 144) | RegionView | **`cSC4WinRegionView::Shutdown()`** (vt+0x14, byte-verified `[0x00AB966C]=0x007B53A0`) |
| 15 | [`sub_7B5430`](#sub_7b5430) (0x7B5430..0x7B59B0, **1408**) | RegionView | **`RegionView::RebuildItemOverlays(item)`** — projects airport/seaport icons + 3D props into screen space |

Headline findings: [§ What this slice settles](#what-this-slice-settles).
Corrections: [§ Corrections](#corrections-to-funcsjson-and-to-ground-truth).

---

## Shared vocabulary (measured in this slice)

### `cSC4WinRegionView` fields — everything this slice reads or writes

Constructor `sub_7B4090` is the authority for the defaults.

| field | ctor default | meaning | evidence |
|---|---|---|---|
| `+0x00` | `0x00AB9658` | primary vtable | `0x7B40A4` `C7 06 58 96 AB 00` |
| `+0xD8` | `0x00AB9644` | **embedded painter interface** (single method at `vt+0x0C`) | `0x7B40AA` (`0x7B4098` writes `0x00AB95E0` first — base-ctor transient) |
| `+0xDC` | 0 | region / city-set key handed to `app->vt+0x2C` | `sub_7B4B80` never; `sub_7B5430:0x7B5520` |
| `+0xE0` | 0 | **background wallpaper image** (Released in `sub_7B53A0`) | `sub_7B4150:0x7B415B`, `sub_7B53A0:0x7B5409` |
| `+0xE4` | 0 | hover / selected `item*` | `sub_7B4150:0x7B44A5`, `0x7B497D` |
| `+0xE8` / `+0xEC` | 0 | **pan** (int x, int y) | `sub_7B4A60:0x7B4A86/0x7B4A92` writes; `sub_7B3030` subtracts |
| `+0xF0` / `+0xF4` | 0 | item-window UI-script instance + GUID (slice 8) | ctor only here |
| `+0xF8` | 0 | 3rd arg to the compositor `sub_7B3300` | `sub_7B4150:0x7B42DB` |
| `+0xFC` | 0 | tint colour for the hover frame (`sub_7B2DD0` arg2) | `sub_7B4150:0x7B4A28` |
| `+0x100/+0x104/+0x108` | 0 | `item*` vector `{begin,end,capEnd}`, **stride 4** | `sub_7B4150`, `sub_7B4A60`, `sub_7B5430` |
| `+0x10C` | 0 | **the tile cache** | `sub_7B4A60:0x7B4B63`, `sub_7B53A0`, `sub_7B5430:0x7B54BB` |
| `+0x110` | 0 (byte) | — | ctor only |
| `+0x111` | **1** (byte) | build a window for every item (slice 8) | ctor `0x7B4110` |
| `+0x112` | 0 (byte) | — | slice 8 |
| `+0x113` | **1** (byte) | pass `item+0x50` (a tint block) to the compositor | `sub_7B4150:0x7B42BC` |
| `+0x114` | 0 (byte) | draw the label even when the city record fails the `vt+0x10C`/`vt+0xAC` test | `sub_7B4150:0x7B44B9` |
| `+0x115` | 0 (byte) | draw the label for the **hovered** item | `sub_7B4150:0x7B44AA` |
| `+0x116` | **1** (byte) | alternate art for the player's current city (slice 8) | ctor `0x7B411C` |
| `+0x118` | 0 (dword) | **VIEW MODE** — `==1` ⇒ composite from `item+0x24`; `!=0` ⇒ run the overlay-icon pass | `sub_7B4150:0x7B42CA`, `0x7B4818`; setter `sub_7B30F0` (slice 6) |
| `+0x11C` / `+0x120` | 0 | `vector<IGZBuffer*>` of **overlay icons**, index 0 = airport, 1 = seaport | `sub_7B5430:0x7B55C0`; destroyed `sub_7B53A0:0x7B53C7` |
| `+0x124` | 0 | — | ctor only |

### The region **item** record (stride `0x80`) — fields this slice touches

| field | type | meaning | evidence |
|---|---|---|---|
| `+0x08` / `+0x0C` | int | **region grid cell (x, y)** — the key for the city lookup | `sub_7B4150:0x7B445C/0x7B4462`, `sub_7B5430:0x7B552E/0x7B5534` |
| `+0x10` / `+0x14` | float | content-space position. **`+0x14` is the BOTTOM edge** — `sub_7B3030` subtracts the source bitmap height to get the top | `sub_7B3030`, `sub_7B4150:0x7B435A/0x7B4370` |
| `+0x18` | uint8 | **size class** — indexes the label font-style pair (see below) | `sub_7B4150:0x7B4507`, `0x7B4520` |
| `+0x1C` | `IGZBuffer*` | source thumbnail | everywhere |
| `+0x24` | `IGZBuffer*` | **alternate** source thumbnail, used only when `view+0x118 == 1` | `sub_7B4150:0x7B42D0` |
| `+0x2C` | `IGZBuffer*` | composite (built by `sub_7B3300`) | `sub_7B4150:0x7B42AE` |
| `+0x30` | `cIGZWin*` | the per-city tooltip/info window | `sub_7B4A60:0x7B4AB3`, `sub_7B4B80:0x7B4B9A` |
| `+0x34` | uint8 | composite-built flag | `sub_7B4150:0x7B42B5/0x7B42F8`, cleared in `sub_7B5430:0x7B5445` |
| `+0x38..` | uint16[] | alpha run-list (built by `sub_7B3670`) | `sub_7B4150:0x7B42EB/0x7B4301` |
| `+0x50` | struct | tint block fed to `sub_7B3300` when `view+0x113` | `sub_7B4150:0x7B42C3` |
| `+0x5C` | struct | tint colour for the hover frame (`sub_7B2DD0` arg1) | `sub_7B4150:0x7B4A38` |
| `+0x68` / `+0x6C` | int | **label anchor offset** relative to the tile top-left | `sub_7B4150:0x7B44EB/0x7B44F8` |
| `+0x70` | node* | intrusive **circular** list head `{next, prev, obj}` of prop/model instances | `sub_7B5430:0x7B5463..0x7B54B8`, `0x7B5937` |
| `+0x74/+0x78/+0x7C` | vector | `{int sx, int sy, IGZBuffer* icon}` **stride `0x0C`** — the projected airport/seaport icons | `sub_7B4150:0x7B4888`, produced by `sub_7B5430` |

### The tile-cache object (vtable `0x00AB9630`, secondary `0x00AB9618` at `+0x04`)

| field | meaning | evidence |
|---|---|---|
| `+0x00` / `+0x04` | primary / secondary vtable | `sub_7B5300:0x7B5307/0x7B530D` |
| `+0x0C/+0x10/+0x14` | `vector<{IGZBuffer* buf; uint8 dirty;}>` — **stride 8** | `sub_7B3E80`, `sub_7B5350` |
| `+0x18` / `+0x1C` | current **tile index** origin (`tileX`, `tileY`) | `sub_7B3E80:0x7B4056/0x7B4067` |
| `+0x20` / `+0x24` | **sub-tile pixel offset** (`pan − tileIndex*tileSize`) | `sub_7B3E80:0x7B4064/0x7B406A` |
| `+0x28` / `+0x2C` | tile pixel **width / height** (256×256 per slice 8) | `sub_7B3E80:0x7B3E8E/0x7B3EA7` |
| `+0x30` / `+0x34` | grid **columns / rows** | `sub_7B3E80:0x7B3EDC/0x7B3EF4` |
| `+0x40` | the **painter** (`view+0xD8`), AddRef'd | `sub_7B5350:0x7B5383`; invoked at `0x7B2842` |

**The paint invocation, byte-read at `0x007B282F`–`0x007B2842`:**

```
mov  ecx, [esi+0x40]                    ; the painter interface
mov  edx, [ecx]
push eax                                ; arg3 = (tileY + row) * tileH   ; eax set at 0x7B2824..0x7B282B
mov  eax, [esi+0x18]
add  eax, ebx                           ; tileX + col
imul eax, [esi+0x28]                    ; * tileW
push eax                                ; arg2
mov  eax, [edi]                         ; the cell's IGZBuffer
push eax                                ; arg1
call [edx+0xc]                          ; ==> sub_7B4150
```

**So `sub_7B4150`'s (arg2, arg3) is the cell's origin in CONTENT space, in pixels.**
The same loop then blits the cell at screen `(col*tileW − cache[+0x20], row*tileH − cache[+0x24])`
(`0x7B27F8`–`0x7B2819`), i.e. `screen = content − pan`. This is the single most
load-bearing fact in the slice — it fixes the coordinate space of everything below.

---

## `sub_7B3D30`
`0x007B3D30 .. 0x007B3D80 (80 bytes; real code ends 0x7B3D7F)`

**PURPOSE** `vector<pair<IUnknown*,uint8>>::erase(first, last)` — the 8-byte-element
flavour used by the tile cache's cell vector.

**CONVENTION** `__thiscall`, `ret 8` → `void* erase(this, T* first, T* last)`.
`this` is the vector `{begin@+0, end@+4, cap@+8}` (note: `+0x00` here is the vector's
`begin`, because callers pass `&cache[+0x0C]`).

```c
T* erase(Vec* this, T* first, T* last) {                 // ecx=this
    T* newEnd = sub_7B3220(first, last, this->end, &tmp, 0);   // 0x7B3D4B  move-assign tail down
    for (T* p = newEnd; p != this->end; p += 8)                // 0x7B3D60
        if (p->obj) p->obj->vt+0x08();                         // Release
    this->end = newEnd;                                        // 0x7B3D76
    return tmp;
}
```

**FIELDS** `[this+0x04]` = `end` (read twice, written once).
**VTABLE** `vt+0x08` = `Release`.
**CALLERS** `sub_7B5350` (`0x7B537E`), `sub_7B5E90` (`0x7B5EB6`, slice 8).

---

## `sub_7B3D80`
`0x007B3D80 .. 0x007B3E60 (224 bytes)`

**PURPOSE** the reallocating path of `vector<pair<IUnknown*,uint8>>::insert(pos, n, val)`.

**CONVENTION** `__thiscall`, `ret 0x14` → 5 stack args
`(T* pos, const T* val, size_t n, ???, ???)` — the arg order is read off the
`sub_7B52DF` call site in `sub_7B51D0`: `push 0; push n; push &guard; push pos; push val`.

```c
void insert_realloc(Vec* this, T* val, T* pos, size_t n, Guard* g, int) {
    size_t oldSize = (this->end - this->begin) / 8;              // 0x7B3D92  sar eax,3
    size_t newCap  = oldSize + max(oldSize, n);                  // 0x7B3D95..0x7B3DA7
    T* buf = newCap ? operator new(newCap * 8) : NULL;           // 0x7B3DAB  lea eax,[ebp*8]
    T* mid = sub_7B35F0(this->begin, pos, buf, &g);              // copy head
    if (n == 1) { mid->obj = val->obj; AddRef; mid->flag = val->flag; mid += 8; }   // 0x7B3DE6
    else        mid = sub_7B3630(mid, n, val, &g);               // fill n copies
    if (!g.thrown) mid = sub_7B35F0(pos, this->end, mid, &g);    // copy tail
    sub_7B3BD0(this);                                            // destroy + free old buffer
    this->begin = buf; this->end = mid; this->cap = buf + newCap*8;
}
```

**VTABLE** `vt+0x04` = `AddRef` (`0x7B3DF4`), `vt+0x08` = `Release`.
**CALLERS** `sub_7B51D0` only (`0x7B52F3`).

---

## Tiny thunks

| VA | bytes | meaning |
|---|---|---|
| `sub_7B3E60` | `83 E9 04 E9 78 E5 FF FF` | `sub ecx,4; jmp 0x007B23E0` — adjustor for **tile-cache secondary base** (`0x00AB9618` slot `+0x00`). `0x007B23E0` is also `0x00AB9630` slot `+0x00`, i.e. `TileCache::QueryInterface`. |
| `sub_7B3E70` | `83 E9 04 E9 88 14 00 00` | `sub ecx,4; jmp 0x007B5300` — `0x00AB9618` slot `+0x0C`, the scalar-deleting dtor. |
| `sub_7B4140` | `81 E9 D8 00 00 00 E9 05 DF EC FF` | `sub ecx,0xD8; jmp 0x00682050` — `0x00AB9644` slot `+0x00`, `cSC4WinRegionView::QueryInterface` (`0x00682050` is also `0x00AB9658` slot `+0x00`). |

Byte-verified vtables:
`[0x00AB9618] = {0x007B3E60, 0x005BE420, 0x005BCB60, 0x007B3E70, 0x0090D981, 0x009D7E63}`
`[0x00AB9630] = {0x007B23E0, 0x005BE3E0, 0x005BCB30, 0x007B28B0, 0x00735290}`
`[0x00AB9644] = {0x007B4140, 0x007BE550, 0x007BE560, 0x007B4150, 0x00000000}`

---

## `sub_7B3E80`
`0x007B3E80 .. 0x007B4090 (528 bytes)`  ← **load-bearing: this is how the region map scrolls**

**PURPOSE** `TileCache::SetOrigin(int px, int py)` — re-anchor the fixed cell grid to a
new pixel origin. The grid is a **torus**: cells that fall off one edge reappear on the
other with their content intact, and only the cells whose source wrapped are marked dirty.

**CONVENTION** `__thiscall`, `ret 8` → `void SetOrigin(int px, int py)`.

```c
void TileCache::SetOrigin(int px, int py) {
    int tx = floordiv(px, this->tileW /*+0x28*/);        // 0x7B3E92 idiv + 0x7B3EA2 dec (floor, not trunc)
    int ty = floordiv(py, this->tileH /*+0x2C*/);
    int dx = tx - this->tileX /*+0x18*/;
    int dy = ty - this->tileY /*+0x1C*/;

    if (abs(dx) >= this->cols /*+0x30*/ || abs(dy) >= this->rows /*+0x34*/) {
        // 0x7B4076 — moved further than the cache is wide: EVERY cell dirty, no realloc
        for (E* e = cells.begin; e != cells.end; e += 8) e->dirty = 1;
        goto set_origin;
    }

    Vec fresh; sub_7B3B60(&fresh, (cells.end - cells.begin)/8);   // 0x7B3F0D  same element count

    for (int y = 0; y < rows; ++y)
      for (int x = 0; x < cols; ++x) {
        int sx  = x + dx,           sy  = y + dy;
        int wsx = (sx + cols) % cols, wsy = (sy + rows) % rows;   // 0x7B3F3E / 0x7B3F4E  idiv
        E* src = &cells[wsy*cols + wsx];
        E* dst = &fresh[y*cols + x];
        if (src->buf != dst->buf) {                               // refcounted assign
            if (src->buf) src->buf->AddRef();   // vt+0x04  @0x7B4F90-equivalent 0x7B3F90
            if (dst->buf) dst->buf->Release();  // vt+0x08  @0x7B3FA3
            dst->buf = src->buf;
        }
        dst->dirty = src->dirty;                                  // 0x7B3FA6
        if (sx != wsx || sy != wsy) dst->dirty = 1;               // 0x7B3FB0..0x7B3FD3  WRAPPED ⇒ repaint
      }

    /* swap in `fresh`, Release + free the old array */          // 0x7B4000..0x7B403D
set_origin:
    this->tileX = tx;  this->tileY = ty;                          // 0x7B4056 / 0x7B4067
    this->offX  = px - tx*tileW;                                  // 0x7B4064
    this->offY  = py - ty*tileH;                                  // 0x7B406A
}
```

**Constants** none. **Vtable calls** `vt+0x04` AddRef, `vt+0x08` Release.
**CALLERS** `sub_7B4A60` only (`0x7B4B6B`).

> Note: Note the full-invalidate branch at `0x7B4076` does **not** reallocate, so a large
> jump costs nothing but a full repaint. A small pan costs one allocation of the entire
> cell array plus an AddRef/Release per cell — even when `dx == dy == 0`, because the
> function is called unconditionally from `sub_7B4A60` whenever the pan changed at all.

---

## `sub_7B4090`
`0x007B4090 .. 0x007B4140 (176 bytes)`

**PURPOSE** `cSC4WinRegionView::cSC4WinRegionView()` — the constructor.

**CONVENTION** `__thiscall`, no args, returns `this` in `eax`.

```c
cSC4WinRegionView* ctor(cSC4WinRegionView* this) {
    sub_99D938(this);                        // base cGZWin ctor
    *(void**)(this+0xD8) = 0x00AB95E0;       // 0x7B4098 — transient base-iface vtable
    *(void**)(this+0x00) = 0x00AB9658;       // 0x7B40A4 — cSC4WinRegionView
    *(void**)(this+0xD8) = 0x00AB9644;       // 0x7B40AA — the painter interface
    this->E0 = this->E4 = this->E8 = this->EC = 0;
    this->F0 = this->F4 = 0;
    this->_100 = this->_104 = this->_108 = this->_10C = 0;
    this->b110 = 0; this->b111 = 1;          // 0x7B40F0 / 0x7B4110
    this->b112 = 0; this->b113 = 1;          // 0x7B40F8 / 0x7B4116
    this->b114 = 0; this->b115 = 0;          // 0x7B40FE / 0x7B4104
    this->b116 = 1;                          // 0x7B411C
    this->_118 = this->_11C = this->_120 = this->_124 = 0;
    return this;
}
```

**Constants** `0x00AB95E0` (`{0x5D4A10 ×4, 0x7B23A0, 0x5BE3E0, 0x5BE3F0, 0x7B2500}` — a
pure-virtual/base placeholder table), `0x00AB9658`, `0x00AB9644`.
**CALLERS** `sub_7B1900` at `0x007B1BC8` — i.e. `cSC4WinRegionScreen::Init`.

---

## `sub_7B4150`
`0x007B4150 .. 0x007B4A60 (2320 bytes)`  ← ★ **THE function of this slice**

**PURPOSE** the tile paint callback: render one 256×256 cache cell of the region map.
Vtable slot `+0x0C` of `0x00AB9644` (byte-verified `[0x00AB9650] = 0x007B4150`).

**CONVENTION** `__thiscall`, `ret 0xC`. `ecx` = the **painter subobject**, i.e.
`view + 0xD8` — the very first thing the body does is `lea ecx,[ebp-0xd8]` at `0x7B41F5`
to recover the real `cSC4WinRegionView*`. Throughout the pseudo-C below, `V` is the view
and every `[ebp+N]` in the disassembly is `V + 0xD8 + N`.

```c
void Painter::Paint(IGZBuffer* dst, int cellX, int cellY);   // cellX/cellY = CONTENT-space pixels
```

### 0. background

```c
if (V->bg /*+0xE0*/) {
    sub_8D8BC0(dst, V->bg, V->bg->GetRect(), dst->GetRect(),
               -(V->panX + cellX), -(V->panY + cellY), 0);        // 0x7B41A0
} else {
    dst->FillRect(NULL, dst->MakeColor(0,0,0));                   // vt+0x48 with vt+0x78
}
```

`sub_8D8BC0` is the **wallpaper tiler**: `(dstSurf, srcSurf, srcRect, dstRect, phaseX, phaseY, flags)`.
It has a 1×1 fast path (`0x8D8BF2`: `cmp edi,1` / `cmp ebx,edi`) that degenerates to a solid
fill, and it reduces `phaseX` modulo the source width (`0x8D8D3D`: `idiv edi`).

> Note: **The `+` sign in `-(pan + cell)` is not a transcription slip** — `0x7B417D`
> `add eax,edi` / `0x7B417F` `add ecx,ebx` then `0x7B418A/0x7B418C` `neg eax` / `neg ecx`.
> Items (below) use `− cell` only. My reconciliation: the cell is drawn on screen at
> `cell − pan`, so the wallpaper's screen origin works out to `−2·cell`, which vanishes
> modulo the wallpaper size whenever that size divides `2·256 = 512` — making the
> wallpaper **screen-locked** rather than scrolling with the map. Unsure: that is an
> inference from the modulus, not a measurement. If someone ever ships a wallpaper whose
> width does not divide 512, this is where the seams will come from.

### 1. pass one — the city thumbnails

```c
for (int i = 0; i < (V->itemsEnd - V->items)/4; ++i) {
    item_t* it = V->items[i];
    int px, py;  sub_7B3030(V, it, &px, &py);        // 0x7B41FB
    px += V->panX - cellX;                            // 0x7B4212  ⇒ px = floor(it->fx) - cellX
    py += V->panY - cellY;                            // 0x7B4224  ⇒ py = floor(it->fy) - src->H - cellY
    RECT dstR = { px, py,
                  px + it->src->GetWidth(),           // vt+0x24 @0x7B4250
                  py + it->src->GetHeight() };        // vt+0x28 @0x7B4233

    RECT cull = *it->src->GetRect();                  // vt+0x30 @0x7B426D   (see WARNING)
    if (!sub_79DD60(&cull, &cull, dst->GetRect())) continue;
    if (!it->composite /*+0x2C*/) continue;

    if (!it->built /*+0x34*/) {
        void* tint = V->b113 ? &it->_50 : NULL;                       // 0x7B42BC
        IGZBuffer* srcSel = (V->mode /*+0x118*/ == 1 && it->_24) ? it->_24 : it->src;  // 0x7B42CA
        sub_7B3300(/*eax=*/srcSel, it->composite, tint, V->_F8);      // 0x7B42E3  usercall: src in EAX
        sub_7B3670(it->composite, &it->runlist /*+0x38*/);            // 0x7B42F0
        it->built = 1;                                                // 0x7B42F8
    }
    sub_7B2A30(/*eax=*/&dstR, /*ecx=*/it->composite->GetRect(),
               /*edi=*/dst, it->composite, &it->runlist /*+0x38*/);   // 0x7B4313
}
```

> Note: **WARNING — pass 1's cull rect is the source bitmap's OWN rect, untranslated.**
> `0x7B4275`–`0x7B428E` copies `it->src->GetRect()` (i.e. `{0,0,w,h}`) into the local at
> `[esp+0x78]`, and `0x7B4299`/`0x7B429E` hand *that same local* to `sub_79DD60` as both
> `this` and arg1. The screen rect `dstR` built at `[esp+0x34..0x40]` is **never** tested.
> The address arithmetic is independent of my `esp` bookkeeping (all three `lea`s and the
> stores resolve to the identical stack slot regardless of a ±4 error), so this is a
> measurement, not an inference. **Pass 1 therefore has no per-cell screen cull** — the
> clipping is entirely inside `sub_7B2A30`. Pass 2 *does* cull correctly (below), using a
> translated rect, which is what makes the asymmetry visible.

`sub_79DD60` is `bool IntersectRect(RECT* out, const RECT* a, const RECT* b)` — verified at
`0x79DD6D`–`0x79DD87` (four early-outs) and `0x79DD8F`–`0x79DDBB` (max/max/min/min into `[ecx]`).

### 2. pass two — the city name + mayor name labels

```c
for (int i = 0; i < nItems; ++i) {
    item_t* it = V->items[i];
    int sx = ftol(floor(it->fx) - V->panX);                     // 0x7B435A..0x7B436B
    int sy = ftol((floor(it->fy) - V->panY) - it->src->GetHeight());   // 0x7B4370..0x7B43B1
    sx += V->panX - cellX;   sy += V->panY - cellY;             // ⇒ absolute − cell origin

    RECT r = *it->src->GetRect();  translate(r, sx - r.left, sy - r.top);   // 0x7B43DF..0x7B4425
    if (!sub_79DD60(&r, &r, dst->GetRect())) continue;          // 0x7B4436  ← a REAL cull

    auto* app  = (*(IApp**)0xB43C94)->vt+0x88();                // 0x7B444B
    auto* set  = app->vt+0x2C(V->_DC);                          // 0x7B4459
    auto* rec  = set->vt+0x2C(it->cellX /*+0x08*/, it->cellY /*+0x0C*/);   // 0x7B4468
    if (!rec) continue;
    cSC4City* city = rec[0];
    bool est = city->vt+0x10C();                                // 0x7B447D
    if (!est && !city->vt+0xAC()) continue;                     // 0x7B4493
    if (it == V->hover /*+0xE4*/ && !V->b115) continue;         // 0x7B44A5
    if (!est && !V->b114) continue;                             // 0x7B44B9

    /* --- text --- */
    ITextSys* svc = NULL;
    (*(IGZCOM**)0xB540AC)->vt+0x14(0xC2C2EB0F, 0x22C2EB1F, &svc);      // 0x7B44E8
    int ax = it->_68 + sx,  ay = it->_6C + sy;                          // 0x7B44EB / 0x7B44F8

    // >>> the size-class-keyed font style pair <<<
    IStyle* s1 = svc->vt+0x14( 2u*(0xC54664C2u - it->sizeClass) );      // 0x7B4515
    IStyle* s2 = svc->vt+0x14( 0x8A8CC985u - 2u*it->sizeClass );        // 0x7B452E

    dst->MakeColor(0x3C,0x53,0x8C);                    // 0x7B4540  RESULT DISCARDED (see note)
    uint32 col = dst->MakeColor(0xDE,0xE8,0xE3);       // 0x7B4556  ← the only colour used

    cRZString name, mayor;                             // vtable 0x00A80810, 8-byte seed buffers
    city->vt+0x84(&name);                              // 0x7B45F2  GetCityName
    city->vt+0x8C(&mayor);                             // 0x7B4605  GetMayorName
    /* 0x7B460B..0x7B4665 — inlined sub_7B3170: blank `mayor` when the
       app->vt+0xC4 registry lookup (0x4B5D10) says byte[+0x10] is set   */

    int maxW = (it->src->GetRect()->right - left) * 4 / 3;              // 0x7B4665..0x7B4688
    RECT box = { 0, 0, maxW, s1->vt+0x8C() /*line height*/ };
    IFont* f = svc->vt+0x8C(0x5377BE31);                                // 0x7B46B3
    s1->vt+0xC8(&name,  f, &box, 0);                                    // 0x7B46D2  layout
    s2->vt+0xC8(&mayor, f, &box, 0);                                    // 0x7B46ED  layout

    int x1 = ax - s1->vt+0xC0(name.p, name.len)/2;                      // 0x7B470A
    int x2 = ax - s2->vt+0xC0(mayor.p, mayor.len)/2;                    // 0x7B4731
    int y1 = ay - s1->vt+0x8C();                                        // 0x7B4757
    int y2 = y1 + s2->vt+0x8C();                                        // 0x7B4770

    s1->vt+0xCC(dst, x1, y1, name.p,  name.len,  col, 0x8000000, 0, 0); // 0x7B47A1
    s2->vt+0xCC(dst, x2, y2, mayor.p, mayor.len, col, 0x8000000, 0, 0); // 0x7B47D0
    /* free both strings, sub_7B24B0(&svc) */
```

Notes on this block, all byte-checked:

* **The two style ids are `0x8A8CC984 − 2·sizeClass` and `0x8A8CC985 − 2·sizeClass`** — a
  consecutive pair. `0x7B4507`: `0F B6 47 18 BE C2 64 46 C5 2B F0 D1 E6 56 FF 52 14`, i.e.
  `movzx eax,[edi+0x18]; mov esi,0xC54664C2; sub esi,eax; shl esi,1; push esi; call [edx+0x14]`
  — and `2 × 0xC54664C2 = 0x18A8CC984`, truncating to `0x8A8CC984`. The second is computed
  directly as `0x8A8CC985 − (sizeClass<<1)` (`0x7B4520`–`0x7B452D`). So:
  `sizeClass 0 → {0x8A8CC984, 0x8A8CC985}`, `1 → {0x8A8CC982, 0x8A8CC983}`,
  `2 → {0x8A8CC980, 0x8A8CC981}`. **This is the lever for region-label text size.**
* **`maxW = tileWidth * 4 / 3`** — `0x7B4665`: `8B 4F 1C 8B 01 FF 50 30 8B 48 08 2B 08
  C1 E1 02 B8 56 55 55 55 F7 E9` = `GetRect(); (right−left)<<2; imul 0x55555556` (signed
  divide by 3). A hard 4/3 wrap width relative to the *thumbnail* width.
* **`y2 = y1 + h2`** uses the *second* style's height, not the first's. If the two styles
  have different line heights the two lines overlap or gap. Measured at `0x7B4753`–`0x7B4770`.
* **`MakeColor(0x3C,0x53,0x8C)` at `0x7B4540` is dead** — `eax` is overwritten at `0x7B4543`
  by `mov eax,[ebx]` before anything reads it. Presumably a drop-shadow colour whose draw
  call was removed. Note: Unless `vt+0x78` has a side effect, which slice 6 does not suggest.
* `0x8000000` is a constant draw flag on both text calls.
* `cRZString` here is a 5-dword object `{vtable=0x00A80810, begin, end, cap, 0}` with an
  8-byte heap seed (`operator new(8)` at `0x7B4576` / `0x7B45B8`).

### 3. pass two, tail — the airport / seaport overlay icons

```c
    if (V->mode /*+0x118*/ != 0) {                              // 0x7B4818
        IUnknown* svc2 = NULL;
        sub_90DDF1()->vt+0x0C(0x0AE6320E, 0x2AE63219, &svc2);   // 0x7B485A  (framework GetSystemService)
        svc2->vt+0x44(dst);                                     // 0x7B4864  SetTarget
        svc2->vt+0x54(-1);                                      // 0x7B486F
        svc2->vt+0x5C(1);                                       // 0x7B487A
        svc2->vt+0x58(1);                                       // 0x7B4885
        for (spr_t* p = it->_74; p != it->_78; p += 0x0C) {     // 0x7B48A0
            RECT s = *p->icon->GetRect();
            RECT d = s;
            translate(d, p->x - (s.right-s.left)/2 - cellX,
                         p->y - (s.bottom-s.top)/2 - cellY);    // 0x7B48CD..0x7B491D
            svc2->vt+0x98(p->icon, &s, &d);                     // 0x7B493F  ← SRC RECT + DST RECT
        }
        svc2->Release();
    }
}
```

> `vt+0x98` on that service is the **only draw call in the whole region-map path that takes
> both a source and a destination rect** — i.e. the only one that *could* resample. Here it
> is fed `d` = `s` translated, so it still runs 1:1, but the capability exists.

### 4. pass three — the hover frame

```c
if (V->hover /*+0xE4*/) {                                        // 0x7B497D
    item_t* h = V->hover;
    int hx = ftol(floor(h->fx) - V->panX) + V->panX - cellX;
    int hy = ftol((floor(h->fy) - V->panY) - h->src->GetHeight()) + V->panY - cellY;
    RECT r = { hx, hy, hx + h->src->GetWidth(), hy + h->src->GetHeight() };
    sub_7B2DD0(/*eax=*/&r, /*esi=*/dst, &h->_5C, V->_FC);        // 0x7B4A47
}
```

**Vtable slots used on the destination surface** (same interface family as the tile
buffers, vtable `0x00AC1400`): `+0x24` GetWidth, `+0x28` GetHeight, `+0x30` GetRect,
`+0x48` **FillRect(rect, colour)** (2 args — proved by stack balance across the two
mutually-exclusive branches at `0x7B41A8`/`0x7B41C4`), `+0x78` MakeColor.

**.data / .rdata referenced** `0x00A80AA8` = `4294967296.0f` (the unsigned-`fild` fixup,
used at `0x7B43A7` and `0x7B49D5`), `0x00A80810` = `cRZString` vtable,
`0x00B43C94` = the SC4 app singleton, `0x00B540AC` = the GZCOM/framework pointer
(getter `0x008793EC` = `mov eax,[0xB540AC]; ret`).

**CALLERS** none direct — invoked only through `[cache+0x40]->vt+0x0C` at `0x007B2842`.

---

## `sub_7B4A60`
`0x007B4A60 .. 0x007B4B80 (288 bytes)`

**PURPOSE** `cSC4WinRegionView::SetPan(int x, int y)`.

**CONVENTION** `__thiscall`, `ret 8`.

```c
void SetPan(int x, int y) {
    if (this->panX == x && this->panY == y) return;              // 0x7B4A6D / 0x7B4A7A
    this->panX = x;  this->panY = y;                             // 0x7B4A86 / 0x7B4A92

    for (item_t** pp = this->items; pp != this->itemsEnd; ++pp) {
        item_t* it = *pp;
        cIGZWin* w = it->win /*+0x30*/;
        if (!w) continue;
        int px, py;  sub_7B3030(this, it, &px, &py);             // 0x7B4AC9
        int cx = (2*px + it->src->GetWidth() ) / 2;              // 0x7B4AF7 / 0x7B4B12  (sar 1 after cdq)
        int cy = (2*py + it->src->GetHeight()) / 2;              // 0x7B4B06 / 0x7B4B14
        cy -= w->GetH();                                         // vt+0xA8  @0x7B4B16
        cx -= w->GetW() / 2;                                     // vt+0xA4  @0x7B4B23
        w->GZWinMoveTo(cx, cy);                                  // vt+0xE0  @0x7B4B33
    }
    this->cache /*+0x10C*/->SetOrigin(this->panX, this->panY);   // 0x7B4B6B → sub_7B3E80
}
```

`cIGZWin` slot names `GetW +0xA4 / GetH +0xA8 / GZWinMoveTo +0xE0` are the repo's
already-confirmed table (`tools/research/SC4-UI-ENGINE.md:249`).

**Placement rule, in plain words:** the per-city window is centred **horizontally** on the
thumbnail and **bottom-aligned to the thumbnail's vertical centre** (its full height is
subtracted, not half). Note: The `+ GetWidth()` / `+ GetHeight()` terms are the *thumbnail's*
size, so this placement moves with the art, not with the window.

**CALLERS** `sub_7AC830` at `0x007ACA8C`.

---

## `sub_7B4B80`
`0x007B4B80 .. 0x007B51D0 (1616 bytes)`

**PURPOSE** position and populate one city's info/tooltip window from the city record.
I am naming it `RegionView::FillItemWindow(item_t* it, cityRecord* rec)`.

**CONVENTION** `__thiscall`, `ret 8`. `ecx` = the view (it reads `+0xE8`).

The first 0x92 bytes (`0x7B4BB2`–`0x7B4C12`) are **byte-for-byte the same placement block
as `sub_7B4A60`** (`sub_7B3030`, halve, `vt+0xA8`, `vt+0xA4/2`, `vt+0xE0`) — inlined
rather than shared.

```c
void FillItemWindow(item_t* it, rec_t* rec) {
    double half = 0.5;                                    // fld [0xA92D28] @0x7B4B86
    cIGZWin* w = it->win /*+0x30*/;
    /* ... identical centring block, then: */

    if (!rec || !rec->vt+0xAC()) goto empty;              // 0x7B4C2D
    cSC4City* city = rec[0];  city->AddRef();

    cRZString name, mayor, s3;                            // three 0x14-byte cRZStrings
    city->vt+0x84(&name);                                 // 0x7B4CBE  GetCityName
    city->vt+0x8C(&mayor);                                // 0x7B4CCD  GetMayorName
    sub_7B3170(city, &mayor);                             // 0x7B4CDD  blank mayor if hidden

    w->GetChildWindowFromID(0x4A552000)->vt+0x128(&name);    // 0x7B4CEB / 0x7B4CFE
    w->GetChildWindowFromID(0x4A552001)->vt+0x128(&mayor);   // 0x7B4D0D / 0x7B4D20

    // three mutually-exclusive indicators driven by city->vt+0x3C()
    w->GetChildWindowFromID(0x6C06F4A0)->vt+0x110(1, city->vt+0x3C() == 0);  // 0x7B4D53
    w->GetChildWindowFromID(0xAC06F4C4)->vt+0x110(1, city->vt+0x3C() == 1);  // 0x7B4D87
    w->GetChildWindowFromID(0xCC06F4CF)->vt+0x110(1, city->vt+0x3C() == 2);  // 0x7B4DBA

    // population line + a gauge
    auto* g = w->GetChildWindowFromID(0x4A552006);           // 0x7B4DE4
    double pop = city->vt+0xC8();                            // 0x7B4DF9   (returns double)
    sub_5F9AB0(ftol(pop), &s3);                              // 0x7B4E13   int64 -> string
    if (pop > 0.0)  { ...->vt+0x118(); g->vt+0x128(&s3); }   // 0x7B4E36 / 0x7B4E46
    else            { g->vt+0x118(); ...->vt+0x128(&s3); }   // 0x7B4E57 / 0x7B4E6B
    ...->vt+0x114();                                          // 0x7B4E76  Hide

    auto* fmt = sub_913D7A()->vt+0x98(0);                     // 0x7B4E9F   number formatter
    w->GetChildWindowFromID(0x4A552003)->vt+0x128( fmt->vt+0x48(city->vt+0x28()) );  // 0x7B4F11/0x7B4F1F
    w->GetChildWindowFromID(0x4A552004)->vt+0x128( fmt->vt+0x48(city->vt+0x2C()) );  // 0x7B4F5C/0x7B4F6A
    w->GetChildWindowFromID(0x4A552005)->vt+0x128( fmt->vt+0x48(city->vt+0x30()) );  // 0x7B4F9D/0x7B4FAB
    double rating = (double)(int8)city->vt+0x38() * 0.005;    // 0x7B4FB5..0x7B4FD8   [0xAB98B8]=0.005
    ...
    goto tail;

empty:                                                        // 0x7B502D
    /* [0xB43CA8]->vt+0x0C(&str, 0xA52160F5, &out, 0, 0)  — a localised
       "no city" string; sub_5FD450(out, 0x6A9C7718, &n)  with n seeded 0x2710 = 10000 */
    w->GetChildWindowFromID(0x4A552002)->vt+0x128(<formatted>);   // 0x7B50F7
    if (!rec) w->GetChildWindowFromID(0x4A560003)->vt+0x110(2, 0);// 0x7B511B

tail:                                                         // 0x7B5147
    if (w->vt+0x94(0x4A553000, 0x4A5D1208, &bar)) {           // GetChildAsRecursive, typed
        bar->vt+0x10(rating);                                 // 0x7B5178   set the gauge (double arg)
        sub_602B70(&tmp, 0, 0x46A006B0, 0x14416327, 9, 0);    // 0x7B5190
        if (tmp) bar->vt+0x0C(tmp);                           // 0x7B51A7
        sub_602BE0(&tmp);
    }
}
```

**Child-window IDs written by this function** (all reachable from a `.UI` override):
`0x4A552000` city name, `0x4A552001` mayor name, `0x4A552002` "no city" text,
`0x4A552003/4/5` three numeric fields, `0x4A552006` population,
`0x6C06F4A0` / `0xAC06F4C4` / `0xCC06F4CF` three state icons,
`0x4A560003` a hidden-when-no-record element, `0x4A553000` the **mayor-rating bar**
(typed `0x4A5D1208`), decorated with `{0x46A006B0, 0x14416327, 9}`.

**Constants** `[0x00A92D28] = 0.5` (double), `[0x00A80990] = 0.0` (double),
`[0x00AB98B8] = 0.005` (double — the rating byte → 0..1 scale), `0x00A80810` cRZString vtable.
**Globals** `[0x00B43CA8]` (a localisation/text service), `[0x00B43C94]` unused here.
**CALLERS** `sub_7B59B0` at `0x007B5B9A` (slice 8 — `RebuildItemWindow`).

---

## `sub_7B51D0`
`0x007B51D0 .. 0x007B5300 (304 bytes — NOT 384; see Corrections)`

**PURPOSE** the non-reallocating front-end of
`vector<pair<IUnknown*,uint8>>::insert(pos, n, value)`.

**CONVENTION** `__thiscall`, `ret 0xC` → `void insert(T* value, T* pos, size_t n)`
(arg1 = `value` at `[esp+0x1C]`-relative, arg2 = `pos`, arg3 = `n` at `[esp+8]`).

```c
void insert(Vec* this, T* value, T* pos, size_t n) {
    if (n == 0) return;                                        // 0x7B51D7
    if ((this->cap - this->end)/8 < n) { sub_7B3D80(...); return; }   // 0x7B52F3  reallocate
    value->obj->AddRef();                                      // 0x7B5206  (guard the source)
    size_t tail = (this->end - pos)/8;
    if (tail > n) {                                            // 0x7B5223
        sub_7B35F0(end-n*8, end, end, &g);                     // 0x7B523E  uninit_copy the last n
        this->end += n*8;
        sub_7B3290(pos, end-n*8, end, &g, 0);                  // 0x7B5259  copy_backward
        sub_7B31D0(pos, pos+n*8, &g);                          // 0x7B5267  fill
    } else {
        sub_7B3630(end, n-tail, &value, &g);                   // 0x7B5283  uninit_fill_n
        this->end += (n-tail)*8;
        sub_7B35F0(pos, end0, end, &g);                        // 0x7B52A5
        this->end += tail*8;
        sub_7B31D0(pos, pos+tail*8, &g);                       // 0x7B52C0
    }
    value->obj->Release();                                     // 0x7B52D4
}
```

**CALLERS** `sub_7B5E90` at `0x007B5ED6` (slice 8, `TileVec::resize`).

---

## `sub_7B5300`
`0x007B5300 .. 0x007B5350 (80 bytes)` — **missing from `funcs.json`**

**PURPOSE** the tile cache's scalar-deleting destructor.

**CONVENTION** `__thiscall`, `ret 4` → `void* ~TileCache(int flags)`.

```c
void* dtor(TileCache* this, int flags) {
    *(void**)(this+0x00) = 0x00AB9630;                 // 0x7B5307
    *(void**)(this+0x04) = 0x00AB9618;                 // 0x7B530D
    if (this->painter /*+0x40*/) this->painter->Release();   // 0x7B531C  vt+0x08
    sub_7B3BD0(&this->cells /*+0x0C*/);                // 0x7B5322  destroy + free the cell vector
    sub_90D990(this + 4);                              // 0x7B5329  base dtor on the secondary
    if (flags & 1) sub_5E5620(this);                   // 0x7B5336  operator delete
    return this;
}
```

Reached through `0x00AB9630` slot `+0x0C`? **No** — `[0x00AB963C] = 0x007B28B0`. It is
reached through the **secondary** vtable, `[0x00AB9624] = 0x007B3E70` → `sub ecx,4` → here.

---

## `sub_7B5350`
`0x007B5350 .. 0x007B53A0 (80 bytes)`

**PURPOSE** `TileCache::Shutdown()` — release every cell buffer and the painter, keeping
the object alive.

**CONVENTION** `__thiscall`, no args, returns `al = 1`.

```c
bool Shutdown() {
    for (E* e = this->cells.begin /*+0x0C*/; e != this->cells.end /*+0x10*/; e += 8)
        if (e->buf) e->buf->vt+0x10();                 // 0x7B536B  NOT Release — vt+0x10
    sub_7B3D30(&this->cells, cells.begin, cells.end);  // 0x7B537E  erase-all (Releases them)
    if (this->painter /*+0x40*/) { this->painter = NULL; painter->Release(); }  // 0x7B5393
    return true;
}
```

> Note: `vt+0x10` on the buffers is called **before** the erase Releases them. Slice 6's slot
> table does not cover `+0x10` on the buffer interface; from context it is a
> "free the pixel storage"/`Uninit` call.

**CALLERS** `sub_7B53A0` (`0x7B53EB`), `sub_7B5EF0` (`0x7B6027`, slice 8).

---

## `sub_7B53A0`
`0x007B53A0 .. 0x007B5430 (144 bytes)`

**PURPOSE** `cSC4WinRegionView::Shutdown()` — vtable slot `+0x14`
(byte-verified `[0x00AB966C] = 0x007B53A0`).

**CONVENTION** `__thiscall`, no args, returns `al = 1`.

```c
bool Shutdown() {
    if (!sub_99BC31(this)) return true;                 // 0x7B53A3  base cGZWin::Shutdown
    sub_7B3C10(this);                                   // 0x7B53AE  destroy the item array
    sub_527180(&this->_11C, this->_11C, this->_120);    // 0x7B53C7  destroy the icon vector
    if (this->cache /*+0x10C*/) {
        (*(void**)0xB43DD0)->vt+0x84(this->cache);      // 0x7B53DF  UNREGISTER from a manager
        this->cache->Shutdown();                        // 0x7B53EB → sub_7B5350
        this->cache = NULL;  cache->Release();          // 0x7B5404
    }
    if (this->bg /*+0xE0*/) { this->bg = NULL; bg->Release(); }   // 0x7B541F
    sub_99D2FE(this);                                   // 0x7B5424  base teardown
    return true;
}
```

`[0x00B43DD0]` is the same global the tile cache is registered with in slice 8 and that
`sub_7B5430` pokes at `0x7B5505` (`vt+0x50`). Note: I did not identify it; it behaves like a
paint/refresh manager (`vt+0x50` = "request repaint", `vt+0x84` = "unregister").

**CALLERS** `sub_7B5C40` (`0x7B5C53`) — the region-view destructor.

---

## `sub_7B5430`
`0x007B5430 .. 0x007B59B0 (1408 bytes)`

**PURPOSE** rebuild one item's **overlay content**: the projected airport/seaport icon
positions (consumed by `sub_7B4150`'s pass-3) and a list of 3D prop instances.
I am naming it `RegionView::RebuildItemOverlays(item_t* it)`.

**CONVENTION** `__thiscall`, `ret 4`. `ecx` = the view, arg1 = the item.

### Phase A — tear down the previous contents

```c
it->built /*+0x34*/ = 0;                                        // 0x7B5445
it->_78 = sub_6143E0(it->_78, it->_78, it->_74, &tmp);          // 0x7B545B  destroy [begin,end)
for (node* n = it->list /*+0x70*/->next; n != head; n = n->next)
    n->obj /*+0x08*/->vt+0x10(0);                               // 0x7B5477
/* free every node, reset the circular list to empty */         // 0x7B5490..0x7B54B8
for (E* e = view->cache->cells; ...) e->dirty = 1;              // 0x7B54D0  FULL cache invalidate
for (item_t** p = view->items; ...) (*p)->built = 0;            // 0x7B54F7  ALL composites stale
(*(void**)0xB43DD0)->vt+0x50();                                 // 0x7B5505  request repaint
```

> Note: **This is a whole-map invalidate for a single item's overlay change.** Every cache cell
> is marked dirty and every item's composite is un-built. If region-map redraw cost ever
> becomes an issue, this is the reason.

### Phase B — the projection

```c
auto* set = (*(IApp**)0xB43C94)->vt+0x88()->vt+0x2C(view->_DC);
auto* rec = set->vt+0x2C(it->cellX /*+0x08*/, it->cellY /*+0x0C*/);   // 0x7B553A
if (!rec) return;
cSC4City* city = rec[0];

float fx = (float)(it->cellX << 10);        // 0x7B554F  shl edx,0xA  — 1 region cell = 1024 units
float fz = (float)(it->cellY << 10);        // 0x7B555A
float baseX = fx*[0xB0DBBC] + fz*[0xB0DBCC];     // 0x7B5592 / 0x7B557E
float baseY = fx*[0xB0DBC0] + fz*[0xB0DBD0];     // 0x7B559C / 0x7B5588

for (int cat = 0; cat < 2; ++cat) {                                  // table walk, see below
    IGZBuffer* icon = ((IGZBuffer**)view->_11C)[cat];                // 0x7B55C0 / 0x7B562B
    if (!icon) continue;
    vec3f* v; vec3f* vend;
    city->vt+0x120(kTable[cat].index, &v, &vend);                    // 0x7B55EC
    for (; v != vend; ++v) {
        float sx = v->x*[0xB0DBBC] + v->y*[0xB0DBC4] + v->z*[0xB0DBCC] + baseX;
        float sy = v->x*[0xB0DBC0] + v->y*[0xB0DBC8] + v->z*[0xB0DBD0] + baseY;
        int   ix = fastround(sx), iy = fastround(sy);                // see the magic below
        push_back(it->_74, { ix, iy, icon });                        // 0x7B56ED / 0x7B5760..0x7B57C7
        /* ... then a 3D prop instance is created from the same v and
           linked into it->list (+0x70): 0x7B57CA .. 0x7B5941        */
    }
}
```

**The isometric basis — six floats, byte-read:**

| VA | value | role |
|---|---|---|
| `0x00B0DBBC` | `+0.0883883461` | X axis → screen X (`= 90.51 / 1024`) |
| `0x00B0DBC0` | `+0.0183058251` | X axis → screen Y (`= 18.75 / 1024`) |
| `0x00B0DBC4` | `+0.0` | elevation → screen X |
| `0x00B0DBC8` | `−0.0828533918` | elevation → screen Y (`≈ −84.84 / 1024`) |
| `0x00B0DBCC` | `−0.0366116501` | Z axis → screen X (`= −37.49 / 1024`) |
| `0x00B0DBD0` | `+0.0441941731` | Z axis → screen Y (`= 45.25 / 1024`) |

**This is GROUND TRUTH's `0xB0DBA4..0xB0DBB0` basis divided by exactly 1024**, paired with
`cell << 10`. Same projection, fixed-point input. `90.51 + 37.49 = 128.0` still holds.

**The fast round**, `0x7B56AF`–`0x7B56E1`:
`fadd [0x00AB95AC]` where `[0x00AB95AC] = 12582912.0f = 1.5·2^23`, store to memory, then
`add ecx, 0xB4C00000` (= subtract `0x4B400000`). Classic round-to-nearest-even. Bytes at
`0x7B56C4`: `81 C1 00 00 C0 B4`.

**The category table** — 2 entries at `0x00AB9594`, stride `0x0C`, `{uint32 id, uint32 index, const char* name}`:

| VA | id | index | name |
|---|---|---|---|
| `0x00AB9594` | `0xEBABB1B0` | 0 | `"region_airport"` (@`0x00AB95C0`) |
| `0x00AB95A0` | `0xEBABB1B1` | 1 | `"region_seaport"` (@`0x00AB95B0`) |

**MEASURED:** the loop cursor is initialised to `0x00AB959C` (`mov eax,0xAB959C` at
`0x7B5561`), terminates on `cmp eax,0x00AB95B4; jl` (`0x7B598E`), advances by `0xC`, and
passes **`[cursor-4]`** to `city->vt+0x120` — so exactly two iterations passing the dwords
`[0x00AB9598] = 0` and `[0x00AB95A4] = 1`. Those are the values that matter.
Note: **INFERRED:** that the record is `{uint32 id, uint32 index, const char* name}` based at
`0x00AB9594`. The evidence is the `0xC`-apart pair `0xEBABB1B0` @ `0x00AB9594` /
`0xEBABB1B1` @ `0x00AB95A0` and the two string pointers at `0x00AB959C` / `0x00AB95A8`.
Nothing in this slice reads the `id` field, and entry 1's third dword would land on
`0x00AB95AC`, which is the float rounding magic — so the table is either two entries with
a truncated tail or my field order is wrong. The **index** reading is measurement; the rest is not.

Slice 8 already established that `view+0x11C` is resized to 2 and loaded with the
airport/seaport PNGs — which is what makes the 0/1 index meaningful.

### Phase C — the prop instance (`0x7B57CA`–`0x7B5941`)

`[0x00B43D1C]->vt+0x1C(&obj, <model key>)` creates an instance; a 0x38-byte transform
block is filled with three `1.0f` (`0x3F800000` at `[esp+0x8C]`, `[esp+0x9C]`, `[esp+0xAC]`,
`[esp+0xBC]`) plus the two projected floats and two `1` bytes, handed to `obj->vt+0x1C`,
then `obj->vt+0x0C(0)`, then a 12-byte node `{next, prev, obj}` is allocated and spliced
into `it->_70`. Note: I did not chase `[0x00B43D1C]`; it behaves like a scene/model manager.

**Constants** `[0x00B4E1D4]` (splatted 9× into a 0x24-byte block at `0x7B5800`, a default
transform row), `[0x00A92D28] = 0.5`, `[0x00AB95AC] = 12582912.0f`.
**CALLERS** `sub_7AFAA0` at `0x007B0106`, `sub_7B5D50` at `0x007B5D99` (`RegionView::AddItem`).

---

## What this slice settles

1. **The paint callback's `(arg2, arg3)` is the cache cell's CONTENT-space origin.** Read
   off the caller at `0x007B282F`–`0x007B2842`, not inferred. Item screen position inside a
   cell is `floor(item.fx) − cellX`, `floor(item.fy) − src->GetHeight() − cellY`. Every
   future "where does this pixel come from" question in the region map starts here.

2. **Nothing in this slice resamples.** `sub_7B2A30` gets a destination rect built as
   `{px, py, px + src->GetWidth(), py + src->GetHeight()}` — the size comes from the source
   bitmap and from nowhere else (`0x7B4233` / `0x7B4250`). There is no scale factor, no
   zoom variable, no multiply. **The region map's size is the thumbnails' size.** That is
   the mechanism behind issue #131.

3. **The one draw call that *could* scale** is the overlay-icon path:
   `svc2->vt+0x98(icon, &srcRect, &dstRect)` at `0x7B493F`, where `svc2` comes from
   `GetSystemService(0x0AE6320E, 0x2AE63219)`. It takes independent source and destination
   rects. It is currently fed a translated copy of the source rect.

4. **Region label text size is selectable by GUID.** The two font styles are
   `0x8A8CC984 − 2·item[+0x18]` and `0x8A8CC985 − 2·item[+0x18]`, obtained through the text
   service `{clsid 0xC2C2EB0F, iid 0x22C2EB1F}` (`0x7B44E8`) via `vt+0x14`. The wrap width
   is `thumbnailWidth · 4 / 3` (`imul 0x55555556` at `0x7B4675`). Both are reachable
   without touching a single pixel of art.

5. **The per-city window is positioned by the game, every pan.** `sub_7B4A60` moves each
   `item[+0x30]` window to `(tileCentreX − GetW()/2, tileCentreY − GetH())` on **every**
   pan change, and `sub_7B4B80` repeats the identical block whenever the window is refilled.
   Any mod that repositions those windows will be overwritten on the next pan.

6. **A single overlay rebuild invalidates the entire map.** `sub_7B5430` marks every cache
   cell dirty and un-builds every item composite (`0x7B54D0`, `0x7B54F7`).

7. **The projection basis exists twice** — `0xB0DBA4..0xB0DBB0` (pixels per cell) and
   `0xB0DBBC..0xB0DBD0` (the same numbers ÷1024, plus an elevation column). A patch that
   changes one and not the other will de-register the icons from the thumbnails.

---

## Corrections to `funcs.json` and to GROUND TRUTH

1. **`funcs.json` is missing a function start at `0x007B5300`.** It lists
   `sub_7B51D0 .. 0x7B5350` (384 bytes). The real boundary is `0x7B51D0..0x7B5300`
   (304 bytes, `ret 0xC` at `0x7B52FD`), and `0x7B5300` begins a separate function — the
   tile cache's scalar-deleting destructor, reached from vtable `[0x00AB9624] = 0x007B3E70`
   (`sub ecx,4; jmp 0x7B5300`). It has no direct callers, which is why the builder missed it.

2. **GROUND TRUTH understates `sub_7B3030`.** It says "item → screen point (no multiply;
   reads item+0x10/+0x14 floats and subtracts the pan)". The bytes at `0x007B3030`–`0x007B30A2`
   show it does three more things:
   * both components go through `floor()` (`call 0x009EFF60`) before `_ftol` (`0x009EEF04`);
   * the **Y result additionally subtracts `item[+0x1C]->GetHeight()`** (`vt+0x28` at
     `0x7B307B`, `fsubr` at `0x7B3090`) — so `item[+0x14]` is the **bottom** anchor and the
     returned point is the tile's **top-left**;
   * the height is treated as **unsigned** (`fadd [0x00A80AA8] = 4294967296.0f` when negative,
     `0x7B308A`).
   The same three steps are inlined verbatim twice inside `sub_7B4150` (`0x7B435A` and
   `0x7B4988`), so this is not a one-off.

3. **GROUND TRUTH's "`sub_7B2A30` blits with a per-pixel inc/inc loop"** — slice 6 already
   corrected this (opaque fast path exists). Repeating it here only because slice 7 is the
   sole caller of `sub_7B2A30`, `sub_7B2DD0`, `sub_7B3300` and `sub_7B3670`.

4. **`vt+0x48` on the destination surface takes TWO arguments, not one.** `FillRect(rect, colour)`.
   Proof is a stack-balance argument across the two mutually exclusive branches that meet at
   `0x007B41C4`: the `push 0` at `0x7B4165` is consumed as the 7th argument of `sub_8D8BC0`
   on the taken branch, and as the `rect` argument of `vt+0x48` on the other. Any other
   reading leaves the two paths `esp`-inconsistent.

---

## Open questions (flagged, not guessed)

* Note: **The wallpaper phase `−(pan + cell)`** (`0x7B417D`/`0x7B418A`) versus the item offset
  `−cell`. My screen-locked-modulo-512 reconciliation is an inference. A live probe that
  pans the region and watches whether the backdrop moves would settle it in one minute.
* Note: **`MakeColor(0x3C,0x53,0x8C)` at `0x7B4540` is dead.** If it was meant to be a text
  drop-shadow, the shadow draw call is gone from the binary.
* Note: **`y2 = y1 + h2`** (`0x7B4770`) uses the mayor style's line height to offset from the
  city style's baseline. Harmless when the two styles match; a visible defect if a mod
  gives them different sizes. Directly relevant if #131 changes the region label fonts.
* Note: **Pass 1 has no screen-space cull** (see the WARNING in `sub_7B4150`). I am confident in
  the bytes; I am not confident it is a *bug* rather than deliberate reliance on
  `sub_7B2A30`'s own clipping.
* Note: `[0x00B43DD0]` (`vt+0x50` repaint / `vt+0x84` unregister) and `[0x00B43D1C]`
  (`vt+0x1C` create instance) are unidentified globals.
* Note: The text service `{0xC2C2EB0F, 0x22C2EB1F}` and its slot usage (`vt+0x14` style-by-GUID,
  `vt+0x8C` used **with an argument** on the service at `0x7B46B3` but **without one** on a
  style at `0x7B468C`) do not line up cleanly with the singleton slot table in
  `SC4-UI-ENGINE.md:2118`. Two different classes are almost certainly involved; I did not
  separate them.
* Note: `vt+0x10` on a tile buffer (`sub_7B5350:0x7B536B`, `sub_7B5430:0x7B5477`) is not in
  slice 6's slot table. Context says "release the pixel storage".
