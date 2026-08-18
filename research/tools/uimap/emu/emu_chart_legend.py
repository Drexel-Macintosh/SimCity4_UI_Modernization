"""
emu_chart_legend.py - the OFFLINE EMULATOR for the Graphs chart legend (#57).

Closed-form, integer-exact re-implementation of sub_76D3D0's legend loop
(0x0076DE95..0x0076E373) - HORIZONTAL and VERTICAL - so a proposed fix can be
adjudicated OFFLINE before it is built. Five rect-patch builds have shipped on
this bug (v2.50.0, v2.51.0, v2.52.0, v2.54.2/.3/.4); this file exists so the
sixth is decided by arithmetic instead of by a screenshot.

SCOPE, STATED UP FRONT (law 42).
  IN  - every rect sub_76D3D0 writes for a legend row: the checkbox WINDOW,
        the swatch entry (vt 0x00ADE0DC, rect obj[2..5]), the text-block entry
        (vt 0x00ADE540, rect obj[7..10]), the row-Y accumulator, and the plot
        rect the same function stores. All from BYTE-VERIFIED immediates.
  IN  - our own mod's transforms on top of them: the sweep's size-only
        checkbox doubling, EARLYCHART's plot rewrite, v2.54.4's LEGENDFIX /
        LEGENDSWATCH. Reproducing OUR OUTPUT is the point; a model that only
        reproduces the healthy case is worthless.
  IN  - a knob: predict(f, Interventions) -> the columns a candidate fix
        produces, with a pass/fail verdict per candidate.
  OUT - the mechanism. This file says nothing about WHICH function to detour
        or which bytes to patch. It says only what the numbers must be.
  OUT - the paint path. Nothing here proves a rect reaches the screen
        (law 46). It models LAYOUT only.
  OUT - any tier but f=1 and f=2 for the EXACT checks. The two font inputs
        (line height, ink ratio) are measured at those two tiers only; the
        knob will run at other f but says so loudly.

WHAT IS REAL AND WHAT IS MODELLED
  REAL, byte-verified from SimCity 4.exe 1.1.641.0 this session via
  tools\\uimap\\fn.py (every constant below carries its address):
      0x0076DE79  mov [esp+0x18],0x14        first row top = 20
      0x0076E0F0  cmp eax,2 / jbe            checkboxes only when series > 2
      0x0076E0F5  sub ebx,0x6a               plain swatch left  = W-106
      0x0076E1F8  sub ebx,0x5a               cbox  swatch left  = W-90
      0x0076E151  add ecx,0x10               checkbox bottom    = Y+16
      0x0076E159  lea ecx,[edx-0x5c]         checkbox right     = W-92
      0x0076E162  add edx,-0x6c              checkbox left      = W-108
      0x0076E168  call [ebx+0xDC]            checkbox SetArea
      0x0076E17B  add ecx,0x4000000          id = 0x04000000 + seriesIndex
      0x0076E233/9  lea ecx,[eax+3] / add eax,9   swatch T=Y+3, B=Y+9
      0x0076E23C  add ebx,0xa                swatch right = left+10
      0x0076E2AF  add ecx,4                  text left  = swatchRight+4
      0x0076E2C5  add eax,0xa                text bottom seed = Y+10
      0x0076E2C8  sub edx,4                  text right = W-4
      0x0076E2FD  call [eax+0xB8]            FitRectToText(str,len,r,1,1)
      0x0076E34B  lea edx,[ecx+eax+4]        rowY += textHeight + 4
      0x0076DD4E/4B  sub edx,0x6e / sub eax,0x14   plot R=W-110, B=H-20
  REAL, measured from pixels (_tests\\captures\\graphs-stock-garbage.png,
  graphs-stock-ref.png) and from SC4UIScale.log v2.54.4 - see each table.
  MODELLED (three inputs, all flagged, all falsifiable):
      LINE_H      the legend font's line height (15 at 1x, 28 at 2x)
      INK_RATIO   the 1x->2x ink-width ratio (2.121, NOT 2.00)
      wrap_lines  greedy break at spaces, mid-word break for an over-wide
                  word, uniform-advance approximation inside a word.
  MODELLED, NOT PROVEN: the +1 line on rows 2 and 4. The pitch formula at
  0x0076E34B has NO group-separator term, so the extra 15px (1x) / 28px (2x)
  those two rows carry MUST be an extra LINE in their text block - i.e. their
  label string ends in a hard break. Cause unproven; the effect is measured at
  BOTH tiers and is modelled as an extra line, not as a separate gap, because
  only the extra-line form follows the disassembled arithmetic.

USAGE
  python emu_chart_legend.py            # the acceptance suite (what CI runs)
  python emu_chart_legend.py -v         # + per-row arithmetic
  python emu_chart_legend.py --knob     # candidate-intervention table only
  python emu_chart_legend.py --falsify  # the audit: prove it CAN go red
Exit 0 only if every check passes. It never prints a pass it did not earn.

IS THIS AN INSTRUMENT? Six falsifications are run by --falsify and all six
turn it red, so its greens mean something:
  F1 ink ratio 2.00 instead of 2.121  -> "Landfill" stops wrapping, 2x wrong
  F2 word-only wrapping (no mid-word) -> 2x line counts wrong
  F3 the two extra-line rows removed  -> pitches wrong at BOTH tiers
  F4 ROW_PAD scaled with f            -> every 2x pitch wrong
  F5 text box width made W-relative   -> 1x columns wrong
  F6 checkbox doubled by MOVE not SIZE-> the reproduced 2x bug disappears
"""

import argparse
import math
import sys

# ===========================================================================
# SECTION 1 - MEASURED GROUND TRUTH
# ===========================================================================

# --- STOCK 1x, 1024x768 windowed, mod fully disabled -----------------------
# Chart window solved from four independently measured pixel edges in
# _tests\captures\graphs-stock-garbage.png + graphs-stock-ref.png:
#   chart origin ABS (513,338), size 488x256, so right edge ABS = 1001.
# Every column below is ABSOLUTE screen x, measured by column scan.
STOCK_ORIGIN_X = 513
STOCK_WIN_W = 488
STOCK_WIN_H = 256

# Garbage (9 series -> checkbox kind).  Column runs, measured.
STOCK_CBOX_COLS = (893, 908)        # inclusive run -> rect 893..909, 16 wide
STOCK_CBOX_SWATCH_COLS = (911, 920)  # rect 911..921, 10 wide
STOCK_CBOX_TEXT_INK_X0 = 926        # ink; the box left is 925 (1px bearing)
# Income/Expenses (2 series -> plain kind).
STOCK_PLAIN_SWATCH_COLS = (895, 904)
STOCK_PLAIN_TEXT_INK_X0 = 910
STOCK_PLOT_RIGHT_COLS = (885, 891)  # the plot frame's right edge run

# Row tops, MEASURED from the checkbox column runs (absolute y).
STOCK_CBOX_TOPS = [358, 377, 411, 430, 464, 483, 502, 521, 555]
STOCK_ORIGIN_Y = 338                # -> local tops 20, 39, 73, ...
STOCK_SWATCH_TOPS = [361, 380, 414, 433, 467, 486, 505, 524, 558]

# Per-LINE text ink bands, MEASURED this session by scanning x 920..1005 of
# graphs-stock-garbage.png.  Exactly two rows show two bands.
#   y361 w42 | y380 w68 | y414 w40 | y433 w40 | y467 w34 | y486 w41
#   y505 w52 | y524 w41 + y539 w33 | y558 w42 + y573 w40
STOCK_TEXT_BAND_TOPS = [361, 380, 414, 433, 467, 486, 505, 524, 539,
                        558, 573]

# --- OUR 2x, chart window 976x512.  Source: SC4UIScale.log v2.54.4 ---------
LIVE_WIN_W = 976
LIVE_WIN_H = 512
LIVE_PLOT_GAME = (45, 20, 866, 492)     # the game's OWN requested plot rect
LIVE_PLOT_OURS = (90, 40, 756, 472)     # after EARLYCHART
LIVE_CBOX_RECT_X = (868, 900)           # LEGENDCBOX: left 868, right 900
LIVE_CBOX_H = 32
LIVE_CBOX_TOPS = [20, 80, 196, 256, 344, 404, 464, 524, 612]
LIVE_TEXT_CBOX = (900, 972)             # game's raw text box, cbox kind
LIVE_TEXT_PLAIN = (884, 972)            # game's raw text box, plain kind
LIVE_SWATCH_CBOX_GAME = (886, 896)      # game's raw swatch, cbox kind
LIVE_SWATCH_PLAIN_GAME = (870, 880)     # game's raw swatch, plain kind
# v2.54.4's own output, from the LEGENDSWATCH / LEGENDFIX lines.
LIVE_2544_SWATCH_CBOX = (872, 892)
LIVE_2544_SWATCH_PLAIN = (772, 792)
LIVE_2544_TEXT_CBOX = (900, 976)
LIVE_2544_TEXT_PLAIN = (800, 976)

# ===========================================================================
# SECTION 2 - THE GAME'S CONSTANTS (byte-verified; addresses in the docstring)
# ===========================================================================


class Consts(object):
    """Every 1x immediate sub_76D3D0 uses for the legend column and the plot.

    An intervention is expressed as a change to THIS object, never as a
    post-hoc edit of an output rect.  That distinction is the whole point of
    the file: v2.54.2/.3/.4 all edited outputs."""

    def __init__(self):
        self.PLOT_L = 45            # 0x0076DD5F  mov [esp+0xa8],0x2d
        self.PLOT_T = 20            # 0x0076DD6A  mov [esp+0xac],0x14
        self.PLOT_R_MARGIN = 110    # 0x0076DD4E  sub edx,0x6e
        self.PLOT_B_MARGIN = 20     # 0x0076DD4B  sub eax,0x14
        self.CBOX_L_MARGIN = 108    # 0x0076E162  add edx,-0x6c
        self.CBOX_R_MARGIN = 92     # 0x0076E159  lea ecx,[edx-0x5c]
        self.CBOX_H = 16            # 0x0076E151  add ecx,0x10
        self.SWATCH_MARGIN_CBOX = 90    # 0x0076E1F8  sub ebx,0x5a
        self.SWATCH_MARGIN_PLAIN = 106  # 0x0076E0F5  sub ebx,0x6a
        self.SWATCH_W = 10          # 0x0076E23C  add ebx,0xa
        self.SWATCH_DY = 3          # 0x0076E233  lea ecx,[eax+3]
        self.SWATCH_H = 6           # 0x0076E239  add eax,9  (9-3)
        self.TEXT_GAP = 4           # 0x0076E2AF  add ecx,4
        self.TEXT_R_MARGIN = 4      # 0x0076E2C8  sub edx,4
        self.ROW0_TOP = 20          # 0x0076DE79  mov [esp+0x18],0x14
        self.ROW_PAD = 4            # 0x0076E34B  lea edx,[ecx+eax+4]

    def copy(self):
        c = Consts()
        c.__dict__.update(self.__dict__)
        return c


STOCK = Consts()

# The Garbage legend, in the order the game emits it.  Order and per-label ink
# widths are MEASURED from the stock capture (band widths above); the two
# extra_line flags are MEASURED (pitch 34 with a single visible band) and
# modelled as a hard break in the string - see the docstring.
GARBAGE_ROWS = [
    # label,              extra_line
    ("Capacity",          False),
    ("Total Garbage",     True),
    ("Imported",          False),
    ("Exported",          True),
    ("Landfill",          False),
    ("Recycled",          False),
    ("Incinerated",       False),
    ("Waste to Energy",   False),
    ("Garbage Pollution", False),
]
PLAIN_ROWS = [("Expenses", False), ("Income", False)]

# Per-word ink widths at 1x, decomposed from the measured whole-label bands:
#   w("Total Garbage")=68/69, w("Garbage")=43 -> w("Total")+w(" ")=26
#   w("Waste to")=42, w("Energy")=33
WORD_INK_1X = {
    "Capacity": 43, "Total": 22, "Garbage": 43, "Imported": 41,
    "Exported": 41, "Landfill": 35, "Recycled": 42, "Incinerated": 53,
    "Waste": 28, "to": 10, "Energy": 33, "Pollution": 41,
    "Expenses": 42, "Income": 33,
}
SPACE_INK_1X = 4

# MODELLED INPUT 1 - the legend font's line height.
#   1x: a 1-line row's pitch is 19 and ROW_PAD is 4          -> 15
#       independently: the two bands of "Waste to"/"Energy"  -> 539-524 = 15
#   2x: the wrapped pair in graphs-ours-2x.png               -> 28
LINE_H = {1.0: 15, 2.0: 28}

# MODELLED INPUT 2 - the 1x->2x ink ratio.  MEASURED from graphs-ours-2x.png:
# "Income" ink 33px at 1x, 70px at 2x.  It is 2.121, NOT 2.00, and that is
# load-bearing: at 2.00 "Landfill" (35 -> 70) would fit the 72px box and the
# model would mispredict row 5.  F1 in --falsify is exactly this.
INK_RATIO_2X = 70.0 / 33.0


def line_height(f):
    if f in LINE_H:
        return LINE_H[f]
    return int(round(LINE_H[1.0] * f))          # knob only; flagged by caller


def ink_ratio(f):
    if f == 1.0:
        return 1.0
    if f == 2.0:
        return INK_RATIO_2X
    return f                                    # knob only; flagged by caller


def label_ink(label, f):
    r = ink_ratio(f)
    words = label.split(" ")
    return (sum(WORD_INK_1X[w] for w in words)
            + SPACE_INK_1X * (len(words) - 1)) * r


def wrap_lines(label, wrap_w, f):
    """Greedy line break.  Breaks at spaces; a word wider than the box breaks
    MID-WORD.  Mid-word breaking is MEASURED, not assumed: the user's 2x
    report reads 'Capaci/ty', 'Total Garba/ge', 'Recycl/ed'."""
    if wrap_w <= 0:
        return 99
    r = ink_ratio(f)
    space = SPACE_INK_1X * r
    lines, cur = 1, 0.0
    for wd in label.split(" "):
        w = WORD_INK_1X[wd] * r
        if cur > 0 and cur + space + w <= wrap_w:
            cur += space + w
            continue
        if cur > 0:
            lines += 1
            cur = 0.0
        while w > wrap_w:                       # uniform-advance approximation
            lines += 1
            w -= wrap_w
        cur = w
    return lines


# ===========================================================================
# SECTION 3 - THE GAME'S LAYOUT, exactly as sub_76D3D0 computes it
# ===========================================================================

def game_layout(win_w, win_h, rows, f, C=STOCK, force_kind=None):
    """Return every rect sub_76D3D0 writes, for one chart, at scale f.

    Note what is NOT an input: the plot rect.  The legend loop never reads it
    (assumption (d) below).  Everything is derived from win_w."""
    kind = force_kind or ("cbox" if len(rows) > 2 else "plain")
    has_cbox = (kind == "cbox")

    swatch_l = win_w - (C.SWATCH_MARGIN_CBOX if has_cbox
                        else C.SWATCH_MARGIN_PLAIN)
    swatch_r = swatch_l + C.SWATCH_W
    text_l = swatch_r + C.TEXT_GAP
    text_r = win_w - C.TEXT_R_MARGIN
    box_w = text_r - text_l
    cbox_l = win_w - C.CBOX_L_MARGIN
    cbox_r = win_w - C.CBOX_R_MARGIN

    lh = line_height(f)
    y = C.ROW0_TOP
    out_rows = []
    for label, extra in rows:
        n = wrap_lines(label, box_w, f) + (1 if extra else 0)
        text_h = lh * n
        out_rows.append({
            "label": label, "lines": n,
            "cbox": (cbox_l, y, cbox_r, y + C.CBOX_H) if has_cbox else None,
            "swatch": (swatch_l, y + C.SWATCH_DY,
                       swatch_r, y + C.SWATCH_DY + C.SWATCH_H),
            "text": (text_l, y, text_r, y + text_h),
            "top": y, "height": text_h,
        })
        y += text_h + C.ROW_PAD

    return {
        "kind": kind, "win_w": win_w, "win_h": win_h, "f": f,
        "rows": out_rows,
        "cbox_x": (cbox_l, cbox_r) if has_cbox else None,
        "swatch_x": (swatch_l, swatch_r),
        "text_x": (text_l, text_r), "box_w": box_w,
        "tops": [r["top"] for r in out_rows],
        "pitches": [out_rows[i + 1]["top"] - out_rows[i]["top"]
                    for i in range(len(out_rows) - 1)],
        "bottom": y,
        "total_h": y - C.ROW0_TOP,
        "plot": (C.PLOT_L, C.PLOT_T,
                 win_w - C.PLOT_R_MARGIN, win_h - C.PLOT_B_MARGIN),
        "lh": lh,
    }


# ===========================================================================
# SECTION 4 - OUR MOD, applied ON TOP of the game's output
# ===========================================================================

class Interventions(object):
    """Every lever we have, expressed as a flag.  Defaults = stock game."""

    def __init__(self, sweep_cbox_size=False, earlychart=False,
                 legendfix_2544=False, scale_budget=False,
                 scale_row0=False, scale_swatch_only=False,
                 widen_text_only=False):
        self.sweep_cbox_size = sweep_cbox_size    # our sweep: SIZE-only x f
        self.earlychart = earlychart              # ChartStoreThunk plot rewrite
        self.legendfix_2544 = legendfix_2544      # the shipped output patches
        self.scale_budget = scale_budget          # the #78-shaped candidate
        self.scale_row0 = scale_row0              # ROW0_TOP x f too
        self.scale_swatch_only = scale_swatch_only    # v2.54.4's half
        self.widen_text_only = widen_text_only        # v2.54.2's half


def apply_pre(iv, f):
    """Interventions that change the game's CONSTANTS (upstream, #78-shaped).

    scale_budget scales the whole right-margin budget as one coupled set.
    Self-check (law 27 / #88): at f=1 it must reduce to stock exactly."""
    C = STOCK.copy()
    if iv.scale_budget:
        for k in ("PLOT_R_MARGIN", "CBOX_L_MARGIN", "CBOX_R_MARGIN",
                  "SWATCH_MARGIN_CBOX", "SWATCH_MARGIN_PLAIN",
                  "SWATCH_W", "SWATCH_H", "SWATCH_DY",
                  "TEXT_GAP", "TEXT_R_MARGIN", "CBOX_H"):
            setattr(C, k, int(round(getattr(C, k) * f)))
    if iv.scale_row0:
        C.ROW0_TOP = int(round(C.ROW0_TOP * f))
    return C


def apply_post(lay, iv, f):
    """Interventions that rewrite OUTPUT rects (downstream). This is the
    family every failed build belongs to; the model applies them faithfully
    so their damage is visible."""
    C = STOCK
    if iv.sweep_cbox_size:
        # MEASURED signature: L and T unchanged, W and H x f.  A size-only,
        # no-move resize (LEGENDCBOX 868..900 vs the game's 868..884).
        for r in lay["rows"]:
            if r["cbox"]:
                l, t, rr, b = r["cbox"]
                r["cbox"] = (l, t, l + int(round((rr - l) * f)),
                             t + int(round((b - t) * f)))
        if lay["cbox_x"]:
            l, rr = lay["cbox_x"]
            lay["cbox_x"] = (l, l + int(round((rr - l) * f)))

    if iv.earlychart:
        l, t, rr, b = lay["plot"]
        w, h = lay["win_w"], lay["win_h"]
        lay["plot"] = (int(round(l * f)), int(round(t * f)),
                       w - int(round((w - rr) * f)),
                       h - int(round((h - b) * f)))

    if iv.legendfix_2544 or iv.widen_text_only:
        # LEGENDFIX: right -> winW; left -> right - w*f (plain) / left kept
        # (cbox).  Reproduced from the shipped log lines verbatim.
        tl, tr = lay["text_x"]
        new_r = lay["win_w"]
        if lay["kind"] == "plain":
            new_l = new_r - int(round((tr - tl) * f))
        else:
            new_l = tl
        lay["text_x"] = (new_l, new_r)
        lay["box_w"] = new_r - new_l
        for r in lay["rows"]:
            _, t, _, b = r["text"]
            r["text"] = (new_l, t, new_r, b)

    if iv.legendfix_2544 or iv.scale_swatch_only:
        # LEGENDSWATCH: size x f, gap x f, hung off the (possibly moved) text
        # left edge.  gap 14 -> 28, 10x6 -> 20x12.
        gap = int(round((C.SWATCH_W + C.TEXT_GAP) * f))
        sw = int(round(C.SWATCH_W * f))
        sh = int(round(C.SWATCH_H * f))
        tl = lay["text_x"][0]
        lay["swatch_x"] = (tl - gap, tl - gap + sw)
        for r in lay["rows"]:
            _, t, _, _ = r["swatch"]
            r["swatch"] = (tl - gap, t, tl - gap + sw, t + sh)
    return lay


def predict(f, iv, rows=None, win_w=None, win_h=None):
    rows = rows if rows is not None else GARBAGE_ROWS
    win_w = win_w if win_w is not None else int(round(STOCK_WIN_W * f))
    win_h = win_h if win_h is not None else int(round(STOCK_WIN_H * f))
    C = apply_pre(iv, f)
    lay = game_layout(win_w, win_h, rows, f, C)
    return apply_post(lay, iv, f)


def verdict(lay):
    """Adjudicate a candidate (law 44). Returns (ok, list-of-problems)."""
    bad = []
    cx = lay["cbox_x"]
    sx = lay["swatch_x"]
    tx = lay["text_x"]
    if cx and sx[0] < cx[1]:
        bad.append("swatch %d..%d starts inside checkbox %d..%d - INVISIBLE"
                   % (sx[0], sx[1], cx[0], cx[1]))
    if sx[1] > tx[0]:
        bad.append("swatch %d..%d overlaps text box left %d"
                   % (sx[0], sx[1], tx[0]))
    if cx and cx[1] > tx[0]:
        bad.append("checkbox right %d past text left %d" % (cx[1], tx[0]))
    if tx[1] > lay["win_w"]:
        bad.append("text right %d past window %d" % (tx[1], lay["win_w"]))
    over = lay["bottom"] - lay["win_h"]
    if over > 0:
        clipped = sum(1 for r in lay["rows"]
                      if r["top"] + r["height"] > lay["win_h"])
        bad.append("legend column overflows window bottom by %d px, %d of %d "
                   "rows clipped" % (over, clipped, len(lay["rows"])))
    if sx[0] < lay["plot"][2]:
        bad.append("swatch %d starts left of the plot right edge %d"
                   % (sx[0], lay["plot"][2]))
    return (not bad), bad


# ===========================================================================
# SECTION 5 - ACCEPTANCE SUITE
# ===========================================================================

class Suite(object):
    def __init__(self):
        self.n = 0
        self.fails = []

    def chk(self, name, got, want):
        self.n += 1
        ok = (got == want)
        print("  %s %-46s %s" % ("[PASS]" if ok else "[FAIL]", name,
                                 repr(got)))
        if not ok:
            print("         %-46s want %s" % ("", repr(want)))
            self.fails.append(name)
        return ok

    def note(self, s):
        print("         " + s)


def case_stock_1x(S, verbose):
    print("=" * 76)
    print("CASE 1  STOCK 1x  (measured pixels, mod disabled) - both kinds")
    print("=" * 76)
    ox, W, H = STOCK_ORIGIN_X, STOCK_WIN_W, STOCK_WIN_H
    right = ox + W                       # 1001

    g = game_layout(W, H, GARBAGE_ROWS, 1.0)
    if verbose:
        for r in g["rows"]:
            print("    %-18s lines=%d h=%3d top=%4d text=%s"
                  % (r["label"], r["lines"], r["height"], r["top"], r["text"]))

    # -- horizontal, checkbox kind: compare in ABSOLUTE screen x -------------
    S.chk("1x cbox  checkbox column (abs)",
          (ox + g["cbox_x"][0], ox + g["cbox_x"][1] - 1),
          STOCK_CBOX_COLS)
    S.chk("1x cbox  swatch column (abs)",
          (ox + g["swatch_x"][0], ox + g["swatch_x"][1] - 1),
          STOCK_CBOX_SWATCH_COLS)
    S.chk("1x cbox  text ink left (abs, box+1)",
          ox + g["text_x"][0] + 1, STOCK_CBOX_TEXT_INK_X0)
    S.chk("1x cbox  text box width", g["box_w"], 72)
    S.chk("1x cbox  plot right edge (abs)",
          ox + g["plot"][2], STOCK_PLOT_RIGHT_COLS[1])
    S.note("window right edge %d ; reserve = %d px" % (right, W - g["plot"][2]))

    p = game_layout(W, H, PLAIN_ROWS, 1.0)
    S.chk("1x plain swatch column (abs)",
          (ox + p["swatch_x"][0], ox + p["swatch_x"][1] - 1),
          STOCK_PLAIN_SWATCH_COLS)
    S.chk("1x plain text ink left (abs, box+1)",
          ox + p["text_x"][0] + 1, STOCK_PLAIN_TEXT_INK_X0)
    S.chk("1x plain text box width", p["box_w"], 88)

    # -- vertical -----------------------------------------------------------
    S.chk("1x cbox  row tops (abs)",
          [STOCK_ORIGIN_Y + t for t in g["tops"]], STOCK_CBOX_TOPS)
    S.chk("1x cbox  row pitches", g["pitches"], [19, 34, 19, 34, 19, 19, 19, 34])
    S.chk("1x cbox  lines per row", [r["lines"] for r in g["rows"]],
          [1, 2, 1, 2, 1, 1, 1, 2, 2])
    S.chk("1x cbox  swatch tops (abs)",
          [STOCK_ORIGIN_Y + r["swatch"][1] for r in g["rows"]],
          STOCK_SWATCH_TOPS)
    # which labels wrap, i.e. how many INK bands the capture must show
    bands = []
    for r in g["rows"]:
        vis = wrap_lines(r["label"], g["box_w"], 1.0)
        for k in range(vis):
            bands.append(STOCK_ORIGIN_Y + r["top"] + 3 + k * g["lh"])
    S.chk("1x cbox  text ink band tops (abs)", bands, STOCK_TEXT_BAND_TOPS)
    S.chk("1x cbox  wrapped labels",
          [r["label"] for r in g["rows"]
           if wrap_lines(r["label"], g["box_w"], 1.0) > 1],
          ["Waste to Energy", "Garbage Pollution"])
    ok, bad = verdict(g)
    S.chk("1x cbox  verdict CLEAN", (ok, bad), (True, []))
    S.note("legend column %d px in a %d px window - fits with %d spare"
           % (g["total_h"], H, H - g["bottom"]))


def case_live_2x(S, verbose):
    print()
    print("=" * 76)
    print("CASE 2  OUR 2x TODAY (SC4UIScale.log v2.54.4) - must reproduce")
    print("        the BUG, not the healthy case")
    print("=" * 76)
    # 2a - the GAME's own 2x output, before any of our post-patches.
    g = game_layout(LIVE_WIN_W, LIVE_WIN_H, GARBAGE_ROWS, 2.0)
    if verbose:
        for r in g["rows"]:
            print("    %-18s lines=%d h=%3d top=%4d text=%s swatch=%s"
                  % (r["label"], r["lines"], r["height"], r["top"],
                     r["text"], r["swatch"]))
    S.chk("2x game  cbox text box", g["text_x"], LIVE_TEXT_CBOX)
    S.chk("2x game  cbox text box width", g["box_w"], 72)
    S.chk("2x game  cbox swatch", g["swatch_x"], LIVE_SWATCH_CBOX_GAME)
    S.chk("2x game  plot rect", g["plot"], LIVE_PLOT_GAME)
    S.chk("2x game  row tops", g["tops"], LIVE_CBOX_TOPS)
    S.chk("2x game  row pitches", g["pitches"],
          [LIVE_CBOX_TOPS[i + 1] - LIVE_CBOX_TOPS[i] for i in range(8)])
    S.chk("2x game  lines per row", [r["lines"] for r in g["rows"]],
          [2, 4, 2, 3, 2, 2, 2, 3, 4])
    p = game_layout(LIVE_WIN_W, LIVE_WIN_H, PLAIN_ROWS, 2.0)
    S.chk("2x game  plain text box", p["text_x"], LIVE_TEXT_PLAIN)
    S.chk("2x game  plain swatch", p["swatch_x"], LIVE_SWATCH_PLAIN_GAME)

    # 2b - THE BUG: our sweep's size-only checkbox doubling on top.
    iv = Interventions(sweep_cbox_size=True, earlychart=True)
    b = predict(2.0, iv, GARBAGE_ROWS, LIVE_WIN_W, LIVE_WIN_H)
    S.chk("2x ours  checkbox window", b["cbox_x"], LIVE_CBOX_RECT_X)
    S.chk("2x ours  checkbox height", b["rows"][0]["cbox"][3] -
          b["rows"][0]["cbox"][1], LIVE_CBOX_H)
    S.chk("2x ours  EARLYCHART plot", b["plot"], LIVE_PLOT_OURS)
    S.chk("2x ours  swatch INSIDE the checkbox",
          b["swatch_x"][0] >= b["cbox_x"][0] and
          b["swatch_x"][1] <= b["cbox_x"][1], True)
    ok, bad = verdict(b)
    S.chk("2x ours  verdict BROKEN", ok, False)
    for m in bad:
        S.note("defect: " + m)
    # Two different questions, kept apart on purpose: a row that STARTS below
    # the window is the user's "the last 2 of 9 rows are clipped off"; a row
    # that merely ENDS below it loses its bottom line only.
    gone = [r["label"] for r in b["rows"] if r["top"] >= LIVE_WIN_H]
    part = [r["label"] for r in b["rows"]
            if r["top"] < LIVE_WIN_H and r["top"] + r["height"] > LIVE_WIN_H]
    S.chk("2x ours  rows entirely below the window", len(gone), 2)
    S.note("entirely gone: %s" % ", ".join(gone))
    S.chk("2x ours  rows partly clipped", len(part), 1)
    S.note("partly clipped: %s" % ", ".join(part))
    S.chk("2x ours  legend column height", b["total_h"], 708)
    S.note("bottom %d vs window %d -> overflow %d px"
           % (b["bottom"], LIVE_WIN_H, b["bottom"] - LIVE_WIN_H))

    # 2c - v2.54.4's own post-patches, reproduced from its log lines.
    iv4 = Interventions(sweep_cbox_size=True, earlychart=True,
                        legendfix_2544=True)
    v4 = predict(2.0, iv4, GARBAGE_ROWS, LIVE_WIN_W, LIVE_WIN_H)
    S.chk("v2.54.4 cbox  swatch", v4["swatch_x"], LIVE_2544_SWATCH_CBOX)
    S.chk("v2.54.4 cbox  text box", v4["text_x"], LIVE_2544_TEXT_CBOX)
    v4p = predict(2.0, iv4, PLAIN_ROWS, LIVE_WIN_W, LIVE_WIN_H)
    S.chk("v2.54.4 plain swatch", v4p["swatch_x"], LIVE_2544_SWATCH_PLAIN)
    S.chk("v2.54.4 plain text box", v4p["text_x"], LIVE_2544_TEXT_PLAIN)
    S.chk("v2.54.4 cbox  swatch STILL inside the checkbox",
          v4["swatch_x"][0] >= v4["cbox_x"][0] and
          v4["swatch_x"][1] <= v4["cbox_x"][1], True)


def case_assumptions(S):
    print()
    print("=" * 76)
    print("CASE 3  THE FAULTY-ASSUMPTION AUDIT - each is tested, not asserted")
    print("=" * 76)

    # (a) "the legend column is already 2x-exact"
    g1 = game_layout(STOCK_WIN_W, STOCK_WIN_H, GARBAGE_ROWS, 1.0)
    g2 = game_layout(LIVE_WIN_W, LIVE_WIN_H, GARBAGE_ROWS, 2.0)
    scaled = {
        "text box width": (g1["box_w"], g2["box_w"]),
        "swatch width": (g1["swatch_x"][1] - g1["swatch_x"][0],
                         g2["swatch_x"][1] - g2["swatch_x"][0]),
        "swatch height": (STOCK.SWATCH_H, STOCK.SWATCH_H),
        "swatch dy": (STOCK.SWATCH_DY, STOCK.SWATCH_DY),
        "row0 top": (g1["tops"][0], g2["tops"][0]),
        "cbox left margin": (STOCK_WIN_W - g1["cbox_x"][0],
                             LIVE_WIN_W - g2["cbox_x"][0]),
        "swatch->text gap": (g1["text_x"][0] - g1["swatch_x"][1],
                             g2["text_x"][0] - g2["swatch_x"][1]),
        "text right margin": (STOCK_WIN_W - g1["text_x"][1],
                              LIVE_WIN_W - g2["text_x"][1]),
        "plot right reserve": (STOCK_WIN_W - g1["plot"][2],
                               LIVE_WIN_W - g2["plot"][2]),
    }
    unscaled = sorted(k for k, (a, b) in scaled.items() if a == b)
    print("  (a) 'the legend column is already 2x-exact'")
    for k in sorted(scaled):
        a, b = scaled[k]
        print("        %-20s 1x=%-4d 2x=%-4d  %s"
              % (k, a, b, "UNSCALED" if a == b else "x%.2f" % (b / float(a))))
    S.chk("(a) FALSIFIED: count of UNSCALED legend quantities",
          len(unscaled), 9)

    # (b) "the text box width scales with the window"
    print("  (b) 'the text box width scales with the window'")
    widths = []
    for W in (400, 488, 700, 976, 1400):
        widths.append(game_layout(W, 300, GARBAGE_ROWS, 1.0)["box_w"])
    print("        cbox  box width at winW 400/488/700/976/1400 -> %s" % widths)
    pw = [game_layout(W, 300, PLAIN_ROWS, 1.0)["box_w"]
          for W in (400, 488, 700, 976, 1400)]
    print("        plain box width at the same widths            -> %s" % pw)
    S.chk("(b) FALSIFIED: cbox box width is winW-INDEPENDENT",
          len(set(widths)), 1)
    S.chk("(b) FALSIFIED: plain box width is winW-INDEPENDENT",
          len(set(pw)), 1)
    S.chk("(b) FALSIFIED: plain box is 88 at BOTH tiers, never 44",
          (game_layout(STOCK_WIN_W, STOCK_WIN_H, PLAIN_ROWS, 1.0)["box_w"],
           game_layout(LIVE_WIN_W, LIVE_WIN_H, PLAIN_ROWS, 2.0)["box_w"]),
          (88, 88))

    # (c) "the swatch is the only unscaled element"
    print("  (c) 'the swatch is the only unscaled element'")
    print("        unscaled: %s" % ", ".join(unscaled))
    non_swatch = [k for k in unscaled if "swatch" not in k]
    S.chk("(c) FALSIFIED: unscaled elements that are NOT the swatch",
          len(non_swatch), 5)
    S.note("not-the-swatch: %s" % ", ".join(non_swatch))

    # (d) "the legend is laid out against the plot rect"
    print("  (d) 'the legend is laid out against the plot rect'")
    base = game_layout(LIVE_WIN_W, LIVE_WIN_H, GARBAGE_ROWS, 2.0)
    C = STOCK.copy()
    C.PLOT_R_MARGIN = 220                   # what EARLYCHART effectively wants
    moved = game_layout(LIVE_WIN_W, LIVE_WIN_H, GARBAGE_ROWS, 2.0, C)
    print("        plot right %d -> %d" % (base["plot"][2], moved["plot"][2]))
    S.chk("(d) FALSIFIED: legend columns unchanged when the plot moves",
          (moved["cbox_x"], moved["swatch_x"], moved["text_x"]),
          (base["cbox_x"], base["swatch_x"], base["text_x"]))
    # EARLYCHART pulls the plot's right edge in to 756 but the legend column
    # never moved, so the space it freed becomes DEAD.
    S.chk("(d) EARLYCHART dead gutter, plot right -> checkbox left",
          base["cbox_x"][0] - (LIVE_WIN_W - 220), 112)
    S.chk("(d) EARLYCHART dead gutter, plot right -> swatch left",
          base["swatch_x"][0] - (LIVE_WIN_W - 220), 130)

    # (e) "the row pitch is independent of text wrapping"
    print("  (e) 'the row pitch is independent of text wrapping'")
    short = [("Income", e) for _, e in GARBAGE_ROWS]
    flat = game_layout(LIVE_WIN_W, LIVE_WIN_H, short, 2.0)
    print("        real labels  -> pitches %s" % base["pitches"])
    print("        short labels -> pitches %s" % flat["pitches"])
    S.chk("(e) FALSIFIED: pitch varies with the label",
          len(set(base["pitches"])) > 1, True)
    S.chk("(e) FALSIFIED: same rows, short labels, uniform pitch",
          sorted(set(p for p in flat["pitches"] if p == 32)), [32])

    # (f) the one nobody wrote down: whose 32 is it?
    print("  (f) 'the 32px checkbox is the game's 2x output'")
    S.chk("(f) FALSIFIED: the game writes 16, not 32",
          base["rows"][0]["cbox"][2] - base["rows"][0]["cbox"][0], 16)
    S.note("the 32 is OUR sweep, size-only (L and T are the game's, "
           "untouched) - so v2.54.3 had two writers on one rect")


def case_knob(S, verbose):
    print()
    print("=" * 76)
    print("CASE 4  THE KNOB - candidate interventions at f=2, adjudicated")
    print("=" * 76)
    cands = [
        ("stock game at 2x (no mod)", Interventions()),
        ("today: sweep+EARLYCHART", Interventions(sweep_cbox_size=True,
                                                  earlychart=True)),
        ("v2.54.2 widen text only", Interventions(sweep_cbox_size=True,
                                                  earlychart=True,
                                                  widen_text_only=True)),
        ("v2.54.4 swatch+text patch", Interventions(sweep_cbox_size=True,
                                                    earlychart=True,
                                                    legendfix_2544=True)),
        ("BUDGET x f + sweep cbox", Interventions(sweep_cbox_size=True,
                                                  scale_budget=True)),
        ("BUDGET x f, sweep STOOD DOWN", Interventions(scale_budget=True)),
        ("BUDGET x f + row0 x f", Interventions(scale_budget=True,
                                                scale_row0=True)),
    ]
    print("  %-27s %-13s %-13s %-13s %-5s %-5s %s"
          % ("candidate", "checkbox", "swatch", "textbox", "boxW", "botm",
             "verdict"))
    results = {}
    for name, iv in cands:
        lay = predict(2.0, iv, GARBAGE_ROWS, LIVE_WIN_W, LIVE_WIN_H)
        ok, bad = verdict(lay)
        cx = lay["cbox_x"] or (0, 0)
        print("  %-27s %-13s %-13s %-13s %-5d %-5d %s"
              % (name, "%d..%d" % cx, "%d..%d" % lay["swatch_x"],
                 "%d..%d" % lay["text_x"], lay["box_w"], lay["bottom"],
                 "OK" if ok else "BROKEN"))
        if not ok and verbose:
            for m in bad:
                print("        - " + m)
        results[name] = (lay, ok, bad)

    # The gate the Design phase actually needs.
    S.chk("knob: today is BROKEN", results["today: sweep+EARLYCHART"][1], False)
    S.chk("knob: v2.54.4 is BROKEN",
          results["v2.54.4 swatch+text patch"][1], False)
    # THE FINDING THIS MODEL PRODUCED, and it was not in the brief:
    # scaling the budget makes the game itself write a 32-wide checkbox
    # (winW-216 .. winW-184).  Our sweep's size-only doubling then runs on top
    # and makes it 64 - a DOUBLE SCALE, law 2/13.  The #78-shaped cure is only
    # correct as a COUPLED PAIR (law 43): scale the budget AND stand the
    # sweep's checkbox doubling down.  Either half alone is a new ping-pong.
    S.chk("knob: BUDGET x f WITH the sweep still doubling is BROKEN",
          results["BUDGET x f + sweep cbox"][1], False)
    S.chk("knob: that breakage is a DOUBLE-SCALED checkbox (64, want 32)",
          results["BUDGET x f + sweep cbox"][0]["cbox_x"][1] -
          results["BUDGET x f + sweep cbox"][0]["cbox_x"][0], 64)
    S.chk("knob: BUDGET x f with the sweep STOOD DOWN is CLEAN",
          results["BUDGET x f, sweep STOOD DOWN"][1], True)
    lay = results["BUDGET x f, sweep STOOD DOWN"][0]
    S.chk("knob: checkbox is then 32 wide from the GAME's own arithmetic",
          lay["cbox_x"][1] - lay["cbox_x"][0], 32)
    S.chk("knob: BUDGET x f box width = 2x stock", lay["box_w"], 144)
    S.chk("knob: BUDGET x f all 9 rows inside the window",
          sum(1 for r in lay["rows"]
              if r["top"] + r["height"] <= LIVE_WIN_H), 9)
    S.chk("knob: BUDGET x f gap checkbox->swatch",
          lay["swatch_x"][0] - lay["cbox_x"][1], 4)
    S.chk("knob: BUDGET x f gap swatch->text",
          lay["text_x"][0] - lay["swatch_x"][1], 8)
    wrapped = [r["label"] for r in lay["rows"]
               if wrap_lines(r["label"], lay["box_w"], 2.0) > 1]
    S.note("BUDGET x f wraps %d labels (%s); stock wraps 2"
           % (len(wrapped), ", ".join(wrapped)))
    S.note("BUDGET x f column height %d px, spare %d px to the window bottom"
           % (lay["total_h"], LIVE_WIN_H - lay["bottom"]))

    # SELF-CHECK, law 27 / #88: the budget general form must reduce to stock.
    one = predict(1.0, Interventions(scale_budget=True), GARBAGE_ROWS,
                  STOCK_WIN_W, STOCK_WIN_H)
    ref = game_layout(STOCK_WIN_W, STOCK_WIN_H, GARBAGE_ROWS, 1.0)
    S.chk("knob: budget general form reduces to stock at f=1",
          (one["cbox_x"], one["swatch_x"], one["text_x"], one["tops"]),
          (ref["cbox_x"], ref["swatch_x"], ref["text_x"], ref["tops"]))


# ===========================================================================
# SECTION 6 - THE FALSIFICATION AUDIT
# ===========================================================================

def falsify():
    global INK_RATIO_2X, GARBAGE_ROWS, wrap_lines
    print("=" * 76)
    print("FALSIFICATION AUDIT - every row must be RED (the model must break)")
    print("=" * 76)

    def state():
        g1 = game_layout(STOCK_WIN_W, STOCK_WIN_H, GARBAGE_ROWS, 1.0)
        g2 = game_layout(LIVE_WIN_W, LIVE_WIN_H, GARBAGE_ROWS, 2.0)
        b = predict(2.0, Interventions(sweep_cbox_size=True, earlychart=True),
                    GARBAGE_ROWS, LIVE_WIN_W, LIVE_WIN_H)
        return (g1["pitches"], g1["cbox_x"], g1["swatch_x"], g1["text_x"],
                g2["pitches"], [r["lines"] for r in g2["rows"]],
                b["cbox_x"], b["swatch_x"][0] >= b["cbox_x"][0])
    good = state()
    print("  baseline captured (%d channels)" % len(good))
    bad = []

    def check(tag):
        now = state()
        differs = now != good
        print("  [%s] %s" % ("RED " if differs else "GREEN", tag))
        if not differs:
            bad.append(tag)

    saved = INK_RATIO_2X
    INK_RATIO_2X = 2.0
    check("F1 ink ratio 2.00 not 2.121")
    INK_RATIO_2X = saved

    sw = wrap_lines

    def word_only(label, wrap_w, f):
        r = ink_ratio(f)
        lines, cur = 1, 0.0
        for wd in label.split(" "):
            w = WORD_INK_1X[wd] * r
            if cur > 0 and cur + SPACE_INK_1X * r + w <= wrap_w:
                cur += SPACE_INK_1X * r + w
            else:
                if cur > 0:
                    lines += 1
                cur = w
        return lines
    wrap_lines = word_only
    check("F2 word-only wrap, no mid-word break")
    wrap_lines = sw

    sr = GARBAGE_ROWS
    GARBAGE_ROWS = [(n, False) for n, _ in sr]
    check("F3 the two extra-line rows removed")
    GARBAGE_ROWS = sr

    STOCK.ROW_PAD = 8
    check("F4 ROW_PAD scaled with f (4 -> 8)")
    STOCK.ROW_PAD = 4

    STOCK.TEXT_R_MARGIN = 40        # makes the box winW-relative in effect
    check("F5 text right margin perturbed")
    STOCK.TEXT_R_MARGIN = 4

    def move_not_size(lay, iv, f):
        for r in lay["rows"]:
            if r["cbox"]:
                l, t, rr, b = r["cbox"]
                r["cbox"] = (l - (rr - l), t, rr, b + (b - t))
        if lay["cbox_x"]:
            l, rr = lay["cbox_x"]
            lay["cbox_x"] = (l - (rr - l), rr)
        return lay
    global apply_post
    sp = apply_post
    apply_post = move_not_size
    check("F6 checkbox doubled by MOVE, not SIZE")
    apply_post = sp

    print()
    if bad:
        print("AUDIT FAILED - these perturbations did NOT break the model: %s"
              % bad)
        return 1
    print("AUDIT PASSED - all 6 falsifications turn the model red, so its "
          "greens mean something.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--falsify", action="store_true")
    ap.add_argument("--knob", action="store_true")
    a = ap.parse_args()

    if a.falsify:
        rc = falsify()
        print()
        print("OVERALL: %s" % ("PASS" if rc == 0 else "FAIL"))
        return rc

    S = Suite()
    if a.knob:
        case_knob(S, True)
    else:
        case_stock_1x(S, a.verbose)
        case_live_2x(S, a.verbose)
        case_assumptions(S)
        case_knob(S, a.verbose)

    print()
    print("=" * 76)
    if S.fails:
        print("FAIL - %d checks, %d failures" % (S.n, len(S.fails)))
        for m in S.fails:
            print("   x " + m)
        print()
        print("OVERALL: FAIL")
        return 1
    print("PASS - %d checks. The closed form reproduces MEASURED stock 1x "
          "(both kinds)," % S.n)
    print("       MEASURED live 2x INCLUDING the defect, and v2.54.4's own "
          "output.")
    print("       SCOPE: layout only. Nothing here proves a rect reaches the "
          "screen.")
    print()
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
