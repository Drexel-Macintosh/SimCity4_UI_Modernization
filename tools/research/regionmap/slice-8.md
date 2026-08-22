# Region-screen module — SLICE 8 of 8 — `0x007B59B0 .. 0x007B6240`

Scope: every `starts` entry in `tools/uimap/funcs.json` in `[0x7B59B0, 0x7B6060]` inclusive
(11 functions; the last one, `sub_7B6060`, runs to `0x7B6240`).

**Everything in this slice belongs to `cSC4WinRegionView` (clsid `0x2BA6BB97`, vtable
`0x00AB9658`) except `sub_7B5E90` / `sub_7B5EF0`, which are methods of the region view's
private 256×256 TILE CACHE object.** Proof of ownership is in
`sub_7B5C40` (writes `0x00AB9658` to `[this+0]`) and `sub_7B6060` (vtable slot `+0x10` of
`0x00AB9658`, byte-verified: `[0x00AB9668] = 0x007B6060`).

---

## Table of contents

| VA | size | name I am giving it | one line |
|---|---|---|---|
| [`sub_7B59B0`](#sub_7b59b0) | 656 | `RegionView::RebuildItemWindow(item*)` | destroys + recreates the per-city child window from a UI-script resource |
| [`sub_7B5C40`](#sub_7b5c40) | 96 | `RegionView::~RegionView()` | non-virtual dtor; frees tile cache, item array, 2 PNG vec, bg PNG |
| [`sub_7B5CA0`](#sub_7b5ca0) | 176 | `RegionView::InvalidateItem(item*)` | item → **content-space** rect → `TileCache::Invalidate(rect)` → rebuild its window |
| [`sub_7B5D50`](#sub_7b5d50) | 96 | `RegionView::AddItem(item*)` | push_back into the `+0x100` vector, then invalidate + `sub_7B5430` |
| [`sub_7B5DB0`](#sub_7b5db0) | 32 | `RegionView::ClearHover()` | `+0xE4 = 0` then invalidate the old hover item |
| [`sub_7B5DD0`](#sub_7b5dd0) | 80 | `RegionView::SetHoverFromPoint(x,y)` | hit-test via `sub_7B3A80`, swap `+0xE4`, invalidate both |
| [`sub_7B5E20`](#sub_7b5e20) | 80 | `RegionView::SetItemWindowResource(inst, guid)` | sets `+0xF0`/`+0xF4` and rebuilds **every** item window |
| [`sub_7B5E70`](#sub_7b5e70) | 32 | `RegionView::` scalar deleting dtor | `~RegionView(); if (flags&1) operator delete(this)` |
| [`sub_7B5E90`](#sub_7b5e90) | 96 | `TileVec::resize(n)` | element stride **8** = `{IGZBuffer* buf; uint8 dirty;}` — **grows with an uninitialised `dirty` byte** |
| [`sub_7B5EF0`](#sub_7b5ef0) | 368 | `TileCache::Configure(w,h,tw,th,painter)` | **THE tile allocator** — the only `Init(w,h,{fmt,bpp})` call site in this slice |
| [`sub_7B6060`](#sub_7b6060) | 480 | `cSC4WinRegionView::Init()` (vt+0x10) | creates the tile cache at 256×256, loads `region_airport` / `region_seaport` PNGs |

Headline findings are collected in [§ What this slice settles](#what-this-slice-settles).

---

## Shared vocabulary (measured, not assumed)

### `cSC4WinRegionView` fields touched in this slice

| field | evidence | meaning |
|---|---|---|
| `+0x00` | `sub_7B5C40:0x7B5C43` writes `0x00AB9658` | primary vtable |
| `+0x4C` | `vt+0x15C` = `0x0099BE4C` = `8B 41 4C C3` (`mov eax,[ecx+0x4C]; ret`) | context ptr handed to the window callback |
| `+0xD8` | `sub_7B5C40:0x7B5C49` writes `0x00AB9644` | **embedded painter interface** (see below) |
| `+0xDC` | `sub_7B59B0:0x7B5A96` | key passed to `app->vt+0x2C` — Note: region/city-set handle |
| `+0xE0` | `sub_7B5C40` Releases it; `sub_7B6060:0x7B618F` assigns it | a PNG image ref (`{0x856DDBAC, 0x6A1EED2C, 0x4A2805FF}`) |
| `+0xE4` | `sub_7B5DB0`, `sub_7B5DD0` | current **hover/selected item\*** |
| `+0xE8` / `+0xEC` | `sub_7B5CA0:0x7B5CBF/0x7B5CC5` (added), `sub_7B3030:0x7B3047/0x7B3068` (subtracted) | **pan** (int x, int y) — confirms GROUND TRUTH |
| `+0xF0` | `sub_7B5E20` writes; `sub_7B59B0` reads (0 ⇒ early-out) | UI-script **instance id** for a normal item window |
| `+0xF4` | `sub_7B5E20` writes; `sub_7B59B0` passes as arg2 of the factory | second GUID for the item window Note: (window class/type id) |
| `+0x100/+0x104/+0x108` | `sub_7B5D50`, `sub_7B5E20`, `sub_7B5C40` (raw `free`) | `item*` vector `{begin, end, capEnd}`, stride 4 |
| `+0x10C` | `sub_7B6060` creates it; `sub_7B5C40` Releases it | **the 256×256 tile cache** |
| `+0x111` | `sub_7B59B0:0x7B5A72` | Note: "build a window for every item" (else only for `+0xE4`) |
| `+0x112` | `sub_7B59B0:0x7B5ACF` | Note: "build even when the cell has no city" |
| `+0x116` | `sub_7B59B0:0x7B5A32` | Note: "use the alternate art for the player's current city" |
| `+0x11C…` | `sub_7B6060:0x7B619A`, dtor `0x6C6E90` | vector, resized to **2**, holds the airport/seaport PNGs |

### The embedded painter interface at `this+0xD8` (vtable `0x00AB9644`)

Byte-verified table `0x00AB9644`: `{0x007B4140, 0x007BE550, 0x007BE560, 0x007B4150, 0}`.
`0x007B4140` = `81 E9 D8 00 00 00 E9 05 DF EC FF` → `sub ecx,0xD8; jmp 0x00682050` — an
**adjustor thunk back to `cSC4WinRegionView::QueryInterface`** (`0x00682050` is
`[0x00AB9658+0]`). That proves the `+0xD8` block is a second base of the view itself, and
`0x007B4150` is the one real method — the **tile paint callback**. Its first act is
`mov ebp,ecx; mov esi,[ebp+8]` = `view+0xE0` = the background PNG.

`sub_7B6060` hands `&this->0xD8` to `sub_7B5EF0`, which stores it at `tileCache+0x40`
(`sub_7B5300`, the cache dtor, Releases exactly that field). **So the tile cache calls back
into the region view to paint each 256×256 tile.**

### Tile-cache fields (class is unnamed; IID `0xC989F960` from `0x007B23E0`)

Object is `0x44` bytes (`push 0x44; call 0x005E55E0` at `0x7B608C`), vtables
`0x00AB9630` (primary) and `0x00AB9618` (secondary at `+4`).

| field | evidence | meaning |
|---|---|---|
| `+0x0C/+0x10/+0x14` | `sub_7B5E90` (`sar …,3`), `sub_7B2620:0x7B274E` | tile vector, **stride 8** = `{IGZBuffer* buf; uint8 dirty;}` |
| `+0x18/+0x1C` | `sub_7B2620:0x7B2627/0x7B262B` (multiplied by `+0x28`/`+0x2C`) | scroll origin **in tile units** |
| `+0x20/+0x24` | zeroed together with `+0x18/+0x1C` at `0x7B600D..0x7B6016` | Note: second origin / last-drawn origin |
| `+0x28` | `sub_7B5EF0:0x7B5F06` | **tile width** (256) |
| `+0x2C` | `sub_7B5EF0:0x7B5F16` | **tile height** (256) |
| `+0x30` | `sub_7B5EF0:0x7B5F22` | tiles across = `(W-1)/tw + 2` |
| `+0x34` | `sub_7B5EF0:0x7B5F2E` | tiles down  = `(H-1)/th + 2` |
| `+0x38` | `sub_7B5EF0:0x7B5F19` | total content width  (= view width) |
| `+0x3C` | `sub_7B5EF0:0x7B5F1C` | total content height (= view height) |
| `+0x40` | `sub_7B5EF0:0x7B5F46`; released in `sub_7B5300` | the painter interface (`view+0xD8`) |

Tile index = `tileY * [cache+0x30] + tileX` — measured in `sub_7B2620:0x7B2740..0x7B274E`
(`imul esi,edx; add esi,eax; mov byte [ebp+esi*8+4], 1`).

### Globals and constants used in this slice

| addr / value | what the bytes say |
|---|---|
| `[0x00B43C94]` | the SC4 application singleton. Setter at `0x00601C04` = `mov eax,[esp+4]; mov [0xB43C94],eax; mov al,1; ret`. Note: named `cISC4App` by inference from its accessor block at `sub_602290`. |
| `[0x00B43C9C]` | **the graphics system.** Obtained at `0x00602384` from `GetSystemService(0xC416025C, 0x0073283C, &out)`; `0xC416025C` is `kGZGraphicSystem_SystemServiceID` in the class registry. |
| `[0x00B43DD0]` | a render/scene singleton (176 xrefs); also written from `regionScreen+0x168` at `0x007AD0EB`. Note: not fully pinned. |
| `0x008793EC` | `A1 AC 40 B5 00 C3` = `return *(void**)0x00B540AC` — the framework/COM singleton getter. Its `vt+0x14` is `GetSystemService(serviceID, iid, void** out)`. |
| `0xA417445E` | `kGZWinMgrDefaultSysServiceID` (class registry) — the **window manager** service. |
| `0x856DDBAC` | resource **TypeID** used for every image load in `sub_7B6060` (SC4 PNG type). |
| `0x00AB9594` | 12-byte table, 2 entries, iterated by `sub_7B6060`: `{0xEBABB1B0, 0, "region_airport"}`, `{0xEBABB1B1, 1, "region_seaport"}` (strings at `0x00AB95C0` / `0x00AB95B0`, byte-read). |
| `0x00A80AA8` | float `4294967296.0` — the unsigned-to-float fixup in `sub_7B3030` (not in this slice, quoted because it explains the Y math). |

---

<a name="sub_7b59b0"></a>
## `sub_7B59B0` (0x007B59B0..0x007B5C40, 656 bytes) — `RegionView::RebuildItemWindow(item*)`

**PURPOSE** — tear down the child cIGZWin attached to one region item (the city plaque /
name button) and build a fresh one from a UI-script resource, choosing an alternate
resource when the item is the player's current city.

**CONVENTION** — `__thiscall`, `this = cSC4WinRegionView*` in ECX, one stack arg, `ret 4`.
`sub_7B59B0(item*)`. `mov edi,[esp+0x38]` at `0x7B59B7` resolves to the arg slot.

```c
bool RebuildItemWindow(RegionItem* it)          // this = view (ESI)
{
    /* --- 1. drop the existing child window ------------------------------- */
    if (it->win /*+0x30*/) {
        this->vt_0x40(it->win);                 // 0x7B59C9  call [edx+0x40]  Note: RemoveChildWindow
        if (it->win) { it->win = 0; it->win->Release(); }   // vt+0x08
    }

    /* --- 2. where is the player's current city? -------------------------- */
    int cx = -1, cy = -1;                                   // 0x83C8FF -> -1
    void* mgr    = App()->vt_0xC4();                        // [0x00B43C94]
    void* region = App()->vt_0x88();
    void* node   = sub_4B6140(mgr, region->vt_0x20());      // find
    if (node) {
        void* rec = sub_4B5E50(mgr, *(void**)node);         // operator[]
        rec->vt_0x14(&cy, &cx);                             // fills the two ints
    }

    /* --- 3. is THIS item the current city? ------------------------------- */
    bool alt = false;                                       // BL
    if (this->f116 && cx == it->cellX /*+0x08*/ && cy == it->cellY /*+0x0C*/
        && cx >= 0 && cy >= 0 && it != this->hover /*+0xE4*/)
        alt = true;
    else {
        if (this->itemWinInstance /*+0xF0*/ == 0) return;   // FEATURE OFF
        if (!this->f111 && it != this->hover) return;
    }

    /* --- 4. does the cell actually hold a city? -------------------------- */
    void* app   = App()->vt_0x88();
    void* rgn   = app->vt_0x2C(this->fDC /*+0xDC*/);
    void* cell  = rgn->vt_0x2C(it->cellX, it->cellY);       // 0x7B5AB0
    if (cell == 0 || (!alt && !(*(void**)cell)->vt_0xAC()))
        if (!this->f112) return;

    /* --- 5. pick the resource key ---------------------------------------- */
    struct { uint32 a, b, c; } key = { 0, 0x96A006B0, this->itemWinInstance };
    uint32 guid = this->f_F4;                               // +0xF4
    if (alt) { guid = 0x0A551C53; key.c = 0xCA539343; }

    /* --- 6. create the window -------------------------------------------- */
    IGZUnknown* out = 0;
    if (GZ() /*0x8793EC*/)
        GZ()->vt_0x14(0xA417445E /*kGZWinMgrDefaultSysServiceID*/, 0x5A4, &out);
    cIGZWinMgr* wm = (cIGZWinMgr*)out;
    sub_4177F0(&out);                                       // release the smart ref
    void* savedFocus = wm->vt_0x90();                       // Note: GetFocus

    cIGZWin* w = sub_5F9390(&key, this, guid);              // cdecl(3)  UI-script factory

    if (w != it->win) { if (w) w->AddRef(); it->win = w; if (old) old->Release(); }
    if (!it->win) goto restore_focus;
    it->win->vt_0x08();                                     // drop the factory ref

    sub_7B4B80(it, cell);                                   // this = view  (0x7B5B9A)
    it->win->vt_0x80(0x22BA0121, 0x007B2340, this->vt_0x15C() /* = this->f4C */);
                                                            // register callback fn 0x7B2340
    IGZUnknown* iq = 0;
    if (it->win->QueryInterface(0x5386D516, &iq)) {
        void* p = operator_new(0x14);                       // 0x6A14 / call 0x5E55E0
        if (p) sub_7B3560(p);
        iq->vt_0x1C(p);
        iq->Release();
    }
restore_focus:
    if (wm->vt_0x60(savedFocus)) wm->vt_0x94(savedFocus);   // Note: SetFocus if still valid
}
```

**FIELDS** — reads `this+0x111`, `+0x112`, `+0x116`, `+0xDC`, `+0xE4`, `+0xF0`, `+0xF4`,
`+0x4C` (via `vt+0x15C`); reads/writes `item+0x30`; reads `item+0x08`, `item+0x0C`.

**VTABLE CALLS** — `this->vt+0x40` (child removal unsure), `this->vt+0x15C` = `0x0099BE4C`
(byte-verified `mov eax,[ecx+0x4C]; ret`), plus the runtime-typed calls above.

**CONSTANTS** — `0x96A006B0` (resource group), `0xCA539343` / `0x0A551C53` (current-city
overrides), `0xA417445E` + `0x5A4` (winmgr service + iid), `0x22BA0121` + `0x007B2340`
(callback key + fn), `0x5386D516` (iid), `0x14` (alloc size).

**CALLERS** — `0x007B5D34` (in `sub_7B5CA0`), `0x007B5E55` (in `sub_7B5E20`).

Unsure: the meanings of `+0x111`, `+0x112`, `+0x116`; the identities of `vt+0x40`,
`wm->vt+0x60/0x90/0x94`; and that `App()->vt+0x88` is "the region".

---

<a name="sub_7b5c40"></a>
## `sub_7B5C40` (0x007B5C40..0x007B5CA0, 96 bytes) — `RegionView::~RegionView()`

**PURPOSE** — non-virtual destructor body. **CONVENTION** — `__thiscall`, no args, plain
`jmp` tail into the base dtor.

```c
void ~RegionView() {
    *(void**)(this+0x00) = 0x00AB9658;        // 0x7B5C43
    *(void**)(this+0xD8) = 0x00AB9644;        // 0x7B5C49  painter iface
    sub_7B53A0(this);                         // Shutdown  (vt+0x14 of 0xAB9658)
    sub_6C6E90(this+0x11C);                   // destroy the 2-PNG vector
    if (this->tileCache /*+0x10C*/) tileCache->Release();
    if (this->items /*+0x100*/) sub_90CF63(this->items);   // raw free()
    if (this->bgImage /*+0xE0*/) bgImage->Release();
    goto sub_99E1A2;                          // base cGZWin dtor (tail jmp)
}
```

**CALLERS** — `0x007B5E73` (in `sub_7B5E70`). Note: The item array at `+0x100` is released with
a *raw* `free` — the items themselves are not deleted here.

---

<a name="sub_7b5ca0"></a>
## `sub_7B5CA0` (0x007B5CA0..0x007B5D50, 176 bytes) — `RegionView::InvalidateItem(item*)`

**PURPOSE** — compute one item's rectangle and mark the overlapping tiles dirty, then
recreate the item's window. **This is the repaint entry point for a single city tile.**

**CONVENTION** — `__thiscall`, `this = view`, one stack arg (`item*`), `ret 4`.

```c
void InvalidateItem(RegionItem* it)
{
    int x, y;
    sub_7B3030(it, &y, &x);          // 0x7B5CBA  item -> screen point (pan SUBTRACTED)
    x += this->panX /*+0xE8*/;       // 0x7B5CC5 / 0x7B5CD8  -> pan added straight back
    y += this->panY /*+0xEC*/;       // 0x7B5CBF / 0x7B5CD3

    const int* r = it->srcBmp /*+0x1C*/ ->vt_0x30();      // GetRect  (0x7B5CDC)
    Rect box;
    box.left   = x;                                       // r[0] + (x - r[0])
    box.top    = y;                                       // r[1] + (y - r[1])
    box.right  = x + (r[2] - r[0]);
    box.bottom = y + (r[3] - r[1]);

    this->tileCache /*+0x10C*/ -> Invalidate(&box);       // 0x7B5D21  call 0x7B2620
    (*(void**)0x00B43DD0)->vt_0x50();                     // 0x7B5D2E  Note: "needs redraw"
    this->RebuildItemWindow(it);                          // 0x7B5D34  call 0x7B59B0
}
```

**Load-bearing detail.** `sub_7B3030` genuinely subtracts `+0xE8/+0xEC`
(`0x7B3047: fisub [esi+0xE8]`, `0x7B3068: fild [esi+0xEC]` + `fsubr`), and this function
adds them straight back — so the rect handed to the tile cache is in **content space, not
screen space**. `sub_7B3110` does the identical add-back at `0x7B312F` / `0x7B3137`.
The tile cache is therefore addressed in unpanned content coordinates; the pan only picks
which tiles are visible.

**FIELDS** — `+0xE8`, `+0xEC`, `+0x10C`; `item+0x1C` (source bitmap).
**VTABLE** — `srcBmp->vt+0x30` = GetRect (matches GROUND TRUTH), `[0xB43DD0]->vt+0x50`.
**CALLERS** — `0x007B5D91`, `0x007B5DC5`, `0x007B5DFC`, `0x007B5E08`.

---

<a name="sub_7b5d50"></a>
## `sub_7B5D50` (0x007B5D50..0x007B5DB0, 96 bytes) — `RegionView::AddItem(item*)`

**CONVENTION** — `__thiscall`, one stack arg, `ret 4`.

```c
void AddItem(RegionItem* it) {
    if (this->itemsEnd /*+0x104*/ != this->itemsCap /*+0x108*/) {
        if (this->itemsEnd) *this->itemsEnd = it;
        this->itemsEnd += 1;                  // 0x7B5D74  add [ecx+4], 4
    } else {
        sub_51CA60(this+0x100, itemsEnd, &loc1, &loc2, 1, 1);   // vector grow+insert
    }
    InvalidateItem(it);                       // 0x7B5D91
    sub_7B5430(it);                           // 0x7B5D99  this = view (builds the item art)
}
```

Note: The `if (eax)` guard at `0x7B5D6E` protects only the store, not the `+= 4`; that path is
only reachable with a null-but-non-full vector, which cannot happen in practice.
Note: The `sub_51CA60` argument shape (`__thiscall` with 5 stack args, two of which are `lea`s
into the caller's own argument slots) is inferred, not proven.

**CALLERS** — `0x007B18B7` (in `sub_7B13C0`, the region screen's item-list builder).

---

<a name="sub_7b5db0"></a>
## `sub_7B5DB0` (0x007B5DB0..0x007B5DD0, 32 bytes) — `RegionView::ClearHover()`

`__thiscall`, no args, plain `ret`.
`old = this->hover /*+0xE4*/; this->hover = 0; if (old) InvalidateItem(old);`
(the call at `0x7B5DC5` is a fall-through with ECX still = `this`).

**CALLERS** — `0x007ABB70` (`sub_7ABB60`), `0x007AF9AC` (`sub_7AF720`).

---

<a name="sub_7b5dd0"></a>
## `sub_7B5DD0` (0x007B5DD0..0x007B5E20, 80 bytes) — `RegionView::SetHoverFromPoint(a,b)`

`__thiscall`, two stack args, `ret 8`.

```c
void SetHoverFromPoint(int a, int b) {
    RegionItem* hit = sub_7B3A80(a, b);          // 0x7B5DE0  this = view; screen pt -> item
    RegionItem* old = this->hover /*+0xE4*/;
    if (hit != old) {
        this->hover = hit;
        if (hit) InvalidateItem(hit);
        if (old) InvalidateItem(old);
    }
}
```
**CALLERS** — `0x007AB77A` (`sub_7AB760`), `0x007ACB61` (`sub_7ACAD0`).

---

<a name="sub_7b5e20"></a>
## `sub_7B5E20` (0x007B5E20..0x007B5E70, 80 bytes) — `RegionView::SetItemWindowResource(inst, guid)`

`__thiscall`, two stack args, `ret 8`.

```c
void SetItemWindowResource(uint32 inst, uint32 guid) {
    this->itemWinInstance /*+0xF0*/ = inst;      // 0x7B5E3B
    this->itemWinGuid     /*+0xF4*/ = guid;      // 0x7B5E41
    for (item** p = this->items; p != this->itemsEnd; ++p)
        RebuildItemWindow(*p);                   // 0x7B5E55
}
```
Passing `inst == 0` is the documented "off" switch — `sub_7B59B0` early-outs on
`+0xF0 == 0` at `0x7B5A6C`.

**CALLERS** — `0x007AC147` and `0x007AC16B` (both in `sub_7AC110` — two different resource
pairs), `0x007ACC50` (`sub_7ACAD0`), `0x007B18CE` (`sub_7B13C0`).

---

<a name="sub_7b5e70"></a>
## `sub_7B5E70` (0x007B5E70..0x007B5E90, 32 bytes) — scalar deleting destructor

`__thiscall`, one byte-flag arg, `ret 4`, returns `this`.
`~RegionView(); if (flags & 1) operator delete(this) /*0x5E5620*/; return this;`
No code callers. Its only reference in the image is the data word at **`0x00AB98A8`**
(byte-scanned) — a class-descriptor/deleter table, not the `0x00AB9658` vtable.

---

<a name="sub_7b5e90"></a>
## `sub_7B5E90` (0x007B5E90..0x007B5EF0, 96 bytes) — `TileVec::resize(n)`

**PURPOSE** — resize the tile-cache's tile vector. **CONVENTION** — `__thiscall`, `ECX =
&vector` (i.e. `tileCache + 0x0C`), one stack arg, `ret 4`.

```c
void resize(unsigned n) {                 // this = {T* begin; T* end; T* cap;}
    T*  begin = this->begin;              // [ecx]
    T*  end   = this->end;                // [ecx+4]
    int cur   = (end - begin) >> 3;       // 0x7B5EA2  sar edi,3  -> sizeof(T) == 8
    T   fill;  *(uint32*)&fill = 0;       // 0x7B5EA7  ONLY the first dword is zeroed
    if (n < cur)  sub_7B3D30(begin + n*8, end);          // erase tail
    else          sub_7B51D0(end, n - cur, &fill);       // append (n-cur) copies
}
```

Note:→**REAL DEFECT (in the game, not in us).** `sizeof(T) == 8` and `sub_7B51D0` reads *both*
halves of the fill value — `0x007B51D0` contains `8B 0F` (`mov ecx,[edi]`, the pointer) and
`8A 47 04` (`mov al,[edi+4]`, **the dirty byte**). But `sub_7B5E90` only executes
`mov dword ptr [esp+8], 0`, zeroing bytes `[esp+8..esp+0xB]`; the byte at `[esp+0xC]` that
becomes `T::dirty` is **uninitialised stack**. Every tile appended by a grow therefore
starts with a random dirty flag. `sub_7B5EF0` immediately overwrites `T::buf` for every
tile but never touches `T::dirty`, so the garbage survives into the first frame.

**CALLERS** — `0x007B5F8A` only (in `sub_7B5EF0`).

---

<a name="sub_7b5ef0"></a>
## `sub_7B5EF0` (0x007B5EF0..0x007B6060, 368 bytes) — `TileCache::Configure(W, H, tw, th, painter)`

**PURPOSE** — **this is the function that decides how many tile buffers exist and how big
each one is.** It is the only `Init(w, h, {fmt,bpp})` call site in this slice.

**CONVENTION** — `__thiscall`, `ECX = tileCache*`, **five** stack args, `ret 0x14`,
returns `bool` in AL.

```c
bool Configure(int W, int H, int tw, int th, IUnknown* painter)
{
    this->tileW  /*+0x28*/ = tw;
    this->tileH  /*+0x2C*/ = th;
    this->totalW /*+0x38*/ = W;
    this->totalH /*+0x3C*/ = H;
    this->cols   /*+0x30*/ = (W - 1) / tw + 2;      // 0x7B5F00..0x7B5F22
    this->rows   /*+0x34*/ = (H - 1) / th + 2;      // 0x7B5F25..0x7B5F2E

    if (painter != this->painter /*+0x40*/) {       // AddRef/Release swap
        if (painter) painter->AddRef();
        this->painter = painter;
        if (old) old->Release();
    }

    /* ---- pixel format, chosen from the CURRENT VIDEO MODE ---------------- */
    cIGZGraphicSystem* gs = *(void**)0x00B43C9C;
    void* mode = gs->vt_0x20();                     // 0x7B5F5C
    int*  info = mode->vt_0x3C(&scratch);           // 0x7B5F68
    int   depth = info[1];                          // 0x7B5F6B
    int   fmt   = (0x10 < depth) ? 9 : 4;           // 0x7B5F6E..0x7B5F89  sbb/and 5/add 4

    tiles.resize(this->cols * this->rows);          // 0x7B5F8A  call 0x7B5E90

    for (T* t = tiles.begin; t != tiles.end; ++t) { // stride 8
        if (t->buf) { t->buf = 0; t->buf->Release(); }   // ALWAYS destroy first
        if (!gs->vt_0x0C(&t->buf)) goto fail;            // 0x7B5FB6  create a NEW buffer
        struct { int fmt, bpp; } pf;
        pf.fmt = fmt;
        switch (fmt) {                              // jumptable @ 0x007B6038, 8 entries
            case 4: pf.bpp = 0x10; break;           // 0x7B5FDC
            case 9: pf.bpp = 0x20; break;           // 0x7B5FE3
            default: pf.bpp = 0;
        }
        if (!t->buf->vt_0x0C(this->tileW, this->tileH, pf))   // 0x7B5FF9  == Init(w,h,{fmt,bpp})
            goto fail;
    }
    this->f18 = this->f1C = this->f20 = this->f24 = 0;       // 0x7B600D..0x7B6016
    return true;
fail:
    sub_7B5350(this);                                        // 0x7B6027  release all tiles
    return false;
}
```

**Jump table** at `0x007B6038`, byte-read: `7B5FD5, 7B5FDC, 7B5FDC, 7B5FDC, 7B5FDC,
7B5FDC, 7B5FE3, 7B5FE3` (index = `fmt - 2`, range check `cmp eax,7 / ja`). The producing
code can only ever emit `fmt = 4` or `fmt = 9`, so only the `0x10` and `0x20` arms are live;
`fmt = 2` → `bpp 8` is dead in this call path.

**Note:→ THIS EXPLAINS THE MEASURED FAILURE.** The game **never re-Inits a live buffer.** Every
tile that reaches `vt+0x0C` was created by `gs->vt_0x0C` a dozen instructions earlier
(`0x7B5FB6`), and any pre-existing buffer in that slot was nulled and Released first
(`0x7B5FA6..0x7B5FAE`). So "`Init(520,320,{9,0x20})` on an already-initialised 260×160
composite returns 0 and changes nothing" is not a bug in our call — it is the documented
behaviour of the only code path the shipping game exercises. A resize must be
**Release → create → Init**, never **Init again**.

**FIELDS** — writes `+0x28`, `+0x2C`, `+0x30`, `+0x34`, `+0x38`, `+0x3C`, `+0x40`,
`+0x18`, `+0x1C`, `+0x20`, `+0x24`; iterates `+0x0C/+0x10`.
**GLOBALS** — `[0x00B43C9C]` (graphic system, `kGZGraphicSystem_SystemServiceID`).
**CALLERS** — `0x007B611F` (in `sub_7B6060`), `0x007B6296` (in `sub_7B6240`, the next
function past this slice — `[0x00AB9658+0xDC]`, i.e. the view's resize/relayout slot).

---

<a name="sub_7b6060"></a>
## `sub_7B6060` (0x007B6060..0x007B6240, 480 bytes) — `cSC4WinRegionView::Init()`

**PURPOSE** — the region view's `Init`. Vtable-verified: `[0x00AB9668] = 0x007B6060`, i.e.
slot `+0x10` of `0x00AB9658`. **CONVENTION** — `__thiscall`, no args, plain `ret`,
returns `bool` in AL.

```c
bool Init()
{
    if (sub_99BC31(this)) return true;      // this->vt_0x10C(0x4000) -> already inited
    sub_99C2C3(this);                       // mark initialised
    this->vt_0x100(0x2BA6BB97);             // SetID(clsid)  [0x0099BE5C: mov [ecx+0x10],arg]

    /* ---- build the tile cache ------------------------------------------- */
    void* tc = operator_new(0x44);          // 0x7B608C  push 0x44; call 0x5E55E0
    if (tc) {
        sub_90DA1E((char*)tc + 4);          // base ctor of the secondary interface
        *(void**)tc       = 0x00AB9630;     // primary vtable
        *(void**)(tc + 4) = 0x00AB9618;     // secondary vtable
        tc->f0C = tc->f10 = tc->f14 = 0;    // empty tile vector
        tc->f40 = 0;                        // no painter yet
    }
    swap_with_addref(this->tileCache /*+0x10C*/, tc);

    if (!sub_7B5EF0(this->tileCache,
                    this->vt_0xA4(),        // 0x0099C81B = [this+0xB0] - [this+0xA8]  == WIDTH
                    this->vt_0xA8(),        // 0x0099C82A = [this+0xB4] - [this+0xAC]  == HEIGHT
                    0x100, 0x100,           // 256 x 256 tiles
                    (char*)this + 0xD8))    // the embedded painter interface
        return false;

    (*(void**)0x00B43DD0)->vt_0x80(this->tileCache, 0, 0x3E8);   // 0x7B6145  register @ z=1000 (note)
    this->vt_0x110(0x00010000, 0);          // SetFlag  (0x0099DB6B, touches [this+0xC8])
    this->vt_0x110(0x00008000, 0);          // SetFlag

    /* ---- images ---------------------------------------------------------- */
    sub_602B70(&tmp, 0x856DDBAC, 0x6A1EED2C, 0x4A2805FF, 1, 0);  // load PNG
    if (tmp.p) sub_5447B0(&this->bgImage /*+0xE0*/, tmp.p);

    vector_resize(this+0x11C, 2);           // 0x7B61A8  call 0x4C1390
    for (i = 0; i < 2; ++i) {               // table 0x00AB9594, stride 0x0C, end 0x00AB95AC
        sub_602B70(&tmp2, 0x856DDBAC, 0x46A006B0, kTable[i].id, 1, 0);
        swap_with_addref(((void**)*(void**)(this+0x11C))[i], tmp2.p);
        sub_602BE0(&tmp2);
    }
    sub_602BE0(&tmp);
    return true;
}
```

**Byte-verified accessors used for the tile-cache size**

| | bytes | meaning |
|---|---|---|
| `vt+0xA4` = `0x0099C81B` | `8B 81 B0 00 00 00  81 C1 A8 00 00 00  2B 01  C3` | `[this+0xB0] - [this+0xA8]` = **client width** |
| `vt+0xA8` = `0x0099C82A` | `8B 81 B4 00 00 00  2B 81 AC 00 00 00  C3` | `[this+0xB4] - [this+0xAC]` = **client height** |

So the tile grid is sized from the **window's own rect**, in 256-px tiles:
`cols = (W-1)/256 + 2`, `rows = (H-1)/256 + 2`. At 1024×768 that is 6×5 = 30 tiles of
256×256; at 2048×1536 it is 10×8 = 80. **Nothing in this path scales with a UI factor —
it scales with the window rect only.**

**The two PNGs** (table `0x00AB9594`, strings byte-read):
`{0x856DDBAC, 0x46A006B0, 0xEBABB1B0}` = `region_airport`,
`{0x856DDBAC, 0x46A006B0, 0xEBABB1B1}` = `region_seaport`, landing in `this+0x11C[0..1]`.
A third PNG `{0x856DDBAC, 0x6A1EED2C, 0x4A2805FF}` lands in `this+0xE0` and is the image the
tile painter `0x007B4150` reads first (`mov esi,[ebp+8]` with `ebp = this+0xD8`).

**CALLERS** — none in code; reached through vtable slot `+0x10` of `0x00AB9658`
(data word at `0x00AB9668`, byte-scanned).

Unsure: `[0x00B43DD0]->vt+0x80(cache, 0, 1000)` — I read it as registering the tile cache
as a draw layer with a sort key of 1000, but I have not proven that.

---

<a name="what-this-slice-settles"></a>
## What this slice settles

1. **The region map has a tiled backing store.** `cSC4WinRegionView+0x10C` is a tile cache of
   256×256 `IGZBuffer`s, `cols = (W-1)/256 + 2` by `rows = (H-1)/256 + 2`, sized from the
   window's client rect (`vt+0xA4`/`vt+0xA8`) and rebuilt wholesale by `sub_7B5EF0`.
   The 256 constants are **immediates** at `0x007B60FF` and `0x007B6104`.
2. **Tiles are painted by the view itself** through the embedded interface at `view+0xD8`
   (vtable `0x00AB9644`, method `0x007B4150`), stored at `cache+0x40`.
3. **The engine never re-Inits a live buffer** — the only `Init(w,h,{fmt,bpp})` in this slice
   (`0x007B5FF9`) always runs on a buffer created moments earlier at `0x007B5FB6`, with any
   previous occupant Released first. That is the complete explanation of the measured
   `Init(520,320,…) → 0` failure. Resize = Release + create + Init.
4. **Pixel format is video-mode-derived, not fixed**: `fmt = 9 / bpp = 0x20` only when the
   current mode's depth > 16; otherwise `fmt = 4 / bpp = 0x10` (`0x007B5F6E..0x007B5F89`,
   jump table `0x007B6038`).
5. **Item rects handed to the tile cache are content-space, not screen-space** — the pan at
   `+0xE8/+0xEC` is subtracted by `sub_7B3030` and added straight back by both
   `sub_7B5CA0` (`0x007B5CC5`/`0x007B5CD8`) and `sub_7B3110` (`0x007B312F`/`0x007B3137`).
6. **The per-city plaque is a real cIGZWin built from a UI script**, group `0x96A006B0`,
   instance `view+0xF0` (or `0xCA539343` for the player's own city), created by the cdecl
   factory `sub_5F9390` — so it is reachable by the normal window-tree scaling machinery,
   unlike the tile bitmaps.
