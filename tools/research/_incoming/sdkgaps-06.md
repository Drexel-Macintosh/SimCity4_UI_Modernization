# TARGET: PRIMARY: `tools\research\SC4-UI-ENGINE.md` — insert as a new numbered section **§4A. `GZWinBMP`, complete** (immediately after §4 "The four art-binding paths", before §5), because it is the reference for the single most load-bearing widget and it depends on §4's vocabulary.

SECONDARY (small patches, all included in the draft below as marked blocks):
- `tools\research\SC4-UI-ENGINE.md` §3.3 — replace the `edgeimage` bullet (pattern 4) and add the clamp rule.
- `tools\research\SC4-UI-ENGINE.md` §8.5 (VA index) — replace the single `0x00ADF6A0 / 0x9BC325` row with the expanded rows.
- `tools\research\SC4-UI-ENGINE.md` §9 — rewrite contradiction #8, extend #11, add new #14 (vtable slot-name drift).
- `tools\research\UI-ART-BINDING.md` §3 — replace the `edgeimage = yes | no` bullet (it is wrong in mechanism).
- `_tests\REGRESSION.md` "The BMPX hook (task #47)" — one corrective paragraph (the hooked slot is GZPaint, not Plot; and the BMPRECT field write bypasses the engine's clamp).

## SUMMARY
Full offline decode of GZWinBMP from the shipped exe: all 151 class-vtable slots (13 overrides identified by body), the complete 12-slot `cIGZWinBMP` interface vtable at `0x00ADF66C` (no header for this exists anywhere — gzcom-dll has no cIGZWinBMP.h), the whole object field map, the six flag bits and the exact `.UI` attribute that sets each (deserializer `0x95002C`, tokens `alpha`=0xB00 / `transparentbkg`=0xB01 / `edgeimage`=0xB02 / `notify`=0xF003 / `image`=0xF016 / `imagerect`=0xF018), the two-pass creation order from the dispatcher at `0x957BE7–0x957C77`, both draw paths written as closed-form formulas, and the 9-slice helper `0x8D8800` decoded blit-by-blit (4 corners via ctx slot 38, 4 edges + centre via ctx slot 39, each edge guarded by a "is there room" test, the centre gated by the caller's flag). Five results are genuinely new and three CONTRADICT current doc text: (1) the hooked slot 88 is **GZPaint**, not Plot — real Plot is slot 89 `0x99BA07` and merely calls PlotComposite/PlotPresent; (2) the dst origin is `[this+0x24]` = **areaToDrawTo** (buffer space), not the window's `area=`; (3) `image={g,i}` makes the deserializer call **`SetSize(imgW,imgH)` on the window** — that is the mechanism behind "419 controls have area == PNG dims" and behind "style-PNG widgets born at the ART's size"; (4) `SetImage` and `Init` both **reset the imagerect to `(0,0,min(winW,imgW),min(winH,imgH))`**, which is the exact law behind task #47's "1x content pinned top-left"; (5) in edge mode only `r` and `b` are divided by 3 — `l`/`t` are left alone, so the cell is `(r/3−l, b/3−t)` and `imagerect` is **never** an inset, contradicting `UI-ART-BINDING.md` §3. An offline PIL recomposition of the real chrome PNGs under both readings is included as the decisive test and leaves one honest OPEN question.

## CONTRADICTIONS
- `UI-ART-BINDING.md` §3 (`edgeimage = yes | no` bullet) — "imagerect=(l,t,r,b) gives the stretchable center rect" and "{1abe787d,14416240} is 180x180 and is drawn with imagerect=(12,22,180,180) ... fixed 12/22px borders, stretched middle" is WRONG IN MECHANISM. `GZPaint` at 0x9BC411-0x9BC425 divides only `src.r` and `src.b` by 3 and leaves `src.l`/`src.t` untouched; the 9-slice cell is therefore (r/3 - l, b/3 - t) = 48x38 for that exact example, not 12x22, and the grid starts at (l,t) so the sheet's outer l/t pixels are never sampled. There is no inset/border semantics anywhere in the class.
- `SC4-UI-ENGINE.md` §8.5 VA index, `MAYOR-MODE.md` ("SOLVED 2026-07-29: slot 87 GZPaint = 0x0099BE4C (base), slot 88 Plot = 0x009BC325 (OVERRIDE)"), `_tests\REGRESSION.md` task #47, and the BMPX comment block in `src\UiSpike.cpp` — all name slot 88 `Plot`. MEASURED: slot 87 is `GetNotificationTarget` (0x99BE4C = `mov eax,[ecx+0x4C]; ret`, a getter, not a paint), slot 88 is **GZPaint**, and the real `Plot` is slot 89 = 0x99BA07 whose body calls slot 123 PlotComposite then slot 124 PlotPresent. The hook targets the right slot; only the name is wrong.
- `SC4-UI-ENGINE.md` widget catalogue row for GZWinBMP and `MAYOR-MODE.md` — "the DRAW is dst = origin + srcWxH" where `origin` is read as the window's `area=` left/top. MEASURED: the origin is `[this+0x24]` = areaToDrawTo, written by slot 97 (0x99CF6A) as the window's rect in the *nearest buffer-owning ancestor's* coordinate space, or `(0,0,w,h)` when the window owns a private buffer (`[this+0x64] != 0`). Proof that +0x24 is areaToDrawTo: slot 99 = 0x477810 = `lea eax,[ecx+0x24]; ret`.
- `SC4-UI-ENGINE.md` widget catalogue row — "a 2x source rect over a 1x bitmap draws only the corner that exists". MEASURED: `SetImageRect` (0x9BC103) CLAMPS `r` and `b` down to the image's real dimensions (and `l`,`t` up to >= 0) whenever an image is bound. A doubled `(0,0,w,h)`-form crop is clamped back to the whole 1x image and draws the WHOLE image at 1x; a doubled crop with non-zero l,t clamps into an INVERTED rect (negative height) instead. Neither is "the corner that exists". Our own BMPRECT field write to +0xE8 bypasses this clamp entirely.
- `vendor\gzcom-dll\gzcom-dll\include\cIGZWin.h` — its declaration order is off by one against the shipped vtable for slots 58..138 (real = header + 1). Verified at nine independent anchors from function bodies (real 60 WindowToScreen, 61 WindowToWindow, 63 GetID, 67 GetFlag, 91 InvalidateSelf, 93 GetDrawContext, 99 GetAreaToDrawTo, 133 1-arg stub shared with 129, 144 5-arg SendMsg). Any doc or code that names a slot in that band from the header is mislabelled; index by number.
- `SC4-UI-ENGINE.md` §3.1 attribute frequency table lists `edgeimage` 844 but never mentions `transparentbkg` (845 occurrences, 457 yes / 388 no) or `notify` (2,578) — both are live, parsed attributes, and `transparentbkg` is the one that decides whether a GZWinBMP fills its background at all (flag 0x02, tested first thing in GZPaint). Conversely `alpha=` and `imagetype=` are registered tokens with ZERO corpus occurrences and, for `alpha`, zero consumers in the draw path.

## OPEN
- THE ONE REAL OPEN QUESTION — does a declared `imagerect` actually reach the draw for `edgeimage=yes` controls? The code says yes (deserializer pass 2 at 0x9501EA sets flag 0x10 whenever `imagerect=` is present, and GZPaint selects `+0xE8` on that flag). But an offline PIL recomposition of the REAL art under the decoded algorithm disagrees with what the game visibly renders: {1abe787d,144161e4} 78x78 with imagerect=(12,12,78,78) gives a 14x14 cell sampled from x,y in [12,26) - which is pure flat interior (the frame's border decoration lives in x in [0,6) and [72,78)) - and composes to a FLAT, fully-opaque, corner-less box. Using the image's natural rect instead (cell 26x26 at (0,0)) composes to the correct rounded, decorated SC4 chrome. Same result for {46a006b0,14416240} 180x180. Supporting evidence for the code reading: our own BMPRECT fix gates on GetFlag(0x10) and only acts when it is true, and doubling that live rect fixed the Save-box tearing (v2.25.10) - so flag 0x10 IS set live on edge BMPs and the stored rect IS in force. SETTLES WITH ONE PROBE, no new instrument: extend the existing BMPRECT walker to log `[win+0xF8] & 0x18` plus `[win+0xE8..0xF4]` and the window's live W/H for one edge BMP (Save dialog body {1abe787d,144161ee}, imagerect=(22,35,180,180)) and compare the composed corners against a stock screenshot. Possible third answer: those 56 BMPs really are the flat interior panels and the decorated frame the player sees is a different window in the stack.
- Does draw-context slot 39 (+0x9C) stretch or tile? It takes two extra zeroed arguments beyond (img, src, dst) and carries all four edges plus the centre of every 9-slice. `blttype = tiled` is the second-most common value in the corpus (254 of 540), which makes "tile with a (0,0) phase" the live hypothesis. The draw-context class was never disassembled - positive control: both slots were located and their argument counts read directly at the call sites (0x8D8928 three-arg, 0x8D896A five-arg), so this is an unread implementation, not a missing observation. Settles by hooking slot 39 the same way BMPX hooks 38 and logging src/dst for one edge window.
- Flag 0x20 (source rect from +0xE8 AND destination offset by (src.l, src.t)) has no setter anywhere. Positive control for the null: the same `push imm8` near `call [reg+0x2C]` scan over all of .text finds the three known GZWinBMP flag setters (0x9500EE push 2, 0x950116 push 8, 0x95020E push 0x10) and many 1/2/4 sites in other classes - it can see the shape - but zero `push 0x20`. Residual escape route: a mask computed into a register. If it really is dead, then the "pixel-registered collage" pattern (SC4-UI-ENGINE §3.3 pattern 3, imagerect l,t == the control's own area l,t) is NOT engine-supported registration - it is authors hand-matching numbers, and it would break differently under 2x than the doc assumes.
- Which draw-context class is at [win+0x6C]? gzcom-dll has cIGZBuffer.h / cIGZGraphicSystem.h but no draw-context header. Identifying it would name slots 10/11/21/35/38/39 properly and would also finish the gauge/dial story in §4.5 (those are code-painted into their own buffers through what is very likely the same interface).
- What is cIGZWin flag 0x4000? `Init` (slot 4) short-circuits on GetFlag(0x4000) (0x99BC31), so it is an "already initialised" latch, but it is absent from the tWinFlag enum in cIGZWin.h. Relevant because it decides whether a re-created GZWinBMP re-derives its imagerect from its (already-scaled) window size or keeps the old one - directly load-bearing for the born-correct architecture.
- The three GZWinBMP mouse message ids (0x68915615, 0x28916985, 0xC89155E3) and the two keyboard ones (types 5 and 6) are sent to [this+0x4C]. Mapping which is down/up/move would let a clickable BMP be driven or intercepted the way the flyout hit-test playbook drives cGZWin menus. Cheap to settle: the neighbouring inherited stubs at slots 135/137 are the shared 3-arg stub and 139 is the 4-arg stub, which brackets the group; one live log of the id order on a click would finish it.

---

═══════════════════════════════════════════════════════════════════════
BLOCK 1 — NEW SECTION for `tools\research\SC4-UI-ENGINE.md`
Insert as **§4A** (after §4.6, before §5). Renumber nothing else.
═══════════════════════════════════════════════════════════════════════

## 4A. `GZWinBMP`, complete

Everything below is read out of `SimCity 4.exe` on disk (7,876,608 bytes,
ImageBase `0x400000`, file offset = VA − `0x400000`) unless a line says
otherwise. This section exists so that a reader can predict any GZWinBMP's
on-screen result from its art size, its `imagerect` and its window size
**without running the game**. Where a claim could not be settled offline it is
marked `[OPEN]` with the one experiment that settles it — do not quietly
upgrade those.

### 4A.1 Identity

| Thing | Value |
|---|---|
| script class name | `GZWinBMP`, clsid **`0x82FE68C4`** |
| interface name | `IGZWinBMP`, iid **`0xC12CEA13`** |
| class vtable | **`0x00ADF6A0`**, **151** code pointers then a `0` terminator |
| interface vtable (sub-object) | **`0x00ADF66C`**, **12** slots |
| interface base vtable | `0x00ADF63C`, 24 slots — the first 12 are all the purecall stub `0x5D4A10`; `0x00ADF63C[12..23] == 0x00ADF66C[0..11]` |
| constructor | `0x9BC4BA` |
| destructor / scalar-deleting dtor | `0x9BC2FA` / slot 148 `0x9BC511` |
| name + iid registration | `0x953056` (registers `"GZWinBMP"`→`0x82FE68C4`, `"IGZWinBMP"`→`0xC12CEA13`, and the three own attribute tokens) |

> EVIDENCE — vtable slot count: file offset `0x6DF6A0`, 151 consecutive
> pointers inside `.text` (`0x407000..0xA7FA2D`), slot 151 = `0x00000000`.
> Matches `UiSpike.cpp`'s `kBmpVtSlots = 151`.
> EVIDENCE — clsid/iid: `0x95306B push 0xAD5CE0 ("GZWinBMP")` beside
> `0x953066 push 0x82FE68C4`; `0x9530A6 push 0xAD5CD4 ("IGZWinBMP")` beside
> `0x9530A0 mov edi, 0xC12CEA13`.
> EVIDENCE — ctor: `0x9BC4CE mov [esi+0xD8], 0xADF66C` / `0x9BC4DC mov [esi],
> 0xADF6A0`.

### 4A.2 The object

The `cIGZWinBMP` interface is an **embedded sub-object at `this+0xD8`**, not a
separate allocation. `QueryInterface` (slot 0, `0x9BC06A`) answers exactly one
iid and returns `this+0xD8`; every interface method converts back with
`−0xD8`.

| Offset | Size | Meaning | Proof |
|---|---|---|---|
| `+0x10` | 4 | window ID | slot 63 `0x99BE66` = `mov eax,[ecx+0x10]; ret` |
| `+0x14..+0x20` | 16 | **absolute** area (l,t,r,b) | slot 50 `0x99BCE8` = `lea eax,[ecx+0x14]` |
| **`+0x24..+0x30`** | 16 | **areaToDrawTo** — the window's rect in the *target buffer's* coordinates | slot 99 `0x477810` = `lea eax,[ecx+0x24]; ret`; written by slot 97 `0x99CF6A` |
| `+0x48` | 4 | window-proc / message target | `DoMessage` `0x9BC201` |
| `+0x4C` | 4 | notification target | slot 87 `0x99BE4C` = `mov eax,[ecx+0x4C]` |
| `+0x64` | 4 | private buffer (non-null ⇒ own coordinate space) | `0x99CF76 cmp [ebx+0x64],0` |
| `+0x68` | 4 | buffer to draw to | slot 94 `0x99BEFD` |
| **`+0x6C`** | 4 | **draw context** | slot 93 `0x99BEF9` = `mov eax,[ecx+0x6C]` |
| `+0x70` | 1 | dirty flag | slot 91 `0x99BECC` = `mov byte [ecx+0x70],1` |
| `+0xA8..+0xB4` | 16 | **own** area (l,t,r,b), parent-relative | slot 41 `0x99C81B` = `[ecx+0xB0] − [ecx+0xA8]` |
| `+0xC8` | 4 | winflags | slot 67 `0x99BDBB` |
| **`+0xD8`** | 4 | `cIGZWinBMP` sub-object vtable ptr | ctor |
| **`+0xDC`** | 4 | bound image (`cIGZBuffer*`), AddRef'd | released by `Shutdown` slot 5 `0x9BC097` |
| `+0xE0` | 1 | alpha **enabled** | ctor writes 0 |
| `+0xE4` | 4 | alpha **value** (float) | ctor writes `0x3F000000` = 0.5f |
| **`+0xE8..+0xF4`** | 16 | **imagerect** (l,t,r,b) | `0x9BC15F` reads it out |
| **`+0xF8`** | 4 | **flag word** | ctor writes `0x12` |

⛔ **G1 — the dst origin is `+0x24`, not `area=`.** Both draw paths anchor on
`[this+0x24]` (areaToDrawTo), which slot 97 (`0x99CF6A`) computes by walking
**up the parent chain accumulating each ancestor's `GetL`/`GetT` until it
reaches an ancestor that owns a private buffer**; a window that owns a private
buffer itself gets `(0,0,w,h)` instead. So "the window's top-left" in every
formula below means *its top-left in the target buffer's space*.
> EVIDENCE — `0x99CF90..0x99CF9B` writes `(0,0,w,h)` into `+0x24` when
> `[ebx+0x64] != 0`; `0x99CFE5/0x99CFF1` call `vt[44] GetT` / `vt[43] GetL` on
> each ancestor and add them into the running rect; `0x99CFC4` stops at the
> first ancestor whose `GetPrivateBuffer` (slot 101) is non-null.
> CORRECTS: `UiSpike.cpp`'s BMPX comment ("dst = {areaL, areaT, …}") and
> `_tests\REGRESSION.md`'s "at the window origin" — right answer, wrong field.

### 4A.3 The flag word (`+0xF8`) and the attribute that sets each bit

Tested through the sub-object's `GetFlag` (interface slot 10, `0x9BC171` =
`(flags & mask) != 0`), never read directly by the draw code.

| Bit | Set by | Effect | Proof |
|---|---|---|---|
| `0x01` | `notify=` (token `0xF003`) | `DoMessage` forwards messages to `[this+0x48]`, adding `GetL`/`GetT` for message types 7..0xE | handler `0x9500C6 push 1; call [eax+0x2C]`; consumer `0x9BC1CC` |
| `0x02` | `transparentbkg=` (token `0xB01`) | **skips the background fill** | handler `0x9500EE push 2`; consumer `0x9BC32E test byte [ebx+0xF8],2 … jne` |
| `0x04` | — (never set by any script attribute) | `IsPointInWindowScreenCoordinates` (slot 62 override `0x9BC251`) returns **false** ⇒ click-through | `0x9BC25C push 4; call [eax+0x28]` |
| `0x08` | `edgeimage=` (token `0xB02`) | selects the **9-slice** draw path | handler `0x950116 push 8`; consumer `0x9BC3AD push 8` |
| `0x10` | `imagerect=` present (token `0xF018`) — and explicitly **cleared** when absent | source rect comes from `+0xE8` instead of the image's natural rect | handler `0x95020E push 0x10` with `1` at `0x95020C` / `0` at `0x950215` |
| `0x20` | **nothing in the image** | same source selection as `0x10`, **plus** the dst is shifted by `(src.l, src.t)` | consumer `0x9BC37E` and `0x9BC3D9` |

Ctor default = `0x12` = `transparentbkg` **on** + `imagerect` **valid**.

> NULL, with its positive control — a scan of the whole `.text` for
> `push imm8` within 18 bytes of `call [reg+0x2C]` (the interface's `SetFlag`
> slot) finds the three known GZWinBMP setters (`0x9500EE` = 2, `0x950116` = 8,
> `0x95020E` = 0x10) and dozens of `1`/`2`/`4` sites elsewhere, but **zero**
> `push 0x20` sites. The scan can see the shape; it does not see bit `0x20`.
> Residual: a computed mask in a register would evade it. **Treat flag `0x20`
> as unreachable from data and unreached by any obvious code path.**

⛔ **G2 — `alpha=` and `imagetype=` are dead in practice.** `alpha=` (token
`0xB00`) parses, clamps to 0..255, scales by a constant at `0xA90BBC` and
stores `(true, f)` into `+0xE0/+0xE4` — and **nothing in `GZPaint` or in the
9-slice helper reads either field**. Corpus count of `alpha=`: **0**.
Positive control for that null: the same grep over the same 281-file corpus
returns `transparentbkg` 845, `edgeimage` 844, `imagerect` 839, `blttype` 540.
`imagetype=` (`0xF017`): also **0**.

### 4A.4 The complete `cIGZWinBMP` interface vtable (`0x00ADF66C`)

There is **no `cIGZWinBMP.h` in gzcom-dll** — this table is the only reference.

| Slot | `+off` | VA | What it does |
|---|---|---|---|
| 0 | `+0x00` | `0x9BC31A` | `QueryInterface` — `sub ecx,0xD8; jmp 0x9BC06A` |
| 1 | `+0x04` | `0x7BE710` | `AddRef` (`−0xD8`, tail-calls the window's) |
| 2 | `+0x08` | `0x7BE720` | `Release` |
| 3 | `+0x0C` | `0x95BA6F` | **`GetWindow()`** — `lea eax,[ecx−0xD8]; ret` |
| 4 | `+0x10` | `0x9BC57E` | **`SetImage(cIGZBuffer*)`** — see G6 |
| 5 | `+0x14` | `0x9BC0BD` | `GetImage`/QI-forward to the bound image |
| 6 | `+0x18` | `0x9BC0CF` | `SetAlpha(bool, float)` → `+0xE0`/`+0xE4`, then invalidate |
| 7 | `+0x1C` | `0x9BC0EE` | `GetAlpha(bool*, float*)` |
| 8 | `+0x20` | `0x9BC103` | **`SetImageRect(rect*)`** — clamped, see G5 |
| 9 | `+0x24` | `0x9BC15F` | `GetImageRect(rect*)` |
| 10 | `+0x28` | `0x9BC171` | `GetFlag(mask)` |
| 11 | `+0x2C` | `0x9BC181` | `SetFlag(mask, bool)` |

> EVIDENCE — slot 3: the mayor-rating controller at `0x7E87AE` does
> `GetChildAs(id, 0xC12CEA13, &p)` then `p->vt[0x0C]()` and calls **cIGZWin**
> methods on the result (`0x7E87B9 call [edx+0xCC]` = slot 51 `SetW`,
> `0x7E87CC call [edx+0x114]` = slot 69 `ShowWindow`).
> CONFIRMS `DYNAMIC-CONTROLS.md:118` ("image (re)bound via cIGZWinBMP
> (iid 0xc12cea13) `[vt+0x10]`") and gives it its 11 siblings.

### 4A.5 The class vtable — the 13 overrides

Every other one of the 151 slots is inherited from the base window class
(`0x0099Bxxx–0x0099Exxx`) or is a shared stub.

| Slot | VA | Override |
|---|---|---|
| 0 | `0x9BC06A` | `QueryInterface` — only `0xC12CEA13`, returns `this+0xD8`, else `jmp 0x99B774` |
| 3 | `0x9BC199` | `DoMessage` — types 5/6/7/0xA/0xD go to `0x99CCF0`; then if flag `0x01` and `[this+0x48]`, offset mouse coords for types 7..0xE and forward |
| 4 | `0x9BC52D` | `Init` — see G4 |
| 5 | `0x9BC097` | `Shutdown` — `Release()` the image, zero `+0xDC`, `jmp 0x99D2FE` |
| 55 | `0x9BC0B8` | `SetArea(l,t,r,b)` — **`jmp 0x99C837`, a pure forwarder.** See G7 |
| 62 | `0x9BC251` | screen-coords hit test — returns false if flag `0x04`, else base `0x99C97C` |
| **88** | **`0x9BC325`** | **`GZPaint` — the draw. §4A.6** |
| 130 | `0x9BC21D` | key-down → `SendMsg([this+0x4C], 5, a1, a2, 0)` |
| 131 | `0x9BC237` | key-up → `SendMsg([this+0x4C], 6, a1, a2, 0)` |
| 134 | `0x9BC2A6` | mouse (3 args) → `SendMsg([this+0x4C], **0x68915615**, x, y, GetID())` |
| 136 | `0x9BC2D0` | mouse (3 args) → `SendMsg([this+0x4C], **0x28916985**, x, y, GetID())` |
| 138 | `0x9BC27C` | mouse (3 args) → `SendMsg([this+0x4C], **0xC89155E3**, x, y, GetID())` |
| 148 | `0x9BC511` | scalar-deleting destructor (`0x9BC2FA` then optionally `0x5E5620`) |

All three mouse overrides go through slot **144** (`+0x240`), the 5-argument
`SendMsg(pWin, type, d1, d2, d3)`, and all end `ret 0xC`. They post; they never
consume.

⛔ **G3 — the slot we hook is `GZPaint`, not `Plot`.** The real `Plot` is
**slot 89 = `0x99BA07`** (inherited, never overridden), whose body is
`vt[123] PlotComposite` → `vt[124] PlotPresent` → an optional child call. The
drawing code lives one slot earlier.
> EVIDENCE — anchors that pin the numbering: slot 99 = `lea eax,[ecx+0x24]`
> (`GetAreaToDrawTo`), slot 93 = `[ecx+0x6C]` (`GetDrawContext`), slot 91 =
> `mov byte [ecx+0x70],1` (`InvalidateSelf`), slot 63 = `[ecx+0x10]` (`GetID`),
> slot 67 = `[ecx+0xC8] & mask` (`GetFlag`, called with `0x4000`, `0x80000`,
> `0x8000000`, `1` at four independent sites). Each of those sits **one slot
> later** than the same name in `vendor\gzcom-dll\…\cIGZWin.h`. See §9 #14.
> **The hook itself is correct** — slot 88 is the drawing entry either way.
> Only the *name* in `MAYOR-MODE.md`, `SC4-UI-ENGINE.md` §8.5 and
> `_tests\REGRESSION.md` is wrong.

### 4A.6 `GZPaint` (`0x9BC325`) — the whole flow

```
GZPaint(this):
  ── BACKGROUND ────────────────────────────────────────────────────────
  if ((flags & 0x02) == 0):                       # transparentbkg=no
      ctx = [this+0x6C]
      ctx->vt[21] SetColor( this->vt[126] GetFillColorRGB() )
      ctx->vt[35] FillRect( &this[0x24] )         # areaToDrawTo
  ── SOURCE SELECTION ──────────────────────────────────────────────────
  if ([this+0xDC] == 0): return true              # no image -> nothing
  if (GetFlag(0x10) || GetFlag(0x20)):  src = *(rect*)&this[0xE8]
  else:                                 src = *image->vt[12] GetRect()
  ── PATH CHOICE ───────────────────────────────────────────────────────
  if (!GetFlag(0x08)):
      ## PLAIN
      dst = { A.l, A.t, A.l + (src.r-src.l), A.t + (src.b-src.t) }   # A = this[0x24]
      if (GetFlag(0x20)): dst += (src.l, src.t)   # on both corners
      ctx->vt[38] DrawImage( image, &src, &dst )  # ONE blit
  else:
      ## EDGE / 9-SLICE
      src.r /= 3 ;  src.b /= 3                    # l and t UNTOUCHED
      helper_0x8D8800( ctx, image, &src, &this[0x24], fillCentre=1 )
  return true
```
> EVIDENCE — every line above is a byte-for-byte read of `0x9BC32E`–`0x9BC441`.
> The `/3` is `0x9BC414 cdq; push 3; pop ecx; idiv ecx` on `[ebp-8]` and
> `0x9BC422` on `[ebp-4]`; the rect copied at `0x9BC39E` is
> `(ebp-0x10, ebp-0xC, ebp-8, ebp-4)` = `(l, t, r, b)`, so **`r` and `b` are
> the values divided**.

⛔ **G8 — in the PLAIN path the window's width and height are never read.**
Only `A.l` and `A.t`. The size of the blit is 100% a function of the source
rect. A GZWinBMP therefore *cannot* letterbox, centre, or fit — it can only
start at its own top-left corner and run for the source's size, spilling past
its own edge if the source is bigger (clipping is the draw context's job, not
the widget's).

⛔ **G9 — src and dst can never "disagree" in the plain path, because dst is
built from src.** The only way to make them differ is to rewrite `dst` after
the fact — which is precisely what the BMPX hook does, and it **stretches**.
> EVIDENCE (live, not inferred) — `SC4UIScale.log` 11:16:23.598 and after:
> `UiSpike: BMPX draw id=0x48E945B4 img 64x64 win 128x128 -> dst 128x128
> (x2.00)`, repeated; the U-Drive-It mission bubble is user-confirmed 2x
> (task #60). So **ctx slot 38 (`+0x98`) scales `src`→`dst`**; it is not a
> 1:1-only blit. Corollary for the 9-slice: its corners come out 1:1 only
> because the helper hands slot 38 a dst of exactly the cell size.

### 4A.7 The 9-slice helper `0x8D8800`, blit by blit

Signature (cdecl, caller cleans `0x14`):
`helper(cIGZDrawContext* ctx, cIGZBuffer* img, cRZRect* srcCell, cRZRect* dst, bool fillCentre)`

`cellW = srcCell.r − srcCell.l`, `cellH = srcCell.b − srcCell.t`. The source
walks a **3 × 3 grid of `cellW × cellH` starting at `(srcCell.l, srcCell.t)`**;
the destination is re-derived from `*dst` for every band, so the dst is never
walked cumulatively.

| # | VA | ctx slot | Band | Guard |
|---|---|---|---|---|
| pre | `0x8D885E` | 10 (`+0x28`) | push draw state | — |
| pre | `0x8D887C` | — | `img->QueryInterface(0x86D72B57)`; on success builds a 32-bit colour from four bytes and calls ctx slot 21 `SetColor`, else `SetColor(-1)` | — |
| 1 | `0x8D8928` | **38** (`+0x98`) | top-left corner | always |
| 2 | `0x8D896A` | **39** (`+0x9C`) | top edge | `dst.l+cellW < dst.r−cellW` |
| 3 | `0x8D89A2` | 38 | top-right corner | always |
| 4 | `0x8D8A17` | 39 | left edge | vertical room |
| 5 | `0x8D8A6A` | 39 | **centre** | `fillCentre != 0` **and** both spans positive |
| 6 | `0x8D8AB2` | 39 | right edge | vertical room |
| 7 | `0x8D8B19` | 38 | bottom-left corner | always |
| 8 | `0x8D8B5B` | 39 | bottom edge | horizontal room |
| 9 | `0x8D8B93` | 38 | bottom-right corner | always |
| post | `0x8D8B9D` | 11 (`+0x2C`) | pop draw state | — |

Slot 39 (`+0x9C`) is called with **two extra zeroed arguments**
(`img, src, dst, 0, 0`).

⛔ **G10 — a window narrower/shorter than two cells does not clip; its corners
overlap.** The four corners are unconditional and are anchored to the dst's
four corners at full cell size; only the middle bands are skipped. Row advance
resets the source column to `srcCell.l` each time (`0x8D89A8` re-reads the
*original* `srcCell` pointer to compute the delta), so the grid is exact.

`[OPEN]` Whether ctx slot 39 **stretches or tiles** was not settled offline —
the draw-context class was not disassembled (positive control: both slots were
located and their argument counts read directly from the call sites; only the
implementation is unread). `blttype = tiled` being the second-most common
value in the corpus (254) makes "tile with a `(0,0)` phase" the live
hypothesis. Settles with one probe: hook ctx slot 39 the way BMPX hooks 38 and
log `src`/`dst` for one `edgeimage=yes` window.

### 4A.8 `imagerect` — the three places it is written, and the clamp

⛔ **G4 — `Init` (slot 4, `0x9BC52D`) sets `imagerect = (0, 0, GetW(),
GetH())` and then clamps it to the image.** It is a no-op if `GetFlag(0x4000)`
is already set (`0x99BC31`).
⛔ **G5 — `SetImageRect` (iface slot 8, `0x9BC103`) clamps: `l = max(0,l)`,
`t = max(0,t)`, `r = min(r, img->GetWidth())`, `b = min(b, img->GetHeight())` —
but only when an image is already bound.** With no image the rect is stored
raw.
⛔ **G6 — `SetImage` (iface slot 4, `0x9BC57E`) *destroys* the current
imagerect.** It AddRefs the new image, Releases the old, then calls `0x9BC447`
with `GetArea()`, which sets
`imagerect = (0, 0, min(winW, imgW), min(winH, imgH))`, then invalidates
(slot 92). The flag word is **not** touched.
⛔ **G7 — `SetArea`/`SetSize`/`SetW`/`SetH` never touch the imagerect.** Slot
55 is a bare `jmp` to the base. Resizing a live GZWinBMP changes where it draws
and nothing else.

**Therefore the complete list of things that change what a GZWinBMP draws is:
`Init`, `SetImage`, `SetImageRect`, and a direct field write to `+0xE8`.**
That single sentence is why "born correct" is the only architecture that works
for this widget and why a post-hoc sweep leaves 1x content behind.

⛔ **G11 — the runtime-supplied-image law (task #47, stated exactly).** A
GZWinBMP whose pixels arrive at runtime via `SetImage` draws
`min(winW, imgW) × min(winH, imgH)` source pixels, from the art's **top-left
corner**, at the window's top-left corner, with **no scaling**. Hence:
- art smaller than the window ⇒ 1x content pinned in the top-left quadrant
  (the §4.5 "unifying diagnostic", now with its cause);
- art **larger** than the window ⇒ the art is **cropped**, never downscaled;
- give it 2x art and the draw is 2x with no code hook at all.
> EVIDENCE — `0x9BC447` (`SetSrcRectFromRect`): `w = arg.r−arg.l`,
> `h = arg.b−arg.t`, stores `(0,0,w,h)` at `+0xE8`, then `if ([+0xF0] >
> img->vt[9] GetWidth()) [+0xF0] = GetWidth()` and the same for `+0xF4` /
> `vt[10] GetHeight()`.

⛔ **G12 — GZWinBMP has no state-strip machinery whatsoever.** There is no
`/4`, no index, no state field anywhere in the class; the only division in the
whole class is the `/3` of the edge path. `.UI` §3.3 pattern 2 ("multi-state
sheets", e.g. the mayor bar `14015549` 102×26 with `imagerect=(0,0,102,11)`)
is **controller-driven**: the controller re-writes the crop through iface slot
8, or swaps the image through slot 4, or — for the mayor rating bar — does not
touch the BMP at all and instead calls **`cIGZWin::SetW`** on it.
> EVIDENCE — `0x7E87B1 imul esi, esi, 7` then `0x7E87B9 call [edx+0xCC]` =
> cIGZWin slot 51 `SetW`, on the object returned by iface slot 3. The `7` is
> the documented "7 px per rating point" patch site.
> `imageWidth/4` state selection belongs to **`GZWinBtn`**, a different class.

### 4A.9 How a GZWinBMP is built from a script (the two-pass order)

The `.UI` window factory calls the per-class attribute handler **twice**, and
calls `Init()` between the two calls:

```
0x957C02   handler(win, res, 1)     # PASS 1  -> 0x95002C first branch
0x957C0E   generic(win, res, 1)     # base attrs: area=, winflag_*, fillcolor
0x957C25   win->vt[4] Init()        # -> imagerect = (0,0,winW,winH) clamped
   … parent attach, vt[23] PullToFront …
0x957C6B   handler(win, res, 0)     # PASS 2  -> 0x95002C second branch
0x957C77   generic(win, res, 0)
```

`0x95002C`, **PASS 1** (`arg3 != 0`), in order:
`alpha=` → `SetAlpha` · `notify=` → `SetFlag(0x01)` · `transparentbkg=` →
`SetFlag(0x02)` · `edgeimage=` → `SetFlag(0x08)` · `image={g,i}` → load the
PNG, **`SetImage(img)`**, then **`win->vt[53] SetSize(img->GetWidth(),
img->GetHeight())`**, then register the TGI as a dependency (type
`0x856DDBAC`) and Release.

`0x95002C`, **PASS 2** (`arg3 == 0`): `imagerect=` present →
`SetImageRect(rect)` + `SetFlag(0x10, true)`; absent → `SetFlag(0x10, false)`.

⛔ **G13 — `image={g,i}` resizes the window to the art.** This is the
mechanism behind §3.1's "419 controls have `area` exactly == PNG dims" and
behind the scaling law "style-PNG widgets are born at the ART's size": it is
not an authoring convention, the engine does it. It is a **default** — the
generic handler runs after it inside the same pass, so an explicit `area=`
wins (340 controls differ). A control with `image=` and **no** `area=` comes up
at exactly the art's dimensions, so **doubling that art doubles the window
too**, with no code involved.
> EVIDENCE — `0x950168 call [eax+0x10]` (iface `SetImage`), then `0x950171
> call [eax+0x28]` (`img->GetHeight`) and `0x950179 call [eax+0x24]`
> (`img->GetWidth`), pushed in that order, then `0x95017F call [ebx+0xD4]`
> where `ebx = *(void**)win` — `+0xD4/4 = 53` = `SetSize(w,h)`
> (`0x99BCB6`, verified: keeps l,t and calls slot 55 `SetArea`).

### 4A.10 Predicting a GZWinBMP, in order

1. Does it have `image=`? If not, and no controller calls `SetImage`, it draws
   **nothing but its background** (and even that only if `transparentbkg=no`).
2. Source rect: `imagerect=` present ⇒ the declared rect, **clamped to the
   art's real pixel size**; absent ⇒ the art's full natural rect.
3. `edgeimage=no` ⇒ **one blit**, size = the source rect's size, at
   `areaToDrawTo`'s top-left. The window's size is irrelevant.
4. `edgeimage=yes` ⇒ cell = `(src.r/3 − src.l, src.b/3 − src.t)`; four corners
   1:1 at the window's corners, four edges + centre filling the rest, middle
   bands dropped if there is no room.
5. Anything the game re-binds at runtime resets rule 2 to
   `(0,0,min(win,img))`.

═══════════════════════════════════════════════════════════════════════
BLOCK 2 — REPLACE §3.3 pattern 4 in `SC4-UI-ENGINE.md`
═══════════════════════════════════════════════════════════════════════

4. **9-slice / edge-blt** — `edgeimage=yes` (56 of 844) turns the *same*
   source rect into a 3×3 grid. ⛔ **The runtime divides only the rect's
   `right` and `bottom` by 3 and leaves `left`/`top` alone**, so the cell is
   `(r/3 − l, b/3 − t)` sampled from `(l, t)` — the grid therefore covers only
   `[l, r−2l) × [t, b−2t)` of the sheet. `imagerect` is **never** an inset,
   an edge width, or a centre rect; there is no inset concept anywhere in the
   engine. Corpus check: in **all 23** distinct `(art, imagerect)` combinations
   used by the 56 `edgeimage=yes` controls, the rect's `r,b` are **exactly the
   PNG's width and height** (e.g. `{1abe787d,144161e4}` 78×78 with
   `imagerect=(12,12,78,78)`; `{…,14416240}` 180×180 with `(12,22,180,180)`),
   which is what you would write if you knew the runtime was about to divide
   them. See §4A.7. **Doubling all four numbers alongside 2x art remains the
   correct transform** — at f=2 the cell `(2r/3 − 2l, 2b/3 − 2t)` is exactly
   twice the original.

Add after the ⛔ box in §3.3:

⛔ **A declared `imagerect` is clamped to the bound art at load time** (`l,t`
up to ≥0; `r,b` down to the image's real size — `0x9BC103`). So a hand-doubled
`imagerect` over 1x art does **not** produce "the corner that exists": a
`(0,0,w,h)`-style crop is clamped back to the whole 1x image and simply draws
1x, while a crop with non-zero `l,t` is clamped into an **inverted** rect
(e.g. `(244,222,878,182)` from doubling `(122,111,878,182)` against an
un-doubled 878×182 sheet) and yields a negative-height blit. ⚠ Our own
runtime `BMPRECT` fix writes `+0xE8` **directly and therefore bypasses this
clamp** — it can create rects the engine itself would never store. That is
fine while the paired art really is 2x and is a live hazard the moment an art
pass is missed.

═══════════════════════════════════════════════════════════════════════
BLOCK 3 — REPLACE the GZWinBMP rows in `SC4-UI-ENGINE.md` §8.5
═══════════════════════════════════════════════════════════════════════

| `0x00ADF6A0` | **GZWinBMP class vtable**, 151 slots; 13 overrides (0,3,4,5,55,62,**88**,130,131,134,136,138,148) |
| **`0x9BC325`** | **GZWinBMP `GZPaint` = slot 88 — the draw we hook.** NOT `Plot`; real `Plot` is slot 89 `0x99BA07` (PlotComposite→PlotPresent). dst origin = `[this+0x24]` areaToDrawTo; plain path = one ctx slot-38 blit sized from the source; edge path divides `src.r`,`src.b` by 3 and calls `0x8D8800` |
| `0x00ADF66C` / `0x00ADF63C` | **`cIGZWinBMP` interface vtable (12 slots) / its base (24)** — `+0x0C GetWindow`, `+0x10 SetImage`, `+0x20 SetImageRect`, `+0x28 GetFlag`, `+0x2C SetFlag` (§4A.4) |
| `0x9BC4BA` / `0x9BC2FA` / `0x9BC511` | ctor (writes flags `0x12`, alpha `0.5f`) / dtor / scalar-deleting dtor |
| `0x9BC57E` / `0x9BC447` / `0x9BC103` | `SetImage` / `SetSrcRectFromRect` (`(0,0,min(win,img))`) / `SetImageRect` (clamped) |
| `0x9BC52D` | GZWinBMP `Init` — imagerect := `(0,0,GetW(),GetH())`, guarded by `GetFlag(0x4000)` |
| `0x9BC0B8` | GZWinBMP `SetArea(l,t,r,b)` — bare `jmp 0x99C837`; **resizing never re-derives the source rect** |
| `0x9BC251` | slot 62 hit-test override — refuses when flag `0x04` |
| `0x9BC2A6` / `0x9BC2D0` / `0x9BC27C` | the three 3-arg mouse overrides; `SendMsg([this+0x4C], 0x68915615 / 0x28916985 / 0xC89155E3, x, y, GetID())` via slot 144 |
| **`0x8D8800`** | **the 9-slice helper** — `(ctx, img, srcCell, dstRect, fillCentre)`; 4 corners via ctx slot 38, 4 edges + centre via ctx slot 39, each middle band guarded, colour key via `img->QI(0x86D72B57)` |
| `0x953056` / `0x95002C` | GZWinBMP name+iid+token registration / its **two-pass attribute handler** (`alpha` 0xB00, `transparentbkg` 0xB01, `edgeimage` 0xB02, `notify` 0xF003, `image` 0xF016, `imagerect` 0xF018) |
| `0x957BE7`–`0x957C77` | the `.UI` window factory: pass 1 → generic pass 1 → `Init()` → pass 2 → generic pass 2 |
| ctx slots (class not yet disassembled) | `+0x28`/`+0x2C` push/pop state, `+0x54` SetColor, `+0x8C` FillRect, **`+0x98` DrawImage(img,src,dst)** — proven to scale, **`+0x9C` DrawImage(img,src,dst,0,0)** |

═══════════════════════════════════════════════════════════════════════
BLOCK 4 — `SC4-UI-ENGINE.md` §9 (contradictions): rewrite #8, extend #11,
add #14
═══════════════════════════════════════════════════════════════════════

8. **What `imagerect` means on a 9-slice.** `UI-ART-BINDING.md` §3 calls it
   "the stretchable center rect" with "fixed 12/22px borders";
   `UISCRIPTS.md` says the slice geometry "appears nowhere in the scripts".
   **Resolution: `imagerect` is a SOURCE RECT, always, and the slice geometry
   *is* derived from it — but not as an inset.** `GZPaint` divides only `r`
   and `b` by 3 (`0x9BC414`/`0x9BC422`); the cell is `(r/3 − l, b/3 − t)` and
   the grid starts at `(l, t)`. "Fixed 12/22px borders" is arithmetically
   impossible under those bytes — for `{46a006b0,14416240}` (180×180,
   `imagerect=(12,22,180,180)`) the cell is **48×38**, not 12×22.

11. **`0x00ADF6A0`.** …existing text… **Extended:** the class is fully
    documented in §4A, and the slot we hook (88) is **`GZPaint`**, not `Plot`.
    Every doc that says "Plot `0x9BC325`" — `MAYOR-MODE.md` ("SOLVED
    2026-07-29"), `_tests\REGRESSION.md` (task #47), `UiSpike.cpp`'s BMPX
    comment — names the wrong virtual. The hook is on the right slot; only the
    label is wrong.

14. **`vendor\gzcom-dll\…\cIGZWin.h` slot names drift by one.** From slot
    **58 through slot 138** the real vtable is `header index + 1` (the header
    is missing one method around 58 and carries one spurious method — most
    likely `GZOnMouseWheel` — around 138). Anchors, all measured from bodies:
    real 60 = `WindowToScreenCoordinates` (adds `[+0x14]`,`[+0x18]`), real 61 =
    `WindowToWindowCoordinates` (3 args, calls `vt[60]` then the other
    window's `vt[59]`), real 63 = `GetID` (`[ecx+0x10]`), real 67 = `GetFlag`,
    real 91 = `InvalidateSelf`, real 93 = `GetDrawContext` (`[ecx+0x6C]` —
    the field `UiSpike.cpp` already reads), real 99 = `GetAreaToDrawTo`
    (`lea eax,[ecx+0x24]`), real 133 = a 1-arg stub shared with real 129
    (impossible under the header's 2-arg/3-arg pairing), real 139 = a 4-arg
    stub, real 144 = the 5-arg `SendMsg` the mouse overrides call.
    ⛔ **Index by NUMBER, never by header name, anywhere in this band.**

═══════════════════════════════════════════════════════════════════════
BLOCK 5 — REPLACE the `edgeimage` bullet in `UI-ART-BINDING.md` §3
═══════════════════════════════════════════════════════════════════════

- `edgeimage = yes | no` (GZWinBMP) — yes 56, no 788. With `yes` the bitmap is
  9-sliced, **but `imagerect` is not the centre rect and is not an inset.**
  The runtime does `src.r /= 3; src.b /= 3` and leaves `src.l`/`src.t` alone
  (`0x9BC411`–`0x9BC425`), then hands `0x8D8800` a single **cell**
  `(l, t, r/3, b/3)` which it steps across a 3×3 grid. So the visible border
  thickness is `artW/3 − l` by `artH/3 − t`, and the sheet's outermost `l`/`t`
  pixels are **never sampled**. The earlier claim here — "`{1abe787d,14416240}`
  is 180×180, drawn with `imagerect=(12,22,180,180)` … fixed 12/22px borders,
  stretched middle" — has the mechanism inverted: those numbers produce a
  **48×38** cell. The *practical* rule is unchanged and now has a derivation:
  **2x art requires doubling all four `imagerect` numbers**, because
  `(2r/3 − 2l, 2b/3 − 2t) = 2 × (r/3 − l, b/3 − t)` exactly.

═══════════════════════════════════════════════════════════════════════
BLOCK 6 — corrective paragraph for `_tests\REGRESSION.md`, under
"The BMPX hook (task #47, UiSpike.cpp)"
═══════════════════════════════════════════════════════════════════════

**Correction (offline disassembly, this session).** Two labels in the
paragraph above are wrong and one field is imprecise. (a) `0x9BC325` is class
vtable slot 88 = **`GZPaint`**, not `Plot`; the real `Plot` is slot 89
(`0x99BA07`) and only calls PlotComposite/PlotPresent. The hook is on the
correct slot — rename only. (b) The dst origin is `[this+0x24]`
(**areaToDrawTo**, the window's rect expressed in the nearest buffer-owning
ancestor's coordinates), not the window's `area=`; for a window that owns a
private buffer it is `(0,0,w,h)`. (c) "the window rect is never read" is
exactly right and now has a cause: `dst` is *constructed* from `src`, so the
window's W/H are structurally absent from the plain path. The self-limiting
`m ≤ 1` clamp against `GetW()/GetH()` is therefore a policy we added, not a
property of the engine. (d) `BMPRECT` writes `+0xE8` directly and so bypasses
`SetImageRect`'s clamp (`l,t ≥ 0`, `r,b ≤ image dims`, `0x9BC103`) — the only
reason that is safe is that we only run it on dialogs whose art we know is
already 2x. Add a trap line: **if a BMPRECT-doubled dialog ever shows a
missing or inverted band, the paired art pass is missing — the clamp that
would normally have caught it is not in our path.**
