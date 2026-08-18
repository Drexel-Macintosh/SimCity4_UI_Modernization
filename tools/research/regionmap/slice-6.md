# Region-screen module — SLICE 6 of 8: `0x007B2320` … `0x007B3D30`

SimCity 4 Deluxe 1.1.641, image base `0x400000`, `fileOffset = VA - 0x400000`.
36 functions, taken from `tools\uimap\funcs.json` (`starts` in `[0x7B2320, 0x7B3C10]`);
each ends where the next `starts` entry begins, so the slice physically covers
`0x007B2320 .. 0x007B3D2F` (2576 bytes).

Everything below was read out of the binary in this pass with
`tools\research\scripts\disasm.py` and a byte-scanner over the PE sections.
Guesses are marked `⚠ UNSURE`.

---

## Table of contents

| # | VA (start..end, bytes) | Owner | One-line purpose |
|---|---|---|---|
| 1 | [`sub_7B2320`](#sub_7b2320) (0x7B2320..0x7B23A0, 128) | cSC4WinRegionScreen | scalar-deleting destructor, vtable `0xAB9260+0x250` |
| 2 | [`sub_7B2340`](#sub_7b2340) (0x7B2340..0x7B23A0, part) | free function | `EnumChildren` callback: clear win-flag `0x8000`, make every button notify a target, recurse |
| 3 | [`sub_7B23A0`](#sub_7b23a0) (0x7B23A0..0x7B23E0, 64) | "bouncer" animator | `QueryInterface` for iid 1 / `0x22E85D8E` (cIGZWinProc) |
| 4 | [`sub_7B23E0`](#sub_7b23e0) (0x7B23E0..0x7B2410, 48) | tile-grid class | `QueryInterface` for iid `0xC989F960`, else thunk to base at `this+4` |
| 5 | [`sub_7B2410`](#sub_7b2410) (0x7B2410..0x7B2430, 32) | cSC4WinRegionView | set two display flags `+0x111`, `+0x112` (no repaint) |
| 6 | [`sub_7B2430`](#sub_7b2430) (0x7B2430..0x7B2440, 16) | cSC4WinRegionView | set display flag `+0x116` (no repaint) |
| 7 | [`sub_7B2440`](#sub_7b2440) (0x7B2440..0x7B2480, 64) | cSC4WinRegionView | vtable `0xAB9658+0x254`: "point hits no child window" test |
| 8 | [`sub_7B2480`](#sub_7b2480) (0x7B2480..0x7B24B0, 48) | **not region code** | shared `GetSingleton(clsid 0xC2C2EB0F, iid 0x22C2EB1F)` helper |
| 9 | [`sub_7B24B0`](#sub_7b24b0) (0x7B24B0..0x7B24FA, 74) | **not region code** | shared SEH-guarded smart-pointer release |
| 10 | [`sub_7B24FA`](#sub_7b24fa) (0x7B24FA..0x7B2500, 6) | — | SEH unwind funclet for #9 |
| 11 | [`sub_7B2500`](#sub_7b2500) (0x7B2500..0x7B2620, 288) | "bouncer" animator | `DoMessage`: attach / detach / per-tick vertical bounce of window `0x4A630000` |
| 12 | [`sub_7B2620`](#sub_7b2620) (0x7B2620..0x7B2770, 336) | tile-grid class | mark every grid cell touched by a pixel rect DIRTY |
| 13 | [`sub_7B2770`](#sub_7b2770) (0x7B2770..0x7B28B0, 320) | tile-grid class | **bake + blit the whole tile grid** to a surface |
| 14 | [`sub_7B28B0`](#sub_7b28b0) (0x7B28B0..0x7B29E0, 304) | tile-grid class | vtable `0xAB9630+0x0C`: acquire the HW draw target and drive #13 |
| 15 | [`sub_7B29E0`](#sub_7b29e0) (0x7B29E0..0x7B2A30, 80) | cSC4WinRegionView | invalidate everything: all cells dirty, all items un-built, request repaint |
| 16 | [`sub_7B2A30`](#sub_7b2a30) (0x7B2A30..0x7B2DD0, 928) | free (usercall) | **run-list blit of an ARGB bitmap** onto a surface, 1:1, opaque runs fast-pathed |
| 17 | [`sub_7B2DD0`](#sub_7b2dd0) (0x7B2DD0..0x7B3030, 608) | free (usercall) | **run-list tint** of a surface in one solid colour, per-pixel weights |
| 18 | [`sub_7B3030`](#sub_7b3030) (0x7B3030..0x7B30B0, 128) | cSC4WinRegionView | **item → screen point** (bottom-anchored: subtracts the source bitmap height) |
| 19 | [`sub_7B30B0`](#sub_7b30b0) (0x7B30B0..0x7B30D0, 32) | cSC4WinRegionView | set flags `+0x114`, `+0x115`, then invalidate |
| 20 | [`sub_7B30D0`](#sub_7b30d0) (0x7B30D0..0x7B30F0, 32) | cSC4WinRegionView | set flag `+0x113`, then invalidate |
| 21 | [`sub_7B30F0`](#sub_7b30f0) (0x7B30F0..0x7B3110, 32) | cSC4WinRegionView | set dword `+0x118`, then invalidate |
| 22 | [`sub_7B3110`](#sub_7b3110) (0x7B3110..0x7B3170, 96) | cSC4WinRegionView | **item → screen RECT** (un-panned; size from the SOURCE bitmap) |
| 23 | [`sub_7B3170`](#sub_7b3170) (0x7B3170..0x7B31D0, 96) | free function | conditional "notify" if a looked-up record has a flag set |
| 24 | [`sub_7B31D0`](#sub_7b31d0) (0x7B31D0..0x7B3220, 80) | STL | `fill(first,last,value)` over refcounted 8-byte elements |
| 25 | [`sub_7B3220`](#sub_7b3220) (0x7B3220..0x7B3290, 112) | STL | `copy(first,last,dest)` over refcounted 8-byte elements |
| 26 | [`sub_7B3290`](#sub_7b3290) (0x7B3290..0x7B3300, 112) | STL | `copy_backward` over refcounted 8-byte elements |
| 27 | [`sub_7B3300`](#sub_7b3300) (0x7B3300..0x7B3560, 608) | free (usercall) | **`rep movsd` composite (1:1) + run-list colour tint of the copy** |
| 28 | [`sub_7B3560`](#sub_7b3560) (0x7B3560..0x7B3590, 48) | "bouncer" animator | constructor (two vtables `0xAB95F0` / `0xAB9604`) |
| 29 | [`sub_7B3590`](#sub_7b3590) (0x7B3590..0x7B35C0, 48) | "bouncer" animator | `this-4` adjustor thunk + scalar-deleting destructor |
| 30 | [`sub_7B35C0`](#sub_7b35c0) (0x7B35C0..0x7B35F0, 48) | "bouncer" animator | destructor |
| 31 | [`sub_7B35F0`](#sub_7b35f0) (0x7B35F0..0x7B3630, 64) | STL | `uninitialized_copy` over refcounted 8-byte elements |
| 32 | [`sub_7B3630`](#sub_7b3630) (0x7B3630..0x7B3670, 64) | STL | `uninitialized_fill_n` over refcounted 8-byte elements |
| 33 | [`sub_7B3670`](#sub_7b3670) (0x7B3670..0x7B3A80, 1040) | free (stdcall-ish) | **THE RUN-LIST BUILDER** + in-place edge composite of a source bitmap |
| 34 | [`sub_7B3A80`](#sub_7b3a80) (0x7B3A80..0x7B3B60, 224) | cSC4WinRegionView | **screen point → item**, with a per-pixel binary-search hit mask |
| 35 | [`sub_7B3B60`](#sub_7b3b60) (0x7B3B60..0x7B3BD0, 112) | STL | `vector<refcounted>::vector(n)` |
| 36 | [`sub_7B3BD0`](#sub_7b3bd0) (0x7B3BD0..0x7B3C10, 64) | STL | `vector<refcounted>::~vector` |
| 37 | [`sub_7B3C10`](#sub_7b3c10) (0x7B3C10..0x7B3D30, 288) | cSC4WinRegionView | **clear the item list** (drop each item's subscription list), then invalidate |

(37 rows because `sub_7B2340` shares a `funcs.json` span boundary with `sub_7B2320`'s
padding — it is a separate function reached only by pointer.)

---

## 0. Reference tables established in this pass

### 0.1 The tile-buffer vtable `0x00AC1400` — slots CONFIRMED here

Ground truth already had `+0x0C Init(w,h,fmt)`, `+0x24 GetWidth`, `+0x28 GetHeight`,
`+0x30 GetRect`. This slice adds, all from live call sites listed per function:

| slot | signature inferred | evidence |
|---|---|---|
| `vt+0x18` | `bool Lock(uint32 flags)` | `0x7B27A6` (`0x8010`), `0x7B2B69` (`0x8080`), `0x7B2B7F` (`0x40`), `0x7B2E7F` (`0x8080`), `0x7B3315` (`0x8080`), `0x7B3329` (`0x800`), `0x7B36DF` (`0x8040`) |
| `vt+0x1C` | `void Unlock(uint32 flags)` | `0x7B289A` (`0x8010`), `0x7B2DB5` (`0x40`), `0x7B2DC1` (`0x8040`), `0x7B3022` (`0x8040`), `0x7B3554` (`0x8080`), `0x7B3A5A` (`0x8040`) |
| `vt+0x30` | `RECT* GetRect()` → `{l,t,r,b}` int32 | everywhere; returns a pointer, not a copy |
| `vt+0x54` | `uint32 GetPixelRGB(int x, int y, uint8* r, uint8* g, uint8* b)` | `0x7B2CDF`, `0x7B2F6A` — 5 args, three `lea`'d byte locals |
| `vt+0x58` | `void SetPixel(int x, int y, uint32 nativeColor)` | `0x7B2D77`, `0x7B2FEF` |
| `vt+0x74` | `bool Blit(IBitmap* src, RECT* srcRect, RECT* dstRect, RECT* clip /*may be 0*/)` | `0x7B2868` (clip = grid rect), `0x7B2C96` (clip = `0`) |
| `vt+0x78` | `uint32 MakeColor(uint8 r, uint8 g, uint8 b)` | `0x7B2D6B`, `0x7B2FE3` |
| `vt+0x7C` | takes the return value of `vt+0x54`; **result discarded** | `0x7B2CE5`, `0x7B2F70` — ⚠ UNSURE what it is (a release/"unlock pixel" pair?) |
| `vt+0x88` | `void* GetBits()` | `0x7B33C5`, `0x7B3743`, `0x7B2C25` |
| `vt+0x8C` | `int GetPitch()` — **bytes per row** | `0x7B33B4`, `0x7B3734`, `0x7B2C15`; always `imul`'d by a row index and added to `GetBits()` |

### 0.2 cIGZWin real vtable offsets vs. our header — an off-by-one is proven

`vendor/gzcom-dll/.../cIGZWin.h` numbers the pure virtuals from `DoMessage = +0x000`.
The real vtable prefixes `cIGZUnknown` (QI/AddRef/Release), so real = header + delta:

* `EnumChildren` header `+0x074` → real **`+0x080`** — proven at `0x7B2392`
  (`push pContext / push 0x7B2340 / push 0x22BA0121 / call [edx+0x80]`; `0x22BA0121`
  = `GZIID_cIGZWin`, and the callback's 4-arg shape matches the header's
  `(parent, childID, child, pContext)`). **delta = 0x0C.**
* `SetFlag(flag,bool)` header `+0x100` → real **`+0x110`** — `0x7B2351`
  (`push 0 / push 0x8000`, 2 args). **delta = 0x10.**
* `SetNotificationTarget(cIGZWin*)` header `+0x148` → real **`+0x158`** — `0x7B2374`
  (1 arg). **delta = 0x10.**
* `GZPaint` header `+0x150` → real **`+0x160`** (ground truth's "slot 88" draw stub
  `0x00648F00`). **delta = 0x10.**

⇒ **our `cIGZWin.h` is missing exactly one virtual somewhere between header slot 30
and header slot 63** (i.e. between `SortChildren +0x078` and `GetFlag +0x0FC`).
Any real offset in that window is ambiguous by one slot; those are flagged
`⚠ UNSURE (delta 0x0C or 0x10)` below. Offsets outside it are safe.

### 0.3 Data / rdata constants used by this slice

| VA | value | used by |
|---|---|---|
| `0x00A80AA8` | **float** `4294967296.0f` (2^32) — unsigned→float fixup | `sub_7B3030` |
| `0x00A80AB0` | **double** `1.0` | `sub_7B2500` |
| `0x00A80AB8` | **double** `4294967296.0` (2^32) — unsigned fixup | `sub_7B2500` |
| `0x00AB95D0` | **double** `6.28318` (2π) | `sub_7B2500` |
| `0x00AB95D8` | **double** `0.00066666666666666664` (= 1/1500) | `sub_7B2500` |
| `0x00A83524` | `0x005D4A10` — a vtable slot value stored transiently by `sub_7B3560` | `sub_7B3560` |
| `0x00AB95F0` | vtable A of the "bouncer" class (5 slots) | `sub_7B3560` |
| `0x00AB9604` | vtable B of the "bouncer" class (11 slots) | `sub_7B3560` |
| `0x00AB9630` | vtable of the tile-grid class (iid `0xC989F960`) | ctors at `sub_7B51D0`, `sub_7B6060` |
| `0x00B43C94` | module-scope service pointer; `vt+0xC4` = "get a lookup table" | `sub_7B3170` |
| `0x00B43DD0` | module-scope service pointer; `vt+0x50` = request repaint (0 args), `vt+0x60`/`vt+0x68` bracket the paint | `sub_7B28B0`, `sub_7B29E0`, `sub_7B3C10`. Set by `0x00602141`/`0x006025CB`, also by `0x007AC3BC`/`0x007AD0EB` in this module. **⚠ UNSURE which class.** |
| `0x00B02AF4` | `.data`: `0x007B24FA` — SEH scope-table entry for `sub_7B24B0` | — |

### 0.4 Helper functions outside the slice, identified here

| VA | identity | how proven |
|---|---|---|
| `0x009EFF60` | **`floor(double)`** | SSE2 exponent-mask body at `0x9EFFA0`; `|x|<1` → `fldz` for positives, `-1.0` via `0xAE6330`/`0xAE6340` for negatives |
| `0x009EEF04` | `_ftol` | classic MSVC `fistp`/fixup body |
| `0x00932A45` | `jmp 0x9F361F` = millisecond clock (`GetSystemTimeAsFileTime` → `0xBAD6B0` epoch delta) | `0x9F3629 call [0xA801C8]` |
| `0x009EEB70` | `memmove` | `rep movsd` + overlap check |
| `0x0090CF54` / `0x0090CF63` | `operator new` / `operator delete` (allocator `0xB62698`) | |
| `0x0090D957` / `0x0090D964` | base ctor/dtor writing vtable `0xACE624` | |
| `0x005E5620` | `operator delete` (the one deleting-destructors call) | |
| `0x009457C6` | base `cRZUnknown::QueryInterface` — only `iid == 1` | `0x9457C6 cmp [esp+4],1` |
| `0x008793BD..EC` | GZCOM framework accessor (returns `[0xB540B0]`) | |
| `0x0078D6E0` | `pWin->EnumChildren(GZIID_cIGZWin, 0x78D670, &{x,y,0})` → returns the hit child | `0x78D701 push 0x22ba0121` |
| `0x0048C290` | `vector<int32>::vector(n)` (raw, `operator new(n*4)`) | |
| `0x0046FE60` | `fill(first, last, *value)` for 4-byte elements | |
| `0x0051CA60` | `vector<int32>::insert / _Grow` (the push_back slow path) | |

### 0.5 The TWO run-list formats (this was the biggest single find)

Both are `std::vector<uint32>` `{begin,end,cap}` and both pack a position as
`(row << 16) | column`.

* **Format A — boundary pairs only, 8 bytes per run.**
  `[open, close, open, close, …]`. Produced by **`sub_7B3670`**, consumed by
  **`sub_7B2A30`**. Consumer advances `ecx += 4` twice per run and never reads
  anything between runs (`0x7B2BC9`, `0x7B2BEB`, loop test `0x7B2DA4`).
* **Format B — 8-byte header + one dword per pixel.**
  `[open, close, w0, w1, … w(n-1), open, close, …]` where `n = closeX - openX`.
  Consumed by **`sub_7B2DD0`** and **`sub_7B3300`**. Proven by the explicit
  stride computation in `sub_7B2DD0`:
  `0x7B2EE5: 83c004  add eax,4 / 8bdd 2bd9  ebx = xEnd-xStart / 8d0498  lea eax,[eax+ebx*4]`
  — i.e. `nextRunHeader = afterHeader + runLen*4`.
  `sub_7B2DD0` uses the full dword as a 0..255 weight; **`sub_7B3300` uses only the
  low byte, shifted right by one** (`0x7B34A7: 8a17 d0ea` → weight 0..127, so its
  tint tops out at ~50%).

**No producer of format B is in this slice.** ⚠ UNSURE where it is built.

---

## 1. cSC4WinRegionScreen

### sub_7B2320
`0x007B2320 .. 0x007B233E (31 bytes of code, span padded to 0x7B2340)`

**PURPOSE** `cSC4WinRegionScreen::'scalar deleting destructor'`.

**CONVENTION** `__thiscall void* f(char flags)` — `ret 4`.

**VTABLE** `0x00AB9260 + 0x250` (the class's own extra virtuals live at
`+0x250/+0x254/+0x258`, past the end of the cIGZWin interface which ends at `+0x24C`).

```c
void* __thiscall RegionScreen_dtor_del(RegionScreen* this, char flags) {
    sub_7B1200(this);                 // real dtor; its first act (0x7B1205) is
                                      // *(void**)this = 0x00AB9260
    if (flags & 1) operator_delete(this);   // 0x005E5620
    return this;
}
```

**CALLERS** none direct; reached only through the vtable.

---

## 2. Window-tree walkers

### sub_7B2340
`0x007B2340 .. 0x007B239D (94 bytes)`

**PURPOSE** `cIGZWin::EnumChildren` callback. For every descendant: clear window
flag `0x8000`, and if the child is a **button** make `pContext` its notification
target. Recurses into the child.

**CONVENTION** `__cdecl bool f(cIGZWin* parent, uint32 childID, cIGZWin* child, void* pContext)`
— 4 stack args, plain `ret`. Matches
`cIGZWin.h:101 typedef bool(*EnumChildrenCallback)(cIGZWin*, uint32_t, void*, void*)`.

```c
bool __cdecl HookUpButtons(cIGZWin* parent, uint32 id, cIGZWin* child, void* pCtx)
{
    child->vt_0x110(0x8000, 0);                    // SetFlag(0x8000, false)
    void* pBtn;
    if (child->QueryInterface(0x00008810, &pBtn))  // GZIID_cIGZWinBtn
    {
        child->vt_0x158(pCtx);                     // SetNotificationTarget(pCtx)
        pBtn->Release();                           // [pBtn]->vt+0x08
    }
    child->vt_0x80(0x22BA0121, &HookUpButtons, pCtx);   // EnumChildren(GZIID_cIGZWin,…)
    return true;
}
```

**CONSTANTS** `0x00008810` = `GZIID_cIGZWinBtn` (our `src\UiSpike.cpp:10378`);
`0x22BA0121` = `GZIID_cIGZWin` (`src\UiSpike.cpp:10376`).

**CALLERS** its address is taken at `0x007B2387` (self-recursion) and at
`0x007B5BB1`, inside **`sub_7B59B0`** (slice 8). So slice 8 kicks this walk off once.

### sub_7B3170
`0x007B3170 .. 0x007B31C0 (80 bytes)`

**PURPOSE** if an object's record in a global table has a flag set, poke a second
object. ⚠ UNSURE what either object is.

**CONVENTION** `__stdcall bool f(A* a0, B* a1)` — `ret 8`, no `this`.

```c
void __stdcall f(A* a, B* b) {
    Table* t = (*(Svc**)0xB43C94)->vt_0xC4();     // service -> lookup table
    if (!a->vt_0x10C())  return;                  // 0-arg bool predicate
    Rec* r = sub_4B5D10(t, a->vt_0x104());        // 0-arg -> key ; map lookup
    if (!r) return;
    if (!*(uint8*)(r + 0x10)) return;
    b->vt_0x3C(0);
}
```

**FIELDS** `[rec+0x10]` = a byte flag.
⚠ UNSURE: `a` is probably **not** a `cIGZWin` — real `+0x10C`/`+0x104` would need
0-arg cIGZWin methods and none of the candidates in either delta fit.

**CALLERS** `sub_7B4B80`.

---

## 3. The "bouncer" — a small animator class

Constructed by `sub_7B3560`, two vtables emitted back-to-back:

```
vtable A = 0x00AB95F0        vtable B = 0x00AB9604   (stored at this+4)
  +0x00 0x007B23A0  QueryInterface     +0x00 0x007B3590  'scalar deleting dtor' thunk
  +0x04 0x005BE3E0  AddRef             +0x04 0x005BE410
  +0x08 0x005BE3F0  Release            +0x08 0x005BE420
  +0x0C 0x007B2500  DoMessage          +0x0C 0x0090D981
  +0x10 0x0041D4C0  (GetGZCLSID? ⚠)    +0x10 0x009D7E63
                                       +0x14 0x007B3E60   (slice 7)
                                       +0x18 0x005BE420
                                       +0x1C 0x005BCB60
                                       +0x20 0x007B3E70   (slice 7)
                                       +0x24 0x0090D981
                                       +0x28 0x009D7E63
```

Object layout: `+0x00` vptrA, `+0x04` vptrB, `+0x08` = 0, `+0x0C` = start timestamp (ms),
`+0x10` = the AddRef'd `cIGZWin*` being animated.

### sub_7B23A0
`0x007B23A0 .. 0x007B23D2 (51 bytes)`

**PURPOSE** `QueryInterface`. **CONVENTION** `__thiscall bool(uint32 riid, void** ppv)`, `ret 8`.

```c
if (riid == 1)            { *ppv = this; AddRef(); return true; }   // GZIID_cIGZUnknown
if (riid == 0x22E85D8E)   { *ppv = this; AddRef(); return true; }   // GZIID_cIGZWinProc
return false;
```
The constant is written as `dec eax` then `sub eax, 0x22E85D8D` (`0x7B23A5`/`0x7B23A7`)
— i.e. `1` and `1 + 0x22E85D8D = 0x22E85D8E`. `0x22E85D8E` = `GZIID_cIGZWinProc`
(`vendor/gzcom-dll/.../cIGZWinProc.h:28`).

**DATA XREFS** `0x00AB5314, 0x00AB5340, 0x00AB5380, 0x00AB53C0, 0x00AB5400,
0x00AB5454, 0x00AB95F0` — the same QI body is shared by six other cIGZWinProc
implementations elsewhere in the exe.

### sub_7B2500
`0x007B2500 .. 0x007B261A (282 bytes)`

**PURPOSE** the animator's `DoMessage`. Three messages: **attach**, **detach**,
**tick**. The tick bounces a window vertically with a `1 − |sin|` envelope,
period **1500 ms**.

**CONVENTION** `__thiscall bool f(void* pSender, uint32* pMsg)` — `ret 8`.
The switch reads `*(uint32*)arg1` directly (`0x7B2500`/`0x7B2504`).

```c
bool __thiscall DoMessage(Bouncer* this, cIGZWin* pSender, uint32* pMsg)
{
  switch (*pMsg)
  {
  case 0xA2BF8AD5:                                   // ATTACH
      this->t0 /*+0x0C*/ = now_ms();                 // 0x932A45
      cIGZWin* n = pSender->vt_0x8C(0x4A630000);     // get child by id (no AddRef)
      cIGZWin* o = this->target /*+0x10*/;
      if (n != o) { if (n) n->AddRef(); this->target = n; if (o) o->Release(); }
      return true;

  case 0xA2BF8AD6:                                   // DETACH
      if (this->target) { cIGZWin* o = this->target; this->target = 0; o->Release(); }
      return true;

  case 0xA2BF8ACD:                                   // TICK
      if (!this->target) return false;
      uint32 t = (now_ms() - this->t0) % 1500;                       // ecx = 0x5DC
      double k = 1.0 - fabs(sin( (t / 1500.0) * 6.28318 ));          // 0xAB95D8, 0xAB95D0, 0xA80AB0
      cIGZWin* parent = this->target->vt_0x2C();                     // GetParentWin()
      int span = parent->vt_0xA8() - this->target->vt_0xA8();         // GetH() - GetH()
      this->target->vt_0xE0(0, (int)(span * k));                     // GZWinMoveTo(0, y)
      return false;                                                  // falls to `xor al,al`
  }
  return false;
}
```

* `vt+0x2C` → header `+0x20` `GetParentWin()` (delta 0x0C is proven for this range).
* `vt+0xA8` → header `+0x9C` `GetH()`.
* `vt+0xE0` → header `+0xD4` `GZWinMoveTo(x, y)` (2 args). ⚠ UNSURE by one slot
  (this offset is inside the ambiguous window of §0.2), but it is the only 2-int
  candidate.
* `vt+0x8C` → `GetChildWindowFromID` or `GetChildWindowFromIDRecursive`
  ⚠ UNSURE (delta ambiguity); non-AddRef'ing either way, since the code AddRefs it itself.

**CONSTANTS** `0x4A630000` is a real UI window id — declared once in the corpus,
`T-00000000_G-96a006b0_I-ca539343.ui`, a **42×65 GZWinBMP** (verified with
`tools\sdk\lookup.py 0x4A630000`). So the bounce moves a 42×65 bitmap through
`parent.H − 65` pixels twice every 1500 ms.

⚠ UNSURE what `0xA2BF8ACD/AD5/AD6` are named; nothing in our corpus or source
names them. Their behaviour here is unambiguous (tick / attach / detach).

### sub_7B3560
`0x007B3560 .. 0x007B358B (44 bytes)`

**PURPOSE** constructor. **CONVENTION** `__thiscall Bouncer* f()`, plain `ret`.

```c
*(void**)this        = 0x00A83524;    // transient (never observed)
sub_90D957(this+4);                   // base ctor: [this+4]=0xACE624, [this+8]=0
*(void**)(this+4)    = 0x00AB9604;
*(void**)(this)      = 0x00AB95F0;
*(void**)(this+0x10) = 0;
```
**CALLERS** `sub_7B59B0` (slice 8).

### sub_7B3590
`0x007B3590 .. 0x007B35BB (44 bytes, two entry points)`

`0x7B3590`: `sub ecx,4 / jmp 0x7B35A0` — the **`this−4` adjustor thunk** installed at
vtable-B slot 0. `0x7B35A0`: the scalar deleting destructor
(`sub_7B35C0(this); if (flags&1) operator delete(this); return this;`), `ret 4`.

### sub_7B35C0
`0x007B35C0 .. 0x007B35E3 (36 bytes)`

**PURPOSE** destructor. `if (this->target) this->target->Release();` then tail-jumps
`0x0090D964` with `ecx = this+4` (base dtor) — or with `ecx = 0` when `this` is null.
Plain `ret` (tail `jmp`).

---

## 4. The tile grid (vtable `0x00AB9630`, iid `0xC989F960`)

Constructed at `sub_7B51D0` (`0x7B5309`) and `sub_7B6060` (`0x7B60B0`) — both
outside this slice. `cSC4WinRegionView` holds it at **`view + 0x10C`** (proven by
`sub_7B29E0` and `sub_7B3C10` walking `[view+0x10C]+0x0C .. +0x10` with the same
8-byte cell stride `sub_7B2620` writes).

**Object layout, entirely from this slice:**

| offset | meaning | evidence |
|---|---|---|
| `+0x00` | vptr (its own interface, `0xAB9630`) | |
| `+0x04` | vptr of the ref-counted base (`sub_7B23E0` does `add ecx,4`) | |
| `+0x0C` | `cells.begin` — `struct Cell { IBitmap* bmp; uint8 dirty; /*pad 3*/ }`, **stride 8** | `0x7B274E byte [ebp+esi*8+4]`, `0x7B29F0` |
| `+0x10` | `cells.end` | `0x7B29E9` |
| `+0x18` | origin **column** (cell index of column 0) | `0x7B2627`, `0x7B2835` |
| `+0x1C` | origin **row** | `0x7B262B`, `0x7B2824` |
| `+0x20` | pixel scroll offset X (subtracted from cell rects) | `0x7B27F0` |
| `+0x24` | pixel scroll offset Y | `0x7B2806` |
| `+0x28` | **cell width in px** | `0x7B2639`, `0x7B27E7` |
| `+0x2C` | **cell height in px** | `0x7B2620`, `0x7B27EA` |
| `+0x30` | columns | `0x7B26CF`, `0x7B27D0` |
| `+0x34` | rows | `0x7B2709`, `0x7B27B5` |
| `+0x38` | total width (px) | `0x7B277A` |
| `+0x3C` | total height (px) | `0x7B2787` |
| `+0x40` | the **cell renderer**; `vt+0x0C(IBitmap*, worldX, worldY)` bakes one cell | `0x7B2842` |

### sub_7B23E0
`0x007B23E0 .. 0x007B2406 (39 bytes)`

**PURPOSE** `QueryInterface`. **CONVENTION** `__thiscall bool(uint32 riid, void** ppv)`, `ret 8` (via the tail jump).

```c
if (riid == 0xC989F960) { *ppv = this; this->AddRef(); return true; }
// otherwise: retarget to the base sub-object and tail-jump the base QI
return sub_9457C6((char*)this + 4, riid, ppv);      // 0x9457C6 accepts only riid==1
```
`0x7B23FB mov [esp+4],eax` rewrites the riid slot with the same value (a compiler
artifact) before `add ecx,4 / jmp 0x9457C6`.

**VTABLE** `0x00AB9630 + 0x00`. ⚠ UNSURE what interface `0xC989F960` names — it is not
in our source lists or the .UI corpus.

### sub_7B2620
`0x007B2620 .. 0x007B2764 (325 bytes)`

**PURPOSE** **mark every grid cell overlapped by a pixel rectangle as DIRTY.**
This is the invalidation entry point for the terrain/tile cache.

**CONVENTION** `__thiscall void f(const RECT* r)` — `ret 4`; `r` = `{l,t,r,b}` int32.

```c
void __thiscall MarkRectDirty(Grid* g, const int32 r[4])
{
    int ox = g->originCol /*+0x18*/ * g->cellW /*+0x28*/;   // 0x7B263C imul ebx,edi
    int oy = g->originRow /*+0x1C*/ * g->cellH /*+0x2C*/;   // 0x7B262F imul ebp,eax

    int x0 = floordiv(r[0] - ox, g->cellW);   x0 = max(x0, 0);
    int y0 = floordiv(r[1] - oy, g->cellH);   y0 = max(y0, 0);
    int x1 = floordiv(r[2] - ox - 1, g->cellW); x1 = min(x1, g->cols /*+0x30*/ - 1);
    int y1 = floordiv(r[3] - oy - 1, g->cellH); y1 = min(y1, g->rows /*+0x34*/ - 1);

    for (int row = y0; row <= y1; ++row)          // 0x7B275B  jle  (INCLUSIVE)
      for (int col = x0; col <= x1; ++col)        // 0x7B2752  jle  (INCLUSIVE)
        g->cells[row * g->cols + col].dirty = 1;  // 0x7B274E byte [ebp + esi*8 + 4] = 1
}
```

`floordiv` is emitted four times as the classic
`cdq / idiv / if (num<0 && q*den != num) --q` fixup —
`0x7B26FD: 7d0a 8bd0 0fafd3 3bd6 7401 48`.
The `max`/`min` are branchless `lea`-of-two-slots selects (`0x7B2662`, `0x7B26DD`).

**CALLERS** `sub_7B5CA0` (slice 8).

### sub_7B2770
`0x007B2770 .. 0x007B28A6 (311 bytes)`

**PURPOSE** **bake and blit the entire tile grid onto a surface.** Dirty cells are
re-rendered first; every cell is then blitted.

**CONVENTION** `__thiscall bool f(IBitmap* dst, int ox, int oy)` — `ret 0xC`.

```c
bool __thiscall PaintGrid(Grid* g, IBitmap* dst, int ox, int oy)
{
    int32 clip[4] = { ox, oy, g->totalW /*+0x38*/ + ox, g->totalH /*+0x3C*/ + oy };
    if (!dst->Lock(0x8010)) return false;              // vt+0x18

    int idx = 0;
    for (int row = 0; row < g->rows; ++row)
      for (int col = 0; col < g->cols; ++col)
      {
        Cell* c = &g->cells[idx++];
        int32 cell[4];
        cell[0] = g->cellW*col - g->scrollX /*+0x20*/;
        cell[1] = g->cellH*row - g->scrollY /*+0x24*/;
        cell[2] = cell[0] + g->cellW;
        cell[3] = cell[1] + g->cellH;

        if (c->dirty) {
            g->renderer /*+0x40*/ ->vt_0x0C( c->bmp,
                     (g->originCol + col) * g->cellW,      // world X
                     (g->originRow + row) * g->cellH );    // world Y
            c->dirty = 0;
        }
        dst->Blit( c->bmp, c->bmp->GetRect(), cell, clip );   // vt+0x74
      }

    dst->Unlock(0x8010);                                // vt+0x1C
    return true;
}
```
Note the **renderer is handed the WORLD pixel origin, not the screen rect** — the
cell's own size is implicit in its bitmap. The blit is a straight
`srcRect → dstRect` with no scale argument.

**CALLERS** `sub_7B28B0`.

### sub_7B28B0
`0x007B28B0 .. 0x007B29D2 (291 bytes)`

**PURPOSE** vtable-`0xAB9630+0x0C` paint entry: take the hardware draw target out of
a context object, compute the offset, drive `sub_7B2770`, then hand off.

**CONVENTION** `__thiscall bool f(Ctx* ctx)` — `ret 4`.

```c
bool __thiscall Paint(Grid* g, Ctx* ctx)
{
    (*(Svc**)0xB43DD0)->vt_0x68();                 // enter (⚠ profiler/scope?)
    void* dev = ctx->svc /*+0x28*/ ->vt_0x20();    // -> edi
    void* pWin = 0;
    ctx->win /*+0x30*/ ->vt_0x130(&pWin);          // fetch a window/target
    if (pWin) { pWin->Release(); pWin = 0; }

    void* hw;
    if (dev->QueryInterface(0xAB300B2B, &hw))      // the HARDWARE BLIT interface
    {
        IBitmap* surf = hw->vt_0x14();
        int dx = dev->vt_0x28() - ctx_rect[?];     // 0x7B2920/0x7B292F  (two GetX-ish calls)
        int dy = dev->vt_0x28() - ctx_rect[?];
        surf->vt_0x0C();                           // begin
        surf->vt_0x18(&{ …, dx, …, dy });          // set origin
        PaintGrid(g, dev, 0, 0);                   // <-- sub_7B2770, ox = oy = 0
        surf->vt_0x24();                           // end
        hw->vt_0x18();
    }
    (*(Svc**)0xB43DD0)->vt_0x60();                 // leave

    ctx->win->vt_0x128( x, y, w, h );              // 0x7B29AE  4 ints
    sub_7D5230(ctx);                               // walks ctx->[0xE0..0xE4], 104-byte stride
    if (pWin) pWin->Release();
    return true;
}
```
`0xAB300B2B` is already in our notes as *"QueryInterface IID for the hardware blit
path"* (`tools/flyout-sim/emu_plot.py:49`, `tools/research/HANDOFF-god-mode-flyouts.md:402`).
⚠ UNSURE on the exact meaning of the `dx/dy` pair and of `ctx` slots `+0x28`/`+0x30`.

`sub_7D5230` divides `(ctx->[0xE4] − ctx->[0xE0])` by **104** (magic
`0x4EC4EC4F`, `sar edx,5` at `0x7D524B`) — a vector of 104-byte records on `ctx`.

**CALLERS** none direct — vtable only (`0x00AB963C`).

---

## 5. cSC4WinRegionView — geometry and state

All of the following are called with `ecx = [regionScreen + 0xE0]`; verified at
`0x7ACBDD/0x7ACBE4` (`sub_7B2430`), `0x7ACBE9/0x7ACBF2` (`sub_7B2410`),
`0x7ACBFD/0x7ACC0B` (`sub_7B30B0`), `0x7ACC66/0x7ACC72` (`sub_7B3110`),
`0x7ACAEF/0x7ACAF7` (`sub_7B3A80`), and again in `sub_7AC110`.
**Ground truth's "+0x118/+0x11C an item array" on the SCREEN is wrong for these
offsets** — see corrections.

### sub_7B2410
`0x007B2410 .. 0x007B2426 (23 bytes)`
`__thiscall void f(uint8 a, uint8 b)`, `ret 8`. `this->[0x111] = a; this->[0x112] = b;`
**No invalidate.** Callers `sub_7AC110`, `sub_7ACAD0`.

### sub_7B2430
`0x007B2430 .. 0x007B243C (13 bytes)`
`__thiscall void f(uint8 a)`, `ret 4`. `this->[0x116] = a;` **No invalidate.**
Callers `sub_7AC110`, `sub_7ACAD0`.

### sub_7B30B0
`0x007B30B0 .. 0x007B30C9 (26 bytes)`
`__thiscall void f(uint8 a, uint8 b)`, `ret 8`.
`this->[0x114] = a; this->[0x115] = b; sub_7B29E0(this);`
Callers `sub_7AC110`, `sub_7ACAD0`.

### sub_7B30D0
`0x007B30D0 .. 0x007B30DF (16 bytes)`
`__thiscall void f(uint8 a)`, `ret 4`. `this->[0x113] = a; sub_7B29E0(this);`
Callers `sub_7AFAA0`, `sub_7B0470`.

### sub_7B30F0
`0x007B30F0 .. 0x007B30FF (16 bytes)`
`__thiscall void f(uint32 v)`, `ret 4`. `this->[0x118] = v; sub_7B29E0(this);`
Callers `sub_7AFAA0`, `sub_7B0470`.

### sub_7B29E0
`0x007B29E0 .. 0x007B2A27 (72 bytes)`

**PURPOSE** full invalidate. **CONVENTION** `__thiscall bool f()` — no stack args, tail `jmp`.

```c
bool __thiscall InvalidateAll(RegionView* v)
{
    Grid* g = v->grid /*+0x10C*/;
    for (Cell* c = g->cells.begin /*+0x0C*/; c != g->cells.end /*+0x10*/; ++c)
        c->dirty = 1;                                  // 0x7B29F0  byte [eax+4] = 1

    for (Item** p = v->items.begin /*+0x100*/; p != v->items.end /*+0x104*/; ++p)
        (*p)->built /*+0x34*/ = 0;                     // 0x7B2A17  byte [esi+0x34] = 0

    return (*(Svc**)0xB43DD0)->vt_0x50();              // tail jmp, 0 args
}
```
Confirms ground truth: item stride in the *pointer array* is 4 (`add eax,4`), the
items themselves are 0x80 bytes, and `[item+0x34]` is the built flag.

**CALLERS** `sub_7B30B0`, `sub_7B30D0`, `sub_7B30F0`.

### sub_7B3030
`0x007B3030 .. 0x007B30A2 (115 bytes)`  ← **load-bearing**

**PURPOSE** item → screen point. **The Y is bottom-anchored**: it subtracts the height
of the item's *source* bitmap.

**CONVENTION** `__thiscall void f(Item* item, int* outX, int* outY)` — `ret 0xC`.

```c
void __thiscall ItemToScreen(RegionView* v, Item* it, int* outX, int* outY)
{
    *outX = (int) ( floor((double)it->fx /*+0x10*/) - (double)v->panX /*+0xE8, int*/ );

    IBitmap* src = it->src /*+0x1C*/;
    float    ty  = (float)( floor((double)it->fy /*+0x14*/) - (double)v->panY /*+0xEC*/ );
    int      h   = src->GetHeight();                        // vt+0x28
    *outY = (int) ( ty - (double)(uint32)h );               // unsigned fixup via 0xA80AA8
}
```

Bytes that pin this down:

```
0x7B3037  d9 47 10           fld   dword [edi+0x10]       ; item->fx  (float)
0x7B303A  83 ec 08 / dd 1c24 fstp  qword [esp]            ; widen to double
0x7B3042  e8 19cf2300        call  0x009EFF60             ; floor()
0x7B3047  da a6 e8000000     fisub dword [esi+0xE8]       ; INTEGER pan subtract
0x7B304D  e8 …               call  0x009EEF04             ; _ftol
…
0x7B3071  d8 e9              fsubr st(0), st(1)           ; st0 = floor(fy) - panY
0x7B307B  ff 52 28           call  [edx+0x28]             ; src->GetHeight()
0x7B3084  db 44 24 14        fild  dword [esp+0x14]
0x7B3088  7d 06 / d8 05 a80a80 00   if (h<0) += 4294967296.0f  ; 0x00A80AA8
0x7B3090  d8 6c 24 10        fsubr dword [esp+0x10]       ; st0 = (floor(fy)-panY) - h
```

**FIELDS** `item+0x10` float screen X, `item+0x14` float screen Y, `item+0x1C` source
bitmap; `view+0xE8` pan X (int32), `view+0xEC` pan Y (int32).

**CALLERS** `sub_7B3110`, `sub_7B3A80`, `sub_7B4150`, `sub_7B4A60`, `sub_7B4B80`, `sub_7B5CA0`.

### sub_7B3110
`0x007B3110 .. 0x007B316A (91 bytes)`  ← **load-bearing**

**PURPOSE** item → screen RECT. Calls `sub_7B3030` and then **adds the pan back**, so
the rect it produces is in *un-panned* region space. The SIZE comes from
`[item+0x1C]` — the **source** bitmap, not the composite at `[item+0x2C]`.

**CONVENTION** `__thiscall void f(Item* item, int32 outRect[4])` — `ret 8`.

```c
void __thiscall ItemToRect(RegionView* v, Item* it, int32 r[4])
{
    ItemToScreen(v, it, &r[0], &r[1]);          // sub_7B3030
    r[0] += v->panX /*+0xE8*/;                  // 0x7B3129
    r[1] += v->panY /*+0xEC*/;                  // 0x7B3131

    int32* b = it->src /*+0x1C*/ ->GetRect();   // vt+0x30, called TWICE
    r[2] = r[0] + (b[2] - b[0]);                // right  = left + srcW
    b = it->src->GetRect();
    r[3] = r[1] + (b[3] - b[1]);                // bottom = top  + srcH
}
```

Net effect: `r = { floor(fx), floor(fy) - srcH, floor(fx) + srcW, floor(fy) }`.

**CALLERS** `sub_7ACAD0` only.

### sub_7B3A80
`0x007B3A80 .. 0x007B3B5D (222 bytes)`  ← **load-bearing**

**PURPOSE** screen point → item, **topmost first**, with a per-pixel opacity test.

**CONVENTION** `__thiscall Item* f(int x, int y)` — `ret 8`.

```c
Item* __thiscall HitTest(RegionView* v, int x, int y)
{
    int i = (v->items.end - v->items.begin)/4 - 1;   // last item first
    if (i < 0) return 0;
    for (; i >= 0; --i)
    {
        Item* it = v->items.begin[i];
        int px, py;
        ItemToScreen(v, it, &px, &py);               // sub_7B3030
        int dx = x - px, dy = y - py;

        int32* b = it->src /*+0x1C*/ ->GetRect();    // vt+0x30
        if (dx <  b[0] || dy <  b[1]) continue;
        if (dx >= b[2] || dy >= b[3]) continue;

        // per-pixel mask: sorted int32 array [it+0x44, it+0x48)
        int key = (dy << 16) + dx + 1;               // 0x7B3B03  lea esi,[esi+edi+1]
        int32* lo = it->mask_begin /*+0x44*/;
        int32* p  = std::lower_bound(lo, it->mask_end /*+0x48*/, key);
        if (((p - lo) /*bytes*/ & 4) != 0)           // 0x7B3B37  test dl,4  -> ODD index
            return it;                               // inside an OPEN run -> HIT
    }
    return 0;
}
```

The binary search is fully inlined (`0x7B3B15..0x7B3B33`, halving `eax` each pass).
`test dl, 4` tests bit 2 of the *byte* difference — i.e. element index odd — which is
exactly "we landed between an `open` and its `close`". So **`[item+0x44]/[item+0x48]`
is a sorted format-A run list serving as the click mask**, `key = (y<<16)|x`, biased
by `+1` so a hit exactly on `open` counts as inside.

**CALLERS** `sub_7ACAD0`, `sub_7B5DD0`.

### sub_7B3C10
`0x007B3C10 .. 0x007B3D2A (283 bytes)`

**PURPOSE** clear the view's item list. Also tears down each item's subscription
list, then invalidates everything.

**CONVENTION** `__thiscall bool f()` — no stack args, tail `jmp`.

```c
bool __thiscall ClearItems(RegionView* v)
{
    v->[0xE4] = 0;                                       // ⚠ UNSURE what this is

    for (Item** p = v->items.begin /*+0x100*/; p != v->items.end /*+0x104*/; ++p)
    {
        ListNode* head = (*p)->subs /*+0x70*/;           // circular doubly-linked, sentinel = head
        for (ListNode* n = head->next; n != head; n = n->next)
            n->obj /*+0x08*/ ->vt_0x10(0);               // "detach/cancel"
        for (ListNode* n = head->next; n != head; ) {
            ListNode* cur = n; n = n->next;
            if (cur->obj) cur->obj->Release();
            operator delete(cur);                        // 0x90CF63
        }
        head->next = head; head->prev = head;            // 0x7B3C97 / 0x7B3CA5
    }

    v->items.end = v->items.begin;                       // CLEAR  (see note)
    Grid* g = v->grid /*+0x10C*/;
    for (Cell* c = g->cells.begin; c != g->cells.end; ++c) c->dirty = 1;
    for (Item** p = v->items.begin; p != v->items.end; ++p) (*p)->built /*+0x34*/ = 0;
    return (*(Svc**)0xB43DD0)->vt_0x50();
}
```

**Note (compiler artifact worth knowing):** the "clear" is an inlined
`erase(begin,end)` whose guard is `cmp eax, eax` —

```
0x7B3CAC  8b 82 04010000   mov eax,[edx+0x104]
0x7B3CB2  3b c0            cmp eax, eax          ; ALWAYS equal
0x7B3CBA  75 04            jne 0x7B3CC0          ; the memmove path is DEAD CODE
```

The same idiom appears at `0x7B36B1..0x7B36B8` in `sub_7B3670`. Do not read the
`memmove` branch as reachable.

**Note:** the item *objects* are not freed and the pointers are not Released here —
ownership lives elsewhere. The second loop after the clear iterates an empty range.

**CALLERS** `sub_7B53A0` (slice 8).

### sub_7B2440
`0x007B2440 .. 0x007B2472 (51 bytes)`

**PURPOSE** "the point hits no child window of the view". Reached only through the
vtable — `0x00AB9658 + 0x254`, the slot immediately after the view's deleting
destructor, i.e. one of `cGZWin`'s own extra virtuals past the end of the cIGZWin
interface (which ends at real `+0x24C`). The region **screen** puts `0x0099BBBE`
(the shared base implementation) in the same slot, so this is a genuine override.

**CONVENTION** `__thiscall bool f(int x, int y)` — `ret 8`. Note the two arguments
are passed **by address** into the vtable call, so the caller's own stack slots are
rewritten in place.

```c
bool __thiscall PointHitsNothing(RegionView* v, int x, int y)
{
    v->vt_0xF0(&x, &y);                    // 2 int& out-params, coordinate conversion
    return sub_78D6E0(v, x, y) == 0;       // 0x7B246A  neg/sbb/inc  ->  (result == 0)
}
```

`sub_78D6E0` is `pWin->EnumChildren(GZIID_cIGZWin, 0x78D670, &{x, y, 0})` returning
the third context slot — i.e. the child window found at that point, or `0`.

⚠ UNSURE which conversion `vt+0xF0` is: it falls inside the ambiguous window of
§0.2, so it is either header `+0xE0 WindowToScreenCoordinates(int&,int&)` (delta
0x10) or header `+0xE4 WindowToWindowCoordinates` (delta 0x0C) — but the latter
takes three arguments and only two are passed, so **`WindowToScreenCoordinates` is
the only fit**. ⚠ The direction (window→screen vs screen→window) is inferred from
that fit alone, not measured.

**CALLERS** none direct; vtable only (`0x00AB98AC`).

---

## 6. The pixel pipeline — the four big ones

### sub_7B3300
`0x007B3300 .. 0x007B355C (605 bytes)`  ← **load-bearing for "why Init(520,320) did nothing"**

**PURPOSE** two phases: (1) copy a source bitmap into a destination bitmap **1:1 with
`rep movsd`**; (2) tint the destination along a **format-B** run list.

**CONVENTION** `__usercall void f(IBitmap* src /*EAX*/, IBitmap* dst /*arg0*/,
Vec32* runs /*arg1*/, uint32 color /*arg2*/)` — plain `ret`, **caller pops 12**.
`ecx` is not a `this`.

```c
if (!dst->Lock(0x8080)) return;                       // vt+0x18, ebp = dst
if (!src->Lock(0x800))  goto unlock_dst;              // vt+0x18, ebx = src

// >>> BOTH GetRect calls are on the SOURCE. The destination's size is never read. <<<
int32* a = src->GetRect();  int32* b = src->GetRect();
int w = min( b[2]-b[0], a[2]-a[0] );      // == srcW
int h = min( b[3]-b[1], a[3]-a[1] );      // == srcH

for (int y = 0; y < h; ++y) {
    uint8* s = (uint8*)src->GetBits() + src->GetPitch()*y;   // vt+0x88 / vt+0x8C
    uint8* d = (uint8*)dst->GetBits() + dst->GetPitch()*y;
    memcpy(d, s, w*4);                                        // rep movsd + rep movsb tail
}
```

The double-`GetRect`-on-the-same-object is not a transcription slip — here are the
bytes at `0x007B3334`:

```
8b 03           mov eax,[ebx]        ; ebx = SOURCE (the EAX register argument)
56 57           push esi / push edi
8b cb           mov ecx,ebx
ff 50 30        call [eax+0x30]      ; src->GetRect()   #1
8b 13           mov edx,[ebx]        ; ebx again — NOT ebp
8b cb           mov ecx,ebx
8b f0           mov esi,eax
ff 52 30        call [edx+0x30]      ; src->GetRect()   #2
```

and the copy direction at `0x007B33B0` (`8b 13 … ff 92 8c000000` = `src->GetPitch()`,
`8b 55 00 … ff 92 8c000000` = `dst->GetPitch()` with `ebp` = dst; `esi` ← src,
`edi` ← dst, then `f3 a5 rep movsd es:[edi], [esi]`).

⚠ Note the source is `Lock(0x800)`-ed at `0x7B3329` and **never unlocked** — only
`dst->Unlock(0x8080)` runs at `0x7B3554`. Either `0x800` is a query flag rather than
a lock, or this is a real asymmetry in the game. Unresolved.

The byte-count is `w*4`, computed once as `lea eax,[edx*4]` at `0x7B339E` and
consumed at `0x7B33EA`:

```
0x7B33EA  8b 4c 24 14   mov ecx,[esp+0x14]     ; w*4
0x7B33EE  8b d1         mov edx,ecx
0x7B33F0  c1 e9 02      shr ecx,2
0x7B33F9  f3 a5         rep movsd
0x7B33FB  8b ca / 83 e1 03 / f3 a4   rep movsb  ; tail
```

**There is no scale factor, no stride conversion and no resample anywhere in this
function** — confirming ground truth. Note the `min()` on both axes: if the
destination is larger than the source, the extra pixels are simply never written.

Phase 2 (only if `runs != 0` and `runs->begin != runs->end`):

```c
uint8 c0 = (uint8)(color);            // arg2 byte0
uint8 c1 = (uint8)(color >> 8);       // arg2 byte1
uint8 c2 = (uint8)(color >> 16);      // arg2 byte2 (read as byte [esp+0x3a])

for (uint32* p = runs->begin; p <= runs->end - 4; ) {
    uint32 h0 = p[0], h1 = p[1];  p += 2;
    int row = h0 >> 16, x0 = h0 & 0xFFFF, x1 = h1 & 0xFFFF;
    uint32* line = (uint32*)((uint8*)dst->GetBits() + dst->GetPitch()*row);
    for (int x = x0; x < x1; ++x) {
        uint8 wgt = (*(uint8*)p) >> 1;   p += 1 /*dword*/;    // 0x7B34A7  8a17 d0ea 83c704
        if (!wgt) continue;
        uint32 px = line[x];
        // per-channel: out = ch + ((target - ch)*wgt + 0x80) >> 8   (arithmetic sar!)
        // alpha byte preserved:  eax &= 0xFF000000; eax += packedRGB
        line[x] = (px & 0xFF000000) | blend3(px, c0, c1, c2, wgt);
    }
}
dst->Unlock(0x8080);
```

The `>> 1` on the weight (`d0 ea`) caps the tint at ~50 %. Rounding uses `sar` not
`shr` (`0x7B34D5`, `0x7B34F1`, `0x7B3511`).

**CALLERS** `sub_7B4150` (slice 7).

### sub_7B2A30
`0x007B2A30 .. 0x007B2DCA (923 bytes)`

**PURPOSE** blit an ARGB source bitmap onto a surface along a **format-A** run list,
with source-over alpha. Fully clipped, **1:1** — every mapping is `dst = src + delta`.

**CONVENTION** `__usercall void f(int32 srcRect[4] /*ECX*/, int32 dstRect[4] /*EAX*/,
ISurface* dst /*EDI*/, IBitmap* src /*arg0*/, Vec32* runs /*arg1*/)` — plain `ret`,
**caller pops 8**. `EDI` is a genuine live-in register argument (never initialised).

```c
// 1. clip srcRect against src->GetRect(), and dstRect against dst->GetRect(),
//    always shifting BOTH rects by the same delta  (0x7B2A9E .. 0x7B2B4C)
// 2. bail if the clipped width or height <= 0
if (!dst->Lock(0x8080)) return;                  // vt+0x18
if (!src->Lock(0x40))   goto unlock_dst;         // vt+0x18

for (uint32* p = runs->begin; p != runs->end; )
{
    uint32 h0 = *p++;  int row = h0 >> 16;  int x0 = max(h0 & 0xFFFF, srcRect[0]);
    uint32 h1 = *p++;  int x1 = min(srcRect[2], h1 & 0xFFFF);
    if (row < srcRect[1] || row >= srcRect[3]) continue;
    if (x1 <= x0) continue;

    uint32* line = (uint32*)((uint8*)src->GetBits() + src->GetPitch()*row);
    int dy = row - srcRect[1] + dstRect[1];
    int dxBase = dstRect[0] - srcRect[0];

    if (line[x0] >= 0xFF000000)                  // 0x7B2C49  81 3c 8e 000000ff
    {                                            // WHOLE RUN OPAQUE -> one rect blit
        int32 s[4] = { x0, row, x1, row+1 };
        int32 d[4] = { dxBase+x0, dy, dxBase+x1, dy+1 };
        dst->Blit(src, &s, &d, 0);               // vt+0x74, clip = NULL
    }
    else
    {
        for (int x = x0; x < x1; ++x)
        {
            uint32 px = line[x];
            uint32 a  = px >> 24;
            if (!a) continue;
            uint8 r,g,b;
            dst->GetPixelRGB(dxBase+x, dy, &r, &g, &b);        // vt+0x54
            dst->vt_0x7C( <return of vt+0x54> );               // ⚠ unknown, result unused
            uint32 inv = 255 - a;
            uint32 R = ((px>>16)&0xFF) + ((r*inv + 0x80) >> 8);   // source-over,
            uint32 G = ((px>> 8)&0xFF) + ((g*inv + 0x80) >> 8);   // source PREMULTIPLIED
            uint32 B = ( px     &0xFF) + ((b*inv + 0x80) >> 8);
            R = min(R,255); G = min(G,255); B = min(B,255);
            dst->SetPixel(dxBase+x, dy, dst->MakeColor(R,G,B));  // vt+0x78 then vt+0x58
        }
    }
}
src->Unlock(0x40); dst->Unlock(0x8040);
```

**The opaque test samples only the FIRST pixel of the run** (`line[x0]`). That is
sound only because `sub_7B3670` emits a fresh run whenever the opacity class
changes — the two functions are a matched pair. If anything ever hand-builds a
format-A list without that invariant, this blit will smear.

`add eax, 0x80 / shr eax, 8` is a `x*inv/255` approximation; `x1` and `x0` are
clamped with branchless two-slot `lea` selects at `0x7B2BB6` / `0x7B2BDB`.

**CALLERS** `sub_7B4150` (slice 7).

### sub_7B2DD0
`0x007B2DD0 .. 0x007B302B (604 bytes)`

**PURPOSE** paint a **format-B** run list onto a surface in one solid colour, using
the per-pixel weights. No source bitmap — this is the "highlight/outline" pass.

**CONVENTION** `__usercall void f(int32 dstRect[4] /*EAX*/, ISurface* dst /*ESI*/,
Vec32* runs /*arg0*/, uint32 color /*arg1*/)` — plain `ret`, caller pops 8.

```c
if (runs->begin == runs->end) return;
int32* dr = dst->GetRect();                 // vt+0x30
// clip dstRect against dr; ox/oy come from dstRect[0]/dstRect[1]
if (!dst->Lock(0x8080)) return;

uint8 t0 = (uint8)(color), t1 = (uint8)(color>>8), t2 = (uint8)(color>>16);

for (uint32* p = runs->begin; p <= runs->end - 4; )
{
    uint32 h0 = p[0], h1 = p[1];
    int x0  = (h0 & 0xFFFF) + ox;
    int x1  = (h1 & 0xFFFF) + ox;
    int row = (h0 >> 16)    + oy;
    uint32* wgt = p + 2;
    p = wgt + (x1 - x0);                    // 0x7B2EE5  lea eax,[eax + ebx*4]

    if (row < clipTop || row >= clipBottom) continue;
    x0 = max(x0, clipLeft); x1 = min(x1, clipRight);

    for (int x = x0; x < x1; ++x) {
        uint32 w = *wgt++;                  // FULL DWORD, 0..255
        if (!w) continue;
        uint8 r,g,b;
        dst->GetPixelRGB(x, row, &r, &g, &b);            // vt+0x54
        dst->vt_0x7C(<ret>);                             // ⚠
        r += (uint8)(((t0 - r)*w + 0x80) >> 8);          // lerp toward the colour
        g += (uint8)(((t1 - g)*w + 0x80) >> 8);
        b += (uint8)(((t2 - b)*w + 0x80) >> 8);
        dst->SetPixel(x, row, dst->MakeColor(r,g,b));    // vt+0x78, vt+0x58
    }
}
dst->Unlock(0x8040);
```

⚠ UNSURE about which of the three colour bytes maps to R/G/B — the code reads
`byte[color+0]`, `byte[color+1]`, `byte[color+2]` and feeds them to `MakeColor` in
that order, but the parameter order of `MakeColor` itself is inferred.

**CALLERS** `sub_7B4150` (slice 7).

### sub_7B3670
`0x007B3670 .. 0x007B3A75 (1030 bytes)`  ← **THE PRODUCER**

**PURPOSE** two jobs in one pass over a source bitmap:
1. rewrite every non-opaque pixel **in place**, compositing it over its right and
   below neighbours (an edge/halo fix);
2. emit a **format-A** run list of non-transparent spans into a caller-supplied vector.

**CONVENTION** `__stdcall-ish void f(IBitmap* src /*arg0*/, Vec32* out /*arg1*/)` —
plain `ret`, caller pops 8. No `this`.

```c
int32* r = src->GetRect();                       // vt+0x30
int W = r[2]-r[0], H = r[3]-r[1];
if (W <= 0 || H <= 0) return;

out->end = out->begin;                           // clear  (dead memmove branch, §sub_7B3C10 note)
if (!src->Lock(0x8040)) return;                  // vt+0x18

vector<int32> zeroRow(W);  sub_48C290 / sub_46FE60   // scratch "row below the last row"

for (int y = 0; y < H; ++y)
{
    uint32* cur  = (uint32*)((uint8*)src->GetBits() + src->GetPitch()*y);
    uint32* next = (y < H-1) ? (uint32*)((uint8*)src->GetBits() + src->GetPitch()*(y+1))
                             : zeroRow.begin;            // 0x7B3752 / 0x7B375A
    int state = 0;                                       // 0 = transparent, 1 = partial, 2 = opaque
    for (int x = 0; x < W; ++x)
    {
        uint32 px = cur[x];
        uint32 a  = px >> 24;

        if (px < 0xFF000000)                             // 0x7B37A7
        {
            uint32 below = next[x];
            uint32 right = (x < W-1) ? cur[x+1] : 0;     // 0x7B37BE / 0x7B37CA
            uint32 mix   = source_over(below, right);    // per channel, (c*inv+0x80)>>8
            cur[x]       = source_over(px,   mix);       // written back IN PLACE, 0x7B38E5
        }

        int ns = (a == 0) ? 0 : (a < 255 ? 1 : 2);
        if (ns != state) {
            if (state != 0) push_back(out, (y<<16)|x);   // close the previous run
            if (ns    != 0) push_back(out, (y<<16)|x);   // open the new one
            state = ns;
        }
    }
    if (state) push_back(out, (y<<16)|W);                // close at the row end
}
src->Unlock(0x8040);                                     // vt+0x1C
operator delete(zeroRow.begin);                          // 0x90CF63
```

`push_back` is inlined four times as
`if (end != cap) { *end = v; end += 4; } else vector_grow(0x51CA60, …)`.
The row key is carried as `(y<<16)` in a register and bumped by `add edx, 0x10000`
once per row (`0x7B3A3B`).

⚠ UNSURE on the exact neighbour semantics of the composite: the chain at
`0x7B37CD..0x7B38E5` unambiguously computes `px OVER (below OVER right)` per
channel with `255 - alpha` weights and `+0x80 >> 8` rounding, but *why* it does
that (premultiply? bilinear-safe edge padding?) is inference.

**CALLERS** `sub_7B4150` (slice 7).

---

## 7. Shared library code that merely landed in this address range

**These are NOT region-screen functions.** They are template instantiations and
COM helpers the linker placed here. `sub_7B2480`/`sub_7B24B0` in particular are
called from 15+ sites all over the exe.

### sub_7B2480
`0x007B2480 .. 0x007B24A7 (40 bytes)`
`__thiscall void** f()` — plain `ret`, no stack args.

```c
*this = 0;
void* framework = sub_8793EC();                 // GZCOM accessor -> [0xB540B0]
if (framework)
    framework->vt_0x14(0xC2C2EB0F, 0x22C2EB1F, this);   // GetClassObject(clsid, iid, ppv)
return this;
```
**CALLERS** `0x913C72, 0x993EA8, 0x994554, 0x99530B, 0x9999BA, 0x99A70F, 0x99A96E,
0x99AC7E, 0x99AFA8, 0x99B0EB, 0x9C7A8A, 0x9C7B29, 0x9C7D0A, 0x9C82A2, 0x9D45D8`.

**This corrects an existing project note.** `tools/uimap/emu/POPUP-VERDICT.md:371` and
`tools/research/_incoming/FINAL-3-PERCENT.md:106` describe `sub_913C72` as "the
getter" for singleton `0xC2C2EB0F` with "no literal clsid at the site". The clsid
**is** literal — it is right here at `0x007B249F` (`push 0xC2C2EB0F`), together with
its interface id `0x22C2EB1F` at `0x007B2495`. `sub_913C72` is just one of 15 callers
of this shared helper.

### sub_7B24B0
`0x007B24B0 .. 0x007B24F9 (74 bytes)`
`__thiscall void f()` — plain `ret`. SEH-framed (`push 0xA6F080` handler table at
`0x7B24B5`); body is `if (*this) (*this)->Release();`. The matching smart-pointer
destructor for `sub_7B2480`. **CALLERS** the same 15 plus `sub_7B4150` and `0x7BE7A0`.

### sub_7B24FA
`0x007B24FA .. 0x007B24FF (6 bytes)` — `mov eax, 0x7B24E2 ; ret`. The SEH unwind
funclet for the above; its address is stored in `.data` at `0x00B02AF4`.

### sub_7B31D0
`0x007B31D0 .. 0x007B321E (79 bytes)` — `__cdecl void f(E* first, E* last, const E* v)`.
`std::fill` over `struct E { T* p; uint8 flag; /*pad3*/ }` (stride 8) with proper
AddRef-new / Release-old ordering. `v` is **not** advanced (`ebp` never incremented).
**CALLERS** `sub_7B51D0`.

### sub_7B3220
`0x007B3220 .. 0x007B3288 (105 bytes)` — `__cdecl E* f(E* first, E* last, E* dest)`.
`std::copy`; returns `dest + (last-first)`. Count = `(last-first) >> 3`.
**CALLERS** `sub_7B3D30`.

### sub_7B3290
`0x007B3290 .. 0x007B32F4 (101 bytes)` — `__cdecl E* f(E* first, E* last, E* destEnd)`.
`std::copy_backward`; returns the new dest begin. **CALLERS** `sub_7B51D0`.

### sub_7B35F0
`0x007B35F0 .. 0x007B3629 (58 bytes)` — `__cdecl E* f(E* first, E* last, E* dest)`.
`std::uninitialized_copy`: writes the raw pointer then AddRefs; never Releases the
destination. Skips the element body (but still advances) when `dest == 0`.
**CALLERS** `sub_7B3D80`, `sub_7B51D0`.

### sub_7B3630
`0x007B3630 .. 0x007B3667 (56 bytes)` — `__cdecl E* f(E* dest, uint32 n, const E* v)`.
`std::uninitialized_fill_n`; `n` is unsigned (`jbe` at `0x7B363B`).
**CALLERS** `sub_7B3B60`, `sub_7B3D80`, `sub_7B51D0`.

### sub_7B3B60
`0x007B3B60 .. 0x007B3BC8 (105 bytes)` — `__thiscall Vec* f(uint32 n)`, `ret 4`.
`vector<E>::vector(n)`:

```c
this->begin = this->end = this->cap = 0;
void* p = n ? operator_new(n*8) : 0;             // 0x90CF54, lea eax,[edi*8]
this->cap   = (E*)((char*)p + n*8);
this->begin = this->end = p;
E zero; zero.p = 0;                              // flag byte left UNINITIALISED ⚠
this->end   = sub_7B3630(p, n, &zero, <extra>);
```
The `uninitialized_fill_n` call pushes **four** args (`add esp,0x10` at `0x7B3BBB`);
the fourth is ignored by the callee — an allocator parameter.
**CALLERS** `sub_7B3E80` (slice 7).

### sub_7B3BD0
`0x007B3BD0 .. 0x007B3C04 (53 bytes)` — `__thiscall void f()`, plain `ret`.
`vector<E>::~vector`: Release every element's pointer, then
`operator delete(this->begin)`. **CALLERS** `0x491C90`, `0x4928C0`, `sub_7B3D80`,
`sub_7B51D0` — note two of the four are far outside this module.

---

## 8. Corrections to GROUND TRUTH (the bytes win)

1. **`sub_7B3030` does more than "subtract the pan".** It also subtracts the
   **height of the item's SOURCE bitmap** (`[item+0x1C]`, `vt+0x28 GetHeight`) from
   the Y (`0x7B307B`, `0x7B3090`). Region items are therefore **bottom-anchored**:
   enlarging a tile grows it *upward*, not downward, and the anchor is driven by
   `[item+0x1C]` — **not** by the composite at `[item+0x2C]`. Any attempt to scale
   the region map must move `[item+0x14]` or resize `[item+0x1C]`, or tiles will
   drift vertically by `(newH − oldH)`.

2. **`sub_7B3110` returns an UN-PANNED rect.** It calls `sub_7B3030` and then adds
   `view->panX/panY` back (`0x7B3129`, `0x7B3131`). Net result
   `{floor(fx), floor(fy)-srcH, +srcW, +srcH}`. Ground truth said "item → screen
   rect"; it is item → *region-space* rect.

3. **`[item+0x38]` is not the run list.** Ground truth: *"`[item+0x38..]` a packed
   uint16 alpha run-list"*. In this slice the hit-test mask is at
   **`[item+0x44]` / `[item+0x48]`** (begin/end of a sorted `int32` vector, keys
   `(y<<16)|x`) — read by `sub_7B3A80` at `0x7B3AFD`/`0x7B3B07`. Entries are
   **32-bit, not uint16**, and the pairs are (open, close) positions.
   Nothing in this slice touches `[item+0x38]`. ⚠ It may still be a *different*
   list; I could not confirm or refute `+0x38` from these 36 functions.

4. **`sub_7B2A30` is not "a per-pixel inc/inc loop" only.** It has an **opaque
   fast path** that issues a whole-run `vt+0x74` rectangle blit
   (`0x7B2C49` tests `line[x0] >= 0xFF000000`). Both paths are still strictly 1:1 —
   the conclusion is unchanged, but the mechanism matters if you hook it.

5. **`sub_7B3300` never reads the destination's size.** Both of its `GetRect` calls
   are on the **source** (`ebx`, the EAX register argument) — bytes at `0x007B3334`:
   `ff 50 30` then `8b 13 8b cb … ff 52 30`, both with `ecx = ebx`. The `min()` pair
   is therefore degenerate and the copy extent is exactly `srcW × srcH`, written
   into `dst` at `dst->GetPitch()` stride. **This is the direct explanation of the
   measured failure**: even if `Init(520,320)` had succeeded on the composite, this
   copy would still have written only a 260×160 patch — 3/4 of the enlarged buffer
   would stay blank — and `sub_7B3030` would then have shifted the tile up by 160 px
   because the height it reads (`[item+0x1C]`, the *source*) never changed.
   The mirror hazard is real too: a composite **smaller** than its source overruns.

6. **`sub_7B2480` / `sub_7B24B0` / `sub_7B24FA` are not region-screen code.** They
   are the shared `0xC2C2EB0F` singleton getter and its RAII release. The clsid
   *is* a literal in the instruction stream at `0x007B249F` — see §7, which
   corrects `tools/uimap/emu/POPUP-VERDICT.md:371` and
   `tools/research/_incoming/FINAL-3-PERCENT.md:106`.

7. **`view+0x118` is a plain dword setting** written by `sub_7B30F0`, and
   `view+0x111..+0x116` are five single-byte display flags. Ground truth listed
   "+0x118/+0x11C an item array" — that pairing does not survive here. The item
   pointer array is at **`+0x100`/`+0x104`** (confirmed) and the tile grid is at
   **`+0x10C`** (new).

8. **Our `cIGZWin.h` is missing one virtual** between header slots 30 and 63 — see
   §0.2. Real `EnumChildren = +0x080` (header +0x074, delta 0x0C) but real
   `SetFlag = +0x110`, `SetNotificationTarget = +0x158`, `GZPaint = +0x160`
   (delta 0x10). Any offset our code derives arithmetically across that boundary
   is wrong by 4.

## 9. Open questions this slice could not close

* Who **produces** a format-B run list (8-byte header + one dword per pixel)?
  `sub_7B2DD0` and `sub_7B3300` consume it; `sub_7B3670` produces format A only.
  Look in slice 7 (`sub_7B4150`) or slice 8.
* Identity of the global at `0x00B43DD0` (`vt+0x50` repaint, `vt+0x60`/`vt+0x68`
  paint bracket) and `0x00B43C94` (`vt+0xC4` → lookup table).
* What `IBitmap::vt+0x7C` is — it consumes the return of `vt+0x54` and its own
  result is discarded at both call sites.
* Interface id `0xC989F960` (the tile-grid class's own interface).
* Message ids `0xA2BF8ACD` / `0xA2BF8AD5` / `0xA2BF8AD6`.
* `view+0xE4`, zeroed by `sub_7B3C10` at `0x7B3C29`.
