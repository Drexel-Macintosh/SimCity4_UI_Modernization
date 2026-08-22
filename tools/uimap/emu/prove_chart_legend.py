# -*- coding: utf-8 -*-
r"""
prove_chart_legend.py - THE ACCEPTANCE ORACLE for the Graphs chart legend (#57).

WHAT THIS IS
------------
A runnable PROVER.  It states, as machine-checked invariants, what a CORRECT
legend layout must satisfy at ANY factor f and for ANY label set, and evaluates
every invariant over

    candidate layout engines  x  2 font hypotheses  x  4 tiers  x  2 kinds
    (+ I3 over EVERY known chart's real label set)

so that a proposed fix can be adjudicated OFFLINE, before it is built.  Four
rect-patches (v2.54.2/.3/.4) shipped because there was no such gate: each one
edited output rects and moved the collision somewhere else.

IT IS CALIBRATED, WHICH IS THE POINT.  Candidate `A-FROZEN` reproduces the
layout the game is drawing TODAY at 2x (every number of it is measured); the
gate FAILS if that candidate does not violate the invariants it is known to
violate.  Candidate `C-v2542` must reproduce the historical split verdict.
Expectations are declared up front in CANDIDATES and checked both ways round.

FOUR STATUSES, AND ONLY ONE OF THEM IS EVIDENCE
  PASS       the check was decidable and held.
  FAIL       the check was decidable and did not hold.
  SKIP       a named primitive is UNKNOWN, so the check could not be made.
  UNDECIDED  the check turns on a difference SMALLER than the text model's own
             residual (TX.TOL = 4.0 px).  Formerly these were silently counted
             as PASS when they happened to land on the right side of the line -
             an asymmetry that converted ignorance into certification.
SKIP and UNDECIDED are counted separately and NEVER count as passes.  A
candidate that needs an UNDECIDED check to reach its verdict is not certified.

=============================================================================
HARDENING PASS - what four independent audits broke, and what was done
=============================================================================
Every item below is a real finding against the PREVIOUS revision of this file.
Each is either RESOLVED (the model was wrong and is corrected) or CAPTURED (it
is now an explicit, named SKIP/UNDECIDED with the one measurement that clears
it).  Nothing was dropped.

R1 RESOLVED - I4's plot-clearance clause read the WRONG EDGE.  The condition
   compared plot.R against text.L while the failure message printed cbox.L, so
   the plot was permitted to be painted straight through the checkbox and
   swatch columns.  Two candidates that do exactly that (H-EARLYCHART, which
   adopts the certified strip but keeps the 756 EARLYCHART already writes, and
   G-CBOXFREE, which reserves only the painted strip) passed the old gate with
   zero failures.  Both are now candidates here and both must FAIL I4.  The
   clause now reads (cbox or swatch)[0] and demands sc(PLOTG,f) clearance.

R2 RESOLVED - I3 could not fail for the certified candidate.  The old E2 box
   was `max(advance(l) for l in LABELS[CHECKBOX])` and I3 then asserted
   `advance(l) <= box` over THE SAME SET at THE SAME point size: true by
   construction.  The box is now derived from a DECLARED, label-set-independent
   bound (NMAX, below), so I3 quantifies over a set the box does not know
   about.  I3 now runs over EVERY chart's real label set, not just Garbage.

R3 RESOLVED - the oracle was not TOTAL.  14 of the 27 shipped graph labels
   raise KeyError inside advance_width (no measured advance for 'U', '#', '(',
   digits, ...), so extending the gate to a second chart crashed it instead of
   producing a verdict.  Widths now go through adv(), which returns None and
   records a SKIP naming the missing glyph.

R4 RESOLVED - I3 was one-sided in the direction that matters.  It exempted
   stock-wrapping labels entirely ("MAY wrap"), so a candidate that turned a
   stock 2-line label into 4 lines passed I3 and only tripped I4 - whose
   column-bottom clause is itself SKIPPED at 1.5x and 3x.  I3b now requires
   lines(L, pt(f), box(f)) <= lines(L, 13, box(1)) for EVERY label.
   DELIBERATELY one-sided the OTHER way: wrapping LESS than stock is allowed.
   It cannot overflow and cannot overlap; it is a strictly better layout.  The
   1.5x attack's "10 lines where stock renders 11" is therefore a PASS here,
   and the real defect it exposed - that the 1.5x box sat 1.07 px from a band
   edge with a 4.0 px residual - is caught by UNDECIDED instead.

R5 RESOLVED - vacuous PASSes.  Measured at 1460 of 3887 (38%).  Fixed three
   ways.  (a) The sc() definition block and the strip-closure identities
   referenced no candidate value at all - x==x repeated 28 times.  They are
   real facts and they are still gate conditions, but they are now HARNESS
   SELF-TESTS in their own section with their own counters, not invariant
   assertions.  (b) I2's and I8's clauses over the plain kind iterated an EMPTY
   list of checkbox windows and scored PASS; they now SKIP, exactly as I1
   already did for the identical situation.  (c) I6's "the candidate draws at
   the tier font" clause tested a harness flag, not the candidate; moved to the
   self-tests.

R6 CAPTURED - I1 is strictly IMPLIED by I8.  Measured over the full ledger:
   zero cells where I1 failed and I8 did not.  I1's checks are therefore
   corroboration, not independent adjudication ("two blind instruments agreeing
   = one").  I1 is retained (it is the readable statement of the defect, and it
   still adjudicates candidates that fail I8) but is TAGGED DERIVED, excluded
   from the independent-adjudication tally, and the implication is itself
   checked every run - if I1 ever fails where I8 passes, the tag is wrong and
   the gate says so.

R7 RESOLVED - I8 over-constrained the swatch and would have REJECTED a correct
   fix.  `swatch.T - rowTop == sc(3,f)` is a hard equality fitted to two
   measured tiers (f=1 and f=2) where it happens to coincide with the rival
   rule "the swatch keeps its proportion of the LINE", round(3*lineH/15).  The
   two diverge at 1.5x and 3x.  I8 now accepts EITHER, and records U6.

R8 RESOLVED - a missing invariant.  Nothing checked checkbox-child-window
   against checkbox-child-window.  I2 only tested swatch-vs-cbox and
   text-vs-cbox, which are X-disjoint by construction and so could never fire.
   NEW I9 ROW PITCH does it - and reports that the slack is EXACTLY ZERO at
   f=2 (a 32 px checkbox in a 32 px one-line row pitch).

R9 RESOLVED - no invariant constrained the COORDINATE FRAME the numbers live
   in.  Perturbing the assumed 1x chart origin by +-4 px left I5 at 168/168
   PASS while every published acceptance target moved 8 px.  The origin
   derivation it rested on was also circular (four margins fitted to four
   edges, residual 0 by substitution - "FIT FAILED" was unreachable).  NEW I10
   FRAME replaces it with a falsifiable anchor measured off the parent panel's
   painted client fill, an object the chart layout never touches, and it turns
   up a NEW divergence at 1.5x (U8).

R10 RESOLVED - U4, the 24-vs-26 pt question, is settled from a capture that
   already existed.  See U4 below.  U2 likewise.

R11 CAPTURED - candidates had no vertical degrees of freedom: every one shared
   a stack() hard-wired to module-level TOP/PAD, so a fix that changed the row
   pitch was not even expressible.  TOP and PAD are now per-candidate fields,
   which is also what makes I8's row clause and I9 falsifiable rather than
   audits of the shared helper.

R12 RESOLVED - the mutation suite tested PRESENCE, not ADEQUACY: every mutation
   deleted a whole invariant or corrupted a measurement, and none submitted an
   adversarial candidate.  That is precisely the gap R1 walked through.  A
   PERTURBATION FAMILY is added: each field of the CERTIFIED candidate is moved
   by a few px and the gate must go red for every one.

=============================================================================
THE INVARIANTS
=============================================================================
  Let f be the tier, W = winW(f), c = 1 if the row carries a checkbox child
  window, and sc(v,f) = floor(v*f + 0.5) (round-half-up, PACKAGES.md).

  I1* ORDER + NON-OVERLAP  (DERIVED - implied by I8; see R6)
        cbox.R <= swatch.L, swatch.R <= text.L, and the two gaps are at least
        the MEASURED stock gaps sc(2,f) and sc(4,f).
  I2  VISIBILITY
        for every row k and every checkbox child window j: swatch[k] and
        text[k] must not intersect cbox[j]; every painted rect lies inside the
        chart client (0,0,W,H).
  I3  FIT (three clauses)
        a  every label stock keeps on ONE line fits the box at pt(f)
        b  lines(L,pt(f),box(f)) <= lines(L,13,box(1))  for EVERY label
        c  the candidate's declared glyph bound NMAX covers every known label
  I4  CONTAINMENT
        text.R <= W - sc(4,f);  plot.R + sc(2,f) <= strip.L  where strip.L is
        the CHECKBOX column when one exists (R1);  column bottom <= H.
  I5  f=1 REDUCTION - the model reproduces the MEASURED stock columns and row
        tops exactly, both kinds.  NECESSARY, NOT SUFFICIENT: all four failed
        patches pass it.  That is why every expectation is measured at f>=1.5.
  I6  MONOTONICITY + NORTHSTAR - every column edge non-decreasing in f, no
        width <= 0, and width(col,f) >= sc(width(col,1),f).  The last clause is
        what forbids "make it 1x again"; candidate F is that control.
  I7  ROUNDING CONSISTENCY - every column width is exactly what the candidate
        DECLARES (scaled / frozen / free), and a font-box candidate's plain-kind
        box equals the font-derived plain box.  (The sc() law itself and the
        strip-closure identities moved to the self-tests - R5a.)
  I8  COUPLED PAIR (law 43) - the three columns move together: both gaps and
        the right margin are exactly sc(2,f)/sc(4,f)/sc(4,f); cbox.T == text.T
        == rowTop; the swatch inset and height follow either the sc rule or the
        line-proportional rule (R7).
  I9  ROW PITCH (new, R8) - consecutive checkbox child windows must not
        overlap: cbox[k].B <= cbox[k+1].T.
  I10 FRAME (new, R9) - the chart-local coordinate frame is anchored to the
        parent panel's painted client, independently of any legend constant.

=============================================================================
THE FONT-SIZE HYPOTHESIS (U4) - RESOLVED THIS PASS, TO RAW
=============================================================================
tools/fonts/make_fontstyle.py ships Legend at f*13 with SIZE_SQUEEZE 0.92, i.e.
13/18/24/36 (SQUEEZED).  Without the squeeze it would be 13/20/26/39 (RAW).
Which one the chart actually resolves was UNRESOLVED and verdict-changing.

THREE INDEPENDENT MEASUREMENTS, all off _tests/captures/graphs-ours-2x.png,
all taken this pass, all say RAW = 26 pt:
  1  THE WRAP.  The plain legend's second row is painted as TWO ink runs plus a
     third run 6 px wide at the LEFT of the text box (chart-local x 885..890,
     text.L = 884): "Expenses" renders as "Expense" / "s".  It wraps inside the
     88 px box.  The model gives 85.5 px at 24 pt (fits, no wrap) and 93.1 px
     at 26 pt (wraps).  Only 26 pt produces a wrap.
  2  THE INK.  Row 0 "Income" ink measures 68 px (chart-local x 887..954).
     Model: 70.1 px at 26 pt, 64.4 px at 24 pt.
  3  THE PITCH.  The nine measured 2x Garbage row pitches are reproduced at
     26 pt and not at 24 pt ('Landfill' differs by one line) - the original U4
     observation, now the third leg rather than the only one.
These are three DIFFERENT failure modes (a wrap decision, an ink width, a row
pitch), so they corroborate rather than repeat each other.
HONEST MARGIN: measurement 1's 24 pt figure is 85.5 against an 88 px box, i.e.
2.5 px of slack, which is INSIDE TX.TOL = 4.0.  Taken alone it would be
UNDECIDED.  It is measurements 2 and 3 that carry it.
CONSEQUENCE: E-STRIPxf is dead - it passes only under SQUEEZED.  BOTH
hypotheses are still run, because certification under both is strictly stronger
and costs nothing; SQUEEZED is now labelled REFUTED-BUT-RETAINED.

=============================================================================
UNKNOWNS - marked, never invented
=============================================================================
  U1  lineH(pt).  MEASURED at 15 px @ 13 pt and 28 px @ 24-26 pt only.  Two
      points do not determine the rule, so every VERTICAL check at f=1.5 and
      f=3 is SKIPPED.  ONE MEASUREMENT PINS IT: capture a 1-line legend row at
      the 1.5x tier and read the swatch-top pitch; pitch - 4 = lineH(18 or 20).
  U2  RESOLVED this pass.  The plain kind's row 0 at f=2 is ONE line: measured
      ink runs (chart-local y) 24..41, 56..79, 91..102 decode as row 0 = 1 line
      at top 20 and row 1 = 2 lines at top 52.  The UiSpike.cpp comment's
      (884,20,972,76) is not row 0.  Pixels win.
  U3  whether the 16 px reserved inside the text width IS the design checkbox
      width or an unrelated constant that equals it.  Recorded as an ALIAS: the
      left-anchored and right-anchored parameterisations are observationally
      identical on all available data.
  U4  RESOLVED this pass, to RAW.  See above.
  U5  whether TOP (20) and PAD (4) should scale in a fix.  Both are MEASURED
      unscaled at f=1 AND f=2, so the candidates keep them unscaled; that is a
      modelling CHOICE inherited from the measurement, and it is now a
      per-candidate field so a future tier can falsify it.
  U6  the swatch vertical rule.  sc(3,f) and round(3*lineH/15) agree at exactly
      the two tiers where lineH is measured and diverge at 1.5x and 3x.  I8
      accepts either.  SAME MEASUREMENT AS U1 clears it.
  U7  NMAX for the tighter corpus box.  E2 uses the PROVABLE bound (below) and
      carries no unknown; the informative E3 variant uses a corpus-derived 20
      and would be falsified by any real label with more glyphs.
  U8  NEW this pass.  winW(1.5) is AMBIGUOUS: scaling the chart width gives
      sc(488,1.5) = 732, while scaling the panel and its inset gives
      sc(498,1.5) - 2*sc(5,1.5) = 747 - 16 = 731.  The two agree at f=1, 2 and
      3 and differ by 1 px at 1.5x - task #75's container-vs-child parity
      divergence, reaching the chart frame.  I10 therefore ASSERTS at f=1/2/3
      and SKIPS at f=1.5.  ONE MEASUREMENT PINS IT: log chart WIN[0xA8] at the
      1.5x tier and read its width.

=============================================================================
THE BOX RULE - why the certified box is not fitted to Garbage
=============================================================================
From emu_text_extent's own model, a label with 1x pen width a and n non-space
glyphs has, at point size S,
        advance(S) = (S/13)*a + n*DELTA*(S/13 - 1),      DELTA = 0.70
(verified exact against TX.advance_width to 1e-3 on three labels x three
sizes).  A stock box of B admits every label with a <= B.  The widest such
label at S therefore needs
        box(S) = ceil( B*(S/13) + NMAX*DELTA*(S/13 - 1) )
where NMAX is the largest glyph count that can fit in B at 13 pt.  That is a
PROVABLE bound, not a fit: the narrowest measured glyph ('I' and 'i', 5.0 px at
26 pt) costs 2.15 px at 13 pt, so NMAX = floor(72 / 2.15) = 33.
  It costs plot width - 168 px at 2x against 158 for a corpus-fitted 20 - and
  that cost is the price of not shipping a constant measured on the one chart
  in front of us, which is the shape all four failed patches had.  E3-CORPUS is
  carried as an INFORMATIVE tighter variant for anyone who wants the 10 px back
  and is willing to measure the corpus bound properly (U7).
  CAVEAT: NMAX is derived from the narrowest MEASURED glyph.  The metric table
  has no digits, '#', '(' or accented glyphs; a narrower one would raise NMAX.

USAGE
  python prove_chart_legend.py            # the gate (what CI runs)
  python prove_chart_legend.py --verbose  # + every individual check
  python prove_chart_legend.py --details  # + the geometry table per candidate
  python prove_chart_legend.py --mutate   # the audit: prove it CAN go red
Exit 0 only if every gate condition holds.  Offline only: imports one sibling
module, reads no game file, writes nothing.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu_text_extent as TX          # noqa: E402

VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv
DETAILS = "--details" in sys.argv

# ===========================================================================
#  MEASURED CONSTANTS.  Provenance on every one; all are UNSCALED in the
#  shipped game, which is the finding both sibling oracles reproduce at
#  residual 0 for f=1 AND f=2.
# ===========================================================================
RM    = 4     # right margin, text.R = W - RM
TXW0  = 88    # text box width, plain kind
CBW0  = 16    # DESIGN checkbox width (what the PAINTER assumes)   [U3 alias]
SWW   = 10    # swatch width
SWH   = 6     # swatch height
SWG   = 4     # swatch -> text gap
CBG   = 2     # checkbox -> swatch gap
STRIP = 108   # the whole right-anchored legend strip
PLOTG = 2     # plot -> strip gap
TOP   = 20    # legend top inset (row 0 top)
PAD   = 4     # inter-row padding
SWDY  = 3     # swatch top offset inside the row
LH1   = 15    # lineH at 13 pt - the reference for the proportional swatch rule

# THE FRAME (I10).  Measured off the parent panel's painted client fill
# (RGB 218,224,229 / 239,243,247) bounded by the dialog border stack
# (156,178,194) - an object the chart layout never touches, so it is an
# INDEPENDENT anchor rather than a restatement of the plot margins.
#   graphs-stock-garbage.png  row y=500 : border 504..506 | client 508..1005
#                                         (498 px) | border 1007..1009
#   graphs-ours-2x.png        row y=1000: border 1000..1005 | client 1008..2003
#                                         (996 px) | border 2006..2011
#   996 == 2 * 498 EXACTLY.  The captures are 1032x810 and 2400x1600 (ratio
#   2.33), so this cannot be screen stretching: the panel is design-px * tier.
PANEL_CLIENT_1 = 498    # parent panel client width at f=1, MEASURED
CHART_INSET_1  = 5      # chart inset inside that client, MEASURED (2x: 10)
LIVE_2X_WINW   = 976    # SC4UIScale.log v2.54.4, WIN[0xA8] 1004-28
LIVE_2X_WINH   = 512    # ditto, 576-64

W1, H1 = 488, 256          # the chart window at f=1 (chart-local)

TIERS = (1.0, 1.5, 2.0, 3.0)

CHECKBOX, PLAIN = "checkbox", "plain"

# lineH is a FONT metric.  MEASURED at two sizes only (U1).
LINEH_BY_PT = {13: 15, 24: 28, 26: 28}

PT_SQUEEZED = {1.0: 13, 1.5: 18, 2.0: 24, 3.0: 36}   # make_fontstyle.py ships
PT_RAW      = {1.0: 13, 1.5: 20, 2.0: 26, 3.0: 39}   # f*13, no SIZE_SQUEEZE
# RAW is the MEASURED one (U4).  SQUEEZED is retained because certifying under
# a refuted hypothesis too is strictly stronger and costs nothing.
PT_HYPS = (("SQUEEZED", PT_SQUEEZED), ("RAW", PT_RAW))
PT_MEASURED = "RAW"

# ===========================================================================
#  TOTALITY SHIM (R3).  emu_text_extent raises KeyError on any glyph it has no
#  measured advance for.  14 of the 27 shipped graph labels contain one.  A
#  crash is not a verdict, so widths go through adv(): it returns None and the
#  caller records a SKIP naming the glyph.
# ===========================================================================
def adv(text, pt):
    try:
        return TX.advance_width(text, pt), None
    except KeyError as e:
        s = str(e)
        i, j = s.find("'"), s.rfind("'")
        return None, (s[i:j + 1] if 0 <= i < j else s)


def wrap_lines(text, pt, box_w):
    try:
        return len(TX.wrap(text, pt, box_w)), None
    except KeyError as e:
        s = str(e)
        i, j = s.find("'"), s.rfind("'")
        return None, (s[i:j + 1] if 0 <= i < j else s)


def nglyphs(s):
    return sum(1 for c in s if c != ' ')


# ===========================================================================
#  LABEL SETS
#
#  The two MEASURED sets drive every invariant.  The rest are the REAL shipped
#  strings, transcribed from <install>\SimCityLocale.DAT (DBPF 1.0, LTEXT type
#  0x2026960B, group 0x6A231EAA, instances 0x0A5D2E96..0x0A5D2EB0 - 27
#  consecutive entries = the vanilla graph label block).  Positive control:
#  "Income"/"Expenses" and "Capacity"/"Total Garbage", the two MEASURED sets,
#  are inside that block.  They drive I3 only: their group separators and their
#  stock wrap behaviour were never captured, so no vertical check can use them.
# ===========================================================================
LABELS = {
    CHECKBOX: TX.LABELS_GARBAGE,          # 9 rows, 3 groups   (MEASURED)
    PLAIN:    TX.LABELS_PLAIN,            # 2 rows, 1 group    (MEASURED)
}
# group separators: a blank line follows these row indices.  DATA, not font -
# visible in graphs-stock-garbage.png as empty bands at y 393..410 / 446..463.
SEPS = {
    CHECKBOX: [0, 1, 0, 1, 0, 0, 0, 0],
    PLAIN:    [0],
}
# which labels STOCK itself wraps.  Measured in graphs-stock-garbage.png.
STOCK_WRAPS = {"Waste to Energy", "Garbage Pollution"}

# (name, kind, labels, binding) - binding CONFIRMED = the LTEXT instance sits
# in the consecutive vanilla graph block; INFERRED = same LTEXT group, chart
# membership not decompiled.
EXTRA_LABEL_SETS = [
    ("Water/Power",        CHECKBOX, ["Capacity", "Current Usage"], "CONFIRMED"),
    ("Jobs & Pop.",        CHECKBOX, ["Resident Population", "Commercial Jobs",
                                      "Industrial Jobs"], "CONFIRMED"),
    ("Pollution",          CHECKBOX, ["Air Pollution", "Water Pollution"],
                                     "CONFIRMED"),
    ("Crime",              CHECKBOX, ["# of Crimes", "# of Arrests"],
                                     "CONFIRMED"),
    ("Res. Avg. Income",   PLAIN,    ["Average Income (000s)"], "CONFIRMED"),
    ("Funds",              PLAIN,    ["Funds (000s)"], "CONFIRMED"),
    ("Mayor Rating",       PLAIN,    ["Mayor Rating"], "CONFIRMED"),
    ("Life Expectancy",    PLAIN,    ["Life Expectancy"], "CONFIRMED"),
    ("Education",          CHECKBOX, ["Education"], "CONFIRMED"),
    ("Commute Time",       PLAIN,    ["Commute Time"], "CONFIRMED"),
    ("by Age",             CHECKBOX, ["1-10", "11-20", "21-30", "31-40",
                                      "41-50", "51-60", "61-70", "71-80",
                                      "81-90"], "CONFIRMED"),
    ("Commute (inferred)", CHECKBOX, ["Morning Commute", "Evening Commute",
                                      "Commute Length"], "INFERRED"),
    ("Water Treated (inf)", CHECKBOX, ["Water Treated"], "INFERRED"),
]

# ===========================================================================
#  MEASURED GROUND TRUTH used by I5 (chart-local; screen origin subtracted).
#
#  ORIGIN PROVENANCE (R9).  The previous revision cited "stock capture origin
#  X0=513, Y0=338, both axes double-anchored, residual 0".  That claim was
#  CIRCULAR: the origin was fitted from the four plot margins (45/20/110/20),
#  which are the very constants the model asserts are unscaled, so the residual
#  was 0 by substitution and "FIT FAILED" was unreachable.  The origin used
#  here is instead anchored on the parent panel's painted client (see the
#  FRAME block above): client 508..1005 at 1x, inset 5 -> X0 = 513, W1 = 488;
#  the 2x capture's client is 996 = 2*498 and the logged chart is 976 = 996-20.
#  That is a falsifiable prediction (996 == 2*498) which could have failed and
#  did not.  I10 checks it every run.
# ===========================================================================
M_STOCK = {
    CHECKBOX: {
        "cbox":   (380, 396),      # screen ink 893..908
        "swatch": (398, 408),      # screen ink 911..920
        "text_l": 412,             # screen ink 925, lsb 0 for 'T'/'C'
        "text_lsb": 0,
        "tops":   [20, 39, 73, 92, 126, 145, 164, 183, 217],
        "swtops": [23, 42, 76, 95, 129, 148, 167, 186, 220],
        "plot_r": 378,
    },
    PLAIN: {
        "cbox":   None,
        "swatch": (382, 392),      # screen ink 895..904
        "text_l": 397,             # screen ink 910; 'I'/'E' carry a 1px lsb
        "text_lsb": 1,
        "tops":   [20, 39],
        "swtops": [23, 42],
        "plot_r": 378,
    },
}
# HONESTY NOTE carried from the audit: M_STOCK[PLAIN]["tops"] is derived as
# swtops - SWDY, so for the PLAIN kind I5's "row tops" and "swatch tops" are
# one measurement counted twice.  The CHECKBOX kind's nine bands are measured
# independently.  Recorded rather than silently double-counted.

# ===========================================================================
#  MEASURED GROUND TRUTH used by the CALIBRATION cross-check at f=2
#  (SC4UIScale.log v2.54.4; chart window 976x512, chart-local already)
# ===========================================================================
M_LIVE_2X = {
    CHECKBOX: {"cbox": (868, 900), "swatch_l": 886, "swatch_t": 23,
               "text": (900, 972), "cbox_h": 32,
               "tops": [20, 80, 196, 256, 344, 404, 464, 524, 612],
               "plot_r": 866},
    PLAIN:    {"cbox": None, "swatch_l": 870, "swatch_t": 23,
               "text": (884, 972), "cbox_h": None,
               "tops": None, "plot_r": 866},
}
M_LIVE_2X_PLOT_R_NOLEGEND = 974


# ===========================================================================
#  THE SCALING LAW
# ===========================================================================
# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
# Integer-exact for integer f; for f=1.5 a .5 result rounds UP.
from scale_rules import scale_round as sc       # noqa: E402


def win_w(f):
    return sc(W1, f)


def win_h(f):
    return sc(H1, f)


def frame_w(f):
    """winW derived from the INDEPENDENT panel anchor instead of from W1."""
    return sc(PANEL_CLIENT_1, f) - 2 * sc(CHART_INSET_1, f)


# ---------------------------------------------------------------------------
#  THE PROVABLE GLYPH BOUND (see the box-rule block in the docstring)
# ---------------------------------------------------------------------------
def _min_glyph_adv13():
    best = None
    for ch in TX.ADV26:
        if ch == ' ':
            continue
        w = TX.advance_width(ch, 13)
        if best is None or w < best:
            best = w
    return best


MIN_GLYPH_13 = _min_glyph_adv13()                  # 2.15 px ('I' / 'i')
NMAX_PROVABLE = int(math.floor((TXW0 - CBW0) / MIN_GLYPH_13))    # 33
NMAX_CORPUS = 20      # DECLARED, from the 842-string evaluable corpus (U7)


def font_box(base_box_1x, pt, nmax):
    """The box width that admits, at `pt`, every label a `base_box_1x` box
    admits at 13 pt - for ANY label set with at most `nmax` glyphs."""
    r = pt / 13.0
    return int(math.ceil(base_box_1x * r + nmax * TX.DELTA * (r - 1.0)))


# ===========================================================================
#  CANDIDATE LAYOUT ENGINES
#
#  Each returns the X geometry of the strip, the vertical fields, and a
#  declaration of how each width was derived (used by I7).  A candidate is a
#  GEOMETRY, not a patch: nothing here claims to know the mechanism.
#
#  cols = dict(cbox=(l,r) or None, swatch=(l,r), text=(l,r), swdy, swh,
#              plot_r, plot_r_noleg, top, pad, nmax, box_rule)
#  decl = {name: ("scaled"|"frozen"|"free", base)}
# ===========================================================================
def _mk(cb, sw, tx, swdy, swh, plot_r, plot_r_noleg, decl,
        top=TOP, pad=PAD, nmax=None, box_rule=None):
    return {"cbox": cb, "swatch": sw, "text": tx, "swdy": swdy, "swh": swh,
            "plot_r": plot_r, "plot_r_noleg": plot_r_noleg, "decl": decl,
            "top": top, "pad": pad, "nmax": nmax, "box_rule": box_rule}


def eng_frozen(f, kind):
    """A-FROZEN - what the game is DRAWING TODAY, at every tier.

    Every painted constant frozen at its 1x value; the ONE thing that scales is
    the checkbox CHILD WINDOW, because our own sweep scales it.  At f=1 this is
    stock, byte for byte.  At f=2 it reproduces every number in the v2.54.4 log
    (cbox 868..900, swatch 886, text 900..972, plot_r 866/974).  This is the
    calibration candidate: the gate FAILS if it does not go red."""
    W = win_w(f)
    c = 1 if kind == CHECKBOX else 0
    txw = TXW0 - CBW0 * c
    tx = (W - RM - txw, W - RM)
    sw = (tx[0] - SWG - SWW, tx[0] - SWG)
    cb = (W - STRIP, W - STRIP + sc(CBW0, f)) if c else None
    return _mk(cb, sw, tx, SWDY, SWH,
               W - PLOTG - STRIP, W - PLOTG,
               {"cbox": ("scaled", CBW0), "swatch": ("frozen", SWW),
                "text": ("frozen", txw), "strip": ("frozen", STRIP)})


def eng_v2544(f, kind):
    """B-v2544 - the shipped v2.54.4 attempt as DESCRIBED in the brief: scale
    the swatch (size x f, gap x f) and split the formula by legend kind, while
    the text box and the strip left edge stay frozen.  Moves the Garbage swatch
    886 -> 872, i.e. deeper under the checkbox window."""
    W = win_w(f)
    c = 1 if kind == CHECKBOX else 0
    txw = TXW0 - CBW0 * c
    tx = (W - RM - txw, W - RM)
    sw = (tx[0] - sc(SWG, f) - sc(SWW, f), tx[0] - sc(SWG, f))
    cb = (W - STRIP, W - STRIP + sc(CBW0, f)) if c else None
    return _mk(cb, sw, tx, sc(SWDY, f), sc(SWH, f),
               W - PLOTG - STRIP, W - PLOTG,
               {"cbox": ("scaled", CBW0), "swatch": ("scaled", SWW),
                "text": ("frozen", txw), "strip": ("frozen", STRIP)})


def eng_v2542(f, kind):
    """C-v2542 - widen the text box leftward and shift the swatch with it, and
    do NOT touch the checkbox child window.  History says this FIXED
    Income/Expenses and BROKE Garbage ('checkbox landed mid-label')."""
    W = win_w(f)
    c = 1 if kind == CHECKBOX else 0
    txw = sc(TXW0 - CBW0 * c, f)
    tx = (W - sc(RM, f) - txw, W - sc(RM, f))
    sw = (tx[0] - sc(SWG, f) - sc(SWW, f), tx[0] - sc(SWG, f))
    cb = (W - STRIP, W - STRIP + sc(CBW0, f)) if c else None
    return _mk(cb, sw, tx, sc(SWDY, f), sc(SWH, f),
               W - PLOTG - STRIP, W - PLOTG,
               {"cbox": ("scaled", CBW0), "swatch": ("scaled", SWW),
                "text": ("scaled", TXW0 - CBW0 * c), "strip": ("free", 0)})


def eng_v2543(f, kind):
    """D-v2543 - C, plus move the checkbox windows so they sit left of the
    swatch, but reserve the DESIGN width (16) for them while DRAWING them at
    16f.  History: 'buried the swatch under the checkbox art'.  MODELLED
    failure mode - the reserve-vs-draw mismatch is the only arithmetic that
    produces the reported symptom."""
    W = win_w(f)
    c = 1 if kind == CHECKBOX else 0
    txw = sc(TXW0 - CBW0 * c, f)
    tx = (W - sc(RM, f) - txw, W - sc(RM, f))
    sw = (tx[0] - sc(SWG, f) - sc(SWW, f), tx[0] - sc(SWG, f))
    cb = None
    if c:
        left = sw[0] - sc(CBG, f) - CBW0          # reserve the DESIGN width
        cb = (left, left + sc(CBW0, f))           # draw at the SCALED width
    return _mk(cb, sw, tx, sc(SWDY, f), sc(SWH, f),
               W - PLOTG - STRIP, W - PLOTG,
               {"cbox": ("scaled", CBW0), "swatch": ("scaled", SWW),
                "text": ("scaled", TXW0 - CBW0 * c), "strip": ("free", 0)})


def _strip_walk(f, kind, box_w, strip_w):
    """Shared left-to-right walk: cbox | gap | swatch | gap | text | margin."""
    W = win_w(f)
    c = 1 if kind == CHECKBOX else 0
    cur = W - strip_w
    cb = None
    if c:
        cb = (cur, cur + sc(CBW0, f))
        cur = cb[1]
    cur += sc(CBG, f)
    sw = (cur, cur + sc(SWW, f))
    cur = sw[1] + sc(SWG, f)
    tx = (cur, cur + box_w)
    return cb, sw, tx


def eng_scaled_strip(f, kind):
    """E-STRIPxf - the fix the two sibling oracles arrive at: scale the whole
    strip, strip = sc(108,f), so the box becomes sc(72,f) / sc(88,f).  plot_r =
    W - sc(2,f) - sc(108,f), which is algebraically W - sc(110,f) - the number
    EARLYCHART already stores (756 at f=2).  DEAD as of U4's resolution: it
    passes only under the REFUTED squeezed font."""
    W = win_w(f)
    c = 1 if kind == CHECKBOX else 0
    strip = sc(STRIP, f)
    box = sc(TXW0 - CBW0 * c, f)
    cb, sw, tx = _strip_walk(f, kind, box, strip)
    return _mk(cb, sw, tx, sc(SWDY, f), sc(SWH, f),
               W - sc(PLOTG, f) - strip, W - sc(PLOTG, f),
               {"cbox": ("scaled", CBW0), "swatch": ("scaled", SWW),
                "text": ("scaled", TXW0 - CBW0 * c),
                "strip": ("scaled", STRIP)})


def _fontbox_engine(f, kind, nmax, plot_rule="strip"):
    """The shared body of the font-box family.

    box  = font_box(72, pt_raw(f), nmax)          (label-set INDEPENDENT, R2)
    strip= scaled furniture + box + scaled margin
    The plain kind inherits the SAME strip, exactly as stock does (stock's two
    kinds both close on 108) - I7 checks that the inherited plain box equals
    the font-derived plain box, which is a real, falsifiable coincidence.
    """
    W = win_w(f)
    c = 1 if kind == CHECKBOX else 0
    pt = PT_RAW[f]                       # size against the WIDER hypothesis
    box_cb = max(sc(TXW0 - CBW0, f), font_box(TXW0 - CBW0, pt, nmax))
    strip = sc(CBW0, f) + sc(CBG, f) + sc(SWW, f) + sc(SWG, f) + box_cb + sc(RM, f)
    box = box_cb if c else strip - sc(CBG, f) - sc(SWW, f) - sc(SWG, f) - sc(RM, f)
    cb, sw, tx = _strip_walk(f, kind, box, strip)
    if plot_rule == "strip":
        plot_r = W - sc(PLOTG, f) - strip
    elif plot_rule == "earlychart":      # what EARLYCHART already writes
        plot_r = W - sc(PLOTG + STRIP, f)
    elif plot_rule == "painted":         # reserve only the PAINTED strip
        plot_r = (cb[1] if c else sw[0]) - sc(PLOTG, f)
    return _mk(cb, sw, tx, sc(SWDY, f), sc(SWH, f),
               plot_r, W - sc(PLOTG, f),
               {"cbox": ("scaled", CBW0), "swatch": ("scaled", SWW),
                "text": ("free", box), "strip": ("free", strip)},
               nmax=nmax, box_rule=(TXW0 - CBW0, nmax))


def eng_font_box(f, kind):
    """E2-FONTBOX - THE CERTIFIED CANDIDATE.  The box is sized by the FONT
    against a PROVABLE glyph bound, so it is independent of which chart's
    labels happen to be in front of us."""
    return _fontbox_engine(f, kind, NMAX_PROVABLE)


def eng_font_box_corpus(f, kind):
    """E3-CORPUS - informative tighter variant: same rule, NMAX declared from
    the evaluable corpus (20) instead of proven (33).  10 px narrower at 2x.
    Carries U7: any real label with more than 20 glyphs that fits the stock box
    falsifies it, and I3c is the check that would say so."""
    return _fontbox_engine(f, kind, NMAX_CORPUS)


def eng_earlychart(f, kind):
    """H-EARLYCHART - THE COUNTEREXAMPLE THAT PASSED THE OLD GATE (R1).
    Adopt the certified strip exactly, but leave plot.R at what EARLYCHART
    already writes today, W - sc(110,f).  At f=2 that paints the plot's right
    border 2 px INSIDE the checkbox column, down all nine checkbox windows.
    This is the MOST LIKELY thing to be built, because the mechanism workflow
    reports 756 is already stored.  It MUST fail I4."""
    return _fontbox_engine(f, kind, NMAX_PROVABLE, plot_rule="earlychart")


def eng_cboxfree(f, kind):
    """G-CBOXFREE - the other counterexample that passed the old gate: reserve
    only the PAINTED strip on the reasoning that the checkbox is a child WINDOW
    and needs no reserve.  At f=2 the plot frame is drawn through the whole
    checkbox column.  It MUST fail I4.

    BONUS FINDING, and it refutes the audit that submitted this candidate: the
    audit claimed 'f=1 returns stock, as UiSpike.cpp and all four shipped
    patches do'.  It does not.  STOCK's own reserve is the FULL 108 including
    the checkbox (plot.R = 378, measured), so dropping the checkbox from the
    reserve puts plot.R at 394 even at f=1.  G-CBOXFREE therefore fails I5 as
    well, and that failure is DECLARED below rather than discovered later."""
    return _fontbox_engine(f, kind, NMAX_PROVABLE, plot_rule="painted")


def eng_taptarget(f, kind):
    """J-TAPTARGET - the I9 falsifier, and a realistic one.

    E2's strip, except the checkbox CHILD WINDOW is enlarged to sc(20,f) above
    f=1 to give the touch build a bigger tap target - something this project
    does elsewhere.  The strip widens with it so every gap stays exact, so it
    passes I1/I5/I6/I7/I8 and it does NOT overlap the swatch (the columns are
    X-disjoint by construction, which is precisely why I2 can never see this).
    What it does is make the SQUARE checkbox window TALLER than a one-line row
    pitch: 40 px against lineH(26) + PAD = 32.  Consecutive checkboxes then
    overlap each other.  Only I9 catches it."""
    W = win_w(f)
    c = 1 if kind == CHECKBOX else 0
    cbw = CBW0 if f == 1.0 else sc(20, f)
    box_cb = max(sc(TXW0 - CBW0, f),
                 font_box(TXW0 - CBW0, PT_RAW[f], NMAX_PROVABLE))
    strip = cbw + sc(CBG, f) + sc(SWW, f) + sc(SWG, f) + box_cb + sc(RM, f)
    box = box_cb if c else strip - sc(CBG, f) - sc(SWW, f) - sc(SWG, f) - sc(RM, f)
    cur = W - strip
    cb = None
    if c:
        cb = (cur, cur + cbw)
        cur = cb[1]
    cur += sc(CBG, f)
    sw = (cur, cur + sc(SWW, f))
    cur = sw[1] + sc(SWG, f)
    tx = (cur, cur + box)
    return _mk(cb, sw, tx, sc(SWDY, f), sc(SWH, f),
               W - sc(PLOTG, f) - strip, W - sc(PLOTG, f),
               {"cbox": ("free", cbw), "swatch": ("scaled", SWW),
                "text": ("free", box), "strip": ("free", strip)},
               nmax=NMAX_PROVABLE, box_rule=(TXW0 - CBW0, NMAX_PROVABLE))


def eng_stocksize(f, kind):
    """F-STOCKSIZE - the NORTHSTAR VIOLATION control: keep the stock legend at
    its stock pixel size (checkbox window NOT scaled either) on a big window,
    and keep the 1x font.  Everything lines up, nothing overlaps, nothing
    overflows - and it is WRONG, because the northstar is 'UI ELEMENTS
    ENLARGED'."""
    W = win_w(f)
    c = 1 if kind == CHECKBOX else 0
    txw = TXW0 - CBW0 * c
    tx = (W - RM - txw, W - RM)
    sw = (tx[0] - SWG - SWW, tx[0] - SWG)
    cb = (W - STRIP, W - STRIP + CBW0) if c else None
    return _mk(cb, sw, tx, SWDY, SWH,
               W - PLOTG - STRIP, W - PLOTG,
               {"cbox": ("frozen", CBW0), "swatch": ("frozen", SWW),
                "text": ("frozen", txw), "strip": ("frozen", STRIP)})


# ===========================================================================
#  ROW STACKING.  Needs lineH, which is UNKNOWN outside 13/24/26 pt, so it
#  returns rows=None there and every caller SKIPS (U1).  TOP and PAD come from
#  the CANDIDATE (R11), not from module scope, so a candidate that changes the
#  row pitch is expressible and therefore adjudicable.
# ===========================================================================
def stack(f, kind, cols, pt):
    labels = LABELS[kind]
    box_w = cols["text"][1] - cols["text"][0]
    n, miss = [], None
    for l in labels:
        k, m = wrap_lines(l, pt, box_w)
        if k is None:
            miss = miss or m
            k = 1
        n.append(k)
    lh = LINEH_BY_PT.get(pt)
    if lh is None:
        return {"n": n, "lh": None, "rows": None, "bottom": None, "miss": miss}
    seps = SEPS[kind]
    rows, y = [], cols["top"]
    cbw = (cols["cbox"][1] - cols["cbox"][0]) if cols["cbox"] else 0
    for k, ni in enumerate(n):
        r = {"top": y,
             "text": (cols["text"][0], y, cols["text"][1], y + ni * lh),
             "swatch": (cols["swatch"][0], y + cols["swdy"],
                        cols["swatch"][1], y + cols["swdy"] + cols["swh"])}
        if cols["cbox"]:
            r["cbox"] = (cols["cbox"][0], y, cols["cbox"][1], y + cbw)
        rows.append(r)
        y += ni * lh + cols["pad"] + (seps[k] if k < len(seps) else 0) * lh
    return {"n": n, "lh": lh, "rows": rows, "bottom": y, "miss": miss}


def overlaps(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


# ===========================================================================
#  THE LEDGER - four statuses, and only PASS is evidence
# ===========================================================================
DERIVED_INVARIANTS = {"I1"}      # implied by I8 (R6) - corroboration, not proof


class Ledger(object):
    def __init__(self):
        self.rows = []       # (inv, cand, hyp, f, kind, name, status, detail)

    def add(self, inv, cand, hyp, f, kind, name, status, detail=""):
        self.rows.append((inv, cand, hyp, f, kind, name, status, detail))

    def bad(self, inv, cand, hyp, f, kind, name, detail):
        self.add(inv, cand, hyp, f, kind, name, "FAIL", detail)

    def skip(self, inv, cand, hyp, f, kind, name, detail):
        self.add(inv, cand, hyp, f, kind, name, "SKIP", detail)

    def undecided(self, inv, cand, hyp, f, kind, name, detail):
        self.add(inv, cand, hyp, f, kind, name, "UNDEC", detail)

    def check(self, cond, inv, cand, hyp, f, kind, name, detail):
        self.add(inv, cand, hyp, f, kind, name, "PASS" if cond else "FAIL",
                 "" if cond else detail)
        return cond

    def check_tol(self, got, limit, tol, inv, cand, hyp, f, kind, name, detail):
        """A check whose verdict turns on `got <= limit`, where the two are
        measured quantities carrying a residual of +-tol.  If they are within
        tol of each other the answer is UNDECIDED - in BOTH directions.  The
        old code annotated a near FAIL as 'not decidable' and counted a near
        PASS silently; that asymmetry is what this fixes."""
        if abs(limit - got) < tol:
            self.undecided(inv, cand, hyp, f, kind, name,
                           "%s  (|%.1f - %.1f| = %.1f < TX.TOL %.1f: NOT "
                           "decidable on this evidence)"
                           % (detail, got, limit, abs(limit - got), tol))
            return None
        return self.check(got <= limit + 1e-9, inv, cand, hyp, f, kind, name,
                          detail)

    def count(self, status=None, **filt):
        n = 0
        for r in self.rows:
            rec = dict(zip(("inv", "cand", "hyp", "f", "kind", "name",
                            "status", "detail"), r))
            if status and rec["status"] != status:
                continue
            if any(rec[k] != v for k, v in filt.items()):
                continue
            n += 1
        return n


L = Ledger()


# ===========================================================================
#  HARNESS SELF-TESTS (R5a).
#
#  These are FACTS ABOUT THE MODEL, not assertions about any candidate: the
#  rounding law is its own definition, the strip decomposition references no
#  candidate value, and the tier font map comes from the harness.  In the
#  previous revision they were 1232 "invariant" PASSes that no candidate could
#  ever move.  They are still gate conditions - they are just no longer
#  counted as evidence about a layout.
# ===========================================================================
SELF = {"pass": 0, "fail": 0, "lines": []}


def _self(cond, what, detail=""):
    if cond:
        SELF["pass"] += 1
    else:
        SELF["fail"] += 1
        SELF["lines"].append("  x %s : %s" % (what, detail))


def selftests():
    # the rounding law, on the values that actually bite at 1.5
    for f in TIERS:
        for v in (1, 2, 3, 4, 5, 10, 13, 16, 72, 88, 108, 110, 488, 498):
            _self(sc(v, f) == int(math.floor(v * f + 0.5)),
                  "sc(%d,%g) is round-half-up" % (v, f))
    # the strip decomposition closes, BOTH kinds, at every tier - and it is a
    # statement about the MEASURED constants, not about a candidate
    for f in TIERS:
        cb = sc(CBW0, f) + sc(CBG, f) + sc(SWW, f) + sc(SWG, f) + \
            sc(TXW0 - CBW0, f) + sc(RM, f)
        pl = sc(CBG, f) + sc(SWW, f) + sc(SWG, f) + sc(TXW0, f) + sc(RM, f)
        _self(cb == sc(STRIP, f), "strip closes (checkbox) at f=%g" % f,
              "%d != %d" % (cb, sc(STRIP, f)))
        _self(pl == sc(STRIP, f), "strip closes (plain) at f=%g" % f,
              "%d != %d" % (pl, sc(STRIP, f)))
        _self(sc(PLOTG, f) + sc(STRIP, f) == sc(PLOTG + STRIP, f),
              "sc(2,f)+sc(108,f)==sc(110,f) at f=%g" % f)
    # the tier font map is what make_fontstyle.py ships.  The squeeze applies
    # only to SCALED sizes - at f=1 the generator emits the stock 13 verbatim,
    # which is why floor(13*1*0.92+.5) = 12 is NOT the shipped 1x value.
    for f in TIERS:
        want = 13 if f == 1.0 else int(math.floor(13 * f * 0.92 + 0.5))
        _self(PT_SQUEEZED[f] == want, "SQUEEZED pt at f=%g" % f,
              "%d != %d" % (PT_SQUEEZED[f], want))
        _self(PT_RAW[f] == int(math.floor(13 * f + 0.5)),
              "RAW pt at f=%g" % f)
    # the closed-form advance decomposition the box rule rests on
    for lab in ("Total Garbage", "Incinerated", "Capacity"):
        a = TX.advance_width(lab, 13)
        n = nglyphs(lab)
        for pt in (20, 26, 39):
            pred = (pt / 13.0) * a + n * TX.DELTA * (pt / 13.0 - 1)
            _self(abs(pred - TX.advance_width(lab, pt)) < 1e-6,
                  "advance decomposition %r @%dpt" % (lab, pt))
    # the provable glyph bound
    _self(abs(MIN_GLYPH_13 - 2.15) < 0.01, "narrowest glyph is 2.15px @13pt",
          "%r" % MIN_GLYPH_13)
    _self(NMAX_PROVABLE == 33, "NMAX_PROVABLE == 33", "%d" % NMAX_PROVABLE)
    _self(font_box(TXW0 - CBW0, 13, NMAX_PROVABLE) == TXW0 - CBW0,
          "the font box reduces to 72 at 13pt")
    # the totality shim really is total on every shipped label
    for _, _, labs, _b in EXTRA_LABEL_SETS:
        for l in labs:
            w, m = adv(l, 13)
            _self(w is not None or m is not None,
                  "adv() is total on %r" % l)


# ===========================================================================
#  THE INVARIANTS
# ===========================================================================
def inv1(cand, hyp, f, kind, cols):
    """I1* ORDER + NON-OVERLAP.  DERIVED: implied by I8 (R6)."""
    tag = "I1"
    sw, tx, cb = cols["swatch"], cols["text"], cols["cbox"]
    if cb:
        L.check(cb[1] <= sw[0], tag, cand, hyp, f, kind, "cbox.R<=swatch.L",
                "cbox.R=%d swatch.L=%d" % (cb[1], sw[0]))
        L.check(sw[0] - cb[1] >= sc(CBG, f), tag, cand, hyp, f, kind,
                "gap(cbox,swatch)>=sc(2,f)",
                "gap=%d need>=%d" % (sw[0] - cb[1], sc(CBG, f)))
    else:
        L.skip(tag, cand, hyp, f, kind, "cbox.R<=swatch.L",
               "plain kind has no checkbox child window")
        L.skip(tag, cand, hyp, f, kind, "gap(cbox,swatch)>=sc(2,f)",
               "plain kind has no checkbox child window")
    L.check(sw[1] <= tx[0], tag, cand, hyp, f, kind, "swatch.R<=text.L",
            "swatch.R=%d text.L=%d" % (sw[1], tx[0]))
    L.check(tx[0] - sw[1] >= sc(SWG, f), tag, cand, hyp, f, kind,
            "gap(swatch,text)>=sc(4,f)",
            "gap=%d need>=%d" % (tx[0] - sw[1], sc(SWG, f)))


def inv2(cand, hyp, f, kind, cols, st):
    """I2 VISIBILITY."""
    tag = "I2"
    W, H = win_w(f), win_h(f)
    if st["rows"] is None:
        for nm in ("swatch outside every cbox window",
                   "text outside every cbox window",
                   "painted rects inside client"):
            L.skip(tag, cand, hyp, f, kind, nm,
                   "lineH unknown at pt=%d (U1) - row rects cannot be built"
                   % st["pt"])
        return
    rows = st["rows"]
    boxes = [r["cbox"] for r in rows if "cbox" in r]
    if not boxes:
        # R5b: the previous revision scored these PASS over an EMPTY set.  A
        # structural null is not evidence.
        L.skip(tag, cand, hyp, f, kind, "swatch outside every cbox window",
               "plain kind has no checkbox child windows - vacuous")
        L.skip(tag, cand, hyp, f, kind, "text outside every cbox window",
               "plain kind has no checkbox child windows - vacuous")
    else:
        badsw = [(k, j) for k, r in enumerate(rows) for j, b in enumerate(boxes)
                 if overlaps(r["swatch"], b)]
        L.check(not badsw, tag, cand, hyp, f, kind,
                "swatch outside every cbox window",
                "%d swatch/checkbox intersections, first %s" %
                (len(badsw), badsw[0] if badsw else ""))
        badtx = [(k, j) for k, r in enumerate(rows) for j, b in enumerate(boxes)
                 if overlaps(r["text"], b)]
        L.check(not badtx, tag, cand, hyp, f, kind,
                "text outside every cbox window",
                "%d text/checkbox intersections, first %s" %
                (len(badtx), badtx[0] if badtx else ""))
    outside = []
    for k, r in enumerate(rows):
        for nm in ("swatch", "text", "cbox"):
            if nm not in r:
                continue
            a = r[nm]
            if a[0] < 0 or a[1] < 0 or a[2] > W or a[3] > H:
                outside.append((k, nm, a))
    L.check(not outside, tag, cand, hyp, f, kind, "painted rects inside client",
            "%d rects outside (0,0,%d,%d), first %s" %
            (len(outside), W, H, outside[0] if outside else ""))


def inv3(cand, hyp, f, kind, cols, pt, labels, setname, stock_wraps,
         box1=None):
    """I3 FIT - three clauses (R2/R3/R4).

    a  every label stock keeps on ONE line fits the box at pt(f).  UNDECIDED
       when the margin is inside the text model's own residual.
    b  no label may render on MORE lines than it does at stock.  Fewer is
       allowed: it can neither overflow nor overlap.
    c  the candidate's DECLARED glyph bound covers every label in this set.
    """
    tag = "I3"
    box = cols["text"][1] - cols["text"][0]
    b1 = box1 if box1 is not None else (TXW0 - CBW0 * (1 if kind == CHECKBOX
                                                       else 0))
    for lab in labels:
        w1, miss = adv(lab, 13)
        if w1 is None:
            L.skip(tag, cand, hyp, f, kind, "[%s] fits:%s" % (setname, lab),
                   "no measured advance for %s (R3) - add the glyph metric"
                   % miss)
            continue
        # --- a: single-line labels must stay single-line ---
        if lab not in stock_wraps and w1 <= b1 + 1e-9:
            if box == b1 and pt == 13:
                # VACUOUS, and it must not be counted as evidence (R5b): the
                # clause would be asserting advance(L,13) <= b1, which is the
                # very predicate that selected L.  True for every candidate at
                # f=1, and true at EVERY tier for F-STOCKSIZE, whose box and
                # font are both frozen at their 1x values - which is exactly
                # why I3 has no power against F and I6 is the one that names
                # it.  Recorded, not silently passed.
                L.skip(tag, cand, hyp, f, kind,
                       "[%s] fits:%s" % (setname, lab),
                       "vacuous: box==stock box (%d) at 13pt, so this clause "
                       "restates the predicate that selected the label" % b1)
            else:
                w, _ = adv(lab, pt)
                L.check_tol(w, box, TX.TOL, tag, cand, hyp, f, kind,
                            "[%s] fits:%s" % (setname, lab),
                            "%r needs %.1fpx at %dpt, box=%d" % (lab, w, pt, box))
        # --- b: line-count parity, EVERY label ---
        n_now, _ = wrap_lines(lab, pt, box)
        n_stock, _ = wrap_lines(lab, 13, b1)
        if n_now is None or n_stock is None:
            L.skip(tag, cand, hyp, f, kind, "[%s] lines:%s" % (setname, lab),
                   "no measured advance for %s (R3)" % miss)
        else:
            L.check(n_now <= n_stock, tag, cand, hyp, f, kind,
                    "[%s] lines:%s" % (setname, lab),
                    "%r renders on %d lines at %dpt/box %d; stock renders %d "
                    "at 13pt/box %d" % (lab, n_now, pt, box, n_stock, b1))
        # --- c: the declared glyph bound must cover this label ---
        if cols.get("nmax") is not None and w1 <= b1 + 1e-9:
            L.check(nglyphs(lab) <= cols["nmax"], tag, cand, hyp, f, kind,
                    "[%s] nmax covers:%s" % (setname, lab),
                    "%r has %d glyphs and fits the stock box, but the "
                    "candidate declares NMAX=%d - the box rule is not proven "
                    "for it" % (lab, nglyphs(lab), cols["nmax"]))


def inv4(cand, hyp, f, kind, cols, st):
    """I4 CONTAINMENT.  R1: the plot-clearance clause now reads the CHECKBOX
    edge, which is where the strip actually starts."""
    tag = "I4"
    W, H = win_w(f), win_h(f)
    L.check(cols["text"][1] <= W - sc(RM, f), tag, cand, hyp, f, kind,
            "text.R<=W-sc(4,f)",
            "text.R=%d limit=%d" % (cols["text"][1], W - sc(RM, f)))
    strip_l = (cols["cbox"] or cols["swatch"])[0]
    L.check(cols["plot_r"] + sc(PLOTG, f) <= strip_l and cols["plot_r"] > 0,
            tag, cand, hyp, f, kind, "plot right clears the strip",
            "plot_r=%d + sc(2,f)=%d > strip.L=%d - the plot frame and its "
            "gridlines are painted %d px INSIDE the legend strip"
            % (cols["plot_r"], sc(PLOTG, f), strip_l,
               cols["plot_r"] + sc(PLOTG, f) - strip_l))
    if st["rows"] is None:
        L.skip(tag, cand, hyp, f, kind, "column bottom<=winH",
               "lineH unknown at pt=%d (U1)" % st["pt"])
        return
    L.check(st["bottom"] <= H, tag, cand, hyp, f, kind, "column bottom<=winH",
            "bottom=%d winH=%d overflow=%+d, %d of %d rows whole" %
            (st["bottom"], H, st["bottom"] - H,
             sum(1 for r in st["rows"] if r["text"][3] <= H), len(st["rows"])))


def inv5(cand, hyp, kind, engine):
    """I5 f=1 REDUCTION - against the MEASURED stock columns."""
    tag, f = "I5", 1.0
    cols = engine(1.0, kind)
    m = M_STOCK[kind]
    if m["cbox"]:
        L.check(cols["cbox"] == m["cbox"], tag, cand, hyp, f, kind, "stock cbox",
                "model %s measured %s" % (cols["cbox"], m["cbox"]))
    else:
        L.check(cols["cbox"] is None, tag, cand, hyp, f, kind, "stock cbox",
                "plain kind must have no checkbox")
    L.check(cols["swatch"] == m["swatch"], tag, cand, hyp, f, kind, "stock swatch",
            "model %s measured %s" % (cols["swatch"], m["swatch"]))
    L.check(cols["text"][0] + m["text_lsb"] == m["text_l"], tag, cand, hyp, f,
            kind, "stock text.L(+lsb)",
            "model %d(+%d lsb) measured ink %d" %
            (cols["text"][0], m["text_lsb"], m["text_l"]))
    L.check(cols["plot_r"] == m["plot_r"], tag, cand, hyp, f, kind, "stock plot.R",
            "model %d measured %d" % (cols["plot_r"], m["plot_r"]))
    st = stack(1.0, kind, cols, 13)
    L.check(st["rows"] is not None and [r["top"] for r in st["rows"]] == m["tops"],
            tag, cand, hyp, f, kind, "stock row tops",
            "model %s measured %s" %
            ([r["top"] for r in (st["rows"] or [])], m["tops"]))
    L.check(st["rows"] is not None and
            [r["swatch"][1] for r in st["rows"]] == m["swtops"],
            tag, cand, hyp, f, kind, "stock swatch tops",
            "model %s measured %s" %
            ([r["swatch"][1] for r in (st["rows"] or [])], m["swtops"]))


def inv6(cand, hyp, kind, engine):
    """I6 MONOTONICITY + NORTHSTAR.  (The 'the candidate draws at the tier
    font' clause moved to the self-tests - it tested a harness flag, R5c.)"""
    tag = "I6"
    prev = None
    base = engine(1.0, kind)
    for f in TIERS:
        cols = engine(f, kind)
        widths = {"swatch": cols["swatch"][1] - cols["swatch"][0],
                  "text": cols["text"][1] - cols["text"][0]}
        if cols["cbox"]:
            widths["cbox"] = cols["cbox"][1] - cols["cbox"][0]
        for nm, w in sorted(widths.items()):
            L.check(w > 0, tag, cand, hyp, f, kind, "width(%s)>0" % nm,
                    "width=%d" % w)
        if prev is not None:
            for nm in ("swatch", "text"):
                L.check(cols[nm][0] >= prev[nm][0], tag, cand, hyp, f, kind,
                        "edge %s.L non-decreasing" % nm,
                        "%d < %d at the previous tier" % (cols[nm][0], prev[nm][0]))
            if cols["cbox"] and prev["cbox"]:
                L.check(cols["cbox"][0] >= prev["cbox"][0], tag, cand, hyp, f,
                        kind, "edge cbox.L non-decreasing",
                        "%d < %d" % (cols["cbox"][0], prev["cbox"][0]))
        b = {"swatch": base["swatch"][1] - base["swatch"][0],
             "text": base["text"][1] - base["text"][0]}
        if base["cbox"]:
            b["cbox"] = base["cbox"][1] - base["cbox"][0]
        for nm in sorted(b):
            L.check(widths[nm] >= sc(b[nm], f), tag, cand, hyp, f, kind,
                    "NORTHSTAR width(%s)>=sc(1x,f)" % nm,
                    "%d < sc(%d,%s)=%d - element NOT enlarged" %
                    (widths[nm], b[nm], f, sc(b[nm], f)))
        prev = cols


def inv7(cand, hyp, f, kind, cols):
    """I7 ROUNDING CONSISTENCY - candidate-dependent clauses ONLY (R5a)."""
    tag = "I7"
    got = {"swatch": cols["swatch"][1] - cols["swatch"][0],
           "text": cols["text"][1] - cols["text"][0]}
    if cols["cbox"]:
        got["cbox"] = cols["cbox"][1] - cols["cbox"][0]
    for nm, w in sorted(got.items()):
        how, base = cols["decl"].get(nm, ("free", 0))
        if how == "scaled":
            L.check(w == sc(base, f), tag, cand, hyp, f, kind,
                    "declared scaled: %s" % nm,
                    "%d != sc(%d,%s)=%d" % (w, base, f, sc(base, f)))
        elif how == "frozen":
            L.check(w == base, tag, cand, hyp, f, kind,
                    "declared frozen: %s" % nm, "%d != %d" % (w, base))
        else:
            L.check(isinstance(w, int) and w > 0, tag, cand, hyp, f, kind,
                    "declared free: %s is a positive integer" % nm, "%r" % w)
    # A font-box candidate's PLAIN box is INHERITED from the shared strip (as
    # stock's two kinds both close on 108) rather than derived.  It must still
    # be at least what the font rule demands for the 88 px stock plain box -
    # otherwise the plain chart would wrap where the checkbox chart does not.
    # NON-OBVIOUS RESULT worth recording: for E2 and E3 the inherited value is
    # EXACTLY the derived one at every tier (2x: 200 == 200; 1.5x: 148; 3x:
    # 311), because the strip carries sc(16,f) and the two boxes differ by the
    # design checkbox width.  J-TAPTARGET, whose checkbox is wider, inherits
    # MORE than it needs - allowed, and visible in the detail.
    if cols["box_rule"] and kind == PLAIN:
        _, nmax = cols["box_rule"]
        want = font_box(TXW0, PT_RAW[f], nmax)
        L.check(got["text"] >= want, tag, cand, hyp, f, kind,
                "inherited plain box >= font-derived plain box",
                "inherited %d, font rule needs %d" % (got["text"], want))


def inv8(cand, hyp, f, kind, cols, st):
    """I8 COUPLED PAIR (law 43).  R7: the swatch clauses accept EITHER the sc
    rule or the line-proportional rule while U6 is open."""
    tag = "I8"
    W = win_w(f)
    sw, tx, cb = cols["swatch"], cols["text"], cols["cbox"]
    if cb:
        L.check(sw[0] - cb[1] == sc(CBG, f), tag, cand, hyp, f, kind,
                "swatch.L-cbox.R==sc(2,f)",
                "%d != %d" % (sw[0] - cb[1], sc(CBG, f)))
    else:
        L.skip(tag, cand, hyp, f, kind, "swatch.L-cbox.R==sc(2,f)",
               "plain kind has no checkbox child window")
    L.check(tx[0] - sw[1] == sc(SWG, f), tag, cand, hyp, f, kind,
            "text.L-swatch.R==sc(4,f)", "%d != %d" % (tx[0] - sw[1], sc(SWG, f)))
    L.check(W - tx[1] == sc(RM, f), tag, cand, hyp, f, kind,
            "W-text.R==sc(4,f)", "%d != %d" % (W - tx[1], sc(RM, f)))
    lh = st["lh"]
    for nm, base, got in (("swatch dy", SWDY, cols["swdy"]),
                          ("swatch height", SWH, cols["swh"])):
        opts = {sc(base, f)}
        if lh is not None:
            opts.add(int(math.floor(base * lh / float(LH1) + 0.5)))
        if lh is None:
            L.skip(tag, cand, hyp, f, kind, "%s follows sc or line rule" % nm,
                   "lineH unknown at pt=%d (U1/U6): the line-proportional "
                   "alternative cannot be evaluated" % st["pt"])
        else:
            L.check(got in opts, tag, cand, hyp, f, kind,
                    "%s follows sc or line rule" % nm,
                    "%d is neither sc(%d,%s)=%d nor round(%d*lineH/%d)=%d"
                    % (got, base, f, sc(base, f), base, LH1,
                       int(math.floor(base * lh / float(LH1) + 0.5))))
    if st["rows"] is None:
        L.skip(tag, cand, hyp, f, kind, "cbox.T==text.T==rowTop",
               "lineH unknown at pt=%d (U1)" % st["pt"])
        return
    if not any("cbox" in r for r in st["rows"]):
        L.skip(tag, cand, hyp, f, kind, "cbox.T==text.T==rowTop",
               "plain kind has no checkbox child windows - vacuous")
        return
    bad = []
    for k, r in enumerate(st["rows"]):
        if "cbox" in r:
            if r["cbox"][1] != r["top"] or r["text"][1] != r["top"]:
                bad.append(k)
            if r["cbox"][3] - r["cbox"][1] != r["cbox"][2] - r["cbox"][0]:
                bad.append(k)
    L.check(not bad, tag, cand, hyp, f, kind, "cbox.T==text.T==rowTop",
            "rows %s are decoupled" % bad[:4])


def inv9(cand, hyp, f, kind, cols, st):
    """I9 ROW PITCH (new, R8).  Consecutive checkbox CHILD WINDOWS must not
    overlap each other.  I2 could never catch this: it only compared the
    swatch and the text against the checkbox, and those are X-disjoint by
    construction.  The slack is EXACTLY ZERO at f=2 (a sc(16,2)=32 px square
    window in a lineH(26)+PAD = 32 px one-line row pitch)."""
    tag = "I9"
    if st["rows"] is None:
        L.skip(tag, cand, hyp, f, kind, "checkbox windows do not overlap",
               "lineH unknown at pt=%d (U1)" % st["pt"])
        return
    boxes = [r["cbox"] for r in st["rows"] if "cbox" in r]
    if len(boxes) < 2:
        L.skip(tag, cand, hyp, f, kind, "checkbox windows do not overlap",
               "fewer than two checkbox child windows - vacuous")
        return
    bad = [(k, boxes[k][3], boxes[k + 1][1]) for k in range(len(boxes) - 1)
           if boxes[k][3] > boxes[k + 1][1]]
    slack = min(boxes[k + 1][1] - boxes[k][3] for k in range(len(boxes) - 1))
    L.check(not bad, tag, cand, hyp, f, kind,
            "checkbox windows do not overlap",
            "%d overlapping pairs, first row %d bottom %d over row %d top %d "
            "(min slack %d)" % (len(bad), bad[0][0], bad[0][1], bad[0][0] + 1,
                                bad[0][2], slack) if bad else "")


def inv10(cand, hyp, kind, engine):
    """I10 FRAME (new, R9).  Nothing else in this file constrains the
    coordinate frame the numbers live in: perturbing the assumed 1x origin by
    +-4 px left I5 at 168/168 PASS while every published target moved 8 px.

    The anchor is the parent panel's painted client, which the chart layout
    never touches:  winW(f) must equal sc(498,f) - 2*sc(5,f).
    U8: that identity holds at f=1, 2 and 3 and fails by 1 px at f=1.5
    (731 vs 732) - task #75's parity divergence reaching the chart frame - so
    f=1.5 is SKIPPED rather than asserted either way."""
    tag = "I10"
    if kind != CHECKBOX:
        return                                # frame is per-tier, not per-kind
    for f in TIERS:
        if f == 1.5:
            L.skip(tag, cand, hyp, f, kind, "winW == panel anchor",
                   "U8: sc(488,1.5)=%d but sc(498,1.5)-2*sc(5,1.5)=%d. The "
                   "two frame derivations diverge by 1px at 1.5x only. ONE "
                   "MEASUREMENT: log chart WIN[0xA8] width at the 1.5x tier"
                   % (win_w(f), frame_w(f)))
            continue
        L.check(win_w(f) == frame_w(f), tag, cand, hyp, f, kind,
                "winW == panel anchor",
                "winW=%d but sc(498,f)-2*sc(5,f)=%d" % (win_w(f), frame_w(f)))
    L.check(win_w(2.0) == LIVE_2X_WINW, tag, cand, hyp, 2.0, kind,
            "winW(2) == the LOGGED live chart width",
            "%d != %d" % (win_w(2.0), LIVE_2X_WINW))
    L.check(win_h(2.0) == LIVE_2X_WINH, tag, cand, hyp, 2.0, kind,
            "winH(2) == the LOGGED live chart height",
            "%d != %d" % (win_h(2.0), LIVE_2X_WINH))
    L.check(sc(PANEL_CLIENT_1, 2.0) == 996, tag, cand, hyp, 2.0, kind,
            "panel client doubles: 996 == 2*498",
            "%d != 996 (MEASURED off graphs-ours-2x.png)"
            % sc(PANEL_CLIENT_1, 2.0))


# ===========================================================================
#  THE CANDIDATES + THEIR DECLARED EXPECTATIONS
#
#    must_fail  - invariants this candidate is KNOWN to violate at f>=1.5.  If
#                 it does not violate them, the ORACLE is too weak and the gate
#                 fails.  (Subset requirement; extra failures are reported.)
#    must_pass  - invariants this candidate MUST satisfy at EVERY tier.  "ALL"
#                 means every invariant.
#  Keyed by (hypothesis or None, kind); None is the fallback.
#
#  Every expectation is measured at f>=1.5 because EVERY candidate is
#  byte-identical to stock at f=1 - which is precisely why passing I5 never
#  caught any of the four shipped patches.  I5 is necessary, not sufficient.
# ===========================================================================
ALL = "ALL"

CANDIDATES = [
    dict(key="A-FROZEN", engine=eng_frozen,
         note="what the game DRAWS TODAY - the calibration candidate",
         expect={(None, CHECKBOX): ({"I1", "I2", "I3", "I4", "I6", "I8"}, set()),
                 (None, PLAIN):    ({"I1", "I3", "I4", "I6", "I8"}, set())}),
    dict(key="B-v2544", engine=eng_v2544,
         note="shipped v2.54.4: scale the swatch and its gap, nothing else",
         expect={(None, CHECKBOX): ({"I1", "I2", "I3"}, set()),
                 (None, PLAIN):    ({"I3", "I4"}, set())}),
    dict(key="C-v2542", engine=eng_v2542,
         note="v2.54.2: widen the text box, leave the checkbox window put",
         # history: FIXED Income/Expenses, BROKE Garbage. The model must
         # reproduce that split - and it additionally finds the latent I4 the
         # eye could not see: the widened box intrudes on the plot's reserve.
         expect={(None, CHECKBOX): ({"I1", "I2", "I4", "I8"}, set()),
                 (None, PLAIN):    ({"I4"}, {"I1", "I2", "I6", "I8"})}),
    dict(key="D-v2543", engine=eng_v2543,
         note="v2.54.3: also move the checkbox, reserving the DESIGN width",
         expect={(None, CHECKBOX): ({"I2", "I4"}, set()),
                 (None, PLAIN):    ({"I4"}, set())}),
    dict(key="E-STRIPxf", engine=eng_scaled_strip,
         note="the sibling oracles' fix: strip = sc(108,f) -> box sc(72,f)",
         # DEAD as of U4: certified only under the REFUTED squeezed font.
         expect={("SQUEEZED", CHECKBOX): (set(), ALL),
                 ("SQUEEZED", PLAIN):    (set(), ALL),
                 ("RAW", CHECKBOX):      ({"I3"}, set()),
                 ("RAW", PLAIN):         (set(), ALL)}),
    dict(key="G-CBOXFREE", engine=eng_cboxfree,
         note="R1 counterexample: reserve only the PAINTED strip (plot drawn "
              "through every checkbox) - passed the OLD gate with zero fails",
         expect={(None, CHECKBOX): ({"I4", "I5"}, set()),
                 (None, PLAIN):    ({"I5"}, set())}),
    dict(key="H-EARLYCHART", engine=eng_earlychart,
         note="R1 counterexample: certified strip + the plot.R EARLYCHART "
              "already writes - the MOST LIKELY thing to be built",
         expect={(None, CHECKBOX): ({"I4"}, set()),
                 (None, PLAIN):    ({"I4"}, set())}),
    dict(key="E2-FONTBOX", engine=eng_font_box, certified=True,
         note="CERTIFIED: scaled furniture + a box sized by the FONT against "
              "a PROVABLE glyph bound (NMAX=%d)" % NMAX_PROVABLE,
         expect={(None, CHECKBOX): (set(), ALL),
                 (None, PLAIN):    (set(), ALL)}),
    dict(key="E3-CORPUS", engine=eng_font_box_corpus,
         note="informative: same rule, NMAX declared from the corpus (20). "
              "10px narrower at 2x, and it carries U7",
         expect={(None, CHECKBOX): (set(), ALL),
                 (None, PLAIN):    (set(), ALL)}),
    dict(key="J-TAPTARGET", engine=eng_taptarget,
         note="I9 falsifier: E2's strip with a sc(20,f) checkbox window - "
              "every gap exact, nothing overlaps in X, and the checkboxes "
              "overlap EACH OTHER",
         expect={(None, CHECKBOX): ({"I9"}, {"I1", "I2", "I3", "I4", "I5",
                                             "I6", "I7", "I8"}),
                 (None, PLAIN):    (set(), ALL)}),
    dict(key="F-STOCKSIZE", engine=eng_stocksize, stock_font=True,
         note="NORTHSTAR VIOLATION control: stock-size legend on a big window",
         expect={(None, CHECKBOX): ({"I6"}, {"I2", "I3", "I5", "I7"}),
                 (None, PLAIN):    ({"I6"}, {"I2", "I3", "I5", "I7"})}),
]


def expectation(cand, hyp, kind):
    e = cand["expect"]
    return e.get((hyp, kind), e.get((None, kind), (set(), set())))


def run_candidate(cand, hyp_name, pt_map):
    key, engine = cand["key"], cand["engine"]
    pt_of = (lambda f: 13) if cand.get("stock_font") else (lambda f: pt_map[f])
    for kind in (CHECKBOX, PLAIN):
        inv5(key, hyp_name, kind, engine)
        inv6(key, hyp_name, kind, engine)
        inv10(key, hyp_name, kind, engine)
        for f in TIERS:
            cols = engine(f, kind)
            pt = pt_of(f)
            st = stack(f, kind, cols, pt)
            st["pt"] = pt
            inv1(key, hyp_name, f, kind, cols)
            inv2(key, hyp_name, f, kind, cols, st)
            inv3(key, hyp_name, f, kind, cols, pt, LABELS[kind], "MEASURED",
                 STOCK_WRAPS)
            inv4(key, hyp_name, f, kind, cols, st)
            inv7(key, hyp_name, f, kind, cols)
            inv8(key, hyp_name, f, kind, cols, st)
            inv9(key, hyp_name, f, kind, cols, st)
            # I3 over EVERY known chart's real label set (R2/R3).  These sets
            # have no measured separators or stock wraps, so only I3 runs.
            for setname, skind, labs, binding in EXTRA_LABEL_SETS:
                if skind != kind:
                    continue
                inv3(key, hyp_name, f, kind, cols, pt, labs,
                     "%s/%s" % (setname, binding), set())


# ===========================================================================
#  CALIBRATION CROSS-CHECK: does A-FROZEN really reproduce the LIVE 2x layout?
# ===========================================================================
def calibrate():
    print("=" * 78)
    print("CALIBRATION - does A-FROZEN reproduce the MEASURED live 2x layout?")
    print("  (if this section is not exact, nothing else in this file is")
    print("   adjudicating the defect the user actually sees)")
    print("=" * 78)
    bad = 0
    n = 0
    for kind in (CHECKBOX, PLAIN):
        cols = eng_frozen(2.0, kind)
        m = M_LIVE_2X[kind]
        pairs = [("text", cols["text"], m["text"]),
                 ("swatch.L", cols["swatch"][0], m["swatch_l"]),
                 ("plot_r", cols["plot_r"], m["plot_r"]),
                 ("plot_r nolegend", cols["plot_r_noleg"],
                  M_LIVE_2X_PLOT_R_NOLEGEND)]
        if m["cbox"]:
            pairs.append(("cbox", cols["cbox"], m["cbox"]))
        for nm, got, want in pairs:
            n += 1
            ok = got == want
            bad += 0 if ok else 1
            print("  [%s] %-9s %-16s model %-14s measured %s"
                  % ("PASS" if ok else "FAIL", kind, nm, got, want))
        st = stack(2.0, kind, cols, 26)
        if m["tops"]:
            n += 1
            got = [r["top"] for r in st["rows"]]
            ok = got == m["tops"]
            bad += 0 if ok else 1
            print("  [%s] %-9s %-16s model %s" %
                  ("PASS" if ok else "FAIL", kind, "row tops", got))
            if not ok:
                print("       %-9s %-16s measured %s" % ("", "", m["tops"]))
    # U4, RESOLVED this pass - the three independent measurements
    n += 1
    w24, _ = adv("Expenses", 24)
    w26, _ = adv("Expenses", 26)
    u4 = (w24 <= TXW0) and (w26 > TXW0)
    bad += 0 if u4 else 1
    print("  [%s] %-9s %-16s 'Expenses' %.1fpx@24 (fits 88) / %.1fpx@26 "
          "(wraps)" % ("PASS" if u4 else "FAIL", PLAIN, "U4 wrap", w24, w26))
    print("       MEASURED in graphs-ours-2x.png: the plain legend's row 1 is")
    print("       painted as 'Expense' / 's' (third ink run 6px wide at")
    print("       chart-local x 885..890, text.L=884). Only 26pt wraps.")
    print("       Corroborated by the row-0 ink width (68 measured; 70.1@26pt,")
    print("       64.4@24pt) and by the nine 2x Garbage row pitches.")
    print("       => U4 RESOLVED to RAW. SQUEEZED is retained as a refuted-")
    print("       but-retained conservative hypothesis, not as an open question.")
    print("  -> %d/%d calibration checks exact" % (n - bad, n))
    return bad, n


# ===========================================================================
#  REPORTING
# ===========================================================================
def admissible_bands():
    print()
    print("=" * 78)
    print("ADMISSIBLE TEXT-BOX BAND per tier (what I3 is really demanding)")
    print("  lower = widest label stock keeps on ONE line, at that point size")
    print("  upper = narrowest label stock WRAPS (exceeding it is ALLOWED -")
    print("          it merely wraps LESS than stock, which I3b permits)")
    print("=" * 78)
    print("  %-6s %-22s %-22s %-8s %-8s %s"
          % ("tier", "SQUEEZED pt / band", "RAW pt / band  <= MEASURED",
             "E box", "E2 box", "E3 box"))
    for f in TIERS:
        cells = []
        for _, pm in PT_HYPS:
            pt = pm[f]
            lo = max(TX.advance_width(l, pt) for l in LABELS[CHECKBOX]
                     if l not in STOCK_WRAPS)
            hi = min(TX.advance_width(l, pt) for l in LABELS[CHECKBOX]
                     if l in STOCK_WRAPS)
            cells.append("%2dpt  %3d..%3d" % (pt, int(math.ceil(lo)),
                                              int(math.ceil(hi)) - 1))
        e = eng_scaled_strip(f, CHECKBOX)["text"]
        e2 = eng_font_box(f, CHECKBOX)["text"]
        e3 = eng_font_box_corpus(f, CHECKBOX)["text"]
        print("  %-6s %-22s %-22s %-8d %-8d %d"
              % ("%gx" % f, cells[0], cells[1], e[1] - e[0], e2[1] - e2[0],
                 e3[1] - e3[0]))
    print("  The E2 box deliberately sits ABOVE the upper band edge: the band")
    print("  is fitted to the NINE Garbage labels, and the box must hold any")
    print("  label the stock box holds (R2).  Exceeding the upper edge only")
    print("  means the two stock-wrapped labels may stop wrapping.")


def acceptance_targets():
    print()
    print("=" * 78)
    print("ACCEPTANCE TARGETS - the numbers a fix must produce (E2-FONTBOX)")
    print("  chart-local px. A patch producing different numbers is NOT")
    print("  certified. The E3 row is the informative tighter variant (U7).")
    print("=" * 78)
    print("  %-6s %-6s %-6s %-11s %-11s %-16s %-7s %s"
          % ("tier", "winW", "strip", "cbox", "swatch", "text (box)",
             "plot.R", "legend bottom / winH"))
    for f in TIERS:
        g = eng_font_box(f, CHECKBOX)
        strip = win_w(f) - (g["cbox"][0])
        st = stack(f, CHECKBOX, g, PT_RAW[f])
        if st["rows"] is None:
            vert = "SKIP (U1: lineH unknown at %dpt)" % PT_RAW[f]
        else:
            vert = "%d / %d  %s (lines %s)" % (
                st["bottom"], win_h(f),
                "fits, %d spare" % (win_h(f) - st["bottom"])
                if st["bottom"] <= win_h(f) else
                "OVERFLOW %+d" % (st["bottom"] - win_h(f)), sum(st["n"]))
        print("  %-6s %-6d %-6d %-11s %-11s %-16s %-7d %s"
              % ("%gx" % f, win_w(f), strip,
                 "%d..%d" % g["cbox"], "%d..%d" % g["swatch"],
                 "%d..%d (%d)" % (g["text"][0], g["text"][1],
                                  g["text"][1] - g["text"][0]),
                 g["plot_r"], vert))
    print()
    print("  DELTA AGAINST THE MECHANISM WORK.  EARLYCHART stores plot.R=%d at"
          % (win_w(2.0) - sc(PLOTG + STRIP, 2.0)))
    print("  2x today.  E2 needs %d; E3 needs %d.  Candidate H-EARLYCHART is"
          % (eng_font_box(2.0, CHECKBOX)["plot_r"],
             eng_font_box_corpus(2.0, CHECKBOX)["plot_r"]))
    print("  exactly 'adopt the strip, keep the 756' and it FAILS I4 - the")
    print("  plot border would be painted inside the checkbox column.")
    print()
    print("  TIERS WITH NO VERTICAL VERIFICATION (U1): 1.5x and 3x. The")
    print("  horizontal targets above are asserted at those tiers; the row")
    print("  stack, the overflow test and the checkbox-pitch test are NOT.")
    print("  Both are SHIPPED packages. ONE MEASUREMENT clears both: capture a")
    print("  1-line legend row at the 1.5x tier and read the swatch-top pitch")
    print("  (pitch - PAD = lineH), then the same at 3x.")


def geometry_table():
    print()
    print("=" * 78)
    print("GEOMETRY per candidate (checkbox kind), chart-local px")
    print("=" * 78)
    print("  %-13s %-5s %-6s %-12s %-12s %-15s %-6s"
          % ("candidate", "f", "winW", "cbox", "swatch", "text", "plot.R"))
    for c in CANDIDATES:
        for f in TIERS:
            g = c["engine"](f, CHECKBOX)
            print("  %-13s %-5s %-6d %-12s %-12s %-15s %-6d"
                  % (c["key"], "%gx" % f, win_w(f),
                     "%d..%d" % g["cbox"] if g["cbox"] else "-",
                     "%d..%d" % g["swatch"],
                     "%d..%d (%d)" % (g["text"][0], g["text"][1],
                                      g["text"][1] - g["text"][0]),
                     g["plot_r"]))
        print()


def derived_audit():
    """R6: I1 is claimed to be IMPLIED by I8.  Check the claim every run."""
    cells8 = set()
    for inv, c, h, f, k, n, st, d in L.rows:
        if inv == "I8" and st == "FAIL":
            cells8.add((c, h, f, k))
    bad = []
    for inv, c, h, f, k, n, st, d in L.rows:
        if inv == "I1" and st == "FAIL" and (c, h, f, k) not in cells8:
            bad.append((c, h, f, k, n))
    return bad


def main():
    print("=" * 78)
    print("prove_chart_legend - #57 Graphs legend ACCEPTANCE ORACLE")
    print("  %d candidates x %d font hypotheses x %d tiers x 2 legend kinds"
          % (len(CANDIDATES), len(PT_HYPS), len(TIERS)))
    print("  + I3 over %d additional real chart label sets"
          % len(EXTRA_LABEL_SETS))
    print("  four statuses: PASS / FAIL / SKIP / UNDECIDED. Only PASS is")
    print("  evidence; SKIP and UNDECIDED are counted separately and named.")
    print("=" * 78)

    selftests()
    print()
    print("HARNESS SELF-TESTS (facts about the MODEL, not about a candidate)")
    print("  the sc() rounding law, the strip-closure identities, the tier")
    print("  font map, the advance decomposition, the provable glyph bound,")
    print("  and adv()'s totality on every shipped label.")
    print("  -> %d pass, %d fail" % (SELF["pass"], SELF["fail"]))
    for ln in SELF["lines"]:
        print(ln)

    print()
    cal_bad, cal_n = calibrate()

    for hyp_name, pt_map in PT_HYPS:
        for cand in CANDIDATES:
            run_candidate(cand, hyp_name, pt_map)

    # ---- per-invariant summary -------------------------------------------
    print()
    print("=" * 78)
    print("PER-INVARIANT TOTALS (across every candidate, hypothesis, tier, kind)")
    print("=" * 78)
    names = {"I1": "ORDER + NON-OVERLAP *", "I2": "VISIBILITY", "I3": "FIT",
             "I4": "CONTAINMENT", "I5": "f=1 REDUCTION",
             "I6": "MONOTONICITY + NORTHSTAR", "I7": "ROUNDING CONSISTENCY",
             "I8": "COUPLED PAIR (law 43)", "I9": "ROW PITCH",
             "I10": "FRAME"}
    print("  %-5s %-26s %7s %7s %7s %7s %7s" %
          ("inv", "name", "checks", "pass", "fail", "skip", "undec"))
    for inv in ("I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "I9", "I10"):
        tot = L.count(inv=inv)
        print("  %-5s %-26s %7d %7d %7d %7d %7d"
              % (inv, names[inv], tot, L.count("PASS", inv=inv),
                 L.count("FAIL", inv=inv), L.count("SKIP", inv=inv),
                 L.count("UNDEC", inv=inv)))
    print("  %-5s %-26s %7d %7d %7d %7d %7d"
          % ("", "TOTAL", len(L.rows), L.count("PASS"), L.count("FAIL"),
             L.count("SKIP"), L.count("UNDEC")))
    print("  * I1 is DERIVED: strictly implied by I8 (R6).  It is retained as")
    print("    the readable statement of the defect but is NOT independent")
    print("    corroboration, and its checks are excluded from the count below.")
    indep = sum(L.count("PASS", inv=i) for i in
                ("I2", "I3", "I4", "I5", "I6", "I7", "I8", "I9", "I10"))
    print("    independent PASSes (excluding I1): %d" % indep)

    # ---- per-candidate verdicts ------------------------------------------
    print()
    print("=" * 78)
    print("PER-CANDIDATE VERDICT  (f>=1.5 only: every candidate is stock at f=1)")
    print("=" * 78)
    gate_fails = []
    for cand in CANDIDATES:
        key = cand["key"]
        print("\n  %s  -- %s" % (key, cand["note"]))
        for hyp_name, _ in PT_HYPS:
            for kind in (CHECKBOX, PLAIN):
                got, f1, und = set(), set(), set()
                for inv, c, h, f, k, n, st, d in L.rows:
                    if c != key or h != hyp_name or k != kind:
                        continue
                    if st == "FAIL":
                        (got if f >= 1.5 else f1).add(inv)
                    elif st == "UNDEC":
                        und.add(inv)
                must_fail, must_pass = expectation(cand, hyp_name, kind)
                mp_txt = "ALL" if must_pass == ALL else \
                    (",".join(sorted(must_pass)) if must_pass else "-")
                print("    %-9s %-9s f=1 fails %-6s f>=1.5 fails %-22s "
                      "undec %-6s [expect fail %s / pass %s]"
                      % (hyp_name, kind,
                         ",".join(sorted(f1)) if f1 else "none",
                         ",".join(sorted(got)) if got else "none",
                         ",".join(sorted(und)) if und else "none",
                         ",".join(sorted(must_fail)) if must_fail else "-",
                         mp_txt))
                missing = must_fail - (got | f1)
                if missing:
                    gate_fails.append(
                        "%s/%s/%s: expected to VIOLATE %s and did not - the "
                        "oracle is too weak to certify a fix"
                        % (key, hyp_name, kind, ",".join(sorted(missing))))
                if must_pass == ALL:
                    if got or f1:
                        gate_fails.append(
                            "%s/%s/%s: required to pass EVERYTHING, failed %s"
                            % (key, hyp_name, kind,
                               ",".join(sorted(got | f1))))
                    if cand.get("certified") and und:
                        gate_fails.append(
                            "%s/%s/%s: CERTIFIED candidate has UNDECIDED "
                            "checks in %s - a verdict resting on a difference "
                            "inside the text model's residual is not a verdict"
                            % (key, hyp_name, kind, ",".join(sorted(und))))
                elif must_pass:
                    broke = must_pass & (got | f1)
                    if broke:
                        gate_fails.append(
                            "%s/%s/%s: required to pass %s, failed %s"
                            % (key, hyp_name, kind,
                               ",".join(sorted(must_pass)),
                               ",".join(sorted(broke))))

    # I5 must hold for every candidate EXCEPT the ones that DECLARE they break
    # it (G-CBOXFREE does: its reserve rule cannot reproduce stock's own 108).
    i5_exempt = set()
    for cd in CANDIDATES:
        for (h, k), (mf, _mp) in cd["expect"].items():
            if "I5" in mf:
                i5_exempt.add(cd["key"])
    i5f = sum(1 for inv, c, h, f, k, n, st, d in L.rows
              if inv == "I5" and st == "FAIL" and c not in i5_exempt)
    if i5f:
        gate_fails.append("I5 failed %d times on a candidate that did NOT "
                          "declare it - a model that does not reduce to stock "
                          "at f=1 is wrong regardless of 2x" % i5f)
    if cal_bad:
        gate_fails.append("calibration: A-FROZEN does not reproduce the live 2x "
                          "layout in %d of %d checks" % (cal_bad, cal_n))
    if SELF["fail"]:
        gate_fails.append("%d harness self-test(s) failed - the MODEL is broken,"
                          " so no candidate verdict means anything"
                          % SELF["fail"])
    da = derived_audit()
    if da:
        gate_fails.append("I1 failed where I8 passed in %d cells (first %s) - "
                          "I1 is NOT derived after all and must be re-stated as"
                          " independent" % (len(da), da[0]))

    admissible_bands()
    acceptance_targets()
    if DETAILS:
        geometry_table()

    if VERBOSE:
        print()
        print("=" * 78)
        print("EVERY CHECK")
        print("=" * 78)
        for inv, c, h, f, k, n, st, d in L.rows:
            print("  %-4s %-13s %-9s %-4s %-8s %-38s %-5s %s"
                  % (inv, c, h, "%gx" % f, k, n[:38], st,
                     d if st != "PASS" else ""))
    else:
        print()
        print("  (--verbose lists all %d checks; --details prints the geometry)"
              % len(L.rows))

    # ---- the gate ---------------------------------------------------------
    print()
    print("=" * 78)
    print("GATE")
    print("=" * 78)
    print("  harness self-tests %d pass, %d fail" % (SELF["pass"], SELF["fail"]))
    print("  calibration        %d/%d exact" % (cal_n - cal_bad, cal_n))
    print("  invariant checks   %d  (PASS %d, FAIL %d, SKIP %d, UNDECIDED %d)"
          % (len(L.rows), L.count("PASS"), L.count("FAIL"), L.count("SKIP"),
             L.count("UNDEC")))
    print("  I1 is DERIVED, so independent PASSes = %d" % indep)
    print()
    print("  SKIP and UNDECIDED are NOT passes. Every one is counted, by")
    print("  named reason:")
    buckets = {"U1 lineH unknown at this tier": 0,
               "U6 swatch rule undecidable without lineH": 0,
               "U8 winW(1.5) frame ambiguity": 0,
               "R3 no measured advance for a glyph": 0,
               "vacuous: plain kind has no checkbox windows": 0,
               "vacuous: box IS the stock box at 13pt": 0,
               "other": 0}
    for inv, c, h, f, k, n, st, d in L.rows:
        if st != "SKIP":
            continue
        if "U8" in d:
            buckets["U8 winW(1.5) frame ambiguity"] += 1
        elif "U1/U6" in d:
            buckets["U6 swatch rule undecidable without lineH"] += 1
        elif "U1" in d:
            buckets["U1 lineH unknown at this tier"] += 1
        elif "no measured advance" in d:
            buckets["R3 no measured advance for a glyph"] += 1
        elif "restates the predicate" in d:
            buckets["vacuous: box IS the stock box at 13pt"] += 1
        elif "vacuous" in d or "no checkbox" in d:
            buckets["vacuous: plain kind has no checkbox windows"] += 1
        else:
            buckets["other"] += 1
    for k in sorted(buckets):
        if buckets[k]:
            print("    %-46s %5d" % (k, buckets[k]))
    print("    %-46s %5d" % ("UNDECIDED (inside TX.TOL = %.1f px)" % TX.TOL,
                             L.count("UNDEC")))
    print("  The glyph table has no B H K N O Q S U X Y Z, h j k q z, no")
    print("  digit and no # ( ) - $ % : those labels are counted UNKNOWN, not")
    print("  assumed to fit.  Measuring them unlocks Water/Power, Crime,")
    print("  Funds, Res. Avg. Income and both by-Age charts in one pass.")
    print("    U7  E3-CORPUS's NMAX=20 is DECLARED, not proven; E2 uses the")
    print("        provable NMAX=%d and carries no such unknown" % NMAX_PROVABLE)

    if gate_fails:
        print()
        for m in gate_fails:
            print("  x " + m)
        print()
        print("OVERALL: FAIL")
        return 1
    print()
    print("  every declared expectation held: the defective and limited")
    print("  candidates - INCLUDING the two that passed the previous")
    print("  revision with zero failures - violated the invariants they are")
    print("  known to violate, and E2-FONTBOX passed every DECIDABLE check")
    print("  under both font hypotheses with no UNDECIDED check anywhere.")
    print()
    print("OVERALL: PASS")
    return 0


# ===========================================================================
#  THE MUTATION SUITE - "is this gate an instrument?"
#
#  Three families now (R12):
#    delete an invariant / corrupt a measurement / swap the candidate  - and
#    PERTURB THE CERTIFIED CANDIDATE, which is the family that would have
#    caught the I4 hole before two counterexamples walked through it.
# ===========================================================================
def mutate():
    import contextlib
    import importlib
    import io

    def trial(label, mut, expect_red=True):
        sys.modules.pop("prove_chart_legend", None)
        m = importlib.import_module("prove_chart_legend")
        mut(m)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = m.main()
        except Exception as e:                       # a crash is not a pass
            print("    %-52s CRASHED: %s" % (label, e))
            return False
        xs = [l.strip()[2:] for l in buf.getvalue().splitlines()
              if l.strip().startswith("x ")]
        ok = (rc != 0) if expect_red else (rc == 0)
        print("    %-52s rc=%d  %s%s"
              % (label, rc, (xs[0][:70] if xs else "no gate complaint"),
                 "" if ok else "   *** WRONG WAY ***"))
        return ok

    def perturb(field, delta):
        """Move ONE field of the CERTIFIED candidate and require a red gate."""
        def mut(m):
            base = m.eng_font_box

            def shifted(f, kind, _b=base, _fl=field, _d=delta):
                c = dict(_b(f, kind))
                if f == 1.0:
                    return c          # keep I5 clean: perturb f>=1.5 only
                if _fl == "plot_r":
                    c["plot_r"] = c["plot_r"] + _d
                elif _fl == "box":
                    c["text"] = (c["text"][0] - _d, c["text"][1])
                elif _fl == "swdy":
                    c["swdy"] = c["swdy"] + _d
                elif _fl == "cbox":
                    if c["cbox"]:
                        c["cbox"] = (c["cbox"][0], c["cbox"][1] + _d)
                elif _fl == "top":
                    c["top"] = c["top"] + _d
                elif _fl == "pad":
                    c["pad"] = c["pad"] + _d
                return c
            for cd in m.CANDIDATES:
                if cd.get("certified"):
                    cd["engine"] = shifted
        return mut

    print("=" * 78)
    print("MUTATION SUITE - every row must turn the gate RED (except M0)")
    print("=" * 78)
    res = [trial("M0 baseline, no mutation", lambda m: None, expect_red=False)]

    print("  family 1 - delete an invariant")
    for tag, attr in (("M1  delete I1 (order/non-overlap)", "inv1"),
                      ("M2  delete I2 (visibility)", "inv2"),
                      ("M3  delete I3 (fit)", "inv3"),
                      ("M4  delete I4 (containment)", "inv4"),
                      ("M5  delete I6 (northstar)", "inv6"),
                      ("M6  delete I8 (coupled pair)", "inv8"),
                      ("M7  delete I9 (row pitch)", "inv9")):
        res.append(trial(tag, lambda m, a=attr: setattr(m, a, lambda *x: None)))
    # I10 is a MODEL FACT, not a candidate property: it reads no candidate
    # value, so deleting it cannot make any candidate verdict move.  Its
    # adequacy is demonstrated the other way round - M12 corrupts the measured
    # panel client and the gate must go red; M8 shows that redness is
    # ATTRIBUTABLE TO I10 by deleting I10 as well and requiring green again.
    res.append(trial("M8  delete I10 AND corrupt the panel client (must be "
                     "GREEN)",
                     lambda m: (setattr(m, "inv10", lambda *x: None),
                                setattr(m, "PANEL_CLIENT_1", 500)),
                     expect_red=False))

    print("  family 2 - corrupt a measurement or the model")
    res.append(trial("M9  sc() truncates instead of round-half-up",
                     lambda m: setattr(m, "sc", lambda v, f: int(v * f))))
    res.append(trial("M10 corrupt a MEASURED stock column (380->381)",
                     lambda m: m.M_STOCK[m.CHECKBOX].__setitem__("cbox",
                                                                 (381, 396))))
    res.append(trial("M11 corrupt the MEASURED live 2x swatch (886->872)",
                     lambda m: m.M_LIVE_2X[m.CHECKBOX].__setitem__("swatch_l",
                                                                   872)))
    res.append(trial("M12 corrupt the MEASURED panel client (498->500)",
                     lambda m: setattr(m, "PANEL_CLIENT_1", 500)))
    res.append(trial("M13 certify E-STRIPxf as if it were E2",
                     lambda m: [cd.__setitem__("engine", m.eng_scaled_strip)
                                for cd in m.CANDIDATES
                                if cd.get("certified")]))

    print("  family 3 - PERTURB THE CERTIFIED CANDIDATE (R12: the family that")
    print("             would have caught the I4 hole)")
    for tag, fld, d in (("M14 certified plot.R  +6  (the EARLYCHART delta)",
                         "plot_r", 6),
                        ("M15 certified plot.R  +32", "plot_r", 32),
                        ("M16 certified box     -2", "box", -2),
                        ("M17 certified box     -32", "box", -32),
                        ("M18 certified cbox    +8  (wider than declared)",
                         "cbox", 8),
                        ("M19 certified swatch dy +4", "swdy", 4),
                        ("M20 certified row top +200 (overflow)", "top", 200),
                        ("M21 certified row pad -40 (rows collide)",
                         "pad", -40)):
        res.append(trial(tag, perturb(fld, d)))

    print()
    print("    mutations behaving correctly: %d/%d" % (sum(res), len(res)))
    print()
    print("OVERALL: %s" % ("PASS" if all(res) else "FAIL"))
    return 0 if all(res) else 1


if __name__ == "__main__":
    sys.exit(mutate() if "--mutate" in sys.argv else main())
