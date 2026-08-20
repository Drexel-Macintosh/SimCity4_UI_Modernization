# SC4 Region Screen — SLICE 2 of 8 : `0x007AACE0` … `0x007AC620`

SimCity 4 Deluxe 1.1.641, 32-bit x86, ImageBase `0x400000`, fileOffset = VA − 0x400000.
Every VA / byte below was read from the shipped exe with
`tools\research\scripts\disasm.py` or a raw byte read. Function boundaries come
from `tools\uimap\funcs.json`.

---

## Table of contents (32 functions, in address order)

| # | Function | Range | Bytes | One line |
|---|---|---|---|---|
| 1 | [`sub_7AACE0`](#sub_7aace0) | 7AACE0..7AAD60 | 128 | **ctor** of the flat region terrain grid (vtable `0xAB8C00`, global `[0xB43CF8]`) |
| 1b | [`sub_7AAD30`](#sub_7aad30) | 7AAD30..7AAD60 | 48 | (inside #1's span, missing from funcs.json) scalar-deleting dtor of that grid |
| 2 | [`sub_7AAD60`](#sub_7aad60) | 7AAD60..7AADF0 | 144 | grid `vt+0x64`: world (x,z) float → **cell index** = floor(z/cell)*stride + floor(x/cell) |
| 3 | [`sub_7AADF0`](#sub_7aadf0) | 7AADF0..7AAE10 | 32 | grid `vt+0x68/0x6C/0x70`: normal = **(0, 1, 0)** — the region terrain is FLAT |
| 4 | [`sub_7AAE10`](#sub_7aae10) | 7AAE10..7AAEC0 | 176 | **ctor** of the right-drag auto-scroll window (vtable `0xAB8CD0`, 0x138 bytes) |
| 5 | [`sub_7AAEC0`](#sub_7aaec0) | 7AAEC0..7AAF20 | 96 | scroll-win `GZOnMouseUpR` — kill the anchor marker, stop scrolling |
| 6 | [`sub_7AAF20`](#sub_7aaf20) | 7AAF20..7AB130 | 528 | scroll-win `GZOnMouseMove` — 8-way direction cursor + velocity from drag distance |
| 7 | [`sub_7AB130`](#sub_7ab130) | 7AB130..7AB520 | 1008 | scroll-win `GZPaint` — the per-frame scroll integrator + edge-scroll + PostMsg |
| 8 | [`sub_7AB520`](#sub_7ab520) | 7AB520..7AB560 | 64 | class-`0xAB8F50` `Init` — latch global `[0xB43DD0]` into `+0xD8` |
| 9 | [`sub_7AB560`](#sub_7ab560) | 7AB560..7AB590 | 48 | class-`0xAB8F50` `Shutdown` — release `+0xD8` |
| 10 | [`sub_7AB590`](#sub_7ab590) | 7AB590..7AB5C0 | 48 | class-`0xAB8F50` `GZPaint` — begin/draw/end on `[+0xD8]` |
| 11 | [`sub_7AB5C0`](#sub_7ab5c0) | 7AB5C0..7AB5E0 | 32 | class-`0xAB8F50` scalar-deleting dtor (`vt+0x250`) |
| 12 | [`sub_7AB5E0`](#sub_7ab5e0) | 7AB5E0..7AB630 | 80 | class-`0xAB8F50` real dtor |
| 12b | [`sub_7AB600`](#sub_7ab600) | 7AB600..7AB630 | 48 | (inside #12's span, missing from funcs.json) dtor of the `0xAB8CB8`/`0xAB8CA0` MI pair |
| 13 | [`sub_7AB630`](#sub_7ab630) | 7AB630..7AB760 | 304 | **draws the region ground quad** from the grid dims — 4 verts, one call |
| 14 | [`sub_7AB760`](#sub_7ab760) | 7AB760..7AB790 | 48 | RegionScreen `GZOnMouseMove` → `sub_7B5DD0(view, x, y)` |
| 15 | [`sub_7AB790`](#sub_7ab790) | 7AB790..7AB7C0 | 48 | RegionScreen `GZOnMouseDownR` → forwards to the scroll window at `+0x174` |
| 16 | [`sub_7AB7C0`](#sub_7ab7c0) | 7AB7C0..7AB9F0 | 560 | **THE LAYOUT FUNCTION** — region px extent from the 4 iso floats; pan clamp `+0x180..+0x18C` |
| 17 | [`sub_7AB9F0`](#sub_7ab9f0) | 7AB9F0..7ABB00 | 272 | RegionScreen `DoMessage` — the 4 message ids incl. the scroll accumulator |
| 18 | [`sub_7ABB00`](#sub_7abb00) | 7ABB00..7ABB60 | 96 | post a notification object to the global message server `[0xB43CCC]` |
| 19 | [`sub_7ABB60`](#sub_7abb60) | 7ABB60..7ABB80 | 32 | RegionScreen `GZOnMouseExit` → `sub_7B5DB0(view)` |
| 20 | [`sub_7ABB80`](#sub_7abb80) | 7ABB80..7ABCD0 | 336 | **assign the DEFAULT tile art pair to an item** (RGB + alpha-mask) by size class |
| 21 | [`sub_7ABCD0`](#sub_7abcd0) | 7ABCD0..7ABDF0 | 288 | **per-pixel alpha stamp**: dst.RGB kept, dst.A ← (mask pixel & 0xFF) |
| 22 | [`sub_7ABDF0`](#sub_7abdf0) | 7ABDF0..7ABF10 | 288 | select one of the 3 region view modes (button + panel + child radio) |
| 23 | [`sub_7ABF10`](#sub_7abf10) | 7ABF10..7AC110 | 512 | **read the region-screen tuning exemplar** (13 properties incl. the layout margins) |
| 24 | [`sub_7AC110`](#sub_7ac110) | 7AC110..7AC1A0 | 144 | leave/reset the current selection state on the view |
| 25 | [`sub_7AC1A0`](#sub_7ac1a0) | 7AC1A0..7AC270 | 208 | **drive the camera** from window centre + pan accumulators + scene basis |
| 26 | [`sub_7AC270`](#sub_7ac270) | 7AC270..7AC2D0 | 96 | store region name into prefs+0xEBC, clear the saved pan (0x80000000), SavePreferences |
| 27 | [`sub_7AC2D0`](#sub_7ac2d0) | 7AC2D0..7AC380 | 176 | store the CURRENT pan (×256) into prefs+0xEBC+0x40/0x44, SavePreferences |
| 28 | [`sub_7AC380`](#sub_7ac380) | 7AC380..7AC490 | 272 | **RegionScreen teardown** — releases +0x158/+0x15C/+0x160/+0x164/+0x168/+0x16C |
| 29 | [`sub_7AC490`](#sub_7ac490) | 7AC490..7AC4D0 | 64 | `std::make_heap`-style loop over 12-byte draw-order records |
| 30 | [`sub_7AC4D0`](#sub_7ac4d0) | 7AC4D0..7AC5C0 | 240 | `std::_Adjust_heap` for those records — **key = x + y + (1 << sizeLog2)** |
| 31 | [`sub_7AC5C0`](#sub_7ac5c0) | 7AC5C0..7AC620 | 96 | scroll-win scalar-deleting dtor (`vt+0x250`) |
| 32 | [`sub_7AC620`](#sub_7ac620) | 7AC620..7AC7D0 | 432 | **create the scroll anchor marker** child window `0x48E945B4` centred on the press |

---

## 0. Two prerequisites this slice MEASURED (use them, don't re-derive)

### 0.1 The cGZWin vtable slot map (measured, not copied from a header)

`cGZWin`'s own vtable is at **`0x00ADC8D8`**. The gzcom-dll header
`vendor/gzcom-dll/gzcom-dll/include/cIGZWin.h` is correct at the top and **+1 slot
short from somewhere after `SetArea(l,t,r,b)`**. Anchors proved by reading the
function bodies:

| Real slot | Target in cGZWin | Proof |
|---|---|---|
| `+0x00` | QueryInterface | `0x0099B774` |
| `+0x04` | AddRef | `0x0094C47C`; called as `vt+4` on refcounted temps throughout this slice |
| `+0x08` | Release | `0x0099B7A3` |
| `+0x0C` | **DoMessage** | `0x0099CCF0`; `sub_7AB9F0` (RegionScreen vt+0x0C) tail-jumps to it |
| `+0x10` | **Init** | `0x0099C2C3`; `sub_7AB520` tail-jumps to it |
| `+0x14` | **Shutdown** | `0x0099D2FE`; `sub_7AB560` and `sub_7AC5C0` call it |
| `+0x1C` | SetWindowManager | `0x0099CA0B` = `mov [ecx+4],arg; ret 4` ⇒ **cGZWin+0x04 is the cIGZWinMgr\*** |
| `+0x38` | ChildAdd | used in `sub_7AC620` |
| `+0x40` | ChildDelete | `0x0099B833` = `mov ecx,[ecx+4]; jmp [winmgr_vt+0x5C]` (WinMgr::DestroyWindow) |
| `+0x88` | GetChildWindowFromID | `0x0099DE74`, walks `[this+0x44]` (the child list) |
| `+0xA4` | GetW | `0x0099C81B` = `[ecx+0xB0] − [ecx+0xA8]` |
| `+0xA8` | GetH | `0x0099C82A` = `[ecx+0xB4] − [ecx+0xAC]` |
| `+0xAC` | GetL | `0x0099BC53` = `return [ecx+0xA8]` |
| `+0xB0` | GetT | `0x00994EE4` = `return [ecx+0xAC]` |
| `+0xB4` | GetR | `0x0099BC5A` = `return [ecx+0xB0]` |
| `+0xB8` | GetB | `0x0099BC61` = `return [ecx+0xB4]` |
| `+0xBC` | GetArea(cRZRect&) | `0x0099BCEC` (rep-movsd of 4 ints from `ecx+0xA8`) |
| `+0xC0` | GetArea() | `0x0099BCE1` = `lea eax,[ecx+0xA8]` |
| `+0xDC` | SetArea(l,t,r,b) | 4 args pushed at `sub_7AC620:0x7AC746` |
| `+0x10C` | GetFlag | `0x0099BDBB` |
| `+0x110` | **SetFlag(flag,bool)** | `0x0099DB6B` — ORs/ANDs `[this+0xC8]` |
| `+0x114` | ShowWindow | called right after SetFlag in `sub_7AC620` |
| `+0x154` | **SetCursor(pCursor,bool)** | `0x0099B993` = `[ecx+0x74]=p; if(arg1) vt+0x150()` |
| `+0x158` | SetNotificationTarget | `0x0099BE42` = `mov [ecx+0x4C],arg` ⇒ **cGZWin+0x4C = notification target** |
| `+0x15C` | GetNotificationTarget | `0x0099BE4C` = `return [ecx+0x4C]` |
| `+0x160` | **GZPaint** | `0x00949ADE` in the base; overridden by `sub_7AB130` and `sub_7AB590` |
| `+0x218..+0x228` | GZOnMouseDownL / DownR / UpL / UpR / Move | five consecutive slots all holding the SAME base stub `0x009378BC`; `+0x22C` (MouseWheel) holds a different stub `0x00938789` — that run of five pins the numbering with no header needed |
| `+0x244` | SendMsg(win, cGZMessage const&) | `0x0099BFEC` — `winMgr->IsWindowValid` then `win->DoMessage` |
| `+0x248` | **PostMsg(win, msgType, d1, d2, d3)** | `0x0099CA60` packs a cGZMessage and calls `vt+0x24C` |
| `+0x24C` | PostMsg(win, cGZMessage const&) | `0x0099C011` = `winMgr->vt+0x3C` = PostMessageToTarget |
| `+0x250` | **scalar-deleting destructor** | base `0x009D060A`; overridden by `sub_7AC5C0` and `sub_7AB5C0` |

`cIGZWinMgr` slots used in this slice (gzcom-dll `cIGZWinMgr.h`, first virtual at `+0x0C`,
all corroborated by call shape): `+0x5C` DestroyWindow, `+0x60` IsWindowValid,
`+0x78` **GZReleaseCapture(win)**, `+0x80` GetCursorManager, `+0x88`
**GetCursorRelativePosition(win, int& x, int& y)**.

### 0.2 Globals this slice touches

| Global | Meaning | Evidence |
|---|---|---|
| `[0xB43CF8]` | the flat region terrain grid (ctor `sub_7AACE0`) | `sub_7AC380` zeroes it in the same block that releases `RegionScreen+0x16C` — **confirms GROUND TRUTH** |
| `[0xB43C94]` | the app singleton (Note: *inferred* cISC4App) | `vt+0x44` = SavePreferences, `vt+0x98` = GetPreferences, `vt+0x88` = the region object |
| `[0xB43CA8]` | a GZCOM resource/properties service | `sub_7ABF10`, `vt+0x0C(key, ...)` |
| `[0xB43CB0]` | a service that takes `vt+0x50(win,0,0)` | `sub_7AB9F0` msg 0x1B branch |
| `[0xB43CCC]` | the message server | `sub_7ABB00`, `vt+0x10(msgObj, 0)` |
| `[0xB43CD8]` | an object with a bool at `+0xF09` gating the edge-scroll | `sub_7AB130` |
| `[0xB43DD0]` `[0xB43DD8]` `[0xB43DDC]` `[0xB43D1C]` | region-screen scratch globals, all zeroed in `sub_7AC380` | |
| `[0xB4E1C0] [0xB4E1C4] [0xB4E1C8]` + flag `[0xB4E1CC]` | three tunables loaded from the exemplar | `sub_7ABF10` |
| `[0xB217B0] [0xB217B4]` | two byte tunables mirrored to globals | `sub_7ABF10` |
| `[0xB628C0]` | cached cIGZWinMgr singleton, fetched by `0x00913C46` | |
| `[0xB628C4]` | cached region-window-factory singleton, fetched by `0x00913C72` (built by `0x7B2480`) | |

Float constants referenced (values read from .rdata/.data):

| VA | Value |
|---|---|
| `0xA80AA8` | `4294967296.0` (unsigned-int fixup) |
| `0xA81054` | `0.0` |
| `0xA81228` | `1.0` |
| `0xA84D2C` | `0.5` |
| `0xA867A4` | `0.001` (ms → s) |
| `0xA9422C` | `256.0` |
| `0xAA6E60` | `0.00390625` = 1/256 |
| `0xAB8BE0` | `12582912.0` = 1.5·2²³ (float→int rounding magic) |
| `0xB0DBA4` | `+90.51` |
| `0xB0DBA8` | `+18.75` |
| `0xB0DBAC` | `−37.49` |
| `0xB0DBB0` | `+45.25` |

---

## Function detail

<a name="sub_7aace0"></a>
### `sub_7AACE0` (0x7AACE0..0x7AAD60, 128 bytes) — region terrain-grid ctor

**PURPOSE** Constructs the flat height-field object that stands in for terrain in the
region view. Its vtable is `0x00AB8C00` (a second base vptr `0x00AB8BE8` at `+0x04`,
so this is multiple inheritance). Also cached in global `[0xB43CF8]`.

**CONVENTION** `__thiscall(uint32 widthCells, uint32 heightCells)`, `ret 8`.

```c
Grid* Grid::Grid(this, int32 w, int32 h)   // ret 8
{
    *(void**)this        = 0x00AB3BE8;      // temporary base vptr
    sub_90D957(this + 4);                   // second base ctor
    *(void**)(this + 4)  = 0x00AB8BE8;
    *(void**)this        = 0x00AB8C00;      // final vptr
    this->0x0C = 0x43870000f;               // 270.0f   base terrain height
    this->0x10 = 0;
    this->0x14 = w;                         // width in cells
    this->0x18 = h;                         // height in cells
    this->0x1C = w + 1;                     // ROW STRIDE = w+1
    this->0x20 = 0x42800000f;               // 64.0f    world units per cell
    this->0x24 = (byte)0;
    return this;
}
```

**FIELDS** `+0x00` vptr; `+0x04` second vptr; `+0x0C` float 270.0 base height;
`+0x10` 0; `+0x14` int width; `+0x18` int height; `+0x1C` int stride = width+1;
`+0x20` float 64.0 cell size; `+0x24` byte flag.

Accessors proved by reading the tiny bodies in vtable `0xAB8C00`:
`vt+0x18` = `0x7AA300` `fld [ecx+0x20]` → **cell size (64.0f)**;
`vt+0x1C` = `0x0040CE70` `return [ecx+0x14]` → **width**;
`vt+0x20` = `0x0040CF10` `return [ecx+0x18]` → **height**;
`vt+0x24` = `0x7AA310` `return [ecx+0x1C]*y + x` (index from x,y);
`vt+0x28` = `0x7AA320` `idiv [ecx+0x1C]` (x,y from index);
`vt+0x54`/`vt+0x58` = `0x7AA4D0` `fld [ecx+0x0C]` → **base height (270.0f)**.

**CALLERS** one site, `0x007ACD75` in `sub_7ACC90`.

<a name="sub_7aad30"></a>
### `sub_7AAD30` (0x7AAD30..0x7AAD60, 48 bytes) — Note: NOT in funcs.json

Scalar-deleting destructor of the same class: restores both vptrs, calls
`0x90D964` (second-base dtor), and `if (arg0 & 1) operator delete(this)`.
`__thiscall(uint8 flags)`, `ret 4`, returns `this`.
**funcs.json has no start at 0x7AAD30** — it is swallowed by `sub_7AACE0`'s span.

<a name="sub_7aad60"></a>
### `sub_7AAD60` (0x7AAD60..0x7AADF0, 144 bytes) — grid `vt+0x64` : world → cell index

**PURPOSE** Convert two float world coordinates into a linear cell index.

**CONVENTION** `__thiscall(float x, float z)` → `int`, `ret 8`.

```c
int Grid::CellIndexFromWorld(this, float x, float z)   // vtable 0xAB8C00 slot +0x64
{
    float inv = 1.0f / this->0x20;      // [0xA81228]=1.0 / cellSize (64.0)
    int row = floor_i(z * inv);
    int col = floor_i(x * inv);
    return this->0x1C * row + col;      // stride = width+1
}
```

`floor_i` is the classic MSVC idiom, emitted twice verbatim:
`v − 0.5f`, `fadd [0xAB8BE0]` (12582912.0), `fstp`, `mov r,[slot]`,
`add r, 0xB4C00000` (= −0x4B400000, strips the magic bias), then a `fild(r+1)` /
`fucompp` fix-up that bumps `r` by one when `v == r+1` — i.e. it repairs the
round-half-to-even case. Net = **floor**.

**FIELDS READ** `+0x1C` stride, `+0x20` cell size.
**CALLERS** none direct — reached only through vtable `0xAB8C00 + 0x64`.

<a name="sub_7aadf0"></a>
### `sub_7AADF0` (0x7AADF0..0x7AAE10, 32 bytes) — grid `vt+0x68/0x6C/0x70` : normal

```c
void Grid::GetNormal(this, ?, ?, float* out)  // ret 0xC
{ out[0] = 0.0f; out[1] = 1.0f; out[2] = 0.0f; }
```
Occupies **three** consecutive vtable slots (`0xAB8C68`, `0xAB8C6C`, `0xAB8C70`).
**The region terrain is a flat plane; its normal is always straight up.**

<a name="sub_7aae10"></a>
### `sub_7AAE10` (0x7AAE10..0x7AAEC0, 176 bytes) — auto-scroll window ctor

**PURPOSE** Constructs the cGZWin subclass that implements **right-button drag
scrolling** of the region map. Allocated `0x138` bytes at `0x7B1E2A` (`push 0x138;
call 0x5E55E0`) inside `cSC4WinRegionScreen::Init` (`sub_7B1900`) and stored at
**`RegionScreen+0x174`** — confirmed by `sub_7AB790`, which forwards
`GZOnMouseDownR` into `[this+0x174]->vt+0x21C`.

**CONVENTION** `__thiscall()`, no args, `ret` (0), returns `this`.

```c
ScrollWin* ScrollWin::ScrollWin(this)
{
    cGZWin::cGZWin(this);                     // 0x0099D938, sets vptr 0x00ADC8D8
    *(void**)this = 0x00AB8CD0;
    this->0xDC = this->0xE0 = 0;              // anchor point (int x, int y)
    this->0xE4 = this->0xE8 = 0;              // velocity accumulator (float x, y)
    this->0xEC = this->0xF0 = 0;              // damped velocity (float)
    this->0xF4 = this->0xF8 = 0;              // direction*speed (float)
    this->0xFC = this->0x100 = 0;             // edge-scroll bias (float)
    this->0x104 = 0x43960000f;                // 300.0f  edge-scroll step
    this->0x108 = this->0x109 = (byte)0;      // "scrolling" / "armed" latches
    this->0x10C = 0;                          // the marker image (cIGZ...*)
    this->0x110 = 10;                         // dead-zone radius, px
    this->0x114 = 32;                         // max drag radius, px
    this->0x118 = 0x40A00000f;                // 5.0f   velocity scale
    this->0x11C = 0x40400000f;                // 3.0f   speed-ramp divisor
    ArrayInit(this + 0x120, 4);               // 0x0088FEDF, element size 4
    return this;
}
```

**vtable `0x00AB8CD0` overrides (diffed slot-for-slot against cGZWin `0x00ADC8D8`)**

| slot | name | target |
|---|---|---|
| `+0x010` | Init | `0x007AA520` *(slice 1)* |
| `+0x014` | Shutdown | `0x007AA570` *(slice 1)* |
| `+0x160` | GZPaint | **`0x007AB130`** |
| `+0x21C` | GZOnMouseDownR | `0x007AD3B0` *(slice 3)* |
| `+0x224` | GZOnMouseUpR | **`0x007AAEC0`** |
| `+0x228` | GZOnMouseMove | **`0x007AAF20`** |
| `+0x250` | scalar-deleting dtor | **`0x007AC5C0`** |

Everything else is inherited. **A 9-entry cursor table sits immediately after the
vtable at `0x00AB8F2C`** (see `sub_7AAF20`).

**CALLERS** one site, `0x007B1E38` in `sub_7B1900`.

<a name="sub_7aaec0"></a>
### `sub_7AAEC0` (0x7AAEC0..0x7AAF20, 96 bytes) — scroll-win `GZOnMouseUpR`

**CONVENTION** `__thiscall(int x, int y, uint32 mods)` → bool, `ret 0xC`. Returns **true**.

```c
bool ScrollWin::GZOnMouseUpR(this, int x, int y, uint32 mods)
{
    cIGZWin* marker = this->GetChildWindowFromID(0x48E945B4);   // vt+0x88
    if (marker) this->ChildDelete(marker);                      // vt+0x40 -> WinMgr::DestroyWindow
    this->0x109 = 0;                       // disarm
    this->0xF4 = this->0xF8 = 0;           // velocity := 0
    this->winMgr->GZReleaseCapture(this);  // [this+4]->vt+0x78
    this->SetFlag(0x200000, true);         // vt+0x110, WinFlag_IgnoreMouse back ON
    return true;
}
```

`0x48E945B4` is the anchor-marker child created by `sub_7AC620`.
Note: Our own `UiSpike.cpp` calls `0x48E945B4` the "EDGE bubble / U-Drive-It marker".
The bytes here say the *region screen* also uses that id for its scroll anchor —
treat any id-keyed logic on `0x48E945B4` as **not unique to the city view**.

<a name="sub_7aaf20"></a>
### `sub_7AAF20` (0x7AAF20..0x7AB130, 528 bytes) — scroll-win `GZOnMouseMove`

**PURPOSE** While the right button is held, turn the cursor's offset from the anchor
into (a) a scroll velocity and (b) one of nine direction cursors.

**CONVENTION** `__thiscall(int x, int y, uint32 mods)` → bool, `ret 0xC`. Returns **false**
(`xor al,al` at `0x7AB120`) — i.e. "not consumed".

```c
bool ScrollWin::GZOnMouseMove(this, int x, int y, uint32 mods)
{
    float dx = (float)(x - this->0xDC);
    float dy = (float)(y - this->0xE0);
    float d2 = dx*dx + dy*dy;
    int   rMin = this->0x110;              // 10

    if (d2 < (float)(rMin*rMin)) {         // inside the dead zone -> STOP
        this->0xF4 = this->0xF8 = 0;
        cursorId = 0xC2A676AC;             // the neutral cursor
        goto setCursor;
    }

    float dist    = sqrtf(d2);
    float clamped = (dist > (float)this->0x114) ? (float)this->0x114 : dist;  // 32
    float t       = (clamped - (float)rMin) / this->0x11C;                    // /3.0
    float speed   = (t < 1.0f) ? 1.0f : t;                                    // 1.0 .. 7.333
    float k       = speed / dist;
    this->0xF4 = k * dx;                   // unit direction * speed
    this->0xF8 = k * dy;

    int hx = (dx < -(float)rMin) ? 0 : (dx >= (float)rMin) ? 2 : 1;
    int hy = (dy < -(float)rMin) ? 0 : (dy >= (float)rMin) ? 2 : 1;
    cursorId = ((uint32*)0x00AB8F2C)[hy*3 + hx];

setCursor:
    cIGZWinMgr* wm = GetWinMgrSingleton();               // 0x00913C46, caches [0xB628C0]
    cursorMgr = wm->GetCursorManager();                  // winmgr vt+0x80
    cursor    = cursorMgr->vt+0x24(cursorId);
    if (cursor) { this->0xD8 = cursorId; this->SetCursor(cursor, true); }  // 0x0099B993
    return false;
}
```

**The 9-entry cursor table at `0x00AB8F2C`** (read as raw dwords), indexed
`row*3 + col`, row 0 = up:

| idx | dir | instance id |
|---|---|---|
| 0 | up-left | `0x02A67691` |
| 1 | up | `0x62A67606` |
| 2 | up-right | `0x82A676A8` |
| 3 | left | `0x62A67694` |
| 4 | **centre / stopped** | `0xC2A676AC` |
| 5 | right | `0xC2A676A4` |
| 6 | down-left | `0xA2A67698` |
| 7 | down | `0x62A6769B` |
| 8 | down-right | `0x22A676A0` |

Index 4 is byte-identical to the hard-coded `mov edi, 0xC2A676AC` at `0x7AB061`.

**FIELDS** reads `+0xDC/+0xE0` anchor, `+0x110` (10), `+0x114` (32), `+0x11C` (3.0f);
writes `+0xD8` current cursor id, `+0xF4/+0xF8` velocity.

<a name="sub_7ab130"></a>
### `sub_7AB130` (0x7AB130..0x7AB520, 1008 bytes) — scroll-win `GZPaint` (`vt+0x160`)

**PURPOSE** This is the per-frame scroll integrator. It is hung on **GZPaint**, not on a
timer. It (1) samples the cursor, (2) adds an edge-scroll push when the cursor is
within 1 px of a window edge, (3) integrates velocity over elapsed ms, and
(4) posts scroll deltas to the notification target.

**CONVENTION** `__thiscall()` → bool, `ret` (0 args). Returns **true** on every path.

```c
bool ScrollWin::GZPaint(this)
{
  if (!Timer_IsRunning(this + 0x120))  { Timer_Start(this + 0x120); return true; }   // 0x0088FEFB / 0x008905C4
  uint32 dtMs = Timer_Read(this + 0x120);                                            // 0x00890198
  Timer_Reset(this + 0x120);                                                         // 0x0089058F

  float vx = this->0xFC + this->0xF4;      // edge bias + drag velocity
  float vy = this->0xF8 + this->0x100;

  bool edgeScrollEnabled = false;
  if (*(byte*)(*(void**)0x00B43CD8 + 0xF09)) {                 // a global toggle
      AutoRef tmp; GetSetting(0x00B43CD8-ish svc, 0xC416025C, 0x0073283C, &tmp);
      edgeScrollEnabled = tmp->vt+0x30();
      tmp.Release();                                            // 0x004495C0
  }

  if (edgeScrollEnabled) {
      int cx, cy;
      this->winMgr->GetCursorRelativePosition(this, &cx, &cy);  // winmgr vt+0x88
      if      (cx <= this->GetL() + 1) vx -= this->0x104;       // 300.0f
      else if (cx >= this->GetR() - 1) vx += this->0x104;
      if      (cy <= this->GetT() + 1) vy -= this->0x104;
      else if (cy >= this->GetB() - 1) vy += this->0x104;
  }

  if (vx != 0.0f || vy != 0.0f) {
      float dt = (float)dtMs * 0.001f;                     // [0xA867A4]
      this->0xE4 -= dt * this->0xEC;                       // damp
      this->0xE8 -= dt * this->0xF0;
      // if any of sign(vx)/sign(vy)/sign(0xE4)/sign(0xE8) disagree -> reset all four to 0
      ...
      this->0xE4 = vx; this->0xE8 = vy;
      this->0xEC = vx * this->0x118;                       // 5.0f
      this->0xF0 = vy * this->0x118;
  }

  if (vx == 0.0f && vy == 0.0f) {                          // came to rest
      if (this->0x108) {
          this->PostMsg(this->0x4C, 0x8A4BAC5B, 0, 0, 0);  // vt+0x248  "scroll END"
          this->0x108 = 0;
      }
      return true;
  }

  float dt = (float)dtMs * 0.001f;
  vx *= dt; vy *= dt;
  if (!this->0x108) {
      this->0x108 = 1;
      this->PostMsg(this->0x4C, 0x8A4BAC53, 0, 0, 0);      // "scroll BEGIN"
  }
  this->PostMsg(this->0x4C, 0xAAA1CDF2,
                (int)(vy * 256.0f), (int)(vx * 256.0f), 0); // [0xA9422C] = 256.0
  return true;
}
```

**Message ids** `0x8A4BAC53` begin, `0x8A4BAC5B` end, `0xAAA1CDF2` delta. All three are
handled by `sub_7AB9F0` (`cSC4WinRegionScreen::DoMessage`), and `this->0x4C` is the
cGZWin **notification target** (`SetNotificationTarget` writes `[this+0x4C]`) — so the
scroll window's notification target IS the region screen. The delta is sent in
**1/256 px fixed point** and the receiver multiplies by `1/256` (`[0xAA6E60]`).

**FIELDS** reads `+0xF4/+0xF8`, `+0xFC/+0x100`, `+0x104` (300.0), `+0x118` (5.0), `+0x4C`;
reads/writes `+0xE4/+0xE8` (velocity), `+0xEC/+0xF0` (damping), `+0x108` (in-scroll latch),
`+0x120` (the elapsed-time timer object).
**vtable calls** `vt+0xAC` GetL, `vt+0xB0` GetT, `vt+0xB4` GetR, `vt+0xB8` GetB,
`vt+0x248` PostMsg; winMgr `vt+0x88` GetCursorRelativePosition.
Note: `0x0073283C` pushed at `0x7AB1BB` looks like a code address but is used as a **GZIID**;
`0xC416025C` is the service/setting id. Not further resolved.

<a name="sub_7ab520"></a>
### `sub_7AB520` (0x7AB520..0x7AB560, 64 bytes) — class-`0xAB8F50` `Init` (`vt+0x10`)

```c
bool X::Init(this) {
    Swap+ref(this->0xD8, (IUnknown*)[0x00B43DD0]);   // AddRef new, Release old
    return cGZWin::Init(this);                       // tail jmp 0x0099C2C3
}
```
Class `0xAB8F50` is a **second, smaller cGZWin subclass** in the region module: it
overrides only `Init`(`+0x10`)→`7AB520`, `Shutdown`(`+0x14`)→`7AB560`,
`GZPaint`(`+0x160`)→`7AB590` and the dtor(`+0x250`)→`7AB5C0`.
Note: Not named; it paints whatever `[0xB43DD0]` currently is.

<a name="sub_7ab560"></a>
### `sub_7AB560` (0x7AB560..0x7AB590, 48 bytes) — class-`0xAB8F50` `Shutdown`

```c
bool X::Shutdown(this) {
    if (this->0xD8) { void* p = this->0xD8; this->0xD8 = 0; p->Release(); }
    return cGZWin::Shutdown(this);   // tail jmp 0x0099D2FE
}
```

<a name="sub_7ab590"></a>
### `sub_7AB590` (0x7AB590..0x7AB5C0, 48 bytes) — class-`0xAB8F50` `GZPaint`

```c
bool X::GZPaint(this) {
    this->0x6C->vt+0xA8();      // begin
    this->0xD8->vt+0x54();      // draw
    this->0x6C->vt+0xAC();      // end
    return true;
}
```
`cGZWin+0x6C` is zeroed by the base ctor `0x0099D938`; Note: I could not prove what it
is — most likely the draw context / render target wrapper.

<a name="sub_7ab5c0"></a>
### `sub_7AB5C0` (0x7AB5C0..0x7AB5E0, 32 bytes)

Scalar-deleting destructor at `0x00AB91A0` = vtable `0xAB8F50 + 0x250` — the **same
slot** as `sub_7AC5C0` in the other class, which is what proves `+0x250` is the dtor.
`__thiscall(uint8 flags)`, `ret 4`: `sub_7AB5E0(this); if (flags & 1) operator delete(this);`

<a name="sub_7ab5e0"></a>
### `sub_7AB5E0` (0x7AB5E0..0x7AB630, 80 bytes)

```c
void X::~X(this) {
    *(void**)this = 0x00AB8F50;
    if (this->0xD8) this->0xD8->Release();
    cGZWin::~cGZWin(this);       // tail jmp 0x0099E1A2
}
```

<a name="sub_7ab600"></a>
### `sub_7AB600` (0x7AB600..0x7AB630, 48 bytes) — Note: NOT in funcs.json

Scalar-deleting destructor of a **multiple-inheritance pair**: primary vptr
`0x00AB8CB8`, secondary vptr `0x00AB8CA0` at `+0x04`; calls `0x0090D990` then the
optional `operator delete`. Vtable `0xAB8CB8` is tiny: `+0x00`=`0x005BCB40`,
`+0x04`=`0x005BE3E0` (AddRef), `+0x08`=`0x005BCB30` (Release), **`+0x0C` = `sub_7AB630`**.
So this object is a **render callback** whose one interesting method is the ground draw.

<a name="sub_7ab630"></a>
### `sub_7AB630` (0x7AB630..0x7AB760, 304 bytes) — draw the region ground quad

**PURPOSE** Emits the single flat quad that is the region's ground/water plane, sized
directly from the terrain grid.

**CONVENTION** `__thiscall(Renderer* r)` → bool (`mov al,1`), `ret 4`.
Called through vtable `0x00AB8CB8 + 0x0C`.

```c
bool GroundDraw::Draw(this, Renderer* r)
{
    Grid* g = (Grid*)[0x00B43CF8];
    sub_7D4530(r, this + 0x0C);          // bind material/texture held at this+0x0C
    float y  = g->vt+0x54();             // 270.0f, base height
    float cw = g->vt+0x18() * (float)g->vt+0x1C();   // cellSize * widthCells
    float ch = g->vt+0x18() * (float)g->vt+0x20();   // cellSize * heightCells

    Vertex v[4];                         // 0x10 bytes each: float x, y, z; uint32 colour
    v[0] = { 0.0f, y, 0.0f,  0xFF400000 };
    v[1] = { 0.0f, y,  ch,   0xFF400000 };
    v[2] = {  cw,  y,  ch,   0xFF400000 };
    v[3] = {  cw,  y, 0.0f,  0xFF400000 };

    sub_7D2970(r, 1, 4, v);              // -> [r+0x30]->vt+0x14(1, 4, v, 0)
    sub_7FC2D0(r, 6, 0, 4);              // -> [r+0x30]->vt+0x0C(6, 0, 4)
    return true;
}
```

The colour dword is written as four byte stores per vertex (`+0x0C`=0, `+0x0D`=0,
`+0x0E`=`0x40`, `+0x0F`=`0xFF`) → little-endian `0xFF400000`.
Note: Whether that is D3DCOLOR ARGB (A=FF, R=0x40) or something else is a guess.
`0x7D2970` and `0x7FC2D0` are one-line forwarders into `[renderer+0x30]`'s vtable.

<a name="sub_7ab760"></a>
### `sub_7AB760` (0x7AB760..0x7AB790, 48 bytes) — RegionScreen `GZOnMouseMove`

At `0x00AB9488` = `cSC4WinRegionScreen` vtable `0xAB9260 + 0x228`.
`__thiscall(int x, int y, uint32 mods)` → bool (always true), `ret 0xC`.

```c
bool RegionScreen::GZOnMouseMove(this, int x, int y, uint32 mods) {
    if (!this->0x1A0)                       // byte "suppress hover" latch
        sub_7B5DD0(this->0xE0 /*the view*/, x, y);
    return true;
}
```

<a name="sub_7ab790"></a>
### `sub_7AB790` (0x7AB790..0x7AB7C0, 48 bytes) — RegionScreen `GZOnMouseDownR`

At `0x00AB947C` = vtable `0xAB9260 + 0x21C`.
`__thiscall(int x, int y, uint32 mods)` → bool (always true), `ret 0xC`.

```c
bool RegionScreen::GZOnMouseDownR(this, int x, int y, uint32 mods) {
    this->0x174->vt+0x21C(x, y, mods);   // = ScrollWin::GZOnMouseDownR = sub_7AD3B0
    return true;
}
```
**This is the hard link that proves `RegionScreen+0x174` holds the class-`0xAB8CD0`
scroll window.**

<a name="sub_7ab7c0"></a>
### `sub_7AB7C0` (0x7AB7C0..0x7AB9F0, 560 bytes) — THE REGION LAYOUT FUNCTION

**PURPOSE** Compute the region map's total pixel extent and from it the pan clamp
rectangle. **This is the function that turns the four isometric floats into pixels,
and it is the natural lever for issue #131 (region map too small at 2x/3x).**

**CONVENTION** `__thiscall()`, no args, `ret` (0). Void.
**CALLERS** one site, `0x007B18D5` in `sub_7B13C0`.

```c
void RegionScreen::RecomputePanBounds(this)
{
    Region* rgn  = [0x00B43C94]->vt+0x88();      // Note: inferred cISC4App::GetRegion()
    Obj*    o    = rgn->vt+0x2C(this->0x1A4);    // Note: per-region lookup by id
    int32   r[4]; o->vt+0x60(r);                 // bounding rect in CELLS

    int W = r[2] - r[0] + 1;                     // width  in region cells
    int H = r[3] - r[1] + 1;                     // height in region cells

    // ---- THE SIZE LAW ----
    int contentW = (int)( fabs(*(float*)0x00B0DBA4) * W      //  90.51
                        + fabs(*(float*)0x00B0DBAC) * H )    //  37.49
                        + 2 * this->0x198;                   //  X margin (exemplar)
    int contentH = (int)( fabs(*(float*)0x00B0DBA8) * W      //  18.75
                        + fabs(*(float*)0x00B0DBB0) * H )    //  45.25
                        + 2 * this->0x19C;                   //  Y margin (exemplar)

    int minX = (int)( -fabs(0x00B0DBAC) * H - GetW()/2 - this->0x198 );
    int minY = (int)( -(float)(this->0x19C + GetH()/2) - *(float*)0x00B0DBB0 );

    int slackX, slackY;
    if (contentW > GetW()) { slackX = contentW - GetW(); minX += GetW()/2; }
    else                   { minX += contentW/2; slackX = 0; }
    if (contentH > GetH()) { slackY = contentH - GetH(); minY += GetH()/2; }
    else                   { minY += contentH/2; slackY = 0; }

    this->0x180 = minX;  this->0x184 = minY;            // pan MIN
    this->0x188 = minX + slackX;                        // pan MAX
    this->0x18C = minY + slackY;

    if (this->0xE4)                                      // a scroller/bounds sink
        sub_7A9C20(this->0xE4,
                   (float)this->0x180,
                   (float)this->0x184,
                   (float)(GetW() + this->0x188),
                   (float)(GetH() + this->0x18C));
}
```

**The two pairs sum to exact powers of two:**
`90.51 + 37.49 = 128.0` (X) and `18.75 + 45.25 = 64.0` (Y).
So **one region cell occupies exactly 128 × 64 screen pixels**, at any resolution.
GROUND TRUTH already stated the 128; the 64 is measured here for the first time,
from a *different* use of the same four constants than the one at `0x7B15D8`.

**FIELDS** reads `+0x198` / `+0x19C` (int margins loaded by `sub_7ABF10`), `+0x1A4`
(a region/city id), `+0xE4`; writes `+0x180`, `+0x184`, `+0x188`, `+0x18C`.
**vtable calls** own `vt+0xA4` GetW, `vt+0xA8` GetH.

<a name="sub_7ab9f0"></a>
### `sub_7AB9F0` (0x7AB9F0..0x7ABB00, 272 bytes) — RegionScreen `DoMessage` (`vt+0x0C`)

At `0x00AB926C` = vtable `0xAB9260 + 0x0C`.
`__thiscall(cGZMessage* m)` → bool, `ret 4`. `m[0]` = type, `m[1]`/`m[2]`/`m[3]` = data.

```c
bool RegionScreen::DoMessage(this, cGZMessage* m)
{
  switch (m->type) {
  case 0x8A4BAC53:                                 // scroll BEGIN
      this->0xE0->0x110 = (byte)1;                 // view "is scrolling" latch
      this->0xE0->vt+0x170();                      // (view) invalidate / begin
      return true;

  case 0x8A4BAC5B:                                 // scroll END
      this->0xE0->0x110 = (byte)0;
      return true;

  case 0xAAA1CDF2:                                 // scroll DELTA (1/256 px)
      this->0x178 += (float)m->data1 * (1.0f/256.0f);   // [0xAA6E60]
      this->0x17C += (float)m->data2 * (1.0f/256.0f);
      return true;

  case 0x1B:                                       // 27 — a UI/keyboard event
      if (m->data2 == 5 || m->data2 == 6) {
          void* p = m->data3;
          ok = this->0x108->vt+0x28(p[1], p[2], (m->data2 == 5), &out);
          if (!ok) return false;
          [0x00B43CB0]->vt+0x50(out, 0, 0);
          return true;
      }
      break;
  }
  return cGZWin::DoMessage(this, m);               // tail jmp 0x0099CCF0
}
```

**Note the axis swap:** the poster (`sub_7AB130`) pushes `(vy*256, vx*256)` as
`(data1, data2)`, and the receiver adds `data1` to `+0x178` and `data2` to `+0x17C`.
Downstream (`sub_7AC1A0`) `+0x178` pairs with **GetW()** and `+0x17C` with **GetH()**.
Note: I did not resolve which of `+0x178`/`+0x17C` the artist would call "X"; the
measured wiring is: `+0x178` ← posted `data1` ← `vy`; used with GetW.

<a name="sub_7abb00"></a>
### `sub_7ABB00` (0x7ABB00..0x7ABB60, 96 bytes) — post a notification object

`__thiscall`-shaped but `ecx` is unused; effectively `__stdcall(void* payload)`, `ret 4`.

```c
void PostRegionNotification(void* payload)
{
    Server* srv = [0x00B43CCC];
    if (!srv) return;
    void* raw = alloc(0x2C);                 // 0x009133DA
    Msg*  m   = raw ? MsgCtor(raw) : 0;      // 0x009134D6
    if (m) m->AddRef();
    m->vt+0x14(payload);                     // set payload
    srv->vt+0x10(m, 0);                      // enqueue
    m->Release();
}
```
**CALLERS** `0x007B0F7A` in `sub_7B0F60`; `0x007B1920` in `sub_7B1900`.

<a name="sub_7abb60"></a>
### `sub_7ABB60` (0x7ABB60..0x7ABB80, 32 bytes) — RegionScreen `GZOnMouseExit`

At `0x00AB9498` = vtable `0xAB9260 + 0x238`. `__thiscall(uint32)` → bool, `ret 4`.
```c
bool RegionScreen::GZOnMouseExit(this, uint32 d) {
    if (!this->0x1A0) sub_7B5DB0(this->0xE0);   // clear the view's hover highlight
    return true;
}
```

<a name="sub_7abb80"></a>
### `sub_7ABB80` (0x7ABB80..0x7ABCD0, 336 bytes) — default tile art for one item

**PURPOSE** Give a region item the *placeholder* pair of bitmaps for its size class.
Directly relevant to how tiles are SIZED, because it is what fills `[item+0x1C]`,
whose rect `sub_7AE510` then copies verbatim into the composite.

**CONVENTION** `__thiscall(Item* it)`, `ret 4`. Void.
**CALLERS** `0x007B00F2` in `sub_7AFAA0`; `0x007B15FE` and `0x007B17EE` in `sub_7B13C0`.

```c
void RegionScreen::AssignDefaultTileArt(this, Item* it)
{
    Region* rgn = [0x00B43C94]->vt+0x88();
    Obj*    o   = rgn->vt+0x20();
    int     mode= o->vt+0x48();               // 0, 1, or >=2

    uint32 sz  = *(uint8*)(it + 0x18);        // SIZE CLASS  (0 / 1 / 2)
    void** rgbSrc, **maskSrc;
    if (mode == 1) { rgbSrc = (void**)(this + sz*8 + 0x13C);
                     maskSrc= (void**)(this + sz*8 + 0x140); }
    else           { rgbSrc = (void**)(this + sz*8 + 0x124);
                     maskSrc= (void**)(this + sz*8 + 0x128); }

    AssignWithRef(&it->0x1C, *rgbSrc);        // AddRef new / Release old
    AssignWithRef(&it->0x20, *maskSrc);

    if (it->0x24) { void* p = it->0x24; it->0x24 = 0; p->Release(); }
    if (it->0x28) { void* p = it->0x28; it->0x28 = 0; p->Release(); }
}
```

**Refinement of GROUND TRUTH.** `RegionScreen+0x124` is not a flat list of default
tile images: it is **two tables of PAIRS, stride 8, three size classes each**:

| table | base | layout |
|---|---|---|
| A (default) | `+0x124` | `[sz]` → `{ +0x124+8·sz = RGB bitmap, +0x128+8·sz = ALPHA MASK }` |
| B (mode 1) | `+0x13C` | `[sz]` → `{ +0x13C+8·sz = RGB bitmap, +0x140+8·sz = ALPHA MASK }` |

(`0x13C − 0x124 = 0x18 = 3 × 8`, so table A holds exactly 3 entries — one per size class.)

**And `[item+0x20]` is the ALPHA-MASK bitmap** — a fact GROUND TRUTH did not have.
It is the second argument of `sub_7ABCD0` (see next), which explains where the
"packed uint16 alpha run-list" at `[item+0x38..]` is ultimately headed.
`[item+0x24]` and `[item+0x28]` are two further refcounted objects, always dropped here.

<a name="sub_7abcd0"></a>
### `sub_7ABCD0` (0x7ABCD0..0x7ABDF0, 288 bytes) — per-pixel alpha stamp

**PURPOSE** Copy an alpha channel from one buffer into another, pixel by pixel.
**CALLED TWICE FROM `sub_7AE510`** (`0x007AE726`, `0x007AE76F`) — the composite creator.

**CONVENTION** `__cdecl(Buffer* dst, Buffer* mask)` — plain `ret`, caller cleans.
Note: The prologue reads a third slot but never uses it, so the declared arity may be 3.

```c
void StampAlpha(Buffer* dst, Buffer* mask)
{
    if (!dst->vt+0x18(0x8080)) return;                 // lock dst
    if (!mask->vt+0x18(0x800)) { dst->vt+0x1C(0x8080); return; }   // lock mask

    int32* ra = mask->vt+0x30();     // GetRect  <-- BOTH calls are on `mask`
    int32* rb = mask->vt+0x30();     //             (bytes at 0x7ABD06 below)
    int W = min(rb[2]-rb[0], ra[2]-ra[0]);
    int H = min(rb[3]-rb[1], ra[3]-ra[1]);

    for (int y = 0; y < H; ++y)
      for (int x = 0; x < W; ++x) {
          uint32 rgb = dst ->vt+0x54(x, y) & 0x00FFFFFF;   // GetPixel
          uint32 a   = mask->vt+0x54(x, y);
          dst->vt+0x58(x, y, rgb + (a << 24));             // SetPixel
      }

    mask->vt+0x1C(0x800);
    dst ->vt+0x1C(0x8080);
}
```

**Note: MEASURED ODDITY, load-bearing.** Raw bytes at `0x007ABD06`:

```
007ABD06  8B 45 00        mov  eax,[ebp]        ; ebp = arg1 (mask)
007ABD09  56 57           push esi / push edi
007ABD0B  8B CD           mov  ecx,ebp          ; this = mask
007ABD0D  FF 50 30        call [eax+0x30]       ; mask->GetRect()
007ABD10  8B 55 00        mov  edx,[ebp]        ; ebp again
007ABD13  8B CD           mov  ecx,ebp          ; this = mask AGAIN
007ABD15  8B F0           mov  esi,eax
007ABD17  FF 52 30        call [edx+0x30]       ; mask->GetRect()
```

**Both `GetRect` calls are on the MASK (`arg1`); the destination's rect is never
consulted.** So the `min()` pair is `min(w,w)`/`min(h,h)` and the loop is bounded
purely by the mask. If a mask is ever larger than the composite it is stamping,
this walks off the composite. Combined with GROUND TRUTH's "the composite is sized
verbatim from the SOURCE bitmap" (`sub_7AE510` @ `0x007AE6D9`/`0x007AE706`), this
means **the mask and the source bitmap must be the same size, and nothing in this
function enforces it.**

Buffer vtable slots used, consistent with GROUND TRUTH's `0x00AC1400` map
(`+0x24` GetWidth, `+0x28` GetHeight, `+0x30` GetRect):
`+0x18` lock/begin-access(flags), `+0x1C` unlock/end-access(flags),
`+0x54` **GetPixel(x,y)**, `+0x58` **SetPixel(x,y,argb)**. Note: Lock/unlock names are a guess;
flags `0x8080` (dst, read+write) and `0x800` (mask, read-only) are exact.

<a name="sub_7abdf0"></a>
### `sub_7ABDF0` (0x7ABDF0..0x7ABF10, 288 bytes) — select a region view mode

**CONVENTION** `__thiscall(int32 mode)`, `ret 4`. Void. `mode` may be −1 ("none").
**CALLERS** `0x007ACBD8` in `sub_7ACAD0`; `0x007AFBA9`, `0x007AFBC1`, `0x007AFC26` in `sub_7AFAA0`.

```c
void RegionScreen::SetViewMode(this, int32 mode)
{
    cIGZWin* host = this->GetChildWindowFromID(0x09EBE9EE);   // vt+0x88

    if (mode >= 0 && this->(0xEC + mode*4) && this->(0xEC+mode*4)->IsVisible()) {
        // already showing: just re-show the pair and bail
        this->(0xEC + mode*4)->vt+0x118();
        if (this->(0xF8 + mode*4)) this->(0xF8 + mode*4)->vt+0x118();
    } else {
        for (int i = 0; i < 3; ++i) {
            if (this->(0xEC + i*4)) this->(0xEC + i*4)->SetFlag(1 /*Visible*/, i == mode);
            if (this->(0xF8 + i*4)) {
                if (i == mode) { this->(0xF8+i*4)->vt+0x78(host, 1);   // MoveRelativeTo
                                 this->(0xF8+i*4)->vt+0x114(); }       // ShowWindow
                else           { this->(0xF8+i*4)->vt+0x118(); }       // HideWindow
            }
        }
    }

    for (uint32 i = 0; i < 3; ++i) {
        void* btn = 0;
        if (this->GetChildAsRecursive(((uint32*)0x00AB91AC)[i], 0x8810, &btn))  // vt+0x94
            btn->vt+0x24(i == mode);            // set the toggle state
        if (btn) btn->Release();
    }
}
```

**FIELDS** `+0xEC/+0xF0/+0xF4` = three mode PANELS; `+0xF8/+0xFC/+0x100` = three mode
sub-windows. **Constant table `0x00AB91AC`** = `{0x09EBF2BD, 0x09EBF2C8, 0x09EBF2C3}`
(the three toggle-button ids), riid `0x8810`. `0x09EBF2BD` (80×60 GZWinBtn) and
`0x09EBF2C3` (60×46 GZWinBtn) are declared in our extracted script
`T-00000000_G-96a006b0_I-aa920991.ui` (root 1154×51) — the region toolbar.
Host container id `0x09EBE9EE`.
Note: `vt+0x118`/`vt+0x114` are Hide/Show in one order or the other; I did not disambiguate.

<a name="sub_7abf10"></a>
### `sub_7ABF10` (0x7ABF10..0x7AC110, 512 bytes) — load the region-screen tuning exemplar

**PURPOSE** Read 13 tuning properties out of one exemplar and scatter them across the
region screen, the scroll window and three globals. **Everything reachable from here
is data-driven and can be changed without a code patch.**

**CONVENTION** `__thiscall()`, `ret`. Void.
**CALLERS** one site, `0x007B1FAD` in `sub_7B1900`.

```c
void RegionScreen::LoadTuning(this)
{
    AutoRef res;
    if (![0x00B43CA8]->vt+0x0C(&key{T=0x6534284A, G=0x690F693F, I=0xAA383BFE},
                               0xA52160F5, &res, 0, 0)) return;
    Props* p = res->vt+0x1C();

    if (this->0x174) {                                   // the scroll window
        GetU32  (p, 0xCA383CA4, &this->0x174->0x110);    // dead-zone radius (default 10)
        GetU32  (p, 0xCA383CA3, &this->0x174->0x114);    // max drag radius  (default 32)
        GetFloat(p, 0xCA383CA7, &this->0x174->0x11C);    // speed-ramp divisor (default 3.0)
    }
    GetInt  (p, 0xCA383CA5, &this->0x198);               // *** LAYOUT X MARGIN ***
    GetInt  (p, 0xCA383CA6, &this->0x19C);               // *** LAYOUT Y MARGIN ***
    [0x00B4E1CC] = 1;
    GetU32  (p, 0xCA383CA8, (void*)0x00B4E1C8);
    GetU32  (p, 0xCA383CA9, (void*)0x00B4E1C4);
    GetU32  (p, 0xCA383CAA, (void*)0x00B4E1C0);
    GetU32  (p, 0xCA383CAB, &this->0x1B0);
    GetU32  (p, 0xCA383CAC, &this->0x1B4);
    GetBool (p, 0xCA383CAD, &this->0x1A1);   [0x00B217B0] = this->0x1A1;
    GetBool (p, 0xCA383CAE, &this->0x1A2);   [0x00B217B4] = this->0x1A2;
    GetFloat(p, 0xCA383CAF, &this->0x1F0);
    GetFloat(p, 0xCA383CB0, &this->0x1EC);

    void* v = p->vt+0x24(0xCA383CB1);        // a variant / array
    if (v && this->0xE4) {
        v->vt+0x14(); v->vt+0x17C();
        sub_7A98C0(this->0xE4, u32-at-v, u32-at-v+1);
    }
    if (this->0xE0)  { this->0xE0->0xF8 = ...; this->0xE0->0xFC = ...; }
    res->Release();
}
```

Property-reader helpers (Note: names inferred from arg shape, all `__cdecl(props, id, out)`):
`0x005FD450` int, `0x005FD480` u32/float, `0x005FD3C0` bool/byte, `0x005FD4F0` float pair.

**This is the single best place to look for #131.** `+0x198`/`+0x19C` are the only
tunable terms in `sub_7AB7C0`'s size law; the 128×64 basis itself is hard `.data`
(`0xB0DBA4..0xB0DBB0`).

<a name="sub_7ac110"></a>
### `sub_7AC110` (0x7AC110..0x7AC1A0, 144 bytes) — reset the current region selection

`__thiscall()`, `ret`. Void. Six call sites in `sub_7ACAD0`, `sub_7AFAA0` (×4), `sub_7B0470`.

```c
void RegionScreen::ClearSelection(this)
{
    View* v = this->0xE0;
    sub_7B2430(v, 1);
    switch (this->0x1A8) {
      case 0: sub_7B2410(v, 0, 1); sub_7B5E20(v, 0, 0); sub_7B30B0(v, 0, 1); break;
      case 1: sub_7B2410(v, 1, 0); sub_7B5E20(v, 0, 0); sub_7B30B0(v, 1, 1); break;
      default: break;                              // >=2: nothing
    }
    this->0x1A0 = (byte)0;                         // un-suppress hover
    sub_7B5DB0(this->0xE0);                        // tail jmp
}
```
`+0x1A8` is a mode selector distinct from the `sub_7ABDF0` one.

<a name="sub_7ac1a0"></a>
### `sub_7AC1A0` (0x7AC1A0..0x7AC270, 208 bytes) — drive the camera from the pan

**PURPOSE** Converts window centre + accumulated pan into a camera eye/target pair.
This is where `+0x178`/`+0x17C` (fed by the scroll messages) actually move the view.

`__thiscall()`, `ret`. Void.
**CALLERS** `0x007ACA01` in `sub_7AC830`; `0x007AD0F3` in `sub_7ACC90`.

```c
void RegionScreen::UpdateCamera(this)
{
    Proj* P = this->0x168->vt+0x20();          // scene (+0x168) -> projection/basis

    float ty = ((float)this->GetH() * 0.5f + this->0x17C) * P->0x150;   // 0x150 = units/pixel
    float uy0 = ty * P->0x6C, uy1 = ty * P->0x70, uy2 = ty * P->0x74;   // "up" basis row

    float tx = ((float)this->GetW() * 0.5f + this->0x178) * P->0x150;
    float rx0 = tx * P->0x60, rx1 = tx * P->0x64, rx2 = tx * P->0x68;   // "right" basis row

    float out[6] = { rx0, rx1, rx2,                     // point
                     rx0 - uy0, rx1 - uy1, rx2 - uy2 }; // point - up   (Note: exact pairing
                                                        //  of the three subtractions is
                                                        //  by stack slot, see below)
    sub_7CD810(this->0x164 /*cSC4CameraControl*/, out);
}
```
Note: The three `fsub`s at `0x7AC237/0x7AC243/0x7AC24F` pair `[esp+0x20..0x24]` against
`[esp+0x10..0x18]`; I am confident about the inputs (`+0x60..+0x68` and `+0x6C..+0x74`
scaled by `+0x150`) and about `this->0x164` being the camera, less so about the exact
component order in the 6-float block.

**FIELDS** `+0x164` camera, `+0x168` scene, `+0x178`/`+0x17C` pan accumulators.
Confirms GROUND TRUTH `+0x164` camera / `+0x168` scene.

<a name="sub_7ac270"></a>
### `sub_7AC270` (0x7AC270..0x7AC2D0, 96 bytes) — remember the region, forget the pan

`__thiscall()`, `ret`. Void. 4 call sites (`sub_7AF720`, `sub_7AFAA0` ×3).

```c
void RegionScreen::SaveRegionAndClearPan(this)
{
    App* app = [0x00B43C94];
    Obj* o   = app->vt+0x88()->vt+0x20()->vt+0x0C();       // region -> ... -> name holder
    char* pref = (char*)app->vt+0x98() + 0xEBC;            // GetPreferences() + 0xEBC
    strncpy(pref, o->vt+0x14(), 0x40);                     // 0x009F0FF0
    *(int*)(pref + 0x40) = 0x80000000;                     // "no saved pan"
    *(int*)(pref + 0x44) = 0x80000000;
    app->vt+0x44();                                        // SavePreferences()  (tail)
}
```

<a name="sub_7ac2d0"></a>
### `sub_7AC2D0` (0x7AC2D0..0x7AC380, 176 bytes) — persist the current pan

`__thiscall()`, `ret`. Void. 5 call sites (`sub_7ADC20`, `sub_7AF720`, `sub_7AFAA0` ×3).

```c
void RegionScreen::SavePan(this)
{
    App* app = [0x00B43C94];
    app->vt+0x88()->vt+0x20()->vt+0x0C();        // (side-effect only here)
    char* pref = (char*)app->vt+0x98() + 0xEBC;
    float cy = (float)this->GetH() * 0.5f + this->0x17C;
    float cx = (float)this->GetW() * 0.5f + this->0x178;
    *(int*)(pref + 0x40) = (int)(cx * 256.0f);   // [0xA9422C] = 256.0
    *(int*)(pref + 0x44) = (int)(cy * 256.0f);
    app->vt+0x44();                              // SavePreferences()  (tail)
}
```
So the saved pan is in the **same 1/256 fixed point** as the scroll messages, and
`0x80000000` is the "unset" sentinel written by `sub_7AC270`.

<a name="sub_7ac380"></a>
### `sub_7AC380` (0x7AC380..0x7AC490, 272 bytes) — RegionScreen teardown

`__thiscall()`, `ret`. Void. **CALLERS** one site, `0x007B10B3` in `sub_7B0F60`.

```c
void RegionScreen::Teardown(this)
{
    [0x00B43D1C] = 0;
    Shutdown+Release(this->0x15C);              // vt+0x10 then Release
    [0x00B43DDC] = [0x00B43DD8] = [0x00B43DD0] = 0;
    Shutdown+Release(this->0x168);              // the SCENE            vt+0x10
    sub_7CB970(this->0x164); Release(this->0x164);   // the CAMERA
    sub_648F00(this->0x160); Release(this->0x160);   // the RENDERER  <-- see note
    [0x00B43CF8] = 0;
    Shutdown+Release(this->0x16C);              // the TERRAIN GRID
    Shutdown+Release(this->0x158);              // the SERVICE          (tail)
}
```

**Confirms GROUND TRUTH** for `+0x158` service, `+0x160` renderer, `+0x164` camera,
`+0x168` scene, `+0x16C` terrain grid ↔ `[0xB43CF8]`. New: `+0x15C` is a sixth
shutdown-able object, and `[0xB43DD0]` (the thing class-`0xAB8F50` latches in `Init`)
is cleared here too.

<a name="sub_7ac490"></a>
### `sub_7AC490` (0x7AC490..0x7AC4D0, 64 bytes) — heapify a run of draw-order records

`__cdecl(Rec* first, Rec* last, ???)`, plain `ret`.
**CALLERS** one site, `0x007ADF7C` in `sub_7ADF40`.

```c
void MakeHeap(Rec* first, Rec* last, X extra) {
    for (Rec* p = first; p != last; ++p)        // stride 0x0C
        sub_7AA9C0(p, /*by-value copy of *p (3 dwords)*/, extra);
}
```
Element size is **0x0C bytes = 3 dwords** — this is *not* the 0x80-byte item array.

<a name="sub_7ac4d0"></a>
### `sub_7AC4D0` (0x7AC4D0..0x7AC5C0, 240 bytes) — `_Adjust_heap` with the isometric key

**PURPOSE** MSVC `std::_Adjust_heap` specialised for a 12-byte record. **The comparator
is the region view's painter's-order key.**

`__cdecl(Rec* base, int hole, int count, Rec value, Cmp cmp)`, plain `ret`.
**CALLERS** `0x007AD363`, `0x007AD393` in `sub_7AD310`; `0x007AD9D7` in `sub_7AD960`;
`0x007ADF06` in `sub_7ADE50`.

```c
struct Rec { int32 d0; int32 d1; int32 d2; };   // 0x0C bytes

// key(r) = r.d0 + r.d1 + (1 << r.d2)
for (int child = 2*hole + 2; child < count; child = 2*hole + 2) {
    Rec& A = base[child];      // right child
    Rec& B = base[child - 1];  // left child
    int s = (1 << A.d2) + A.d1 + A.d0
          - (1 << B.d2) - B.d1 - B.d0;
    if (s < 0 || (s == 0 && A.d0 < B.d0)) --child;   // 0x7AC530 js / 0x7AC534 jne / 0x7AC538 jge
    base[hole] = base[child];
    hole = child;
}
if (child == count) { base[hole] = base[count-1]; hole = count-1; }
sub_7AAA40(base, hole, first, value, cmp);
```

`(1 << d2)` is emitted literally as `mov eax,1; mov cl,[rec+8]; shl eax,cl`
(`0x7AC504`..`0x7AC50C` and `0x7AC50E`..`0x7AC516`). So **`d2` is a log2 span** —
consistent with SC4's small/medium/large city tiles — and the sort key
`x + y + span` is exactly the far-to-near ordering for a 2:1 isometric grid.
Ties break on `d0`.

<a name="sub_7ac5c0"></a>
### `sub_7AC5C0` (0x7AC5C0..0x7AC620, 96 bytes) — scroll-win scalar-deleting dtor

At `0x00AB8F20` = vtable `0xAB8CD0 + 0x250`. `__thiscall(uint8 flags)`, `ret 4`, returns `this`.

```c
void* ScrollWin::`scalar deleting destructor'(this, uint8 flags)
{
    *(void**)this = 0x00AB8CD0;
    if (this->GetFlag(0x4000)) {                     // 0x0099BC31 = GetFlag(0x4000)
        if (this->0x10C) { this->0x10C->Release(); this->0x10C = 0; }
        cGZWin::Shutdown(this);                      // 0x0099D2FE
    }
    TimerDtor(this + 0x120);                         // 0x00A6D837
    cGZWin::~cGZWin(this);                           // 0x0099E1A2
    if (flags & 1) operator delete(this);
    return this;
}
```
Note: Flag `0x4000` is not in the gzcom-dll `tWinFlag` list; from context it is an
"initialised / created" bit.

<a name="sub_7ac620"></a>
### `sub_7AC620` (0x7AC620..0x7AC7D0, 432 bytes) — create the scroll anchor marker

**PURPOSE** On right-button-down, drop the little anchor graphic at the press point
and remember it as the scroll origin.

**CONVENTION** `__thiscall(int x, int y)`, `ret 8`. Void.
**CALLERS** one site, `0x007AD3F2` in `sub_7AD3B0` (= `ScrollWin::GZOnMouseDownR`).

```c
void ScrollWin::DropAnchorMarker(this, int x, int y)
{
    this->0xDC  = x;                      // anchor
    this->0xE0  = y;
    this->0x109 = (byte)1;                // armed

    if (!this->0x10C) {
        AutoRes r(T=0x856DDBAC, G=0x46A006B0, I=0x094AC89A, 1, 0);   // 0x00602B70
        this->0x10C = r.ptr;
        if (this->0x10C) {
            this->0x10C->AddRef();
            uint32 c = this->0x10C->vt+0x78(0xFF, 0, 0xFF);   // make colour (255,0,255)
            this->0x10C->vt+0x5C(c);                          //  = magenta key
        }
        r.~AutoRes();                                          // 0x00602BE0
    }
    if (!this->0x10C) return;

    int32* rc = this->0x10C->vt+0x30();          // GetRect of the marker art
    int l = rc[0], t = rc[1], rr = rc[2], b = rc[3];
    int ox = -((rr - l) / 2), oy = -((b - t) / 2);
    l += ox; rr += ox; t += oy; b += oy;         // centre the art on (0,0)
    l += x;  rr += x;  t += y;  b += y;          // then on the press point

    Factory* f = GetRegionWinFactory();          // 0x00913C72, caches [0xB628C4]
    void* w = f->vt+0x3C(0x48E945B4, this->0x10C, 1);   // make a window from the bitmap
    if (!w) return;
    cIGZWin* win = w->vt+0x0C();

    win->SetArea(l, t, rr, b);                   // vt+0xDC
    win->SetFlag(2,        false);               // vt+0x110  Enabled  OFF
    win->SetFlag(0x200000, true);                //           IgnoreMouse ON
    win->SetFlag(4,        true);                //           AlphaBlend  ON
    win->ShowWindow();                           // vt+0x114

    if (this->ChildAdd(win))  this->vt+0x68(win);              // ChildToFront
    else                      this->GetWindowManager()->DestroyWindow(win);
    w->Release();
}
```

**The marker art is TGI `{0x856DDBAC, 0x46A006B0, 0x094AC89A}`** — group `0x46A006B0`
is the standard SC4 UI-art group, so this is an ordinary overridable bitmap.
The window is **centred on the cursor and sized verbatim from the bitmap's rect** —
i.e. it will be exactly 1× no matter the UI scale tier, and there is no code path
that scales it. That, plus `sub_7AAF20`'s pixel radii (10 / 32, both exemplar-driven
via `sub_7ABF10`), is the complete story of the anchor's geometry.

---

## Corrections to GROUND TRUTH (bytes win)

1. **`cSC4WinRegionView`'s no-op paint is at vtable slot `+0x160`, not `+0x88`.**
   `0x00AB9658 + 0x160 = 0x00AB97B8`, and `[0x00AB97B8] = 0x00648F00`. By contrast
   `0x00AB9658 + 0x88 = 0x00AB96E0`, and `[0x00AB96E0] = 0x0099DE74` — the ordinary
   inherited `cGZWin::GetChildWindowFromID`. Slot `+0x160` is **GZPaint** by my measured
   slot map, so the *conclusion* ("the view paints nothing") survives; the slot number
   in the brief does not.

2. **`0x00648F00` (`B0 01 C3`) is a shared engine stub, not a view-specific fact.**
   A byte scan of the image finds **302** little-endian references to `0x00648F00`.
   It is used elsewhere in this very module as the *renderer's* shutdown call
   (`sub_7AC380` at `0x007AC414`, on `RegionScreen+0x160`). Treat "slot X is 648F00"
   as "slot X is defaulted", never as evidence about a particular class.

3. **`+0x124` is not one table of default tile images — it is two tables of PAIRS.**
   `sub_7ABB80` indexes `this + sizeClass*8 + 0x124` **and** `+0x128` (a second pointer
   4 bytes later), and a parallel pair at `+0x13C`/`+0x140` chosen when the region mode
   is 1. Three size classes each (`0x13C − 0x124 = 3×8`).

4. **`[item+0x20]` is the item's ALPHA-MASK bitmap** (GROUND TRUTH lists `+0x1C` source
   and `+0x2C` composite but not `+0x20`). It is assigned alongside `+0x1C` in
   `sub_7ABB80` and is the second argument to the alpha stamp `sub_7ABCD0`.
   `[item+0x24]` and `[item+0x28]` are two further refcounted slots, released there.

5. **The isometric basis also yields an exact 64.0 in Y.** GROUND TRUTH records
   `90.51 + 37.49 = 128.0`. `sub_7AB7C0` uses the other two the same way and
   `18.75 + 45.25 = 64.0` — one region cell is exactly **128 × 64** screen px.

6. **funcs.json is missing two function starts in this range:** `0x007AAD30`
   (grid scalar-deleting dtor, inside `sub_7AACE0`'s span) and `0x007AB600`
   (dtor of the `0xAB8CB8`/`0xAB8CA0` MI pair, inside `sub_7AB5E0`'s span). Any pass
   that iterates funcs.json will silently skip both.

7. **`0x48E945B4` is not exclusive to the city view.** Our `UiSpike.cpp` calls it the
   "EDGE bubble / U-Drive-It marker"; `sub_7AC620` creates a window with that same id
   in the region screen's scroll window, and `sub_7AAEC0` destroys it. Any id-keyed
   rule on `0x48E945B4` fires in both screens.

---

## Things I could NOT determine

* Which concrete class vtable `0x00AB8CD0` and vtable `0x00AB8F50` correspond to by
  name — neither appears in the `0x00B05000..0x00B0B000` clsid/name registry via any
  path I could follow from this slice. I call them "the scroll window" and
  "class-`0xAB8F50`" from behaviour only.
* Whether `[0x00B43C94]->vt+0x88` is `cISC4App::GetRegion` or `GetNation`. Anchoring
  the header arithmetic on the two calls I *did* prove (`vt+0x44` = SavePreferences,
  `vt+0x98` = GetPreferences, both from `sub_7AC270`/`sub_7AC2D0` behaviour) puts
  `GetNation` at `+0x88` and `GetRegion` at `+0x8C`. The semantics (bounding rect in
  cells, per-city lookup) say region. One of the two community headers is off by one;
  I did not resolve which.
* The exact component order of the 6-float block `sub_7AC1A0` hands to `sub_7CD810`.
* Names for `0x005FD3C0` / `0x005FD450` / `0x005FD480` / `0x005FD4F0` (property readers)
  and for buffer slots `+0x18`/`+0x1C` (lock/unlock).
* `cGZWin+0x6C`, used by `sub_7AB590` as a begin/end draw pair.
* The identity of `0x0073283C` (pushed as a GZIID in `sub_7AB130`, but the value
  happens to fall inside `.text`).
