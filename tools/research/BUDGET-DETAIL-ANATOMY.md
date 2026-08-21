# THE BUDGET DETAIL DIALOGS — DECODED ENGINE REFERENCE

Decoded by disassembly and live measurement against a true-stock 1024x768
reference. The target in every case is stock geometry scaled by f, judged by
geometry and arithmetic rather than by pixel counting.

## 1. THE LAYOUT ENGINE

One shared transient `0x0423278F` (exe-built; no .UI script exists — all
271 layout scripts checked, none reference it), rebuilt per department by
per-department builder functions. Its geometry comes from three primitives:

- **`sub_77A390`** (band factory): loads PNG {0x856DDBAC, 0x46A006B0, inst},
  creates an anonymous GZWinBMP sized FROM THE ART, returns art height.
- **`sub_77A6F0`** (the vertical band STACKER): y-cursor at [builder+0x80];
  stacks title band → group-1 header band → group-1 slabs (one slab art =
  TWO rows) → group-1 cap → group-2 header band → group-2 slabs → cap →
  footer, x=0, each y = cursor, advancing by each art's own height. The
  dialog frame W/H = the art sums (SetSize at the stacker tail + recentre).
  **Dialog size is ART-derived, not font-derived.**
- **`sub_779660`** (label factory): (parent, id, x, y, text, align, styleId,
  R,G,B) → autosized text window, then a `SetArea` carrying the constant 1000
  (`push 0x3e8` @0x77971A); align 0 = left at x, align 6 = RIGHT EDGE lands on
  x, 0x63 = FILL. No internal cursor — y always supplied by the caller. That
  1000 is not a wrap width: it is applied *before* alignment and, in the 0x63
  branch, immediately overwritten by `SetArea(x, y, parentW−2x, parentH−y)` —
  see §POPUP P3. Wrap width is never a constant here; it is `GetW()−10`,
  recomputed per `SetArea` (`SC4-UI-ENGINE.md` §5.0).

Metric source `0x7881DE`: builder.contentWidth = width(slab art),
builder.rowPitch = height(slab art)/2 — so with 2x art EVERYTHING self-scales.
Row cursors: [builder+0x98] (group 1), [builder+0x9C] (group 2), advanced by
rowPitch.

**Art families (band sets, one per dialog family):**

| Family | Stock width | Dialogs |
|---|---|---|
| 0x140155F0-F7 | 450 | Ordinances |
| 0x140155D0-D7 | 500 | slider departments + Neighbor Deals (2 consumers) |
| 0x2BFEB0C7-CF | 650 | Transportation |

0x140155D4 (group-2 header band) IS the pink box top cap: 6px blue-grey,
2px border, 36px pink, 2px grey (at 2x). The "Monthly Expense" header text
sits ON it. With the shipped 2x art the whole stack is exactly stock×2
(58/46/72/82/80 reproduce every measured rect incl. the 1000x554 dialog).
**The band/slab GEOMETRY is correct at every tier; the stacker takes no
patch.** Specifically do not touch `add edx,eax` 0x77A7C7 — noping it
corrupts the group-2 cursor too.

## 2. ELEMENT IDENTIFICATIONS

- Ids 0x551-0x554 (128x20, art 140155CB/CC) are **the per-section SCROLL
  ARROWS** (exe ids 0x451-0x454, +0x100 at runtime; 4-state strips,
  CB = up, CC = down, cell 16x10 at 1x). Anchored `x = W-33` (1x const), y from
  rowPitch (self-scales). Stock ink = sectionRight−17. The 14
  `sub r32,0x21` anchor sites carry 33f.
- The 16x36 element at x=339 in slider rows is the slider track's vertical
  RULE, art 0x140155C8 (8x18). NOTCHPIN re-seats it proportionally on the live
  track — keep.
- In Neighbor Deals, ids 0xABCE2xx are combo BACKING PLATES (art 0x140155B8,
  138x18 stock, shipped 2x), not arrows. The combo's drop arrow is an
  INTERNAL child of GZWinCombo (id 0x53430D98), positioned by the class from
  the combo's area — it moves automatically when the combo resizes.
- The region 0x77F5xx-0x7815xx is the NEIGHBOR DEALS builder's 13 static row
  blocks (builder spans 0x77E600-0x781C8E; 0x781C90+ is its refresh/updater,
  creates nothing).
- **GROUP-1/GROUP-2 TWINS:** every slider-department create exists twice
  (the group-1 branch is dead for these departments — group-1 rows = 0). The
  LIVE "Monthly Expense" x is `0x78898B` (create 0x788991), estimate margin
  `0x7889C0`; the 0x7883DD/0x788416 pair is the DEAD twin (patched too,
  harmlessly). When a patched site does nothing, look for its twin.

## 3. WHO OWNS EACH QUANTITY

| Regime | Elements | Behavior at tier f |
|---|---|---|
| ART-derived | bands/slabs (dialog W/H!), rowPitch, arrow/backing/track windows, strips, checkboxes | self-scales wherever the shipped dats carry f-scaled art |
| FONT-derived | text extents, content-fit heights in Ordinances-style flows | self-scales via FontStyle |
| EXE consts (in-memory patched per launch) | every column x, button/box sizes, right margins (W−38), arrow anchors (W−33), title/header x/y | CodePatches tables, round(stock×f), verify-before-write |
| Class-internal (unpatchable encodings) | combo width 120 (`lea disp8`, max 127) | runtime width pin (UiSpike, idempotent, no record) |

## 4. THE PATCH SET

Buttons 360x60+anchors; Ordinances insets (18→36f, 34→68f, names 68→127cap);
slider-dept columns (strips 36, names 96, counts 516, slider 520 w127cap,
Subtotal 500) + LIVE header pair (36 / W−76) + hidden item-slider twin;
Business box 600x127+X+texts; scroll arrows W−66 (14 sites); Neighbor Deals
full column set (labels 36, values 436, backing 412, combos 436, right
W−76, title 40/16, header 36) + combo width pin 240. All values
round(stock×f); imm8/disp8 ceilings logged (slider w, ordinance names,
combo width via pin instead).

## 5. STANDING FACTS

- The D-series band arts have a second consumer (`0x77F596` = the Neighbor
  Deals stack) — any art change hits both families.
- `CustomBudgetDepartments.dll` exists in Plugins and can alter row counts;
  the row-count clamp to 9 at `0x77C829` is what keeps the height formula
  bounded under it.

## 6. RULED OUT BY DISASSEMBLY

sub_77A080/77A120 = vector copies; sub_77C3C0/77C420 = vector erase;
sub_77D7E0 = vector insert; [obj+0x68] at 0x7772xx = 3-colour label class
(NOT scroll state); vscrollimage .ui keys unused here; 0x1441624A-C =
file-browser icons; no literal 339/0x153 exists in the exe (combo-derived).

---

# §POPUP — THE ORDINANCE DESCRIPTION POPUP

Two things govern this popup: the BOX constants, and one text flag bit.

## P1. The window tree (live)

```
Ordinances dialog 0x0423278F (900 wide)
└── 0x0423278D  popup            (60,y 780x250 at f=2)
    ├── 0x00000168 close-X
    ├── 0x00000484 backdrop
    └── 0x0423278F content        (0,0 780x250)
        ├── 0x0ABCE000 TITLE      align 0    (push 0    @0x78BA1D)
        └── 0x0ABCE001 BODY       align 0x63 (push 0x63 @0x78BA69)
```

The SAME window serves the Business Deals empty box via a DIFFERENT code
path (0x77C26C/0x77C292 vs the ordinance path 0x78BA35/0x78BA81), each with
its own copies of the constants. Concretely it is TWO builders with
different stock heights: `sub_78B120` (ordinance description popup, stock H
**125**, backdrop ids `0x384`/`0x484`, host = the Ordinances dialog) and
`sub_77BEC0` (empty-ledger box, stock H **100**, backdrop ids `0x385`/`0x485`,
close-X `0xCC`/`0x1CC`, and the host **is** the box itself — a top-level
600x127 window). The POPBOX pin therefore carries both heights, not one;
applying the ordinance twin's 125 to the empty-ledger twin puts the close-X
above the host rect where the hit walk never descends. The empty-ledger twin
takes a five-window coupled resize — host + popup + content + `0x485` +
`0x385` — using `round(100*f)`. The WinProc closes this popup on ESC / ENTER /
F4 (`0x78BCFE`).

## P2. THE TWO GOVERNING MECHANISMS

**(a) The box constants.** Verified by disassembly and by an independent
offline pass over the binary:

| VA | encoding | stock | note |
|---|---|---|---|
| 0x78B99F, 0x78B9B0, 0x78BACE, 0x78BAEA | `push 0x7d` | 125 | popup height — **four** twin sites, two re-applied per open |
| 0x78B9A1 | `sub ebx,0x3c` | 60 | right margin → width = dialogW − 60 |
| 0x78B9C3 | `add eax,-0x7d` | −125 | y clamp |
| 0x78B9D7 | `push 0x1e` | 30 | popup x |

Left alone at 2x these give 840x125 where `round(stock×f)` is 780x250. The
body, sized by the align-0x63 FILL branch as `parentH − 2y`, then lands
**25 px tall** — less than one line of Arta 28. 250 and −250 exceed the imm8
ceiling, so the height + clamp are a **sweep pin** (POPBOX) and the margin +
x are byte patches.

**(b) The text regime.** Stock leaves `flags & 0x0002` clear, so the body
breaks only at hard newlines and clips the rest. The full mechanism, and the
general rule for every `GZWinText`, lives in **`SC4-UI-ENGINE.md` §5.0** —
that is the canonical home; it is not duplicated here.

Cure: `SetWinTextFlag(0x0002, true)` then resize (the resize is the trigger).
The engine then wraps at `GetW()−10` at every tier: 335 @1x, 680 @2x,
1025 @3x.

## P3. THE FILL BRANCH (align 0x63) — general to every filled label

`sub_779660`'s 0x63 branch (0x779793-0x7797D2) calls
`SetArea(x, y, parentW − 2x, parentH − y)` — it **overwrites all four edges
and discards the text extent**. So for ANY string in ANY font:

    body W = parentW − 3x        body H = parentH − 2y

This reproduces every measured rect: 795x75 = body at (15,25) in an 840x125
box; 750x25 = the same body at (30,50). Growing the parent later does NOT
re-run this; the pin must re-apply the formula itself.

## P4. APPROACHES THAT CANNOT WORK

| Attempt | Why it cannot work |
|---|---|
| `SetW` + `SetCaption(same)` | caption unchanged → text object early-outs |
| `FitWindowToText(false,true)` | sizes the window to the text, not the text to the window |
| `SetCaption("")` then restore | re-layout happens, but the newline-only regime has no wrap to perform |
| measure with `cIGZFontSys` + inject `\n` | **overload-reversal trap** — 3 `FontAcquire` overloads before `EnumerateFontInfo`; calls hit wrong vtable slots (null, then a swallowed fault). See `SC4-UI-ENGINE.md` §5.0 warning |

**The `push 0x3e8` (1000) at 0x77971A is NOT a wrap width** — it is applied
*after* the only layout call and then overwritten by the fill branch. That is
settled on ORDERING, which no value argument could have settled.

## P5. THE MEASURED TEXT EXTENT

The natural, unwrapped extent of the ordinance body text measures
**4,225-6,166 px** — a screenshot reading of ~920 px is off by 6x, and it is
what makes "widen the box" look plausible. Widening cannot reach that extent;
wrapping is the only cure.

A stock capture of this popup is not load-bearing: the geometry reduces to
stock at f=1 by construction, so the popup is correct without one.

## THE CREATE SIZE vs THE FINAL SIZE

The frame is built BORN VISIBLE at a create size and only reaches its final
size at the stacker tail, so the create size is on screen for real frames —
it is not an internal detail. Measured live on 0x0423278F over three opens,
identical:

    (0,0 0x0)         -> (975,736 450x127)    built
    (975,736 450x127) -> (975,736 450x150)    final

The create size comes from `0x77BEC0`'s five `push imm8 h; push imm32 w` sites
(CONSTANT-MAP.md). Because the height is a **push imm8**, a naive patch cannot
express 100*f for any shipped tier (150/200/300 all exceed 127) — and clamping
it produces a visible open-jump on every open. It is widened through a
per-site jmp-to-cave, so create == final and nothing corrects the window
after it is shown.

**Law:** patching these constants means patching WIDTH AND HEIGHT TOGETHER,
or refusing both. A scaled width with a clamped height is worse than no patch
at all: it looks like a working fix and jumps on every open.
