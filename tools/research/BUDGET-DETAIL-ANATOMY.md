# THE BUDGET DETAIL DIALOGS — DECODED ENGINE REFERENCE (2026-07-30, v2.26.0)

> **Level 1 of the instruction hierarchy** (`METHOD.md` §1): this file is to
> be re-read and QUOTED before any budget-dialog fix, and extended in the
> same session with anything new. §POPUP's failed-attempts table exists so no
> attempt is made twice.

Fully decoded by three disassembly passes + live MWKID/BHDR measurement +
the true-stock 1024x768 reference (`_tests\captures\stock-budget\`,
STOCK-REFERENCE.md carries the standing directive: output = stock scaled
by f, judged by GEOMETRY/MATH, never pixel counting). Supersedes the
2026-07-30 morning draft entirely (several of its identifications were
wrong — corrections flagged ⚠ below).

## 1. THE LAYOUT ENGINE

One shared transient `0x0423278F` (exe-built; NO .UI script exists — all
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
  x, 0x63 = FILL. No internal cursor — y always supplied by the caller.
  ⚠ **CORRECTED 2026-07-30 (v2.28.4):** the earlier reading of that 1000 as a
  wrap width ("widened to 1000−textW") was WRONG and cost four builds. It is
  applied *before* alignment and, in the 0x63 branch, immediately overwritten
  by `SetArea(x, y, parentW−2x, parentH−y)` — see §POPUP P3. Wrap width is
  never a constant here; it is `GetW()−10`, recomputed per `SetArea`
  (`SC4-UI-ENGINE.md` §5.0).

Metric source `0x7881DE`: builder.contentWidth = width(slab art),
builder.rowPitch = height(slab art)/2 — so with 2x art EVERYTHING self-scales.
Row cursors: [builder+0x98] (group 1), [builder+0x9C] (group 2), advanced by
rowPitch.

**Art families (band sets, one per dialog family):**
| Family | Arts | Stock width | Dialogs |
|---|---|---|---|
| 0x140155F0-F7 | 450 | Ordinances |
| 0x140155D0-D7 | 500 | slider departments + Neighbor Deals (2 consumers) |
| 0x2BFEB0C7-CF | 650 | Transportation |

0x140155D4 (group-2 header band) IS the pink box top cap: 6px blue-grey,
2px border, 36px pink, 2px grey (at 2x). The "Monthly Expense" header text
sits ON it. With our 2x art the whole stack is exactly stock×2
(58/46/72/82/80 reproduce every measured rect incl. the 1000x554 dialog).
**The band/slab GEOMETRY was never broken; never patch the stacker.**
Specifically do NOT touch `add edx,eax` 0x77A7C7 — noping it corrupts the
group-2 cursor too.

## 2. ⚠ CORRECTED IDENTIFICATIONS (the morning draft was wrong)

- "Subtotal plates 0x551-0x554 (128x20, art 140155CB/CC)" → **the per-section
  SCROLL ARROWS** (exe ids 0x451-0x454 +0x100 at runtime; 4-state strips,
  CB=▲ CC=▼, cell 16x10 at 1x). Anchored `x = W-33` (1x const), y from
  rowPitch (self-scales). Stock ink = sectionRight−17. Fixed v2.26.0:
  the 14 `sub r32,0x21` anchor sites → 33f.
- The 16x36 element at x=339 in slider rows ("funding notch") = the slider
  track's vertical RULE, art 0x140155C8 (8x18). NOTCHPIN re-seats it
  proportionally on the live track — keep.
- In Neighbor Deals, ids 0xABCE2xx are combo BACKING PLATES (art 0x140155B8,
  138x18 stock, shipped 2x), NOT arrows. The combo's drop arrow is an
  INTERNAL child of GZWinCombo (id 0x53430D98), positioned by the class from
  the combo's area — it moves automatically when the combo resizes.
- The region 0x77F5xx-0x7815xx is NOT a "Taxes builder" — it is the NEIGHBOR
  DEALS builder's 13 static row blocks (builder spans 0x77E600-0x781C8E;
  0x781C90+ is its refresh/updater, creates nothing).
- **GROUP-1/GROUP-2 TWINS:** every slider-department create exists twice
  (group-1 branch is dead for these departments — group-1 rows = 0). The
  LIVE "Monthly Expense" x is `0x78898B` (create 0x788991), estimate margin
  `0x7889C0`; the 0x7883DD/0x788416 pair is the DEAD twin (patched too,
  harmlessly). When a patched site "does nothing", look for its twin.

## 3. WHO OWNS EACH QUANTITY (final)

| Regime | Elements | Behavior at tier f |
|---|---|---|
| ART-derived | bands/slabs (dialog W/H!), rowPitch, arrow/backing/track windows, strips, checkboxes | self-scales wherever our dats ship f-scaled art |
| FONT-derived | text extents, content-fit heights in Ordinances-style flows | self-scales via FontStyle |
| EXE consts (in-memory patched per launch) | every column x, button/box sizes, right margins (W−38), arrow anchors (W−33), title/header x/y | CodePatches tables, round(stock×f), verify-before-write |
| Class-internal (unpatchable encodings) | combo width 120 (`lea disp8`, max 127) | runtime width pin (UiSpike, idempotent, no record) |

## 4. THE SHIPPED FIX SET (v2.25.25 → v2.26.0)

Buttons 360x60+anchors; Ordinances insets (18→36f, 34→68f, names 68→127cap);
slider-dept columns (strips 36, names 96, counts 516, slider 520 w127cap,
Subtotal 500) + LIVE header pair (36 / W−76) + hidden item-slider twin;
Business box 600x127+X+texts; scroll arrows W−66 (14 sites); Neighbor Deals
full column set (labels 36, values 436, backing 412, combos 436, right
W−76, title 40/16, header 36) + combo width pin 240. All values
round(stock×f); imm8/disp8 ceilings logged (slider w, ordinance names,
combo width via pin instead).

## 5. OPEN

- The gray header band: engine+art say it must paint pink through the same
  plain-blit path as the slabs. The v2.25.33/34 hooks (now removed) are the
  prime suspect for the observations. JUDGE LIVE at v2.26.0 before anything
  else; if still gray, the next step is a draw trace — never geometry.
- Taxes dialog: not yet eyes-on under the family patches (shares builders/
  helpers; verify then patch residual sites the same way if flagged).
- Second consumer of the D-series band arts (0x77F596 = Neighbor Deals'
  stack) — any art change hits both families.
- CustomBudgetDepartments.dll exists in Plugins and can alter row counts.

## 6. DEAD ENDS (never re-walk)

sub_77A080/77A120 = vector copies; sub_77C3C0/77C420 = vector erase;
sub_77D7E0 = vector insert; [obj+0x68] at 0x7772xx = 3-colour label class
(NOT scroll state); vscrollimage .ui keys unused here; 0x1441624A-C =
file-browser icons; no literal 339/0x153 exists in the exe (combo-derived).

---

# §POPUP — THE ORDINANCE DESCRIPTION POPUP — SOLVED (2026-07-30, v2.28.4)

**Four fixes failed before this one. All four assumed the text was the
problem; it was the BOX, plus one flag bit.** Kept in full because the
failures are the instructive part.

## P1. The window tree (POPKID, live)

```
Ordinances dialog 0x0423278F (900 wide)
└── 0x0423278D  popup            (60,y 780x250 AFTER the fix; was 30,y 840x125)
    ├── 0x00000168 close-X
    ├── 0x00000484 backdrop
    └── 0x0423278F content        (0,0 780x250)
        ├── 0x0ABCE000 TITLE      align 0    (push 0    @0x78BA1D)
        └── 0x0ABCE001 BODY       align 0x63 (push 0x63 @0x78BA69)
```

The SAME window serves the Business Deals empty box via a DIFFERENT code
path (0x77C26C/0x77C292 vs the ordinance path 0x78BA35/0x78BA81), each with
its own copies of the constants — law 16.

## P2. THE TWO REAL CAUSES

**(a) The box was never scaled.** Its own constants, all unpatched until
v2.28.2, verified by disassembly AND by the offline census independently:

| VA | encoding | stock | note |
|---|---|---|---|
| 0x78B99F, 0x78B9B0, 0x78BACE, 0x78BAEA | `push 0x7d` | 125 | popup height — **four** twin sites, two re-applied per open |
| 0x78B9A1 | `sub ebx,0x3c` | 60 | right margin → width = dialogW − 60 |
| 0x78B9C3 | `add eax,-0x7d` | −125 | y clamp |
| 0x78B9D7 | `push 0x1e` | 30 | popup x |

At 2x that gave 840x125 where `round(stock×f)` is 780x250. The body, sized by
the align-0x63 FILL branch as `parentH − 2y`, therefore landed **25 px tall** —
less than one line of Arta 28. 250 and −250 exceed the imm8 ceiling, so the
height + clamp are a **sweep pin** (POPBOX) and the margin + x are byte
patches.

**(b) The text was in the newline-only regime.** `flags & 0x0002` was clear,
so it broke only at hard newlines and clipped the rest. Full mechanism, and
the general rule for every `GZWinText`, is now **`SC4-UI-ENGINE.md` §5.0** —
that is the canonical home; do not duplicate it here.

Cure: `SetWinTextFlag(0x0002, true)` then resize (the resize is the trigger).
Engine then wraps at `GetW()−10` at every tier: 335 @1x, 680 @2x, 1025 @3x.

## P3. THE FILL BRANCH (align 0x63) — general to every filled label

`sub_779660`'s 0x63 branch (0x779793-0x7797D2) calls
`SetArea(x, y, parentW − 2x, parentH − y)` — it **overwrites all four edges
and discards the text extent**. So for ANY string in ANY font:

    body W = parentW − 3x        body H = parentH − 2y

This reproduces every measured rect: 795x75 = body at (15,25) in an 840x125
box; 750x25 = the same body after v2.27.0 moved it to (30,50). **The
"three lines vs one line" evidence that drove three fixes was an artifact of
two dumps straddling that patch — not a wrap.** Growing the parent later does
NOT re-run this; the pin must re-apply the formula itself.

## P4. FAILED ATTEMPTS — mechanisms, so none is retried

| Ver | Attempt | Why it could never work |
|---|---|---|
| v2.27.1 | `SetW` + `SetCaption(same)` | caption unchanged → text object early-outs |
| v2.27.2 | `FitWindowToText(false,true)` | sizes the window to the text, not the text to the window |
| v2.27.3 | `SetCaption("")` then restore | re-layout happened, but regime 3 has no wrap to perform |
| v2.28.0/.1 | measure with `cIGZFontSys` + inject `\n` | **overload-reversal trap** — 3 `FontAcquire` overloads before `EnumerateFontInfo`; calls hit wrong vtable slots (null, then a swallowed fault). See ENGINE §5.0 warning |

**The `push 0x3e8` (1000) at 0x77971A is NOT a wrap width** — it is applied
*after* the only layout call and then overwritten by the fill branch.
Refuted on ORDERING, which no value argument could have settled. It was the
prime suspect in this file for a full day; that is why "quote the doc" is not
the same as "the doc is right".

## P5. WHAT THIS COST, AND THE LESSON

Four shipped builds, because the natural text width was **inferred** from
screenshots at ~920 px. Measured, it is **4,225-6,166 px** — wrong by 6x, and
it silently made "widen the box" look plausible for hours. The first build
that logged a real number ended the argument in one launch.

Stock capture of this popup: still never taken. It is no longer load-bearing
(the fix reduces to stock at f=1 by construction) but remains the cheapest
outstanding parity check — §5 procedure.

## THE CREATE SIZE vs THE FINAL SIZE (#189, 2026-08-18)

The frame is built BORN VISIBLE at a create size and only reaches its final
size at the stacker tail, so the create size is on screen for real frames -
it is not an internal detail. MEASURED live on 0x0423278F, three opens,
identical (BUDGETTICK):

    (0,0 0x0)         -> (975,736 450x127)    built
    (975,736 450x127) -> (975,736 450x150)    final

The create size comes from `0x77BEC0`'s five `push imm8 h; push imm32 w` sites
(CONSTANT-MAP.md). Because the height is a **push imm8**, a naive patch cannot
express 100*f for any shipped tier (150/200/300 all exceed 127) - and clamping
it is what produced the visible open-jump for months. It is now widened through
a per-site jmp-to-cave, so create == final and nothing corrects the window
after it is shown.

⚠ If you touch these constants, patch WIDTH AND HEIGHT TOGETHER or refuse
both. A scaled width with a clamped height is worse than no patch at all: it
looks like a working fix and jumps on every open.
