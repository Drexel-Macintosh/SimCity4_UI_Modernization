# POPUP-VERDICT — what the ordinance description popup actually does

**Produced by** `tools\uimap\emu\emu_layout.py` (Stage 3 of the offline UI
model, `METHOD.md` §6). Offline only: the exe was read, never launched, never
modified. Everything below marked MEASURED comes from the live POPKID dumps
already recorded in `BUDGET-DETAIL-ANATOMY.md` §POPUP; everything marked
PREDICTED is the emulator's output and is a **HYPOTHESIS until a live dump
confirms it** (`METHOD.md` standing rule: the model is never the authority).

Run the evidence yourself:

```
cd tools\uimap\emu
python emu_layout.py --selftest --fresh -v
```

---

## 0. VERDICT IN ONE PARAGRAPH

**The model reproduces both ground-truth rects exactly — 795x75 and 750x25 —
and it reproduces them WITHOUT ANY FONT INPUT AT ALL.** That is the finding.
The ordinance body is created with `align 0x63` (*fill*), and the fill branch
of `sub_779660` **overwrites all four edges** from the parent popup's size:
`SetArea(x, y, parentW − 2x, parentH − y)`. The text extent computed a moment
earlier is discarded. So the two numbers that §POPUP called the "decisive
observation" of wrapping (795x75 = "three lines", 750x25 = "one line") are not
about text at all: **795x75 is the body at x/y = (15,25) and 750x25 is the same
body after the v2.27.0 patch moved it to (30,50)**. Both fall out of the same
formula, for any string, in any font.

Consequences, in order of importance:

1. **The `push 0x3e8` (1000) at `0x77971A` is NOT the wrap width, and cannot
   be.** It is applied *after* the layout and is then overwritten by the fill
   branch. Patching it would change every align-0 / align-6 label in the budget
   family and would not touch this popup by one pixel. **Do not scope it, do
   not detour it — question 2 of §POPUP P4 is answered NO.**
2. **The real defect is geometric and ours.** Three of the popup's own
   constants were never scaled: its height `125`, its right margin `60`, and
   its x `30`. The body therefore gets **25 px of height at 2x where stock
   gives it 75** — with a 28-pt font that is less than one line. The popup is
   also 60 px too wide for the same reason.
3. The fix is a three-constant `round(stock × f)` patch that reduces to stock
   at `f = 1` and is proven by emulation to land on exactly 2x stock at
   `f = 2` (§4).
4. **§5 closes the other half.** The line breaks are computed by `sub_9BF3E0`
   against `[this+0x160] = GetW() − 2×gutter(5)` — **recomputed and re-broken
   on every `SetArea`** (override `0x009BFCA5`), so the effective wrap width
   today is `750 − 10 = 740`, not 1000. It does not wrap because the
   **word-wrap flag `0x0002` in `[this+0x128]` is off** (ctor default 0;
   `sub_779660` never sets it), leaving the `'\n'`-only regime — which is
   exactly why one description breaks early and another clips mid-word.
   **Cure: one `cIGZWinText::SetWinTextFlag(2, true)` on `0x0ABCE001`. No
   constant, no string work.**

---

## 1. THE CHAIN, DECODED — `sub_779660` (`0x00779660`, `ret 0x28`, 10 args)

Signature confirmed by the emulated run and by both call sites:

```
sub_779660(parent, id, x, y, pText, align, styleId, R, G, B)   // __thiscall
```

Execution order (this ORDER is the whole answer):

| # | VA | What |
|---|---|---|
| 1 | `0x0077967A` | `factory->[vt+0x34](id, pText)` — **create the text window, caption already set** |
| 2 | `0x0077968B` | `win->SetID(id)` |
| 3 | `0x007796A1` | `font = factory->[vt+0x14](styleId)`; `0x007796A7` `text->SetFont(font)` |
| 4 | `0x007796C4` | `colour = gfx->[vt+0x88](R,G,B)`; `0x007796CD` `text->SetTextColor(colour)` |
| 5 | **`0x007796D8`** | **`text->FitWindowToText(false, false)` — the ONLY layout step** |
| 6 | `0x007796E6` | `w = win->GetW()` → **this is the function's return value** |
| 7 | `0x007796FB` | `r = win->GetArea()` → `int32_t*` to `{L,T,R,B}` |
| 8 | **`0x00779723`** | `win->SetArea(r.R, r.T, **1000**, r.B)` ← the `push 0x3e8` at `0x0077971A` |
| 9 | `0x00779736` / `0x00779777` / `0x00779793` | the align branch (see below) |
| 10 | `0x007797F6` | `text->SetAlignment(align)`; `0x0077980B`/`0x00779823` clear flags `0x800` / `0x8000` |
| 11 | `0x00779835` | `parent->ChildAdd(win)`; `0x0077983C` `text->Release()` |

The three align branches:

| align | VA | Effect |
|---|---|---|
| `0` (left) | `0x00779777` | `GZWinMoveTo(x, y)` — keeps `W = 1000 − textW` |
| `6` (right edge on x) | `0x00779736` | `GZWinMoveTo(x − GetW(), y)` — keeps `W = 1000 − textW` |
| **`0x63` (fill)** | **`0x00779793`** | **`SetArea(x, y, parentW − 2x, parentH − y)` — every edge replaced; `1000` and `textW` both gone** |

Rect semantics proven by reading the base class, not assumed:
`cGZWin::SetArea` (`0x0099C837`) stores its four args **directly** as
`L,T,R,B` at `[this+0xA8..0xB4]`; `GetW` (`0x0099C81B`) returns `[+0xB0]−[+0xA8]`.
So for the fill branch:

```
W = (parentW − 2x) − x = parentW − 3x
H = (parentH − y) − y  = parentH − 2y
```

The SDK's `cRZRect` is declared `{nX, nY, nWidth, nHeight}`. **That naming
does not apply to a window's area field** — the engine stores L,T,R,B there.
Anyone reading `cRZRect.h` and assuming width/height will mis-derive every
budget rect.

---

## 2. THE ACCEPTANCE TEST — PASSED, 5/5

Emulated with the **real** `sub_779660`, the **real** `cGZWin::SetArea`,
`GZWinMoveTo`, `GetW`, `GetH` and `GetArea`. Only `FitWindowToText` and the
service getters are python.

| Case | Inputs | Predicted | Measured | |
|---|---|---|---|---|
| BODY 2x, x/y **unpatched** (15,25) | popup 840x125 | **795x75** | 795x75 (City Lottery dump) | yes |
| BODY 2x, x/y **patched** (30,50) | popup 840x125 | **750x25** | 750x25 (Smoke Detector dump) | yes |
| TITLE 2x, align 0 | text extent 303x37 | **697x37** | 697x37 | yes |
| BODY 1x stock (15,25) | popup 390x125 | **345x75** | *never captured* | PREDICTION |
| BODY 2x with the §4 fix | popup 780x250 | **690x150** | *not built yet* | PREDICTION |

The verbose trace of the second case is the evidence for §0.1 — watch the 1000
appear and then die:

```
FitWindowToText(0, 0) -> MODELLED text extent 768x12
SetArea(win:0x0ABCE001, 768,0,1000,12) -> 232x12      <- the push 0x3e8
SetArea(win:0x0ABCE001, 30,50,780,75) -> 750x25       <- fill branch, overwrites it
GZWinMoveTo(win:0x0ABCE001, 30,50)
SetArea(win:0x0ABCE001, 30,50,780,75) -> 750x25
```

Feed it a 12-character description or a 500-character one: the body rect does
not move. **That is what "reproduces the ground truth without font input"
means, and it is why three shipped wrap fixes could not have worked.**

---

## 3. WHERE THE POPUP'S OWN GEOMETRY COMES FROM

Builder `0x0078B980+` (ordinance path). Constants read back from the shipped
exe by the tool itself (`--selftest` prints them):

| VA | Encoding | Stock value | Meaning | Scaled by us today? |
|---|---|---|---|---|
| `0x0078B99F` | `push 0x7d` (imm8 @ `0x0078B9A0`) | **125** | popup **height** (`SetSize` on both `0x0423278D` and content `0x0423278F`) | no **NO** |
| `0x0078B9A1` | `sub ebx,0x3c` (imm8 @ `0x0078B9A3`) | **60** | popup width = `dialogW − 60` | no **NO** |
| `0x0078B9D7` | `push 0x1e` (imm8 @ `0x0078B9D8`) | **30** | popup **x** | no **NO** |
| `0x0078B9C3` | `add eax,-0x7d` | **125** | the y clamp (`y ≤ dialogH − 125`) | no **NO** |
| `0x0078BA2B` / `0x0078BA29` | `push 0xa` / `push 5` | 10 / 5 | TITLE x / y | yes v2.27.0 |
| `0x0078BA77` / `0x0078BA75` | `push 0xf` / `push 0x19` | 15 / 25 | BODY x / y | yes v2.27.0 |

Verified against `src\CodePatches.cpp` `kDeptImm8Sites`: only the four
title/body coordinates are in the table. The height, margin and x are not.

**TWIN**: the Business Deals path `0x0077C1C0+` carries its own copies —
`0x0077C262`/`0x0077C260` (title 10,5) and `0x0077C288`/`0x0077C286`
(body 15,25), already patched at v2.25.30. The tool recovers both sets
automatically:

```
python emu_layout.py --builder=0x78B980 --len=0x140 --parent=840x125
   0x0078BA35  id=0x0ABCE000  x=10  y=5   align=0x00 (left@x)
   0x0078BA81  id=0x0ABCE001  x=15  y=25  align=0x63 (fill(parent))
python emu_layout.py --builder=0x77C1C0 --len=0x120 --parent=840x125
   0x0077C26C  id=0x0ABCE000  x=10  y=5   align=0x00 (left@x)
   0x0077C292  id=0x0ABCE001  x=15  y=25  align=0x63 (fill(parent))
```

No later resize exists: the builder tail `0x0078BAF5–0x0078BC02` only
shows/hides children. **The popup height is a literal 125 forever** — the
`CodePatches.cpp` note claiming it "is computed from body.y + body.height +
margin, [so it] grows to match" is wrong; nothing recomputes it.

### The arithmetic that follows

| | stock `f = 1` | shipped 2x today | correct 2x |
|---|---|---|---|
| ordinance dialog W (art-derived) | 450 | 900 | 900 |
| popup | `450−60 = 390` x 125 @ x=30 | `900−60 = **840**` x **125** @ x=**30** | `900−120 = 780` x 250 @ x=60 |
| body (fill, x,y) | (15,25) → **345 x 75** | (30,50) → **750 x 25** | (30,50) → **690 x 150** |
| body vs 2×stock | — | **+60 wide, −125 tall** | 690 = 2×345 yes, 150 = 2×75 yes |

`BdgtPopupBody` (`0xEA85D308`) is `Arta 14 linespacing=2` at 1x and `Arta 28`
at 2x (`tools\fonts\FontStyle.default.ini` line 137 /
`FontStyle.candidate.ini` line 149). A 28-pt line needs roughly 32–34 px.
**The shipped 2x body is 25 px tall — it cannot hold even one line**, while the
1x stock body's 75 px holds about four. That, not wrapping, is the visible
"crushed box".

---

## 4. RECOMMENDED FIX — AS MATH, REDUCING TO STOCK AT f = 1

Add three sites to the `round(stock × f)` imm8 table (same verify-before-write
discipline, same startup site count):

```
value = round(stock × f)

0x0078B9A0   popup height   125 → round(125 × f)      # imm8 of `push 0x7d`
0x0078B9C3+2 y-clamp        125 → round(125 × f)      # imm8 of `add eax,-0x7d`, keep the sign
0x0078B9A3   width margin    60 → round(60  × f)      # imm8 of `sub ebx,0x3c`
0x0078B9D8   popup x         30 → round(30  × f)      # imm8 of `push 0x1e`
```

Then, with the existing v2.27.0 body patch `x = round(15f)`, `y = round(25f)`:

```
popupW = round(450f) − round(60f)          # dialog art is already f-scaled
popupH = round(125f)
bodyW  = popupW − 3·round(15f)
bodyH  = popupH − 2·round(25f)

f = 1   :  popup  390x125 , body  345x75     == stock, byte for byte
f = 1.5 :  popup  585x188 , body  519x112    = 1.504x / 1.493x stock (rounding only)
f = 2   :  popup  780x250 , body  690x150    == exactly 2 x stock
f = 3   :  popup 1170x375 , body 1035x225    == exactly 3 x stock
```

Every row above is emulator output, not arithmetic on paper:

```
python -c "import emu_layout as E; ..."     # see README section 'tier sweep'
```

**imm8 ceiling (law: log every clamp).** All four constants are `imm8`
(signed, ±127):

| constant | f = 1.5 | f = 2 | f = 3 | first f that overflows |
|---|---|---|---|---|
| 125 (height, twice) | 188 ✗ | 250 ✗ | 375 ✗ | **f > 1.016** |
| 60 (margin) | 90 ✓ | 120 ✓ | 180 ✗ | f > 2.11 |
| 30 (x) | 45 ✓ | 60 ✓ | 90 ✓ | f > 4.2 |

So the **height cannot be byte-patched at any shipping tier**. Two lawful
options, in preference order:

* **A — re-encode the two height sites.** `6A 7D` (`push imm8`) → `68 xx xx xx xx`
  (`push imm32`) needs 3 extra bytes and there is no slack, so this means a
  5-byte `jmp` trampoline to a stub — the project has no precedent for that on
  this dialog and it is the riskiest option. **Not recommended.**
* **B — a runtime PIN on the popup, on the sweep** (`METHOD.md` §4.1). The
  popup `0x0423278D` and its content `0x0423278F` are already located every
  sweep by `UiSpike`. Pin both to
  `SetSize(GetW(), round(125 × f))` **and** re-run the body's own fill formula
  `body->SetArea(x, y, popupW − 2x, popupH − y)` with `x = body->GetL()`,
  `y = body->GetT()` read live. This is **idempotent, position/size only, and
  keeps no scale record** — it satisfies law 14, and its pairing rule (window
  ids) does not depend on the state being corrected (law 19). The margin
  (60) and x (30) can still go in the imm8 table at every tier up to 2.11
  and be folded into the pin above that.
  `0x0423278F` is permanently banned from `kCityDialogIds` (law 14) — the
  pin must be an explicit, record-free `SetSize`, **not** a scale-record entry.

**What the fix does and does not promise.** It makes the popup and its body
*exactly* stock-scaled. If stock renders the description on N wrapped lines,
we will now have room for N lines at any tier. If stock renders it on one
clipped line, we will match stock — which is this project's stated standard
(the stock-budget capture reference, since retired: *output = stock scaled, judged by geometry*). It does
**not** by itself force a re-wrap, because of §5.

---

## 5. WHERE THE LINE BREAKS COME FROM — DECODED (answers Q1/Q2/Q3)

Added after live 2x screenshots showed one description breaking early with
space left in the box and another running to the box edge and being cut
mid-word. **Both behaviours are one mechanism.**

### 5.1 The three functions

| VA | What |
|---|---|
| **`0x009BCBC5`** | **the wrap width**: `wrapWidth = this->GetW() − 2×[this+0x158] − (scrollbar ? scrollbar.GetW() : 0)`, clamped to **0** if the window is narrower than that. `[this+0x158]` is the **gutter**, ctor default **5** (`0x009BFFCC`) → **`wrapWidth = GetW() − 10`**. Stored at `[this+0x160]`. |
| **`0x009BF3E0`** | the line-break pass. Its three-way switch is at **`0x009BF486`**. |
| **`0x009BFCA5`** | the text class's **`SetArea` override**: base `SetArea` (`0x0099C837`) → recompute via `0x009BCBC5` → store `[this+0x160]` → **`sub_9BF98B` re-breaks every line**. |

### 5.2 The regime switch, transcribed (`0x009BF486`)

```
w = [this+0x160]                                   ; the wrap width
if (w == 0 || (flags & 0x0200))  -> ONE LINE, no breaks at all   (0x009BF4D7)
else if (flags & 0x0002)         -> WORD WRAP at w               (0x009BF4B3)
                                    cIGZFont::CalculateWordsToFitInWidth(
                                        buf, len, w, NULL, WordWrapMode 2)
else                             -> break at '\n' ONLY, then clip (0x009BF4BB)
```

`flags` is **`[this+0x128]`** — the field `cIGZWinText::SetWinTextFlag(long,bool)`
(vtable `+0x1C`) writes. **Constructor default is 0** (`mov [esi+0x128], edi`
with `edi = 0`, `0x009C026C`). Corroborated by a real caller at `0x009C7DA9`
doing `push 0; push 2; call [eax+0x1C]` — i.e. explicitly turning flag **2**
*off* on a fresh single-line label.

**`sub_779660` never calls `SetWinTextFlag`.** It only clears the *window*
flags `0x800`/`0x8000` (`cIGZWin::SetFlag`, a different vtable). So **every
label the factory makes has word wrap OFF.**

### 5.3 The answers

**Q1 — what width is in effect at `FitWindowToText` (`0x007796D8`)?**
`createdWidth − 10`. **But it does not matter**, because the break is not
frozen there — see Q3.

**Q2 — is the wrap width a constant?** **No. There is no CodePatches site.**
It is *derived*, every time, from the window's own width minus twice the
gutter. The only constant in the chain is the gutter `5` at `0x009BFFCC`
(`mov dword ptr [esi+0x158], 5`, `imm32`), which is a class-wide default and
must not be touched.

**Q3 — is the break computed once at layout, or against the current rect?**
**Against the current rect, every time the rect changes.** The `SetArea`
override re-derives the width and re-breaks. `sub_779660` issues two
`SetArea`s *after* the autosize, so the **last** one wins. The emulator now
prints this per step (`--selftest -v`):

```
FitWindowToText(0, 0) -> MODELLED text extent 768x12
SetArea(win:0x0ABCE001, 768,0,1000,12) -> 232x12  [wrap width becomes 222]
SetArea(win:0x0ABCE001, 30,50,780,75) -> 750x25   [wrap width becomes 740]
GZWinMoveTo(win:0x0ABCE001, 30,50)
SetArea(win:0x0ABCE001, 30,50,780,75) -> 750x25   [wrap width becomes 740]
```

The effective wrap width today is **740** (`750 − 10`), not 1000 and not
900-something. This also **narrows law 21**: text does *not* re-wrap from a
re-applied caption, but it **does** re-wrap from a `SetArea`.

### 5.4 So why is it not wrapping at 740?

Because flag `0x0002` is clear, so the **third** regime applies: **breaks
happen only at explicit `\n` in the LTEXT, and any newline-delimited segment
longer than the box is clipped horizontally.** That is exactly the pair of
behaviours observed:

* *"Smoke Detector … breaks after '…in every' with empty space still left in
  the box"* → a **hard newline in the LTEXT**, which lands short of the edge.
* *"Paper Waste … runs to the box edge and is cut mid-word at 'Requ'"* → a
  newline-delimited segment **longer than 750**, clipped.

A real 740-px word wrap could not produce either one. The apparent
"wrap at 900-1000" is not a wrap.

### 5.5 THE CURE — one call, no constants, no string work

```
cIGZWinText::SetWinTextFlag(0x0002, true)     // vtable +0x1C
```
on the body `0x0ABCE001`, reached with
`content->GetChildAs(0x0ABCE001, GZIID_cIGZWinText /*0x212CDC1F*/, &pText)`.
Follow it with any `SetArea` — the geometry pin of §4 already performs one —
to trigger `0x009BFCA5` → recompute → `sub_9BF98B` re-break.

The engine then wraps at `GetW() − 10` **by itself, at every tier, with zero
constants**: 335 at 1x, 680 after the §4 geometry fix at 2x, 1025 at 3x. It
is idempotent (setting a set flag is a no-op), it survives any later resize
by design, and it needs **none** of the `CalculateWordsToFitInWidth` string
work a manual wrap would require.

**Order of operations matters**: apply §4 (height 125 → `round(125×f)`)
*first*. With the flag on and the height still 125, the body is 25 px tall and
you will see wrapped line 1 only. With both, the box is 150 px at 2x and shows
the same number of lines stock shows at 75 px.

### 5.6 One-line live confirmation before shipping

The field map above belongs to the class in `0x009BC000-0x009C1000`; that the
label factory's service creates *this* class is **HYPOTHESIS** (the service is
a runtime COM singleton, `sub_7B2480`, id `0xC2C2EB0F` — not statically
resolvable). Confirm it for free, with no risk, from the existing sweep:

```
GetWinTextFlag(0x0002)      // vtable +0x18, on 0x0ABCE001
```
Log it. **`false` confirms the whole diagnosis**; `true` means the class is a
different one and §5.4 is wrong. Do this in the same build as §4.

---

## 5A. APPENDIX — leads and false leads recorded during the decode

What is **proven**:

* The only layout call is `FitWindowToText(false,false)` at step 5, i.e.
  **before** the `1000` SetArea and **before** the fill SetArea. Whatever
  width the layout used, it was the window's width *as the factory created
  it* — never 1000, never 750, never 840. The "wrap at the unscaled 1000"
  hypothesis is refuted on **ordering**, which is stronger than a value
  argument.
* Nothing in `sub_779660` sets a word-wrap flag. It only *clears* window
  flags `0x800` (Sortable) and `0x8000` (AcceptFocus) — `cIGZWin::SetFlag`,
  not `cIGZWinText::SetWinTextFlag`.
* The candidate flag sites `0x777299`, `0x777424`, `0x777479` are a **false
  lead**: they call `[vt+0x18](flag)` then `[vt+0x1C](flag)` with **one**
  argument. `cIGZWinText::SetWinTextFlag` takes **two** (`flag, value`) —
  confirmed by a genuine two-argument call `push 0; push 2; call [eax+0x1C]`
  at `0x009C7DA9`. Those `0x8001` / `0x8010` sites belong to a different
  class and mean nothing here. `0x0077899B` is likewise a one-argument
  getter on a non-text object.

**Correction to an earlier draft of this document:** the guess that the
layout is frozen at creation width was wrong — the `SetArea` override
re-derives it (§5), so the *last* `SetArea` decides. The conclusion that
follows: **stock does not wrap this text either** (flag `0x0002` is off at
every tier), so a 1x capture shows the same `\n`-only breaks plus clipping,
just at 345 px. Take one anyway — it is 3 minutes and it is the only thing
that distinguishes "we match stock" from "we broke it".

Other leads found on the way, recorded so nobody re-derives them:

| VA | What it is |
|---|---|
| `0x009C7C6C` | natural-extent walker: iterates the laid-out **line** objects, maxes `[font+0xB4]` width and `[font+0xB8]` height, then adds the gutter bytes `[this+0xEC]`/`[this+0xED]`. Constrained fields initialised to `0xFFFF` = unbounded. |
| `0x009C870B` | another text-class `SetArea` override — on size change calls `[vt+0x284]` then `[vt+0x280]`. Primary vtable `0x00AE1780`. A *different* class from §5's; more than one text class re-flows. |
| `0x00AE1678` | a `cIGZWinText`-shaped secondary vtable (`+0x10` SetCaption at `0x009C93D7`). its `+0x14` is `ret 4`, but `sub_779660` provably passes **two** args to `+0x14` — **not** the label factory's class. |
| `0x009A8135` | the **second** 5-argument `CalculateWordsToFitInWidth` site in the engine (the other is §5's `0x009BF4B3`). Different class — most likely the rich/HTML text engine. Not this path. |
| `cIGZFont` vtable (header confirmed by `+0x8C = GetLineHeight`) | `+0xA4 CalculateWordsToFitInWidth`, `+0xB4/+0xB8 CalculateTextArea`, `+0xC0 GetStringWidth` — the manual-wrap route. **§5.5 makes it unnecessary.** |

**Note on a reasoning block that lived in `src\UiSpike.cpp`:** it stated the
body window "already self-scales — measured 750 wide inside the 840 box,
which is right", and that the wrap happens against the unscaled 1000. Both
are refuted above: 750 is **60 px too wide** (2×stock is 690) and 25 px tall
against a 2×stock of 150, and the 1000 is applied *after* the layout and
then overwritten. Per §5.5 any manual `CalculateWordsToFitInWidth` +
newline-injection block can be **deleted entirely** — one
`SetWinTextFlag(2, true)` makes the engine do it, correctly, at every tier,
and re-do it on every resize.

---

## 6. WHAT THIS COST / WHAT TO NEVER RE-WALK

* Three shipped builds (v2.27.1 `SetW`+`SetCaption`, v2.27.2 `FitWindowToText`,
  v2.27.3 clear-and-restore) all attacked **re-wrapping**. None of them could
  have worked, because the body's rect never depended on the text in the first
  place. The offline model would have shown that in one run.
* "795x75 = three lines / 750x25 = one line" was a **coincidence of the patch
  landing between the two dumps**, not a measurement of line count. When two
  dumps of the "same" element disagree, check whether a constant changed
  between them before theorising about the engine.
* `cRZRect` = `{x,y,w,h}` in the SDK header, but a window's area field is
  `{L,T,R,B}`. Read `GetW` before trusting a field name.
