# Region-screen module — SLICE 4 of 8: `0x7AE3D0` .. `0x7AFAA0`

Source of truth: `SimCity 4.exe` (Deluxe 1.1.641, imagebase `0x400000`, `fileOffset = VA - 0x400000`).
Every VA / byte quoted below was read out of the binary in this pass, not copied from a prior report.
Function boundaries taken from `tools/uimap/funcs.json` (`starts` in `[0x7AE3D0, 0x7AFAA0]` inclusive,
each ending at the next start).

---

## Table of contents

| # | Function | Range | Bytes | One-liner |
|---|---|---|---|---|
| 1 | [`sub_7AE3D0`](#1-sub_7ae3d0) | `0x7AE3D0..0x7AE510` | 320 | Make a **sub-pixel-shifted copy** of a tile bitmap, `+2` px in each dimension |
| 2 | [`sub_7AE510`](#2-sub_7ae510) | `0x7AE510..0x7AE7B0` | 672 | **THE ITEM (tile) BUILDER** — shift the 4 source bitmaps, size + create the composite, build the 3 run-lists |
| 3 | [`sub_7AE7B0`](#3-sub_7ae7b0) | `0x7AE7B0..0x7AE8D0` | 288 | Item **copy-constructor** (stride `0x80`) |
| 4 | [`sub_7AE8D0`](#4-sub_7ae8d0) | `0x7AE8D0..0x7AE9B0` | 224 | MSVC `std::_Sort` introsort recursion, **12-byte elements** |
| 5 | [`sub_7AE9B0`](#5-sub_7ae9b0) | `0x7AE9B0..0x7AEA00` | 80 | `std::copy` over items (stride `0x80`, uses `operator=`) |
| 6 | [`sub_7AEA00`](#6-sub_7aea00) | `0x7AEA00..0x7AEC00` | 512 | **`GetOrCreateCity(item, bCreate)`** — the `1<<item[0x18]` size law lives here |
| 7 | [`sub_7AEC00`](#7-sub_7aec00) | `0x7AEC00..0x7AED00` | 256 | Sum every city's byte-size and report it to a stats service |
| 8 | [`sub_7AED00`](#8-sub_7aed00) | `0x7AED00..0x7AED60` | 96 | `std::sort(first, last, pred)` — 12-byte elements |
| 9 | [`sub_7AED60`](#9-sub_7aed60) | `0x7AED60..0x7AEDA0` | 64 | `std::uninitialized_copy` over items |
| 10 | [`sub_7AEDA0`](#10-sub_7aeda0) | `0x7AEDA0..0x7AEDD0` | 48 | `std::uninitialized_fill_n` over items |
| 11 | [`sub_7AEDD0`](#11-sub_7aedd0) | `0x7AEDD0..0x7AF4B0` | 1760 | **`kCommandID_RegionBitmapLoad`** — validate `config.bmp`, re-bake every city's `N×N` terrain bitmap |
| 12 | [`sub_7AF4B0`](#12-sub_7af4b0) | `0x7AF4B0..0x7AF720` | 624 | Find a city by name, or the first empty plot of a given size, and enter it |
| 13 | [`sub_7AF720`](#13-sub_7af720) | `0x7AF720..0x7AFAA0` | 896 | **`cIGZCommandServer` handler** — the 8 region-screen SCROLL commands live here |
| 14 | [`sub_7AFAA0`](#14-sub_7afaa0) | `0x7AFAA0..0x7B0470` | 2512 | **UI message handler** (`DoWinMessage`) — button/checkbox dispatch for the region screen |

Appendices:
* [A. The tile-buffer class (vtable `0x00AC1400`) — resolved slots](#appendix-a--tile-buffer-class-vtable-0x00ac1400)
* [B. Why `Init(520,320)` returned 0 — SOLVED](#appendix-b--why-init520320-returns-0-solved)
* [C. Item struct field map as measured in this slice](#appendix-c--item-struct-0x80-bytes--fields-touched-by-this-slice)
* [D. Constants / globals / strings referenced](#appendix-d--constants-globals-strings)

---

## 1. `sub_7AE3D0`
`sub_7AE3D0  (0x7AE3D0..0x7AE510, 320 bytes)`

**PURPOSE** — Create a NEW tile bitmap that is the source bitmap **shifted by a sub-pixel offset**,
sized `srcW+2 × srcH+2`. This is the only genuine resampling step anywhere in the tile pipeline,
and its scale factor is hard-wired to 1.0 (see `sub_7AE160`); the doubles carry only the *fractional*
part of the tile's screen position.

**CALLING CONVENTION** — `__cdecl`, all args on stack (no `ret N`; caller does `add esp,0x18`).

```c
bool __cdecl sub_7AE3D0(void*  src,        // [esp+0x30]
                        void** ppDst,      // [esp+0x34]  in/out slot
                        double dx,         // [esp+0x38]
                        double dy);        // [esp+0x40]
```
(arg-slot proof: `0x007AE47E fld qword [esp+0x40]` then, after `sub esp,0x10`,
`0x007AE48D fld qword [esp+0x48]` = the pre-`sub` `[esp+0x38]`.)

**PSEUDO-C**
```c
bool sub_7AE3D0(IGZBitmap* src, IGZBitmap** ppDst, double dx, double dy)
{
    if (!src) return false;                       // 0x007AE3DA

    cIGZGraphicSystem* gfx = sub_913C1A();        // cached singleton, clsid kGZGraphicSystem_SystemServiceID
    if (!gfx->vt+0x0C(ppDst))                     // 0x007AE3EC  CreateBitmap(out)
        return true;                              // NB: returns TRUE on create-failure (0x007AE4FC)

    IGZBitmap* dst = *ppDst;                      // 0x007AE3F9

    RECT r1, r2;
    src->vt+0x2C(&r1);                            // 0x007AE402  GetRect(out)
    dst->vt+0x2C(&r2);                            // 0x007AE40E  fetched and NEVER USED  (note)

    // 0x007AE423..0x007AE43C — all four reads are from r1 (the SOURCE)
    int w = r1.right  - r1.left;
    int h = r1.bottom - r1.top;
    if (!dst->vt+0x0C(w + 2, h + 2, {9, 0x20}))   // 0x007AE443  Init(w+2, h+2, fmt)
    {
        (*ppDst)->Release();                      // 0x007AE44E — *ppDst is NOT nulled  Note: DANGLING
        return false;
    }

    if (!src->vt+0x18(0x8040)) return true;       // 0x007AE463  Lock(0x8040)
    if ( dst->vt+0x18(0x8040)) {                  // 0x007AE477  Lock(0x8040)
        sub_7AE160(dst->GetBits(),  dst->GetPitch(),      // args 1,2   vt+0x88, vt+0x8C
                   src->GetBits(),  src->GetPitch(),      // args 3,4
                   dst->GetWidth(), dst->GetHeight(),     // args 5,6   vt+0x24, vt+0x28
                   src->GetWidth(), src->GetHeight(),     // args 7,8
                   dx, dy);                               // args 9,10  (trailing doubles)
        dst->vt+0x1C(0x8040);                     // 0x007AE4ED  Unlock
    }
    src->vt+0x1C(0x8040);                         // 0x007AE4F9  Unlock
    return true;
}
```
The `+2` is literal bytes: `0x007AE439 83c002  add eax,2` / `0x007AE43C 83c102  add ecx,2`.

**FIELDS** — none (no `this`).

**VTABLE CALLS** (all on the tile-buffer class, vtable `0x00AC1400` — see Appendix A)
| slot | target VA | meaning |
|---|---|---|
| `vt+0x0C` (on gfx) | *service* | `CreateBitmap(IGZBitmap** out) -> bool` |
| `vt+0x0C` | `0x008269B0` | `Init(w, h, {fmt,bpp}) -> bool` |
| `vt+0x18` | `0x00826AA0` | `Lock(flags) -> bool` |
| `vt+0x1C` | `0x00826490` | `Unlock(flags)` |
| `vt+0x24` | `0x00808620` | `GetWidth()  -> [this+0x1C]` |
| `vt+0x28` | `0x004ED900` | `GetHeight() -> [this+0x20]` |
| `vt+0x2C` | `0x008268D0` | `GetRect(RECT* out)` (copies 4 dwords from `[this+0x14]`) |
| `vt+0x88` | `0x008265C0` | `GetBits()  -> [this+0x3C]` |
| `vt+0x8C` | `0x0068D1B0` | `GetPitch() -> [this+0x40]` |

Because `vt+0x28` is `mov eax,[ecx+0x20]; ret` (**no** `ret N`), the two doubles parked at
`[esp]`/`[esp+8]` by `sub esp,0x10` survive the intervening vtable calls and land as the trailing
args of `sub_7AE160`. The `add esp,0x30` at `0x007AE4E3` (= `0x10` doubles + 8 pushes) proves it.

**CALLERS** — `sub_7AE510` ×4 (`0x007AE5B9`, `0x007AE5EA`, `0x007AE65D`, `0x007AE68E`).

Unsure: the purpose of the unused `dst->GetRect(&r2)` at `0x007AE40E`. Dead code, most likely.

---

## 2. `sub_7AE510`
`sub_7AE510  (0x7AE510..0x7AE7B0, 672 bytes)` — **the most load-bearing function in this slice.**

**PURPOSE** — Rebuild one region item's drawable state: sub-pixel-shift its four source bitmaps,
**create the composite buffer sized from the (already shifted) source**, then build the three
alpha/edge run-lists and the corner pair.

**CALLING CONVENTION** — `__thiscall`, `ret 4`.
```c
void __thiscall sub_7AE510(cSC4WinRegionScreen* this /*ecx*/, Item* item /*[ebp+8]*/);
```

**PSEUDO-C**
```c
void sub_7AE510(RegionScreen* this, Item* it)
{
    IGZBitmap* old1C = it->img1C;  if (old1C) old1C->AddRef();   // 0x007AE525
    IGZBitmap* old20 = it->img20;  if (old20) old20->AddRef();   // 0x007AE535

    // ---- fractional part of the item's precomputed SCREEN POSITION -------------
    double fx = 1.0 - (          (double)it->posX  - floor((double)it->posX) );  // 0x007AE548..
    double fy = 1.0 - (          (double)it->posY  - floor((double)it->posY) );
    //  bytes: fld [ebx+0x10] / call 0x9EFF60 (floor) / fsubr [esp+..] / fsubr qword [0xA80AB0]
    //  [0xA80AB0] = 1.0 (00 00 00 00 00 00 f0 3f)

    if (it->img20) { it->img20 = NULL; old->Release(); }
    sub_7AE3D0(old20, &it->img20, fx, fy);                        // 0x007AE5B9
    if (it->img1C) { it->img1C = NULL; old->Release(); }
    sub_7AE3D0(old1C, &it->img1C, fx, fy);                        // 0x007AE5EA

    if (it->img24 && it->img28) {                                 // 0x007AE5FE / 0x007AE60C
        AddRef both;
        it->img24 = NULL; release; sub_7AE3D0(old24, &it->img24, fx, fy);  // 0x007AE65D
        it->img28 = NULL; release; sub_7AE3D0(old28, &it->img28, fx, fy);  // 0x007AE68E
        release old28; release old24;
    }

    // ---- THE COMPOSITE --------------------------------------------------------
    cIGZGraphicSystem* gfx = this->[0x154];                       // 0x007AE6B2  mov esi,[ecx+0x154]
    if (it->composite) { it->composite = NULL; release; }         // 0x007AE6C2
    if (gfx->vt+0x0C(&it->composite))                             // 0x007AE6D2  CreateBitmap
    {
        RECT* r = it->img1C->vt+0x30();                           // 0x007AE6DE  GetRect() -> &[img+0x14]
        int w = r->right  - r->left;                              //   ( = shifted source width  )
        int h = r->bottom - r->top;                               //   ( = shifted source height )
        if (!it->composite->vt+0x0C(w, h, {9, 0x20}))             // 0x007AE706  Init(w,h,fmt)
            { it->composite = NULL; release; }                    // 0x007AE713  (SAFE: nulled)
    }

    sub_7ABCD0(it->img1C, it->img20);                             // 0x007AE726  (slice 3)
    // three run-list builders — sub_7AD400 is __usercall: ESI = out vector
    esi = &it->vec44;  sub_7AD400(it->img20, 0,    0);            // 0x007AE739
    esi = &it->vec5C;  sub_7AD400(it->img20, 8,    1);            // 0x007AE748
    esi = &it->vec50;  sub_7AD400(it->img20, 0x10, 1);            // 0x007AE757
    if (it->img24 && it->img28) sub_7ABCD0(it->img24, it->img28); // 0x007AE76F
    eax = it->img20;                                              // 0x007AE777 (passed in EAX unsure)
    sub_7AA6A0(&it->f68, &it->f6C);                               // 0x007AE781

    release old20; release old1C;
}
```

**FIELDS**
| offset | R/W | meaning |
|---|---|---|
| `this+0x154` | R | `cIGZGraphicSystem*` (the bitmap factory) — **note: NOT `+0x158`** |
| `item+0x10` | R | float, precomputed screen X |
| `item+0x14` | R | float, precomputed screen Y |
| `item+0x1C` | R/W | source thumbnail bitmap → replaced by its `+2` shifted copy |
| `item+0x20` | R/W | 2nd bitmap (mask/alpha source) → replaced by its `+2` shifted copy |
| `item+0x24` | R/W | 3rd bitmap (optional pair) |
| `item+0x28` | R/W | 4th bitmap (optional pair) |
| `item+0x2C` | W | **composite buffer** — created here |
| `item+0x44` | W | run-list vector (`sub_7AD400(img20, 0, 0)`) |
| `item+0x50` | W | run-list vector (`sub_7AD400(img20, 0x10, 1)`) |
| `item+0x5C` | W | run-list vector (`sub_7AD400(img20, 8, 1)`) |
| `item+0x68`, `+0x6C` | R/W | passed as a pair to `sub_7AA6A0` |

**CONSTANTS** — `[0xA80AB0] = 1.0` (double). Format struct `{9, 0x20}` built inline at
`0x007AE6E8`/`0x007AE6EE`.

**CALLERS** — `sub_7AFAA0` @ `0x007B00FA` (the "establish city" UI path), `sub_7B13C0` @ `0x007B185B`.

### Note: CORRECTION to GROUND TRUTH
> *"`sub_7AE510` creates the composite: at `0x007AE6D9` it reads the SOURCE's rect and at `0x007AE706`
> calls `Init(w,h,{9,0x20})` — so the composite is sized verbatim from the source bitmap."*

The addresses are right, but **by the time `0x007AE6D9` runs, `item+0x1C` is no longer the original
source** — it was replaced at `0x007AE5EA` by `sub_7AE3D0`, which builds a bitmap **2 px wider and
2 px taller**. So:

```
composite size  ==  originalSource + (2, 2)
```

Any patch that wants a larger composite must therefore change *either* `sub_7AE3D0`'s `+2`
(`0x007AE439` / `0x007AE43C`), *or* the `w`/`h` that reach `0x007AE706` — and must **not** simply
re-`Init` the finished composite (see Appendix B).

---

## 3. `sub_7AE7B0`
`sub_7AE7B0  (0x7AE7B0..0x7AE8D0, 288 bytes)`

**PURPOSE** — Item copy-constructor. Confirms the whole item layout in one place.

**CONVENTION** — `__thiscall`, `ret 4`, returns `this` in EAX.
`Item* __thiscall sub_7AE7B0(Item* this /*ecx*/, const Item* src /*[esp+0x14]*/)`

```c
this[0x00..0x14] = src[0x00..0x14];        // 6 dwords, memberwise
this[0x18]       = src[0x18];              // BYTE (size class)
for (o in {0x1C,0x20,0x24,0x28,0x2C,0x30}) { this[o] = src[o]; if (this[o]) AddRef(); }
this[0x34]       = src[0x34];              // BYTE (built flag)
sub_462F00(&this[0x38], &src[0x38]);       // 0x007AE849  vector<dword> copy-assign
sub_462F00(&this[0x44], &src[0x44]);       // 0x007AE852
sub_462F00(&this[0x50], &src[0x50]);       // 0x007AE85B
sub_462F00(&this[0x5C], &src[0x5C]);       // 0x007AE86A
this[0x68] = src[0x68];  this[0x6C] = src[0x6C];
this[0x70] = new list_head(12 bytes, self-linked);  sub_6C6CA0(...)   // std::list splice-copy
sub_624D60(&this[0x74], &src[0x74]);       // 0x007AE8B9
return this;
```

**NOTE on the vectors** — `sub_462F00` at `0x00462F12` does `sar ecx,2`, i.e. **element size 4 bytes**.
So `item+0x38 / +0x44 / +0x50 / +0x5C` are each a `std::vector<uint32>` (`{begin,end,cap}` = 0xC bytes).
Ground truth calls `+0x38` "a packed uint16 alpha run-list" — that is compatible if two `uint16`s are
packed per element, but the *container* is 4-byte-element. Note: Flagged, not contradicted.

Layout implied: `0x74` + `0xC` (the `sub_624D60` member) = `0x80` — matches the confirmed stride.

**CALLERS** — `sub_7AED60` @ `0x007AED7A`, `sub_7AEDA0` @ `0x007AEDBC`,
`sub_7B0E60` @ `0x007B0ED1`, `sub_7B13C0` @ `0x007B1523`.

---

## 4. `sub_7AE8D0`
`sub_7AE8D0  (0x7AE8D0..0x7AE9B0, 224 bytes)`

**PURPOSE** — MSVC `std::_Sort` (introsort) recursion. **Element size 12 bytes**, not `0x80`.
The magic `0x2AAAAAAB` + `sar edx,1` at `0x007AE8E0`..`0x007AE8E7` is the classic `/12`.

**CONVENTION** — `__cdecl`, 5 args:
`void __cdecl sub_7AE8D0(T* first, T* last, int /*unused, always 0*/, int ideal, Pred comp)`

```c
while ((last - first)/12 > 16) {                    // 0x007AE8F0 cmp eax,0x10
    if (ideal-- == 0) { sub_7ADE50(first, last, last, 0); return; }   // heap sort fallback
    T* mid = sub_7AA920(first, first + 12*(((n)/2)),  last-12, comp); // _Median
    T* cut = sub_7AD1F0(first, last, *mid, comp);                     // _Unguarded_partition
    sub_7AE8D0(cut, last, 0, ideal, comp);          // 0x007AE96A recurse RIGHT
    last = cut;                                     // iterate LEFT
}
```
**CALLERS** — itself (`0x007AE96A`), `sub_7AED00` @ `0x007AED46`.

The 12-byte element is `{ int a; int b; int sizeLog; }` — `sub_7AA920` (slice 3) computes
`(1<<a.size) - (1<<b.size) - b.y + a.y - b.x + a.x`, i.e. an **isometric painter's-order key**.

---

## 5. `sub_7AE9B0`
`sub_7AE9B0  (0x7AE9B0..0x7AEA00, 80 bytes)`

**PURPOSE** — `std::copy` over items, stride `0x80` (`0x007AE9BB sar eax,7`), using the item
**assignment operator** `sub_7ADFA0` (slice 3 — it has the pointer-equality guard at `0x007ADFD8`
that a copy-ctor would not need).

`__cdecl Item* sub_7AE9B0(Item* first /*[esp+4]*/, Item* last /*[esp+8]*/, Item* dest /*[esp+0xC]*/, void* /*[esp+0x10]*/)`
returns `dest + n*0x80`; returns `[esp+0x10]` when `n <= 0`.

**CALLERS** — `sub_7B0BB0` @ `0x007B0BCB`.

---

## 6. `sub_7AEA00`
`sub_7AEA00  (0x7AEA00..0x7AEC00, 512 bytes)` — **the city-size law lives here.**

**PURPOSE** — `GetOrCreateCity(item, bCreate)`: look the city record up in the region by the item's
cell coordinates; if absent and `bCreate`, allocate a fresh `0x1A0`-byte city record named
`"New City"` sized `(1<<item[0x18]) × (1<<item[0x18])` **region cells**, add it to the region, and
return it.

**CONVENTION** — `__stdcall`-ish: `ret 8`, ECX untouched (callers load ECX for the *next* call).
```c
cSC4City* __stdcall sub_7AEA00(Item* it /*[esp+0x4C]→ebp*/, bool bCreate /*[esp+0x50]*/);
```

**PSEUDO-C**
```c
RegionMgr* mgr    = (*(void**)0xB43C94)->vt+0x88();     // 0x007AEA0E
Region*    region = mgr->vt+0x20();                     // 0x007AEA1A  GetCurrentRegion

cSC4City* c = region->vt+0x2C(it->cellX /*+0x08*/, it->cellY /*+0x0C*/);   // 0x007AEA2F
if (c)        return c;
if (!bCreate) return c;                                 // 0x007AEA3E

// build "<mgrPath><regionPath>\"  (0x40AE00 = string ctor, 0x90F06C = append, then '\\')
std::string path = mgr->vt+0x14();  path += region->vt+0x14();  path += '\\';

cSC4City* nc = (cSC4City*)operator new(0x1A0);          // 0x007AEABD push 0x1A0 / call 0x5E55E0
sub_4AC040(nc);                                         // ctor
nc->AddRef(); nc->AddRef(); nc->vt+0x0C();
int dim = 1 << it->sizeClass;                           // 0x007AEAF9..0x007AEAFE  mov eax,1 / shl eax,cl
nc->vt+0x20(dim, dim);                                  // 0x007AEB04  SetSizeInCells(dim, dim)
nc->vt+0x18(it->cellX, it->cellY, 0);                   // 0x007AEB15  SetPosition
nc->vt+0x88( <string "New City" @0xAB91BC> );           // 0x007AEB90  SetName
region->vt+0x30(nc);                                    // 0x007AEB9B  AddCity
nc->Release();
return region->vt+0x2C(it->cellX, it->cellY);           // 0x007AEBB1  re-lookup and return
```

**FIELDS** — `item+0x08` (cell X), `item+0x0C` (cell Y), `item+0x18` (size class BYTE).

**CONSTANTS**
* `[0xB43C94]` — the SC4 master service (see also §11, §12, §14).
* `0xAB91BC` = `"New City"`.
* `0x6A231EAA` / `0xAA738C4E` — TGI group/instance pair built at `0x007AEB7F` (`sub_603040`) for the
  fresh city's persist record.
* `0xA80810` — the shared empty-`std::string` representation.

### KEY DERIVED FACT (cross-checked in §11)
`item+0x18` is a **log2 size class in {0,1,2}**:

| `item[0x18]` | cells (`1<<b`) | game tiles (`0x100 >> (2-b)`) | screen px (`128 × cells`) |
|---|---|---|---|
| 0 = small  | 1×1 | 64×64   | 128 |
| 1 = medium | 2×2 | 128×128 | 256 |
| 2 = large  | 4×4 | 256×256 | 512 |

The tile-count column is measured at `0x007AF14C`..`0x007AF168`:
`mov ecx,2 / mov edi,0x100 / sub ecx,edx / sar edi,cl`.

**CALLERS** — `sub_7AEDD0` @ `0x007AF295`, `sub_7AF4B0` @ `0x007AF5D5`,
`sub_7AFAA0` @ `0x007AFDEC`, `0x007AFE4C`, `0x007B00DA`.

---

## 7. `sub_7AEC00`
`sub_7AEC00  (0x7AEC00..0x7AED00, 256 bytes)`

**PURPOSE** — Walk the item array and accumulate `sum(city->vt+0x28())` (a byte size / footprint),
then hand the total to a reporting service. Diagnostics, not rendering.

**CONVENTION** — `__thiscall`, no stack args, no `ret N`.

```c
void __thiscall sub_7AEC00(cSC4WinRegionScreen* this)
{
    int total = 0;
    for (Item* it = this->[0x118]; it != this->[0x11C]; it += 0x80) {     // 0x007AEC19 / 0x007AEC58
        RegionMgr* m = (*(void**)0xB43C94)->vt+0x88();
        Region*    r = m->vt+0x20();
        void*      c = r->vt+0x2C(it->cellX, it->cellY);                  // 0x007AEC42
        if (c) total += (*(void**)c)->vt+0x28();                          // 0x007AEC4F (note double deref)
    }
    Svc* s = sub_913D7A()->vt+0x98(0);                                    // 0x007AEC6C
    std::string msg;                                                       // 0xA80810 empty-rep
    s->vt+0x48((int64)total, &msg);                                        // 0x007AECBD
    this->vt+0x8C(0xC9E41918)->vt+0x128(&msg);                             // 0x007AECC9 / 0x007AECD8
}
```
**FIELDS** — `this+0x118` / `this+0x11C` (item array begin/end), stride `0x80` confirmed again.
**CALLERS** — `sub_7AFAA0` @ `0x007B0114`, `sub_7B0470` @ `0x007B08B5`.
Unsure: `0xC9E41918` is not in the `.data` class-name registry (`0xB05000..0xB0B000`).

---

## 8. `sub_7AED00`
`sub_7AED00  (0x7AED00..0x7AED60, 96 bytes)`

**PURPOSE** — `std::sort(first, last, pred)` for the **12-byte** draw-order records.

`__cdecl void sub_7AED00(T* first, T* last, Pred comp)` (caller cleans; `n = (last-first)/12`).
```c
if (first == last) return;
int lg = 0; for (int n = (last-first)/12; n != 1; n >>= 1) ++lg;   // 0x007AED30 loop
sub_7AE8D0(first, last, 0, lg*2, comp);   // 0x007AED46  introsort
sub_7ADF40(first, last, comp);            // 0x007AED4E  final insertion sort
```
**CALLERS** — `sub_7B13C0` @ `0x007B1423` (the item-array builder, slice 6).

---

## 9. `sub_7AED60`
`sub_7AED60  (0x7AED60..0x7AEDA0, 64 bytes)`

`std::uninitialized_copy` over items. `__cdecl Item* (Item* first, Item* last, Item* dest, void*)`;
loops `dest->sub_7AE7B0(src)` and advances both by `0x80`; returns `dest`.
**CALLERS** — `sub_7B0E60` @ `0x007B0EB7` and `0x007B0F0B`.

---

## 10. `sub_7AEDA0`
`sub_7AEDA0  (0x7AEDA0..0x7AEDD0, 48 bytes)`

`std::uninitialized_fill_n` over items. `__cdecl Item* (Item* first, unsigned n, const Item* val)`;
constructs `n` copies of `*val` at stride `0x80`; returns the end pointer.
Note `jbe` at `0x007AEDAB` — `n` is treated as **unsigned**.
**CALLERS** — `sub_7B0E60` @ `0x007B0EEA`.

---

## 11. `sub_7AEDD0`
`sub_7AEDD0  (0x7AEDD0..0x7AF4B0, 1760 bytes)`

**PURPOSE** — `kCommandID_RegionBitmapLoad` (`0x6A9757C2`). Loads the region's terrain source,
**validates its pixel size against the item grid**, then for every city bakes an `N×N` 8-bit
height bitmap out of the region-wide height field and installs it as that city's terrain thumbnail.

**CONVENTION** — `__thiscall`, no stack args.
`void __thiscall sub_7AEDD0(cSC4WinRegionScreen* this /*ecx→ebx*/)`

**PSEUDO-C** (abbreviated; the string/refcount churn is elided)
```c
RegionMgr* m = (*(void**)0xB43C94)->vt+0x88();
Region*    R = m->vt+0x2C(this->[0x1A4]);              // 0x007AEDF9 — [this+0x1A4] = region key

// ---- progress dialog ---------------------------------------------------------
void* dlg = new(0xF0) ...; sub_79D810(dlg);            // 0x007AEE4F
dlg->vt+0x110(0x10000, 1);  dlg->vt+0x110(0x100, 1);   // 0x007AEE70 / 0x007AEE81
centre dlg over this->[0x04] using vt+0xA4 (X) and vt+0xA8 (Y):
    dx = (parent.vt+0xA4() - dlg.vt+0xA4()) / 2;       // 0x007AEEAB..0x007AEEB6 (sub, cdq, sub, sar 1)
    dy = (parent.vt+0xA8() - dlg.vt+0xA8()) / 2;
    dlg->vt+0xE0(dx, dy);                              // 0x007AEEDD  Move
(*(void**)0xB43CE0)->vt+0x28(dlg, 1);                  // 0x007AEEF0  show + modal veil
...
(*(void**)0xB43CE0)->vt+0x18(dlg);                     // 0x007AEF31  hide

// ---- expected region-bitmap size ---------------------------------------------
int maxX = 0, maxY = 0;
for (Item* it : items[0x118..0x11C]) {                 // 0x007AF000 loop
    maxX = max(maxX, it->[0x00] + 1);
    maxY = max(maxY, it->[0x04] + 1);
}
int expW = (maxX << 6) + 1;                            // 0x007AF069 shl ecx,6 / inc ecx
int expH = (maxY << 6) + 1;                            // 0x007AF078 shl eax,6 / inc eax
RECT* b = terrain->vt+0x30();                          //  (the region height bitmap)
if (b->w != expW || b->h != expH) goto ERROR;          // 0x007AF07C / 0x007AF090
    // ERROR path 0x007AF3B8: formats 0xAB91C8
    //   "Region bitmap size is incorrect -- %dx%d, should be %dx%d"
    //   with title 0xAB9204 "Region generation error"

// ---- per-item bake -----------------------------------------------------------
for (Item* it : items) {                               // 0x007AF130 loop
    int dim = 0x100 >> (2 - it->sizeClass);            // 0x007AF14C..0x007AF168  → 64 / 128 / 256
    IGZBitmap* img = NULL;
    if ((*(void**)0xB43C9C)->vt+0x0C(&img)             // 0x007AF177  bitmap factory
     && img->vt+0x0C(dim, dim, {2, 8}))                // 0x007AF19C  Init(dim, dim, fmt{2,8})
    {
        if (terrain->vt+0x18(0x800) && img->vt+0x18(0x8080)) {   // Lock src / Lock dst
            int ox = it->cellX << 6;                   // 0x007AF1D3  shl eax,6   (64 tiles / cell)
            int oy = it->cellY << 6;                   // 0x007AF1DE
            for (int y = 0; y < dim; ++y)
              for (int x = 0; x < dim; ++x) {
                  int v = terrain->vt+0x54(ox + y, oy + x);      // 0x007AF20C  GetHeight
                  img    ->vt+0x58(y, x, v);                     // 0x007AF216  SetPixel
              }
            img->vt+0x1C(0x8080);  terrain->vt+0x1C(0x800);
        }
        cSC4City* city = sub_7AEA00(it, /*bCreate*/1); // 0x007AF295
        ...->vt+0x9C() slot at [+0x200] swapped to hold `img`   // 0x007AF281 / 0x007AF2AF
        ...->vt+0x18(city); vt+0x94(); vt+0x3C(); vt+0x38();     // write the .sc4 / save
    }
}
```

**FIELDS**
| offset | meaning |
|---|---|
| `this+0x04` | the parent/host window (used for the progress-dialog centring) |
| `this+0x118` / `+0x11C` | item array begin/end |
| `this+0x1A4` | region key/handle handed to `RegionMgr::vt+0x2C` |

**CONSTANTS / GLOBALS**
* `[0xB43C94]` master service, `vt+0x88` → RegionMgr, `vt+0x2C(key)` → Region.
* `[0xB43C9C]` a bitmap factory (`vt+0x0C(&out)`).
* `[0xB43CD0]` an object AddRef'd for the duration.
* `[0xB43CE0]` the show/hide + modal-veil manager (`vt+0x28(win,bool)` / `vt+0x18(win)`).
* `0xAB91C8` `"Region bitmap size is incorrect -- %dx%d, should be %dx%d"`
* `0xAB9204` `"Region generation error"`
* `0xA80810` empty-`std::string` rep.

**CALLERS** — `sub_7AF720` @ `0x007AFA89` (command `kCommandID_RegionBitmapLoad`).

### NEW FACTS THIS ADDS TO THE GROUND TRUTH
1. **`item+0x00` / `item+0x04`** are the region-cell extent used for the `config.bmp` sanity check:
   `expectedPixels = (maxCell+1)*64 + 1` in each axis — i.e. **64 game tiles per region cell**, and
   the terrain bitmap carries the usual `+1` fence-post row/column.
2. **`item+0x08` / `item+0x0C`** are the city's origin in region cells (`<<6` → game tiles).
3. The per-city terrain thumbnail is `dim × dim` at `{2, 8}` = 8-bit, `dim ∈ {64,128,256}`.
   Note: Note the sampling loop indexes `terrain(ox+y, oy+x)` and writes `img(y, x)` — the two loop
   counters are used in the same order on both sides, so no transpose; but the outer counter is
   `ebp` and the inner is `esi`, and `ox` pairs with `ebp` while `oy` pairs with `esi`.

---

## 12. `sub_7AF4B0`
`sub_7AF4B0  (0x7AF4B0..0x7AF720, 624 bytes)`

**PURPOSE** — "Load city": scan the item array for either (a) a city whose name matches, or
(b) the first **unestablished** plot whose area matches the requested size, then enter it.

**CONVENTION** — `__thiscall`, `ret 0x10` (4 dword args).
```c
bool __thiscall sub_7AF4B0(cSC4WinRegionScreen* this /*ecx*/,
                           std::string* name  /*[esp+0x44]*/,   // {?, begin@+4, end@+8}
                           int          size  /*[esp+0x48]*/,   // 0=small 1=medium 2=large, other=any
                           std::string* out   /*[esp+0x4C]*/,   // receives the chosen city's name
                           bool         flag  /*[esp+0x50]*/);
```

```c
bool nameEmpty = (name->end == name->begin);          // 0x007AF4BE  sete
int  wantArea  = (size==0) ? 1 : (size==1) ? 4 : (size==2) ? 0x10 : 0;   // 0x007AF4D8..0x007AF4F8
Region* R = (*(void**)0xB43C94)->vt+0x88()->vt+0x2C(this->[0x1A4]);

for (Item* it : this->[0x118..0x11C]) {
    void* rec = R->vt+0x2C(it->cellX, it->cellY);      // 0x007AF55C
    bool established = rec ? (*(void**)rec)->vt+0xAC() : false;   // 0x007AF56A

    if (nameEmpty) {
        if (established) continue;                     // 0x007AF57C
        int area;
        if (rec && !flag) { rec->vt+0x1C(&w,&h); area = w*h; }    // 0x007AF5A3 / 0x007AF5AA
        else              { int d = 1 << it->sizeClass; area = d*d; }  // 0x007AF5B1..0x007AF5BB
        if (wantArea && wantArea != area) continue;    // 0x007AF5C6
        cSC4City* c = sub_7AEA00(it, 1);               // 0x007AF5D5  create if needed
        if (this->sub_7ADC20(c)) {                     // 0x007AF5E1  enter the city
            (*(void**)it)->vt+0x84(out);               // 0x007AF6C0  hand back its name
            return true;
        }
    } else {
        if (!established) continue;                    // 0x007AF5F9
        std::string s; rec->vt+0x84(&s);               // 0x007AF63C  GetName
        if (s == *name) {                              // 0x007AF64A..0x007AF666  repe cmpsb
            if (this->sub_7ADC20(rec)) {               // 0x007AF66F
                if (out != &s) sub_408A70(s.begin, s.end, out);   // 0x007AF6F0
                return true;
            }
        }
    }
}
return false;
```
**FIELDS** — `this+0x118`/`+0x11C` (items), `this+0x1A4` (region key).
**CALLERS** — `sub_7AF720` @ `0x007AF8A2`.
Unsure: the exact semantics of `flag` — it only decides whether the *record's own* stored size or
the *item's* size class is used for the area test.

---

## 13. `sub_7AF720`
`sub_7AF720  (0x7AF720..0x7AFAA0, 896 bytes)` — **the pan/scroll levers.**

**PURPOSE** — `cIGZCommandServer` command handler for the region screen (a switch on a command id).

**CONVENTION** — `__thiscall`, `ret 0xC` (3 dword args).
```c
bool __thiscall sub_7AF720(cSC4WinRegionScreen* this /*ecx→ebp*/,
                           uint32 cmdID    /*[esp+0x04] read pre-prologue*/,
                           void*  argsIn   /*[esp+0x38]*/,
                           void*  argsOut  /*[esp+0x3C]*/);
```
All paths `xor al,al` — the handler always reports **false** (not-consumed) except by side effect.

### The scroll block (verbatim byte evidence)
```
0x007AF76A  8bad74010000   mov ebp, [ebp+0x174]        ; the scroller object
0x007AF770  d98504010000   fld dword [ebp+0x104]       ; the SPEED magnitude
0x007AF777  d80d5410a800   fmul dword [0xA81054]       ; [0xA81054] = 0.0f
0x007AF77F  d99d00010000   fstp dword [ebp+0x100]      ; Y velocity := 0
```
| command id | name (from the exe's own registry) | effect |
|---|---|---|
| `0x2A94826B` | `kCommandID_ScrollDownStop`  | `[0x174]+0x100 = [0x174]+0x104 * 0.0f` |
| `0x2A948272` | `kCommandID_ScrollUpStop`    | `[0x174]+0x100 = [0x174]+0x104 * 0.0f` |
| `0x2A94826E` | `kCommandID_ScrollRightStop` | `[0x174]+0x0FC = [0x174]+0x104 * 0.0f` |
| `0x2A948275` | `kCommandID_ScrollLeftStop`  | `[0x174]+0x0FC = [0x174]+0x104 * 0.0f` |
| `0x6A935CD8` | `kCommandID_ScrollLeft`      | `[0x174]+0x0FC = [0x174]+0x104 * -1.0f` (`[0xA8FE78]`) |
| `0x6A935CDD` | `kCommandID_ScrollUp`        | `[0x174]+0x100 = [0x174]+0x104 * -1.0f` |
| `0x6A935CE0` | `kCommandID_ScrollRight`     | `[0x174]+0x0FC = [0x174]+0x104` (plain copy) |
| `0x6A935CE2` | `kCommandID_ScrollDown`      | `[0x174]+0x100 = [0x174]+0x104` (plain copy) |

So `[this+0x174]` is a **scroller/auto-pan object** with
`+0xFC = X velocity (float)`, `+0x100 = Y velocity (float)`, `+0x104 = speed magnitude (float)`.
`[0xA81054] = 0.0f`, `[0xA8FE78] = -1.0f` — both are shared read-only float literals with
1973 and 65 data references respectively, so **neither may be patched in place**.

Note: `[this+0x174]` is **not** the `+0x164` camera named in the ground truth. Separate object.

### The rest of the switch
| command id | name | handler |
|---|---|---|
| `0x6A935CF1` | `kCommandID_Cancel` | `this->[0xE0]` (the region VIEW) → `sub_7B5DB0()` @ `0x007AF9AC` |
| `0x6A935E3C` | `kCommandID_QuitGame` | `sub_7AC270`, `sub_7AC2D0`, then `[0xB43C94]->vt+0x2C(!bl)` |
| `0x6AA9FE51` | `kCommandID_SetExpandedToolTips` | writes/toggles `BYTE [ [0xB43CD8] + 0xF0A ]` |
| `0x6A9757C2` | `kCommandID_RegionBitmapLoad` | `sub_7AEDD0(this)` @ `0x007AFA89` |
| `0x0BB3C277` | `kCommandID_LoadRegion` | `sub_7ADAC0(this, &str)`; on failure `argsOut->vt+0x28(2)` |
| `0x0BB2747D` | `kCommandID_LoadCity` | parse the size parameter, then `sub_7AF4B0` @ `0x007AF8A2` |

**`kCommandID_LoadCity` parameter parsing** (`0x007AF803`..`0x007AF87C`) — each is
`argsIn->vt+0x2C(1, <name>, 0)`:
| string VA | text | size code passed to `sub_7AF4B0` |
|---|---|---|
| `0xAB9228` | `"small"`  | 0 |
| `0xA82BB8` | `"medium"` | 1 |
| `0xAB9220` | `"large"`  | 2 |
| `0xAB921C` | `"any"`    | 3 (⇒ `wantArea = 0`, no filter) |
| — | none of the above | `argsIn->vt+0x14(1)->vt+0x60()` (a numeric parameter) |

plus `argsIn->vt+0x2C(2, 0xA923FC /* "empty" */, 0)` → the `flag` argument.

**CALLERS** — `sub_7B0AF0` @ `0x007B0B38`.

---

## 14. `sub_7AFAA0`
`sub_7AFAA0  (0x7AFAA0..0x7B0470, 2512 bytes)`

**PURPOSE** — The region screen's UI/window message handler: a switch on the message type, then on
the originating control id.

**CONVENTION** — `__thiscall`, `ret 8`.
```c
bool __thiscall sub_7AFAA0(cSC4WinRegionScreen* this /*ecx→esi*/,
                           uint32 msgType /*[esp+0x04] read pre-prologue*/,
                           uint32 ctrlID  /*[esp+0x9C]*/);
```
Two message types only: `0x287259F7` and `0x287259F6`. **Every** path returns `true` (`mov al,1`);
the default at `0x007B0456` also returns `true`.

### `msgType == 0x287259F7` (a checkbox/toggle notification)
Only handles `ctrlID == 0xEA5A96E6`:
```c
IGZWin* w; if (this->vt+0x94(0xEA5A96E6, 0x8810, &w)) {   // 0x007AFAE7  GetChildAs(id, iid, &out)
    bool on = w->vt+0x28();                                // 0x007AFAF7  GetState
    sub_7B30D0(this->[0xE0], on);                          // 0x007AFB0B  push to the region VIEW
    (*(void**)0xB43C94)->vt+0x98()->[0xF04] = on;          // 0x007AFB1E  persist the pref
}
```
`0x8810` is the `cIGZWin`-family IID used for every `vt+0x94` lookup in this function.

### `msgType == 0x287259F6` (button click) — full control-id dispatch
| ctrlID | handler |
|---|---|
| `0x098F4F6C` | `new(0x20)` + `sub_791360` ctor → `sub_7913A0(obj)` (a modal dialog) |
| `0x098F4FBD` | `sub_7ABDF0(this, 0)` |
| `0x098F4FC3` | `sub_7ABDF0(this, 2)` |
| `0x09EBF2C8` | `sub_7ABDF0(this, 1)` |
| `0x0A5510A9` | `new(0x10)` + `sub_76AB30` ctor → `sub_76AB50(obj)` |
| `0x26C10A3E` | `sub_7AC270`, `sub_7AC2D0`, `[0xB43C94]->vt+0x2C(1)`, then child `0x26C10A3E`→`vt+0x24(0)` |
| `0x2A5B0000` | `sub_777FF0(this)` → index → select that region cell |
| `0x2A5B0001` | `sub_7780C0(this)` → index → `RegionMgr->vt+0x24(idx)`, `sub_7AC270`, `vt+0x30(0)` |
| `0x2A5B0002` | `sub_778130(this)`; if true `Region->vt+0x30(this->[0x1A4])`, `sub_7AC270`, `vt+0x30(0)` |
| `0x4A560000` | `sub_74C6E0(this->[0xE0])` → item; `sub_7AEA00(item,1)`; `sub_7ADC20`; else `sub_7AC110` |
| `0x4A560001` | `sub_7AC110(this)` |
| `0x4A560002` | **rename/retitle the selected city** — see below |
| `0x4A560003` | **establish the selected city** — see below |
| `0x4A779A09` / `0x4A779A1A` | `sub_603580(&k, 0x6A231EAA, 0x4A77A0B1 / 0x4A779D9D, 1)` → `sub_5FA810(&k,1)` |
| `0x4BB92C1F` | `this->[0x1FD] = 0`, then two `sub_9AFCFE` notifications (`0x0BB0F5E7`, `0x6BB92BCA`) |
| `0xEBB91356` | `this->[0x1FD] = 1`, same two notifications |
| `0x8A1DA655` | `sub_913C46()->vt+0x0C()`, then `sub_7B7530(this->[0x48], 1)` |
| `0xA98F4F88` | `new(0x80)` + `sub_4F2450` ctor → `sub_4F25F0(obj)` |
| `0xCA1DA670` | `sub_7BDD60(1,1,this->[0x48],0)` → `sub_7BDC90(obj,0)` → `sub_7B69E0(obj)` |
| `0xCA5CFEE2` | child `0xCA5CFEE2`→`vt+0x28()` → `this->[0x1A8]`; `sub_7AC110`; persist to `[…]+0xF05` |
| `0xABA290E1`, `0xCBA290EC`, `0xABA290F6` | **the 3-way radio group** — see below |

**`0x4A560003` — establish city** (`0x007B0099`):
```c
if (!sub_778220(this)) break;
Item* it = sub_74C6E0(this->[0xE0]);                        // the item under the cursor/selection
Region* R = RegionMgr->vt+0x2C(this->[0x1A4]);
cSC4City* c = sub_7AEA00(it, 1);                            // 0x007B00DA  create it
R->vt+0x38(&c);                                             // 0x007B00EC
sub_7ABB80(this, it);                                       // 0x007B00F2
sub_7AE510(this, it);                                       // 0x007B00FA  *** REBUILD THE TILE ***
sub_7B5430(this->[0xE0], it);                               // 0x007B0106  tell the view
sub_7AC110(this);                                           // 0x007B010D
sub_7AEC00(this);                                           // 0x007B0114  re-report memory
```
This is the **only** call site of `sub_7AE510` in this slice, and it is the "you just founded a
city, redraw its tile" path. The other one is `sub_7B13C0` (slice 6, the array builder).

**`0x4A560002` — rename** (`0x007AFE31`): reads `it->sizeClass` and uses it to index a table:
```
0x007AFE59  0fb64f18        movzx ecx, byte [edi+0x18]
0x007AFE5D  8b148d3092ab00  mov edx, [ecx*4 + 0xAB9230]
```
`[0xAB9230] = { 0x6A7A268A, 0xAA7A26BF, 0xAA7A26CE }` — one persist instance-id per city size
(small / medium / large), paired with group `0x6A231EAA`. Then `sub_78DFF0` picks a template,
`sub_778D80(this, dim, dim, …)` is called with `dim = 1 << it->sizeClass` (`0x007AFF2B`), and
finally `regionSvc->vt+0x40(city, name, it->cellX, it->cellY)` at `0x007AFF9B`.

**The 3-way radio group** (`0x007B0370`), table at `0xAB8B70`:
```
0xAB8B70: e1 90 a2 ab   ec 90 a2 cb   f6 90 a2 ab
        = { 0xABA290E1, 0xCBA290EC, 0xABA290F6 }
```
```c
for (int i = 0; i < 3; ++i) {                          // 0x007B03F2 cmp ebx,3
    bool sel = (ctrlID == kTable[i]);                  // 0x007B0380
    if (sel) { sub_7B30F0(this->[0xE0], i);            // 0x007B0399  set the view mode = i
               RegionMgr->vt+0x98()->[0xF06] = i; }    // 0x007B03AC  persist
    if (this->vt+0x94(kTable[i], 0x8810, &w)) w->vt+0x24(sel);   // set the radio state
}
```
So **`this->[0xE0]` (`cSC4WinRegionView`) has a 0/1/2 "view mode"** driven from these three
buttons and mirrored into a preferences byte at `+0xF06`.

**FIELDS**
| offset | meaning |
|---|---|
| `this+0x48` | passed to `sub_7B7530` / `sub_7BDD60` (a sub-panel or dialog owner) |
| `this+0xE0` | the `cSC4WinRegionView` — confirms ground truth |
| `this+0x118`/`+0x11C` | items (via the helpers it calls) |
| `this+0x1A4` | region key |
| `this+0x1A8` | a bool set from checkbox `0xCA5CFEE2`, mirrored to prefs `+0xF05` |
| `this+0x1FD` | a bool flag (0 / 1) written by `0x4BB92C1F` / `0xEBB91356` |

**CALLERS** — none found by `fn.py --callers` (it is reached through the vtable, slot unknown unsure).

---

## Appendix A — tile-buffer class (vtable `0x00AC1400`)

Resolved this pass by reading each slot's target. Consistent with, and extending, the ground truth.

| slot | target VA | signature / behaviour |
|---|---|---|
| `+0x0C` | `0x008269B0` | `bool Init(int w, int h, Fmt{a,b})`, `ret 0x10` — **refuses if already initialised** |
| `+0x10` | `0x00825CE0` | `bool Deinit()` — `vt+0xB0()` then `BYTE [this+8] = 0`, returns true |
| `+0x14` | `0x00825CE0` | same function as `+0x10` |
| `+0x18` | `0x00826AA0` | `bool Lock(uint flags)` — fails if `[this+0x3C]==0`; `if (flags & 0x8000) ++[this+0x30]`; `[this+0x44] \|= flags`; `++WORD [this+0x38]` |
| `+0x1C` | `0x00826490` | `bool Unlock(uint flags)` — `[this+0x44] &= ~flags`; `--WORD [this+0x38]` |
| `+0x20` | `0x008268B0` | `bool IsLocked()` — `WORD [this+0x38] != 0` |
| `+0x24` | `0x00808620` | `int GetWidth()  -> [this+0x1C]` |
| `+0x28` | `0x004ED900` | `int GetHeight() -> [this+0x20]` |
| `+0x2C` | `0x008268D0` | `void GetRect(RECT* out)` — copies 4 dwords from `[this+0x14]`, `ret 4` |
| `+0x30` | `0x008268C0` | `RECT* GetRect()` — `lea eax,[ecx+0x14]; ret` (returns the INTERNAL rect) |
| `+0x88` | `0x008265C0` | `void* GetBits()  -> [this+0x3C]` |
| `+0x8C` | `0x0068D1B0` | `int   GetPitch() -> [this+0x40]` |
| `+0xA8` | `0x00826350` | `bool AllocBits()` — calls `vt+0xAC`; on failure `[this+0x3C]=0`, return 0 |
| `+0xB0` | `0x00826370` | `bool FreeBits()` — `operator delete([this+0x3C])` via `0x5E5620`, `[this+0x3C]=0` |

### Field map implied by `Init` (`0x008269B0`)
```
[this+0x08]  BYTE  bInitialised          <-- the gate
[this+0x0C]  dword fmt.a  (= 9  for the tile buffers)
[this+0x10]  dword fmt.b  (= 0x20 bpp)
[this+0x14]  int   rect.left    := 0     (Init writes 0)
[this+0x18]  int   rect.top     := 0     (Init writes 0)
[this+0x1C]  int   rect.right   := width
[this+0x20]  int   rect.bottom  := height
[this+0x30]  int   dirty counter (incremented by Lock when flags & 0x8000)
[this+0x38]  WORD  lock count
[this+0x3C]  void* bits
[this+0x40]  int   pitch                 <-- NEW, was not in the ground truth
[this+0x44]  uint  current lock flags
```
Note `GetWidth`/`GetHeight` are literally `rect.right`/`rect.bottom` because `rect.left`/`top` are
forced to 0 by `Init`.

---

## Appendix B — why `Init(520,320)` returns 0 (SOLVED)

The measured failure in the ground truth —
*"calling vtable slot `+0x0C` of `0x00AC1400` as `Init(520,320,{9,0x20})` on an ALREADY-INITIALISED
260x160 composite returns 0 and leaves it 260x160. All 9 tiles, no exception."* —
is explained by the **first four instructions of `Init`**:

```
0x008269B0  56              push esi
0x008269B1  8bf1            mov  esi, ecx
0x008269B3  8a4608          mov  al,  byte [esi+8]     ; the "initialised" flag
0x008269B6  33d2            xor  edx, edx
0x008269B8  3ac2            cmp  al,  dl
0x008269BA  7541            jne  0x8269FD              ; --> xor al,al ; ret 0x10
```
`[this+0x08]` is the initialised flag, and the ground truth's own live head recorded `+0x08 = 1`.
`Init` bails **before touching anything**, which is exactly the observed "returns 0, no side effect,
no exception".

`Init` also refuses `w == 0` (`0x008269C0`) or `h == 0` (`0x008269C8`), and returns 0 if the
allocation (`vt+0xA8`) fails (`0x008269F0`).

### The correct resize sequence
```c
buf->vt+0x10();                       // 0x00825CE0 : FreeBits + [this+8] = 0
buf->vt+0x0C(newW, newH, {9, 0x20});  // 0x008269B0 : now succeeds
```
`vt+0x10` frees the pixel buffer through `operator delete` (`0x005E5620`) and nulls `[this+0x3C]`,
so **the old bits are gone** — anything already blitted into the composite is lost and must be
rebuilt (i.e. re-run `sub_7AE510`'s tail, or the `sub_7B3300` compositor).

Note: HAZARD, measured: if `Init` fails inside **`sub_7AE3D0`** (`0x007AE443`), the failure path at
`0x007AE44A` calls `Release()` on `*ppDst` but **does not null it** — `sub_7AE510` then goes on to
call `vt+0x30` on that freed pointer at `0x007AE6DE`. Do not engineer an `Init` failure there.
The composite's own failure path (`0x007AE70D`) *does* null the slot first and is safe.

---

## Appendix C — item struct (`0x80` bytes) — fields touched by this slice

| offset | type | evidence | meaning |
|---|---|---|---|
| `+0x00` | int | `0x007AF004` | region-cell extent X (used for the `config.bmp` size check) |
| `+0x04` | int | `0x007AF021` | region-cell extent Y |
| `+0x08` | int | `0x007AEA24`, `0x007AF1CF` | city origin, region cell X (`<<6` → game tiles) |
| `+0x0C` | int | `0x007AEA21`, `0x007AF1DA` | city origin, region cell Y |
| `+0x10` | float | `0x007AE548` | precomputed screen X |
| `+0x14` | float | `0x007AE552` | precomputed screen Y |
| `+0x18` | BYTE | `0x007AEAF4`, `0x007AF145`, `0x007AF5B1`, `0x007AFE59`, `0x007AFF21` | **size class 0/1/2** |
| `+0x1C` | ptr | `0x007AE525`, `0x007AE6D9` | source thumbnail bitmap (replaced in-place with the `+2` shifted copy) |
| `+0x20` | ptr | `0x007AE535`, `0x007AE739` | 2nd bitmap; the run-list builders read it |
| `+0x24` | ptr | `0x007AE5EF` | 3rd bitmap (optional; only used if `+0x28` is also non-null) |
| `+0x28` | ptr | `0x007AE604` | 4th bitmap |
| `+0x2C` | ptr | `0x007AE6C2` | **composite buffer** |
| `+0x30` | ptr | `0x007AE82D` (copy-ctor) | a 6th refcounted pointer — **not written anywhere in this slice** Note: |
| `+0x34` | BYTE | `0x007AE83C` | "built" flag |
| `+0x38` | vector\<dword\> | `0x007AE849` | 0xC bytes; not written in this slice |
| `+0x44` | vector\<dword\> | `0x007AE739` | run-list, `sub_7AD400(img20, 0, 0)` |
| `+0x50` | vector\<dword\> | `0x007AE757` | run-list, `sub_7AD400(img20, 0x10, 1)` |
| `+0x5C` | vector\<dword\> | `0x007AE748` | run-list, `sub_7AD400(img20, 8, 1)` |
| `+0x68` | dword | `0x007AE780` | passed as `&item[0x68]` to `sub_7AA6A0` |
| `+0x6C` | dword | `0x007AE77C` | passed as `&item[0x6C]` to `sub_7AA6A0` |
| `+0x70` | list head | `0x007AE87E`..`0x007AE8AD` | `std::list` (12-byte head) |
| `+0x74` | 0xC bytes | `0x007AE8B9` | copied by `sub_624D60`; ends the struct at `0x80` |

---

## Appendix D — constants, globals, strings

### Floats / doubles
| VA | value | used by |
|---|---|---|
| `0xA80AB0` | `1.0` (double) | `sub_7AE510` — `frac` complement |
| `0xA81054` | `0.0f` | `sub_7AF720` scroll-stop (1973 data refs — **do not patch**) |
| `0xA8FE78` | `-1.0f` | `sub_7AF720` scroll-negative (65 data refs — **do not patch**) |

### Strings
| VA | text |
|---|---|
| `0xAB91BC` | `"New City"` |
| `0xAB91C8` | `"Region bitmap size is incorrect -- %dx%d, should be %dx%d"` |
| `0xAB9204` | `"Region generation error"` |
| `0xAB921C` | `"any"` |
| `0xAB9220` | `"large"` |
| `0xAB9228` | `"small"` |
| `0xA82BB8` | `"medium"` |
| `0xA923FC` | `"empty"` |
| `0xA80810` | the shared empty-`std::string` representation |

### Tables
| VA | contents | meaning |
|---|---|---|
| `0xAB9230` | `0x6A7A268A, 0xAA7A26BF, 0xAA7A26CE` | city-template instance id per size class |
| `0xAB8B70` | `0xABA290E1, 0xCBA290EC, 0xABA290F6` | the 3 region-view-mode radio button ids |

### Globals
| VA | role (as used in this slice) |
|---|---|
| `[0xB43C94]` | master SC4 service. `vt+0x88`→RegionMgr, `vt+0x98`→prefs blob (`+0xF04/F05/F06`), `vt+0x2C(b)`, `vt+0x30(b)`, `vt+0x24(i)` |
| `[0xB43C9C]` | bitmap factory used by the terrain bake (`vt+0x0C(&out)`) |
| `[0xB43CD0]` | AddRef'd for the duration of `sub_7AEDD0` |
| `[0xB43CD8]` | prefs/settings blob; `+0xF0A` = expanded-tooltips flag |
| `[0xB43CE0]` | show/hide + modal-veil manager (`vt+0x28(win,bool)`, `vt+0x18(win)`) |

### Class / command ids resolved against the exe's own registry (`.data 0xB05000..0xB0B000`)
```
0xC416025C  kGZGraphicSystem_SystemServiceID   (the factory behind sub_913C1A)
0xEA659793  cSC4WinRegionScreen
0x2BA6BB97  cSC4WinRegionView
0x6A9757C2  kCommandID_RegionBitmapLoad
0x0BB2747D  kCommandID_LoadCity
0x0BB3C277  kCommandID_LoadRegion
0x6A935CD8  kCommandID_ScrollLeft      0x2A948275  kCommandID_ScrollLeftStop
0x6A935CE0  kCommandID_ScrollRight     0x2A94826E  kCommandID_ScrollRightStop
0x6A935CDD  kCommandID_ScrollUp        0x2A948272  kCommandID_ScrollUpStop
0x6A935CE2  kCommandID_ScrollDown      0x2A94826B  kCommandID_ScrollDownStop
0x6A935CF1  kCommandID_Cancel
0x6A935E3C  kCommandID_QuitGame
0x6AA9FE51  kCommandID_SetExpandedToolTips
```
Not in the registry (Note: names unknown): `0x287259F6`, `0x287259F7`, `0xC9E41918`, `0xEA5A96E6`,
`0x26C10A3E`, `0xCA5CFEE2`, `0xABA290E1`, `0xCBA290EC`, `0xABA290F6`, `0x4A5600xx`, `0x2A5B000x`,
`0x098F4Fxx`, `0x09EBF2C8`, `0x0A5510A9`, `0x4BB92C1F`, `0xEBB91356`, `0x8A1DA655`, `0xA98F4F88`,
`0xCA1DA670`, `0x4A779A09`, `0x4A779A1A`, `0x6BB92BCA`, `0x0BB0F5E7`, `0x6A231EAA`, `0xAA738C4E`.

---

## Cross-slice hand-offs (functions this slice calls that live elsewhere)

| VA | what this slice proves about it |
|---|---|
| `sub_7AE160` | 16.16 fixed-point **scanline resampler**. `[esp+0x70]` seeds `0xFFFF0000` (= −1.0 in 16.16) and adds `0x10000` per row (`0x007AE385`); scale is hard-wired `0x3F800000` (1.0f) at `0x007AE186`/`0x007AE1FD` with `0x46800000` (16384.0f) as the fixed-point range; callback `0x7AA0E0`. Signature: `(dstBits, dstPitch, srcBits, srcPitch, dstW, dstH, srcW, srcH, double dx, double dy)`. **It CAN scale; the region tile path never asks it to.** |
| `sub_7ABCD0` | `(img1C, img20)` — pairs the shifted source with its mask |
| `sub_7AD400` | `__usercall`: `ESI` = out `vector<dword>`; `(bitmap, int threshold, int mode)` — builds a run-list |
| `sub_7AA6A0` | `__usercall`: `EAX` = `item->img20`; `(&item[0x68], &item[0x6C])` |
| `sub_7ADFA0` | item `operator=` (has the pointer-equality guard at `0x007ADFD8`) |
| `sub_7AA920` | `_Median` for the 12-byte draw-order records; the depth key is `(1<<a.sz) - (1<<b.sz) + (a.y-b.y) + (a.x-b.x)` |
| `sub_7ADF40` / `sub_7ADE50` / `sub_7AD1F0` | insertion sort / heap sort / unguarded partition (12-byte) |
| `sub_7ADC20` | `__thiscall(this, cityRecord)` → enter/open that city |
| `sub_7AC110`, `sub_7AC270`, `sub_7AC2D0`, `sub_7ABB80`, `sub_7ABDF0` | region-screen refresh / teardown helpers |
| `sub_74C6E0` | `__thiscall(regionView)` → the currently selected `Item*` |
| `sub_7B30D0`, `sub_7B30F0`, `sub_7B5430`, `sub_7B5DB0` | `cSC4WinRegionView` setters (toggle, view-mode 0..2, "tile changed", cancel) |
| `sub_913C1A` | cached-singleton getter for `kGZGraphicSystem_SystemServiceID` (`[0xB628BC]`) |
| `sub_913D7A` | cached-singleton getter (`[0xB628DC]`) used only by `sub_7AEC00` |
