# Region-screen module — SLICE 1 of 8 — `0x007A9240 .. 0x007AABB0`

Decompiled 2026-08-04 from `C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe`
(1.1.641, image base `0x400000`, `fileOffset = VA - 0x400000`).

Function list taken from `tools\uimap\funcs.json` `starts[]` in `[0x7A9240, 0x7AABB0]` — **56 entries**.
Three further *real* functions live inside those spans and are **absent from funcs.json**
(`0x007A9300`, `0x007AA0E0`, `0x007AAB10`); they are documented here too (59 total).

---

## What is actually in this slice

The slice is **not** region-tile code. It is three unrelated classes that happen to be
linked into this address range, plus the region quadtree's sort primitives and the
region tile-art **resampling kernel machinery**:

| Range | Owner |
|---|---|
| `0x7A9240 – 0x7A9770` | **`cSC4WinRCI`** (clsid `0xC7A0E17E`) — the R/C/I demand indicator. Factory `0x466170`, ctor `0x7A9770`, primary vt `0xAB8884`, cIGZWin vt `0xAB8628`, cIGZMessageTarget2 vt `0xAB8614`. Object size **0x134**. |
| `0x7A9880 – 0x7A9D60` (+ `0x7A9D60` draw) | **the region-screen CLOUD particle layer**, window id `0x6A0AF41D`. ctor `0x7A9AE0`, vt `0xAB88C0`, size **0x140**. Created by `cSC4WinRegionScreen::Init` (`sub_7B1900` @ `0x7B1EFF`) and stored at **`regionScreen+0xE4`**. |
| `0x7AA110`, `0x7AA860`, `0x7AA0E0`, `0x7AABB0`, `0x7AA6A0` | **tile-art resampling + centroid helpers** used by `sub_7AE160` and `sub_7AE510` (the composite creator). |
| `0x7AA2A0 – 0x7AA510` | **terrain-grid base class**, ctor `sub_7AACE0` (next slice), vt `0xAB8C00`, IID `0xAB953253`. This is the GROUND-TRUTH "terrain grid" at `regionScreen+0x16C` / global `[0xB43CF8]`. |
| `0x7AA5A0`, `0x7AA920`, `0x7AA9C0`, `0x7AAA40` | **region quadtree painter's-order comparator + sort/heap primitives** (`{x, y, level}` 0x0C-byte records). |
| `0x7AA600`, `0x7AA640` | **`cSC4WinRegionScreen` vt+0x234 and vt+0x00** (they live here because the compiler emitted them here). |
| `0x7AA520`, `0x7AA570` | Init / Shutdown of the class ctor'd at `0x7AAE1C` (vt `0xAB8CD0`, Draw `0x7AB130`). |
| `0x7AAB10` | recursive child-window walker (buttons + option groups). |

---

## Table of contents

| # | VA | Size | Purpose |
|---|---|---|---|
| 1 | [`sub_7A9240`](#sub_7a9240) | 128 | `cSC4WinRCI::QueryInterface` |
| 2 | [`sub_7A92C0`](#sub_7a92c0) | 16 | `cSC4WinRCI::SetFillColor` → `this+0x130` |
| 3 | [`sub_7A92D0`](#sub_7a92d0) | 16 | adjustor thunk (−4) → QI |
| 4 | [`sub_7A92E0`](#sub_7a92e0) | 16 | adjustor thunk (−4) → deleting dtor |
| 5 | [`sub_7A92F0`](#sub_7a92f0) | 80 | adjustor thunk (−0xDC) → QI; **contains `0x7A9300` = the real deleting dtor** |
| 5b | [`sub_7A9300`](#sub_7a9300) | 56 | `cSC4WinRCI::` scalar deleting destructor *(not in funcs.json)* |
| 6 | [`sub_7A9340`](#sub_7a9340) | 80 | `cSC4WinRCI::Init` (cIGZWin vt+0x10) |
| 7 | [`sub_7A9390`](#sub_7a9390) | 80 | `cSC4WinRCI::Shutdown` (cIGZWin vt+0x14) |
| 8 | [`sub_7A93E0`](#sub_7a93e0) | 288 | `cSC4WinRCI::RecomputeDemand` — the value fetch |
| 9 | [`sub_7A9500`](#sub_7a9500) | 624 | **`cSC4WinRCI::Draw`** (cIGZWin vt+0x160) — log-scaled bar |
| 10 | [`sub_7A9770`](#sub_7a9770) | 96 | `cSC4WinRCI::cSC4WinRCI` |
| 11 | [`sub_7A97D0`](#sub_7a97d0) | 64 | `cSC4WinRCI::SetSources(uint32* ids, int n)` |
| 12 | [`sub_7A9810`](#sub_7a9810) | 112 | `cSC4WinRCI::DoMessage` (MT2 vt+0x0C) |
| 13 | [`sub_7A9880`](#sub_7a9880) | 32 | clouds: `Shutdown` (vt+0x14) |
| 14 | [`sub_7A98A0`](#sub_7a98a0) | 32 | clouds: `SetPan(POINT*)` → `+0xF0/+0xF4` |
| 15 | [`sub_7A98C0`](#sub_7a98c0) | 32 | clouds: `SetAlphaRange(u8 lo, u8 hi)` → `+0x110/+0x111` |
| 16 | [`sub_7A98E0`](#sub_7a98e0) | 160 | clouds: `MakeParticle(out24)` |
| 17 | [`sub_7A9980`](#sub_7a9980) | 64 | clouds: `SetWindDirection(float dx, float dy)` (normalises) |
| 18 | [`sub_7A99C0`](#sub_7a99c0) | 288 | **clouds: `Init`** — SetID, 4 texture bindings, size-to-root |
| 19 | [`sub_7A9AE0`](#sub_7a9ae0) | 176 | clouds: constructor |
| 20 | [`sub_7A9B90`](#sub_7a9b90) | 112 | clouds: destructor |
| 21 | [`sub_7A9C00`](#sub_7a9c00) | 32 | clouds: scalar deleting destructor (vt+0x250) |
| 22 | [`sub_7A9C20`](#sub_7a9c20) | 320 | **clouds: `SetBounds(l,t,r,b)` + repopulate** (area / 16384 particles) |
| 23 | [`sub_7A9D60`](#sub_7a9d60) | 944 | **clouds: `Draw`** (vt+0x160) — the emitter/integrator/blitter |
| 23b | [`sub_7AA0E0`](#sub_7aa0e0) | 35 | `double tentKernel(double x) = max(0, 1-|x|)` *(not in funcs.json)* |
| 24 | [`sub_7AA110`](#sub_7aa110) | 400 | **horizontal 2-tap 14-bit fixed-point ARGB resample** |
| 25 | [`sub_7AA2A0`](#sub_7aa2a0) | 64 | grid: `QueryInterface` (IID `0xAB953253`) |
| 26 | [`sub_7AA2E0`](#sub_7aa2e0) | 16 | grid: `[this+0x24] = 1` |
| 27 | [`sub_7AA2F0`](#sub_7aa2f0) | 16 | grid: `[this+0x24] = 0` |
| 28 | [`sub_7AA300`](#sub_7aa300) | 16 | grid: `return float [this+0x20]` (cell size = 64.0) |
| 29 | [`sub_7AA310`](#sub_7aa310) | 16 | **grid: `CellIndex(x,y) = y*stride + x`** |
| 30 | [`sub_7AA320`](#sub_7aa320) | 48 | **grid: `IndexToXY(idx, &x, &y)`** |
| 31 | [`sub_7AA350`](#sub_7aa350) | 96 | **grid: `InBounds(float wx, float wy)`** |
| 32 | [`sub_7AA3B0`](#sub_7aa3b0) | 16 | grid: `return float [this+0x0C]` (ret 4) |
| 33 | [`sub_7AA3C0`](#sub_7aa3c0) | 112 | grid: `FillRegion(rect, base, rowStep, colStep)` with `[this+0x0C]` |
| 34 | [`sub_7AA430`](#sub_7aa430) | 96 | grid: same, writing `0` |
| 35 | [`sub_7AA490`](#sub_7aa490) | 32 | grid: write `[this+0x0C]` to `out[0..3]` (ret 0xC) |
| 36 | [`sub_7AA4B0`](#sub_7aa4b0) | 16 | grid: `return float [this+0x0C]` (ret 8) — 4 slots |
| 37 | [`sub_7AA4C0`](#sub_7aa4c0) | 16 | grid: `return 0.0f` (ret 4) |
| 38 | [`sub_7AA4D0`](#sub_7aa4d0) | 16 | grid: `return float [this+0x0C]` (ret 0) |
| 39 | [`sub_7AA4E0`](#sub_7aa4e0) | 16 | grid: `return 0.0f` (ret 0) |
| 40 | [`sub_7AA4F0`](#sub_7aa4f0) | 16 | grid: `return 1023.0f` |
| 41 | [`sub_7AA500`](#sub_7aa500) | 16 | grid: `return float [this+0x10]` |
| 42 | [`sub_7AA510`](#sub_7aa510) | 16 | grid: `return 0.0f` (ret 8) — 3 slots |
| 43 | [`sub_7AA520`](#sub_7aa520) | 80 | `Init` of the vt-`0xAB8CD0` window |
| 44 | [`sub_7AA570`](#sub_7aa570) | 48 | `Shutdown` of the vt-`0xAB8CD0` window |
| 45 | [`sub_7AA5A0`](#sub_7aa5a0) | 96 | **quadtree painter's-order `less(a,b)`** on `{x,y,level}` |
| 46 | [`sub_7AA600`](#sub_7aa600) | 64 | `cSC4WinRegionScreen` vt+0x234 |
| 47 | [`sub_7AA640`](#sub_7aa640) | 96 | **`cSC4WinRegionScreen::QueryInterface`** (vt+0x00) |
| 48 | [`sub_7AA6A0`](#sub_7aa6a0) | 448 | **alpha-weighted centroid of a 16-bpp surface → item+0x68/+0x6C** |
| 49 | [`sub_7AA860`](#sub_7aa860) | 128 | **build a normalised filter kernel (sum = 16384)** |
| 50 | [`sub_7AA8E0`](#sub_7aa8e0) | 64 | `POINT::operator!=` |
| 51 | [`sub_7AA920`](#sub_7aa920) | 160 | median-of-3 pivot for the quadtree sort |
| 52 | [`sub_7AA9C0`](#sub_7aa9c0) | 128 | insertion-sort step over 0x0C-byte records |
| 53 | [`sub_7AAA40`](#sub_7aaa40) | 176 | heap sift-down over 0x0C-byte records |
| 54 | [`sub_7AAAF0`](#sub_7aaaf0) | 16 | adjustor thunk (−4) → `0x7AAD30` |
| 55 | [`sub_7AAB00`](#sub_7aab00) | 16 | adjustor thunk (−4) → `0x7AB600`; **contains `0x7AAB10`** |
| 55b | [`sub_7AAB10`](#sub_7aab10) | 146 | recursive Btn/OptGrp child walker *(not in funcs.json)* |
| 56 | [`sub_7AABB0`](#sub_7aabb0) | 304 | **vertical 2-tap 14-bit fixed-point ARGB resample** |

---

## 0. Shared facts established while decompiling this slice

### 0.1 `cIGZGDriver` vtable — the SDK header is off by 3 slots

`vendor\gzcom-dll\...\cIGZGDriver.h` lists only the class's own virtuals; the real vtable
has `cIGZUnknown`'s three first. **Real `vt+0xNN` == header entry `NN − 0x0C`.**
Proved by arity at four independent sites inside `sub_7A9D60`:

| real slot | header slot | signature | call site | pushes |
|---|---|---|---|---|
| `+0x0C` | `+0x00` | `DrawArrays(prim, first, count)` | `0x7AA0AC` | `4,0,1` → (1,0,4) |
| `+0x14` | `+0x08` | `InterleavedArrays(fmt, n, verts)` | `0x7A9F7D` | 3 args, fmt `0xA` |
| `+0x54` | `+0x48` | `BlendFunc(src, dst)` | `0x7A9E4A` | `5,4` → (4,5) |
| `+0xD4` | `+0xC8` | `TexStageMatrix(m, a, b, flags)` | `0x7A9E71` | 4 args |
| `+0x70/+0x74` | `+0x64/+0x68` | `TexEnv` / `TexParameter` (3 args) | `0x7AA09F`, `0x7AA085` | 3 args each |
| `+0xA4/+0xA8` → real `+0xB0/+0xB4` | `Enable`/`Disable` | 1 arg | `0x7A9E0C..0x7A9E3C` | 1 arg each |

Note: One mismatch remains: real `vt+0xE8` is called with **1** argument at `0x7AA075`
(header `+0xDC SetTexture(uint32, uint32)` wants 2). Either the header is wrong there or
the real `SetTexture` takes just the handle. Marked UNSURE.

### 0.2 `cGZWin` slots confirmed by bytes in this slice

| slot | target | meaning | evidence |
|---|---|---|---|
| `+0x28` | `0x0099BE2A` = `mov ecx,[ecx+4]; mov eax,[ecx]; jmp [eax+0x0C]` | forwards to **`cGZWin+0x04`** (the window manager) → returns the **root** window | used twice in `sub_7A99C0` then `SetArea(0,0,root->GetW(),root->GetH())` |
| `+0x80` | — | `EnumChildren(iid, callback)` | `sub_7AAB10` @ `0x7AAB89` passes `GZIID_cIGZWin` + itself |
| `+0xA4 / +0xA8` | — | `GetW` / `GetH` | `sub_7A99C0` @ `0x7A9A76 / 0x7A9A6B` |
| `+0xDC` | — | `SetArea(l,t,r,b)` | `sub_7A99C0` @ `0x7A9A85` |
| `+0xFC` | `0x0099BE66` = `mov eax,[ecx+0x10]; ret` | **GetID** | bytes |
| `+0x100` | `0x0099BE5C` = `mov eax,[esp+4]; mov [ecx+0x10],eax; ret 4` | **SetID** | `sub_7A99C0` @ `0x7A99E6` writes `0x6A0AF41D` |
| `+0x110` | `0x0099DB6B` | **SetFlag(uint32 flag, bool)** | called *non-virtually* from `sub_7A9AE0` @ `0x7A9B78/0x7A9B86` |
| `+0x160` | — | **Draw** | `sub_7A9500`, `sub_7A9D60`, `0x7AC830`, and GROUND TRUTH's "slot-88" (`88*4 = 0x160`) |
| `+0x170` | — | **repaint / invalidate** | `sub_7A9810` @ `0x7A986E`, invoked exactly when a demand value changed |
| `+0x250` | — | **scalar deleting destructor** | `0xAB8878` (RCI) and `0xAB8B10` (clouds) |

> Note: **Repo-doc correction:** `tools\research\SC4-UI-ENGINE.md` line 249 lists "`SetID +0xFC`".
> The bytes say `+0xFC` is the **getter** and `+0x100` is the setter. `Show +0x110` in the
> same line is really the generic `SetFlag(flag, bool)`.

### 0.3 Tile-buffer vtable `0x00AC1400` — four slots newly resolved

| slot | target | body | meaning |
|---|---|---|---|
| `+0x18` | `0x00826AA0` | `if(![ecx+0x3C]) return 0; if(flags & 0x8000) ++[ecx+0x30]; [ecx+0x44] \|= flags; ++(word)[ecx+0x38]; return 1;` | **Lock(uint32 flags)** |
| `+0x1C` | `0x00826490` | — | **Unlock(uint32 flags)** (called with `0x40`, `sub_7AA6A0` @ `0x7AA7CA`) |
| `+0x30` | `0x008268C0` | `lea eax,[ecx+0x14]; ret` | **GetRect** → pointer to the 4 dwords at `buf+0x14 .. +0x20` |
| `+0x88` | `0x008265C0` | `mov eax,[ecx+0x3C]; ret` | **GetBits** |
| `+0x8C` | `0x0068D1B0` | `mov eax,[ecx+0x40]; ret` | **GetRowPitch (bytes)** — `buf+0x40`, *not previously recorded* |

Consequences for the GROUND TRUTH head map:
* `+0x1C`/`+0x20` really are width/height — they are `rect[2]`/`rect[3]` of the `+0x14` rect.
* `+0x30` is **not** the constant 3; it is a counter `Lock()` bumps when the lock flags
  have bit 15 set. `+0x38`'s low 16 bits are the **lock count** (`inc word ptr`), and
  `+0x44` accumulates the OR of every lock's flags. The observed `+0x38 = 0x00040001`
  therefore reads as "lock depth 1, high half 4".
* `+0x40` = row pitch. Add it to the head map.

### 0.4 Constants referenced by this slice

| VA | type | value | used by |
|---|---|---|---|
| `0xAB7E10` | f32 | **128.0** | cloud sprite edge (`sub_7A98E0`, `sub_7A9C20`, `sub_7A9D60`) |
| `0xA80AB0` | f64 | 1.0 | RCI draw, `sub_7A98E0`, `sub_7AA0E0` |
| `0xA92D28` | f64 | 0.5 | RCI draw (rounding) |
| `0xAB3AD0` | f64 | 5.0 | cloud speed scale |
| `0xA81228` | f32 | 1.0 | `sub_7A9980` reciprocal |
| `0xA81054` | f32 | 0.0 | grid null getters, `sub_7AA350` |
| `0xA80990` | f64 | 0.0 | `sub_7AA0E0` out-of-support return |
| `0xAB8B20` | f64 | **6.103515625e-05 = 1/16384** | `sub_7A9C20` particle count = area/16384 |
| `0xAB8B28` | f64 | 0.003 | `sub_7A9D60` per-frame spawn probability |
| `0xAB8B80` | f32 | 1023.0 | grid `vt+0x60` |
| `0xA867A4` | f32 | 0.001 | `sub_7A9D60` ms→s |
| `0xACEC98` | f32 | (LCG scale) | RNG `0x91372E` |

> Note: Do **not** conflate `0xAB7E10 = 128.0` with GROUND TRUTH's "one region cell = 128.0 px".
> The latter is *derived* (`90.51 + 37.49`) from the isometric basis at `0xB0DBA4..0xB0DBB0`;
> `0xAB7E10` is a separate literal that this slice uses only as the cloud sprite size.

### 0.5 IIDs / CLSIDs seen

| id | name | source |
|---|---|---|
| `0x22BA0121` | `GZIID_cIGZWin` ("GZWin") | class-name registry `0xB1709C` |
| `0x452294AA` | `GZIID_cIGZMessageTarget2` | `GZCLSIDDefs.h:77` |
| `0xC6AE7085` | **`GZIID_cIGZWinMessageFilter`** | `cIGZWinMessageFilter.h:28` |
| `0xA1336CC0` | `GZIID_cIGZWinOptGrp` | `cIGZWinOptGrp.h:25` |
| `0x00008810` | `GZIID_cIGZWinBtn` | `cIGZWinBtn.h:32` |
| `0x1AC0E11A` / `0xFAC0E219` | `GZCLSID`/`GZIID_cIS3DTextureBindingFactory` | `cIS3DTextureBindingFactory.h:32-33` |
| `0x89E1574C` | `cSC4WinRCI`'s own IID | `sub_7A9240` (not in the name registry) |
| `0xAB953253` | terrain-grid IID | `sub_7AA2A0` (not in the name registry) |
| `0x426840A0` | message type `cSC4WinRCI` subscribes to (RCI demand changed) | `sub_7A9340/0x7A9390/0x7A9810` |
| `0x6A0AF41D` | window id of the cloud layer | `sub_7A99C0` @ `0x7A99E6` |
| `0x4A624656..0x4A624659` | the four cloud texture instance ids | `sub_7A99C0` @ `0x7A9A38` (`lea eax,[ebp+0x4A624656]`, `ebp` = 0..3) |
| `0xC2A676AC` | value stored at `+0xD8` of the vt-`0xAB8CD0` window | `sub_7AA520` @ `0x7AA53E` — Note: unidentified |

### 0.6 Helper functions used repeatedly

| VA | meaning | how established |
|---|---|---|
| `0x9EEF04` | `int ftol_round(st0)` | ubiquitous; always follows FPU math, result in `eax` |
| `0x9EFEB0` | `__alldiv` (64-bit signed divide) | 4 pushes, `edx:eax` in/out (`sub_7AA6A0`) |
| `0x5E55E0` / `0x5E5620` | `operator new` / `operator delete` | allocation sites |
| `0x90CF54` / `0x90CF63` | pooled `alloc(size)` / `free(p)` | list-node churn in `sub_7A9C20` |
| `0x99D938` / `0x99E1A2` | `cGZWin::cGZWin` / `~cGZWin` | both ctors/dtors in this slice |
| `0x99BC31` / `0x99BC3F` / `0x99C2C3` / `0x99D2FE` | `IsInited()` / `SetInited(b)` / `MarkInited()` / base `Shutdown()` | Init/Shutdown guard idiom |
| `0x8793EC` | `GZCOM()` | `sub_7A99C0`; result gets `vt+0x14 = GetClassObject(clsid,iid,out)` |
| `0x8090E0` | release/free a `cS3DTextureBinding*` | `sub_7A99C0`, `sub_7A9B90` |
| `0x4495C0` | `cRZAutoRefCount::~` | `sub_7A99C0` tail |
| `0x91372E` | **`float cRZRandom::Rand01()`** — LCG `state *= 0x278DDE6D`, `* [0xACEC98] + 0.5` | body read directly |
| `0x9136CA` | **`int cRZRandom::RandRange(lo, hi)`** = `lo + Rand(hi-lo)` | body read directly |
| `0x913A5C` | `cRZRandom::Seed(int)` | ctor call with `-1` |
| `0x88FEDF` / `0x890181` / `0x88FEFB` / `0x890198` / `0x89058F` / `0x8905C4` / `0xA6D837` | stopwatch at `clouds+0xD8`: ctor(4) / setmode(4) / `IsRunning` / `ElapsedMs` / `Restart` / `Start` / dtor | Note: names inferred from the `dt` computation in `sub_7A9D60` |
| `0x747FF0` | `list<sprite>::push(&sprite)` on `clouds+0x114` | `sub_7A9D60` @ `0x7A9FAF` |
| `0x5650A0` | destroy the `+0x114` list | `sub_7A9B90` |
| `0x910003` | memcpy-ish row copy (the "no filtering" path in `sub_7AE160`) | Note: inferred from the call site |

Globals:

| VA | contents | evidence |
|---|---|---|
| `[0xB43CCC]` | **`cIGZMessageServer2`** — `vt+0x14` AddNotification, `vt+0x18` RemoveNotification | `sub_7A9340`/`sub_7A9390`; already recorded in `SC4-UI-ENGINE.md:576` |
| `[0xB43CA0]` | **`cIGZGraphicSystem`** — `vt+0x0C` returns the `cIGZGDriver` | `sub_7A9D60` @ `0x7A9DF9` |
| `[0xB43D74]` | the **demand/statistics service** — `vt+0x18(uint32 id, 0x20000)` returns a value object with float getters at `vt+0x30/+0x38/+0x3C` | `sub_7A93E0`; Note: class not identified |

---

# Part A — `cSC4WinRCI` (`0x7A9240` – `0x7A9810`)

**Object layout** (size `0x134`, allocated by the factory at `0x466170` which returns
`obj+4`, i.e. callers hold the **cIGZWin** pointer):

| offset | field |
|---|---|
| `+0x000` | vptr `0xAB8884` — the `0x89E1574C` interface |
| `+0x004` | vptr `0xAB8628` — **`cIGZWin`** (the `cGZWin` base occupies `+0x04 .. +0xDB`) |
| `+0x0AC .. +0x0B8` | the window rect L,T,R,B (= `cIGZWin this+0xA8..0xB4`) |
| `+0x070` | (= `cIGZWin this+0x6C`) the fill helper used by `Draw` — Note: identity unknown |
| `+0x0DC` | vptr `0xAB8614` — **`cIGZMessageTarget2`** |
| `+0x0E0 .. +0x11F` | `uint32 sourceIds[16]` (no bounds check — see `sub_7A97D0`) |
| `+0x120` | `int sourceCount` |
| `+0x124` | `int accMin` — Σ `source->vt+0x3C()` (used as the **negative-side scale**) |
| `+0x128` | `int accMax` — Σ `source->vt+0x38()` (used as the **positive-side scale**) |
| `+0x12C` | `int value`  — Σ `source->vt+0x30()` (the **current demand**) |
| `+0x130` | `int fillColor` (set by `sub_7A92C0`, consumed by `Draw`) |

<a id="sub_7a9240"></a>
## `sub_7A9240`  (0x7A9240..0x7A92C0, 128 bytes)

**PURPOSE** `cSC4WinRCI::QueryInterface` — vt `0xAB8884` slot `+0x00`.
**CONVENTION** `__stdcall` method: `this` in `ECX`, `(uint32 iid, void** out)`, `ret 8`.

```c
bool QI(uint32 iid, void** out) {          // this == obj+0
    switch (iid) {
    case 0x00000001:                       // cIGZUnknown
    case 0x89E1574C: *out = this;              break;   // 0x7A92A6
    case 0x22BA0121: *out = (char*)this + 4;   break;   // cIGZWin,           0x7A925F
    case 0x452294AA: *out = (char*)this + 0xDC;break;   // cIGZMessageTarget2,0x7A9276
    default: return false;                              // 0x7A92A1
    }
    if (!this) *out = 0;                   // 0x7A9288 (the this==0 legs)
    this->vt[1]();                         // AddRef  (mov eax,[ecx]; call [eax+4])
    return true;
}
```
Constants compared: `0x452294AA` (`cmp eax, 0x452294AA` @ `0x7A9244`), `1` (`dec eax`),
`0x22BA0121` (`sub eax, 0x22BA0120` after the `dec`), `0x89E1574C` (`0x7A929A`).
**CALLERS** none direct — vtable only (`0xAB8884+0x00`; reached through the thunks
`sub_7A92D0`, `sub_7A92F0`).

<a id="sub_7a92c0"></a>
## `sub_7A92C0`  (0x7A92C0..0x7A92D0, 16 bytes)
`__stdcall`, vt `0xAB8884+0x10`. `this->[0x130] = arg1; ret 4`. The value `Draw` hands to
`m_fill->vt+0x54()` — i.e. **the bar colour / fill token**. **CALLERS** vtable only.

<a id="sub_7a92d0"></a>
## `sub_7A92D0`  (0x7A92D0..0x7A92E0, 16 bytes)
Adjustor thunk at vt `0xAB8628+0x00`: `sub ecx,4; jmp sub_7A9240`. (cIGZWin→primary.)

<a id="sub_7a92e0"></a>
## `sub_7A92E0`  (0x7A92E0..0x7A92F0, 16 bytes)
Adjustor thunk at vt `0xAB8628+0x250`: `sub ecx,4; jmp 0x7A9300` (deleting destructor).

<a id="sub_7a92f0"></a>
## `sub_7A92F0`  (0x7A92F0..0x7A9340, 80 bytes)
First 6 bytes only: adjustor thunk at vt `0xAB8614+0x00`:
`sub ecx,0xDC; jmp sub_7A9240`. The remaining 74 bytes are `sub_7A9300` below.

<a id="sub_7a9300"></a>
## `sub_7A9300`  (0x7A9300..0x7A9337, 56 bytes) — **absent from funcs.json**

**PURPOSE** `cSC4WinRCI::` scalar deleting destructor.
**CONVENTION** `__stdcall` method, `this` in `ECX`, `(int flags)`, `ret 4`.

```c
void* dtor(int flags) {
    this[0x000] = 0xAB8884;   // 0x7A9306
    this[0x004] = 0xAB8628;   // 0x7A930C
    this[0x0DC] = 0xAB8614;   // 0x7A9312
    cGZWin::~cGZWin( (char*)this + 4 );      // call 0x99E1A2, ecx = this+4
    if (flags & 1) operator delete(this);    // 0x5E5620
    return this;
}
```

<a id="sub_7a9340"></a>
## `sub_7A9340`  (0x7A9340..0x7A9390, 80 bytes)

**PURPOSE** `cSC4WinRCI::Init` — cIGZWin vt `+0x10`. **`this` = obj+4.**
**CONVENTION** `__thiscall`, no args, plain `ret`, returns `bool` in AL.

```c
bool Init() {
    if (IsInited())    return true;              // 0x99BC31
    MarkInited();                                // 0x99C2C3
    (void)sub_913C72();                          // lazy singleton guarded by [0xB628C4] -> 0x7B2480  (Note: unidentified)
    cIGZMessageServer2* ms = *(void**)0xB43CCC;
    if (ms) {
        void* target = (char*)this + 0xD8;       // == obj+0xDC, the MT2 subobject
        ms->vt[0x14](target, 0x426840A0);        // AddNotification
    }
    return true;
}
```
Note the odd `lea eax,[esi-4]; test eax,eax` at `0x7A9362` — a null-check on `obj+0`;
if it is 0 the code passes `NULL` as the target instead (`0x7A937E`).

<a id="sub_7a9390"></a>
## `sub_7A9390`  (0x7A9390..0x7A93E0, 80 bytes)

**PURPOSE** `cSC4WinRCI::Shutdown` — cIGZWin vt `+0x14`. `this` = obj+4.

```c
bool Shutdown() {
    if (!IsInited()) return true;
    cIGZMessageServer2* ms = *(void**)0xB43CCC;
    if (ms) ms->vt[0x18]((char*)this + 0xD8, 0x426840A0);   // RemoveNotification
    return cGZWin::Shutdown(this);                          // tail-jmp 0x99D2FE
}
```

<a id="sub_7a93e0"></a>
## `sub_7A93E0`  (0x7A93E0..0x7A9500, 288 bytes)

**PURPOSE** `cSC4WinRCI::RecomputeDemand` — re-reads the three numbers from the demand
service and reports whether any of them changed. **`this` = obj+0.**
**CONVENTION** `__thiscall`, no args, plain `ret`, `bool` in AL.

```c
bool Recompute() {
    void* svc = *(void**)0xB43D74;
    if (!svc) return false;                                  // 0x7A93F2

    int oldMin = this->[0x124], oldMax = this->[0x128], oldVal = this->[0x12C];
    int n      = this->[0x120];
    this->[0x124] = this->[0x128] = this->[0x12C] = 0;

    uint32* p = &this->[0xE0];
    for (int i = 0; i < n; ++i, ++p) {
        int id = *p;
        if (id <= 0) continue;                               // 0x7A944A  (signed jle!)
        void* o = svc->vt[0x18](id, 0x20000);                // 0x7A9458
        if (!o) continue;
        this->[0x124] += ftol(o->vt[0x3C]());                // 0x7A9465
        this->[0x128] += ftol(o->vt[0x38]());                // 0x7A947D
        this->[0x12C] += ftol(o->vt[0x30]());                // 0x7A9495
    }
    return !(oldMin==this->[0x124] && oldMax==this->[0x128] && oldVal==this->[0x12C]);
}
```
Note: `if (id <= 0) continue` is a **signed** test on a resource id — ids with bit 31 set are
silently skipped. Not exercised by the shipped `.UI` data (the RCI passes small ids).

**CALLERS** `sub_7A97D0` @ `0x7A97FC`; `sub_7A9810` @ `0x7A9859`.

<a id="sub_7a9500"></a>
## `sub_7A9500`  (0x7A9500..0x7A9770, 624 bytes)

**PURPOSE** **`cSC4WinRCI::Draw`** — cIGZWin vt `+0x160` (`0xAB8628 + 0x160 = 0xAB8788`).
Paints one filled rectangle whose *near edge* is a **logarithmically scaled** function of
the current demand. **`this` = obj+4** (so `this+0x120` == `obj+0x124`, etc.).
**CONVENTION** `__thiscall`, no stack args, plain `ret`, `bool` in AL.

```c
bool Draw() {
    m_fill->vt[0x54]( this->[0x12C] );          // obj+0x130, the colour   (0x7A9512)

    int L = this->[0xA8], T = this->[0xAC], R = this->[0xB0], B = this->[0xB4];
    int accMin = this->[0x120];   // obj+0x124
    int accMax = this->[0x124];   // obj+0x128
    int value  = this->[0x128];   // obj+0x12C
    int rect[4];

    if ((R - L) > (B - T)) {                    // WIDE bar            (0x7A9539)
        int half = (R - L) / 2;                 // sar 1, sign-corrected
        rect[1] = 0; rect[3] = B - T;
        if (value > 0) {
            rect[2] = half + 1;
            double t = log((float)value)/log((float)accMax) + (float)value/(float)accMax;
            rect[0] = ftol( (t*half + 1.0) * 0.5 + (half + 1) );
        } else if (value < 0) {
            rect[2] = half;
            double t = log((float)-value)/log((float)-accMin) + (float)value/(float)accMin;
            rect[0] = ftol( (double)half - (t*(double)half + 1.0) * 0.5 );
        } else return true;                     // value == 0 -> draw nothing (0x7A95C1 jge 0x7A975F)
    } else {                                    // TALL bar            (0x7A964B)
        int half = (B - T) / 2;
        rect[0] = 0; rect[2] = R - L;
        if (value > 0) {
            rect[3] = half;
            double t = log((float)value)/log((float)accMax) + (float)value/(float)accMax;
            rect[1] = ftol( (double)half - (t*(double)half + 1.0)*0.5 );
        } else if (value < 0) {
            rect[1] = half + 1;
            double t = log((float)-value)/log((float)-accMin) + (float)value/(float)accMin;
            rect[3] = ftol( (t*half + 1.0)*0.5 + (half + 1) );
        } else return true;                     // 0x7A96E3 jge 0x7A975F
    }
    m_fill->vt[0x8C](rect);                     // 0x7A963E / 0x7A9759
    return true;
}
```
Instruction notes that matter:
* natural logs are built as `fldln2; fxch; fyl2x` (= `ln2 · log2 x`), twice, then `fdivp`.
* the "+1.0 then ×0.5" is `fadd qword [0xA80AB0]` / `fmul qword [0xA92D28]` — a
  round-to-nearest-half, **not** a scale factor.
* `sar eax,1` after `cdq; sub eax,edx` is C's `/2` (truncate toward zero).
* **Zero pixel constants.** Everything derives from the window rect → the control is
  fully resolution-proportional. (Matches `SC4-UI-ENGINE.md:317`.)

**FIELDS** reads `this+0x6C` (fill helper), `this+0xA8/0xAC/0xB0/0xB4` (rect),
`this+0x120/0x124/0x128/0x12C`.
**VTABLE CALLS** `m_fill vt+0x54` (set colour), `m_fill vt+0x8C` (fill rect).
Note: `this+0x6C`'s class is **not** established — only that it has those two slots.
**CALLERS** vtable `0xAB8788` only.

<a id="sub_7a9770"></a>
## `sub_7A9770`  (0x7A9770..0x7A97D0, 96 bytes)

**PURPOSE** `cSC4WinRCI::cSC4WinRCI`. **CONVENTION** `__thiscall`, no args, returns `this`.

```c
cSC4WinRCI* ctor() {
    this[0x00]  = 0xAB889C;              // transient
    cGZWin::cGZWin((char*)this + 4);     // 0x99D938
    this[0xDC]  = 0xA81174;              // generic cIGZMessageTarget2 vtable
    this[0x04]  = 0xAB8628;
    this[0x120] = 0;  this[0xE0] = 0;  this[0xE4] = 0;  this[0x12C] = 0;
    this[0x00]  = 0xAB8884;
    this[0xDC]  = 0xAB8614;
    return this;
}
```
Note: Note `this[0x124]`, `this[0x128]` and `this[0x130]` are **never initialised** by the
ctor. `+0x124/+0x128` are zeroed on the first `Recompute`; `+0x130` (the colour) is
garbage until someone calls `sub_7A92C0`.

**CALLERS** the factory at `0x466170` (`new(0x134)`, then `return obj + 4`).
That factory is registered in the window-class table at `0x4663A7`.

<a id="sub_7a97d0"></a>
## `sub_7A97D0`  (0x7A97D0..0x7A9810, 64 bytes)

**PURPOSE** `cSC4WinRCI::SetSources(const uint32* ids, int count)` — vt `0xAB8884+0x14`.
**CONVENTION** `__stdcall` method, `this` in ECX, `ret 8`.

```c
bool SetSources(const uint32* ids, int count) {
    uint32* dst = &this->[0xE0];
    for (int i = 0; i < count; ++i) dst[i] = ids[i];   // 0x7A97E7  NO bounds check
    this->[0x120] = count;
    return Recompute();                                 // tail into sub_7A93E0, ecx preserved
}
```
Note: **Latent overflow**: the destination array is `+0xE0..+0x11F` = 16 slots; `count > 16`
writes over `sourceCount`, the accumulators and the colour. Never hit in stock data.

<a id="sub_7a9810"></a>
## `sub_7A9810`  (0x7A9810..0x7A9880, 112 bytes)

**PURPOSE** `cSC4WinRCI::DoMessage` — cIGZMessageTarget2 vt `0xAB8614+0x0C`.
**`this` = obj+0xDC.** **CONVENTION** `__stdcall` method, `(cIGZMessage2* msg)`, `ret 4`.

```c
bool DoMessage(cIGZMessage2* m) {
    if (m->vt[0x10]() != 0x426840A0) return false;    // GetType
    uint32 changed = m->vt[0x24]();                   // the source id that changed
    int n = this->[0x44];                             // == obj+0x120  (sourceCount)
    for (int i = 0; i < n; ++i)
        if (changed == this->[0x04 + 4*i]) {          // == obj+0xE0 + 4i
            if (sub_7A93E0( (char*)this - 0xDC ))     // Recompute on obj+0
                ((cIGZWin*)((char*)this - 0xD8))->vt[0x170]();   // repaint  (obj+4)
            break;
        }
    return false;
}
```
This is the load-bearing cross-check on the whole field map: `this+0x44 == obj+0x120`
and `this+0x04 == obj+0xE0` line up exactly with `sub_7A97D0`/`sub_7A93E0`.

---

# Part B — the region-screen CLOUD layer (`0x7A9880` – `0x7AA110`)

Window id **`0x6A0AF41D`**, vtable `0xAB88C0`, object size **`0x140`**, created by
`cSC4WinRegionScreen::Init` (`0x7B1EFF`) into **`regionScreen+0xE4`**, then added as a
child (`regionScreen->vt+0x38`) and `SetFlag(0x800, 0)`-ed at `0x7B1F59`.
`tools\uimap\coverage-matrix.md:675` already flags it "cosmetic — leave alone".

**Object layout** (all offsets are obj-relative; the `cGZWin` base is at `+0`, so
`this` for every method here == obj):

| offset | field |
|---|---|
| `+0x000 .. +0x0D7` | `cGZWin` base (vptr `0xAB88C0`) |
| `+0x0D8 .. +0x0EF` | stopwatch (ctor `0x88FEDF(4)`, dtor `0xA6D837`) |
| `+0x0F0`, `+0x0F4` | `int panX, panY` (`SetPan`) |
| `+0x0F8 .. +0x104` | `float left, top, right, bottom` — emitter bounds |
| `+0x108`, `+0x10C` | `float windX, windY` — unit vector |
| `+0x110`, `+0x111` | `uint8 alphaLo = 0x20, alphaHi = 0x40` |
| `+0x114` | circular doubly-linked list head (a 0x20-byte sentinel from `0x90CF54`) |
| `+0x118 .. +0x124` | `cS3DTextureBinding* tex[4]` |
| `+0x128 .. +0x13F` | `cRZRandom` |

**Particle node** (0x20 bytes, `alloc(0x20)`): `+0x00 next`, `+0x04 prev`,
`+0x08 float x`, `+0x0C float y`, `+0x10 float vx`, `+0x14 float vy`,
`+0x18 int texIndex`, `+0x1C uint8 alpha`.

<a id="sub_7a9880"></a>
## `sub_7A9880`  (0x7A9880..0x7A98A0, 32 bytes)
`Shutdown` (vt `+0x14`). `if (IsInited()) { SetInited(false); cGZWin::Shutdown(); } return true;`

<a id="sub_7a98a0"></a>
## `sub_7A98A0`  (0x7A98A0..0x7A98C0, 32 bytes)
`__stdcall SetPan(const int p[2])`, `ret 4`: `[this+0xF0] = p[0]; [this+0xF4] = p[1];`
**CALLERS** `sub_7AC830` @ `0x7ACAA8` — i.e. **`cSC4WinRegionScreen::Draw` (vt+0x160 =
`0x7AC830`) pushes the current region pan into the cloud layer every frame.**

<a id="sub_7a98c0"></a>
## `sub_7A98C0`  (0x7A98C0..0x7A98E0, 32 bytes)
`__stdcall SetAlphaRange(uint8 lo, uint8 hi)`, `ret 8`: writes `+0x110`, `+0x111`.
**CALLERS** `sub_7ABF10` @ `0x7AC0D7`.

<a id="sub_7a98e0"></a>
## `sub_7A98E0`  (0x7A98E0..0x7A9980, 160 bytes)

**PURPOSE** `MakeParticle(out)` — fills a 0x18-byte sprite record with a random particle.
**CONVENTION** `__stdcall` method, `(sprite* out)`, `ret 4`.

```c
void MakeParticle(sprite* o) {
    o->x  = this->left - 128.0f;                                    // [0xAB7E10]
    float t = rnd.Rand01();                                          // 0x91372E
    o->y  = (this->bottom - this->top) * t + (this->top - 128.0f);
    float s = (rnd.Rand01() + 1.0) * 5.0;                            // [0xA80AB0], [0xAB3AD0]
    o->vx = s * this->windX;                                         // +0x108
    o->vy = s * this->windY;                                         // +0x10C
    o->tex   = rnd.RandRange(0, 4);                                  // 0x9136CA(0,4)
    o->alpha = (uint8)rnd.RandRange(this->alphaLo, this->alphaHi);   // (0x20, 0x40)
}
```
Particles are born **one sprite-width off the left edge** and drift right at 5..10 px/s.
**CALLERS** `sub_7A9C20` @ `0x7A9CC7`; `sub_7A9D60` @ `0x7A9F9F`.

<a id="sub_7a9980"></a>
## `sub_7A9980`  (0x7A9980..0x7A99C0, 64 bytes)
`__stdcall SetWindDirection(float dx, float dy)`, `ret 8`:
`k = 1.0f / sqrt(dx*dx + dy*dy); this->[0x108] = dx*k; this->[0x10C] = dy*k;`
Note: no zero-length guard — `(0,0)` yields NaNs. **CALLERS** `sub_7B1900` @ `0x7B1F9F`
(`cSC4WinRegionScreen::Init` sets the wind once).

<a id="sub_7a99c0"></a>
## `sub_7A99C0`  (0x7A99C0..0x7A9AE0, 288 bytes)

**PURPOSE** cloud layer `Init` — vt `+0x10`. **CONVENTION** `__thiscall`, no args, `bool`.

```c
bool Init() {
    if (IsInited()) return true;
    MarkInited();
    this->vt[0x100](0x6A0AF41D);                       // SetID              0x7A99E6

    cIS3DTextureBindingFactory* f = 0;
    if (cIGZCOM* com = GZCOM())                        // 0x8793EC
        com->vt[0x14](0x1AC0E11A, 0xFAC0E219, &f);     // GetClassObject     0x7A9A0E
    if (f)
        for (int i = 0; i < 4; ++i) {                  // 0x7A9A20 .. 0x7A9A4B
            if (this->tex[i]) { this->tex[i] = 0; release(0x8090E0); }
            f->vt[0x14](0x4A624656 + i, &this->tex[i]);   // GetBinding(uint32, cS3DTextureBinding**)
        }

    cIGZWin* root  = this->vt[0x28]();                 // -> cGZWin+0x04 (WinMgr) vt+0x0C = root
    cIGZWin* root2 = this->vt[0x28]();
    this->vt[0xDC](0, 0, root2->vt[0xA4](), root->vt[0xA8]());   // SetArea(0,0,rootW,rootH)

    this->left  = 0; this->top = 0;                                    // +0xF8 / +0xFC
    this->right  = (float)this->vt[0xA4]();                            // +0x100 = own GetW
    this->bottom = (float)this->vt[0xA8]();                            // +0x104 = own GetH
    release(f);
    return true;
}
```
This is why "resizing the window is a no-op": the emitter rect is latched here, and the
window is sized to the **root** window, not to the region view.
**CALLERS** none direct — vtable `0xAB88D0` (`0xAB88C0+0x10`).

<a id="sub_7a9ae0"></a>
## `sub_7A9AE0`  (0x7A9AE0..0x7A9B90, 176 bytes)

**PURPOSE** cloud layer constructor. `__thiscall`, no args, returns `this`.

```c
void* ctor() {
    cGZWin::cGZWin(this);                       // 0x99D938
    stopwatch_ctor(this + 0xD8, 4);             // 0x88FEDF
    this[0x00]  = 0xAB88C0;
    this->panX = this->panY = 0;                // +0xF0 / +0xF4
    this->alphaLo = 0x20;  this->alphaHi = 0x40;// +0x110 / +0x111   (BYTE writes)
    this->[0x114] = 0;
    void* head = alloc(0x20);                   // 0x90CF54
    head[0] = head; head[1] = head;             // empty circular list
    this->[0x114] = head;
    this->tex[0..3] = 0;                        // +0x118 .. +0x124
    rnd.Seed(-1);                               // 0x913A5C on this+0x128
    stopwatch_setmode(this + 0xD8, 4);          // 0x890181
    cGZWin::SetFlag(this, 0x10000, false);      // 0x99DB6B  (== vt+0x110)
    cGZWin::SetFlag(this, 0x200000, true);
    return this;
}
```
Note: `+0xF8..+0x10C` (bounds and wind) are **not** initialised here — `Init` sets the bounds
and `cSC4WinRegionScreen::Init` sets the wind.
**CALLERS** `sub_7B1900` @ `0x7B1EFF`, after `new(0x140)` at `0x7B1EEC`.

<a id="sub_7a9b90"></a>
## `sub_7A9B90`  (0x7A9B90..0x7A9C00, 112 bytes)

**PURPOSE** cloud layer destructor. `__thiscall`, no args.

```c
void dtor() {
    this[0] = 0xAB88C0;
    if (IsInited()) { SetInited(false); cGZWin::Shutdown(this); }
    for (int i = 3; i >= 0; --i)                       // 0x7A9BC0 loop, esi walks +0x124 -> +0x118
        if (this->tex[i]) release(this->tex[i]);       // 0x8090E0
    destroyList(this + 0x114);                         // 0x5650A0
    stopwatch_dtor(this + 0xD8);                       // 0xA6D837
    cGZWin::~cGZWin(this);                             // tail-jmp 0x99E1A2
}
```
Note: The texture loop does **not** null the slots after releasing them.

<a id="sub_7a9c00"></a>
## `sub_7A9C00`  (0x7A9C00..0x7A9C20, 32 bytes)
Scalar deleting destructor, vt `0xAB8B10` (= `0xAB88C0 + 0x250`). `dtor(); if (flags&1) delete this; return this;` `ret 4`.

<a id="sub_7a9c20"></a>
## `sub_7A9C20`  (0x7A9C20..0x7A9D60, 320 bytes)

**PURPOSE** `SetBounds(float l, float t, float r, float b)` — sets the emitter rect,
**wipes** the live particle list and repopulates it to the steady-state density.
**CONVENTION** `__stdcall` method, `ret 0x10`.

```c
void SetBounds(float l, float t, float r, float b) {
    this->left = l; this->top = t; this->right = r; this->bottom = b;   // +0xF8..+0x104

    for (node* p = head->next; p != head; ) { node* n = p->next; free(p); p = n; }  // 0x90CF63
    head->next = head; head->prev = head;

    int n = ftol( (b - t) * (r - l) * 6.103515625e-05 );    // [0xAB8B20] == 1/16384
    for (int i = 0; i < n; ++i) {
        sprite s; MakeParticle(&s);                          // sub_7A98E0
        float u = rnd.Rand01();
        s.x = ((r - l) - 128.0f) * u + (l - 128.0f);         // spread across the whole band
        node* q = alloc(0x20);                               // 0x90CF54
        memcpy(&q->x, &s, 0x18);                             // 6 dwords, 0x7A9D10..0x7A9D36
        link_at_head(q);
    }
}
```
**1/16384 = 1/(128·128)** — i.e. **exactly one cloud sprite per 128×128 screen block**.
Consequence for the scaling project: the cloud count is a function of the *window* size,
which is the ROOT window, so it already tracks resolution.
**CALLERS** `sub_7AB7C0` @ `0x7AB9DB`.

<a id="sub_7a9d60"></a>
## `sub_7A9D60`  (0x7A9D60..0x7AA110, 944 bytes)

**PURPOSE** cloud layer **`Draw`** — vt `0xAB8A20` (= `0xAB88C0 + 0x160`).
Time-steps, spawns, draws and reaps the particle list.
**CONVENTION** `__thiscall`, no stack args, plain `ret`, `bool` in AL.

```c
bool Draw() {
    if (!tex[0] || !tex[1] || !tex[2] || !tex[3]) return true;    // 0x7A9D69..0x7A9D9B

    // ---- dt -------------------------------------------------------------
    float dt;
    if (!stopwatch_isRunning(this+0xD8)) { stopwatch_start(this+0xD8); dt = <uninit>; }
    else { int ms = stopwatch_elapsedMs(this+0xD8);
           dt = (float)min(ms, 200) * 0.001f;                     // [0xA867A4]
           stopwatch_restart(this+0xD8); }

    // ---- render state ---------------------------------------------------
    cIGZGDriver* g = (*(cIGZGraphicSystem**)0xB43CA0)->vt[0x0C]();
    g->Disable(3); g->Disable(0); g->Enable(4); g->Disable(1); g->Enable(5);
    g->BlendFunc(4, 5);                       // vt+0x54
    g->TexStage(0); g->TexStageCoord(0); g->TexStageMatrix(NULL, 3, 2, 1);

    // ---- one quad, 4 verts, stride 0x18 = {float x,y,z; ubyte4 rgba; float u,v}
    vtx v[4]; memset-ish: rgb = (255,255,255), a = 0x20,
              v[0].uv=(0,0) v[1].uv=(1,0) v[2].uv=(0,1) v[3].uv=(1,1);
    g->InterleavedArrays(0xA, 0, v);          // vt+0x14, ONCE for the whole list

    // ---- spawn ----------------------------------------------------------
    if (rnd.Rand01() < 0.003) {               // [0xAB8B28]
        sprite s; MakeParticle(&s); list_push(&this->[0x114], &s);   // 0x747FF0
    }

    // ---- per particle ---------------------------------------------------
    for (node* p = head->next; p != head; ) {
        if (p->x >= this->right) { unlink(p); free(p); p = next; continue; }   // 0x7A9FD0

        v[0..3].a = p->alpha;                                   // node+0x1C
        float px = p->x - (float)this->panX;                    // fild +0xF0
        float py = p->y - (float)this->panY;                    // fild +0xF4
        v[0] = (px,       py      );
        v[1] = (px+128.0f,py      );
        v[2] = (px,       py+128.0f);
        v[3] = (px+128.0f,py+128.0f);                           // [0xAB7E10] = 128.0

        g->SetTexture( *(uint32*)*(void**)this->tex[p->tex] );  // vt+0xE8, 1 arg   (note)
        g->TexParameter(0, 0, 1);   g->TexParameter(0, 1, 1);   // vt+0x74 ×2
        g->TexEnv(0, 0, 1);                                     // vt+0x70
        g->DrawArrays(1, 0, 4);                                 // vt+0x0C

        p->x += dt * p->vx;   p->y += dt * p->vy;               // 0x7AA0AF..0x7AA0C6
        p = p->next;
    }
    return true;
}
```
Facts worth keeping:
* the sprite is a **fixed 128×128 screen-space quad**; it never scales with UI factor.
* the reap test is `p->x >= this->right` — the *right* emitter bound, i.e. the window width.
* `dt` is clamped at 200 ms, so a stall cannot teleport the clouds.
* Note: On the very first frame the "stopwatch not running" leg leaves `dt` = whatever was in
  `[esp+0x10]` (`0x7A9DAC` sets it to 0 before the branch, so it is 0 — benign).
* Note: `SetTexture`'s argument is `**binding` (two dereferences of `tex[i]`). I could not
  prove which field of `cS3DTextureBinding` that is.

<a id="sub_7aa0e0"></a>
## `sub_7AA0E0`  (0x7AA0E0..0x7AA103, 35 bytes) — **absent from funcs.json**

**PURPOSE** the **tent / triangle (linear) filter kernel**.
**CONVENTION** `__cdecl double f(double x)`, result in `st(0)`.

```c
double tent(double x) {
    double a = fabs(x);
    if (a < 1.0) return 1.0 - a;      // fcom [0xA80AB0]=1.0, then fsubr
    return 0.0;                       // fld [0xA80990]
}
```
Its address is taken as a function pointer at `0x7AE1EB` (`push 0x7AA0E0`) and handed to
`sub_7AA860`. **This is the filter SC4 uses to resample region tile art.**

<a id="sub_7aa110"></a>
## `sub_7AA110`  (0x7AA110..0x7AA2A0, 400 bytes)

**PURPOSE** **horizontal 2-tap ARGB resample of one scanline**, 14-bit fixed point.
**CONVENTION** `__cdecl`, 6 args, caller cleans (`add esp,0x18` at `0x7AE337`).

```c
void FilterRow(uint32* dst,          // a1
               const uint32* src,    // a2
               int   count,          // a3   number of output pixels
               int   srcLen,         // a4   clamp bound
               const int weights[2], // a5   14-bit fixed weights
               int32 pos_16_16)      // a6   start position, 16.16 fixed  (callers pass 0xFFFF0000 = -1.0)
{
    for (int i = 0; i < count; ++i) {
        int x = pos_16_16 >> 16;                       // sar 0x10
        const uint32* tap = &src[x];
        if (x < 0 || x > srcLen - 2) {                 // 0x7AA148 / 0x7AA14D
            uint32 tmp[2];
            for (int k = 0; k < 2; ++k, ++x)
                tmp[k] = (x < 0 || x >= srcLen) ? 0 : src[x];   // out-of-range -> 0x00000000
            tap = tmp;
        }
        uint32 p0 = tap[0], p1 = tap[1];
        int w0 = weights[0], w1 = weights[1];
        int a = ((p0>>24)&0xFF)*w0 + ((p1>>24)&0xFF)*w1;
        int r = ((p0>>16)&0xFF)*w0 + ((p1>>16)&0xFF)*w1;
        int g = ((p0>> 8)&0xFF)*w0 + ((p1>> 8)&0xFF)*w1;
        int b = ( p0     &0xFF)*w0 + ( p1     &0xFF)*w1;
        a = (a + 0x2000) >> 14;  ... etc                // 0x7AA1E9 .. 0x7AA20A
        // saturate: if ((unsigned)v >= 0x100) v = ~(v >> 31) & 0xFF;   0x7AA20D..
        *dst++ = (a<<24) | (r<<16) | (g<<8) | b;        // 0x7AA250..0x7AA25D
        pos_16_16 += 0x10000;                           // 0x7AA274 — always exactly +1 source pixel
    }
}
```
**Key numbers:** `+0x2000` = 8192 and `>> 14` — the weights are normalised to **16384**
(`2^14`), which is exactly what `sub_7AA860` is asked to produce (`0x46800000 = 16384.0f`).
**Edge handling is transparent-black, not clamp-to-edge** — taps outside `[0, srcLen)`
contribute `0x00000000`.
Because the step is a hard `+1.0`, this is a **fixed 2-tap convolution at 1:1 scale**
(a shift/blur), not an arbitrary rescale.
**CALLERS** `sub_7AE160` @ `0x7AE332`.

---

# Part C — the terrain-grid base class (`0x7AA2A0` – `0x7AA510`)

Constructed by **`sub_7AACE0`** (first function of slice 2), whose body settles the layout:

```c
Grid* ctor(int w, int h) {                     // __thiscall, ret 8
    this[0x00] = 0xAB3BE8;                     // transient
    base_ctor(this + 4);                       // 0x90D957
    this[0x14] = w;                            // 0x7AACFE
    this[0x04] = 0xAB8BE8;                     // secondary vptr
    this[0x1C] = w + 1;                        // 0x7AAD08   <-- STRIDE = w+1  (vertex grid)
    this[0x00] = 0xAB8C00;
    this[0x0C] = 0x43870000;                   //  270.0f    default height
    this[0x10] = 0;
    this[0x18] = h;
    this[0x20] = 0x42800000;                   //   64.0f    cell size
    this[0x24] = 0;                            //  bool
    return this;
}
```

| offset | field |
|---|---|
| `+0x00` | vptr `0xAB8C00` |
| `+0x04` | secondary vptr `0xAB8BE8` (its slot 0 is the thunk `sub_7AAAF0`) |
| `+0x0C` | `float defaultValue` = **270.0f** |
| `+0x10` | `float` = 0 |
| `+0x14` | `int width` |
| `+0x18` | `int height` |
| `+0x1C` | `int stride` = `width + 1` |
| `+0x20` | `float cellSize` = **64.0f** |
| `+0x24` | `bool` (edit/dirty latch) |

> The `+0x1C = w + 1` is the single most useful fact here: the grid is a **vertex** grid,
> so an `n×n` region has `(n+1)×(n+1)` samples. Anything that indexes it with `w` instead
> of `w+1` will skew by one column per row.

<a id="sub_7aa2a0"></a>
## `sub_7AA2A0`  (0x7AA2A0..0x7AA2E0, 64 bytes)
`QueryInterface`, vt `0xAB8C00+0x00`. Accepts `1` and **`0xAB953253`**, both returning
`this` + AddRef; everything else `false`. `ret 8`. Note: `0xAB953253` is not in the
`{clsid → name}` registry at `0xB05000..0xB0B000`.

<a id="sub_7aa2e0"></a>
## `sub_7AA2E0`  (0x7AA2E0..0x7AA2F0, 16 bytes)
vt `+0x0C`. `mov al,1; mov byte [ecx+0x24], al; ret` — set the latch, return true. `ret 0`.

<a id="sub_7aa2f0"></a>
## `sub_7AA2F0`  (0x7AA2F0..0x7AA300, 16 bytes)
vt `+0x10`. `mov byte [ecx+0x24], 0; mov al,1; ret` — clear the latch, return true.

<a id="sub_7aa300"></a>
## `sub_7AA300`  (0x7AA300..0x7AA310, 16 bytes)
vt `+0x18`. `fld dword [ecx+0x20]; ret` — **GetCellSize() = 64.0f**.
(Also referenced from `0xAA2784`, an unrelated vtable.)

<a id="sub_7aa310"></a>
## `sub_7AA310`  (0x7AA310..0x7AA320, 16 bytes)
vt `+0x24`, `__stdcall (int x, int y)`, `ret 8`:
`return this->[0x1C] * y + x;`  — **`CellIndex(x, y) = y*stride + x`** (`imul eax,[esp+8]`).

<a id="sub_7aa320"></a>
## `sub_7AA320`  (0x7AA320..0x7AA350, 48 bytes)
vt `+0x28`, `__stdcall (int idx, int* outX, int* outY)`, `ret 0xC`:
`*outX = idx % stride; *outY = idx / stride;` (two `idiv [ecx+0x1C]`, **signed**).

<a id="sub_7aa350"></a>
## `sub_7AA350`  (0x7AA350..0x7AA3B0, 96 bytes)
vt `+0x2C`, `__stdcall bool InBounds(float wx, float wy)`, `ret 8`:

```c
if (wx < 0.0f) return 0;                       // fcomp [0xA81054] = 0.0f
if (wy < 0.0f) return 0;
float s = 1.0f / this->cellSize;               // [0xA81228] = 1.0f, fdiv [ecx+0x20]
if (!((wx * s) < (float)this->width))  return 0;
if (!((wy * s) < (float)this->height)) return 0;
return 1;
```
World units → cells is a **divide by 64**, and the test is strict `<` against
`width`/`height` (`+0x14`/`+0x18`), **not** against the `+1` stride.

<a id="sub_7aa3b0"></a>
## `sub_7AA3B0`  (0x7AA3B0..0x7AA3C0, 16 bytes)
vt `+0x30`, `ret 4`: `fld dword [ecx+0x0C]` — the null grid returns 270.0f for any index.

<a id="sub_7aa3c0"></a>
## `sub_7AA3C0`  (0x7AA3C0..0x7AA430, 112 bytes)

vt `+0x3C`, `__stdcall (const int rect[4], float* base, int rowStep, int colStep)`, `ret 0x10`.

```c
for (int y = rect[1]; y < rect[3]; ++y) {          // 0x7AA3C9 jge out
    float* p = base;                               // NOTE: not offset by rect[0]
    for (int x = rect[0]; x <= rect[2]; ++x) {     // 0x7AA410 jle
        *p = this->[0x0C];                         // 270.0f
        p += colStep;                              // shl 2 -> dword stride
    }
    base += rowStep;
}
```
Note: Two quirks confirmed in the bytes: the row loop is **half-open** (`y < rect[3]`) while
the column loop is **closed** (`x <= rect[2]`), and the column start `rect[0]` is used
only as a loop counter — the pointer always starts at `base`.

<a id="sub_7aa430"></a>
## `sub_7AA430`  (0x7AA430..0x7AA490, 96 bytes)
vt `+0x40`. Byte-for-byte the same loop as `sub_7AA3C0` but stores `0` instead of
`[this+0x0C]`. Same signature, `ret 0x10`.

<a id="sub_7aa490"></a>
## `sub_7AA490`  (0x7AA490..0x7AA4B0, 32 bytes)
vt `+0x44`, `__stdcall (a1, a2, float out[4])`, `ret 0xC`:
writes `[this+0x0C]` into `out[0..3]`. Almost certainly "four corner heights of a cell".

<a id="sub_7aa4b0"></a>
## `sub_7AA4B0`  (0x7AA4B0..0x7AA4C0, 16 bytes)
`fld dword [ecx+0x0C]; ret 8`. Occupies **four** slots: `+0x34`, `+0x38`, `+0x4C`, `+0x50`
(vtable addresses `0xAB8C34/0xAB8C38/0xAB8C48/0xAB8C4C`).

<a id="sub_7aa4c0"></a>
## `sub_7AA4C0`  (0x7AA4C0..0x7AA4D0, 16 bytes)
`fld dword [0xA81054] (= 0.0f); ret 4`. Slots `+0x50` and `+0x7C`.

<a id="sub_7aa4d0"></a>
## `sub_7AA4D0`  (0x7AA4D0..0x7AA4E0, 16 bytes)
`fld dword [ecx+0x0C]; ret` (no stack args). Slots `+0x54`, `+0x58`.

<a id="sub_7aa4e0"></a>
## `sub_7AA4E0`  (0x7AA4E0..0x7AA4F0, 16 bytes)
`fld dword [0xA81054] (= 0.0f); ret`. Slot `+0x5C`.

<a id="sub_7aa4f0"></a>
## `sub_7AA4F0`  (0x7AA4F0..0x7AA500, 16 bytes)
`fld dword [0xAB8B80] (= **1023.0f**); ret`. Slot `+0x60`. Note: 1023 = the maximum terrain
height the engine will report from the null grid.

<a id="sub_7aa500"></a>
## `sub_7AA500`  (0x7AA500..0x7AA510, 16 bytes)
`fld dword [ecx+0x10]; ret`. Slot `+0x74`.

<a id="sub_7aa510"></a>
## `sub_7AA510`  (0x7AA510..0x7AA520, 16 bytes)
`fld dword [0xA81054] (= 0.0f); ret 8`. Slots `+0x78`, `+0x80`, `+0x84`.

---

# Part D — misc window plumbing

<a id="sub_7aa520"></a>
## `sub_7AA520`  (0x7AA520..0x7AA570, 80 bytes)

**PURPOSE** `Init` (vt `0xAB8CD0 + 0x10`) of the window whose ctor is `0x7AAE1C` and whose
`Draw` is `0x7AB130`. `__thiscall`, `bool`.

```c
bool Init() {
    if (IsInited()) return true;
    MarkInited();
    this->[0xD8] = 0xC2A676AC;               // 0x7AA53E   Note: unidentified id
    this->vt[0x110](0x10000, false);         // SetFlag
    this->vt[0x110](0x8000,  false);
    return true;
}
```

<a id="sub_7aa570"></a>
## `sub_7AA570`  (0x7AA570..0x7AA5A0, 48 bytes)
`Shutdown` (vt `0xAB8CD0 + 0x14`): if inited, release `this->[0x10C]` (`vt+0x08`), null it,
then `cGZWin::Shutdown` (`0x99D2FE`). `bool`.

<a id="sub_7aa5a0"></a>
## `sub_7AA5A0`  (0x7AA5A0..0x7AA600, 96 bytes)

**PURPOSE** the **painter's-order comparator** for the region quadtree.
**CONVENTION** `__stdcall` method (`this` in ECX is *ignored*), `(const node* a, const node* b)`, `ret 8`.

Records are `0x0C` bytes: `{ int x; int y; int level; }`.

```c
bool less(const node* a, const node* b) {
    int d = (1 << a->level) - (1 << b->level)
          - b->y + a->y
          - b->x + a->x;                       // 0x7AA5B0 .. 0x7AA5D2
    if (d <  0) return true;
    if (d == 0) return a->x < b->x;            // 0x7AA5DA
    return false;
}
```
i.e. the sort key is **`x + y + (1 << level)`**, tie-broken on `x` — the classic
back-to-front ordering for an isometric quadtree. Everything the region map draws is
ordered by this.
**CALLERS** `sub_7AA920` ×4 (`0x7AA966`, `0x7AA975`, `0x7AA996`, `0x7AA9A5`).

<a id="sub_7aa600"></a>
## `sub_7AA600`  (0x7AA600..0x7AA640, 64 bytes)

**PURPOSE** `cSC4WinRegionScreen` **vt+0x234** (`0xAB9260 + 0x234 = 0xAB9494`).
**CONVENTION** `__stdcall` method, 1 (ignored) arg, `ret 4`, returns `true`.

```c
bool f(void* ignored) {
    int a, b;
    this->[0x04]->vt[0x88](this, &a, &b);      // 0x7AA616  — [regionScreen+0x04] is the cGZWin WinMgr
    this->vt[0x228](a, b, 0);                  // 0x7AA62C  (0xAB9260+0x228 = 0x7AB760)
    return true;
}
```
Note: The `vt+0x88` on the window manager is unidentified; from context it yields a
coordinate pair for `this`.

<a id="sub_7aa640"></a>
## `sub_7AA640`  (0x7AA640..0x7AA6A0, 96 bytes)

**PURPOSE** **`cSC4WinRegionScreen::QueryInterface`** — vt `0xAB9260 + 0x00`.
This pins down the class's interface layout:

```c
bool QI(uint32 iid, void** out) {
    if (iid == 1 || iid == 0x22BA0121) { *out = this; ... }          // cIGZUnknown / cIGZWin at +0
    else if (iid == 0xC6AE7085)        { *out = (char*)this + 0xD8; }// cIGZWinMessageFilter
    else return false;
    AddRef(); return true;
}
```
> **`cSC4WinRegionScreen`'s `cGZWin` base is at offset 0** (no `+4` adjustment, unlike
> `cSC4WinRCI`), and its only extra interface is **`cIGZWinMessageFilter` at `+0xD8`**.
> GROUND TRUTH's field list is therefore all `cGZWin`-relative — consistent.

<a id="sub_7aa6a0"></a>
## `sub_7AA6A0`  (0x7AA6A0..0x7AA860, 448 bytes)

**PURPOSE** **alpha-weighted centroid of a surface** — the "hot spot" of a tile thumbnail.
**CONVENTION** **`__usercall`**: `this` in **EAX**, two `int*` out-params on the stack,
**caller cleans** (`add esp,8` at `0x7AE78A`). Signature:
`void Centroid(/*EAX*/ Buffer* buf, int* outX, int* outY)`.

```c
void Centroid(Buffer* buf, int* outX, int* outY) {
    int* r = buf->vt[0x30]();          // GetRect -> &buf[0x14]; r[2] = width, r[3] = height
    int  W = r[2], H = r[3];
    int64 sx = 0, sy = 0, sw = 0;

    if (buf->vt[0x18](0x40)) {         // Lock(0x40)
        for (int y = 0; y < H; ++y) {
            uint8* row = (uint8*)buf->vt[0x88]() + buf->vt[0x8C]() * y;   // bits + pitch*y
            int ax = 0, ay = 0, aw = 0;
            for (int x = 0; x < W; ++x) {
                uint8 a = row[2*x + 1];          // <-- 16 BITS PER PIXEL, high byte
                if (!a) continue;
                ax += a * x;  ay += a * y;  aw += a;
            }
            sx += ax; sy += ay; sw += aw;        // 32->64 widening (cdq/adc)
        }
        buf->vt[0x1C](0x40);           // Unlock(0x40)
    }

    if (sw > 0) {
        int64 half = sw / 2;                                   // __alldiv, 0x7AA7E2
        *outX = (int)((sx + half) / sw);                        // 0x7AA805
        *outY = (int)((sy + half) / sw);                        // 0x7AA820
    } else {
        *outX = W / 2;                                          // 0x7AA83A
        *outY = H / 2;                                          // 0x7AA84D
    }
}
```
Two things matter here for the tile pipeline:
1. **It reads the surface as 16 bpp** (`row[2*x + 1]`), taking the high byte of each
   16-bit pixel as the weight. GROUND TRUTH's composite head has `+0x10 = 0x20` (32 bpp) —
   so either this runs on a *different* (16-bit) source buffer, or a 32-bpp buffer would be
   mis-sampled. Flagged, not resolved.
2. The result is stored into **`item+0x68` and `item+0x6C`** by the one call site:
   `0x7AE777: mov eax,[edi]; lea edx,[ebx+0x6C]; push edx; add ebx,0x68; push ebx; call 0x7AA6A0`.
   Note: I did not trace `ebx` back to the 0x80-stride item array inside `sub_7AE510`, but
   `sub_7AE510` addresses `ebx+0x24/+0x28/+0x50/+0x5C/+0x68/+0x6C` — all inside a 0x80 stride.

**CALLERS** `sub_7AE510` @ `0x7AE781` (the composite creator).

<a id="sub_7aa860"></a>
## `sub_7AA860`  (0x7AA860..0x7AA8E0, 128 bytes)

**PURPOSE** **sample a filter function over a range and normalise the samples to a fixed
sum** — this is how the 14-bit weights consumed by `sub_7AA110`/`sub_7AABB0` are made.
**CONVENTION** `__cdecl`, 6 args (frame pointer, `mov esp,ebp; pop ebp; ret`).

```c
void BuildKernel(float  x0,                 // [ebp+0x08]
                 float  dx,                 // [ebp+0x0C]
                 float* begin,              // [ebp+0x10]
                 float* end,                // [ebp+0x14]
                 double (*f)(double),       // [ebp+0x18]
                 float  total)              // [ebp+0x1C]
{
    float sum = 0.0f;
    for (float* p = begin; p != end; ++p) {
        *p   = (float)f((double)x0);        // 0x7AA880..0x7AA88C
        sum += *p;
        x0  += dx;                          // 0x7AA89E
    }
    float k = total / sum;                  // 0x7AA8AB
    for (float* p = begin; p != end; ++p) *p *= k;
}
```
Note: No `sum == 0` guard.
**CALLERS** `sub_7AE160` @ `0x7AE1B6` and `0x7AE206`, `sub_7C0B80` @ `0x7C0BF6`.
At `0x7AE1E6..0x7AE206` the arguments are literally
`BuildKernel(-<offset>, 1.0f, begin, end, /*f=*/0x7AA0E0 /*tent*/, 16384.0f)`
(`push 0x3F800000` = 1.0f, `push 0x46800000` = 16384.0f).

> **This closes the loop on the region tile resampler:** tent filter → kernel normalised to
> 2^14 → 2-tap horizontal pass (`sub_7AA110`) → 2-tap vertical pass (`sub_7AABB0`), all in
> 14-bit fixed point with `+0x2000` rounding.

<a id="sub_7aa8e0"></a>
## `sub_7AA8E0`  (0x7AA8E0..0x7AA920, 64 bytes)
`__cdecl bool operator!=(const POINT* a, const POINT* b)` — returns **1 when they differ**
(the `sete cl` at the end inverts an internal equal-flag).
**CALLERS** `0x4271F3`, `0x4377D8`, `0x4DC0BD`, `0x646C08`, and `sub_7B13C0` @ `0x7B17B5`.

<a id="sub_7aa920"></a>
## `sub_7AA920`  (0x7AA920..0x7AA9C0, 160 bytes)
**PURPOSE** median-of-three pivot selection over `{x,y,level}` records, using the
`sub_7AA5A0` key. `__cdecl`, 3 record pointers + (unused) 4th slot, returns the median
pointer. The first comparison is inlined (identical arithmetic to `sub_7AA5A0`), the rest
call `sub_7AA5A0`.
**CALLERS** `sub_7AE8D0` @ `0x7AE939`.

<a id="sub_7aa9c0"></a>
## `sub_7AA9C0`  (0x7AA9C0..0x7AAA40, 128 bytes)
**PURPOSE** insertion step of the same sort: walks **backwards** in `0x0C`-byte strides
(`sub edx,0x0C`) copying records forward while the new key sorts before them, then writes
the new `{x, y, level}`. `__cdecl`, `ret` plain.
Note: I did not fully resolve which stack slot supplies which of the three new-record fields —
the final stores are `[ebx] = edi`, `[ebx+4] = ecx`, `[ebx+8] = [esp+0x1C]`.
**CALLERS** `sub_7AC490` @ `0x7AC4BC`, `sub_7AD8D0` @ `0x7AD94B`.

<a id="sub_7aaa40"></a>
## `sub_7AAA40`  (0x7AAA40..0x7AAAF0, 176 bytes)
**PURPOSE** heap sift-down over the same `0x0C`-byte records: the index arithmetic is
`lea ecx,[eax+eax*2]` then `[ebp + ecx*4]` (= `base + idx*12`), and the parent index is
recomputed as `(i-1)/2` (`lea eax,[edi-1]; cdq; sub eax,edx; sar eax,1`). Same
`x + y + (1<<level)` key. `__cdecl`, `ret` plain.
**CALLERS** `sub_7AC4D0` @ `0x7AC5AC`.

<a id="sub_7aaaf0"></a>
## `sub_7AAAF0`  (0x7AAAF0..0x7AAB00, 16 bytes)
Adjustor thunk at vt `0xAB8BE8+0x00`: `sub ecx,4; jmp 0x7AAD30`.
(The `+4` secondary interface of the terrain-grid class; real QI is `sub_7AAD30`, slice 2.)

<a id="sub_7aab00"></a>
## `sub_7AAB00`  (0x7AAB00..0x7AABB0, 176 bytes)
First 8 bytes: adjustor thunk at vt `0xAB8CAC+0x00`: `sub ecx,4; jmp 0x7AB600`.
The remaining 146 bytes are `sub_7AAB10`.

<a id="sub_7aab10"></a>
## `sub_7AAB10`  (0x7AAB10..0x7AABA2, 146 bytes) — **absent from funcs.json**

**PURPOSE** recursive child-window walker: clears flag `0x8000` on every window in a
subtree, and pushes a value into every `cIGZWinBtn` / `cIGZWinOptGrp` it finds.
**CONVENTION** `__cdecl`, plain `ret`. It is **passed to `cIGZWin::vt+0x80` as its own
callback** (`push 0x7AAB10` at `0x7AAB7F`), so this is the enumerator signature.

```c
bool Walk(a1, a2, cIGZWin* w /*3rd dword arg*/, void* value /*4th dword arg*/) {
    w->vt[0x110](0x8000, false);                       // SetFlag         0x7AAB22
    cIGZUnknown* p = 0;
    if (w->vt[0x00](0x00008810 /*GZIID_cIGZWinBtn*/, &p)) {
        w->vt[0x158](value);                           // 0x7AAB45
        p->Release();
    }
    cIGZUnknown* q = 0;
    if (w->vt[0x00](0xA1336CC0 /*GZIID_cIGZWinOptGrp*/, &q))
        w->vt[0x158](value);                           // 0x7AAB75
    else
        w->vt[0x80](0x22BA0121 /*GZIID_cIGZWin*/, &Walk);   // recurse    0x7AAB89
    if (q) q->Release();
    return true;
}
```
Note: The exact argument slots: `w` is read from `[E+0x0C]` and `value` from `[E+0x10]`
(`E` = esp at entry). Whether the enumerator supplies `(parent, iid, child, data)` or
`(child, id, data, extra)` is not proven — only the offsets are measured.
Note **`vt+0x158`** is the "set value/state" slot common to `cIGZWinBtn` and `cIGZWinOptGrp`.

<a id="sub_7aabb0"></a>
## `sub_7AABB0`  (0x7AABB0..0x7AACE0, 304 bytes)

**PURPOSE** **vertical 2-tap ARGB resample**, the transpose of `sub_7AA110`.
**CONVENTION** `__cdecl`, 4 args. Call site `0x7AE35B..0x7AE36B` pushes
`(weights, count, &rowTable, dst)` so the args are:

```c
void FilterColumn(uint32*        dst,       // a1  [E+0x04]
                  uint32* const* rows,      // a2  [E+0x08]  (a 4-dword record)
                  int            count,     // a3  [E+0x0C]
                  const int      w[2])      // a4  [E+0x10]
{
    for (int i = 0; i < count; ++i) {
        uint32 p0 = rows[0][i];             // 0x7AABD4
        uint32 p1 = rows[3][i];             // 0x7AAC02   <-- index 3, not 1
        int w0 = w[0], w1 = w[1];
        // identical per-channel math to sub_7AA110:
        //   (c0*w0 + c1*w1 + 0x2000) >> 14, saturated to [0,255], repacked ARGB
        *dst++ = pack(...);                 // 0x7AACAF
    }
}
```
Note: **`rows[0]` and `rows[3]`** — the second tap is taken from `+0x0C` of the record, not
`+0x04`. Either the caller's record is `{row0, ?, ?, row1}`, or this is a 4-row ring
buffer of which only the two ends are used with these weights. I could not settle it
without decoding `sub_7AE160`'s frame (slice 5/6 territory).
**CALLERS** `sub_7AE160` @ `0x7AE36B`.

---

## Open questions handed to the other slices

1. `cSC4WinRCI`'s `cIGZWin+0x6C` (the object with `vt+0x54` = set colour and `vt+0x8C` =
   fill rect). It is a `cGZWin` field, so identifying it once names it everywhere.
2. The service at `[0xB43D74]` (`vt+0x18(id, 0x20000)` → value object with float getters at
   `vt+0x30/+0x38/+0x3C`).
3. `sub_7AA6A0`'s 16-bpp assumption vs the 32-bpp composite head — which buffer is `[edi]`
   at `0x7AE777`?
4. `sub_7AABB0`'s `rows[0]` / `rows[3]` record layout (needs `sub_7AE160`'s frame map).
5. `0xC2A676AC` stored at `+0xD8` of the vt-`0xAB8CD0` window (`sub_7AA520`).
6. `cIGZGDriver` real `vt+0xE8` arity (1 arg observed, SDK header says 2).
