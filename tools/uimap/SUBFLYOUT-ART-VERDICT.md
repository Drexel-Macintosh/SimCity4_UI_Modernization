# SUB-FLYOUT GEOMETRY: ART-DERIVED OR CODE-DERIVED? — THE VERDICT

> ## **CODE-DERIVED.** Every pixel of the nested sub-flyout's geometry — the invariant width, the per-menu height, the item strip and its row pitch — is computed from `imm8` constants inside `sub_7EAEB0` and the container class's own `vf10`/`vf14`; the bitmap the builder loads is **never read for the window rect**. The single art-derived runtime quantity is `[container+0xec] = artWidth − 2×capH`, and it parameterises the *blit*, not the rect. Build the byte-patch.

Offline analysis: the exe was opened read-only and the game was never
launched. Every number below is measured — from the PE image or from the
shipped PNG headers — except where a line is explicitly labelled HYPOTHESIS.
Companion documents: `SUBFLYOUT-BUILDER.md` (the full decode),
`SUBFLYOUT-LIVE-EVIDENCE.md` (the live oracle), `SUBFLYOUT-CONSTANTS.md`
(the early scan whose art-bound hypothesis this verdict supersedes).

**Tools written for this investigation** (in `tools\uimap\_subflyout-art\`):
`measure_art.py` (IHDR/JFIF/BMP/FSH dimension inventory of all 2,280
type-`0x856DDBAC` entries → `art-dims.csv`), `sfdis.py` (PE-resolved capstone
disassembler).

---

## 1. THE COMPLETE FORMULA

```
W_stock = [obj+0xf0] − [obj+0xf8] + [obj+0xe4]        = 80 − 4 + 53  = 129   (invariant)
H_stock = max(stripH, [obj+0xf4]) + 2 × [obj+0xe8]    = max(stripH, 53) + 50
stripH  = count × (cellH 44 + gap 5) − gap 5          = 49·count − 5
count   = clamp(provider->GetCount(), 1, 8),  further capped to 6 if viewH ≤ 600
```

All seven inputs are `push imm8` in the builder. **Nothing on the right-hand
side comes from an image.**

The live sizes in `MAYOR-MODE.md` and in the task brief are these values
**doubled by our own sweep**. `src\UiSpike.cpp:2544` says so in as many words —
*"SIZE was already correct via the generic sweep (129x241 -> 258x482)"* — a
line I found only **after** deriving 129 and 241 from the immediates, so it is
an independent confirmation rather than the source of the claim.

### Every observed size reproduced — 8/8 containers, 4/4 archived strips

| items | stripH = 49n−5 | contH = max(·,53)+50 | ×2 → container | ×2 → strip | observed |
|---|---|---|---|---|---|
| 1 | 44 → **floored to 53** | 103 | **258 × 206** | 88 × 88 | Freight ✔ |
| 2 | 93 | 143 | 258 × 286 | 88 × 186 | ✔ |
| 3 | 142 | 192 | 258 × 384 | 88 × **284** | ✔ ✔ |
| 4 | 191 | 241 | 258 × 482 | 88 × **382** | ✔ ✔ |
| 5 | 240 | 290 | 258 × 580 | 88 × 480 | ✔ |
| 6 | 289 | 339 | 258 × 678 | 88 × **578** | strip ✔ |
| 7 | 338 | 388 | 258 × 776 | 88 × 676 | ✔ |
| 8 | 387 | 437 | 258 × 874 | 88 × **774** | ✔ ✔ |

Container heights from `MAYOR-MODE.md` (482/384/874/776/580) + the brief
(482/286/206). Strip heights 284/382/578/774 from the archived-log list quoted
in `src\UiSpike.cpp:5727`. **Zero misses, zero fudge factors.**

**Freight is the proof.** One item gives `49·1 − 5 = 44`, which is *below* the
53 floor, so it clamps: `53 + 50 = 103`, ×2 = **206**. That is the one height
that breaks every arithmetic progression anyone would fit to the data (the
other seven are `90 mod 98`; 206 is `10 mod 98`), and the formula produces it
exactly, from a constant — `0x35` at VA `0x007EB163` — that no art asset
supplies.

---

## 2. THE EVIDENCE, IN CODE

### 2.1 Correction first: the builder is `sub_7EAEB0`, not `sub_7EAC70`

`tools\uimap\SUBFLYOUT-CONSTANTS.md` attributes this to `sub_7EAC70`
"0x007EAC70…0x007EB84C". **`sub_7EAC70` ends at `0x007EAEAD` (`ret`, then
`int3 int3`).** The function that creates the container is a separate
`__thiscall` at **`0x007EAEB0`** (`ret 0x18` = 6 stack args), ending
`0x007EB2E9`. Consequences:

* the `124` at `0x007EAD4B` (flagged there as an unpatchable ceiling) is in the
  *other* function and is **not on this path**;
* the `0x258` at `0x007EAF3D` is **600 decimal**, a view-height threshold. It
  is not the container's 258 and the two must never be conflated;
* `0x8A6E61E0` has exactly one push site image-wide (`0x007EB11B`), so
  `sub_7EAEB0` is unambiguously *the* builder.

### 2.2 The builder's constant stanzas

| VA | bytes | value | goes to | meaning (derived) |
|---|---|---|---|---|
| `0x007EAEF3` | `6a 2c` | 44 | `provider->vf30` arg1 | cell W |
| `0x007EAEF1` | `6a 2c` | 44 | arg2 | **cell H** |
| `0x007EAEEF` | `6a 05` | 5 | arg3 | **row gap** |
| `0x007EAF21` | `bb 01…` | 1 | count floor | not geometry |
| `0x007EAF2D` | `bb 08…` | 8 | count ceiling | not geometry |
| `0x007EAF3D` | `3d 58020000` | **600** | `cmp viewH, 600` | screen-height rule |
| `0x007EAF49` | `bb 06…` | 6 | count cap ≤600 | not geometry |
| `0x007EB169` | `6a 35` | 53 | `container->vf10` arg2 → `+0xe4` | **bar width** (also the `IsPointInMe` claim, §2.5) |
| `0x007EB167` | `6a 19` | 25 | arg3 → `+0xe8` | **end cap** (×2 = the +50) |
| `0x007EB165` | `6a 50` | 80 | arg4 → `+0xf0` | ring-sprite width term of W |
| `0x007EB163` | `6a 35` | 53 | arg5 → `+0xf4` | **minimum content extent** (Freight) |
| `0x007EB161` | `6a 04` | 4 | arg6 → `+0xf8` | overlap subtracted from W |
| `0x007EB15F` | `6a 1b` | 27 | arg7 → `+0xfc` | anchor offset (cross axis) |
| `0x007EB15D` | `6a 1d` | 29 | arg8 → `+0x100` | anchor offset (long axis) |

Argument→field mapping was taken from the **stores inside `vf10`**, not from
push order guessing; the previous table in `SUBFLYOUT-CONSTANTS.md` §2 has the
roles reversed and all rows marked UNVERIFIED. They are now verified.

### 2.3 `vf10` = `0x0079AC60` — where the art enters, and where it stops

Container object primary vtable = **`0x00AB6D04`** (written by ctor
`0x0079AFF0`; the `cIGZWin` sub-object at `+4` gets `0x00AB6AA8`, which is the
value the `SVT` probe reported). `vf10 = [0xAB6D04+0x10] = 0x0079AC60`,
`ret 0x20` = 8 args. It stores:

```
+0xdc = the bitmap            (AddRef/Release pair @ 0x79AC7B / 0x79AC8C — a refcounted object)
+0xe4 = 53      +0xe8 = 25    +0xf0 = 80     +0xf4 = 53
+0xf8 = 4       +0xfc = 27    +0x100 = 29
+0xec = bmp->vf28() − 2 × [+0xe8]           <-- THE ONLY ART-DERIVED FIELD
```

`0x0079ACA9: mov edx,[ecx]; call [edx+0x28]` on the bitmap, then
`lea ecx,[edi+edi]; sub eax,ecx` → `[+0xec] = artDim − 50`.

*HYPOTHESIS (well-supported, not measured):* `vf28` is `GetWidth`, so
`[+0xec] = 292 − 50 = 242` = the stretchable middle of a 9-slice whose two end
caps are the 25 in `[+0xe8]`. It fits the art (§3) and the alternative
(`GetHeight` → `53 − 50 = 3`) is absurd. **It does not affect the verdict
either way**, because:

### 2.4 `vf14` = `0x0079AD00` — the SetArea, and it never touches `+0xec`

`vf14`, `ret 0x18` = 6 args, called at `0x007EB193` as
`vf14(stripW, stripH, x, y, 10, viewBottom−10)`:

```
0x0079AD0A  ebp = [esi+0xf0]                      ; 80
0x0079AD1D  ebp -= [esi+0xf8]                     ; −4
0x0079AD23  ebp += [esi+0xe4]                     ; +53   -> ebp = 129
0x0079AD2B  cmp arg2, [esi+0xf4] / jl ...         ; ecx = max(stripH, 53)
0x0079AD47  lea eax,[ecx + eax*2]                 ; eax = max(...) + 2*[esi+0xe8]  (+50)  -> W
   ... vertical clamping against arg5 (10), arg6, [esi+0xe8], [esi+0x100] ...
0x0079ADBD  push eax        ; edi + W             = bottom
0x0079ADBE  lea eax,[ecx+ebp] / push              = right   (= left + 129)
0x0079ADC2  push edi                              = top
0x0079ADC3  push ecx                              = left
0x0079ADC7  call [edx+0xdc]  on [esi+4]           ; SetArea4 (+0xDC, confirmed in SC4-UI-ENGINE.md:145)
```

**Fields read by `vf14`: `+0xe4, +0xe8, +0xf0, +0xf4, +0xf8, +0xfc, +0x100`.
`+0xec` is never read. The bitmap pointer at `+0xdc` is never read.** This is
the whole answer: the rect is a pure function of seven immediates and the item
count. `(left, top, left+129, top+W)` is unmistakably an L/T/R/B call, and the
x-derived argument feeds left/right (→ **W = 129**) while the y-derived one,
the only one that gets screen-clamped, feeds top/bottom (→ **H = W-term**).

### 2.5 Cross-check the project has already paid for

The container's custom `IsPointInMe` (`0x0079AE30`) claims only the rightmost
`[win+0xe0]` pixels — and `win = obj+4`, so `[win+0xe0]` **is** `[obj+0xe4]`
**= the 53 pushed at `0x007EB169`**. `MAYOR-MODE.md` measured exactly this
("only right half clickable… claims only the rightmost `[this+0xe0]` px") and
cured it with **`ClaimScale=2`** — a runtime *doubling of a code constant*.
Likewise `gStripFieldScale=2` doubles the 44 cell. The project has therefore
**already had to patch these very constants twice**, which is only necessary if
they are code, not art.

The bar arithmetic closes the loop: art 53 wide drawn flush right in a 258
buffer → `205..258`; the fix `152 + 106 = 258`. At stock that is a 53-wide bar
flush right in a **129** buffer → `76..129`. Consistent.

---

## 3. THE ART, MEASURED

`measure_art.py` over all 2,280 type-`0x856DDBAC` entries of `SimCity_1.dat`
(the only archive with UI art — `tools\dbpf\NOTES.md`).

### 3.1 What the builder actually loads

`0x007EB0C0–0x007EB0D4` fetches `{0x856DDBAC, 0x46A006B0, arg5}`. `arg5` is a
caller argument; all **seven** call sites of `sub_7EAEB0` were disassembled and
each pushes a literal:

| call site | instance | measured size |
|---|---|---|
| `0x007EC663` | `0x14215ED0` | **292 × 53** |
| `0x007EC6C9` | `0x14215ED0` | **292 × 53** |
| `0x007EC729` | `0x14215ED1` | **292 × 53** |
| `0x007EDDC6` | `0x14215EDD` | **292 × 53** |
| `0x007F3B8B` | `0x14215ED3` | **292 × 53** |
| `0x007F3D97` | `0x14215ED2` | **292 × 53** |
| `0x007F4EE1` | `0x14215ED4` | **292 × 53** |

(each also mirrored byte-identically in group `0x1ABE787D`; `0x14215ED5` exists
at the same size but is pushed by no call site.)

**This is falsification #1, and it is decisive.** `SUBFLYOUT-CONSTANTS.md` §0
predicts *"heights differ per menu because the art instance differs."* The art
instance **does** differ — and its size **never** does. Seven different
instances, one size, seven different window heights from 103 to 437 stock. No
art-driven mechanism can produce that.

The atlas decomposes cleanly against the immediates:
`292 = 80 + 4 × 53` — one 80-wide ring sprite plus four 53-wide frames, all 53
tall (visually confirmed: ring-with-tail, oval, three arrow tiles). So the code
constants `80`, `53`, `4` **mirror** the art. They are hand-authored to match
it. They are not *read* from it.

### 3.2 Does 258 / 88 / 382 equal an art dimension or a sum?

| quantity | stock | equals art? |
|---|---|---|
| container W **258** | **129** = 80 − 4 + 53 | **No** (see the 129×129 note below). |
| container H 482 etc. | 241 etc. | **No.** Only 3 images in 2,280 have any of the heights 103/143/192/241/290/339/388/437 (86×103, 41×103, 128×143) and none is 129 wide. |
| strip **88** | **44** | 44 *is* the icon frame size (`176×44` = 4 states × 44) — but see §4. |
| strip **382** | **191** = 4×44 + 3×5 | **No.** Pure arithmetic; no 44×191 asset exists (only 6 images are 44 wide at all). |

**The 129-wide art, stated honestly.** There *are* 129-wide images: 24 of them
(instances `0x14416220`…`0x1441622B` × both mirror groups), and every one is
exactly **129 × 129** — square. They are excluded because (a) none appears as
an imm32 anywhere in the exe, (b) all are `.UI`-referenced (`refmap.csv`
rows 7/8/243–245…), and (c) a single square asset cannot produce eight
different heights against one fixed width. The 129 in `W` is a *sum of three
immediates*, `80 − 4 + 53`, computed at `0x0079AD0A–0x0079AD23`; that it also
happens to be an art size elsewhere in the game is a collision, not a source.
Recorded because the next investigator will grep for 129 and find these.

**The one 258-wide image is a red herring and must be recorded as such.** Of
2,280 entries exactly one is 258 wide: `T-856ddbac G-46a006b0 I-14416322`,
**258 × 239** (a rounded balloon with a tail — it *looks* the part). It is
excluded on three counts: (a) `0x14416322` appears **nowhere** in the exe as an
imm32, so no code path loads it; (b) `refmap.csv:283` shows it is `.UI`-bound
(`T-00000000_G-96a006b0_I-ca539340.ui`, 3 refs); (c) 258 is our *doubled*
value — stock is 129 — so matching it would be matching the wrong number
anyway. Anyone re-running this investigation will find that image first; this
paragraph exists so they stop where I did.

---

## 4. "IS THE ART ALREADY 2x?" — the third falsification

**The sub-flyout's own atlas is NOT shipped at 2x.** `0x14215ED0..ED5` and
`EDD` are absent from `refmap.csv`, `package-list.txt`, `selective-safe\stage\`
and `CODE_BOUND_TGIS` in `build_selective_safe.py`. `refmap.csv` is built from
`.UI` references and this art has none, so the reference-driven pass could
never reach it — the same blind spot that `CODE_BOUND_TGIS` exists to patch.

That means the literal experiment "art is 2x, window still 1x" has not been run
*on this atlas*. It **has** been run on the strip's contents, and it failed the
art hypothesis:

* `tools\itemicons\stage\` holds **320 icons at 352 × 88** — 4 states × 88,
  doubled from stock `176 × 44`. Shipped.
* The strip cell nevertheless stayed **44**, because `provider->vf30(44,44,5)`
  hardcodes it.
* The project's fix was `gStripFieldScale=2` — a **runtime constant patch**.

Art at 2x did not move the geometry one pixel. Two runtime constant patches
did. Combined with §3.1 (constant art, varying height) the art hypothesis is
falsified by evidence, not by analogy.

**The art still has to be doubled** — just not for size. The `MAYOR-MODE.md`
items *"bar 1x"*, *"circle 1x"*, *"ring not 2x-covering"* are exactly a 1x
atlas blitting into a 2x window. Ship `0x14215ED0..ED5`, `EDD` (both group
mirrors) at 2x **and** patch the constants — and do it in lockstep, because
`[+0xec] = artW − 2×25` recomputes itself from the art while the 25 does
not: a 584-wide atlas with an unpatched 25 mis-cuts the 9-slice.

---

## 5. WHY THIS EXPLAINS THE FLASH, AND WHAT TO BUILD

The container is **born** at `129 × 241` and painted there. Our sweep runs 4×/s
and resizes it to `258 × 482`. That is the reported *"1x for a moment, then
snaps to 2x"* — the textbook reactive-sweep flash
(`feedback-sc4-reactive-sweep-flashes`), and per that memory the cure is
**born-2x**. Here born-2x has a precise, bounded meaning: patch the seven
immediates so `vf10`/`vf14` produce the scaled rect at construction.

### Patch table (roles now verified; ceilings computed)

| VA | bytes | stock | role | f=1.5 | f=2 | f=3 |
|---|---|---|---|---|---|---|
| `0x007EAEF3` | `6a 2c` | 44 | cell W | 66 ✓ | 88 ✓ | 132 ✗ |
| `0x007EAEF1` | `6a 2c` | 44 | cell H | 66 ✓ | 88 ✓ | 132 ✗ |
| `0x007EAEEF` | `6a 05` | 5 | row gap | 8 ✓ | 10 ✓ | 15 ✓ |
| `0x007EB169` | `6a 35` | 53 | bar width / claim | 80 ✓ | 106 ✓ | 159 ✗ |
| `0x007EB167` | `6a 19` | 25 | end cap | 38 ✓ | 50 ✓ | 75 ✓ |
| `0x007EB165` | `6a 50` | 80 | W term | 120 ✓ | **160 ✗** | ✗ |
| `0x007EB163` | `6a 35` | 53 | min extent | 80 ✓ | 106 ✓ | 159 ✗ |
| `0x007EB161` | `6a 04` | 4 | W overlap | 6 ✓ | 8 ✓ | 12 ✓ |
| `0x007EB15F` | `6a 1b` | 27 | anchor X | 41 ✓ | 54 ✓ | 81 ✓ |
| `0x007EB15D` | `6a 1d` | 29 | anchor Y | 44 ✓ | 58 ✓ | 87 ✓ |

Check at f=2: `W = 160 − 8 + 106 = 258` ✓ and, for 4 items,
`H = max(4×98 − 10, 106) + 100 = 382 + 100 = 482` ✓, strip `88 × 382` ✓ —
**exactly** the sizes the sweep currently produces after the fact. The patch
reproduces today's end state at birth; that is the whole point.

Implementation notes, flagged not decided:

* **`0x007EB165` (80) overflows `imm8` at f ≥ 1.6** (signed cap 127). f=1.5 is
  pure byte-patch; f=2/3 need `6a 50` → `68 imm32` (2 bytes → 5, so a cave or
  an in-place re-encode of the whole push block), or a runtime pin. This is the
  single blocker and it is one instruction.
* Do **not** scale `1`/`8`/`6` (item counts). The `600` at `0x007EAF3D` is a
  screen-height rule — scaling it is a product decision, not a fact.
* Once born-2x, the sweep must become idempotent for `0x8A6E61E0` or it will
  double 258 → 516. `IsSubFlyoutId` already exists as the hook point.
* The patch surface is clean: `sub_7EAEB0` is the *only* creator of
  `0x8A6E61E0`, and its seven callers are all sub-flyouts. But
  `0x8A2CAD8B` has a **second** push site at `0x007E5EB9`, outside this
  builder — status unknown, check before assuming one path (law 15/16).

---

## 6. WHAT WOULD OVERTURN THIS (there is one measurement, and it is cheap)

The evidence is not ambiguous — 8/8 heights, 4/4 strip heights, a clamped
outlier reproduced exactly, three independent falsifications, and the
formula's stock value already written in our own source. But the honest
one-line test, if anyone wants it, is the same log line
`SUBFLYOUT-CONSTANTS.md` §5 proposed, read the other way round:

```
SUBFLY: cont 0x8A6E61E0 (l,t WxH)  strip 0x8A2CAD8B (l,t WxH)  items=N
```

with the sweep disabled for this id. **Prediction: `129 × (max(49N−5,53)+50)`
and strip `44 × (49N−5)`, for every menu, with the 292×53 art unchanged.** A
single menu whose *stock* width is anything other than 129 would overturn the
verdict. Nothing else would.

The remaining genuine unknown is narrow and does not touch the verdict: whether
the bitmap `vf28` is `GetWidth` (§2.3), i.e. whether `[+0xec]` is 242 or 3.
Settle it by disassembling the container's paint path off `0x00AB6AA8` slot
87/88 and watching `[+0xec]` reach a blit source rect — an offline half-hour,
needed only when the art re-ship is built.
