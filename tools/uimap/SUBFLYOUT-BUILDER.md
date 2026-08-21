# THE SUB-FLYOUT BUILDER — DECODED

> **Scope.** The shared second-level menu container **`0x8A6E61E0`** and its
> item strip **`0x8A2CAD8B`** — the strip that opens when the player picks a
> tool *inside* a flyout (zone density, road types, rail depots …). This file
> answers which function creates them, and where every number comes from.
> Model for the layout: `tools\research\BUDGET-DETAIL-ANATOMY.md`.
>
> Every claim carries a VA or a byte pattern, read from `SimCity 4.exe`
> 1.1.641.0 (Steam).
>
> Companions: `SUBFLYOUT-ART-VERDICT.md` settles the art-versus-code question,
> and `SUBFLYOUT-LIVE-EVIDENCE.md` holds the live-instrument readings.

---

## 0. THE ONE-LINE ANSWER

**`sub_7EAEB0` (`0x007EAEB0 .. 0x007EB320`, 1136 bytes) is the builder.**
It is the only code in the exe that creates either window, it runs **fresh on
every sub-menu open** (`operator new` at `0x7EB0DD`), and it lays the whole
assembly out from **twelve `push imm8`-class constants of its own**.
The geometry is **CODE-derived, not art-derived** (§6).

That places it squarely in row 3 of `SC4-UI-ENGINE.md` §4.7 —
*"Code-created fresh on every open → patch the BUILDER's constants so children
are created at scaled coordinates"* — the same regime as the budget family,
which is exactly why the flash is in the sub-panels and not in the three main
toolbars.

---

## 1. HOW TO LOCATE IT

```
python -c "import struct;d=open(r'<install>\Apps\SimCity 4.exe','rb').read();
print([hex(i+0x400000) for i in range(len(d)) if d[i:i+4]==struct.pack('<I',0x8A6E61E0)])"
```

A raw file offset in this image maps to its VA by adding `0x400000`. The scan
reports the address of the id operand; the `push` opcode is the byte before it.

| id | occurrences in the whole exe | VA | bytes | what it feeds |
|---|---|---|---|---|
| `0x8A6E61E0` | **1** | `0x007EB11A` | `68 E0 61 6E 8A` | `SetID` (`call [edx+0x100]`) at `0x007EB121` |
| `0x8A2CAD8B` | 2 | `0x007EB1F4` | `68 8B AD 2C 8A` | `SetID` at `0x007EB1FB` |
| | | `0x007E5EB9` | `68 8B AD 2C 8A` | inside `sub_7E5E90` — a **lookup** helper, creates nothing |

Both create sites are in `sub_7EAEB0`, and slot `+0x100` on the window vtable
is `SetID`, so the identification needs no guessing.

These two windows are built through **class methods on an anonymous class**,
not through the `sub_779xxx` label/band/button factories, which is why a census
keyed on those primitives never reaches them. That is the gap this file closes.

---

## 2. THE CAST (all VAs proven by ctor / vtable reads)

| VA | what | proof |
|---|---|---|
| **`sub_7EAEB0`** | **sub-flyout builder** (2nd-level menus) | contains both `SetID`s |
| **`sub_7E7270`** | **first-level flyout builder** (disaster / tool flyout) — the TWIN | the only other caller of the container ctor |
| `sub_79AFF0` | container ctor, `new(0x150)` | sets `[obj]=0xAB6D04`, `[obj+4]=0xAB6AA8` at `0x79B006/0x79B00C` |
| `sub_79B500` | strip ctor, `new(0x140)` | sets `[obj]=0xAB6D28`, `[obj+4]=0xAB6D88` at `0x79B51C/0x79B514` |
| `sub_78F100` | strip **factory** (menu → strip control) | `new(0x140)` + `call 0x79B500` at `0x78F11B` |
| **`sub_79AC60`** | container **`SetLayout(img,a2..a8)`** = vtable `0xAB6D04` **+0x10**, `ret 0x20` | writes `[0xDC],[0xE4],[0xE8],[0xEC],[0xF0],[0xF4],[0xF8],[0xFC],[0x100]` |
| **`sub_79AD00`** | container **`Place(w,h,cx,cy,margT,margB)`** = `0xAB6D04` **+0x14**, `ret 0x18` | the **only** `SetArea` in the family (`call [edx+0xdc]` @`0x79ADC7`) |
| `sub_79B050` | container `GetStripRect(out)` = `0xAB6D04` **+0x18** | copies `obj[0x108..0x114]` |
| **`sub_79A0E0`** | strip **`SetItemMetrics(w,h,spacing)`** = `0xAB6D28` **+0x30** | writes `strip[0xF8/0xFC/0x100]` |
| **`sub_79A620`** | strip **`GetDesiredSize(out,n)`** = `0xAB6D28` **+0x34** | `out=(itemW, (itemH+spacing)*n − spacing)` |
| `sub_79B0E0` | container `Plot` (`0xAB6AA8` slot 88) | draw only — never sets an area |
| `sub_79AE30` | the hit-claim (`0xAB6AA8` slot 121) | `claim = local_x >= W − win[0xE0]` = `obj[0xE4]` |

**Offset note that reconciles this file with `SC4-UI-ENGINE.md` §2.1.** The
object carries two vptrs: the primary at `obj+0` (`0xAB6D04`) and the
`cIGZWin` base at `obj+4` (`0xAB6AA8`). `SetLayout` is called with
`this = obj+0`; `Plot`, `IsPointInMe` and every live dump see `this = obj+4`.
So **`ENGINE`'s `win[0xE0..0xF4]` == this file's `obj[0xE4..0xF8]`** — the same
six fields, shifted by four. Both readings are correct; only one can be used
at a time.

---

## 3. THE LAYOUT ENGINE — every number, in order

### 3.1 What `sub_7EAEB0` does, top to bottom

```
0x7EAEB6  if (this[0x204] == arg1) { vt+0xF0(); return; }   // click the same tool again = CLOSE
0x7EAEEF  strip->SetItemMetrics(44, 44, 5)                  // <-- CONSTANTS 1..3
0x7EAF17  n = strip->GetItemCount();  clamp 1..8
0x7EAF3D  if (view->GetH() <= 600) n = min(n, 6)            // POLICY, not geometry
0x7EAF4E  strip->GetDesiredSize(&sz, n)   -> sz = (44, 49n-5)
0x7EAF60  new(0x1b4) + sub_799DD0                            // the hover/tooltip label object
0x7EB00E  btn   = parentWin->vt+0x88(buttonId)               // arg2, arg3
0x7EB016  cx = btn.GetW()/2 + btn.GetX() + parent.GetX()     // ABSOLUTE button centre
0x7EB061  cy = btn.GetH()/2 + btn.GetY() + parent.GetY()
0x7EB0A2  viewY = this[0x18C]->GetY()
0x7EB0C0  TGI = { 0x856DDBAC, 0x46A006B0, arg5 }  -> load    // background/ring atlas
0x7EB0DD  new(0x150) + sub_79AFF0                            // THE CONTAINER
0x7EB11A  container->SetID(0x8A6E61E0)                       // <-- the id
0x7EB14A  view->AddChild(containerWin)                       // child of the 3D VIEW
0x7EB16E  container->SetLayout(img, 53, 25, 80, 53, 4, 27, 29)   // <-- CONSTANTS 4..10
0x7EB193  container->Place(sz.w, sz.h, cx, cy, 10, viewY-10)     // <-- CONSTANTS 11,12  -> SetArea
0x7EB1D2  container->GetStripRect(&r);  stripWin->SetArea(&r)
0x7EB1F4  stripWin->SetID(0x8A2CAD8B)                        // <-- the id
0x7EB20D  containerWin->AddChild(stripWin)
```

### 3.2 `SetLayout` (`sub_79AC60`) — where each argument lands

| arg | value @ `sub_7EAEB0` | field | meaning |
|---|---|---|---|
| 1 | loaded image | `obj[0xDC]` | atlas; **draw source only** |
| 2 | **53** | `obj[0xE4]` | bar width; also the **hit-claim** width |
| 3 | **25** | `obj[0xE8]` | bar end-cap height **and** the container's vertical padding |
| — | *computed* | `obj[0xEC]` | `img.GetHeight() − 2*[0xE8]` — the tileable middle-segment height |
| 4 | **80** | `obj[0xF0]` | ring sprite width |
| 5 | **53** | `obj[0xF4]` | ring sprite height **and** the minimum content height |
| 6 | **4** | `obj[0xF8]` | ring/bar overlap |
| 7 | **27** | `obj[0xFC]` | x anchor |
| 8 | **29** | `obj[0x100]` | y anchor |

### 3.3 `Place` (`sub_79AD00`) — the closed-form geometry

```
stripW   = itemW                                  = 44
stripH   = (itemH + spacing) * n − spacing        = 49n − 5
contentH = max(stripH, [0xF4]) + 2*[0xE8]         = max(49n−5, 53) + 50

containerW    = [0xF0] − [0xF8] + [0xE4]          = 80 − 4 + 53 = 129     @0x79ADBE
containerLeft = cx − [0xFC]                       = cx − 27               @0x79AD61
containerTop  = ([0xF4]>>1) − (contentH>>1) + cy − [0x100]                @0x79AD70..79AD76
                then, in order:
                  max(., 10)                      (arg5)                  @0x79AD78
                  min(., (viewY−10) − contentH)   (arg6)                  @0x79AD86
                  min(., cy − [0x100] − [0xE8])                           @0x79AD96
                  max(., cy + [0xF4] − contentH + [0xE8] − [0x100])       @0x79ADAE
SetArea(left, top, left+containerW, top+contentH)                         @0x79ADC7

stripLeft = containerW − (([0xE4] + stripW) >> 1) − 1  = 129 − 48 − 1 = 80  @0x79ADD1..79ADEE
stripTop  = (contentH − stripH) >> 1                                        @0x79ADFC
stripRight/Bottom = +stripW / +stripH
```

### 3.4 The model reproduces seven independently measured live numbers

| prediction | measured, elsewhere in this repo |
|---|---|
| container **129** wide → 258 at 2x | `MAYOR-MODE.md`: *"destIsSubContainer = EXACT width 258"* |
| heights `max(49n−5,53)+50` = 103/143/192/241/290/339/388/437 → **206/286/384/482/580/678/776/874** at 2x | `MAYOR-MODE.md` lists exactly `258 x 206/286/384/482/580/678/776/874` |
| strip **44 x 191** for n=4 → **88x382** at 2x, inside a 258x482 container | `MAYOR-MODE.md` / `UiSpike.cpp` SUBHOOK: `strip 0x8A2CAD8B 88x382`, container `258x482` |
| ring sprite exactly **80** wide | `MAYOR-MODE.md`: *"this sprite is EXACTLY 80 wide so it missed by one pixel"* |
| native placement `btn + (20, −86)` for a 4-item menu with a 2x (94x74) button: `left = btnX+47−27 = btnX+20`; `top = btnY+37−29+ (53>>1) − (241>>1) = btnY−86` | `MAYOR-MODE.md`: *"btn(158,560)+(20,-86) = live (178,474)"* |
| **twin**: first-level container `94 − 6 + 53` = **141** wide, `289+50` = **339** tall at its 6-row cap | `SC4-UI-ENGINE.md` §2.1: `srcBuf [0xDC] = 141x339` |
| **twin** fields `53, 25, artH−50, 94, 62, 6` | §2.1's live DOBS dump: `53, 25, 12, 94, 62, 6` |

Nothing is fitted. Every formula comes out of the disassembly and reproduces
numbers that were recorded independently of it.

Corollaries worth knowing:
- **258x206 is a ONE-ITEM menu.** `n=1 → stripH = 44 < 53`, so the
  `max(stripH,[0xF4])` floor fires and the height stops at 103.
- **Height is fully covered by the item metrics.** `contentH` scales exactly
  by `f` if `itemH`, `spacing`, `[0xF4]` and `[0xE8]` are all scaled — there is
  no separate height constant to miss.
- **The 6-row cap explains the 678.** A 6-row menu is `339` tall — the same
  number as the first-level flyout's buffer, for the same reason.

---

## 4. THE CONSTANT TABLE

Encodings and original bytes, re-read from the exe at all 30 sites. In the
tier columns, `✗` marks a value that no longer fits the instruction's signed
1-byte immediate field (§5).

### 4.1 `sub_7EAEB0` — the SUB-FLYOUT

| VA | bytes | enc | role | stock | 1.5x | 2x | 3x | twin |
|---|---|---|---|---|---|---|---|---|
| `0x7EAEF3` | `6a 2c` | push imm8 | itemW → `strip[0xF8]`, strip window width | 44 | 66 | 88 | **132 ✗** | `0x7E72A8` |
| `0x7EAEF1` | `6a 2c` | push imm8 | itemH → `strip[0xFC]` | 44 | 66 | 88 | **132 ✗** | `0x7E72A6` |
| `0x7EAEEF` | `6a 05` | push imm8 | spacing → `strip[0x100]` | 5 | 8 | 10 | 15 | `0x7E72A4` |
| `0x7EB169` | `6a 35` | push imm8 | `[0xE4]` bar width / hit-claim | 53 | 80 | 106 | **159 ✗** | `0x7E74A9` |
| `0x7EB167` | `6a 19` | push imm8 | `[0xE8]` cap height / v-padding | 25 | 38 | 50 | 75 | `0x7E74A7` |
| `0x7EB165` | `6a 50` | push imm8 | `[0xF0]` ring width | 80 | 120 | **160 ✗** | **240 ✗** | `0x7E74A5` |
| `0x7EB163` | `6a 35` | push imm8 | `[0xF4]` ring height / min content H | 53 | 80 | 106 | **159 ✗** | `0x7E74A3` |
| `0x7EB161` | `6a 04` | push imm8 | `[0xF8]` ring/bar overlap | 4 | 6 | 8 | 12 | `0x7E74A1` |
| `0x7EB15F` | `6a 1b` | push imm8 | `[0xFC]` x anchor | 27 | 41 | 54 | 81 | `0x7E749F` |
| `0x7EB15D` | `6a 1d` | push imm8 | `[0x100]` y anchor | 29 | 44 | 58 | 87 | `0x7E749D` |
| `0x7EB183` | `6a 0a` | push imm8 | top screen margin | 10 | 15 | 20 | 30 | `0x7E74C3` |
| `0x7EB17B` | `83 c0 f6` | add r32,imm8 | bottom screen margin | −10 | −15 | −20 | −30 | `0x7E74BB` |

### 4.2 `sub_7E7270` — the FIRST-LEVEL twin (read §7 before patching)

| VA | bytes | enc | role | stock | 1.5x | 2x | 3x |
|---|---|---|---|---|---|---|---|
| `0x7E72A8` / `0x7E72A6` / `0x7E72A4` | `6a 2c` / `6a 2c` / `6a 05` | push imm8 | itemW / itemH / spacing | 44 / 44 / 5 | 66/66/8 | 88/88/10 | **132✗/132✗**/15 |
| `0x7E74A9` | `6a 35` | push imm8 | `[0xE4]` bar width | 53 | 80 | 106 | **159 ✗** |
| `0x7E74A7` | `6a 19` | push imm8 | `[0xE8]` cap height | 25 | 38 | 50 | 75 |
| `0x7E74A5` | `6a 5e` | push imm8 | `[0xF0]` ring width | 94 | **141 ✗** | **188 ✗** | **282 ✗** |
| `0x7E74A3` | `6a 3e` | push imm8 | `[0xF4]` ring height | 62 | 93 | 124 | **186 ✗** |
| `0x7E74A1` | `6a 06` | push imm8 | `[0xF8]` overlap | 6 | 9 | 12 | 18 |
| `0x7E749F` | `6a 28` | push imm8 | `[0xFC]` x anchor | 40 | 60 | 80 | 120 |
| `0x7E749D` | `6a 22` | push imm8 | `[0x100]` y anchor | 34 | 51 | 68 | 102 |
| `0x7E74C3` | `6a 0a` | push imm8 | top screen margin | 10 | 15 | 20 | 30 |
| `0x7E74BB` | `83 c0 f6` | add r32,imm8 | bottom screen margin | −10 | −15 | −20 | −30 |

### 4.3 NOT geometry — documented so nobody "completes the set"

| VA | bytes | insn | stock | why it must stay |
|---|---|---|---|---|
| `0x7EAF3D` | `3d 58 02 00 00` | `cmp eax,600` | 600 | **real screen pixels.** `view.GetH() <= 600` drops the row cap 8→6. Doubling it would cut rows on a 1600px screen. |
| `0x7EAF28` / `0x7EAF44` / `0x7EAF1C` | `83 fb 08` / `83 fb 06` / `83 fb 01` | `cmp ebx,…` | 8 / 6 / 1 | row-count caps |
| `0x7E72DF` / `0x7E72D3` | `83 f8 06` / `83 f8 01` | `cmp eax,…` | 6 / 1 | first-level flyouts are always capped at 6 rows |
| `0x7EAF60` / `0x7EB0DD` | `68 b4 01 …` / `68 50 01 …` | `push 0x1b4` / `push 0x150` | 436 / 336 | `operator new` sizes. Touching either corrupts the heap. |
| `0x7EAFC9` / `0x7EAFCB` | `6a 05` / `6a 08` | `push 5` / `push 8` | 5 / 8 | **font-style selector.** `[this+0x3d8]->vt+0x14(8,5)` and the result goes to the hover label's `vt+0x10`, immediately beside a colour fetch (`vt+0x50` → `vt+0x4c`) — a style/colour pair, not a rect. Twin at `0x7E733D`/`0x7E733F`. **They sit 0x22 bytes from the item-metrics pushes and are byte-identical to them; do not sweep the region.** |

---

## 5. VALUES THAT CANNOT BE PATCHED (the imm8 ceiling)

`push imm8` and `add r32,imm8` are 2- and 3-byte forms with a **signed 1-byte**
field: the value must land in −128..127. There is no padding anywhere in
either push run, so a site cannot be widened in place.

| tier | sites over the ceiling | which |
|---|---|---|
| **1.5x** | 1 | `0x7E74A5` ringW 94→141 (twin only) |
| **2x** | **2** | `0x7EB165` ringW 80→**160**, `0x7E74A5` ringW 94→**188** |
| **3x** | 10 | both ringW, both `[0xE4]`, both `[0xF4]`, all four itemW/itemH |

**At 2x the sub-flyout has exactly ONE unpatchable constant: `[0xF0]`, the ring
width, at `0x7EB165`.** And it is not optional — it is a *width* term:
`containerW = [0xF0] − [0xF8] + [0xE4]`. Leaving it at 80 with the other two
doubled gives `80 − 8 + 106 = 178`, not 258.

### 5.1 The cure — one vtable thunk, not a pin

`SetLayout` is a **fixed-arity `__thiscall`** (`ret 0x20`, 8 stack args) reached
through **one** vtable slot, `0xAB6D04 + 0x10`. A thunk there:

- receives all seven numeric arguments **before** any of them is stored,
- can scale each one by any factor with no encoding limit,
- fires for **both** builders, so one hook covers the whole family, and
- distinguishes them by **return address** (`0x007EB171` = sub-flyout,
  `0x007E74B1` = first-level), which is also the proof line of §8.

This beats a runtime pin on all three counts that `METHOD.md` §4.1 weighs: it
runs at BIRTH (no sweep race, no flash), its identification does not depend on
the state it corrects (it is the call itself), and it stores no window pointer
that can go stale. Where a thunk is unavailable, the fallback is
`push 0x50 → push 0x7F` (127) plus a **+33 width correction** applied in the
`Place` thunk — two mechanisms where one does the job.

Do **not** absorb the shortfall into `[0xE4]`: `[0xE4]` is **dual-use** — it is
also the hit-claim width (`0x79AE30`) and the bar's flush-right draw width, so
a correction there moves the click target and the bar art along with it.

---

## 6. IS THE ITEM GEOMETRY CODE-DERIVED? — YES, DECISIVELY

The question is worth asking: the budget band family sizes its dialog from the
**sum of art heights**, and if this family did the same there would be nothing
to patch. **It does not.**

**Every number that reaches a `SetArea` is a code immediate.** Traced end to
end:

- `containerW` ← `[0xF0], [0xF8], [0xE4]` — three `push imm8`s, `0x79ADBE`.
- `contentH` ← `itemH`, `spacing`, `n`, `[0xF4]`, `[0xE8]` — four `push imm8`s
  plus a runtime item count, `0x79AD47`.
- `stripW`/`stripH` ← `GetDesiredSize` (`0x79A620`), which reads **only**
  `strip[0xF8]/[0xFC]/[0x100]` — the three values pushed at `0x7EAEEF..0x7EAEF3`.
  The art is never consulted.
- `left`/`top` ← `[0xFC]`, `[0x100]`, the two margins, and the live button
  centre.

**The art contributes exactly one number, and it never reaches a `SetArea`.**
`SetLayout` computes `obj[0xEC] = img.GetHeight() − 2*[0xE8]` at `0x79ACAB`
(`vt+0x28` on the image is `GetHeight`: `Plot` compares it against
`win.bottom − win.top` at `0x79B13A..0x79B143`). `[0xEC]` is the height of the
**tileable middle segment of the bar** and is consumed only by `Plot`
(`0x79B1E7`). It sizes nothing.

Cross-check that closes it: the shipped atlas `T-856DDBAC I-14215ED0..ED5` is
**292x53** (`MAYOR-MODE.md`, measured from the DAT). `53 − 2*25 = 3` — a 53-tall
bar with two 25px caps and a 3px tileable middle. The first-level flyout's own
atlas gives `62 − 50 = 12`, which is **exactly** the `[0xEC]`=12 measured live
in `ENGINE` §2.1. Two different atlases, two matching predictions, and neither
number appears in any window rect.

> **One real coupling, and it bites.** `[0xEC] = artH − 2*[0xE8]`. Doubling
> `[0xE8]` to 50 against a **1x** (53-tall) atlas yields `[0xEC] = −47` and the
> bar draw goes negative, so the `[0xE8]` patch is valid only while the scaled
> atlas is loaded. The exe requests the atlas from group **`0x46A006B0`**
> (`0x7EB0C8`); the 2x art packages supply `I-14215ED0..ED5` plus `EDD` under
> that group and under `0x1ABE787D`, so both lookups resolve to scaled art.

---

## 7. THE TWIN IS ALREADY SCALED BY OTHER MEANS — DO NOT PATCH IT BLIND

`sub_7E7270` builds the **first-level** flyout, from the **same two classes** —
which is why the `SVT` vtable probe reads byte-identical vtables for the two
windows, and why every disaster-flyout fix applies verbatim to the sub-flyout.
That window is already handled after birth: `gForceRecreate`,
`gStripFieldScale`, `gBarDX`, `ClaimScale`, the god-flyout
pre-scale-while-hidden path and `kMayorFlyoutDock` all act on it.

Patching its builder **as well** double-scales it. Born-2x and resize-to-2x are
mutually exclusive by construction, so a build that patches the `sub_7EAEB0`
block drops `gStripFieldScale` and the container resize for `0x8A6E61E0` in the
same build. The twin keeps its post-birth treatment.

`sub_7E7270` is called from **`0x7F4D2C` in `sub_7F4690`** — the same function
that opens one of the sub-menus (`0x7F4EE1`). The two levels share an owner, so
a region-wide byte sweep hits both. Patch by VA, never by pattern.

---

## 8. THE ONE LOG LINE THAT PROVES IT

A single line from a live sub-menu open shows that this builder is the one that
actually runs. **Hook `0xAB6D04` slot `+0x10` (`SetLayout`, `sub_79AC60`) and
log the caller's return address with the seven arguments:**

```
SUBLAY ret=0x007EB171 e4=53 e8=25 f0=80 f4=53 f8=4 fc=27 100=29 img=<w>x<h>
```

Why this one line and no other:

- **`ret=0x007EB171` is decisive by construction.** It is the instruction after
  `call [eax+0x10]` at `0x7EB16E`. There are exactly **two** call sites of this
  slot in the entire exe; the other returns to `0x007E74B1`. One field
  therefore names the builder *and* rules out the twin — no correlation, no
  timing argument, no inference.
- **The seven values are the builder's fingerprint.** `53/25/80/53/4/27/29` can
  only come from the push run at `0x7EB15D..0x7EB169`; the twin's run is
  `53/25/94/62/6/40/34`. If the numbers and the return address disagree, the
  exe is not the build this file was read from — which is itself the answer.
- **It arrives before the flash.** `SetLayout` runs *before* the `SetArea` in
  `Place`, so the line is emitted at birth, not after the sweep — it proves the
  builder ran *and* timestamps the moment the 1x geometry was committed.

A weaker but zero-code alternative: the **first** `DPROBE`/`SUBSKIP` sighting of
`0x8A6E61E0` in a session, before the sweep touches it, reads **width 129**
with `left = spawnButtonAbsCentreX − 27`. `129` exists nowhere in the exe as a
literal — it only ever comes into being as `80 − 4 + 53` at `0x79ADBE`.

---

## 9. DEAD ENDS AND TRAPS (do not re-walk)

- **`sub_7E5E90`** (`0x7E5EB9` pushes `0x8A2CAD8B`) is a *lookup*, not a
  builder. 176 bytes, creates nothing.
- **`sub_799DD0`** (`new(0x1b4)`, called at `0x7EAF7F`) is **not** the
  container — different vtables (`0xAB69D0`/`0xAB6770`). It is the hover/tooltip
  label object, released at `0x7EB312`. It has 9 callers across the exe; do not
  chase them.
- **`obj[0xDC]` is not the paint buffer.** `SetLayout` puts the *atlas* there;
  `Plot` uses `obj[0xE0]` (`win[0xDC]`) as the render buffer and reallocates it
  when the window rect changes (`0x79B117`). Reading `ENGINE`'s `[0xDC]` as this
  file's `[0xDC]` is a four-byte trap — see §2.
- **`obj[0xE0]` is never written after the ctor zeroes it** (scan of
  `0x799D00..0x79C000`, no `mov dword [reg+0xE0]`). Plot's multi-segment step
  therefore collapses. Not a constant; nothing to patch.
- **`0x7EAFC9`/`0x7EAFCB` `push 5` / `push 8`** are font-style ids that sit 0x22
  bytes from the item-metrics pushes and look exactly like geometry. §4.3.
- **No `.UI` script defines either window** — 330 scripts, zero hits — and the
  same result arrives from the other direction: the ids exist only as
  `push imm32` operands feeding `SetID`.
- **Searching for the literal 258 / `0x102` finds nothing, and one false
  friend.** The width is *computed*, never stored, so `0x102` does not appear
  anywhere in this path. What a decimal-"258" scan **does** hit is
  `cmp eax,0x258` at `0x7EAF3D` — that is **600**, the small-screen row gate
  (§4.3). Two different numbers wearing the same digits. The window **ids** are
  the only usable search key; `129` (the true native width) is likewise never a
  literal.
