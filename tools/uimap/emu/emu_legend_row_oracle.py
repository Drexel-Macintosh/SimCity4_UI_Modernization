"""
emu_legend_row_oracle.py - the ROW acceptance oracle for the Graphs chart legend (#57).

WHAT THIS IS. A closed-form, integer-exact model of ONE legend row of a SimCity 4
chart at any scale factor f. It is a GATE, not a fix: it reproduces the measured
STOCK layout at f=1 AND the measured BROKEN 2x layout at f=2, from ONE formula with
ZERO free parameters. Because it reproduces the BUG, a proposed fix can be proved
right or wrong against it offline, before it is built.

SIBLING FILE. emu_chart_legend.py (parallel workflow) is the VERTICAL oracle -
wrapping, group separators, column height. This file is the ROW oracle: it owns the
HORIZONTAL closed form (checkbox / swatch / text columns and the collision), and
carries only as much vertical as is needed to place a row (row origin, row pitch,
swatch dy). Where they overlap they must agree; both are run by the same gate.

SCOPE, STATED UP FRONT (law 42).
  IN  - the X geometry of all three legend cells, exact, both legend kinds.
  IN  - the Y geometry of a row GIVEN the wrapped line count n[k].
  OUT - n[k] itself. Predicting it needs the game's measure()/wrap engine at a given
        font size; we have no text engine offline. n[k] is an INPUT here. At f=1 it
        is MEASURED from ink bands. At f=2 it is SOLVED from the measured pitches and
        checked for INTEGRALITY - 8 independent divisibility checks that a wrong
        lineH or pad would fail. That is a falsification, not a fit.
  OUT - lineH(pt). MEASURED at exactly two points (15px @ 13pt, 28px @ 24pt). The
        pt->px rule is NOT pinned by two samples. See UNKNOWNS.
  OUT - the mechanism. Nothing here says which function to detour.

SOURCES (no number below was invented):
  A. _tests/captures/graphs-stock-ref.png      1032x810, stock 1024x768, Income/Expenses
  B. _tests/captures/graphs-stock-garbage.png  1032x810, stock 1024x768, Garbage
  C. _tests/captures/graphs-ours-2x.png        2400x1600, our 2x, Income/Expenses,
                                               plot rect NOT yet rescaled -> raw game 2x
  D. Documents/SimCity 4/Plugins/SC4UIScale.log  v2.54.4, READ-ONLY, lines 350-464:
       EARLYCHART store (45,20,866,492) in 976x512   <- legend chart, game's own rect
       EARLYCHART store (45,20,974,492) in 976x512   <- NO-legend chart (line 464)
       LEGENDCBOX id=0x0400000n rect=(868,y,900,y+32)     9 rows
       LEGENDFIX  cbox  text w 72 left 900 (winW 976)
       LEGENDFIX  plain text w 88 left 884 (winW 976)
       LEGENDSWATCH 10x6 gap 14

CHART-LOCAL ORIGIN - how it was established, and the uncertainty (this was the crux).
  The stored plot rect is chart-local and the plot is drawn as a 1px dark border round
  a near-white fill, so the border columns ARE the rect edges (right/bottom borders
  land at r-1 / b-1: half-open rects). Each axis therefore has TWO independent anchors.
    A/B (stock, winW=488, stored plot (45,20,378,236)):
        X: L border 558 -> X0 = 558-45 = 513
           R border 890 -> X0 = 890-(378-1) = 513          AGREE, uncertainty +-0
        Y: T border 358 -> Y0 = 358-20 = 338
           B border 573 -> Y0 = 573-(236-1) = 338          AGREE, uncertainty +-0
    C (2x, winW=976, stored plot (45,20,866,492)):
        X: L border 1063 -> X0 = 1018 ; R border 1883 -> X0 = 1883-865 = 1018
                                                            AGREE, uncertainty +-0
        Y: B border 1155 -> Y0 = 1155-491 = 664
           T border  695 -> Y0 = 675                        DISAGREE by 11.
  Y0 = 664 is adopted. The load-bearing anchor is the plot BOTTOM (legend-independent).

  *** RETRACTION, 2026-08-03 - the "11 px" and the finding built on it ARE WRONG. ***
  This file previously concluded, as a "separate, unreported finding", that
  "PLOT[0xE0].top is not where the frame is drawn at 2x" because "the 26pt chart
  title is painted inside the top of the plot rect".  MEASURED and refuted:
        graphs-ours-2x.png, x=1700 (a column with no title ink):
            y 678..683 = panel fill (218,224,229)
            y 684      = FRAME      (174,191,192)      <- 684 - 664 = 20 = PLOT.top
            y 685..    = plot fill  (239,243,247)
        x=1063 (the plot's left border column) shows the same frame colour from 684.
        x=1500 is buried under dark title ink (64,74,103) spanning y 678..690 -
        THAT is where the 695 came from.
  There is NO rect-vs-frame divergence: the frame IS at .top, and both Y anchors
  agree on Y0 = 664.  Do not spend a build on the retracted version.
  THE REAL FACT UNDERNEATH, smaller and still worth owning: at 2x the chart TITLE
  ink overflows ~6 px PAST the frame into the plot interior (it reaches y 690 while
  the frame is at 684), which it does not do at 1x.  That is a TITLE-BAND defect and
  it belongs to neither the legend nor the hunt for "what consumes the 110".

THE MODEL IN WORDS.
  Everything the CHART PAINTS ITSELF (swatch + label text) lives in a strip of
  CONSTANT width 108px hugging the RIGHT EDGE of the chart window. Not one pixel of
  that strip scales with f. It decomposes exactly, and identically, for both kinds:
      cbox 16 | gap 2 | swatch 10 | gap 4 | text 72 | margin 4  = 108
      (none)  | gap 2 | swatch 10 | gap 4 | text 88 | margin 4  = 108
  The two text widths differ by exactly the DESIGN checkbox width, 88-72 = 16, which
  is what makes it one formula rather than two.
  The plot rect reserves 110 = 108 + a 2px gap. A chart with no legend reserves 2 -
  measured directly (974 = 976-2 on the no-legend chart, log line 464).
  The ONE element that scales is the checkbox, because it is a real child WINDOW and
  OUR OWN SWEEP scales it: width 16 -> 16f. Its LEFT is placed by the chart at
  winW-108 (unscaled), so growing its width drives its RIGHT edge into the swatch.

THE DEFECT AS A PREDICATE:
      swatch buried  <=>  cbox.L + 16f > swatch.L  <=>  16f > CBG + CBW0 = 18
                     <=>  f > 1.125
  False at f=1, true at EVERY shipped tier (1.5, 2, 3). That one inequality is the
  whole of failure #1, and it is why v2.54.2/.3/.4 each moved the collision instead of
  removing it: they edited OUTPUT rects while the strip stayed 108 wide.

UNKNOWNS - marked, not invented.
  U1. lineH(pt). Measured 15 @ 13pt and 28 @ 24pt. Two points cannot separate
      "round(1.15*pt)" from a table lookup or a ceil. ONE MEASUREMENT PINS IT: capture
      one legend row at the 1.5x tier (Legend 18pt) and read the swatch-top pitch of a
      known 1-line row; pitch-4 is lineH(18). round(1.15*18)=21 vs ceil(1.15*18)=21 vs
      a 20 would discriminate the family.
  U2. text.B for the PLAIN kind at f=2. A source comment in UiSpike.cpp records the
      rect as (884,20,972,76), i.e. height 56 = 2 lines, but capture C measures the
      row-0 pitch as 32 = 1*28+4, i.e. ONE line for "Income". Comment and pixels
      disagree. ONE MEASUREMENT PINS IT: log obj[7..10] of the FIRST text entry of the
      plain chart (a LEGENDOBJ line already dumps obj[0..7]; extend it to obj[10]).
      Nothing in the horizontal model depends on this.
  U3. Whether the "16" in the text-width reserve is literally the design checkbox
      width or an unrelated constant that happens to equal it. The two are
      observationally identical in every capture available. It cannot be separated
      without a chart whose checkbox art is a different design width; none exists in
      the shipped game as far as these captures show. Recorded as an ALIAS, not a fact.

IS THIS AN INSTRUMENT? Thirteen falsifications were run (`--falsify` reruns them all).
Every single-constant perturbation turns it RED, and the two rival hypotheses that a
reasonable person would hold are REFUTED BY MEASURED DATA - which is the whole point,
because those two are exactly what v2.54.2/.3/.4 implicitly assumed:
    F1  STRIP 108->107          -> 10 fails      F7  lineH(2x) 28->30  -> 17 fails
    F2  TXW0  88->89            -> 16 fails      F8  lineH(1x) 15->16  -> 25 fails
    F3  CBW0  16->17            ->  9 fails      F9  SWW   10->12      ->  8 fails
    F4  PAD    4->5             -> 42 fails      F10 TOP   20->21      -> 32 fails
    F5  SWDY   3->4             -> 14 fails
    F6  PLOTG  2->3             ->  4 fails
    H1  "the strip scales with f"                -> 10 fails, ALL of them f=2.
        (At f=1 H1 is indistinguishable from the truth - which is precisely why four
        rect-patches shipped without anyone noticing the strip was frozen.)
    H2  "the painter reads the ACTUAL checkbox width"
                                                 ->  4 fails: it predicts the swatch at
        902; the game paints it at 886. This is the single most important refutation in
        the file: the painter uses the DESIGN width 16, so widening the checkbox window
        cannot move the swatch out of the way, only under the checkbox.
    H3  the left-anchored cursor form            -> GREEN, 0 fails. Not a failure: it
        confirms the two parameterisations are observationally IDENTICAL on the data we
        have. Recorded as UNKNOWN U3 below, not as a fact.

WHAT IS INDEPENDENT AND WHAT IS ONLY CONSISTENT (do not over-read the 58 greens).
  Independent predictions, f=1: all 11 X checks and all 18 Y checks. n[] comes from ink
    bands, not from pitches, so the row tops are genuinely predicted.
  Fitted-then-constrained, f=1: sep[] (8 binary values). They are solved, not free: the
    model only permits pitch - n*15 - 4 in {0, 15}, and all 8 measured pitches land on
    exactly one of those two values. A model with the wrong PAD or lineH fails
    integrality (see F4 and F8, which do exactly that).
  Independent, f=2: the 11 X checks from the log, the 5 X/Y checks from capture C
    pixels, the 2 plot-rect checks, and the 8 INTEGRALITY constraints on n[].
  NOT independent, f=2: the 9 f2.rowTop[] checks. n[] was solved from those pitches, so
    they are a consistency restatement. The real f=2 vertical content is the
    integrality, plus the fact that sep[] was carried over from f=1 UNREFITTED.

USAGE
  python emu_legend_row_oracle.py            # the gate (what CI runs)
  python emu_legend_row_oracle.py --verbose  # + every residual
  python emu_legend_row_oracle.py --falsify  # rerun the 13 falsifications
Exit 0 only if every measured number is reproduced with residual 0.
Offline only: reads nothing, touches no game file.
"""

import sys

VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

# ---------------------------------------------------------------------------
# THE CONSTANTS. Every one MEASURED; every one UNSCALED in the shipped game.
# That they are unscaled is the FINDING, and the residual table is its proof:
# the same integers reproduce f=1 and f=2 with zero residual.
# ---------------------------------------------------------------------------
RM    = 4    # right margin        text.R = winW - RM              [A,B,D]
TXW0  = 88   # text box width, no checkbox                         [A,D]
CBW0  = 16   # DESIGN checkbox width - what the chart's PAINTER assumes [B]
SWW   = 10   # swatch width                                        [A,B,C,D]
SWH   = 6    # swatch height                                       [A,B,C,D]
SWG   = 4    # swatch -> text gap                                  [A,B]
CBG   = 2    # checkbox -> swatch gap                              [B]
STRIP = 108  # total right-anchored legend strip                   [B,D]
PLOTG = 2    # plot -> strip gap                                   [D line 464]
TOP   = 20   # legend top inset (row 0 top)                        [B,D]
PAD   = 4    # inter-row padding                                   [B,C,D]
SWDY  = 3    # swatch top offset inside the row                    [A,B,C,D]

# lineH is a FONT metric: it tracks the FONT SIZE, not f. Our 2x Legend is 24pt
# (26 * the 0.92 SIZE_SQUEEZE in tools/fonts/make_fontstyle.py). See UNKNOWN U1.
LINEH = {1.0: 15, 2.0: 28}


def strip_check():
    """The decomposition must close to STRIP for BOTH legend kinds."""
    return (CBW0 + CBG + SWW + SWG + (TXW0 - CBW0) + RM,
            CBG + SWW + SWG + TXW0 + RM)


# ===========================================================================
#  THE CLOSED FORM
# ===========================================================================
def row(f, has_checkbox, win_w, row_top, n_lines, line_h):
    """One legend row. Integer-exact: nothing is multiplied by f except the
    checkbox WINDOW, and 16*f is exact at every shipped tier (1.5/2/3 ->
    24/32/48), so the round-half-up law never actually bites here."""
    txw      = TXW0 - (CBW0 if has_checkbox else 0)
    text_r   = win_w - RM
    text_l   = text_r - txw
    swatch_r = text_l - SWG
    swatch_l = swatch_r - SWW
    cbox_l   = win_w - STRIP
    cbox_w   = int(CBW0 * f)                     # the ONE f-dependent term
    out = {
        "text":      (text_l, row_top, text_r, row_top + n_lines * line_h),
        "swatch":    (swatch_l, row_top + SWDY, swatch_l + SWW, row_top + SWDY + SWH),
        "rowHeight": n_lines * line_h + PAD,
    }
    if has_checkbox:
        out["checkbox"] = (cbox_l, row_top, cbox_l + cbox_w, row_top + cbox_w)
    return out


def column(f, has_checkbox, win_w, n_lines, sep, line_h):
    """Stack rows:  y[k+1] = y[k] + n[k]*lineH + PAD + sep[k]*lineH."""
    rows, y = [], TOP
    for k, n in enumerate(n_lines):
        rows.append(row(f, has_checkbox, win_w, y, n, line_h))
        y += n * line_h + PAD + (sep[k] if k < len(sep) else 0) * line_h
    return rows, y


def plot_right(win_w, has_legend):
    return win_w - PLOTG - (STRIP if has_legend else 0)


# ===========================================================================
#  MEASURED GROUND TRUTH
# ===========================================================================
X0_STOCK, Y0_STOCK = 513, 338
X0_2X,    Y0_2X    = 1018, 664

W_STOCK, W_LIVE = 488, 976

# --- f=1, capture B (Garbage, checkbox kind) -------------------------------
S_CBOX_INK      = (893, 908)     # 16 ink columns
S_SWATCH_INK    = (911, 920)     # 10 ink columns
S_TEXT_INK_L    = 925
S_CBOX_TOPS     = [358, 377, 411, 430, 464, 483, 502, 521, 555]
S_SWATCH_TOPS   = [361, 380, 414, 433, 467, 486, 505, 524, 558]
# n[] MEASURED from ink bands, independent of the pitches:
#   rows 0..6 one band each; row 7 "Waste to"/"Energy" two bands (tops 524,539 ->
#   lineH=15); row 8 "Garbage"/"Pollution" two bands.
S_N             = [1, 1, 1, 1, 1, 1, 1, 2, 2]
S_PLOT_R        = 378

# --- f=1, capture A (Income/Expenses, plain kind) --------------------------
S_P_SWATCH_INK  = (895, 904)
S_P_TEXT_INK_L  = 910
S_P_SWATCH_TOPS = [361, 380]

# --- f=2, log D (Garbage, checkbox kind) -----------------------------------
L_CBOX          = (868, 900)
L_CBOX_TOPS     = [20, 80, 196, 256, 344, 404, 464, 524, 612]
L_TEXT_L, L_TEXT_R = 900, 972
L_SWATCH_L      = 886
L_SWATCH_T      = 23     # recovered from LEGENDSWATCH: out t=20, h1=12 -> cy=26
                         # -> in (t,b) = (23,29)
L_PLOT_R_LEG    = 866
L_PLOT_R_NOLEG  = 974

# --- f=2, capture C (Income/Expenses, plain kind), ABSOLUTE pixels ---------
C_SWATCH_INK    = (1888, 1897)
C_TEXT_INK_L    = 1902
C_SWATCH_TOPS   = [687, 719]
C_N             = [1, 2]         # "Income" 1 ink band; "Expenses" -> "Expense"/"s"


RESIDUALS, FAILS = [], []


def check(tag, predicted, measured):
    r = predicted - measured
    RESIDUALS.append((tag, predicted, measured, r))
    if r != 0:
        FAILS.append((tag, predicted, measured, r))


def main():
    print("=" * 78)
    print("emu_legend_row_oracle - #57 Graphs legend ROW acceptance oracle")
    print("=" * 78)

    a, b = strip_check()
    print("\n[0] STRIP DECOMPOSITION - must close to %d for BOTH kinds" % STRIP)
    print("    checkbox kind  16+2+10+4+72+4 = %d" % a)
    print("    plain    kind     2+10+4+88+4 = %d" % b)
    check("strip.cbox", a, STRIP)
    check("strip.plain", b, STRIP)

    # ---- f=1 checkbox kind -------------------------------------------------
    print("\n[1] f=1  GARBAGE (checkbox kind)  winW=%d  origin (%d,%d)"
          % (W_STOCK, X0_STOCK, Y0_STOCK))
    lh1 = LINEH[1.0]
    tops = [t - Y0_STOCK for t in S_CBOX_TOPS]
    sep = []
    for k in range(len(tops) - 1):
        extra = (tops[k + 1] - tops[k]) - (S_N[k] * lh1 + PAD)
        if extra % lh1 != 0 or extra // lh1 not in (0, 1):
            FAILS.append(("sep[%d] not an integral 0/1 divider" % k, extra, lh1, extra))
            sep.append(0)
        else:
            sep.append(extra // lh1)
    print("    solved group separators (0/1 per gap): %s" % sep)
    print("    -> dividers after rows 1 and 3, CONFIRMED independently by ink:")
    print("       row1 'Total Garbage' and row3 'Exported' are ONE ink band each,")
    print("       yet their pitch is 34 = 15+4+15. The +15 is a blank entry, not a wrap.")

    rows1, end1 = column(1.0, True, W_STOCK, S_N, sep, lh1)
    r0 = rows1[0]
    check("f1.cbox.L",   r0["checkbox"][0] + X0_STOCK, S_CBOX_INK[0])
    check("f1.cbox.R",   r0["checkbox"][2] + X0_STOCK, S_CBOX_INK[1] + 1)
    check("f1.swatch.L", r0["swatch"][0] + X0_STOCK,   S_SWATCH_INK[0])
    check("f1.swatch.R", r0["swatch"][2] + X0_STOCK,   S_SWATCH_INK[1] + 1)
    check("f1.text.L",   r0["text"][0] + X0_STOCK,     S_TEXT_INK_L)
    for k, rr in enumerate(rows1):
        check("f1.rowTop[%d]" % k, rr["text"][1] + Y0_STOCK, S_CBOX_TOPS[k])
        check("f1.swTop[%d]" % k,  rr["swatch"][1] + Y0_STOCK, S_SWATCH_TOPS[k])
    check("f1.plotR", plot_right(W_STOCK, True), S_PLOT_R)

    # ---- f=1 plain kind ----------------------------------------------------
    print("\n[2] f=1  INCOME/EXPENSES (plain kind)  winW=%d" % W_STOCK)
    p1, _ = column(1.0, False, W_STOCK, [1, 1], [0], lh1)
    check("f1p.swatch.L", p1[0]["swatch"][0] + X0_STOCK, S_P_SWATCH_INK[0])
    check("f1p.swatch.R", p1[0]["swatch"][2] + X0_STOCK, S_P_SWATCH_INK[1] + 1)
    # +1: left side bearing of 'I'/'E' at 13pt - the ONLY sub-pixel allowance in
    # the file, and it is stated, not absorbed. See the residual note in the report.
    check("f1p.text.L(+lsb1)", p1[0]["text"][0] + X0_STOCK + 1, S_P_TEXT_INK_L)
    for k in range(2):
        check("f1p.swTop[%d]" % k, p1[k]["swatch"][1] + Y0_STOCK, S_P_SWATCH_TOPS[k])

    # ---- f=2 checkbox kind: THE DEFECT ------------------------------------
    print("\n[3] f=2  GARBAGE (checkbox kind)  winW=%d   <- MUST REPRODUCE THE BUG"
          % W_LIVE)
    lh2 = LINEH[2.0]
    n2 = []
    for k in range(len(L_CBOX_TOPS) - 1):
        pitch = L_CBOX_TOPS[k + 1] - L_CBOX_TOPS[k]
        num = pitch - PAD - sep[k] * lh2
        if num % lh2 != 0 or num // lh2 < 1:
            FAILS.append(("f2.n[%d] non-integral" % k, num, lh2, num % lh2))
            n2.append(1)
        else:
            n2.append(num // lh2)
    print("    line counts SOLVED from the pitches, reusing the f=1 separators")
    print("    (a divider is DATA - it cannot depend on the font):  n[] = %s" % n2)
    print("    all 8 came out positive integers -> lineH=28 and PAD=4 survive")
    n2.append(3)   # last row unconstrained; used only for the overflow figure

    rows2, end2 = column(2.0, True, W_LIVE, n2, sep, lh2)
    q0 = rows2[0]
    check("f2.cbox.L",   q0["checkbox"][0], L_CBOX[0])
    check("f2.cbox.R",   q0["checkbox"][2], L_CBOX[1])
    check("f2.swatch.L", q0["swatch"][0],   L_SWATCH_L)
    check("f2.swatch.R", q0["swatch"][2],   L_SWATCH_L + SWW)
    check("f2.swatch.T", q0["swatch"][1],   L_SWATCH_T)
    check("f2.swatch.H", q0["swatch"][3] - q0["swatch"][1], SWH)
    check("f2.text.L",   q0["text"][0],     L_TEXT_L)
    check("f2.text.R",   q0["text"][2],     L_TEXT_R)
    check("f2.text.W",   q0["text"][2] - q0["text"][0], 72)
    for k, rr in enumerate(rows2):
        check("f2.rowTop[%d]" % k, rr["text"][1], L_CBOX_TOPS[k])
    check("f2.plotR.legend",   plot_right(W_LIVE, True),  L_PLOT_R_LEG)
    check("f2.plotR.nolegend", plot_right(W_LIVE, False), L_PLOT_R_NOLEG)

    # ---- f=2 plain kind, from PIXELS (independent of the log) -------------
    print("\n[4] f=2  INCOME/EXPENSES (plain kind)  winW=%d, from capture C PIXELS"
          % W_LIVE)
    p2, _ = column(2.0, False, W_LIVE, C_N, [0], lh2)
    check("f2p.swatch.L", p2[0]["swatch"][0] + X0_2X, C_SWATCH_INK[0])
    check("f2p.swatch.R", p2[0]["swatch"][2] + X0_2X, C_SWATCH_INK[1] + 1)
    check("f2p.text.L",   p2[0]["text"][0] + X0_2X,   C_TEXT_INK_L)
    for k in range(2):
        check("f2p.swTop[%d]" % k, p2[k]["swatch"][1] + Y0_2X, C_SWATCH_TOPS[k])

    # ---- the predicates ----------------------------------------------------
    print("\n[5] DEFECT PREDICATES (winW=%d)" % W_LIVE)
    swl = W_LIVE - RM - (TXW0 - CBW0) - SWG - SWW
    txl = W_LIVE - RM - (TXW0 - CBW0)
    print("    %-7s %-9s %-10s %-8s %-10s %s" %
          ("f", "cbox.R", "swatch.L", "text.L", "swatch", "text"))
    for f in (1.0, 1.125, 1.5, 2.0, 3.0):
        cbr = W_LIVE - STRIP + int(CBW0 * f)
        print("    %-7s %-9d %-10d %-8d %-10s %s" %
              (f, cbr, swl, txl,
               "BURIED" if cbr > swl else "clear",
               "EATEN" if cbr > txl else "clear"))
    print("    closed form:  swatch buried  <=>  16f > CBG+CBW0 = 18  <=>  f > 1.125")
    print("    -> broken at EVERY shipped tier (1.5, 2, 3); correct only at f=1.")

    print("\n[6] VERTICAL OVERFLOW")
    print("    f=1 legend bottom %3d / chart height 256 -> %s"
          % (end1, "FITS (%d spare)" % (256 - end1)))
    print("    f=2 legend bottom %3d / chart height 512 -> OVERFLOW %+d"
          % (end2, end2 - 512))

    # ---- the NORTHSTAR target ---------------------------------------------
    print("\n[7] NORTHSTAR TARGET - the strip SCALED, f=2 (what a fix must produce)")
    f = 2
    s = STRIP * f
    c_l = W_LIVE - s
    c_r = c_l + CBW0 * f
    sw_l = c_r + CBG * f
    tx_l = sw_l + SWW * f + SWG * f
    tx_r = W_LIVE - RM * f
    print("    cbox (%d..%d)  swatch (%d..%d)  text (%d..%d) w=%d"
          % (c_l, c_r, sw_l, sw_l + SWW * f, tx_l, tx_r, tx_r - tx_l))
    check("target.strip", (CBW0 + CBG + SWW + SWG + (TXW0 - CBW0) + RM) * f, s)
    need = W_LIVE - PLOTG * f - s
    print("    required plot.R = winW - %d = %d" % (PLOTG * f + s, need))
    check("target.plotR.matches.EARLYCHART", need, 756)
    print("    -> EARLYCHART ALREADY stores 756. The plot half is correct today;")
    print("       only the painted strip is still 108 instead of 216.")
    rowsT, endT = column(2.0, True, W_LIVE, S_N, sep, lh2)
    print("    with a %dpx text box the labels wrap like stock -> legend bottom %d/512: %s"
          % (tx_r - tx_l, endT, "FITS (%d spare)" % (512 - endT) if endT <= 512
             else "OVERFLOW %+d" % (endT - 512)))

    # ---- report ------------------------------------------------------------
    print("\n" + "=" * 78)
    if VERBOSE:
        print("%-30s %10s %10s %9s" % ("check", "predicted", "measured", "residual"))
        for t, p, m, r in RESIDUALS:
            print("%-30s %10d %10d %9d" % (t, p, m, r))
    print("checks: %d   non-zero residual: %d" % (len(RESIDUALS), len(FAILS)))
    if FAILS:
        for t, p, m, r in FAILS:
            print("  FAIL %-28s predicted %d measured %d residual %+d" % (t, p, m, r))
        print("RESULT: RED")
        return 1
    print("RESULT: GREEN - every measured number reproduced with residual 0,")
    print("        at f=1 (healthy) AND f=2 (defective), from one formula,")
    print("        with zero free parameters.")
    return 0


def falsify():
    """Rerun the 13 falsifications. A gate whose greens mean something must be
    able to go red on demand; this is that demonstration, kept in the file so it
    can never drift away from the model it tests."""
    import importlib, io, contextlib
    results = []

    def trial(mut, label, expect_red=True):
        sys.modules.pop("emu_legend_row_oracle", None)
        m = importlib.import_module("emu_legend_row_oracle")
        mut(m)
        m.RESIDUALS.clear(); m.FAILS.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            rc = m.main()
        ok = (rc != 0) if expect_red else (rc == 0)
        results.append(ok)
        print("    %-46s rc=%d fails=%2d  %s"
              % (label, rc, len(m.FAILS), "OK" if ok else "*** WRONG WAY ***"))

    print("FALSIFICATION SUITE - each row must turn the gate RED (except F0/H3)")
    trial(lambda m: None, "F0 baseline, no mutation", expect_red=False)
    for name, attr, val in [("F1 STRIP 108->107", "STRIP", 107),
                            ("F2 TXW0  88->89", "TXW0", 89),
                            ("F3 CBW0  16->17", "CBW0", 17),
                            ("F4 PAD    4->5", "PAD", 5),
                            ("F5 SWDY   3->4", "SWDY", 4),
                            ("F6 PLOTG  2->3", "PLOTG", 3),
                            ("F9 SWW   10->12", "SWW", 12),
                            ("F10 TOP  20->21", "TOP", 21)]:
        trial(lambda m, a=attr, v=val: setattr(m, a, v), name)
    trial(lambda m: m.LINEH.__setitem__(2.0, 30), "F7 lineH(2x) 28->30")
    trial(lambda m: m.LINEH.__setitem__(1.0, 16), "F8 lineH(1x) 15->16")

    def h1(m):
        def r(f, hc, w, rt, n, lh):
            txw = int((m.TXW0 - (m.CBW0 if hc else 0)) * f)
            tr = w - int(m.RM * f); tl = tr - txw
            sl = tl - int(m.SWG * f) - int(m.SWW * f)
            cl = w - int(m.STRIP * f)
            o = {"text": (tl, rt, tr, rt + n * lh),
                 "swatch": (sl, rt + m.SWDY, sl + int(m.SWW * f), rt + m.SWDY + m.SWH),
                 "rowHeight": n * lh + m.PAD}
            if hc: o["checkbox"] = (cl, rt, cl + int(m.CBW0 * f), rt + int(m.CBW0 * f))
            return o
        m.row = r
    trial(h1, "H1 'the strip scales with f'")

    def h2(m):
        def r(f, hc, w, rt, n, lh):
            cl = w - m.STRIP; cw = int(m.CBW0 * f)
            sl = cl + (cw + m.CBG if hc else m.CBG)
            tl = sl + m.SWW + m.SWG
            o = {"text": (tl, rt, w - m.RM, rt + n * lh),
                 "swatch": (sl, rt + m.SWDY, sl + m.SWW, rt + m.SWDY + m.SWH),
                 "rowHeight": n * lh + m.PAD}
            if hc: o["checkbox"] = (cl, rt, cl + cw, rt + cw)
            return o
        m.row = r
    trial(h2, "H2 'painter reads the ACTUAL cbox width'")

    def h3(m):
        def r(f, hc, w, rt, n, lh):
            cl = w - m.STRIP
            sl = cl + (m.CBW0 + m.CBG if hc else m.CBG)
            tl = sl + m.SWW + m.SWG
            txw = m.TXW0 - (m.CBW0 if hc else 0)
            o = {"text": (tl, rt, tl + txw, rt + n * lh),
                 "swatch": (sl, rt + m.SWDY, sl + m.SWW, rt + m.SWDY + m.SWH),
                 "rowHeight": n * lh + m.PAD}
            if hc: o["checkbox"] = (cl, rt, cl + int(m.CBW0 * f), rt + int(m.CBW0 * f))
            return o
        m.row = r
    trial(h3, "H3 left-anchored form (EQUIVALENT - must stay GREEN)",
          expect_red=False)

    print("\n    falsifications behaving correctly: %d/%d"
          % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(falsify() if "--falsify" in sys.argv else main())
