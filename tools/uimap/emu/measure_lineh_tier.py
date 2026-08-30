#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
measure_lineh_tier.py  --  clear U1: lineH(pt) at the 1.5x and 3x tiers.

WHAT THIS IS.  An instrument, not a model.  Given ONE capture PNG of the Graphs
chart at a known tier, it locates the chart, finds the legend rows, measures the
row pitch, and prints lineH -- or REFUSES and names the single measurement that
would clear the refusal.  It never invents a number and it never reports one it
cannot defend.

WHY.  prove_chart_legend.py carries LINEH_BY_PT = {13: 15, 24: 28, 26: 28}.
Two points do not determine the pt->px rule, so EVERY vertical check (row stack,
column overflow, checkbox pitch) is SKIPPED at f=1.5 and f=3 -- 2914 of the
oracle's 10708 checks are skips and this unknown is the largest single cause.
Both 1.5x and 3x are SHIPPED packages, so a whole class of checks is silent at
two of our three tiers.

USAGE
  python tools\uimap\emu\measure_lineh_tier.py <capture.png> --tier 1.5
  python tools\uimap\emu\measure_lineh_tier.py <capture.png> --tier 3 \
         --fontstyle <the FontStyle.ini that was LIVE for that capture> \
         --chart-origin 1018,664      # from the log's CHARTGEO, optional
         --json out.json
  python tools\uimap\emu\measure_lineh_tier.py --selftest

Exit 0 = a number was measured.  Exit 1 = REFUSED (reasons printed).
Read-only: reads the PNG (+ optionally one ini), writes only the --json file.

---------------------------------------------------------------------------
THE MEASUREMENT, AND WHY IT IS NOT JUST "READ A PITCH"
---------------------------------------------------------------------------
A legend row's advance is        p = (n + s) * lineH + PAD
  n = wrapped line count of that row's label   (>= 1)
  s = group separator blank lines after it     (>= 0, DATA, chart-specific)
  PAD = 4, the row advance's additive term at 0x0076E34B, deliberately
        unpatched, MEASURED unscaled at f=1 and f=2.
So a single pitch is NOT lineH + PAD unless you have proved n = 1 and s = 0,
and the trap is real and expensive: at 2x the plain legend's two rows are TWO
lines each, pitch 60, and "60 - 4" would have written 56 into the oracle as a
MEASUREMENT.  An inference written down as a measurement kills the next seven
candidates.  So three things are required before a number is printed:

  LEG A  (one-line evidence -- the POSITIVE CONTROL, and it is mandatory)
         Per row, count the text INK bands inside that row's span.  Only pairs
         whose FIRST row has exactly one ink line can contribute a pitch.
         At least MIN_ONE_LINE_PAIRS such pairs are required.
  LEG B  (the pitch)  L1 = min(qualifying pitches) - PAD.
  LEG C  (PAD-FREE corroboration)  every pitch differs from that minimum by a
         multiple of lineH, so G = gcd(L1, all nonzero pitch gaps) must EQUAL
         L1.  G does not use PAD at all and does not use the minimum row's line
         count, so it fails loudly on exactly the case LEG B cannot see alone
         (all rows multi-line: 2x live checkbox tops give L1 = 56 while the
         gaps force G = 28, and the instrument refuses instead of shipping 56).
  LEG D  (a different PIXEL FEATURE, when the chart has checkboxes)  the same
         solve run on the checkbox-outline tops.  Grey box outline vs saturated
         colour dash are different failure modes; the band scanner is shared,
         so this corroborates the MODEL, not the SCANNER.  Stated, not hidden.

Legs C and D are corroboration.  Leg A is the load-bearing one: without it the
pitch is uninterpretable, and no amount of agreement between B, C and D repairs
that (two blind instruments agreeing = one).

---------------------------------------------------------------------------
REUSE
---------------------------------------------------------------------------
The chart frame finder and the band-scanning idiom are IMPORTED from
measure_legend_columns.py (the scanner already used for the stock captures) --
find_plot_frame(), is_bg(), sat(), and its colour constants.  There is no
second copy of that logic here; a fix there is a fix here.  What is new is the
auto-locate (the stock scanner is handed a hard-coded search box per capture,
which cannot work at a tier whose chart position is unknown), the pass-2 swatch
rescan, the per-row ink line count, and the solver above.

---------------------------------------------------------------------------
INPUTS THAT ARE NOT MEASURED HERE (so they are printed as INPUTS)
---------------------------------------------------------------------------
  PAD = 4                    0x0076E34B, unpatched at every tier.
  legend TOP = 20            unscaled; only used for the optional swatch-dy
                             (U6) block, and only when --chart-origin is given.
  CERT_STRIP {1.5:178, 2:240, 3:371}   CodePatches.cpp kGraphLegendStrips.
                             Used ONLY to bound the pixel scan window.  If the
                             8-site budget patch declined, the text lands
                             outside that window, the ink bands vanish and the
                             instrument REFUSES -- it cannot silently pass.
  pt per tier                read from a FontStyle .ini.  With --fontstyle it
                             is EVIDENCE (the file that was live).  Without it
                             the repo package file is read and labelled
                             REPO-PACKAGE: that is what SHOULD have been live,
                             not proof of what WAS.
"""

from __future__ import print_function

import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from PIL import Image
except ImportError:                                        # pragma: no cover
    sys.exit("PIL/Pillow required (same dependency as measure_legend_columns.py)")

import measure_legend_columns as MLC                       # THE shared scanner

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CAPTURES = os.path.join(REPO, "_tests", "captures")

# --------------------------------------------------------------- INPUTS ----
PAD = 4                    # row advance additive term, 0x0076E34B (unpatched)
LEGEND_TOP = 20            # legend column top inset, unscaled (U5)

# CodePatches.cpp kGraphLegendStrips -- the CERTIFIED legend strip per tier.
# 1.0 is the stock strip (no patch).  Used only to bound the scan window.
CERT_STRIP = {1.0: 108, 1.5: 178, 2.0: 240, 3.0: 371}

# Repo package FontStyle files, per tier.  GraphInsetLegend is the legend style
# (GUID 0x4a909aaa).  make_fontstyle.py scales it from the 1x 13 -- ROUND
# half-up at an INTEGER factor, FLOOR at a non-integer one (2026-08-06; before
# that it rounded everywhere, and rounding clipped every long label at 1.5x).
# So the shipped sizes are 13 / 19 / 26 / 39, NOT the 13 / 20 / 26 / 39 this
# comment claimed until 2026-08-30.  Nothing here depends on that: the pt is
# READ from the file below, never computed -- which is exactly why --fontstyle
# is not optional.
FONTSTYLE_BY_TIER = {
    1.0: os.path.join(REPO, "tools", "fonts", "FontStyle.default.ini"),
    1.5: os.path.join(REPO, "tools", "packages", "15x", "FontStyle-15x.ini"),
    2.0: os.path.join(REPO, "tools", "fonts", "FontStyle.candidate.ini"),
    3.0: os.path.join(REPO, "tools", "packages", "3x", "FontStyle-3x.ini"),
}
LEGEND_STYLE = "GraphInsetLegend"

MIN_ONE_LINE_PAIRS = 3     # fewer than this and a bad row cannot be outvoted
MIN_ROWS = 3               # 2 rows = 1 pitch = nothing to cross-check
SAT_MIN = 40               # MLC's own swatch saturation threshold
INK_MAX_SUM = 620          # MLC's own "dark ink" test (sum of RGB)


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import scale_round as sc       # noqa: E402


# =========================================================================
#  REFUSALS.  A refusal is a first-class result: it names the ONE measurement
#  that clears it.  Never a silent None.
# =========================================================================
class Refusal(Exception):
    def __init__(self, why, clears):
        Exception.__init__(self, why)
        self.why = why
        self.clears = clears


# =========================================================================
#  AUTO-LOCATE THE CHART
#  The stock scanner is handed a per-capture search box; at a new tier the
#  chart's screen position is unknown, so find it first, then hand the box to
#  MLC.find_plot_frame() so the FRAME itself is measured by the shared code.
# =========================================================================
def locate_plot(im):
    W, H = im.size
    raw = im.tobytes()
    target = bytes(bytearray(MLC.PLOT_FILL))
    stride = 3 * W
    rows = []
    for y in range(H):
        row = raw[y * stride:(y + 1) * stride]
        # .count() is C-level and ignores pixel alignment; on a solid fill the
        # mis-aligned false positives are negligible and only ever RAISE the
        # count, so the threshold below stays conservative.
        if row.count(target) >= 60:
            rows.append(y)
    if not rows:
        raise Refusal(
            "no plot interior found: not one image row holds >=60 px of the "
            "chart plot fill RGB%s" % (MLC.PLOT_FILL,),
            "re-capture with the Graphs chart actually on screen and not "
            "occluded; or pass --search x0,y0,x1,y1 if the chart is present "
            "but this auto-locate is wrong")
    # Longest run of qualifying rows = the plot band.  Gridlines and the data
    # series paint straight across the interior, so a plot row can hold ZERO
    # plot-fill pixels (measured: y 361/369/404 in graphs-stock-garbage.png).
    # Runs are therefore joined across gaps of up to ROW_GAP_TOL.
    # (best and cur must be DISTINCT lists - aliasing them makes every run
    # look like the current one.)
    ROW_GAP_TOL = 8
    best = [rows[0], rows[0]]
    cur = [rows[0], rows[0]]
    for y in rows[1:]:
        if y - cur[1] <= ROW_GAP_TOL:
            cur[1] = y
        else:
            if cur[1] - cur[0] > best[1] - best[0]:
                best = [cur[0], cur[1]]
            cur = [y, y]
    if cur[1] - cur[0] > best[1] - best[0]:
        best = [cur[0], cur[1]]
    y0, y1 = best
    xs0, xs1 = W, 0
    for y in (y0, (y0 + y1) // 2, y1):
        row = raw[y * stride:(y + 1) * stride]
        i = row.find(target)
        while i != -1 and i % 3:
            i = row.find(target, i + 1)
        j = row.rfind(target)
        while j != -1 and j % 3:
            j = row.rfind(target, 0, j + 2)
        if i != -1 and j != -1:
            xs0 = min(xs0, i // 3)
            xs1 = max(xs1, j // 3)
    if xs1 - xs0 < 120 or y1 - y0 < 60:
        raise Refusal(
            "the largest plot-fill region is only %dx%d px - too small to be a "
            "Graphs chart" % (xs1 - xs0, y1 - y0),
            "re-capture with the Graphs window open and the chart unoccluded")
    return (max(0, xs0 - 6), max(0, y0 - 6), min(W, xs1 + 7), min(H, y1 + 7))


def measure_frame(px, search):
    fr = MLC.find_plot_frame(px, search)          # <- the SHARED scanner
    if fr is None or any(v is None for v in fr):
        raise Refusal(
            "measure_legend_columns.find_plot_frame could not resolve all four "
            "plot frame edges in %s (got %s)" % (search, fr),
            "a capture where the 1px plot frame RGB%s is intact - PrintWindow "
            "of the game window, not a scaled/resampled screenshot"
            % (MLC.PLOT_FRAME,))
    return fr


# =========================================================================
#  BAND SCANNING.  Same idiom as measure_legend_columns.analyse(): walk y,
#  count qualifying pixels across an x window, cut contiguous runs into bands.
# =========================================================================
def bands_from(px, x0, x1, y0, y1, test, need):
    out, cur = [], None
    for y in range(y0, y1):
        n = 0
        for x in range(x0, x1):
            if test(px[x, y]):
                n += 1
        if n >= need:
            cur = [y, y] if cur is None else [cur[0], y]
        else:
            if cur:
                out.append(tuple(cur))
                cur = None
    if cur:
        out.append(tuple(cur))
    return out


def band_x_extent(px, x0, x1, a, b, test):
    xs = [x for x in range(x0, x1) for y in range(a, b + 1) if test(px[x, y])]
    return (min(xs), max(xs)) if xs else None


def modal(vals):
    best, n = None, 0
    for v in set(vals):
        c = vals.count(v)
        if c > n:
            best, n = v, c
    return best, n


# =========================================================================
#  THE SOLVER
# =========================================================================
def solve(tops, one_line, label):
    """tops = row tops in capture order.  one_line[i] = True when row i is
    KNOWN to render exactly one text line.  Returns a dict; raises Refusal."""
    if len(tops) < MIN_ROWS:
        raise Refusal(
            "%s: only %d rows found (need >= %d)" % (label, len(tops), MIN_ROWS),
            "capture a chart with at least %d legend rows - Population by Age "
            "has nine" % MIN_ROWS)
    pitches = [tops[i + 1] - tops[i] for i in range(len(tops) - 1)]
    if any(p <= 0 for p in pitches):
        raise Refusal("%s: non-monotonic row tops %s" % (label, tops),
                      "a clean capture; this means the band scanner merged or "
                      "mis-ordered rows")
    qual = [(i, pitches[i]) for i in range(len(pitches)) if one_line[i]]
    if len(qual) < MIN_ONE_LINE_PAIRS:
        raise Refusal(
            "%s: only %d of %d row pairs start on a PROVEN one-line row "
            "(need >= %d).  Line counts per row: %s"
            % (label, len(qual), len(pitches), MIN_ONE_LINE_PAIRS,
               ["1" if o else ">1" for o in one_line]),
            "re-capture the POPULATION BY AGE chart: nine labels of five "
            "glyphs ('1-10'..'81-90') cannot wrap in the certified box at any "
            "tier, so every row is one line by construction")
    pmin = min(p for _, p in qual)
    L1 = pmin - PAD
    if L1 <= 0:
        raise Refusal("%s: minimum one-line pitch %d <= PAD %d"
                      % (label, pmin, PAD),
                      "a capture at the declared tier; this pitch is smaller "
                      "than the stock row padding, so the rows are not rows")
    gaps = [p - pmin for p in pitches if p != pmin]
    bad = [g for g in gaps if g < 0]
    if bad:
        raise Refusal(
            "%s: a pitch is SMALLER than the smallest one-line pitch (%s < %d)"
            % (label, bad, pmin),
            "a clean capture; a shorter pitch than a one-line row is "
            "impossible under p = (n+s)*lineH + PAD")
    G = L1
    for g in gaps:
        if g:
            G = math.gcd(G, g)
    corroborated = (G == L1)
    nonint = [p for p in pitches if (p - PAD) % L1 != 0]
    return {
        "label": label,
        "tops": tops,
        "pitches": pitches,
        "one_line_pairs": [i for i, _ in qual],
        "pmin": pmin,
        "lineH": L1,
        "gcd": G,
        "gcd_leg": ("CORROBORATES" if corroborated else
                    ("STRUCTURAL NULL (all pitches equal - no gaps to take a "
                     "gcd of)" if not [g for g in gaps if g]
                     else "CONTRADICTS")),
        "gaps": sorted(set(g for g in gaps if g)),
        "nonintegral": nonint,
        "quotients": [(p - PAD) / float(L1) for p in pitches],
    }


# =========================================================================
#  ONE CAPTURE
# =========================================================================
def analyse(path, tier, chart_origin=None, search=None):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    notes, warns = [], []

    box = search or locate_plot(im)
    fl, ft, fr, fb = measure_frame(px, box)
    notes.append("plot frame px ABS  L=%d T=%d R=%d B=%d   [MEASURED via "
                 "measure_legend_columns.find_plot_frame]" % (fl, ft, fr, fb))

    strip = CERT_STRIP.get(round(tier, 2))
    if strip is None:
        strip = sc(108, tier)
        warns.append("tier %.2f has no CERTIFIED strip in CodePatches.cpp; the "
                     "scan window falls back to sc(108,f)=%d" % (tier, strip))
    # ---- the scan window, bounded TWO independent ways --------------------
    # (1) the MODEL bound: the legend strip is the certified strip plus the
    #     sc(2,f) the plot border clears itself by (CodePatches
    #     GraphLegendPlotRightMargin), so the chart's right edge is at most
    #     frame_right + 1 + strip + sc(2,f), + a little slack.
    # (2) the PIXEL bound: right of the chart there is no chart fill at all.
    #     Whichever is TIGHTER wins.  A window that runs past the chart is how
    #     the city behind it gets scanned as legend, and that is what turns
    #     nine swatch rows into five merged bands.
    ry0 = ft
    ry1 = min(H, fb + 1 + sc(20, tier))               # chart bottom margin
    model_x1 = fr + 1 + strip + sc(2, tier) + sc(8, tier)
    pix_x1 = fr + 2
    x = fr + 2
    while x < W:
        if not any(px[x, y] == MLC.OUTER_FILL for y in range(ry0, ry1)):
            break
        x += 1
    pix_x1 = x
    gx0 = fr + 2
    gx1 = min(W, model_x1, max(pix_x1, gx0 + 8))
    notes.append("legend scan window x %d..%d  y %d..%d  (model bound %d, "
                 "pixel bound %d)" % (gx0, gx1, ry0, ry1, model_x1, pix_x1))

    # ---- swatches, pass 1: saturated dashes (MLC's own test) --------------
    sat_bands = bands_from(px, gx0, gx1, ry0, ry1,
                           lambda p: MLC.sat(p) > SAT_MIN, 3)
    if not sat_bands:
        raise Refusal(
            "no saturated swatch bands in the legend gutter x %d..%d" % (gx0, gx1),
            "a capture of a chart that HAS a legend (the no-legend chart "
            "variant exists - EARLYCHART logs plot right 974 for it), at the "
            "declared tier, with the 8-site legend budget patch armed (log: "
            "'CodePatches: graph legend budget x%.2f (8 of 8 sites)')" % tier)
    exts = []
    for (a, b) in sat_bands:
        e = band_x_extent(px, gx0, gx1, a, b, lambda p: MLC.sat(p) > SAT_MIN)
        if e:
            exts.append(e)
    ext, nmode = modal(exts)
    if nmode < 2:
        raise Refusal(
            "the saturated bands do not line up into a column (x extents %s)"
            % sorted(set(exts)),
            "a capture where the legend swatches share one x column; scattered "
            "extents mean the scan window caught something that is not a legend")
    swx0, swx1 = ext

    # ---- swatches, pass 2: rescan that exact column for ANY non-background
    # A BLACK swatch has zero saturation - the stock 1x Garbage capture loses
    # 'Incinerated' for exactly this reason (8 bands for 9 rows in
    # measure_legend_columns).  A missing row turns two pitches into one and
    # would break the PAD model, so it must be recovered, not tolerated.
    sw_bands = bands_from(px, swx0, swx1 + 1, ry0, ry1,
                          lambda p: not MLC.is_bg(p),
                          max(3, (swx1 - swx0 + 1) // 2))
    recovered = len(sw_bands) - len(sat_bands)
    if recovered > 0:
        notes.append("swatch pass 2 recovered %d row(s) whose swatch has zero "
                     "saturation (black/grey) - pass 1 saw %d, pass 2 sees %d"
                     % (recovered, len(sat_bands), len(sw_bands)))
    sw_tops = [a for a, _ in sw_bands]
    sw_h, _ = modal([b - a + 1 for a, b in sw_bands])

    # ---- checkbox column (cbox charts only) ------------------------------
    cb_tops, cb_x = None, None
    minrun = max(6, sc(14, tier))
    xs = []
    for x in range(gx0, swx0):
        run = best = 0
        for y in range(ry0, ry1):
            if not MLC.is_bg(px[x, y]):
                run += 1
                best = max(best, run)
            else:
                run = 0
        if best >= minrun:
            xs.append(x)
    if xs:
        cb_x = (min(xs), max(xs))
        cb_bands = bands_from(px, cb_x[0], cb_x[1] + 1, ry0, ry1,
                              lambda p: not MLC.is_bg(p),
                              int((cb_x[1] - cb_x[0]) * 0.6))
        cb_tops = [a for a, _ in cb_bands]
        cb_h, _ = modal([b - a + 1 for a, b in cb_bands])
    else:
        cb_h = None
        notes.append("no checkbox column left of the swatch: PLAIN chart kind. "
                     "LEG D (checkbox pitch) is a STRUCTURAL null here - this "
                     "chart has no checkboxes to measure, which is not the "
                     "same as measuring and finding none.")

    kind = "cbox" if cb_tops else "plain"

    # ---- text ink, per row ------------------------------------------------
    # box width is derived from the certified strip, not fitted to this capture.
    consumed = (sc(16, tier) if kind == "cbox" else 0) + sc(2, tier) \
        + sc(10, tier) + sc(4, tier) + sc(4, tier)
    if round(tier, 2) == 1.0:
        consumed = (16 if kind == "cbox" else 0) + 2 + 10 + 4 + 4
    box_w = strip - consumed
    tx0 = swx1 + 1
    tx1 = min(W, tx0 + sc(4, tier) + box_w + sc(6, tier))
    ink = lambda p: (not MLC.is_bg(p)) and sum(p) < INK_MAX_SUM
    raw_ink = bands_from(px, tx0, tx1, ry0, ry1, ink, 1)
    # merge bands separated by <=1px and drop specks (a comma-only band)
    merged = []
    for (a, b) in raw_ink:
        if merged and a - merged[-1][1] <= 1:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    if not merged:
        raise Refusal(
            "no legend TEXT ink in x %d..%d (the certified box for tier %.2f, "
            "kind %s, is %d px wide)" % (tx0, tx1, tier, kind, box_w),
            "a capture with the legend budget patch ARMED - if it declined, "
            "the text is laid out at the STOCK 72/88 px box and lands outside "
            "this window.  Check the log for 'graph legend budget x%.2f "
            "(8 of 8 sites)'." % tier)
    hmode, _ = modal([b - a + 1 for a, b in merged])
    lines = [(a, b) for (a, b) in merged if (b - a + 1) >= max(2, 0.35 * hmode)]

    # ---- assign ink lines to rows ----------------------------------------
    skeleton = cb_tops if cb_tops else sw_tops
    skel_name = "checkbox" if cb_tops else "swatch"
    if len(skeleton) < MIN_ROWS:
        raise Refusal(
            "only %d legend rows detected from the %s column"
            % (len(skeleton), skel_name),
            "a chart with >= %d rows: Population by Age (nine) or Garbage "
            "(nine)" % MIN_ROWS)
    spans = []
    for i, t in enumerate(skeleton):
        end = skeleton[i + 1] if i + 1 < len(skeleton) else ry1
        spans.append((t, end))
    counts = []
    for (a, b) in spans:
        counts.append(sum(1 for (u, v) in lines if a <= (u + v) // 2 < b))
    one_line = [c == 1 for c in counts]
    clean = all(c == 1 for c in counts)

    # ---- solve, on both features -----------------------------------------
    res_sw = None
    sw_one = one_line if not cb_tops else None
    if cb_tops:
        # map swatch bands onto skeleton rows so the swatch leg uses the SAME
        # per-row line counts; a swatch with no matching row is a detection bug.
        sw_one = []
        for i in range(len(sw_tops) - 1):
            j = None
            for k, (a, b) in enumerate(spans):
                if a - sc(6, tier) <= sw_tops[i] < b:
                    j = k
                    break
            sw_one.append(one_line[j] if j is not None else False)
        sw_one.append(False)
    res_sw = solve(sw_tops, sw_one, "swatch-top pitch")
    res_cb = solve(cb_tops, one_line, "checkbox-top pitch") if cb_tops else None

    if res_cb and res_cb["lineH"] != res_sw["lineH"]:
        raise Refusal(
            "the two pixel features DISAGREE: swatch-top pitch gives lineH=%d, "
            "checkbox-top pitch gives lineH=%d"
            % (res_sw["lineH"], res_cb["lineH"]),
            "a clean capture; a disagreement here is a scanner fault, and "
            "either number alone would be a guess")
    if res_sw["gcd_leg"] == "CONTRADICTS":
        raise Refusal(
            "LEG C (PAD-free) CONTRADICTS the pitch: min one-line pitch - PAD "
            "= %d, but gcd of the pitch gaps = %d.  The smallest row is "
            "therefore NOT one line and %d would be %.1f lines."
            % (res_sw["lineH"], res_sw["gcd"], res_sw["lineH"],
               res_sw["lineH"] / float(res_sw["gcd"])),
            "re-capture the POPULATION BY AGE chart, whose nine 5-glyph labels "
            "cannot wrap at any tier")
    if res_sw["nonintegral"]:
        raise Refusal(
            "pitches %s are not (n+s)*%d + %d for integer n+s - the row model "
            "does not hold on this capture"
            % (res_sw["nonintegral"], res_sw["lineH"], PAD),
            "a clean capture at the declared tier; a non-integral pitch means "
            "a missed or merged row band")

    lineH = res_sw["lineH"]

    # ---- tier consistency: is this capture ACTUALLY at the declared tier? --
    tier_obs = []
    exp_sw_w = (sc(10, tier) - 2) if round(tier, 2) != 1.0 else 8
    got_sw_w = swx1 - swx0 + 1
    tier_obs.append(("swatch core width", got_sw_w, exp_sw_w,
                     "unpatched swatch stays 8 at every tier"))
    if cb_h is not None:
        tier_obs.append(("checkbox band height", cb_h, sc(16, tier),
                         "unpatched checkbox stays 16"))
    mism = [t for t in tier_obs if t[1] != t[2]]
    if mism and len(mism) == len(tier_obs):
        warns.append(
            "TIER CHECK: every scaled-geometry probe disagrees with tier %.2f "
            "(%s).  Either the capture is at another tier, or the legend "
            "budget patch declined.  lineH below is still the measured pitch, "
            "but the pt it is filed under may be wrong."
            % (tier, "; ".join("%s %d != %d" % (n, g, e)
                               for n, g, e, _ in mism)))

    # ---- optional U6 block: swatch dy inside the row ----------------------
    u6 = None
    if chart_origin:
        oy = chart_origin[1]
        dy = sw_tops[0] - oy - LEGEND_TOP
        u6 = {"swatch_dy_measured_core": dy,
              "sc(3,f)": sc(3, tier),
              "round(3*lineH/15)": int(math.floor(3 * lineH / 15.0 + 0.5)),
              "note": "core top is ~1px inside the stored rect (see "
                      "measure_legend_columns SECTION 2), so compare with "
                      "+/-1; TOP=20 unscaled is an INPUT (U5)."}

    return {
        "path": path, "size": (W, H), "tier": tier, "kind": kind,
        "frame_abs": (fl, ft, fr, fb),
        "swatch_x": (swx0, swx1), "swatch_h": sw_h,
        "cbox_x": cb_x, "cbox_h": cb_h,
        "text_x": (tx0, tx1), "box_w": box_w, "strip": strip,
        "rows": len(skeleton), "skeleton": skel_name,
        "ink_lines_per_row": counts, "clean_one_line": clean,
        "swatch": res_sw, "checkbox": res_cb,
        "lineH": lineH, "u6": u6, "notes": notes, "warnings": warns,
    }


# =========================================================================
#  pt ATTRIBUTION
# =========================================================================
def read_legend_pt(path):
    if not os.path.isfile(path):
        return None, "MISSING: " + path
    rx = re.compile(r'^\s*%s\s*=\s*"[^"]*"\s*,\s*"(\d+)"' % LEGEND_STYLE)
    with open(path, "r", errors="replace") as f:
        for ln in f:
            m = rx.match(ln)
            if m:
                return int(m.group(1)), path
    return None, "no %s entry in %s" % (LEGEND_STYLE, path)


# =========================================================================
#  REPORT
# =========================================================================
def hr(c="="):
    print(c * 78)


def report(r, pt, pt_src, pt_evidence):
    hr()
    print("measure_lineh_tier  --  %s" % os.path.basename(r["path"]))
    hr()
    print("  capture        %dx%d   tier %.2f   chart kind %s"
          % (r["size"][0], r["size"][1], r["tier"], r["kind"]))
    for n in r["notes"]:
        print("  note           %s" % n)
    print("  legend strip   %d (CERTIFIED input) -> text box %d px, scanned "
          "x %d..%d" % (r["strip"], r["box_w"], r["text_x"][0], r["text_x"][1]))
    print("  swatch column  x %d..%d (w %d)  band height %d"
          % (r["swatch_x"][0], r["swatch_x"][1],
             r["swatch_x"][1] - r["swatch_x"][0] + 1, r["swatch_h"]))
    if r["cbox_x"]:
        print("  cbox column    x %d..%d (w %d)  band height %s"
              % (r["cbox_x"][0], r["cbox_x"][1],
                 r["cbox_x"][1] - r["cbox_x"][0] + 1, r["cbox_h"]))
    print()
    print("  LEG A  one-line evidence (POSITIVE CONTROL, mandatory)")
    print("         %d rows from the %s column; text ink lines per row %s"
          % (r["rows"], r["skeleton"], r["ink_lines_per_row"]))
    if r["clean_one_line"]:
        print("         CLEAN: every row renders exactly ONE line.  This is "
              "the capture the procedure asks for.")
    else:
        print("         CONDITIONAL: %d of %d rows wrap.  Only pairs starting "
              "on a one-line row were used (%s); the number below is still "
              "measured, but a clean capture is stronger."
              % (sum(1 for c in r["ink_lines_per_row"] if c != 1), r["rows"],
                 r["swatch"]["one_line_pairs"]))
    print()
    for leg, key in (("LEG B/C  swatch-top", "swatch"),
                     ("LEG D    checkbox-top", "checkbox")):
        s = r[key]
        if s is None:
            print("  %s  STRUCTURAL NULL - this chart kind has no "
                  "checkbox column (not 'measured and absent')" % leg)
            continue
        print("  %s pitch" % leg)
        print("         tops     %s" % s["tops"])
        print("         pitches  %s" % s["pitches"])
        print("         min one-line pitch %d  -  PAD %d  =  lineH %d"
              % (s["pmin"], PAD, s["lineH"]))
        print("         PAD-free gcd of gaps %s -> %d   %s"
              % (s["gaps"] or "(none)", s["gcd"], s["gcd_leg"]))
        print("         pitch/lineH quotients %s"
              % ["%.2f" % q for q in s["quotients"]])
    for w in r["warnings"]:
        print()
        print("  WARNING  %s" % w)
    print()
    hr("-")
    print("  RESULT   lineH = %d px   at %s pt   (tier %.2f)"
          % (r["lineH"], pt if pt else "?", r["tier"]))
    print("  UNCERTAINTY  +/-0 px on the pitch: it is a DIFFERENCE of two tops "
          "measured the same way, so the swatch core's ~1px inset cancels.")
    print("               Every contributing pitch was equal; a 1px "
          "anti-aliasing shift on any one top would have shown up as an "
          "unequal minimum and been reported, not absorbed.")
    print("  PAD = %d is an INPUT (0x0076E34B, unpatched), not measured here; "
          "LEG C is the leg that does not depend on it." % PAD)
    print("  pt SOURCE    %s   [%s]" % (pt_src, pt_evidence))
    if pt_evidence == "REPO-PACKAGE":
        print("               ^ this is what SHOULD have been live, not proof "
              "of what WAS.  Pass --fontstyle <the live FontStyle.ini> to make "
              "it evidence, or confirm the log line 'AutoScale: ... -> tier "
              "%.2f'." % r["tier"])
    if r["u6"]:
        print()
        print("  U6 (swatch vertical rule), from --chart-origin:")
        for k, v in r["u6"].items():
            print("     %-22s %s" % (k, v))
    print()
    if pt:
        print("  THE ORACLE EDIT (prove_chart_legend.py, ONE line):")
        print("     LINEH_BY_PT[%d] = %d      # MEASURED %s, tier %.2f"
              % (pt, r["lineH"], os.path.basename(r["path"]), r["tier"]))
    hr()


# =========================================================================
#  SELF-TEST - the instrument's own positive AND negative controls
# =========================================================================
def selftest():
    """One POSITIVE control (a known lineH must come back out) and two
    NEGATIVE controls (the instrument must go RED where a naive pitch reader
    would print a wrong number).  A gate that cannot go red is not a gate."""
    cases = [
        ("POSITIVE  1x Garbage -> lineH 15",
         os.path.join(CAPTURES, "graphs-stock-garbage.png"), 1.0, 15),
        ("NEGATIVE  1x plain (2 rows) -> REFUSE",
         os.path.join(CAPTURES, "graphs-stock-ref.png"), 1.0, None),
        ("NEGATIVE  2x plain (2 rows, BOTH wrapped: a naive reader prints "
         "60-4=56) -> REFUSE",
         os.path.join(CAPTURES, "graphs-ours-2x.png"), 2.0, None),
    ]
    fails = 0
    for name, path, tier, want in cases:
        print("-" * 78)
        print(name)
        if not os.path.isfile(path):
            print("   SKIP - capture missing: %s" % path)
            print("   (a SKIP is not a pass; this control did not run)")
            fails += 1
            continue
        try:
            r = analyse(path, tier)
            got = r["lineH"]
            if want is None:
                print("   FAIL - expected a REFUSAL, got lineH = %d" % got)
                fails += 1
            elif got != want:
                print("   FAIL - expected lineH %d, got %d" % (want, got))
                fails += 1
            else:
                print("   PASS - lineH = %d (rows %s, ink/row %s)"
                      % (got, r["rows"], r["ink_lines_per_row"]))
        except Refusal as e:
            if want is None:
                print("   PASS - REFUSED as required: %s" % e.why)
            else:
                print("   FAIL - refused but should have measured %d: %s"
                      % (want, e.why))
                fails += 1
    # ---- control 4: the 56 trap, on the solver directly -------------------
    # The three captures above all refuse for structural reasons (too few
    # rows), so none of them exercises LEG C.  This one does, from MEASURED
    # data that needs no PNG: the 2x LIVE checkbox tops logged by LEGENDCBOX
    # (prove_chart_legend.M_LIVE_2X), where every row is TWO lines.  A naive
    # reader takes min pitch 60, subtracts PAD and prints 56.  LEG C must
    # contradict it, because the 88-px pitch forces a gap of 28.
    print("-" * 78)
    print("NEGATIVE  2x live checkbox tops, all rows 2 lines -> LEG C must "
          "CONTRADICT the naive 56")
    tops = [20, 80, 196, 256, 344, 404, 464, 524, 612]
    s = solve(tops, [True] * len(tops), "2x live cbox tops (naive one_line)")
    if s["lineH"] == 56 and s["gcd"] == 28 and s["gcd_leg"] == "CONTRADICTS":
        print("   PASS - naive lineH would be 56; gcd of gaps = 28 -> "
              "CONTRADICTS, so analyse() refuses instead of shipping 56")
    else:
        print("   FAIL - lineH %d, gcd %d, leg %s"
              % (s["lineH"], s["gcd"], s["gcd_leg"]))
        fails += 1

    print("-" * 78)
    print("selftest: %d failure(s)" % fails)
    print("  1 positive control (a known lineH comes back out), 3 negative "
          "controls (2 structural, 1 on the wrap trap).")
    return 1 if fails else 0


# =========================================================================
def main():
    ap = argparse.ArgumentParser(
        description="Measure the Graphs legend lineH at a shipped tier.")
    ap.add_argument("capture", nargs="?", help="capture PNG")
    ap.add_argument("--tier", type=float, help="1.5 / 2 / 3 - the ACTIVE tier")
    ap.add_argument("--fontstyle", help="the FontStyle.ini that was LIVE for "
                                        "this capture (makes pt evidence)")
    ap.add_argument("--pt", type=int, help="assert the legend point size "
                                           "(labelled OPERATOR-ASSERTED)")
    ap.add_argument("--chart-origin", help="X,Y of the chart window from the "
                                           "log's CHARTGEO - enables the U6 block")
    ap.add_argument("--search", help="x0,y0,x1,y1 override for the chart hunt")
    ap.add_argument("--json", help="write the full result as JSON")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.capture or a.tier is None:
        ap.error("need <capture.png> and --tier (or --selftest)")
    if not os.path.isfile(a.capture):
        print("REFUSED: no such capture %s" % a.capture)
        return 1

    origin = None
    if a.chart_origin:
        origin = tuple(int(v) for v in a.chart_origin.split(","))
    search = None
    if a.search:
        search = tuple(int(v) for v in a.search.split(","))

    if a.pt:
        pt, pt_src, ev = a.pt, "--pt %d" % a.pt, "OPERATOR-ASSERTED"
    elif a.fontstyle:
        pt, pt_src = read_legend_pt(a.fontstyle)
        ev = "LIVE FILE (evidence)"
    else:
        pt, pt_src = read_legend_pt(
            FONTSTYLE_BY_TIER.get(round(a.tier, 2), ""))
        ev = "REPO-PACKAGE"

    try:
        r = analyse(a.capture, a.tier, origin, search)
    except Refusal as e:
        hr()
        print("REFUSED - no lineH reported.")
        hr()
        print("  WHY     %s" % e.why)
        print("  CLEARS  %s" % e.clears)
        hr()
        return 1

    report(r, pt, pt_src, ev)
    if a.json:
        out = dict(r)
        out["pt"] = pt
        out["pt_source"] = pt_src
        out["pt_evidence"] = ev
        with open(a.json, "w") as f:
            json.dump(out, f, indent=2)
        print("wrote %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
