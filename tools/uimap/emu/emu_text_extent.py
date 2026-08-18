# -*- coding: utf-8 -*-
r"""
emu_text_extent.py -- MEASURED text-extent model for the SC4 chart legend (#57).

WHAT THIS IS
------------
A closed-form, integer-exact model of how wide a legend label is when the game
draws it at a given font size, plus the wrap simulator that decides where a
label breaks inside a box of a given width.  It exists so a proposed legend fix
can be ADJUDICATED offline, before it is built.

PROVENANCE OF EVERY NUMBER  (nothing here is inferred from a screenshot "look")
------------------------------------------------------------------------------
The font files shipped with SimCity 4 are Monotype MicroType-Express containers
(<install>\Fonts\*.mxf, magic 'MXFN').  There is NO .ttf/.otf anywhere in the
install or in this repo, so PIL / FreeType CANNOT be pointed at the real face.
Rather than substitute a look-alike font (which would have produced a
metric table that is wrong by an unknown amount), every metric below is
MEASURED OUT OF THE GAME'S OWN RENDERED PIXELS:

  1x / 13 pt :  _tests\captures\graphs-stock-ref.png      (1024x768, mod OFF)
                _tests\captures\graphs-stock-garbage.png  (1024x768, mod OFF)
  2x / 26 pt :  _tests\captures\graphs-ours-2x.png        (2400x1600, v2.5x)

`--extract` re-derives the tables from those PNGs; the baked tables below are
what that pass produced, so the file is runnable with no images present.

KEY MEASURED FACT #1 -- the legend style and the chart-list style have
IDENTICAL advance metrics.  "Garbage" is rendered by both (legend row and the
radio list) and is 42 px wide in BOTH at 13 pt.  Arta ships regular + italic
only (no `Arta (Bold).mxf`), so the Legend style's `bold` flag does not change
the metrics.  That is what lets the 18 chart-list labels be pooled with the
13 legend labels into one metric set.

KEY MEASURED FACT #2 -- text width is NOT linear in point size.
Over 17 independent strings measured at BOTH 13 pt and 26 pt the ink width
grows by a factor of 2.13 +- 0.03, not 2.00.  Modelled here as a per-glyph
rounding loss:  W(s,S) = S * V(s) - n(s) * DELTA,  DELTA = 0.70 px/glyph.
Ignoring this term under-predicts a 2x label by ~6 %, which is exactly the
size of the "Expense / s" shortfall the 0.92 SIZE_SQUEEZE was invented to
paper over.

Offline only.  Reads two PNGs; writes nothing.
"""

import sys

# =============================================================================
#  MEASURED GLYPH METRICS -- Arta, as rasterised by the game's Font Fusion
#  engine at 26 pt (style params xscale=0.95 | xadvancescale=0.99).
#  ADV26[c] = pen advance in px.   INK26[c] = ink (blackbox) width in px.
#  Derived by segmenting the 26 pt renderings in graphs-ours-2x.png; the
#  per-instance spread is given in the comment after each estimate count.
# =============================================================================

ADV26 = {
    # capitals                       instances seen
    'A': 19.00,   # 4   (18,19,19,20)
    'C': 18.50,   # 4   (18,18,19,19)
    'D': 17.00,   # 1
    'E': 11.67,   # 3   (11,12,12)
    'F': 12.00,   # 1
    'G': 18.00,   # 1   (hand-aligned: "Garbage", r+b merged)
    'I':  5.00,   # 2   (5,5)
    'J': 10.00,   # 1
    'L': 12.00,   # 1   (hand-aligned: "Life Expectancy")
    'M': 22.00,   # 1
    'P': 12.00,   # 5   (all 12)
    'R': 12.00,   # 3   (all 12)
    'T': 14.00,   # 1
    'W': 25.00,   # 2   (25,25)
    # lowercase
    'a': 13.00,   # 8   (all 13)
    'b': 12.67,   # 3   (12,13,13)
    'c': 11.00,   # 4   (all 11)
    'd': 12.67,   # 3   (12,13,13)
    'e': 12.62,   # 8   (12,12,12,13,13,13,13,13)
    'f':  8.00,   # ESTIMATED +-1  (only appears inside merged "fe"/"ffi" runs)
    'g': 13.33,   # 3   (13,13,14)
    'i':  5.00,   # 10  (all 5)
    'l':  5.40,   # 5   (5,5,5,6,6)
    'm': 18.00,   # 7   (all 18)
    'n': 11.83,   # 6   (11,12,12,12,12,12)
    'o': 13.27,   # 15  (13 x11, 14 x4)
    'p': 12.33,   # 3   (12,12,13)
    'r':  8.00,   # 1
    's':  9.50,   # 2   (9,10)
    't':  7.60,   # 10  (7,7,7,7,8,8,8,8,8,8)
    'u': 12.14,   # 7   (12 x6, 13)
    'V': 16.00,   # BACK-SOLVED from the 26 pt "Traffic Volume" total (148 px);
                  # absorbs any error in the estimated 'f'
    'v': 13.00,   # 1
    'w': 16.00,   # 1
    'x': 13.00,   # 1
    'y': 12.00,   # 1
    # punctuation / space
    ' ':  5.20,   # 8 space-crossing deltas, back-solved: 4.5..6.4, mean 5.2
    '.':  5.50,   # ESTIMATED (back-solved from two ". " deltas of 10,11)
    '&': 20.80,   # ESTIMATED (one "& " delta of 26 minus space)
    '/':  9.00,   # 1
}

INK26 = {
    '&': 19, '.': 2, '/': 7,
    'A': 17, 'C': 16, 'D': 15, 'E': 10, 'F': 10, 'G': 16, 'I': 3, 'J': 8,
    'L':  9, 'M': 20, 'P': 10, 'R': 11, 'T': 13, 'W': 24,
    'a': 11, 'b': 11, 'c': 10, 'd': 11, 'e': 11, 'f': 6, 'g': 11, 'i': 3,
    'l':  3, 'm': 15, 'n': 10, 'o': 12, 'p': 10, 'r':  7, 's': 7, 't': 6,
    'u': 10, 'V': 14, 'v': 12, 'w': 15, 'x': 11, 'y': 11, ' ': 0,
}

REF_SIZE = 26.0          # the size the tables above were measured at
DELTA    = 0.70          # px lost per glyph to per-glyph advance rounding
                         # (fit over 17 strings measured at both 13 and 26 pt;
                         #  per-string spread 0.39..1.08, sd 0.16)

# =============================================================================
#  MEASURED STRING WIDTHS -- the ground truth this model must reproduce
# =============================================================================

# Legend labels, 13 pt, ink width in px, from the two stock captures.
INK13_LEGEND = {
    "Income":         33,   # graphs-stock-ref.png     x 910..942
    "Expenses":       42,   # graphs-stock-ref.png     x 910..951
    "Capacity":       42,   # graphs-stock-garbage.png x 926..967
    "Total Garbage":  69,   # graphs-stock-garbage.png x 925..993
    "Imported":       41,   # x 926..966
    "Exported":       41,   # x 926..966
    "Landfill":       34,   # x 926..959
    "Recycled":       42,   # x 926..967
    "Incinerated":    53,   # x 926..978
    "Waste to":       41,   # x 926..966   (stock WRAPS "Waste to Energy" here)
    "Energy":         33,   # x 926..958
    "Garbage":        42,   # x 926..967   (stock WRAPS "Garbage Pollution")
    "Pollution":      40,   # x 926..965
}

# Chart-selection radio list, same font metrics, 13 pt and 26 pt.
# (17 of these have a partner at 26 pt; they are the linearity instrument.)
PAIRS_13_26 = {
    "Crime":                (28,  59),
    "Commute Time":         (69, 151),
    "Power":                (29,  61),
    "Water":                (30,  65),
    "Air Pollution":        (59, 123),
    "Water Pollution":      (73, 156),
    "Garbage":              (42,  88),
    "Education":            (45,  97),
    "Education by Age":     (83, 177),
    "Population by Age":    (87, 185),
    "Res. Avg. Income":     (80, 170),
    "City Income/Expenses": (100, 216),
    "Funds":                (26,  55),
    "RCI Demand":           (59, 126),
    "Mayor Rating":         (63, 133),
    "Traffic Volume":       (69, 148),
    "Income":               (33,  70),   # legend, Legend style, 26 pt capture
}

# The full legend label sets, in the order the game lists them.
LABELS_PLAIN   = ["Income", "Expenses"]
LABELS_GARBAGE = ["Capacity", "Total Garbage", "Imported", "Exported",
                  "Landfill", "Recycled", "Incinerated",
                  "Waste to Energy", "Garbage Pollution"]

# Shipped Legend point sizes per tier (tools\fonts\make_fontstyle.py,
# round-half-up, SIZE_SQUEEZE = {"Legend": 0.92}).
LEGEND_PT = {           # f     : (squeezed, unsqueezed)
    1.0:  (13, 13),
    1.5:  (18, 20),     # floor(13*1.5*0.92+.5)=18 ; floor(13*1.5+.5)=20
    2.0:  (24, 26),
    3.0:  (36, 39),
}


# =============================================================================
#  THE EXTENT FUNCTION
# =============================================================================

def _unit_adv(ch, delta=DELTA):
    """IDEAL (pre-rounding) advance of `ch` in px per point.

    ADV26[] holds the *rendered* advance at 26 pt, i.e. already after the
    engine's per-glyph rounding, so the ideal advance is ADV26 + delta.
    Spaces carry no outline and take no rounding loss.
    """
    if ch not in ADV26:
        raise KeyError("no measured advance for %r -- add it or the model "
                       "is guessing" % ch)
    return (ADV26[ch] + (0.0 if ch == ' ' else delta)) / REF_SIZE


def _unit_ink(ch):
    return INK26.get(ch, 0) / REF_SIZE


def advance_width(text, size, delta=DELTA):
    """Pen width of `text` at `size` points, in px (float).

        W(s,S) = S * SUM_c ideal_unit_advance(c)  -  n_glyphs(s) * delta

    The `delta` term is the MEASURED per-glyph advance-rounding loss.  It is
    what makes 13 pt -> 26 pt come out at x2.13 instead of x2.00.  At S = 26
    the two delta terms cancel and W is exactly the sum of the measured
    26 pt advances -- the tables are anchored there.
    """
    total = sum(_unit_adv(c, delta) for c in text) * float(size)
    n = sum(1 for c in text if c != ' ')
    return total - n * delta


def ink_width(text, size, delta=DELTA):
    """Ink (blackbox) width -- what a pixel ruler on a screenshot measures.
    Equals the pen width minus the trailing glyph's right side bearing."""
    if not text:
        return 0.0
    last = text[-1]
    w = advance_width(text, size, delta)
    rsb26 = ADV26[last] - INK26.get(last, 0)
    return w - rsb26 * float(size) / REF_SIZE


def fits(text, size, box_w, delta=DELTA):
    return advance_width(text, size, delta) <= box_w + 1e-9


# =============================================================================
#  THE WRAP SIMULATOR
#  Models cIGZFont::CalculateWordsToFitInWidth (0x009BF4B3): greedy word wrap,
#  and when a single word cannot fit on a line of its own, break it after the
#  last character that fits.
# =============================================================================

def wrap(text, size, box_w, delta=DELTA):
    lines, cur = [], ""
    for word in text.split(" "):
        cand = word if not cur else cur + " " + word
        if fits(cand, size, box_w, delta):
            cur = cand
            continue
        if cur:
            lines.append(cur)
            cur = ""
        # `word` alone on a fresh line
        while word and not fits(word, size, box_w, delta):
            k = len(word)
            while k > 1 and not fits(word[:k], size, box_w, delta):
                k -= 1
            lines.append(word[:k])
            word = word[k:]
        cur = word
    if cur:
        lines.append(cur)
    return lines


def break_after(text, size, box_w, delta=DELTA):
    """The rendered first line -- i.e. where the label visibly breaks."""
    return wrap(text, size, box_w, delta)[0]


# =============================================================================
#  SELF-CHECK -- the model must reproduce the measurements it was built from
# =============================================================================

TOL = 4.0   # px. Max residual actually observed is 3.8 px, on the three
            # strings that contain a SPACE -- the space advance (5.2 px at
            # 26 pt) is the single least-well-measured metric in the table
            # (back-solved from 8 space-crossing pen deltas, spread 4.5..6.4).


def selfcheck(verbose=True):
    bad = 0
    if verbose:
        print("=" * 74)
        print("A. 26 pt reconstruction (per-glyph table -> whole strings)")
        print("=" * 74)
        print("%-22s %6s %6s %6s" % ("label", "meas", "model", "err"))
    for lab, (w13, w26) in sorted(PAIRS_13_26.items()):
        m = ink_width(lab, 26.0)
        e = m - w26
        if abs(e) > TOL:
            bad += 1
        if verbose:
            print("%-22s %6d %6.1f %+6.1f%s" % (lab, w26, m, e,
                                                "   <-- FAIL" if abs(e) > TOL else ""))
    if verbose:
        print()
        print("=" * 74)
        print("B. 13 pt prediction  (the real test: 26 pt tables + DELTA -> 13 pt)")
        print("=" * 74)
        print("%-22s %6s %6s %6s" % ("label", "meas", "model", "err"))
    errs = []
    src = dict((k, v[0]) for k, v in PAIRS_13_26.items())
    src.update(INK13_LEGEND)
    for lab in sorted(src):
        m = ink_width(lab, 13.0)
        e = m - src[lab]
        errs.append(e)
        if abs(e) > TOL:
            bad += 1
        if verbose:
            print("%-22s %6d %6.1f %+6.1f%s" % (lab, src[lab], m, e,
                                                "   <-- FAIL" if abs(e) > TOL else ""))
    if verbose:
        n = len(errs)
        mean = sum(errs) / n
        sd = (sum((x - mean) ** 2 for x in errs) / n) ** 0.5
        print()
        print("  n=%d  mean err %+.2f px  sd %.2f px  max |err| %.2f px"
              % (n, mean, sd, max(abs(x) for x in errs)))
        print()
        print("  %d check(s) outside +-%.1f px" % (bad, TOL))
    return bad


# =============================================================================
#  THE ANSWER TABLES
# =============================================================================

BOXES = [72, 88, 140, 144]

def table_sizes():
    print("=" * 92)
    print("LEGEND LABEL PEN WIDTHS (px) -- shipped Legend point size per tier")
    print("  sq = with SIZE_SQUEEZE 0.92 (shipped)   raw = f x 13 unsqueezed")
    print("=" * 92)
    cols = [("1x", 13), ("1.5x sq", 18), ("1.5x raw", 20),
            ("2x sq", 24), ("2x raw", 26), ("3x sq", 36), ("3x raw", 39)]
    print("%-20s" % "label" + "".join("%9s" % c[0] for c in cols))
    for lab in LABELS_PLAIN + LABELS_GARBAGE:
        print("%-20s" % lab + "".join("%9.1f" % advance_width(lab, s)
                                      for _, s in cols))
    print()


def table_fit():
    print("=" * 92)
    print("FITS IN BOX?  pen width vs box width.  Y = fits on one line.")
    print("=" * 92)
    for size in (13, 24, 26):
        print("-- Legend %d pt --" % size)
        print("%-20s %8s" % ("label", "width") +
              "".join("%8s" % ("box %d" % b) for b in BOXES))
        for lab in LABELS_PLAIN + LABELS_GARBAGE:
            w = advance_width(lab, size)
            print("%-20s %8.1f" % (lab, w) +
                  "".join("%8s" % ("Y" if w <= b else "n") for b in BOXES))
        print()


def table_wrap():
    print("=" * 92)
    print("PREDICTED WRAP -- first rendered line for each box width")
    print("=" * 92)
    for size in (13, 24, 26):
        for b in BOXES:
            print("-- Legend %d pt, box %d px --" % (size, b))
            for lab in LABELS_PLAIN + LABELS_GARBAGE:
                ls = wrap(lab, size, b)
                print("   %-20s %s" % (lab, " / ".join(ls)))
            print()


# The wrapping the user reports seeing at 2x (task #57 brief).  Each entry is
# the visible break: (label, text before the break, text after it).
USER_REPORT_2X = [
    ("Capacity",      "Capaci",      "ty"),
    ("Total Garbage", "Total Garba", "ge"),
    ("Imported",      "Import",      "ed"),
    ("Recycled",      "Recycl",      "ed"),
    ("Incinerated",   "Inciner",     "ated"),
]

# The ORIGINAL #57 report, before the 0.92 SIZE_SQUEEZE: the plain
# Income/Expenses chart at 2x rendered "Expense / s".  Independent regression
# case for the model -- and the reason the squeeze exists.
HISTORIC_2X = [("Expenses", 26, 88, ["Expense", "s"])]


def _score(lab, before, after, size, box):
    """0 = no match, 1 = the reported break appears somewhere in the wrap,
    2 = ... and it is exact; 'near' = off by exactly one character."""
    lines = wrap(lab, size, box)
    for i in range(len(lines) - 1):
        if lines[i].endswith(before) and lines[i + 1].startswith(after[:1]):
            if lines[i] == before or lines[i].endswith(before):
                return "exact" if (lines[i] == before or
                                   "".join(lines[:i + 1]).replace(" ", "") ==
                                   before.replace(" ", "")) else "hit"
    # tolerance: one character either side
    flat = []
    pos = 0
    for i, l in enumerate(lines[:-1]):
        pos += len(l)
        flat.append(pos)
        if lab[pos:pos + 1] == " ":
            pos += 1
    want = len(before)
    if any(abs(p - want) <= 1 for p in flat):
        return "near"
    return "-"


def table_user_report():
    print("=" * 92)
    print("ADJUDICATION: which (Legend pt, box px) reproduces what the user sees?")
    print("  'exact'  the model breaks the label at exactly the reported place")
    print("  'near'   the model breaks it one character away (model err is +-1.5 px)")
    print("=" * 92)
    hyps = [(s, b) for s in (24, 26) for b in BOXES]
    print("%-20s %-14s" % ("label", "user sees") +
          "".join("%-11s" % ("%dpt/%d" % h) for h in hyps))
    tally = dict((h, [0, 0]) for h in hyps)
    for lab, before, after in USER_REPORT_2X:
        row = "%-20s %-14s" % (lab, before + "/" + after)
        for h in hyps:
            v = _score(lab, before, after, h[0], h[1])
            if v in ("exact", "hit"):
                tally[h][0] += 1
            elif v == "near":
                tally[h][1] += 1
            row += "%-11s" % v
        print(row)
    print()
    print("  score (exact + near, out of 5):")
    for h in hyps:
        e, n = tally[h]
        print("    Legend %2d pt, box %3d px : %d exact, %d near   -> %d/5"
              % (h[0], h[1], e, n, e + n))
    print()
    print("  full predicted wrap at the two winning hypotheses:")
    for s in (24, 26):
        print("   -- Legend %d pt, box 72 px --" % s)
        for lab in LABELS_GARBAGE:
            print("      %-20s %s" % (lab, " / ".join(wrap(lab, s, 72))))
    print()
    print("  INDEPENDENT REGRESSION (the original, pre-squeeze #57 report):")
    for lab, s, b, want in HISTORIC_2X:
        got = wrap(lab, s, b)
        print("    plain chart, Legend %d pt, box %d px: %-20s reported %s   %s"
              % (s, b, " / ".join(got), " / ".join(want),
                 "MATCH" if got == want else "MISMATCH"))
    print()


def table_stock_control():
    print("=" * 92)
    print("STOCK CONTROL -- what box width reproduces STOCK's own wrapping?")
    print("  stock FACTS: 'Total Garbage' fits on one line;")
    print("               'Waste to Energy' and 'Garbage Pollution' both wrap.")
    print("=" * 92)
    lo, hi = None, None
    for b in range(50, 130):
        ok = (len(wrap("Total Garbage", 13, b)) == 1 and
              len(wrap("Waste to Energy", 13, b)) > 1 and
              len(wrap("Garbage Pollution", 13, b)) > 1)
        if ok:
            if lo is None:
                lo = b
            hi = b
    print("  admissible stock checkbox-legend box width: %s..%s px" % (lo, hi))
    print("    W('Total Garbage'  ,13) = %6.1f  (must fit)" % advance_width("Total Garbage", 13))
    print("    W('Waste to Energy',13) = %6.1f  (must NOT fit)" % advance_width("Waste to Energy", 13))
    print("    W('Garbage Pollution',13)=%6.1f  (must NOT fit)" % advance_width("Garbage Pollution", 13))
    print()
    print("  measured OUR-2x checkbox-legend box = 72 px (SC4UIScale.log v2.54.4)")
    print("  => the 2x box is INSIDE the stock 1x admissible band. It did not scale.")
    print()
    print("  GEOMETRIC CORROBORATION (independent of the wrap evidence).")
    print("  Distance from the legend text-box left edge to the chart panel's")
    print("  client right edge, measured on the captures:")
    print("    stock 1x  panel client right x=1005 | plain text left  909 -> 96 px")
    print("                                        | c'box text left  925 -> 80 px")
    print("    ours  2x  panel client right x=2003 | plain text left 1903 -> 100 px")
    print("                                        | c'box text left 1919 ->  84 px")
    print("  Identical to within the +4 px legend-rect widening v2.53.2 adds.")
    print("  A box that scaled by f=2 would read ~192 / ~160 px. It does not.")
    print("  => BOTH legend boxes (88 plain / 72 checkbox) are 1x CODE CONSTANTS")
    print("     that pass through our EARLYCHART unscaled. 88 is NOT 2 x 44.")
    print()


def table_required_box():
    print("=" * 92)
    print("REQUIRED BOX WIDTH -- narrowest box that wraps NO MORE than stock does")
    print("  (stock wraps exactly 'Waste to Energy' and 'Garbage Pollution')")
    print("=" * 92)
    print("%-10s %-8s %-14s %-14s %s" % ("tier", "pt", "widest label", "needs px",
                                         "stock-parity box"))
    for f in (1.0, 1.5, 2.0, 3.0):
        for which, idx in (("sq", 0), ("raw", 1)):
            pt = LEGEND_PT[f][idx]
            widest, wmax = None, -1
            for lab in LABELS_GARBAGE:
                # stock leaves these two wrapped, so they do not set the bar
                if lab in ("Waste to Energy", "Garbage Pollution"):
                    continue
                w = advance_width(lab, pt)
                if w > wmax:
                    wmax, widest = w, lab
            # box must also still wrap the two that stock wraps
            need_lt = min(advance_width("Waste to Energy", pt),
                          advance_width("Garbage Pollution", pt))
            print("%-10s %-8d %-14s %-14.1f %d .. %d" %
                  ("%gx %s" % (f, which), pt, widest, wmax,
                   int(wmax) + 1, int(need_lt)))
    print()
    print("  NOTE the invariant: at every tier the stock-parity box is very close")
    print("  to  round(72 * pt / 13)  -- i.e. the box must scale WITH THE FONT,")
    print("  not with the window.  At 2x/24pt that is 133..141 px, not 72.")
    print()


# =============================================================================
#  --extract : re-derive the tables from the captures
# =============================================================================

def extract():
    from PIL import Image
    import os
    base = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                        "..", "..", "..", "_tests", "captures"))
    def lum(q):
        return 0.299 * q[0] + 0.587 * q[1] + 0.114 * q[2]

    def segs(px, X0, X1, y0, y1, thr):
        cols = [x for x in range(X0, X1)
                if any(lum(px[x, y]) < thr for y in range(y0, y1))]
        if not cols:
            return []
        out = []
        c0 = pr = cols[0]
        for x in cols[1:]:
            if x > pr + 1:
                out.append((c0, pr))
                c0 = x
            pr = x
        out.append((c0, pr))
        return out

    print("captures dir:", base)
    im = Image.open(os.path.join(base, "graphs-stock-garbage.png")).convert("RGB")
    px = im.load()
    ROWS = [(361, 372, "Capacity"), (380, 391, "Total Garbage"),
            (414, 425, "Imported"), (433, 444, "Exported"),
            (467, 475, "Landfill"), (486, 497, "Recycled"),
            (505, 513, "Incinerated"), (524, 532, "Waste to"),
            (539, 550, "Energy"), (558, 569, "Garbage"),
            (573, 581, "Pollution")]
    print("\n-- stock 13 pt legend ink widths (graphs-stock-garbage.png) --")
    for y0, y1, lab in ROWS:
        s = segs(px, 922, 1004, y0, y1 + 1, 170)
        w = s[-1][1] - s[0][0] + 1
        flag = "" if INK13_LEGEND.get(lab) == w else "   <-- differs from baked table"
        print("  %-16s x %d..%d  w=%d%s" % (lab, s[0][0], s[-1][1], w, flag))

    im2 = Image.open(os.path.join(base, "graphs-stock-ref.png")).convert("RGB")
    px2 = im2.load()
    print("\n-- stock 13 pt legend ink widths (graphs-stock-ref.png) --")
    for y0, y1, lab in [(361, 369, "Income"), (380, 391, "Expenses")]:
        s = segs(px2, 907, 1004, y0, y1 + 1, 170)
        w = s[-1][1] - s[0][0] + 1
        print("  %-16s x %d..%d  w=%d" % (lab, s[0][0], s[-1][1], w))

    im3 = Image.open(os.path.join(base, "graphs-ours-2x.png")).convert("RGB")
    px3 = im3.load()
    print("\n-- ours 2x, Legend 26 pt (graphs-ours-2x.png) --")
    for y0, y1, lab in [(688, 705, "Income"), (720, 743, "Expense"),
                        (754, 765, "s")]:
        s = segs(px3, 1900, 2000, y0, y1 + 1, 170)
        print("  %-16s x %d..%d  w=%d" % (lab, s[0][0], s[-1][1],
                                          s[-1][1] - s[0][0] + 1))
    print("\n-- chart panel client right edge (both captures) --")
    for nm, im_, y in (("graphs-stock-garbage.png", px, 450),
                       ("graphs-ours-2x.png", px3, 800)):
        x = 950 if nm.startswith("graphs-stock") else 1950
        while x < 2100:
            try:
                c = im_[x, y]
            except IndexError:
                break
            if c != (218, 224, 229):
                break
            x += 1
        print("  %-26s light chart bg ends at x=%d" % (nm, x - 1))


def main():
    args = sys.argv[1:]
    if "--extract" in args:
        extract()
        return
    if "--selfcheck" in args:
        sys.exit(1 if selfcheck() else 0)
    selfcheck()
    print()
    table_sizes()
    table_fit()
    table_stock_control()
    table_user_report()
    table_required_box()
    if "--wrap" in args:
        table_wrap()


if __name__ == "__main__":
    main()
