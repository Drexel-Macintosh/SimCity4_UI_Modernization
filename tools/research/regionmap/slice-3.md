# SC4 Region Screen — decompilation slice 3 of 8
### VA range 0x007AC7D0 .. 0x007AE3CF (21 functions)

SimCity 4 Deluxe 1.1.641, image base 0x400000, fileOffset = VA − 0x400000.
Every address, byte string and constant below was read out of
`C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe`
during this pass. Guesses are flagged `Unsure`.

---

## Table of contents

| # | Function | Extent | Bytes | One-line purpose |
|---|----------|--------|-------|------------------|
| 1 | [`sub_7AC7D0`](#1-sub_7ac7d0) | 7AC7D0..7AC82F | 96 | ctor of the 0x14-byte scene draw-callback object (vtables 0xAB8CB8/0xAB8CA0) |
| 2 | [`sub_7AC830`](#2-sub_7ac830) | 7AC830..7ACACF | 672 | **cSC4WinRegionScreen vtable +0x160 — the per-frame tick: smooth-scroll integrator, pan clamp, camera→view pan hand-off** |
| 3 | [`sub_7ACAD0`](#3-sub_7acad0) | 7ACAD0..7ACC8F | 448 | **cSC4WinRegionScreen vtable +0x218 — mouse handler: click-select, double-click detect, launch-city** |
| 4 | [`sub_7ACC90`](#4-sub_7acc90) | 7ACC90..7AD1EF | 1376 | **cSC4WinRegionScreen::BuildSceneAndServices — creates terrain grid / renderer / camera / scene, sets world extents** |
| 5 | [`sub_7AD1F0`](#5-sub_7ad1f0) | 7AD1F0..7AD2BF | 208 | Hoare partition over 12-byte `{int x,int y,int level}` records, key = `x+y+(1<<level)` (isometric painter order) |
| 6 | [`sub_7AD2C0`](#6-sub_7ad2c0) | 7AD2C0..7AD30F | 80 | `list<refptr>::erase(first,last)` — unlink, Release, free node |
| 7 | [`sub_7AD310`](#7-sub_7ad310) | 7AD310..7AD3AF | 160 | `make_heap(first,last,cmp)` over the same 12-byte record |
| 8 | [`sub_7AD3B0`](#8-sub_7ad3b0) | 7AD3B0..7AD3FF | 80 | vtable 0xAB8CD0 slot +0x21C — mouse handler on the *other* region window class |
| 9 | [`sub_7AD400`](#9-sub_7ad400) | 7AD400..7AD79F | 928 | **__usercall — builds a tile's channel RUN-LIST vector from a 32-bpp bitmap (the +0x44/+0x50/+0x5C vectors)** |
| 10 | [`sub_7AD7A0`](#10-sub_7ad7a0) | 7AD7A0..7AD8CF | 304 | `vector<T12>::operator=` (generic, shared with 4 non-region callers) |
| 11 | [`sub_7AD8D0`](#11-sub_7ad8d0) | 7AD8D0..7AD95F | 144 | `__linear_insert(first,last,value,cmp)` |
| 12 | [`sub_7AD960`](#12-sub_7ad960) | 7AD960..7AD9FF | 160 | `sort_heap(first,last,cmp)` |
| 13 | [`sub_7ADA00`](#13-sub_7ada00) | 7ADA00..7ADABF | 192 | **DESTRUCTOR of the 0x80-byte region TILE ITEM — definitive field census** |
| 14 | [`sub_7ADAC0`](#14-sub_7adac0) | 7ADAC0..7ADC1F | 352 | `SelectRegionByName(cIGZString*)` — linear search of the region manager |
| 15 | [`sub_7ADC20`](#15-sub_7adc20) | 7ADC20..7ADD2F | 272 | "enter the named city / fall back to region reload" transition helper |
| 16 | [`sub_7ADD30`](#16-sub_7add30) | 7ADD30..7ADD7F | 80 | `__insertion_sort(first,last,cmp)` |
| 17 | [`sub_7ADD80`](#17-sub_7add80) | 7ADD80..7ADE4F | 208 | `list<refptr>::operator=` (AddRef/Release aware) |
| 18 | [`sub_7ADE50`](#18-sub_7ade50) | 7ADE50..7ADF3F | 240 | `partial_sort(first,middle,last,cmp)` |
| 19 | [`sub_7ADF40`](#19-sub_7adf40) | 7ADF40..7ADF9F | 96 | `__final_insertion_sort` (SGI STL, threshold 16) |
| 20 | [`sub_7ADFA0`](#20-sub_7adfa0) | 7ADFA0..7AE15F | 448 | **COPY-ASSIGN of the 0x80-byte region TILE ITEM — definitive field census (matches #13)** |
| 21 | [`sub_7AE160`](#21-sub_7ae160) | 7AE160..7AE3CF | 624 | **1-D filtered RESAMPLE pass (16.16 fixed point, unit tent kernel) — the game DOES resample tile art here** |

Cross-cutting results are collected in [§ Headline corrections](#headline-corrections-to-ground-truth)
and [§ Field maps](#field-maps).

---

## Headline corrections to GROUND TRUTH

1. **"NEITHER RESAMPLES" is true for `sub_7B3300` / `sub_7B2A30` but NOT for the module.**
   `sub_7AE160` (this slice) is a real 16.16 fixed-point resampler with a **unit
   triangle (tent/bilinear) kernel** — `sub_7AA0E0` is literally
   `f(x) = |x| < 1.0 ? 1.0 − |x| : 0.0` (`fld qword[esp+4]; fabs; fcom qword[0xA80AB0]`,
   `[0xA80AB0] = 1.0`, `[0xA80990] = 0.0`). `sub_7AE160` builds **two** filter
   tables per call (one per axis, 0x7AE1B6 and 0x7AE206); its single caller
   `sub_7AE3D0` is itself called **four times** by `sub_7AE510`, the composite
   creator (0x7AE5B9, 0x7AE5EA, 0x7AE65D, 0x7AE68E).
   So the composite pipeline *does* filter, at build time.

2. **The item is not one run-list at +0x38 — there are FOUR 12-byte `std::vector`s**
   at `+0x38`, `+0x44`, `+0x50`, `+0x5C`. Proven twice, independently, by the
   item destructor (`sub_7ADA00`) and the item copy-assign (`sub_7ADFA0`).
   `sub_7AE510` fills **+0x44, +0x5C, +0x50** (shift 0, 8, 0x10) — `+0x38` is
   filled somewhere else.

3. **The item has SIX refcounted buffer pointers**, at `+0x1C, +0x20, +0x24, +0x28,
   +0x2C, +0x30` — not just the `+0x1C` source and `+0x2C` composite. The bitmap
   that feeds the run-lists is **`+0x20`**, not `+0x1C` (see 0x7AE738 / 0x7AE747 /
   0x7AE756: `push [ebx+0x20]`).

4. **Item stride 0x80 is now derived, not assumed**: `sub_7ADFA0` copies fields
   through `+0x74` and that last field is a 12-byte vector → 0x74 + 0x0C = **0x80**. ✓

5. **Tile-buffer vtable 0x00AC1400 gains two confirmed slots**: `vt+0x88 = GetBits()`
   and `vt+0x8C = GetPitchInBytes()` (proof: `rowPtr = GetBits() + GetPitch()*y`,
   then indexed `[rowPtr + x*4]` — the ×4 forces the pitch to be bytes).
   Also `vt+0x18 = Lock(flags)->bool` / `vt+0x1C = Unlock(flags)` (called with
   0x800 in `sub_7AD400`, with 0x8040 in `sub_7AE3D0`).

6. **`cSC4WinRegionScreen +0x158` is not a nameless "service": it is
   `cSC4AnimationTickManager`** (clsid `0xA9C73857`, from the class-name registry
   entry at 0xB08370-region; the pair is pushed at 0x7ACCBD/0x7ACCC2 as
   `GetClassObject(0xA9C73857, 0x86AD10ED, &this->0x158)`). `sub_7AC830` ticks it
   every frame via `vt+0x24`.
   Likewise **`+0x15C` = `cSC4EffectsManager`** (clsid `0x49822F75`, iid `0xC97CF5CD`),
   mirrored into the global `[0xB43D1C]`.

7. **`0x00648F00` verified**: bytes at file offset 0x248F00 are
   `B0 01 C3 CC CC CC CC CC` = `mov al,1; ret`. It is used as a *shared* do-nothing
   virtual — it also sits at **`cSC4WinRegionView` vtable +0x160**, i.e. the region
   *view* has no per-frame tick at all; all the motion is in the *screen*
   (`sub_7AC830`).

Nothing in GROUND TRUTH was contradicted outright by the bytes; items 1–6 are
extensions/refinements and item 1 is a caveat that materially changes the
"nothing resamples" conclusion.

---

## Field maps

### `cSC4WinRegionScreen` (clsid 0xEA659793, vtable 0x00AB9260) — fields touched in this slice

| Offset | Type | Evidence | Meaning |
|---|---|---|---|
| +0x0E0 | ptr | 0x7ACA73, 0x7ACAEF | `cSC4WinRegionView*` (GT ✓) |
| +0x0E4 | ptr | 0x7ACA91 | second view-ish object; `sub_7A98A0(&POINT)` target Note: |
| +0x158 | ptr | 0x7ACCA3, 0x7ACAAD | `cSC4AnimationTickManager` (clsid 0xA9C73857, iid 0x86AD10ED); ticked each frame via `vt+0x24` |
| +0x15C | ptr | 0x7AD0FD | `cSC4EffectsManager` (clsid 0x49822F75, iid 0xC97CF5CD) → also `[0xB43D1C]` |
| +0x160 | ptr | 0x7ACDB7 | renderer (clsid==iid `0xE9C6262A`; fallback `new(0x1A8) sub_7FF930`) |
| +0x164 | ptr | 0x7ACE41 | `cSC4CameraControl` (0xC9C628EC; fallback `new(0x160) sub_7CC990`) (GT ✓) |
| +0x168 | ptr | 0x7ACF70 | scene (`new(0x2E8) sub_7C9B10`) (GT ✓) → also `[0xB43DD0]` |
| +0x16C | ptr | 0x7ACD80 | terrain grid (`new(0x28) sub_7AACE0`) → also `[0xB43CF8]` (GT ✓) |
| +0x178 | float | 0x7AC8AF, 0x7AC910 | **scroll position X** (screen px) |
| +0x17C | float | 0x7AC8BF, 0x7AC922 | **scroll position Y** |
| +0x180 | int | 0x7AC953 | scroll clamp **minX** |
| +0x184 | int | 0x7AC95F | scroll clamp **minY** |
| +0x188 | int | 0x7AC959 | scroll clamp **maxX** |
| +0x18C | int | 0x7AC96D | scroll clamp **maxY** |
| +0x1A0 | byte | 0x7ACAD8, 0x7ACC5B | "click armed / a tile is selected" latch |
| +0x1A4 | int | 0x7ACCE1, 0x7ADBBD | **current region index** into the region manager |
| +0x1A8 | int | 0x7ACBF7 | mode; `(x == 1)` is passed to `view->sub_7B30B0` Note: |
| +0x1B8 | obj | 0x7AC85E | frame stopwatch (see § timer API) |
| +0x1D0 | obj | 0x7ACB16, 0x7ACC55 | double-click stopwatch |
| +0x1E8 | int | 0x7AC838 | countdown; on reaching 0 → `this->vt+0x110(0x200000, 0)` |
| +0x1F4 | float | 0x7AC8A9 | **scroll target X** |
| +0x1F8 | float | 0x7AC8B9 | **scroll target Y** |
| +0x1FC | byte | 0x7AC89D | "scrolling to target" flag |

Region-screen vtable overrides seen from this slice (base impls are `0x0099xxxx`,
i.e. plain `cGZWin`):

```
0x00AB9260 + 0x160 -> 0x007AC830   (this slice)   per-frame tick
0x00AB9260 + 0x218 -> 0x007ACAD0   (this slice)   mouse handler, ret 0xC
0x00AB9260 + 0x21C -> 0x007AB790                  (slice 2)
0x00AB9260 + 0x228 -> 0x007AB760                  (slice 2)
```
Sibling class, vtable **0x00AB8CD0** (ctor `sub_7AAE10` @0x7AAE1A, scalar-deleting
dtor `sub_7AC5C0` @0x7AC5C3; constructed from `sub_7B1900` at 0x7B1E38) overrides
`+0x160 -> 0x7AB130`, `+0x21C -> 0x7AD3B0` (this slice), `+0x228 -> 0x7AAF20`.
`cSC4WinRegionView` (0x00AB9658) overrides none of 0x218/0x21C/0x228, and its
`+0x160` is the `mov al,1; ret` stub.

### The 0x80-byte region TILE ITEM — complete layout

Derived twice independently: destructor `sub_7ADA00` and copy-assign `sub_7ADFA0`.

| Offset | Size | Kind | Notes |
|---|---|---|---|
| +0x00 | 4 | dword | copied verbatim |
| +0x04 | 4 | dword | copied verbatim |
| +0x08 | 4 | **int** | region cell **X** — pushed to `regionMgr->GetCityAt` at 0x7ACC13/0x7ACC19 Note: (order X/Y not independently proven) |
| +0x0C | 4 | **int** | region cell **Y** |
| +0x10 | 4 | **float** | precomputed screen X (GT ✓, written at 0x7B15D8) |
| +0x14 | 4 | **float** | precomputed screen Y (GT ✓, written at 0x7B15EF) |
| +0x18 | 1 | byte | size class (GT ✓) |
| +0x1C | 4 | refptr | source thumbnail buffer (GT ✓) |
| +0x20 | 4 | refptr | **run-list source bitmap** (fed to `sub_7AD400` ×3) |
| +0x24 | 4 | refptr | paired with +0x28 through `sub_7ABCD0` at 0x7AE76F |
| +0x28 | 4 | refptr | " |
| +0x2C | 4 | refptr | composite buffer (GT ✓) |
| +0x30 | 4 | refptr | sixth buffer |
| +0x34 | 1 | byte | "built" flag (GT ✓) |
| +0x38 | 12 | `vector<u32>` | run-list #0 — **not** written by `sub_7AE510` |
| +0x44 | 12 | `vector<u32>` | run-list, `sub_7AD400(bmp=+0x20, shift=0,    emitValues=0)` |
| +0x50 | 12 | `vector<u32>` | run-list, `sub_7AD400(bmp=+0x20, shift=0x10, emitValues=1)` |
| +0x5C | 12 | `vector<u32>` | run-list, `sub_7AD400(bmp=+0x20, shift=8,    emitValues=1)` |
| +0x68 | 4 | dword | copied verbatim; `&item[+0x68]` and `&item[+0x6C]` passed to `sub_7AA6A0` at 0x7AE781 |
| +0x6C | 4 | dword | " |
| +0x70 | 4 | list head | `list<refptr>` (assign `sub_7ADD80`, clear `sub_473EC0`) |
| +0x74 | 12 | `vector<T12>` | vector of the 12-byte `{x,y,level}` records — **this is the thing all the sort helpers in this slice sort** |
| **0x80** | | | end of record ✓ |

Destructor order (0x7ADA00): free `+0x74.begin`, clear list `+0x70`, free
`+0x5C/+0x50/+0x44/+0x38`, then Release `+0x30, +0x2C, +0x28, +0x24, +0x20, +0x1C`
(the last is a `jmp [edx+8]` tail call).

### Globals referenced in this slice

| VA | Role (evidence) |
|---|---|
| `0xB43C94` | app/director. `vt+0x88()` → region manager; `vt+0x30(bool)` → bool; `vt+0x34(str*,ptr)`; `vt+0x9C()` → a struct with a refptr at `+0x200`; `vt+0x18(ptr)` |
| `0xB43C9C` | GZCOM factory; `vt+0x00(clsid, void**)` used for `0xC47B747C` |
| `0xB43CB8` | optional service; `vt+0x2C(1, 0x2A5C322B, 0,0,0)` on city launch Note: (sound/effect trigger?) |
| `0xB43CCC` | message server; `vt+0x10(msg, 0)` |
| `0xB43CF8` | terrain grid (mirror of screen `+0x16C`) — GT ✓ |
| `0xB43D1C` | `cSC4EffectsManager` (mirror of `+0x15C`) |
| `0xB43DD0` | scene (mirror of `+0x168`) |
| `0xB43DD8` | `scene->vt+0x20()` result |
| `0xB43DDC` | `scene->vt+0x24()` result |

### .rdata constants used in this slice

| VA | Bytes | Value | Used by |
|---|---|---|---|
| `0xA84D28` | `00 00 A0 40` | **5.0f** | scroll speed = 5·distance |
| `0xAB91B8` | `00 00 96 44` | **1200.0f** | scroll speed **cap** (px/s) |
| `0xA867A4` | `6F 12 83 3A` | **0.001f** | ms → seconds |
| `0xA8825C` | `00 00 00 40` | **2.0f** | arrival epsilon (Manhattan) |
| `0xAB8BE0` | `00 00 40 4B` | **12582912.0f** = 1.5·2²³ | float→int "magic number" bias |
| `0xA80AB0` | (double) | **1.0** | tent-filter support radius |
| `0xA80990` | (double) | **0.0** | tent-filter zero |
| `0xA80810` | — | vtable | `cRZString` (the literal `"basic_string"` lives at 0xA806F0, used by the `length_error` throw `sub_9DD1D0`) |
| `0xA80810`-object | — | 0x14 bytes | vtable + {begin,end,cap} + refcount |
| immediates | | `0x3E800000`=0.25f, `0x44000000`=512.0f, `0x46800000`=16384.0f, `0x3F800000`=1.0f, `0xBF800000`=−1.0f, `0x43960000`=300.0f | see call sites |

### Class ids seen (resolved against the .data registry 0x00B05000..0x00B0B000)

```
0xEA659793 cSC4WinRegionScreen              (entry 0xB08FC0)
0x2BA6BB97 cSC4WinRegionView                (entry 0xB08FC8)
0xC9C628EC cSC4CameraControl                (entry 0xB08FF8)
0xA9C73857 cSC4AnimationTickManager         (entry 0xB08980)
0x49822F75 cSC4EffectsManager               (entry 0xB08C28)
0x2B96B3EA kSC4MessagePostAppServicesInit         (entry 0xB08370)
0xAB96B05F kSC4MessagePostAppServicesInitComplete (entry 0xB08378)
```
**Not in the registry and not present anywhere in .data/.rdata as a dword** (they
exist only as code immediates, so they cannot be named from the binary):
`0xC47B747C`, `0xE9C6262A`, `0x86AD10ED`, `0xC97CF5CD`, `0x2A5C322B`,
`0x287259F6`, `0xCA539340`, `0x0A8CD184`, `0x0A551C50`, `0x48E945B4`.

### The stopwatch API (`this+0x1B8`, `this+0x1D0`)

| Call | Inferred meaning | Proof inside the slice |
|---|---|---|
| `sub_88FEFB` | `IsRunning() -> bool` | 0x7AC866; if false, `sub_8905C4` then nothing else happens that frame |
| `sub_8905C4` | `Start()` | 0x7AC871 |
| `sub_890198` | `ElapsedMilliseconds() -> int` | 0x7AC888 result is clamped to ≤ 0xC8 (200) and later multiplied by `0.001f` → milliseconds ✓ |
| `sub_89058F` | `Reset()` | 0x7AC888, 0x7ACC61 |

---

# 1. `sub_7AC7D0`
`sub_7AC7D0  (0x007AC7D0..0x007AC82F, 96 bytes)`

**PURPOSE** — Constructor of the small (0x14-byte) object that `sub_7ACC90`
registers with the scene through `scene->vt+0x80(obj, 0, 0)`. It is a
two-base (multiple-inheritance) object.

**CONVENTION** — `__thiscall`, `this` in ECX, no stack args, returns `this` in EAX.
`ret` (0 bytes popped).

```c
void* sub_7AC7D0(T* this /*ecx*/) {
    *(void**)this = (void*)0x00A881C0;          // temporary vtable during base ctor
    sub_90DA1E((char*)this + 4);                // base-2 ctor
    *(void**)this       = (void*)0x00AB8CB8;    // final primary vtable
    *(void**)(this + 4) = (void*)0x00AB8CA0;    // final secondary vtable
    *(int*)(this + 0x0C) = 0;
    *(int*)(this + 0x10) = 0;
    sub_7D2B50((char*)this + 0x0C,              // 14 literal args, see below
               1, 1, 1, 0, 1, 0, 0, 7, 0, 1, -1, 0xBF800000 /*-1.0f*/, -1, -1);
    return this;
}
```
The 14 pushes in program order (0x7AC7E4..0x7AC812, i.e. *last* pushed is the
first argument): `-1, -1, 0xBF800000, -1, 1, 0, 7, 0, 0, 1, 0, 1, 1, 1`.
Unsure what `sub_7D2B50` is; the shape (a −1.0f plus a small enum `7` plus a
bag of 0/1 flags) reads like a render-state / material descriptor init.

**FIELDS** — `[this+0x00]` primary vtable, `[this+0x04]` secondary vtable,
`[this+0x0C]`, `[this+0x10]` zeroed then handed to `sub_7D2B50`.

**Class identity**: the scalar-deleting destructor for the same pair of vtables is
`sub_7AB600` (writes 0xAB8CB8 / 0xAB8CA0 at 0x7AB606 / 0x7AB60C). Object size is
**0x14** (`push 0x14; call 0x5E55E0` at 0x7AD071).

**CALLERS** — 1 site: `0x007AD081` in `sub_7ACC90`.

---

# 2. `sub_7AC830`
`sub_7AC830  (0x007AC830..0x007ACACF, 672 bytes)`
**= `cSC4WinRegionScreen` vtable slot `+0x160`** (0x00AB9260 + 0x160).

**PURPOSE** — The region screen's per-frame update. Four jobs, in order:
(a) tick down a flag latch; (b) integrate the smooth scroll toward the target;
(c) clamp the scroll to the region bounds; (d) push the camera position down into
the region view as an integer pan, and tick the animation manager.

**CONVENTION** — `__thiscall`, `this` in ECX, no stack args, returns `bool` (`al=1`).
`ret` (0 bytes popped).

```c
bool cSC4WinRegionScreen::OnTick(void)          // vt+0x160
{
    // ---- (a) deferred flag clear -------------------------------------
    if (this->m_latch_1E8 != 0) {
        if (--this->m_latch_1E8 == 0)
            this->vt_0x110(0x200000, 0);        // clear win flag 0x200000
    }

    // ---- (b) frame delta ---------------------------------------------
    Stopwatch* sw = &this->m_clock_1B8;
    if (!sw->IsRunning()) { sw->Start(); goto clamp; }
    int dtMs = sw->ElapsedMs();
    sw->Reset();
    if (dtMs > 200) dtMs = 200;                 // cmp ebp,0xC8 / jle @0x7AC88D

    if (this->m_scrolling_1FC) {
        float dx = this->m_targetX_1F4 - this->m_scrollX_178;
        float dy = this->m_targetY_1F8 - this->m_scrollY_17C;
        float dist  = sqrtf(dx*dx + dy*dy);
        float speed = 5.0f * dist;              // [0xA84D28]
        if (speed > 1200.0f) speed = 1200.0f;   // [0xAB91B8]  ← hard cap
        float t = speed * (dtMs * 0.001f) / dist;   // [0xA867A4] = 0.001f
        this->m_scrollX_178 += dx * t;
        this->m_scrollY_17C += dy * t;
        if (fabsf(this->m_scrollX_178 - this->m_targetX_1F4) +
            fabsf(this->m_scrollY_17C - this->m_targetY_1F8) <= 2.0f)   // [0xA8825C]
            this->m_scrolling_1FC = 0;
    }

clamp:
    // ---- (c) clamp; any clamp also cancels the scroll ----------------
    if ((float)this->m_minX_180 >  this->m_scrollX_178)
        { this->m_scrollX_178 = (float)this->m_minX_180; this->m_scrolling_1FC = 0; }
    else if ((float)this->m_maxX_188 < this->m_scrollX_178)
        { this->m_scrollX_178 = (float)this->m_maxX_188; this->m_scrolling_1FC = 0; }
    if ((float)this->m_minY_184 >  this->m_scrollY_17C)
        { this->m_scrollY_17C = (float)this->m_minY_184; this->m_scrolling_1FC = 0; }
    else if ((float)this->m_maxY_18C < this->m_scrollY_17C)
        { this->m_scrollY_17C = (float)this->m_maxY_18C; this->m_scrolling_1FC = 0; }

    sub_7AC1A0(this);                           // pushes 178/17C into the camera
    this->m_scene_168->vt_0xB4(&tmpA, &tmpB);   // Note: results never read

    // ---- (d) camera -> integer view pan ------------------------------
    int panX = ROUND(this->m_camera_164->x_98)  - this->GetWidth() /2;   // vt+0xA4
    int panY = ROUND(-this->m_camera_164->y_9C) - this->GetHeight()/2;   // vt+0xA8
    if (this->m_view_0E0) sub_7B4A60(this->m_view_0E0, panX, panY);
    if (this->m_obj_0E4)  { POINT p = {panX,panY}; sub_7A98A0(this->m_obj_0E4, &p); }

    this->m_animTickMgr_158->vt_0x24();
    return true;
}
```

**Load-bearing detail — the ROUND()**. The integer extraction is the classic
"magic number" trick, not a cvt instruction. Bytes at 0x7ACA42:
`D9 05 E0 8B AB 00  99  2B C2  8B 16  D1 F8  2B F8  8B 86 64 01 00 00  8B CE  D8 A0 9C 00 00 00  81 EF 00 …`

```
0x7ACA24  fld  dword [ecx+0x98]        ; camera.x
0x7ACA2C  fadd dword [0xAB8BE0]        ; + 12582912.0f
0x7ACA34  fstp dword [esp+0x1C]
...       edi = [esp+0x1C]  ;  edi -= width/2  ;  edi -= 0x4B400000
```
and for Y the operands are **reversed**:
```
0x7ACA42  fld  dword [0xAB8BE0]        ; 12582912.0f
0x7ACA59  fsub dword [eax+0x9C]        ; − camera.y     ← Y IS NEGATED
0x7ACA65  fstp dword [esp+0x1C]
...       ebp = [esp+0x1C]  ;  ebp -= height/2  ;  ebp -= 0x4B400000
```
So **panX = +round(camera.x) − screenW/2** and **panY = −round(camera.y) − screenH/2**.
The Y-axis inversion between camera space and view-pan space lives here and
nowhere else in the module.

**FIELDS read/written** — `+0x1E8`, `+0x1B8`, `+0x1F4`, `+0x1F8`, `+0x1FC`,
`+0x178`, `+0x17C`, `+0x180`, `+0x184`, `+0x188`, `+0x18C`, `+0x164` (camera,
`+0x98` x, `+0x9C` y), `+0x168` (scene), `+0x0E0` (view), `+0x0E4`, `+0x158`.

**VTABLE CALLS** — `this->vt+0x110(0x200000,0)`; `this->vt+0xA4()` → screen width;
`this->vt+0xA8()` → screen height; `scene->vt+0xB4(ptr,ptr)`;
`animTickMgr->vt+0x24()`.

**DIRECT CALLS** — `sub_88FEFB`, `sub_8905C4`, `sub_890198`, `sub_89058F`,
`sub_7AC1A0` (slice 2), `sub_7B4A60` (slice 6/7 — the view's SetPan),
`sub_7A98A0` (slice 1/2).

**CALLERS** — none direct; reached only through vtable slot +0x160.

**Why this matters for #131/#132** — the scroll speed cap (1200 px/s) and the
arrival epsilon (2.0 px) are in *screen pixels*, so they do **not** rescale with
any UI factor; and the pan hand-off is `camera → int` here, meaning any attempt
to zoom the region map must go through `sub_7AC1A0`/the camera, not through
`+0x178/+0x17C` alone.

---

# 3. `sub_7ACAD0`
`sub_7ACAD0  (0x007ACAD0..0x007ACC8F, 448 bytes)`
**= `cSC4WinRegionScreen` vtable slot `+0x218`.**

**PURPOSE** — Mouse handler. Two behaviours share the body:
if the "armed" latch `+0x1A0` is set it performs hit-testing / double-click
detection; otherwise (and on the fall-through) it *commits* the currently
selected tile: it posts a launch trigger, reconfigures the view, asks the region
manager whether the city at the tile's cell is established, and swaps the view's
overlay art accordingly.

**CONVENTION** — `__thiscall`, `this` in ECX, **3 stack args** (`ret 0xC`).
`arg1` = X, `arg2` = Y (they are handed straight to `sub_7B3A80` and
`sub_7B5DD0`), `arg3` unused. Returns `bool`.

```c
bool cSC4WinRegionScreen::OnMouse(int x, int y, int /*unused*/)   // vt+0x218
{
    if (this->m_armed_1A0) {
        Item* hit = sub_7B3A80(this->m_view_0E0, x, y);          // point -> item
        if (hit && hit == sub_74C6E0(this->m_view_0E0)) {        // == current sel
            void*  sys      = sub_913C72();                      // system-params obj
            int    elapsed  = this->m_dblclk_1D0.ElapsedMs();
            uint32 interval = sys->vt_0xA0();                    // dbl-click ms
            if (elapsed < interval) {
                this->vt_0x23C(0x287259F6, 0x4A560000);          // Note: launch/verb
                return true;
            }
        }
        sub_7B5DD0(this->m_view_0E0, x, y);                      // select at point
        if (sub_74C6E0(this->m_view_0E0) == NULL) {              // nothing selected
            sub_7AC110(this);                                    // deselect path
            return true;
        }
        /* else fall through */
    }

    Item* sel = sub_74C6E0(this->m_view_0E0);
    if (!sel) return true;

    if (g_B43CB8) g_B43CB8->vt_0x2C(1, 0x2A5C322B, 0, 0, 0);     // Note: sound/fx

    void* regionMgr = g_B43C94->vt_0x88();
    void* region    = regionMgr->vt_0x20();

    sub_7ABDF0(this, -1);
    sub_7B2430(this->m_view_0E0, 1);
    sub_7B2410(this->m_view_0E0, 0, 1);
    sub_7B30B0(this->m_view_0E0, (this->m_mode_1A8 == 1), 0);

    uint32 idA = 0x0A8CD184;                                     // default art
    void*  city = region->vt_0x2C( sel->cellX_08, sel->cellY_0C );
    if (city && (*(void**)city)->vt_0xAC())                      // established?
        idA = 0xCA539340;
    sub_7B5E20(this->m_view_0E0, idA, 0x0A551C50);               // set overlay art

    this->m_armed_1A0 = 1;
    this->m_dblclk_1D0.Reset();
    sub_7B3110(this->m_view_0E0, sel, &rect);                    // item -> screen rect
    return true;
}
```

**Key bytes / exact sites**
* 0x7ACAF7 `call 0x7B3A80` with `push [esp+0x28]` (y) then `push [esp+0x24]` (x).
* 0x7ACB11 `call 0x913C72` — returns an **object**, and `edi` (previously the hit
  item) is overwritten by it; the item is only used for the `==` test.
* 0x7ACB2B `call [edx+0xA0]` on that object → the double-click interval; the
  compare at 0x7ACB35 is `elapsed >= interval → not a double click`.
* 0x7ACB40/0x7ACB3B `push 0x287259F6; push 0x4A560000` → `this->vt+0x23C(...)`.
  `0x4A560000` is `3506176.0f` as a float; neither id resolves in the registry.
  Unsure whether this is (msgId, data) or (verb, param).
* 0x7ACC10/0x7ACC13 `mov eax,[edi+0xC]; mov ecx,[edi+8]` → the two ints pushed to
  `region->vt+0x2C`. That is the only place the item's `+0x08/+0x0C` ints are used
  in this slice, which is why they are read as **cell X / cell Y**. Note: The X↔Y
  assignment is by convention only.
* 0x7ACC34/0x7ACC39 vs 0x7ACC40/0x7ACC45 — the *only* difference between the
  established and unestablished branch is `0xCA539340` vs `0x0A8CD184`; the second
  argument `0x0A551C50` is identical on both paths, so it is almost certainly a
  **group** id and the first an **instance** id. (note)

**FIELDS** — `+0x1A0`, `+0x0E0`, `+0x1D0`, `+0x1A8`.
**VTABLE CALLS** — `this->vt+0x23C`; `sys->vt+0xA0`; `g_B43CB8->vt+0x2C`;
`g_B43C94->vt+0x88`; `regionMgr->vt+0x20`; `region->vt+0x2C`; `city->vt+0xAC`.
**CALLERS** — none direct; vtable slot +0x218 only.

---

# 4. `sub_7ACC90`
`sub_7ACC90  (0x007ACC90..0x007AD1EF, 1376 bytes)`

**PURPOSE** — The region screen's scene construction. Acquires the animation-tick
manager, sizes and creates the **terrain grid** from the region's bounding rect,
creates the renderer, the camera and the scene, wires them together, registers a
draw callback, publishes four globals and finally broadcasts two
`kSC4MessagePostAppServicesInit*` messages. **This is where the region map's
sampling resolution is decided.**

**CONVENTION** — `__thiscall`, `this` in ECX, no stack args, `void` (`ret`).

```c
void cSC4WinRegionScreen::BuildScene(void)
{
    IGZCOM* com = sub_90DDF1();

    // ---- animation tick manager -> +0x158 ---------------------------
    Release(this->m_158); this->m_158 = 0;
    com->GetClassObject(0xA9C73857 /*cSC4AnimationTickManager*/,
                        0x86AD10ED, &this->m_158);
    this->m_158->vt_0x0C();                                  // Init()

    // ---- region bounding rect ---------------------------------------
    void* regionMgr = g_B43C94->vt_0x88();
    void* region    = regionMgr->vt_0x2C(this->m_regionIndex_1A4);
    RECT  r;  region->vt_0x60(&r);                           // {l,t,r,b}

    int w = r.right  - r.left + 1;
    int h = r.bottom - r.top  + 1;
    int gridW = min(w, 32) * 16;                             // see byte note
    int gridH = min(h, 32) * 16;

    // ---- terrain grid -> +0x16C and global 0xB43CF8 ------------------
    void* grid = new(0x28) sub_7AACE0(gridW, gridH);
    swap_release(&this->m_grid_16C, grid);
    this->m_grid_16C->vt_0x0C();
    g_B43CF8 = this->m_grid_16C;

    // ---- renderer -> +0x160 -----------------------------------------
    if (!this->m_renderer_160) {
        IGZCOM* c2 = sub_90DDF1();
        Release(this->m_renderer_160); this->m_renderer_160 = 0;
        if (!c2->GetClassObject(0xE9C6262A, 0xE9C6262A, &this->m_renderer_160))
            swap_release(&this->m_renderer_160, new(0x1A8) sub_7FF930());
    }
    sub_648F00(this->m_renderer_160);                        // = mov al,1; ret (no-op)

    // ---- camera -> +0x164 -------------------------------------------
    if (!this->m_camera_164) {
        IGZCOM* c3 = sub_90DDF1();
        Release(this->m_camera_164); this->m_camera_164 = 0;
        if (!c3->GetClassObject(0xC9C628EC /*cSC4CameraControl*/,
                                0xC9C628EC, &this->m_camera_164))
            swap_release(&this->m_camera_164, new(0x160) sub_7CC990());
    }
    sub_7CB9B0(this->m_camera_164, this->GetWidth(), this->GetHeight());   // vt+0xA4 / vt+0xA8
    sub_7CDAA0(this->m_camera_164, (float)(w << 10), (float)(h << 10));    // 1024 units / region cell
    { float eye[3] = { 512.0f, 0.0f, 512.0f };                             // 0x44000000,0,0x44000000
      sub_7CDB20(this->m_camera_164, eye, this->m_renderer_160); }

    // ---- a graphics object from GZCOM -------------------------------
    void* gfx = 0;
    g_B43C9C->vt_0x00(0xC47B747C, &gfx);

    // ---- scene -> +0x168 --------------------------------------------
    swap_release(&this->m_scene_168, new(0x2E8) sub_7C9B10());
    this->m_scene_168->vt_0x18(gfx);
    this->m_scene_168->vt_0x30(this->GetWidth(), this->GetHeight());
    this->m_scene_168->vt_0x1C(gfx->vt_0x0C());
    this->m_scene_168->vt_0x3C(this->m_renderer_160);
    this->m_scene_168->vt_0x44(this->m_camera_164);
    this->m_scene_168->vt_0xDC(1);
    this->m_scene_168->vt_0x14( max(1, max((gridW+63)/64, (gridH+63)/64)) );
    this->m_scene_168->vt_0x0C();

    // ---- draw callback ----------------------------------------------
    T* cb = new(0x14) sub_7AC7D0();
    if (cb) cb->AddRef();
    this->m_scene_168->vt_0x80(cb, 0, 0);
    if (cb) cb->Release();

    sub_7CD6E0(this->m_camera_164, 0.25f);                   // 0x3E800000

    g_B43DD8 = this->m_scene_168->vt_0x20();
    g_B43DDC = this->m_scene_168->vt_0x24();
    g_B43DD0 = this->m_scene_168;

    sub_7AC1A0(this);

    // ---- effects manager -> +0x15C and global 0xB43D1C ---------------
    IGZCOM* c4 = sub_90DDF1();
    Release(this->m_fx_15C); this->m_fx_15C = 0;
    c4->GetClassObject(0x49822F75 /*cSC4EffectsManager*/, 0xC97CF5CD, &this->m_fx_15C);
    this->m_fx_15C->vt_0x0C();
    g_B43D1C = this->m_fx_15C;

    // ---- broadcast ---------------------------------------------------
    if (g_B43CCC) {
        Msg* m = new(0x2C) sub_9134D6(); m->AddRef();
        m->vt_0x14(0x2B96B3EA);          // kSC4MessagePostAppServicesInit
        g_B43CCC->vt_0x10(m, 0);
        Msg* n = new(0x2C) sub_9134D6(); n->AddRef();
        n->vt_0x14(0xAB96B05F);          // kSC4MessagePostAppServicesInitComplete
        g_B43CCC->vt_0x10(n, 0);
        n->Release(); m->Release();
    }
}
```

**Load-bearing byte note — the grid dimension math.**
Bytes at 0x7ACD04: `B9 20 00 00 00 89 44 24 14 3B C1 89 4C 24 10 8D 44 24 10 7F 04 8D 44 24 14 8B 00 C1 E0 06 99 83 E2 03 03 C2 8B D8 …`

```
mov  ecx, 0x20                 ; 32
mov  [esp+0x14], eax           ; span
cmp  eax, ecx
mov  [esp+0x10], ecx
lea  eax, [esp+0x10]           ; -> 32
jg   +4                        ; span > 32 ? keep 32
lea  eax, [esp+0x14]           ; -> span
mov  eax, [eax]                ; = min(span, 32)
shl  eax, 6                    ; * 64
cdq / and edx,3 / add eax,edx / sar eax,2      ; signed /4
                               ; net effect = min(span,32) * 16
```
So the terrain grid is **min(regionSpan, 32) × 16 samples per axis**, i.e. 16
samples per region-config pixel, i.e. **one height sample per 4×4 game cells**
(a config.bmp pixel = 64×64 cells). The `32` is a hard clamp: regions wider than
32 config pixels get no extra grid resolution.

The scene LOD argument is `max(1, max(ceil(gridW/64), ceil(gridH/64)))`
(0x7AD011..0x7AD063; the `+0x3F / sar 6` pair is a signed divide by 64).
The camera world extent is `(span) * 1024` **units per region-config pixel**
(`shl ecx, 0xA` at 0x7ACEE9 and `shl edx, 0xA` at 0x7ACF02).

**FIELDS** — `+0x158, +0x15C, +0x160, +0x164, +0x168, +0x16C, +0x1A4`.
**CALLERS** — 1 site: `0x007B1ABC` in `sub_7B1900` (`cSC4WinRegionScreen::Init`).

---

# 5. `sub_7AD1F0`
`sub_7AD1F0  (0x007AD1F0..0x007AD2BF, 208 bytes)`

**PURPOSE** — Hoare partition step of an introsort over 12-byte records
`struct T12 { int a; int b; int level; }`, using the composite key
`key(n) = n.a + n.b + (1 << n.level)` with `n.a` as the tie-breaker.

**CONVENTION** — `__cdecl`, 5 stack args, no `this`, `ret` (caller cleans).
`sub_7AD1F0(T12* first, T12* last, int pivotA, int pivotB, int pivotLevel)`
(args at `[esp+4] .. [esp+0x14]` at entry). It returns nothing usable in EAX;
the caller (`sub_7AE8D0`) recomputes the cut.

Bytes at 0x7AD212 (the key computation, the load-bearing part):
`8B 48 08  8B 38  BA 01 00 00 00  D3 E2  03 50 04  8B 4C 24 30  2B D5  2B D1  2B D3  03 D7  78 …`
```
mov  ecx, [eax+8]          ; n.level
mov  edi, [eax]            ; n.a
mov  edx, 1 ; shl edx, cl  ; 1 << n.level
add  edx, [eax+4]          ; + n.b
mov  ecx, [esp+0x30]       ; pivotB
sub  edx, ebp              ; − (1 << pivotLevel)
sub  edx, ecx              ; − pivotB
sub  edx, ebx              ; − pivotA
add  edx, edi              ; + n.a
js / jne / cmp edi,ebx / jge
```
i.e. `edx = key(n) − key(pivot)`; advance while `edx < 0`, or `edx == 0 && n.a < pivot.a`.
The mirror loop from the right (0x7AD23C) uses the negated form, then the two
12-byte records are swapped in place through `[esp+0x18]/[esp+0x1C]`.

**INTERPRETATION** — `a + b + size` is the far corner along the isometric depth
axis of a `2^level`-sized quad. This is the **painter-order sort of the region
terrain quadtree**, which is exactly the vector living at **item+0x74**.

**CALLERS** — 1 site: `0x007AE959` in `sub_7AE8D0` (the quicksort driver).

---

# 6. `sub_7AD2C0`
`sub_7AD2C0  (0x007AD2C0..0x007AD30F, 80 bytes)`

**PURPOSE** — `std::list<refptr>::erase(first, last)`: walk the node chain,
unlink each node (`node->next->prev`, `node->prev->next`), `Release()` the
payload at `node+8` (`vt+0x08`), free the node with `sub_90CF63` (`operator delete`).

**CONVENTION** — `__thiscall` with `this` **unused**; 3 stack args (`ret 0xC`):
`(iterator* out, node* first, node* last)`; the result iterator is written to
`*out` (`mov eax,[esp+0xC]; mov [eax], ebx` at 0x7AD2F8).
Node layout: `+0x00 next`, `+0x04 prev`, `+0x08 refcounted payload`.

**CALLERS** — 1 site: `0x007ADE12` in `sub_7ADD80`.

---

# 7. `sub_7AD310`
`sub_7AD310  (0x007AD310..0x007AD3AF, 160 bytes)`

**PURPOSE** — `std::make_heap(first, last, cmp)` over `T12` (12-byte records).

**CONVENTION** — `__cdecl`. `sub_7AD310(T12* first, T12* last, X cmpCtx, ...)`;
the caller (`sub_7ADE50`) pushes **5** dwords (`first, middle, ctx, 0, 0`) and
cleans 0x14. Element count is computed by the `0x2AAAAAAB` reciprocal-multiply
idiom (`imul; sar edx,1; shr/add`) = divide by 12.

```c
int n = (last - first) / 12;
if (n < 2) return;
int hole = (n - 2) / 2;
T12* p = first + hole;
for (;;) {
    sub_7AC4D0(first, hole, n, *p, ctx);      // __adjust_heap
    if (hole == 0) break;
    --hole; p -= 1;                            // p -= 12 bytes
}
```
`sub_7AC4D0` (slice 2) is `__adjust_heap(first, holeIndex, len, value, cmp)`;
`value` is passed **by value** as three dwords via `sub esp,0xC` + three stores.

**CALLERS** — 1 site: `0x007ADE6A` in `sub_7ADE50`.

---

# 8. `sub_7AD3B0`
`sub_7AD3B0  (0x007AD3B0..0x007AD3FF, 80 bytes)`
**= vtable `0x00AB8CD0` slot `+0x21C`** (the sibling region window class:
ctor `sub_7AAE10`, dtor `sub_7AC5C0`, built from `sub_7B1900` at 0x7B1E38).

**PURPOSE** — Mouse handler on that class: fetch a child/sub-object by id
`0x48E945B4`, hand it to `vt+0x40`, clear window flag `0x200000`, notify the
object at `this+4`, then delegate the real work to `sub_7AC620`.

**CONVENTION** — `__thiscall`, `this` in ECX, 3 stack args (`ret 0xC`); only the
first two are used. Returns `bool` (`al = 1`).

```c
bool T::OnMouse(int a, int b, int /*unused*/)      // vt+0x21C
{
    void* o = this->vt_0x88(0x48E945B4);           // Note: GetChildFromID / GetIface
    if (o) this->vt_0x40(o);
    this->vt_0x110(0x200000, 0);                   // clear the same flag as sub_7AC830
    ((T2*)this->m_04)->vt_0x74(this);              // Note: [this+4] treated as an object
    sub_7AC620(this, a, b);
    return true;
}
```
Unsure: `[this+4]` as an object pointer is unusual for a `cGZWin` (where +4 is
often the refcount); it is what the bytes do (`mov ecx,[esi+4]; mov edx,[ecx];
push esi; call [edx+0x74]` at 0x7AD3DD..0x7AD3E3) but the field's identity is a guess.

**CALLERS** — none direct; vtable slot only. Note that the *region screen's*
equivalent slot `+0x21C` is `sub_7AB790` (slice 2) and the base implementation
in `cSC4WinRegionView` is `0x009378BC`.

---

# 9. `sub_7AD400`
`sub_7AD400  (0x007AD400..0x007AD79F, 928 bytes)`
### The most relevant function in this slice for "how a tile is BUILT".

**PURPOSE** — Scans one 8-bit channel of a 32-bpp bitmap and rebuilds a
`std::vector<uint32>` run-list describing the non-zero horizontal spans, with an
optional per-pixel value payload.

**CONVENTION** — **`__usercall`.** The destination `std::vector<uint32>*` arrives
in **ESI** (the function's first instruction is `mov eax,[esi+4]` with ESI never
initialised). Three `__cdecl` stack args, caller cleans (`add esp,0x24; ret`):

```
sub_7AD400@<esi=vector>( cIGZBitmap* bmp /*[esp+4]*/,
                         int         shift /*[esp+8]*/,
                         BOOL        emitValues /*[esp+0xC]*/ )
```
Proven by the three call sites in `sub_7AE510`:
```
0x7AE730  lea edi,[ebx+0x20]      ; the bitmap slot
0x7AE735  lea esi,[ebx+0x44]      ; <-- vector in ESI
0x7AE738  push edx                ; bmp = [ebx+0x20]
0x7AE739  call 0x7AD400           ; args: (bmp, 0,    0)
0x7AE744  lea esi,[ebx+0x5C]
0x7AE748  call 0x7AD400           ; args: (bmp, 8,    1)
0x7AE753  lea esi,[ebx+0x50]
0x7AE757  call 0x7AD400           ; args: (bmp, 0x10, 1)
0x7AE75F  add esp,0x2C            ; 3 calls x 3 dwords + 2 dwords elsewhere
```

**PSEUDO-C**
```c
void BuildRunList@<esi>(vector<u32>* v, cIGZBitmap* bmp, int shift, BOOL emitValues)
{
    v->end = v->begin;                       // ALWAYS clears — see byte note
    if (!bmp->vt_0x18(0x800)) return;        // Lock(0x800)

    RECT* r = bmp->vt_0x30();                // GetRect
    int H = r->bottom - r->top;
    int W = r->right  - r->left;
    if (H <= 0) return;

    u32 rowKey = 0;                          // += 0x10000 per row  (y << 16)
    for (int y = 0; y < H; ++y) {
        u8*  row  = (u8*)bmp->vt_0x88() + bmp->vt_0x8C() * y;   // bits + pitch*y
        u32* px   = (u32*)row;
        bool inRun = false;
        int  runStart = 0;
        for (int x = 0; x < W; ++x) {
            u32 s = px[x] >> shift;
            if ((u8)s != 0) {
                if (!inRun) { v->push_back(rowKey + x); runStart = x; inRun = true; }
            } else if (inRun) {
                v->push_back(rowKey + x);                     // run END
                if (emitValues)
                    for (int i = runStart; i < x; ++i)
                        v->push_back((px[i] >> shift) & 0xFF);
                inRun = false;
            }
        }
        if (inRun) {                                          // run reaches the edge
            v->push_back(rowKey + W);
            if (emitValues)
                for (int i = runStart; i < W; ++i)
                    v->push_back((px[i] >> shift) & 0xFF);
        }
        rowKey += 0x10000;
    }
}
```

**Load-bearing byte notes**

1. *The clear is unconditional.* Bytes at 0x7AD400:
   `8B 46 04  8B 0E  83 EC 24  3B C0  57  75 04  8B C1  EB 11 …`
   `3B C0` is `cmp eax, eax` — ZF is **always** set, so the `jne` at 0x7AD40B is
   never taken and the function always falls into `mov eax, ecx` (`8B C1`, eax =
   `v->begin`) → `mov [esi+4], eax`. The `memmove` arm at 0x7AD411..0x7AD420 is
   dead code (an inlined `erase(end,end)` the compiler could not fold away).

2. *The pixel read.* Bytes at 0x7AD4B0:
   `8B 4C 24 0C  8B 14 8B  8B 4C 24 38  D3 EA  84 D2  74 53 …`
   `mov edx,[ebx+ecx*4]` — 4-byte stride, so the buffer is 32 bpp (consistent with
   the `{9, 0x20}` format the composite is initialised with). `shr edx, cl` uses
   `cl` loaded from `[esp+0x38]` = **arg2**, and `test dl,dl` tests only the
   **low byte** after the shift.

3. *Pitch is in bytes.* `rowPtr = vt_0x88() + vt_0x8C() * y` and the indexing is
   `[rowPtr + x*4]`; if `vt+0x8C` returned a pixel count the arithmetic would be
   wrong by ×4. → `vt+0x88 = GetBits`, `vt+0x8C = GetPitchBytes`.

4. *`emitValues` is re-loaded from the arg slot* at 0x7AD557 (`mov al,[esp+0x3C]`)
   and 0x7AD68B, because the register holding `inRun` is destroyed by the
   `push_back` helper `sub_51CA60` (which is `__thiscall` and cleans 0x14 bytes —
   proven by the two writes of the same local `[esp+0x10]` at 0x7AD4E8 and
   0x7AD509 having to resolve to the same address).

**Run-list wire format** (per opaque span):
`[ (y<<16) | xStart ] , [ (y<<16) | xEnd ]` then, only when `emitValues`,
`xEnd − xStart` further dwords each holding one channel byte (`0..0xFF`).

**INTERPRETATION** — shifts 0 / 8 / 0x10 are the B / G / R byte lanes of an
ARGB dword; there is **no** shift-24 (alpha) call. Unsure whether the source at
`item+0x20` is a genuine colour image (in which case these are three colour
planes) or a purpose-built mask image whose three low bytes carry three different
masks. The fact that lane 0 is stored **without** values (a pure span index) and
lanes 8 and 0x10 **with** values argues for the mask reading.

**BITMAP VTABLE SLOTS USED** (class 0x00AC1400):
`vt+0x18 Lock(0x800)->bool`, `vt+0x30 GetRect()`, `vt+0x88 GetBits()`,
`vt+0x8C GetPitchBytes()`.

**HELPERS** — `sub_51CA60` (vector `_Insert_n`, `ret 0x14`), `sub_90CF54`
(`operator new`), `sub_90CF63` (`operator delete`), `sub_9EEB70` (`memmove`).

**CALLERS** — 3 sites, all in `sub_7AE510`: 0x007AE739, 0x007AE748, 0x007AE757.

---

# 10. `sub_7AD7A0`
`sub_7AD7A0  (0x007AD7A0..0x007AD8CF, 304 bytes)`

**PURPOSE** — `std::vector<T12>::operator=(const vector<T12>&)`. Element size 12
(all four `0x2AAAAAAB` reciprocal multiplies). Three paths: reallocate-and-copy
(`sub_623FA0` = uninitialised copy), overwrite-in-place (`sub_6143E0` = copy),
or copy + copy-construct the tail.

**CONVENTION** — `__thiscall`, `this` in ECX (the destination vector),
1 stack arg (`ret 4`) = source vector. Returns `this`.
Vector layout `{ +0 begin, +4 end, +8 cap }`.

**CALLERS** — 5 sites, only one of them in this module:
`0x004A4C28` (`sub_4A4C20`), `0x004A8A6C` (`sub_4A8A40`), `0x0063E0DB`
(`sub_63E060`), `0x0071A713` (`sub_71A0C0`), `0x007AE152` (`sub_7ADFA0`).
The four foreign callers confirm `T12` is a general-purpose engine type, not a
region-only struct.

---

# 11. `sub_7AD8D0`
`sub_7AD8D0  (0x007AD8D0..0x007AD95F, 144 bytes)`

**PURPOSE** — SGI-STL `__linear_insert(first, last, value, cmp)` for `T12`.

**CONVENTION** — `__cdecl`, 6 stack args, `ret`:
`(T12* first, T12* last, int val.a, int val.b, int val.level, X cmp)`
— the value is passed **by value** as three dwords.

```c
if ( key(val) < key(*first) ||
    (key(val) == key(*first) && val.a < first->a) ) {
    sub_614430(first, last, last + 1, &tmp, 0);     // copy_backward
    *first = val;
} else {
    sub_7AA9C0(last, val, cmp);                      // __unguarded_linear_insert
}
```
Key identical to `sub_7AD1F0`: `a + b + (1 << level)`.

**CALLERS** — 1 site: `0x007ADD6A` in `sub_7ADD30`.

---

# 12. `sub_7AD960`
`sub_7AD960  (0x007AD960..0x007AD9FF, 160 bytes)`

**PURPOSE** — `std::sort_heap(first, last, cmp)` for `T12`: while `n > 1`, swap
`*first` with `*(last-1)` and `sub_7AC4D0(first, 0, n-1, savedValue, cmp)`.

**CONVENTION** — `__cdecl`, 3+ stack args (`first` at `[esp+4]`, `last` at
`[esp+8]`, ctx at `[esp+0xC]`), `ret`.

**CALLERS** — 1 site: `0x007ADF24` in `sub_7ADE50`.

---

# 13. `sub_7ADA00`
`sub_7ADA00  (0x007ADA00..0x007ADABF, 192 bytes)`
### Destructor of the 0x80-byte region tile item.

**PURPOSE** — Release/free every owned member of the tile item. This is the
cleanest single source of truth for the item layout.

**CONVENTION** — `__thiscall`, `this` in ECX, no args, `void`. Bytes at 0x7ADA00:
`56 8B F1 8B 46 74 85 C0 74 09 50 E8 53 F5 15 00 83 C4 04 57 …`

```c
void Item::~Item(void)
{
    if (this->vec74_begin) operator delete(this->vec74_begin);   // vector<T12> at +0x74
    sub_473EC0(&this->list70);                                   // list::clear
    if (*(void**)&this->list70) operator delete(*(void**)&this->list70);
    if (this->vec5C_begin) operator delete(this->vec5C_begin);
    if (this->vec50_begin) operator delete(this->vec50_begin);
    if (this->vec44_begin) operator delete(this->vec44_begin);
    if (this->vec38_begin) operator delete(this->vec38_begin);
    if (this->p30) this->p30->Release();
    if (this->p2C) this->p2C->Release();
    if (this->p28) this->p28->Release();
    if (this->p24) this->p24->Release();
    if (this->p20) this->p20->Release();
    if (this->p1C) this->p1C->vt_0x08();      // tail JMP at 0x7ADAB4
}
```
Note it frees `+0x74`, `+0x5C`, `+0x50`, `+0x44`, `+0x38` **begin pointers**
directly (no `end`/`cap` fixup) — i.e. these are POD vectors.

**CALLERS** — 4 sites: `0x007B0BE2` (`sub_7B0BB0`), `0x007B0F24` (`sub_7B0E60`),
`0x007B12F4` (`sub_7B1200`), `0x007B154B` (`sub_7B13C0`).

---

# 14. `sub_7ADAC0`
`sub_7ADAC0  (0x007ADAC0..0x007ADC1F, 352 bytes)`

**PURPOSE** — Find a region by name and make it current.
Iterates the region manager's list, materialises each region's name into a
heap buffer, `memcmp`s it against the caller's string, and on a hit either
returns early (already current) or switches to it.

**CONVENTION** — `__thiscall`, `this` in ECX, 1 stack arg (`ret 4`) = a
`cIGZString`-like object whose `{begin,end}` char range lives at `+4`/`+8`.
Returns `bool`.

```c
bool cSC4WinRegionScreen::SelectRegionByName(cIGZString* name)   // Note: name is a guess
{
    void* mgr = g_B43C94->vt_0x88();
    uint32 n  = mgr->vt_0x18();                       // count
    for (uint32 i = 0; i < n; ++i) {
        void* rgn = mgr->vt_0x2C(i)->vt_0x0C();
        char* p   = rgn->vt_0x1C();                   // name ptr
        uint32 len= rgn->vt_0x18();                   // name length
        uint32 sz = len + 1;
        char* buf = (sz == 0 || sz > 0xFFFFFFFF) ? throw_length_error("basic_string")
                                                 : (char*)operator new(sz);
        memmove(buf, p, len); buf[len] = 0;

        const char* s0 = name ? ((char**)name)[1] : 0;   // name+4
        const char* s1 = name ? ((char**)name)[2] : 0;   // name+8
        if ((s1 - s0) == len && memcmp(s0, buf, len) == 0) {
            if (i == this->m_regionIndex_1A4) { free(buf); return true; }   // already current
            mgr->vt_0x24(i);                              // set current region
            bool ok = g_B43C94->vt_0x30(0);
            free(buf);
            return ok;
        }
        free(buf);
    }
    return false;
}
```
`this` is only used for the `+0x1A4` comparison (it is spilled to the frame at
0x7ADAC5 and reloaded at 0x7ADBB5 as `[esp+0x1C]`).
The `0xA806F0` string `"basic_string"` is only reached on the length-error path
(`sub_9DD1D0`).

**CALLERS** — 1 site: `0x007AF7B6` in `sub_7AF720`.

---

# 15. `sub_7ADC20`
`sub_7ADC20  (0x007ADC20..0x007ADD2F, 272 bytes)`

**PURPOSE** — Transition helper: given a `T**` handle, ask the app to enter that
object by name; on failure, drop the app's cached object at `+0x200` and take the
generic path instead.

**CONVENTION** — `__thiscall`, `this` in ECX, 1 stack arg (`ret 4`) = `T** pp`.
Returns `bool`.

```c
bool T::Enter(Obj** pp)
{
    this->AddRef();                             // vt+0x04
    sub_7AC2D0(this);
    void* app = g_B43C94;
    app->vt_0x88()->vt_0x20();                  // Note: result discarded

    Obj* o = *pp;  if (o) o->AddRef();

    cRZString s;                                // vtable 0x00A80810, 8-byte buffer
    o->vt_0x7C(&s);                             // GetName(s)

    bool ok;
    if (s.begin != s.emptyBuf) {                // the name is non-empty
        ok = app->vt_0x34(&s, pp);              // enter-by-name
        if (!ok) goto generic;
    } else {
generic:
        void* c = app->vt_0x9C();
        Release(*(void**)((char*)c + 0x200));   // drop the cached object
        *(void**)((char*)c + 0x200) = 0;
        ok = app->vt_0x18(pp);
    }
    this->Release();                            // vt+0x08
    s.~cRZString();
    if (o) o->Release();
    return ok;
}
```
Unsure about `vt_0x34` / `vt_0x18` naming; the *shape* (name first, generic
fallback second, with a cache invalidation in between) is solid.

**CALLERS** — 3 sites: `0x007AF5E1` and `0x007AF66F` in `sub_7AF4B0`,
`0x007AFDF8` in `sub_7AFAA0`.

---

# 16. `sub_7ADD30`
`sub_7ADD30  (0x007ADD30..0x007ADD7F, 80 bytes)`

**PURPOSE** — `__insertion_sort(first, last, cmp)` for `T12`:
for `i = first+1; i != last; ++i` call `sub_7AD8D0(first, i, *i, cmp)`.
Returns immediately if `first == last` or `first+1 == last`.

**CONVENTION** — `__cdecl`, 3 stack args, `ret`.
**CALLERS** — 2 sites, both in `sub_7ADF40`: 0x007ADF72, 0x007ADF90.

---

# 17. `sub_7ADD80`
`sub_7ADD80  (0x007ADD80..0x007ADE4F, 208 bytes)`

**PURPOSE** — `std::list<refptr>::operator=`: walks both chains in lockstep,
assigning payloads with correct AddRef-new / Release-old ordering, then either
erases the surplus tail (`sub_7AD2C0`) or inserts the shortfall (`sub_6C6CA0`).

**CONVENTION** — `__thiscall`, `this` in ECX (destination list), 1 stack arg
(`ret 4`) = source list. Returns `this` in EAX.
Node layout `{ +0 next, +4 prev(unused here), +8 payload }`; the list head is the
sentinel (loop terminates on `node == head`).

**CALLERS** — 1 site: `0x007AE146` in `sub_7ADFA0`.

---

# 18. `sub_7ADE50`
`sub_7ADE50  (0x007ADE50..0x007ADF3F, 240 bytes)`

**PURPOSE** — `std::partial_sort(first, middle, last, cmp)` for `T12`.

**CONVENTION** — `__cdecl`, 5 stack args, `ret`:
`(T12* first, T12* middle, T12* last, X cmpCtx, ...)`.

```c
sub_7AD310(first, middle, ctx, 0, 0);            // make_heap
for (T12* i = middle; i < last; ++i)
    if (key(*i) < key(*first) || (equal && i->a < first->a))
        sub_7AC4D0(first, 0, (last_arg - first)/12, *i, ctx);   // pop-and-push
sub_7AD960(first, middle, ctx);                  // sort_heap
```
Key computed inline at 0x7ADE80..0x7ADEB0 — identical to `sub_7AD1F0`.

**CALLERS** — 1 site: `0x007AE999` in `sub_7AE8D0`.

---

# 19. `sub_7ADF40`
`sub_7ADF40  (0x007ADF40..0x007ADF9F, 96 bytes)`

**PURPOSE** — SGI-STL `__final_insertion_sort(first, last, cmp)`.

**CONVENTION** — `__cdecl`, 3 stack args, `ret`.

```c
int n = (last - first) / 12;
if (n > 16) {                                    // cmp eax,0x10 / jle @0x7ADF61
    T12* cut = first + 16;                       // lea edi,[esi+0xC0]  (16*12 = 0xC0)
    sub_7ADD30(first, cut, cmp);                 // insertion_sort the first 16
    sub_7AC490(cut, last, 0, cmp);               // __unguarded_insertion_sort
} else {
    sub_7ADD30(first, last, cmp);
}
```
The `0xC0 = 16 × 12` constant is the direct byte proof that the element is 12 bytes.

**CALLERS** — 1 site: `0x007AED4E` in `sub_7AED00`.

---

# 20. `sub_7ADFA0`
`sub_7ADFA0  (0x007ADFA0..0x007AE15F, 448 bytes)`
### Copy-assign of the 0x80-byte region tile item.

**PURPOSE** — Field-by-field assignment of one tile item to another. Together with
`sub_7ADA00` this pins the item layout exactly.

**CONVENTION** — `__thiscall`, `this` in ECX (destination), 1 stack arg
(`ret 4`) = source. Returns `this` in EAX.
Head bytes 0x7ADFA0: `53 55 56 8B F1 57 8B 7C 24 14 8B 07 89 06 8B 4F …`
Tail bytes 0x7AE14B: `83 C7 74 57 8D 4E 74 E8 49 F6 FF FF 5F 8B C6 5E 5D 5B C2 04 00`
(`add edi,0x74; push edi; lea ecx,[esi+0x74]; call sub_7AD7A0; … ret 4`).

```c
Item& Item::operator=(const Item& s)
{
    d[0x00] = s[0x00];  d[0x04] = s[0x04];
    d[0x08] = s[0x08];  d[0x0C] = s[0x0C];      // int cell coords
    d[0x10] = s[0x10];  d[0x14] = s[0x14];      // float screen pos
    d.b[0x18] = s.b[0x18];                      // size class (byte)

    assign_refptr(&d[0x1C], s[0x1C]);           // AddRef new, store, Release old
    assign_refptr(&d[0x20], s[0x20]);
    assign_refptr(&d[0x24], s[0x24]);
    assign_refptr(&d[0x28], s[0x28]);
    assign_refptr(&d[0x2C], s[0x2C]);
    assign_refptr(&d[0x30], s[0x30]);

    d.b[0x34] = s.b[0x34];                      // built flag (byte)

    sub_462C10(&d[0x38], &s[0x38]);             // vector<u32>::operator=
    sub_462C10(&d[0x44], &s[0x44]);
    sub_462C10(&d[0x50], &s[0x50]);
    sub_462C10(&d[0x5C], &s[0x5C]);

    d[0x68] = s[0x68];  d[0x6C] = s[0x6C];

    sub_7ADD80(&d[0x70], &s[0x70]);             // list<refptr>::operator=
    sub_7AD7A0(&d[0x74], &s[0x74]);             // vector<T12>::operator=
    return d;                                    // last field ends at 0x74+0x0C = 0x80 ✓
}
```
Each `assign_refptr` is the 6-instruction MSVC pattern
`if (new != old) { if (new) new->AddRef(); *slot = new; if (old) old->Release(); }`
(`call [edx+4]` = AddRef, `call [eax+8]` = Release), repeated verbatim at
0x7ADFDC, 0x7AE00D, 0x7AE03F, 0x7AE071, 0x7AE0A3, 0x7AE0D5.

**CALLERS** — 1 site: `0x007AE9D3` in `sub_7AE9B0`.

---

# 21. `sub_7AE160`
`sub_7AE160  (0x007AE160..0x007AE3CF, 624 bytes)`
### The module's resampler. Contradicts the "nothing resamples" reading.

**PURPOSE** — One 1-D filtered resample pass over a 32-bpp image: it builds a
filter weight table with a **unit tent kernel**, then walks the destination in
**16.16 fixed point**, emitting one filtered span per destination row and
zero-filling rows whose source index falls outside `[0, srcH-1]`.

**CONVENTION** — `__cdecl`, **12 dwords of arguments** (`add esp, 0x30` at the
call site 0x7AE4E3), `ret`. Fully resolved from `sub_7AE3D0`'s push sequence
(0x7AE484..0x7AE4DB; in `__cdecl` the *last* push is arg 1, and the two doubles
were stored above the pushes by the `sub esp,0x10` at 0x7AE484, so they are the
*last* arguments). In `sub_7AE3D0`, **`edi` = arg1 = the SOURCE bitmap** and
**`esi` = *arg2 = the DESTINATION bitmap**.

| arg | pushed at | expression | meaning |
|---|---|---|---|
| 1 | 0x7AE4DB | `esi->vt_0x88()` | **dst bits** |
| 2 | 0x7AE4D0 | `esi->vt_0x8C()` | **dst pitch (bytes)** |
| 3 | 0x7AE4BA | `edi->vt_0x88()` | **src bits** |
| 4 | 0x7AE4B1 | `edi->vt_0x8C()` | **src pitch (bytes)** |
| 5 | 0x7AE4A7 | `esi->vt_0x24()` | dst width |
| 6 | 0x7AE4A1 | `esi->vt_0x28()` | dst height |
| 7 | 0x7AE497 | `edi->vt_0x24()` | src width |
| 8 | (0x7AE494 result) | `edi->vt_0x28()` | src height |
| 9–10 | `[esp]` | **double** = `sub_7AE3D0` arg3 (its 1st double) | axis-1 parameter, read at 0x7AE163 |
| 11–12 | `[esp+8]` | **double** = `sub_7AE3D0` arg4 (its 2nd double) | axis-2 parameter, read at 0x7AE1DA |

(Arg 8 lands from the `push eax` at 0x7AE497 that follows the `call [edx+0x28]`
at 0x7AE494 — the eight pushes at 0x7AE497/4A1/4A7/4B1/4BA/4C7/4D0/4DB carry, in
push order, `edi.h, edi.w, esi.h, esi.w, edi.pitch, edi.bits, esi.pitch, esi.bits`.)

**Skeleton** — note the two filter builds are **inside this one function** (one
per axis); `sub_7AE3D0` calls `sub_7AE160` exactly **once** (single call site
0x7AE4DC).
```c
void Resample2D(...)
{
    // ---- axis 1 ----------------------------------------------------
    float d1 = -(float)arg9_10;                                   // fchs @0x7AE169
    sub_7AA860(d1, 1.0f, &tblA1, &tblB1, sub_7AA0E0 /*kernel*/, 16384.0f);
    sub_7BFF20(&a1, &b1, &c1, 0x4000 /*16384*/);
    // ---- axis 2 ----------------------------------------------------
    float d2 = -(float)arg11_12;                                  // fchs @0x7AE1E4
    sub_7AA860(d2, 1.0f, &tblA2, &tblB2, sub_7AA0E0, 16384.0f);
    sub_7BFF20(&a2, &b2, &c2, 0x4000);
    // ---- the walk --------------------------------------------------

    int   acc  = 0xFFFF0000;                 // 16.16 = -1.0
    for (int row = 0; row < rows; ++row) {
        int srcRow = (acc >> 16) + 2;        // sar eax,0x10
        int span   = min(srcRow - prev, ...);
        for (...) {
            if (0 <= idx && idx <= height-1)
                sub_7AA110(dst, src + idx*pitch, n, ..., 0xFFFF0000);
            else
                memset(dst, 0, n);           // sub_910003
        }
        sub_7AABB0(...);                     // row finish
        acc += 0x10000;                      // advance 1.0
    }
    // frees 2 temp buffers via the loop at 0x7AE3B0 (edi=2, esi walks back by 0xC)
}
```

**The kernel is the load-bearing evidence.** `sub_7AA0E0`, the function pointer
pushed at 0x7AE172 / 0x7AE1EB:
```
0x7AA0E0  fld   qword [esp+4]
0x7AA0E4  fabs
0x7AA0E6  fcom  qword [0xA80AB0]        ; 1.0
0x7AA0EE  test  ah,5 / jp 0x7AA0FA
0x7AA0F3  fsubr qword [0xA80AB0]        ; return 1.0 - |x|
0x7AA0FA  fstp  st(0) / fld qword [0xA80990]   ; return 0.0
```
= `f(x) = max(0, 1 − |x|)` — a unit-support **triangle filter**, i.e. bilinear.
Its companion `sub_7AA110` is a 16.16-stepped, edge-clamped, 4-bytes-per-pixel
scanline accumulator (`sar eax,0x10`, `lea edx,[ecx+eax*4]`, clamp against
`[edi-2]`).

**What `sub_7AE3D0` (the caller, slice 4) does with it** —
`sub_7AE3D0(cIGZBitmap* src, cIGZBitmap** pDst, double d1, double d2)`
(`__cdecl`, 6 dwords, `add esp,0x18` at 0x7AE5C0). It Locks both bitmaps with
flag `0x8040` (`vt+0x18` / `vt+0x1C`), reads the **source** rect with `vt+0x2C`
and initialises the destination to **`(srcW + 2, srcH + 2)`** with format
`{9, 0x20}` — bytes 0x7AE439 `add eax,2`, 0x7AE43C `add ecx,2`,
0x7AE443 `call [edx+0xC]` — then makes the single `sub_7AE160` call. Both doubles
are **negated inside `sub_7AE160`** (`fchs` at 0x7AE169 and 0x7AE1E4).

Note: **Best reading**, stated as an inference: this is a **sub-pixel shift** with a
bilinear kernel, not a scale — the scale argument handed to `sub_7AA860` is the
literal `1.0f` (`0x3F800000` at 0x7AE186 / 0x7AE1FD), and the +2-pixel canvas is
exactly the border a unit-support filter needs to carry a fractional offset. That
would make it the mechanism by which a city thumbnail is nudged onto the
fractional isometric lattice (`0xB0DBA4 = +90.51`, `0xB0DBA8 = +18.75`,
`0xB0DBAC = −37.49`, `0xB0DBB0 = +45.25`). I could not prove the doubles are
sub-pixel offsets rather than a scale ratio without decompiling `sub_7AA860`,
which is outside this slice.

**CALLERS** — 1 site: `0x007AE4DC` in `sub_7AE3D0`; `sub_7AE3D0` in turn is called
4× from `sub_7AE510` (0x007AE5B9, 0x007AE5EA, 0x007AE65D, 0x007AE68E).

---

## Open questions handed to the next slices

1. **Who fills `item+0x38`?** Slice 3 proves the vector exists and is destroyed,
   but `sub_7AE510` only fills `+0x44/+0x50/+0x5C`. Look for a fourth
   `lea esi,[reg+0x38]` + `call 0x7AD400` (or a different builder) in slices 4–5.
2. **`sub_7AA860` / `sub_7BFF20` / `sub_7AA110` / `sub_7AABB0`** (slice 2) decide
   whether `sub_7AE160` can *scale* or only *shift*. If `sub_7AA860` takes
   (offset, ratio, …) then the region tiles already have a filtered scaler in the
   binary and the "no resampler" premise behind the 520×320 Init experiment
   should be revisited.
3. **`sub_7AC1A0`** (slice 2) is the bridge from `+0x178/+0x17C` to
   `camera+0x98/+0x9C`; anything that wants to zoom or re-centre the region map
   has to go through it, since `sub_7AC830` reads the camera, not the floats.
4. **Class identity of vtable `0x00AB8CD0`** (ctor `sub_7AAE10`, dtor `sub_7AC5C0`,
   built by `sub_7B1900` at 0x7B1E38; `+0x104` initialised to `300.0f`). It is a
   second `cGZWin`-derived region window with the same 0x258-byte vtable size as
   `cSC4WinRegionScreen`. It is not in the class-name registry via any id used in
   this slice.
5. **The two GZCOM ids that never appear in .data** — `0xC47B747C` (the graphics
   object the scene is bound to) and `0xE9C6262A` (the renderer). Naming them
   needs a live `cIGZCOM::GetClassObject` trace, not the binary.
