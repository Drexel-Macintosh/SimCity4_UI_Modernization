# SC4 Region Screen — Slice 5 of 8: `0x007B0470 .. 0x007B2320`

SimCity 4 Deluxe 1.1.641, image base 0x400000. Every VA below was read out of
`SimCity 4.exe` in this pass; anything inferred is tagged `⚠ UNSURE`.

This slice is the **lifecycle spine** of `cSC4WinRegionScreen`: its constructor,
destructor, `Init`, `Shutdown`, `DoMessage`, the chrome-construction pass, the
item-vector plumbing, and — most importantly — **`sub_7B13C0`, the function that
creates one item per city and computes its screen position.**

---

## Table of contents

| VA | size | name / purpose |
|---|---|---|
| [`sub_7B0470`](#sub_7b0470) | 1664 | `BuildChrome()` — creates the region-screen HUD from two `.UI` scripts, docks it, wires the three view-mode radios |
| [`sub_7B0AF0`](#sub_7b0af0) | 192 | `cIGZMessageTarget2::DoMessage(cIGZMessage2*)` (the `this+0xDC` sub-object) |
| [`sub_7B0BB0`](#sub_7b0bb0) | 80 | `ItemVector::erase(first,last)` — 0x80 stride |
| [`sub_7B0C00`](#sub_7b0c00) | 544 | **`cSC4WinRegionScreen::cSC4WinRegionScreen()`** — the constructor / full field map |
| [`sub_7B0E20`](#tiny-adjustor-thunks) | 16 | adjustor thunk `this-0xD8` → `QueryInterface` 0x7AA640 |
| [`sub_7B0E30`](#tiny-adjustor-thunks) | 16 | adjustor thunk `this-0xDC` → `QueryInterface` 0x7AA640 |
| [`sub_7B0E40`](#tiny-adjustor-thunks) | 16 | adjustor thunk `this-0xDC` → `AddRef` 0x7BE160 |
| [`sub_7B0E50`](#tiny-adjustor-thunks) | 16 | adjustor thunk `this-0xDC` → `Release` 0x7BE170 |
| [`sub_7B0E60`](#sub_7b0e60) | 256 | `ItemVector::_Insert_n_realloc(...)` — grow + move, 0x80 stride |
| [`sub_7B0F60`](#sub_7b0f60) | 672 | **`cSC4WinRegionScreen::Shutdown()`** (vtable `+0x14`) |
| [`sub_7B1200`](#sub_7b1200) | 448 | `~cSC4WinRegionScreen()` (scalar dtor body) |
| [`sub_7B13C0`](#sub_7b13c0) | 1344 | **`BuildCityItems()` — THE TILE BUILDER.** one item per city; the iso-basis position math; loads the savegame thumbnails; calls the compositor |
| [`sub_7B1900`](#sub_7b1900) | 2592 | **`cSC4WinRegionScreen::Init()`** (vtable `+0x10`) |

---

## 0. Facts established in this slice (the short version)

* **Vtable `0x00AB9260` slot `+0x10` = `sub_7B1900` (Init), slot `+0x14` = `sub_7B0F60` (Shutdown).**
  Read from the binary at `0xAB9270` / `0xAB9274`. (Ground truth "Init = sub_7B1900" **confirmed**.)
* **The four iso-basis floats are exactly as ground truth says** — verified byte-for-byte:

  | VA | bytes | value |
  |---|---|---|
  | `0x00B0DBA4` | `1f 05 b5 42` | `+90.51000213623047` |
  | `0x00B0DBA8` | `00 00 96 41` | `+18.75` |
  | `0x00B0DBAC` | `c3 f5 15 c2` | `-37.4900016784668` |
  | `0x00B0DBB0` | `00 00 35 42` | `+45.25` |

  Neighbours, not used by this slice but adjacent and probably related:
  `0x00B0DBBC = 0.0883883461356163` (`3d b5 04 f3`), `0x00B0DBC0 = 0.0183058250695467` (`3c 95 f6 19`).
* **The item's stored screen position is computed ONCE, in `sub_7B13C0` at `0x007B15D8` / `0x007B15EF`**,
  and the inputs are region **cell** indices — never pixels, never a resolution, never a zoom factor.
  There is no scale term anywhere in the expression.
* **Every tile-image dimension in this slice comes out of the city's savegame file.**
  `sub_7B13C0` calls `sub_5DDA40(path, &item+0x1C, &item+0x20, &item+0x24, &item+0x28)` which
  opens the `.sc4` file and hands back four bitmaps. Nothing resamples them.
* **The only place the game itself calls `Init(w,h,{9,0x20})` on a tile buffer in this slice is
  `0x007B1DA1..0x007B1DB9`, and it does so on a *brand-new* object** (created two instructions
  earlier), with `Init(1, 1, {9,0x20})`. That is consistent with the measured failure
  (Init on an already-initialised 260x160 composite returns 0): the game never re-Inits.
* `this+0x154` is the **cIGZGraphicSystem** (`kGZGraphicSystem_SystemServiceID = 0xC416025C`),
  copied from global `[0x00B43C9C]` in Init at `0x007B1AA9`.

---

## Globals this slice touches

| global | set at | what it is |
|---|---|---|
| `0x00B43C94` | `0x00601C04` (a setter) | the app / game singleton. `vt+0x88` → region manager, `vt+0x98` → user-preferences object |
| `0x00B43C9C` | `0x00602384` | `cIGZGraphicSystem` (`GetClass(0xC416025C, iid 0x0073283C)`) |
| `0x00B43CA8` | `0x006023E8` | system service `GetClass(0x056B906E, iid 0x656B8EFC)` — the resource/UI-script loader ⚠ |
| `0x00B43CB0` | `0x006022D6` | **`kGZCommandServerSysServiceID` (0xEB903A32)** — the command server (`vt+0x18` = AddCommand, `vt+0x24` = RemoveCommand) |
| `0x00B43CCC` | `0x006024BB` | **`kDefaultSysServiceID` (0x04FA845B)** — the message server (`vt+0x10` = MessageSend) |
| `0x00B43CD8` | `0x00602310` | cached `[0xB43C94]->vt+0x98()` = the **user-preferences** object |
| `0x00B43CF8` | `0x00601C39`, `0x007ACDBD`, `0x007AC42E` | the terrain / region grid object (ground truth: ctor `sub_7AACE0`) |

Class ids resolved from the registry at `0x00B05000..0x00B0B000`:

```
0xEA659793 cSC4WinRegionScreen        0x2BA6BB97 cSC4WinRegionView
0xC9C628EC cSC4CameraControl          0xC416025C kGZGraphicSystem_SystemServiceID
0xEB903A32 kGZCommandServerSysServiceID   0x04FA845B kDefaultSysServiceID
0xABB5BB44 kSC4MessagePreRegionInit    0xCBB5BB45 kSC4MessagePostRegionInit
0x8BB5BB46 kSC4MessagePreRegionShutdown 0x8BB5BB4B kSC4MessagePostRegionShutdown
0x231BBF91 kMessageTypePreferencesChanged
0x2B96B3EA kSC4MessagePostAppServicesInit
0x2A3AD653 kMessageSetRadioStation
```

---
---

## sub_7B0470

`sub_7B0470  (0x007B0470..0x007B0AF0, 1664 bytes)`

**PURPOSE** — Build/refresh the region screen's chrome: instantiate two child windows from
`.UI` script resources, dock them relative to the screen's own size, register their button
callbacks, bind the three view-mode radio buttons, and push the saved view mode into the
`cSC4WinRegionView`.

**CONVENTION** — `__thiscall void BuildChrome(cSC4WinRegionScreen* this /*ecx*/)`. No args.

**CALLERS** — one direct site: `0x007B21A3` in `sub_7B1900` (Init).

### The two `.UI` scripts (load-bearing)

```
0x007B04B0  push 0x09EBE9EE                 ; window id
0x007B04BF  mov [esp+0x44], 0x96A006B0      ; TGI.group  = 0x96A006B0  (the UI-script group)
0x007B04C7  mov [esp+0x48], 0xAA920991      ; TGI.instance
            ( [esp+0x40] = 0 = TGI.type )
0x007B04CF  call 0x005F9390                 ; cdecl(TGI*, cIGZWin* parent=this, uint32 winID)
```

```
0x007B0732  push 0x0BB0F5E7                 ; window id
0x007B0741  mov [esp+0x38], 0x96A006B0      ; TGI.group
0x007B0749  mov [esp+0x3C], 0xABC0ED33      ; TGI.instance
0x007B0751  call 0x005F9390
```

So the region screen's chrome is **two `.UI` resources, group `0x96A006B0`,
instances `0xAA920991` and `0xABC0ED33`**, given window ids `0x09EBE9EE` and `0x0BB0F5E7`.
⚠ `sub_5F9390` is inferred to be "create-child-window-from-UI-script"; the evidence is that its
return value is used exclusively as a `cIGZWin*` (SetPosition / SetFlag / AddNotification / Release).

### Pseudo-C

```c
void cSC4WinRegionScreen::BuildChrome()
{
    ListHdr* saved = new_list_header(0x14);        // 0x90CF54 = operator new
    sub_78E990(this, &saved);                      // cdecl(this, &list) — snapshot current chrome ⚠

    // ---- panel A ---------------------------------------------------------
    GZTGI tgiA = { 0, 0x96A006B0, 0xAA920991 };
    cIGZWin* a = sub_5F9390(&tgiA, this, 0x09EBE9EE);
    if (a) {
        int W  = this->vt_0xA4();               // GetWidth  (screen)
        int H  = this->vt_0xA8();               // GetHeight (screen)
        /* a->vt_0xA4() result discarded */
        int ah = a->vt_0xA8();                  // child height
        int x  = ((W > 3*H) ? (W/3) : 0) + 5;   // 0x007B0517: magic-div 0xAAAAAAAB, shr edx,1
        int y  = (H - ah) + 2;
        a->vt_0xE0(x, y);                       // SetPosition
        a->vt_0x5C();                           // relayout / commit ⚠
        a->vt_0x80(0x22BA0121, 0x007AAB10, this);   // AddNotification(kind, callback, ctx)
        a->vt_0x110(0x800, 0);                  // SetFlag(0x800 /*visible*/, false)
        a->vt_0x08();                           // Release
    }

    sub_78F3C0(this, &tmp, &tmp);               // cdecl
    sub_78E610(&tmp2, this);                    // cdecl

    // two other panels get the same notification hookup
    for (id in { 0x6A91DC16, 0x6A91DC15 }) {
        cIGZWin* w = this->vt_0x8C(id);         // GetChildWindowFromIDRecursive ⚠
        if (w) w->vt_0x80(0x22BA0121, 0x007AAB10, this);
    }

    // ---- three view-mode button PAIRS -----------------------------------
    // this+0xEC[3] and this+0xF8[3]  (both arrays are 3 x cIGZWin*)
    for (int i = 0; i < 3; ++i) {
        uint32 base = (i==0) ? 0x09EBEE45
                    : (i==1) ? 0xEA54DF28
                    :          0x09EBEE60;
        cIGZWin* w = this->vt_0x88(base);       // GetChildWindowFromID
        if (!w) continue;
        REPLACE_REF(this->field_EC[i], w);      // AddRef new / Release old
        w->vt_0x118();
        w->vt_0x80(0x22BA0121, 0x007AAB10, this);
        cIGZWin* w2 = this->vt_0x88(base + 1);
        if (!w2) continue;
        REPLACE_REF(this->field_F8[i], w2);
        w2->vt_0x118();
    }

    // ---- the 0x09EBE9EE panel is shown, then hidden again ---------------
    cIGZWin* p = this->vt_0x88(0x09EBE9EE);
    p->vt_0x110(0x800, 1); p->vt_0x5C(); p->vt_0x110(0x800, 0);

    // ---- gate a control on the region-manager state ---------------------
    void* rm = (*(void**)0x00B43C94)->vt_0x88();
    if (rm->vt_0x18() <= 1) {                       // 0x007B070B: cmp eax,1 / ja
        cIGZWin* c = this->vt_0x8C(0x2A5B0002);
        c->vt_0x110(2, 0);                          // SetFlag(2 /*enabled*/, false)
    }

    // ---- panel B (0x0BB0F5E7), docked bottom-right ----------------------
    GZTGI tgiB = { 0, 0x96A006B0, 0xABC0ED33 };
    cIGZWin* b = sub_5F9390(&tgiB, this, 0x0BB0F5E7);
    if (b) {
        int y = (this->vt_0xA8() - b->vt_0xA8()) - 5;   // 0x007B0773: ebx = -5 - childH; += screenH
        int x = (this->vt_0xA4() - b->vt_0xA4()) - 5;
        b->vt_0xE0(x, y);                              // SetPosition
        b->vt_0x5C();
        b->vt_0x80(0x22BA0121, 0x007AAB10, this);
        b->vt_0x110(0x800, 0);
        b->vt_0x118();
        b->vt_0x08();
    }

    // ---- optional panel 0x6BB92BCA, docked bottom-right with -10 inset --
    if (sub_9AFCDE(b, 0x6BB92BCA, 0x22BA0121, &out)) {   // cdecl 4 args
        cIGZWin* c = out;
        int y = (this->vt_0xA8() - c->vt_0xA8()) - 10;   // 0x007B0827: ebx = -10 - h
        int x = (this->vt_0xA4() - c->vt_0xA4()) - 10;
        c->vt_0xE0(x, y);
        c->vt_0x5C();
        c->vt_0x80(0x22BA0121, 0x007AAB10, this);
        c->vt_0x110(0x800, 0);
        c->vt_0x118();
    }

    sub_7AEC00(this);                                // ⚠ (neighbouring slice)

    // ---- push the saved view mode into the view --------------------------
    void* region = rm->vt_0x2C(this->field_1A4);      // region for the current region id
    cIGZWin* q   = this->vt_0x8C(0xEA5BD179);
    q->vt_0x128( region->vt_0x0C() );

    Prefs* pr = (*(void**)0x00B43C94)->vt_0x98();
    bool  f04 = pr->byte_F04 != 0;
    bool  f05 = pr->byte_F05 != 0;
    this->field_1A8 = (uint32)f05;
    sub_7B30D0(this->view /*+0xE0*/, f04);           // view: set flag A

    // checkbox 0xEA5A96E6 <- f04 ; checkbox 0xCA5CFEE2 <- 0
    // three radios from the table at 0x00AB8B70:
    //     { 0xABA290E1, 0xCBA290EC, 0xABA290F6 }
    uint8 mode = pr->[base+0x4A];                    // base = pr + 0xEBC
    if (mode >= 3) mode = 0;                         // 0x007B09C7: cmp al,3 / jae
    for (int i = 0; i < 3; ++i) {
        if (this->vt_0x94(((uint32*)0x00AB8B70)[i], 0x8810, &out))
            out->vt_0x24( mode == i );               // set radio checked
    }
    sub_7B30F0(this->view /*+0xE0*/, mode);          // view: set view mode

    // enable/disable two panels from this+0x1FD
    sub_9AFCFE(this, 0x0BB0F5E7, (this->byte_1FD && mode != 0), 1);
    sub_9AFCFE(this, 0x6BB92BCA, (this->byte_1FD && mode != 0), 1);

    sub_7AC110(this);                                 // ⚠ (neighbouring slice)
    ...free the saved-chrome list...
}
```

**FIELDS**
| field | r/w | meaning |
|---|---|---|
| `+0xE0` | r | the `cSC4WinRegionView` (passed as `this` to `sub_7B30D0` / `sub_7B30F0`) |
| `+0xEC[3]` | rw | three view-mode button windows (ids `0x09EBEE45 / 0xEA54DF28 / 0x09EBEE60`) |
| `+0xF8[3]` | rw | their sibling windows (`id + 1`) |
| `+0x1A4` | r | current **region id** (see Init) |
| `+0x1A8` | w | `= (prefs.byte_F05 != 0)` |
| `+0x1FD` | r | a "chrome enabled" boolean |

**CONSTANTS** — `0x96A006B0` (UI-script group), `0xAA920991`, `0xABC0ED33` (script instances),
window ids `0x09EBE9EE 0x0BB0F5E7 0x6BB92BCA 0x6A91DC15 0x6A91DC16 0xEA5A96E6 0xCA5CFEE2
0xEA5BD179 0x2A5B0002 0x09EBEE45 0xEA54DF28 0x09EBEE60`, notification kind `0x22BA0121`
with callback `0x007AAB10`, radio-id table `0x00AB8B70 = {0xABA290E1, 0xCBA290EC, 0xABA290F6}`.

> **Relevance to "region map unusably small at 2x/3x":** this is the function that positions the
> region-screen chrome, and it does so **in raw pixels relative to `GetWidth()/GetHeight()`**
> (`+5`, `-5`, `-10`, `W/3`, `H-childH+2`). It contains **no** tile-size code — the map itself is
> not sized here.

---

## sub_7B0AF0

`sub_7B0AF0  (0x007B0AF0..0x007B0BB0, 192 bytes)`

**PURPOSE** — `cIGZMessageTarget2::DoMessage`. Sits at `0x00AB9248` = slot `+0x0C` of the
4-slot vtable `0x00AB923C`, which the ctor writes into `this+0xDC`.

**CONVENTION** — `__stdcall bool DoMessage(cIGZMessage2* msg)`; `ecx` = **`this+0xDC`**
(no adjustor — the function itself does `lea ecx,[edi-0xDC]` at `0x007B0B32` to get the real `this`).
`ret 4`.

```c
bool DoMessage(cIGZMessage2* msg)      // ecx = (char*)screen + 0xDC
{
    char* sub = (char*)ecx;
    uint32 type = msg->vt_0x10();                      // GetType

    cIGZUnknown* std = 0;
    if (msg->vt_0x00(0x4B99446A, &std)) {              // QueryInterface
        uint32 b = msg->vt_0x28();
        uint32 c = msg->vt_0x3C();
        sub_7AF720(sub - 0xDC, type, b, c);            // __thiscall(screen, type, b, c)
    }
    else if (type == 0x231BBF91 /*kMessageTypePreferencesChanged*/) {
        Prefs* p = (*(void**)0x00B43C94)->vt_0x98();
        cIGZWin* w = *(cIGZWin**)(sub + 0x08);         // == screen+0xE4
        if (w) w->vt_0x110(1, p->byte_F11 != 0);       // SetFlag(1, bool)
    }
    else if (type == 0x2B96B3EA /*kSC4MessagePostAppServicesInit*/) {
        sub_7CC5B0( *(void**)(sub + 0x88) );           // == screen+0x164  == the CAMERA
        cIGZWin* w = *(cIGZWin**)(sub + 0x0C);         // == screen+0xE8
        w->vt_0x110(1, 1);
    }
    if (std) std->Release();
    return true;
}
```

**Field decode (relative to the sub-object at `this+0xDC`)** — `[edi+0x88] = screen+0x164` = the
`cSC4CameraControl` (**ground truth confirmed**), `[edi+0x0C] = screen+0xE8`,
`[edi+0x08] = screen+0xE4`.

**CALLERS** — vtable only (`0x00AB9248`).

---

## sub_7B0BB0

`sub_7B0BB0  (0x007B0BB0..0x007B0C00, 80 bytes)`

**PURPOSE** — `std::vector<RegionItem>::erase(first, last)` for the **0x80-byte item**.

**CONVENTION** — `__thiscall Item* erase(ItemVec* this /*ecx*/, Item* first, Item* last)`, `ret 8`.

```c
Item* ItemVec::erase(Item* first, Item* last)
{
    Item* newEnd = sub_7AE9B0(last, this->_Mylast, first, &first, 0);  // move tail down
    for (Item* p = newEnd; p != this->_Mylast; p += 0x80)              // 0x007B0BE7: add esi,0x80
        sub_7ADA00(p);                                                 // ~Item()
    this->_Mylast = newEnd;                                            // [this+4]
    return first;
}
```

**FIELDS** — `[this+0x00] = _Myfirst`, `[this+0x04] = _Mylast`, `[this+0x08] = _Myend`.
When called from Shutdown, `this` = `screen + 0x118`, i.e. **the item array lives at
`screen+0x118 / +0x11C / +0x120`** (ground truth `+0x118/+0x11C` confirmed, `+0x120` is the
capacity end).

**CALLERS** — `0x007B10AC` in `sub_7B0F60`.

---

## sub_7B0C00

`sub_7B0C00  (0x007B0C00..0x007B0E20, 544 bytes)`

**PURPOSE** — **`cSC4WinRegionScreen::cSC4WinRegionScreen()`**. This is the authoritative field
map for the class: every member it writes is listed below with its literal initialiser.

**CONVENTION** — `__thiscall cSC4WinRegionScreen* ctor(void* this /*ecx*/)`, no args, returns `this`.

**CALLERS** — `0x004E0D62` in `sub_4E0D40` (the factory / `New`).

```c
cSC4WinRegionScreen::cSC4WinRegionScreen()
{
    sub_99D938(this);                        // base ctor (cSC4WinScreen / cGZWin)
    // base ctor left 0xA86864 @ +0xD8 and 0xA81174 @ +0xDC — we override all three:
    *(void**)(this + 0x000) = (void*)0x00AB9260;   // main vtable
    *(void**)(this + 0x0D8) = (void*)0x00AB924C;   // { QI-thunk 7B0E20, 7BE550, 7BE560, 62C980 }
    *(void**)(this + 0x0DC) = (void*)0x00AB923C;   // { 7B0E30, 7B0E40, 7B0E50, DoMessage 7B0AF0 }

    +0x0E0 = 0;  +0x0E4 = 0;  +0x0E8 = 0;          // 3 child cIGZWin* (view, ?, ?)
    +0x0EC = +0x0F0 = +0x0F4 = 0;                  // view-mode button array [3]
    +0x0F8 = +0x0FC = +0x100 = 0;                  // sibling array [3]
    +0x104 = 0;  +0x108 = 0;
    sub_913603(this + 0x10C);                      // ctor of a container at +0x10C
    +0x118 = +0x11C = +0x120 = 0;                  // ITEM VECTOR (first,last,end)
    +0x124 .. +0x150 = 0;                          // 12 x cIGZBitmap* = 6 PAIRS of default tiles
    +0x154 = 0;                                    // cIGZGraphicSystem*  (filled in Init)
    +0x158 .. +0x194 = 0;                          // 16 more pointers/ints
    +0x198 = 0x96 (150);  +0x19C = 0x96 (150);
    +0x1A0 = (byte)0;  +0x1A1 = (byte)0x80;  +0x1A2 = (byte)0x40;
    +0x1A4 = 0;                                    // current region id
    +0x1A8 = 1;
    +0x1B0 = 0x00808080;  +0x1B4 = 0x00FFFF00;     // two RGB colours
    sub_88FEDF(this + 0x1B8, 4);                   // container, elem/bucket = 4
    sub_88FEDF(this + 0x1D0, 4);                   // container, elem/bucket = 4
    +0x1E8 = 0;
    +0x1EC = 0x40A00000f  =    5.0f;               // ⚠ looks like a min zoom / near clip
    +0x1F0 = 0x44960000f  = 1200.0f;               // ⚠ looks like a max zoom / far clip
    +0x1F4 = 0;  +0x1F8 = 0;
    +0x1FC = (byte)0;  +0x1FD = (byte)0;
    sub_99DB6B(this, 0x200000, 1);                 // base SetFlag(0x200000, true)
    sub_99DB6B(this, 0x010000, 0);                 // base SetFlag(0x010000, false)
    +0x010 = 0xEA659793;                           // clsid  (cSC4WinRegionScreen)
    sub_913628(this + 0x10C, (void*)0x00AB8B88, 0x11);   // 17 notification ids, see below
    return this;
}
```

`+0x10C` is seeded with the **17-entry id table at `0x00AB8B88`**:

```
[ 0] 0xC53D10AA   [ 1] 0x231BBF91 kMessageTypePreferencesChanged
[ 2] 0x2B96B3EA kSC4MessagePostAppServicesInit
[ 3] 0x6A935E3C kCommandID_QuitGame          [ 4] 0x6A9757C2 kCommandID_RegionBitmapLoad
[ 5] 0x6A935CD8 (ScrollLeft)                 [ 6] 0x2A948275 kCommandID_ScrollLeftStop
[ 7] 0x2A94826E (ScrollRightStop)            [ 8] 0x6A935CE0 (ScrollRight)
[ 9] 0x6A935CDD (ScrollUp)                   [10] 0x2A948272 (ScrollUpStop)
[11] 0x2A94826B (ScrollDownStop)             [12] 0x6A935CE2 (ScrollDown)
[13] 0x6AA9FE51 kCommandID_SetExpandedToolTips
[14] 0x0BB3C277 kCommandID_LoadRegion        [15] 0x0BB2747D kCommandID_LoadCity
[16] 0x6A935CF1 kCommandID_Cancel
```

⚠ `0x00B0DBBC/0x00B0DBC0` (0.088388/0.018306) sit two dwords past the iso basis and are **not**
referenced by this slice.

---

## Tiny adjustor thunks

| VA | bytes | meaning |
|---|---|---|
| `sub_7B0E20` | `81 e9 d8 00 00 00 / e9 15 98 ff ff` | `this -= 0xD8; jmp 0x007AA640` — QueryInterface for the `+0xD8` sub-object. Vtable slot `0x00AB924C+0x00`. |
| `sub_7B0E30` | `81 e9 dc 00 00 00 / e9 05 98 ff ff` | `this -= 0xDC; jmp 0x007AA640` — QueryInterface for the `+0xDC` (message-target) sub-object. Slot `0x00AB923C+0x00`. |
| `sub_7B0E40` | `81 e9 dc 00 00 00 / e9 15 d3 00 00` | `this -= 0xDC; jmp 0x007BE160` — AddRef. Slot `0x00AB923C+0x04`. (also appears at `0x00AB8380`, an unrelated class with the same layout) |
| `sub_7B0E50` | `81 e9 dc 00 00 00 / e9 15 d3 00 00` | `this -= 0xDC; jmp 0x007BE170` — Release. Slot `0x00AB923C+0x08`. |

Main vtable head, for reference (read at `0x00AB9260`):
```
+0x00 0x007AA640 QueryInterface   +0x04 0x007BE160 AddRef      +0x08 0x007BE170 Release
+0x0C 0x007AB9F0 ?                +0x10 0x007B1900 Init        +0x14 0x007B0F60 Shutdown
+0x18 0x009D7E63  +0x1C 0x0099CA0B  +0x20 0x009C32AC  +0x24 0x0099BF01
+0x28 0x0099BE2A  +0x2C 0x0099B7EE
```

---

## sub_7B0E60

`sub_7B0E60  (0x007B0E60..0x007B0F60, 256 bytes)`

**PURPOSE** — the reallocating insert for the 0x80-byte item vector (MSVC `_Insert_n` out-of-line
grow path). **This is where the item stride 0x80 is proven**: `sar eax,7` at `0x007B0E70` and
`shl eax,7` at `0x007B0E8B` / `shl ebp,7` at `0x007B0F4A`.

**CONVENTION** — `__thiscall void _Insert_n(ItemVec* this /*ecx*/, Item* _Where, const Item& _Val,
<unused>, size_t _Count, uint8 noTail)`, `ret 0x14` (5 stack args).
⚠ the 3rd stack arg (`[esp+0xC]` at entry) is never read.
⚠ the 5th arg is passed **by value** but its *stack address* is handed to the copy helpers
(`lea ecx,[esp+0x28]; push ecx` at `0x007B0EAD`), and its low byte is re-read at `0x007B0EF4`
to decide whether to copy the tail. `sub_7B13C0` passes the literal `1` — i.e. "appending at the
end, there is no tail", which is correct for a `push_back`.

```c
void ItemVec::_Insert_n(Item* _Where, const Item& _Val, void*, size_t _Count, uint8 flag)
{
    size_t size = (this->_Mylast - this->_Myfirst) / 0x80;
    size_t cap  = size + max(size, _Count);            // 0x007B0E7D..0x007B0E85
    Item*  buf  = cap ? (Item*)operator new(cap * 0x80) : 0;

    Item* p = sub_7AED60(this->_Myfirst, _Where, buf, &flag);   // uninitialised_copy head
    if (_Count == 1) { if (p) sub_7AE7B0(p, &_Val); p += 0x80; }// placement copy-ctor
    else             p = sub_7AEDA0(p, _Count, &_Val, &flag);   // uninitialised_fill_n
    if (!flag) p = sub_7AED60(_Where, this->_Mylast, p, &flag); // uninitialised_copy tail

    for (Item* q = this->_Myfirst; q != this->_Mylast; q += 0x80) sub_7ADA00(q);  // ~Item()
    if (this->_Myfirst) operator delete(this->_Myfirst);

    this->_Mylast  = p;
    this->_Myend   = buf + cap*0x80;
    this->_Myfirst = buf;
}
```

Item helpers identified here (all in neighbouring slices):
`sub_7ADA00` = `~Item()`, `sub_7AE7B0` = `Item(const Item&)`,
`sub_7AED60` = `uninitialized_copy(Item*)`, `sub_7AEDA0` = `uninitialized_fill_n(Item*)`,
`sub_7AE9B0` = `copy(Item*)` (used by `erase`).

**CALLERS** — `0x007B1542` in `sub_7B13C0`.

---

## sub_7B0F60

`sub_7B0F60  (0x007B0F60..0x007B1200, 672 bytes)`

**PURPOSE** — **`cSC4WinRegionScreen::Shutdown()`**, vtable slot `+0x14`.

**CONVENTION** — `__thiscall bool Shutdown(this /*ecx*/)`, no args, always returns `true`.

```c
bool cSC4WinRegionScreen::Shutdown()
{
    if (!sub_99BC31(this)) return true;              // "am I initialised?" guard (base)

    sub_7ABB00(this, 0x8BB5BB46);                    // kSC4MessagePreRegionShutdown

    for (f in { +0xE8, +0xE0 }) {                    // in that order
        if (this->f) { this->vt_0x40(this->f); RELEASE_AND_NULL(this->f); }   // vt+0x40 = RemoveChildWindow ⚠
    }
    sub_91359F(this + 0x10C, this + 0xDC, 0);        // unregister all 17 notification ids

    cIGZCommandServer* cs = *(void**)0x00B43CB0;     // kGZCommandServerSysServiceID
    if (cs) {
        cs->vt_0x24(0x6A935E3C);  // QuitGame
        cs->vt_0x24(0x6A9757C2);  // RegionBitmapLoad
        cs->vt_0x24(0x6A935CD8);  // ScrollLeft
        cs->vt_0x24(0x2A948275);  // ScrollLeftStop
        cs->vt_0x24(0x2A94826E);  // ScrollRightStop
        cs->vt_0x24(0x6A935CE0);  // ScrollRight
        cs->vt_0x24(0x6A935CDD);  // ScrollUp
        cs->vt_0x24(0x2A948272);  // ScrollUpStop
        cs->vt_0x24(0x2A94826B);  // ScrollDownStop
        cs->vt_0x24(0x6A935CE2);  // ScrollDown
        cs->vt_0x24(0x6AA9FE51);  // SetExpandedToolTips
        cs->vt_0x24(0x0BB3C277);  // LoadRegion
        cs->vt_0x24(0x0BB2747D);  // LoadCity
        cs->vt_0x24(0x6A935CF1);  // Cancel
    }                                                 // 14 commands, exactly ids [3..16] of the ctor table

    ItemVec_erase(this+0x118, this->items_first, this->items_last);   // sub_7B0BB0 — drop ALL items
    sub_7AC380(this);                                                // ⚠ neighbouring slice

    RELEASE_AND_NULL(+0x154);   // graphic system
    RELEASE_AND_NULL(+0xE4);
    RELEASE_AND_NULL(+0x104);
    RELEASE_AND_NULL(+0x174);
    RELEASE_AND_NULL(+0x108);
    for (i=0;i<3;i++) RELEASE_AND_NULL(+0xEC + 4*i);      // view-mode buttons
    for (i=0;i<3;i++) RELEASE_AND_NULL(+0xF8 + 4*i);      // their siblings
    for (i=0;i<12;i++) RELEASE_AND_NULL(+0x124 + 4*i);    // 6 PAIRS of default tile bitmaps
                                                          // (written as 6 outer x 2 inner, 0x007B1170)
    if (*(void**)0x00B43CA8) (*(void**)0x00B43CA8)->vt_0xAC();
    sub_99D2FE(this);                                     // base shutdown

    // broadcast kSC4MessagePostRegionShutdown
    if (msgServer = *(void**)0x00B43CCC) {
        cIGZMessage2* m = new_message(0x2C);              // 0x9133DA + 0x9134D6
        m->AddRef(); m->vt_0x14(0x8BB5BB4B); msgServer->vt_0x10(m, 0); m->Release();
    }
    return true;
}
```

**CALLERS** — vtable `0x00AB9274`; one direct call from `~cSC4WinRegionScreen` (`0x007B121D`).

---

## sub_7B1200

`sub_7B1200  (0x007B1200..0x007B13C0, 448 bytes)`

**PURPOSE** — `~cSC4WinRegionScreen()`. Restores the three vtables, calls `Shutdown()`, then
tears the object down in exact reverse-construction order.

**CONVENTION** — `__thiscall void dtor(this /*ecx*/)`, no args, tail-jumps to the base dtor
`0x0099E1A2`.

```c
~cSC4WinRegionScreen()
{
    *(void**)(this)       = 0x00AB9260;
    *(void**)(this+0x0D8) = 0x00AB924C;
    *(void**)(this+0x0DC) = 0x00AB923C;
    this->Shutdown();                                  // sub_7B0F60
    sub_A6D837(this + 0x1D0);  sub_A6D837(this + 0x1B8);   // the two 0x88FEDF containers
    RELEASE_IF(+0x174); RELEASE_IF(+0x170); RELEASE_IF(+0x16C); RELEASE_IF(+0x168);
    RELEASE_IF(+0x164); RELEASE_IF(+0x160); RELEASE_IF(+0x15C); RELEASE_IF(+0x158);
    RELEASE_IF(+0x154);
    for (p = this+0x150; p >= this+0x124; p -= 4) RELEASE_IF(*p);   // 12 default-tile bitmaps
    for (Item* q = items_first; q != items_last; q += 0x80) sub_7ADA00(q);
    if (items_first) operator delete(items_first);
    sub_9135FE(this + 0x10C);
    RELEASE_IF(+0x108); RELEASE_IF(+0x104);
    for (p = this+0x100; p >= this+0xF8; p -= 4) RELEASE_IF(*p);    // 3
    for (p = this+0xF4;  p >= this+0xEC; p -= 4) RELEASE_IF(*p);    // 3
    RELEASE_IF(+0xE8); RELEASE_IF(+0xE4); RELEASE_IF(+0xE0);
    jmp sub_99E1A2(this);                                // base dtor
}
```

The `+0x124..+0x150` loop (12 iterations, `0x007B12C7: mov ebx, 0xC`) is what proves the
**default-tile-image array is 12 slots = 6 pairs**.

**CALLERS** — `0x007B2323` in `sub_7B2320` (the scalar-deleting dtor, next slice).

---

## sub_7B13C0

`sub_7B13C0  (0x007B13C0..0x007B1900, 1344 bytes)` — **THE TILE BUILDER**

**PURPOSE** — Enumerate every city in the current region, sort them into draw order, `push_back`
one 0x80-byte item per city, fill the item's cell rect / size class / **precomputed screen
position**, load its four bitmaps out of the savegame, build the composite, and hand every item
to the `cSC4WinRegionView`.

**CONVENTION** — `__thiscall void BuildCityItems(cSC4WinRegionScreen* this /*ecx*/)`, no args.

**CALLERS** — `0x007B1FA6` in `sub_7B1900` (Init), immediately before the pan is centred.

### The city list

```c
void* rm     = (*(void**)0x00B43C94)->vt_0x88();         // region manager
             rm->vt_0x2C(this->field_1A4);               // -> region object  (1 arg)
void* region = <that>;                                   //   kept at [esp+0x4C]
struct CityEnt { int32 x; int32 y; uint8 sizeClass; };   // 12-byte stride (see below)
vector<CityEnt> cities;
region->vt_0x5C(&cities);                                // enumerate cities of the region
sub_7AED00(cities.first, cities.last, cmp);              // std::sort — MSVC _Sort, depth 2*log2(n)
```

The 12-byte stride is proven twice: the sort's magic divide (`imul 0x2AAAAAAB; sar edx,1` =
`/12` at `0x007AED12`) and the loop increment `add ebp, 0xC` at `0x007B1883`.

### Per-city body

```c
for (CityEnt* e = cities.first; e != cities.last; ++e)
{
    // --- push_back a default-constructed Item -------------------------------
    //   the temp Item lives at [esp+0x60]; the frame writes below are at esp-4,
    //   so [esp+0x80..0xD4] == tmp+0x1C .. tmp+0x70.
    Item tmp;
    zero  tmp+0x1C .. tmp+0x30, tmp+0x38 .. tmp+0x64;   // NOTE: tmp+0x34 is deliberately SKIPPED
    tmp.f_68 = -1;  tmp.f_6C = -1;                      // 0x007B14D3 / 0x007B14DA (or eax,-1)
    tmp.f_70 = operator new(0xC);                       // list head node; [p]=p, [p+4]=p
    tmp.f_74 = 0;  tmp.f_78 = 0;  tmp.f_7C = 0;         // written after `add esp,4`
    if (items._Mylast != items._Myend) { copy-ctor in place; _Mylast += 0x80; }
    else  ItemVec::_Insert_n(_Mylast, tmp, &junk, /*count*/1, /*noTail*/1);   // sub_7B0E60
    ~tmp();                                             // sub_7ADA00

    Item* it = items._Mylast - 0x80;          // the item we just added

    // --- cell rectangle + size class ---------------------------------------
    int span = 1 << e->sizeClass;             // 0x007B155F: mov eax,1 / shl eax,cl
    it->f_00 = span + e->x - 1;               // maxX (inclusive)
    it->f_04 = span + e->y - 1;               // maxY (inclusive)
    it->f_08 = e->x;                          // minX
    it->f_0C = e->y;                          // minY
    it->f_18 = (uint8)e->sizeClass;
    it->f_34 = 0;                             // "built" flag cleared

    // --- THE POSITION MATH  (0x007B15A4 .. 0x007B15EF) ---------------------
    //  90.51 @0xB0DBA4   18.75 @0xB0DBA8   -37.49 @0xB0DBAC   45.25 @0xB0DBB0
    it->screenX /*+0x10*/ = (float)(it->f_08)        * 90.51f
                          + (float)(it->f_0C + span) * (-37.49f);
    it->screenY /*+0x14*/ = (float)(it->f_08 + span) * 18.75f
                          + (float)(it->f_0C + span) * 45.25f;
```

  Raw bytes for the two stores (load-bearing):
  ```
  0x007B15D8:  d9 5e 10        fstp dword ptr [esi + 0x10]
  0x007B15EF:  d9 5e 14        fstp dword ptr [esi + 0x14]
  ```
  and the four multiplies, in order:
  ```
  0x007B15C1:  d8 0d a4 db b0 00   fmul dword [0xB0DBA4]   ; minX * 90.51
  0x007B15CE:  d8 0d ac db b0 00   fmul dword [0xB0DBAC]   ; (minY+span) * -37.49
  0x007B15DF:  d8 0d a8 db b0 00   fmul dword [0xB0DBA8]   ; (minX+span) * 18.75
  0x007B15E7:  d8 0d b0 db b0 00   fmul dword [0xB0DBB0]   ; (minY+span) * 45.25
  ```

  With basis `screen(a,b) = (a*90.51 + b*(-37.49), a*18.75 + b*45.25)`, the stored X is the
  **leftmost** corner of the diamond (`a=min, b=max`) and the stored Y is the value at
  (`a=max, b=max`), i.e. the **maximum** Y of the diamond.
  ⚠ UNSURE: I could not reconcile "stored Y = bottom of the diamond" with `sub_7B3110`
  treating `+0x10/+0x14` as the top-left of the blit rect. Either the drawn bitmap's own
  origin compensates, or the region view's Y axis runs upward at this stage. **The formula
  above is measured; the *interpretation* of the Y anchor is not.**

  Note the scale invariant this gives you: `90.51 + 37.49 = 128.0` exactly is the screen width
  of **one region cell**, and a city of size class `s` spans `1<<s` cells, so `128 * (1<<s)`
  pixels wide — small=128, medium=256, large=512. Nothing in the expression depends on
  resolution, window size, or a zoom factor. **Ground truth confirmed.**

```c
    // --- load the four bitmaps out of the city's savegame ------------------
    void* city = region->vt_0x2C(e->x, e->y);         // 2 args — the city record
    sub_7ABB80(this, it);                             // ⚠ "use the default tile for this item"
    if (!city) goto composite;

    cRZString path;                                   // vtable 0x00A80810, ctor'd on stack
    city->vt_0x7C(&path);                             // get the .sc4 file path
    if (path.empty()) goto cleanup;                   // 0x007B165F

    RELEASE_AND_NULL(it->f_28); RELEASE_AND_NULL(it->f_24);
    RELEASE_AND_NULL(it->f_20); RELEASE_AND_NULL(it->f_1C);

    bool ok = sub_5DDA40(path, &it->f_1C, &it->f_20, &it->f_24, &it->f_28);
    //   sub_5DDA40 = open(path) [0x5DBFE0] -> read 4 images [0x5DD480] -> close [0x5DBC10]

    if (ok) {
        // consistency: f_20 must be the same pixel size as f_1C
        Rect a = it->f_20->vt_0x30(), b = it->f_1C->vt_0x30();
        if ((a.r-a.l) != (b.r-b.l) || (a.b-a.t) != (b.b-b.t)) ok = false;

        // and f_24 must match f_1C too, else drop f_24 + f_28
        if (it->f_1C && it->f_24 && it->f_28) {
            Rect c = it->f_28->vt_0x30(), d = it->f_24->vt_0x30();
            if ((c.r-c.l)==(d.r-d.l) && (c.b-c.t)==(d.b-d.t)) {
                Size s1 = sizeof(it->f_1C->vt_0x30()), s2 = sizeof(it->f_24->vt_0x30());
                if (!sub_7AA8E0(&s1, &s2))       // 0x7AA8E0 returns TRUE when the sizes DIFFER
                    goto keep;
            }
            RELEASE_AND_NULL(it->f_28); RELEASE_AND_NULL(it->f_24);
        }
    }
keep:
    if (!ok) sub_7ABB80(this, it);                    // fall back to the default tile
    if (it->f_24 && !it->f_28) { it->f_24->vt_0x10(); RELEASE_AND_NULL(it->f_24); }
    if (it->f_28)              { it->f_28->vt_0x10(); RELEASE_AND_NULL(it->f_28); }
cleanup:
    ~path();
composite:
    sub_7AE510(this, it);                             // BUILD THE COMPOSITE (+0x2C)
    if (it->f_20) { it->f_20->vt_0x10(); RELEASE_AND_NULL(it->f_20); }
}

// --- register every item with the view ------------------------------------
for (Item* it = items._Myfirst; it != items._Mylast; it += 0x80)
    sub_7B5D50(this->view /*+0xE0*/, it);
sub_7B5E20(this->view, 0, 0);
sub_7AB7C0(this);
```

**Why this matters for sizing:** the composite is built by `sub_7AE510`, which (ground truth,
`0x007AE6D9` / `0x007AE706`) reads the SOURCE bitmap's rect and calls `Init(w,h,{9,0x20})` —
so the composite is **verbatim the size of `it->f_1C`**, and `it->f_1C` came straight out of the
`.sc4` file via `sub_5DDA40`. **Nothing in this slice resamples, scales, or clamps a tile
bitmap.** The only scaling knob anywhere near the region map is the four `.data` floats.

**FIELDS OF `this`** — reads `+0x118/+0x11C/+0x120` (item vector), `+0x1A4` (region id),
`+0xE0` (the view). Writes the item vector only.

**FIELDS OF `Item` (stride 0x80) written here**
| off | type | meaning |
|---|---|---|
| `+0x00` | int32 | max cell X (inclusive) = `minX + (1<<size) - 1` |
| `+0x04` | int32 | max cell Y (inclusive) |
| `+0x08` | int32 | min cell X |
| `+0x0C` | int32 | min cell Y |
| `+0x10` | float | precomputed screen X (iso basis) |
| `+0x14` | float | precomputed screen Y (iso basis) |
| `+0x18` | uint8 | size class (0/1/2 → span 1/2/4 cells) |
| `+0x1C` | ptr | **source thumbnail bitmap** (from the savegame) |
| `+0x20` | ptr | 2nd savegame image, released after compositing |
| `+0x24` | ptr | 3rd savegame image (kept only if it matches `+0x1C`'s size) |
| `+0x28` | ptr | 4th savegame image (paired with `+0x24`) |
| `+0x34` | uint8 | "built" flag, cleared here (and deliberately *skipped* by the temp's zero-fill) |
| `+0x68`,`+0x6C` | int32 | initialised to `-1` |
| `+0x70` | ptr | head node of an embedded `std::list` (`new(0xC)`, self-linked) |
| `+0x74` | uint32 | list size = 0 |
| `+0x78`,`+0x7C` | uint32 | 0 |

Item stride is `0x80`, and `+0x74..+0x7C` are the last dwords — the object is fully accounted for
except `+0x30` and `+0x2C` (`+0x2C` is the composite buffer per ground truth).

---

## sub_7B1900

`sub_7B1900  (0x007B1900..0x007B2320, 2592 bytes)` — **`cSC4WinRegionScreen::Init()`**

**PURPOSE** — vtable slot `+0x10`. Full bring-up of the region screen.

**CONVENTION** — `__thiscall bool Init(this /*ecx*/)`, no args, always returns `true`.

**CALLERS** — vtable `0x00AB9270` only.

```c
bool cSC4WinRegionScreen::Init()
{
    if (sub_99BC31(this)) return true;                    // already initialised
    sub_7ABB00(this, 0xABB5BB44);                         // kSC4MessagePreRegionInit
    sub_99C2C3(this);                                     // base Init
    this->vt_0x100(0xEA659793);                           // SetID(clsid)

    // ---- 1. load the screen's own UI-script resource ----------------------
    GZTGI tgi = { 0xA2E3D533, 0x6A231EAA, 0x6A9362F0 };   // written at [esp+0x78..0x80]
    void* svc = *(void**)0x00B43CA8;
    if (svc->vt_0x0C(&tgi, 0x42E3EA4B, &out, 0, 0)) {
        void* f = sub_90DDF1();
        RELEASE_AND_NULL(this->f_108);
        f->vt_0x0C(0x42E967BE, 0xE2C1B3C4, &this->f_108);
        if (ok) out->vt_0x0C(this->f_108);
    }

    // ---- 2. which region are we entering? --------------------------------
    void* rm = (*(void**)0x00B43C94)->vt_0x88();
    rm->vt_0x18();
    bool  same = rm->vt_0x28(&prevRegion);                // prev region id, out-param
    this->f_1A4 = rm->vt_0x1C();                          // CURRENT region id  -> +0x1A4
    if (same && this->f_1A4 != prevRegion) same = false;  // 0x007B19FF
    //  `same` (kept in [esp+0x13]) gates the "restore my old camera" path below

    // ---- 3. broadcast kMessageSetRadioStation(1) -------------------------
    m = new_message(0x2C); m->AddRef(); m->vt_0x14(0x2A3AD653); m->vt_0x2C(1);
    (*(void**)0x00B43CCC)->vt_0x10(m, 0);

    // ---- 4. size myself to my parent -------------------------------------
    a = this->vt_0x28(); b = this->vt_0x28();
    this->vt_0xDC(0, 0, b->vt_0xA4(), a->vt_0xA8());      // SetArea(0,0,W,H) ⚠

    // ---- 5. take a reference on the graphic system ------------------------
    REPLACE_REF(this->f_154, *(void**)0x00B43C9C);        // cIGZGraphicSystem
    sub_7ACC90(this);

    // ---- 6. create the three owned child objects --------------------------
    obj = operator new(0xDC);  ctor: sub_99D938 + vtable 0x00AB8F50, +0xD8 = 0;
    REPLACE_REF(this->f_E8, obj);
    this->f_E8->vt_0xDC(0, 0, this->vt_0xA4(), this->vt_0xA8());
    this->f_E8->vt_0x110(0x10000, 0);
    this->vt_0x38(this->f_E8);                            // AddChildWindow ⚠
    this->f_E8->vt_0x60();
    this->f_E8->vt_0x110(0x800, 0);
    this->f_E8->vt_0x110(0x200000, 1);
    this->f_E8->vt_0x110(1, 0);

    obj = operator new(0x128);  sub_7B4090(obj);          // ⚠ some overlay/controller
    REPLACE_REF(this->f_E0, obj);                         // <-- THE cSC4WinRegionView
    this->vt_0x38(this->f_E0);
    this->f_E0->vt_0xDC(0, 0, this->vt_0xA4(), this->vt_0xA8());
    this->f_E0->vt_0x5C();
    this->f_E0->vt_0x110(0x800,   0);
    this->f_E0->vt_0x110(0x80000, 1);
    this->f_E0->vt_0x110(1,       1);
    this->f_E0->field_DC = this->f_1A4;                   // region id -> view+0xDC
    this->f_E0->field_F8 = this->f_1B0;                   // 0x00808080
    this->f_E0->field_FC = this->f_1B4;                   // 0x00FFFF00
```

> ⚠ `operator new(0x128)` + `sub_7B4090` for `+0xE0`, and `operator new(0x140)` + `sub_7A9AE0`
> for `+0xE4` below. Ground truth says `+0xE0` is the region VIEW object; the ctor called here
> is `sub_7B4090`, not `sub_7C9B10`. **If `+0xE0` really is `cSC4WinRegionView` (clsid
> 0x2BA6BB97 / vtable 0x00AB9658), then `sub_7B4090` is its constructor** — that is what the
> bytes say. Flagging because slice 6/7 owns `sub_7B4090` and should confirm.

```c
    // ---- 7. the 6 PAIRS of default tile bitmaps --------------------------
    // table cursor walks 0x00AB8B44 .. <0x00AB8B74, step 8; reads [cur-4] and [cur]
    // destination walks this+0x124, step 8
    for (cur = 0x00AB8B44, dst = this + 0x124; cur < 0x00AB8B74; cur += 8, dst += 8)
    {
        GZPtr p0, p1;
        sub_602B70(&p0, /*T*/0x856DDBAC, /*G*/0x6A1EED2C, /*I*/*(uint32*)(cur-4), 9, 0);
        sub_602B70(&p1, /*T*/0x856DDBAC, /*G*/0x6A1EED2C, /*I*/*(uint32*)(cur  ), 9, 0);
        if (p0 && p1) { REPLACE_REF(dst[0], p0); REPLACE_REF(dst[1], p1); }
        else {
            // FALLBACK: two 1x1 dummy bitmaps
            void* gz = sub_8793EC();                       // the GZCOM framework
            void* gs = 0;
            gz->vt_0x14(0xC416025C /*kGZGraphicSystem*/, 0x0073283C, &gs);
            for (int k = 0; k < 2; ++k) {
                RELEASE_AND_NULL(dst[k]);
                gs->vt_0x0C(&dst[k]);                      // CreateBitmap
                struct { uint32 fmt; uint32 bpp; } fd = { 9, 0x20 };
                dst[k]->vt_0x0C(1, 1, fd);                 // Init(1,1,{9,0x20})   <<<<
                if (dst[k]->vt_0x18(0x8001)) {             // Lock
                    dst[k]->vt_0x48(0, 0);
                    dst[k]->vt_0x1C(0x8001);               // Unlock
                }
            }
            gs->Release();
        }
        ~p1(); ~p0();
    }
```

The `Init(1,1,{9,0x20})` call — the *only* place in this slice where the game itself drives
tile-buffer vtable slot `+0x0C` — is built like this:

```
0x007B1D9F:  8b 0f              mov  ecx, [edi]        ; the freshly created bitmap
0x007B1DA1:  83 ec 08           sub  esp, 8            ; room for the by-value format struct
0x007B1DA4:  8b c4              mov  eax, esp
0x007B1DA6:  6a 01              push 1                 ; height
0x007B1DA8:  c7 00 09 00 00 00  mov  dword [eax], 9    ; fmt.depth
0x007B1DAE:  c7 40 04 20 00 00 00 mov dword [eax+4], 0x20 ; fmt.bpp
0x007B1DB5:  8b 11              mov  edx, [ecx]
0x007B1DB7:  6a 01              push 1                 ; width
0x007B1DB9:  ff 52 0c           call dword [edx + 0xc] ; Init(w, h, {9,0x20})
```

**This confirms the ground-truth signature `vt+0x0C = Init(int w, int h, struct{u32,u32})`,
and it confirms the game only ever calls it on a NEWLY CREATED buffer.**

The 12 instance ids (type `0x856DDBAC` = PNG, group `0x6A1EED2C`) are:

| pair | slots | instance A | instance B |
|---|---|---|---|
| 0 | `+0x124/+0x128` | `0x6A231946` | `0x6A231947` |
| 1 | `+0x12C/+0x130` | `0xEA23195D` | `0xEA23195E` |
| 2 | `+0x134/+0x138` | `0x0A2312D9` | `0x0A2312D8` |
| 3 | `+0x13C/+0x140` | `0x6A6CA89E` | `0x6A6CA89F` |
| 4 | `+0x144/+0x148` | `0x6A6CA6DF` | `0x6A6CA6DE` |
| 5 | `+0x14C/+0x150` | `0x0A6CAB89` | `0x0A6CAB88` |

```c
    // ---- 8. two more owned objects ---------------------------------------
    obj = operator new(0x138); sub_7AAE10(obj);  REPLACE_REF(this->f_174, obj);
    this->f_174->vt_0xDC(0, 0, this->vt_0xA4(), this->vt_0xA8());
    this->f_174->vt_0x110(0x10000, 0);
    this->vt_0x38(this->f_174);  this->f_174->vt_0x5C();
    this->f_174->vt_0x110(0x800, 0);  this->f_174->vt_0x110(0x200000, 1);

    obj = operator new(0x140); sub_7A9AE0(obj);  REPLACE_REF(this->f_E4, obj);
    this->vt_0x38(this->f_E4);  this->f_E4->vt_0x5C();
    this->f_E4->vt_0x110(0x800, 0);
    Prefs* pr = (*(void**)0x00B43C94)->vt_0x98();
    this->f_E4->vt_0x110(1, pr->byte_F11 != 0);

    // ---- 9. hand the iso basis to +0xE4 ----------------------------------
    sub_7A9980(this->f_E4, /*a*/ *(uint32*)0x00B0DBA4,   //  90.51f
                            /*b*/ *(uint32*)0x00B0DBA8); //  18.75f
```
```
0x007B1F8B:  8b 0d a8 db b0 00   mov ecx, [0x00B0DBA8]   ; 18.75f  (pushed 2nd -> arg1)
0x007B1F91:  8b 15 a4 db b0 00   mov edx, [0x00B0DBA4]   ; 90.51f  (pushed 1st -> arg0)
0x007B1F9F:  e8 dc 79 ff ff      call 0x007A9980
```
> Only the **X-row** of the basis (`90.51`, `18.75`) is passed. ⚠ Whatever `+0xE4` is
> (`sub_7A9AE0`, 0x140 bytes — the scroll/minimap overlay?) it is configured with the
> half-basis, not all four floats.

```c
    // ---- 10. BUILD THE TILES ---------------------------------------------
    sub_7B13C0(this);                       // <<< the tile builder
    sub_7ABF10(this);                       // computes the region bounding box into +0x180..+0x18C

    // ---- 11. initial pan = centre of the region bbox ----------------------
    this->f_178 /*float*/ = (float)((this->f_180 + this->f_188) / 2);   // sar 1, signed
    this->f_17C /*float*/ = (float)((this->f_184 + this->f_18C) / 2);

    // ...unless we are re-entering the SAME region, in which case restore
    if (same) {
        Prefs* p = *(void**)0x00B43CD8;
        if (p->int_EFC != 0x80000000) {
            float camX = (float)p->int_EFC * 0.00390625f;   // 0xAA6E60 = 1/256
            float camY = (float)p->int_F00 * 0.00390625f;
            this->f_178 = camX - (float)this->vt_0xA4() * 0.5f;   // 0xA84D2C = 0.5
            this->f_17C = camY - (float)this->vt_0xA8() * 0.5f;
        }
    }

    // ---- 12. register for the 17 notification ids -------------------------
    sub_913556(this + 0x10C, this + 0xDC, 0);

    // ---- 13. register the 14 named commands with the command server -------
    cs = *(void**)0x00B43CB0;                  // kGZCommandServerSysServiceID
    cs->vt_0x18(0x6A935E3C, "QuitGame",            0);   // 0x00AB957C
    cs->vt_0x18(0x6A9757C2, "RegionBitmapLoad",    0);   // 0x00AB9568
    cs->vt_0x18(0x6A935CD8, "ScrollLeft",          0);   // 0x00AB955C
    cs->vt_0x18(0x2A948275, "ScrollLeftStop",      0);   // 0x00AB954C
    cs->vt_0x18(0x2A94826E, "ScrollRightStop",     0);   // 0x00AB953C
    cs->vt_0x18(0x6A935CE0, "ScrollRight",         0);   // 0x00AB9530
    cs->vt_0x18(0x6A935CDD, "ScrollUp",            0);   // 0x00AB9524
    cs->vt_0x18(0x2A948272, "ScrollUpStop",        0);   // 0x00AB9514
    cs->vt_0x18(0x2A94826B, "ScrollDownStop",      0);   // 0x00AB9504
    cs->vt_0x18(0x6A935CE2, "ScrollDown",          0);   // 0x00AB94F8
    cs->vt_0x18(0x6AA9FE51, "SetExpandedToolTips", 0);   // 0x00AB94E4
    cs->vt_0x18(0x0BB3C277, "LoadRegion",          0);   // 0x00AB94D8
    cs->vt_0x18(0x0BB2747D, "LoadCity",            0);   // 0x00AB94CC
    cs->vt_0x18(0x6A935CF1, "Cancel",              0);   // 0x00AAD96C

    // ---- 14. chrome ------------------------------------------------------
    sub_7B0470(this);                        // build the two .UI panels + radios
    this->f_1E8 = 2;                         // (ctor set it to 0)

    // ---- 15. the 3-D "region_global" scene node --------------------------
    RELEASE_AND_NULL(this->f_170);
    if (this->f_15C->vt_0x1C("region_global" /*0x00AB94BC*/, &this->f_170)) {
        void* grid = *(void**)0x00B43CF8;                    // the terrain/region grid
        float cell = grid->vt_0x18();                        // returns st0
        int   nx   = grid->vt_0x20();
        int   ny   = grid->vt_0x1C();
        float tx   = (float)nx * cell * 0.5f;                // 0xA84D2C = 0.5
        float ty   = (float)ny * cell * 0.5f;
        Matrix4 m = IDENTITY;                                // 0x3F800000 on the diagonal
        m.tx = tx;  m.ty = ty;   // [esp+0x58] / [esp+0x5C]; [esp+0x60]=tx-ish, [esp+0x64]=1.0
        m.flags[0] = m.flags[1] = 1;                         // bytes at [esp+0x30],[esp+0x31]
        this->f_170->vt_0x1C(&m);                            // SetTransform
        this->f_170->vt_0x0C(0);
    }

    // ---- 16. broadcast kSC4MessagePostRegionInit -------------------------
    m = new_message(0x2C); m->AddRef(); m->vt_0x14(0xCBB5BB45);
    (*(void**)0x00B43CCC)->vt_0x10(m, 0); m->Release();
    return true;
}
```

**FIELDS WRITTEN BY Init**
| field | value |
|---|---|
| `+0x1A4` | current **region id** (`rm->vt_0x1C()`) |
| `+0x154` | `cIGZGraphicSystem` (from `[0x00B43C9C]`) |
| `+0xE8` | new 0xDC-byte object, vtable `0x00AB8F50` |
| `+0xE0` | new 0x128-byte object, ctor `sub_7B4090` — the region **view** |
| `+0x174` | new 0x138-byte object, ctor `sub_7AAE10` |
| `+0xE4` | new 0x140-byte object, ctor `sub_7A9AE0`; fed the X-row of the iso basis |
| `+0x124..+0x150` | the 6 pairs of default tile bitmaps (PNG T=0x856DDBAC G=0x6A1EED2C) |
| `+0x178 / +0x17C` | **float pan X / Y** = centre of the region bbox, or the restored camera |
| `+0x180..+0x18C` | region screen-space bbox `{minX, minY, maxX, maxY}` (filled by `sub_7ABF10`) |
| `+0x108` | object from `sub_90DDF1()->vt_0x0C(0x42E967BE, 0xE2C1B3C4, ...)` |
| `+0x170` | the `"region_global"` 3-D scene node, from `+0x15C` |
| `+0x1E8` | `2` |

**CONSTANTS** — `0x00A84D2C = 0.5f`, `0x00AA6E60 = 0.00390625f (1/256)`,
`0x3F800000 = 1.0f`, UI-script TGI `{0xA2E3D533, 0x6A231EAA, 0x6A9362F0}` with iid `0x42E3EA4B`,
PNG type `0x856DDBAC`, tile group `0x6A1EED2C`, the 14 command-name strings listed above,
`"region_global"` at `0x00AB94BC`.

---

## Corrections to the supplied GROUND TRUTH

Nothing in this slice contradicts the ground truth. Confirmations and one refinement:

1. **CONFIRMED** — vtable `0x00AB9260` slot `+0x10` is `sub_7B1900` = `Init` (byte-read at
   `0x00AB9270`); slot `+0x14` is `sub_7B0F60` = `Shutdown` (`0x00AB9274`).
2. **CONFIRMED byte-for-byte** — the four iso-basis floats at `0x00B0DBA4/A8/AC/B0`.
3. **CONFIRMED** — `+0x164` is the `cSC4CameraControl`: `DoMessage` reaches it as
   `[thisPlus0xDC + 0x88]` at `0x007B0B4F`.
4. **CONFIRMED** — item stride 0x80 (`sar/shl 7` in `sub_7B0E60`), fields `+0x10/+0x14` float
   screen pos, `+0x18` size class, `+0x1C` source thumbnail, `+0x34` built flag.
5. **CONFIRMED** — `vt+0x0C` on a tile buffer is `Init(int w, int h, struct{u32 fmt; u32 bpp})`
   passed by value; the game's own call site is `0x007B1DA1..0x007B1DB9` with `(1, 1, {9,0x20})`,
   always on a bitmap created two instructions earlier. The game **never** re-Inits a live buffer,
   which is consistent with the measured "returns 0, stays 260x160".
6. **REFINEMENT (not a contradiction)** — ground truth lists `+0x124..` as "default tile images";
   the bytes show it is exactly **12 slots (`+0x124..+0x150`) = 6 PAIRS**, loaded from the
   instance table at `0x00AB8B40..0x00AB8B6C`, PNG type `0x856DDBAC`, group `0x6A1EED2C`.
   The item vector is `+0x118 / +0x11C / +0x120` (first / last / **capacity end**).
7. **REFINEMENT** — the region screen keeps its own pan at `+0x178/+0x17C` (floats), set in
   Init; the view's `+0xE8/+0xEC` pan from ground truth is a separate copy.
8. **NEW / ⚠** — ground truth says the scene ctor is `sub_7C9B10` for `+0x168`. Init constructs
   `+0xE0` with `sub_7B4090` (0x128 bytes) and `+0xE4` with `sub_7A9AE0` (0x140 bytes);
   `+0x168` is **not** written by Init in this slice. Slice 6/7 should resolve `sub_7B4090`.

## Open questions for other slices

* `sub_7B4090` (0x128 B) — is this `cSC4WinRegionView::ctor`? Init stores its result in `+0xE0`.
* `sub_7A9AE0` (0x140 B) at `+0xE4` — it is the only object handed the iso basis
  (`sub_7A9980(90.51f, 18.75f)`); if anything ever needs a **zoom** knob, this is the first place
  to look.
* `sub_7ABF10` — fills `+0x180..+0x18C`, the region bbox in screen space. That, plus the four
  `.data` floats, is the entire sizing model of the region map.
* `+0x1EC = 5.0f` and `+0x1F0 = 1200.0f` set in the ctor and never touched in this slice — a
  plausible zoom/clip range for task #132.
