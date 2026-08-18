# -*- coding: utf-8 -*-
r"""attack_15x.py - RED TEAM against prove_chart_legend.py, TIER 1.5 LENS ONLY.

Read-only adversary.  Imports the oracle and its text model, runs them, and
tries to make the gate lie at f=1.5.  Writes nothing, deploys nothing.

  python attack_15x.py
"""
import importlib
import io
import math
import contextlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu_text_extent as TX
import prove_chart_legend as P

SEP = "=" * 78


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import scale_round as sc_up     # noqa: E402


def sc_trunc(v, f):
    return int(v * f)


def sc_down(v, f):
    return int(math.ceil(v * f - 0.5))


def sc_bank(v, f):
    return int(round(v * f))          # banker's rounding


# ---------------------------------------------------------------------------
# A1  Is the rounding law actually EXERCISED at f=1.5?
# ---------------------------------------------------------------------------
def a1():
    print(SEP)
    print("A1  Is I7's f=1.5 content real?  (the file claims task #75 is")
    print("    'exercised explicitly' at f=1.5)")
    print(SEP)
    consts = [("RM", P.RM), ("TXW0", P.TXW0), ("CBW0", P.CBW0), ("SWW", P.SWW),
              ("SWH", P.SWH), ("SWG", P.SWG), ("CBG", P.CBG),
              ("STRIP", P.STRIP), ("PLOTG", P.PLOTG), ("TOP", P.TOP),
              ("PAD", P.PAD), ("SWDY", P.SWDY),
              ("PLOTG+STRIP", P.PLOTG + P.STRIP), ("W1", P.W1), ("H1", P.H1)]
    print("  every constant in the model, and whether f=1.5 lands on a half:")
    halves = []
    for nm, v in consts:
        half = (v * 3) % 2 == 1          # v*1.5 has a .5 part iff v is odd
        print("    %-12s = %-5d  v*1.5 = %-7.1f  %s"
              % (nm, v, v * 1.5, "HALF-PIXEL" if half else "exact"))
        if half:
            halves.append(nm)
    print("  -> constants that actually round at f=1.5: %s"
          % (", ".join(halves) if halves else "NONE"))

    print()
    print("  I7's SUBSTANTIVE checks re-evaluated under four rounding laws:")
    laws = [("round-half-up (shipped)", sc_up), ("truncate", sc_trunc),
            ("round-half-down", sc_down), ("banker's", sc_bank)]
    rows = []
    for lname, s in laws:
        f = 1.5
        cb = s(P.CBW0, f) + s(P.CBG, f) + s(P.SWW, f) + s(P.SWG, f) + \
            s(P.TXW0 - P.CBW0, f) + s(P.RM, f)
        pl = s(P.CBG, f) + s(P.SWW, f) + s(P.SWG, f) + s(P.TXW0, f) + s(P.RM, f)
        rows.append((lname, cb, pl, s(P.STRIP, f),
                     s(P.PLOTG, f) + s(P.STRIP, f), s(P.PLOTG + P.STRIP, f),
                     s(P.W1, f)))
    print("    %-24s %6s %6s %6s %8s %8s %6s"
          % ("law", "cb-sum", "pl-sum", "sc(108)", "2+108", "sc(110)", "winW"))
    for r in rows:
        print("    %-24s %6d %6d %6d %8d %8d %6d" % r)
    same = len(set(r[1:] for r in rows)) == 1
    print("  -> all four laws agree: %s" % same)
    print("     I7's f=1.5 geometry checks are ROUNDING-INSENSITIVE.  The only")
    print("     f=1.5 checks that can move are the sc(v,f)==floor(v*f+.5)")
    print("     self-tests, which test the function against its own formula.")
    return same


# ---------------------------------------------------------------------------
# A2  What does the oracle ACTUALLY check about E2 at f=1.5?
# ---------------------------------------------------------------------------
def a2():
    print()
    print(SEP)
    print("A2  E2-FONTBOX at f=1.5: what is checked, what is skipped")
    print(SEP)
    m = importlib.import_module("prove_chart_legend")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.main()
    per = {}
    for inv, cand, hyp, f, kind, name, st, det in m.L.rows:
        if cand != "E2-FONTBOX" or f != 1.5:
            continue
        per.setdefault(inv, {"PASS": 0, "FAIL": 0, "SKIP": 0})[st] += 1
    print("    %-4s %7s %7s %7s" % ("inv", "pass", "fail", "skip"))
    tot = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for inv in sorted(per):
        c = per[inv]
        for k in tot:
            tot[k] += c[k]
        print("    %-4s %7d %7d %7d" % (inv, c["PASS"], c["FAIL"], c["SKIP"]))
    print("    %-4s %7d %7d %7d" % ("TOT", tot["PASS"], tot["FAIL"], tot["SKIP"]))
    print()
    print("  Which f=1.5 PASSES are construction-forced (tautologies) for a")
    print("  strip-walk candidate like E2?  _strip_walk() lays the columns out")
    print("  left-to-right with exactly the gaps I1/I8 then demand back:")
    print("    I1 gaps, I8 gaps/margin/dy/height/squareness ... FORCED")
    print("    I3 fit ... FORCED (the box is DEFINED as ceil(max need))")
    print("    I4 text.R<=W-sc(4,f) ... FORCED (strip closes on sc(RM,f))")
    print("    I6 NORTHSTAR w>=sc(w1,f) ... FORCED (box = max(sc(72,f), ...))")
    print("    I2, I4 column-bottom, I8 rowTop ... SKIPPED (U1)")
    print("  -> the only non-forced f=1.5 checks are I6's edge-monotonicity")
    print("     and I4's plot_r>0, both of which only bite on absurd inputs.")
    return tot


# ---------------------------------------------------------------------------
# A3  The one thing that IS 1.5-specific: 13*1.5 = 19.5 rounds UP
# ---------------------------------------------------------------------------
def a3():
    print()
    print(SEP)
    print("A3  THE 1.5x HALF-PIXEL THAT MATTERS: the FONT, not the geometry")
    print(SEP)
    print("    %-6s %-8s %-8s %-9s %-9s %s"
          % ("tier", "raw pt", "sqz pt", "raw/1x", "geom f", "raw/sqz spread"))
    for f in P.TIERS:
        raw, sqz = P.PT_RAW[f], P.PT_SQUEEZED[f]
        print("    %-6s %-8d %-8d %-9.4f %-9.2f %.4f%s"
              % ("%gx" % f, raw, sqz, raw / 13.0, f, raw / float(sqz),
                 "   <-- 13*1.5=19.5 rounds UP" if f == 1.5 else ""))
    print("  At f=1.5 ONLY, the raw font grows 1.5385x while the window grows")
    print("  1.5x, and the raw/squeezed spread is 11.1%% vs 8.3%% everywhere")
    print("  else.  Had 19.5 rounded DOWN the spread would be 19/18 = 5.6%%.")

    print()
    print("  Consequence - the ADMISSIBLE BOX BAND intersection per tier")
    print("  (a box must satisfy I3 under BOTH hypotheses to be certifiable):")
    print("    %-6s %-14s %-14s %-14s %-8s %s"
          % ("tier", "SQZ band", "RAW band", "intersection", "width", "margin px"))
    for f in P.TIERS:
        cells = {}
        for tag, pm in (("SQZ", P.PT_SQUEEZED), ("RAW", P.PT_RAW)):
            pt = pm[f]
            lo = max(TX.advance_width(l, pt) for l in P.LABELS[P.CHECKBOX]
                     if l not in P.STOCK_WRAPS)
            hi = min(TX.advance_width(l, pt) for l in P.LABELS[P.CHECKBOX]
                     if l in P.STOCK_WRAPS)
            cells[tag] = (lo, hi)
        lo = max(cells["SQZ"][0], cells["RAW"][0])
        hi = min(cells["SQZ"][1], cells["RAW"][1])
        ilo, ihi = int(math.ceil(lo)), int(math.ceil(hi)) - 1
        margin = hi - lo
        print("    %-6s %-14s %-14s %-14s %-8s %.2f%s"
              % ("%gx" % f,
                 "%3d..%3d" % (math.ceil(cells["SQZ"][0]),
                               math.ceil(cells["SQZ"][1]) - 1),
                 "%3d..%3d" % (math.ceil(cells["RAW"][0]),
                               math.ceil(cells["RAW"][1]) - 1),
                 "%3d..%3d" % (ilo, ihi) if ihi >= ilo else "EMPTY",
                 (ihi - ilo + 1) if ihi >= ilo else 0, margin,
                 "   <-- SINGLE VALUE" if ihi == ilo else ""))
    print("  TX.TOL = %.1f px is the text model's own declared residual." % TX.TOL)
    print("  At f=1.5 the two-sided margin is SMALLER than that residual, so")
    print("  which integer box widths are admissible at 1.5x is NOT DECIDABLE")
    print("  on the evidence in the repo - yet the gate prints PASS for E2.")


# ---------------------------------------------------------------------------
# A4  Perturb the text model INSIDE its own stated residual, at f=1.5
# ---------------------------------------------------------------------------
def a4():
    print()
    print(SEP)
    print("A4  Perturb the text model inside its OWN +-%.1f px residual" % TX.TOL)
    print("    (the space advance is the file's declared weakest metric:")
    print("     5.2 px at 26 pt, back-solved from a 4.5..6.4 spread)")
    print(SEP)
    base = TX.ADV26[' ']
    print("    %-7s %-8s %-8s %-8s %-8s %s"
          % ("space", "TG@20", "WtE@18", "band 1.5x", "band 2x", "1.5x verdict"))
    for spc in (4.5, 5.0, 5.2, 5.8, 6.4):
        TX.ADV26[' '] = spc
        tg20 = TX.advance_width("Total Garbage", 20)
        wte18 = TX.advance_width("Waste to Energy", 18)
        lo15 = max(TX.advance_width(l, pt) for pt in (18, 20)
                   for l in P.LABELS[P.CHECKBOX] if l not in P.STOCK_WRAPS)
        hi15 = min(TX.advance_width(l, pt) for pt in (18, 20)
                   for l in P.LABELS[P.CHECKBOX] if l in P.STOCK_WRAPS)
        lo2 = max(TX.advance_width(l, pt) for pt in (24, 26)
                  for l in P.LABELS[P.CHECKBOX] if l not in P.STOCK_WRAPS)
        hi2 = min(TX.advance_width(l, pt) for pt in (24, 26)
                  for l in P.LABELS[P.CHECKBOX] if l in P.STOCK_WRAPS)
        n15 = int(math.ceil(hi15)) - 1 - int(math.ceil(lo15)) + 1
        n2 = int(math.ceil(hi2)) - 1 - int(math.ceil(lo2)) + 1
        print("    %-7.1f %-8.1f %-8.1f %-8s %-8s %s"
              % (spc, tg20, wte18,
                 "%d..%d" % (math.ceil(lo15), math.ceil(hi15) - 1),
                 "%d..%d" % (math.ceil(lo2), math.ceil(hi2) - 1),
                 "%d admissible%s" % (max(n15, 0),
                                      "  <-- NO LEGAL BOX" if n15 <= 0 else "")))
    TX.ADV26[' '] = base
    print("  Within the model's own space-advance spread the 1.5x admissible")
    print("  set goes EMPTY while the 2x set stays populated.  The oracle")
    print("  never notices, because no invariant enforces the UPPER band edge")
    print("  (wrapping LESS than stock is unchecked).")


# ---------------------------------------------------------------------------
# A5  The missing invariant: checkbox-vs-checkbox vertical collision
# ---------------------------------------------------------------------------
def a5():
    print()
    print(SEP)
    print("A5  MISSING INVARIANT: consecutive checkbox CHILD WINDOWS may")
    print("    overlap each other vertically.  I2 only tests swatch-vs-cbox")
    print("    and text-vs-cbox, which are X-disjoint by construction.")
    print(SEP)
    print("    cbox is SQUARE with side sc(16,f); a one-line row's pitch is")
    print("    lineH(pt) + PAD, PAD frozen at 4.  No overlap iff")
    print("        lineH(pt) >= sc(16,f) - 4")
    print()
    print("    %-6s %-8s %-10s %-12s %-10s %s"
          % ("tier", "sc(16,f)", "need lineH", "lineH known?", "measured",
             "slack"))
    for f in P.TIERS:
        need = P.sc(16, f) - P.PAD
        for tag, pm in (("SQZ", P.PT_SQUEEZED), ("RAW", P.PT_RAW)):
            pt = pm[f]
            lh = P.LINEH_BY_PT.get(pt)
            print("      %-4s %-8d %-10d %-12s %-10s %s"
                  % ("%gx/%s" % (f, tag), P.sc(16, f), need,
                     "yes" if lh else "NO (U1)",
                     ("%d @%dpt" % (lh, pt)) if lh else "-@%dpt" % pt,
                     ("%+d" % (lh - need)) if lh else "UNKNOWN"))
    print("    At f=2 the slack is EXACTLY ZERO (32 px box, 32 px pitch) and")
    print("    no invariant looks at it.  At f=1.5 and f=3 lineH is unknown,")
    print("    so the collision is undecidable at both SHIPPED tiers.")
    print("    Required ratio lineH/pt: 1.5x/SQZ %.3f, 3x/SQZ %.3f."
          % ((P.sc(16, 1.5) - 4) / 18.0, (P.sc(16, 3.0) - 4) / 36.0))
    print("    Measured ratios: 15/13=%.3f, 28/24=%.3f, 28/26=%.3f."
          % (15 / 13., 28 / 24., 28 / 26.))
    print("    -> 3x/SQZ needs 1.222, ABOVE every measured ratio.")


# ---------------------------------------------------------------------------
# A6  The vertical SKIP at 1.5x - sensitivity sweep over the unknown lineH
# ---------------------------------------------------------------------------
def a6():
    print()
    print(SEP)
    print("A6  What the 1.5x vertical SKIP is hiding: sweep lineH")
    print(SEP)
    for tag, pt in (("SQZ", 18), ("RAW", 20)):
        cols = P.eng_font_box(1.5, P.CHECKBOX)
        box = cols["text"][1] - cols["text"][0]
        nlines = [len(TX.wrap(l, pt, box)) for l in P.LABELS[P.CHECKBOX]]
        S = sum(nlines) + 2                       # + 2 group separators
        H = P.win_h(1.5)
        print("    1.5x/%s  pt=%d  box=%d  lines=%s  sum+groups=%d  winH=%d"
              % (tag, pt, box, nlines, S, H))
        ok = []
        for lh in range(15, 32):
            total = 9 * P.PAD + lh * S
            ok.append((lh, total, total <= H))
        good = [lh for lh, t, o in ok if o]
        print("      totalH = 36 + %d*lineH ; fits winH for lineH <= %d"
              % (S, max(good) if good else -1))
        print("      plausible lineH(%d) from the two measured points:" % pt)
        for rule, val in (("15/13 ratio", round(pt * 15 / 13.)),
                          ("28/24 ratio", round(pt * 28 / 24.)),
                          ("28/26 ratio", round(pt * 28 / 26.)),
                          ("linear (13,15)-(24,28)", round(15 + (pt - 13) * 13 / 11.))):
            total = 9 * P.PAD + val * S
            print("        %-24s lineH=%-3d totalH=%-4d %s"
                  % (rule, val, total, "fits" if total <= H else "OVERFLOW"))


# ---------------------------------------------------------------------------
# A7  A CONCRETE label-set counterexample: breaks at 1.5, holds at 1, 2, 3
# ---------------------------------------------------------------------------
def e2_geom(f, kind, labels_cb, labels_pl):
    """Re-implementation of P.eng_font_box with an injected label set, so the
    search does not have to re-import the module thousands of times."""
    W = P.win_w(f)
    c = 1 if kind == P.CHECKBOX else 0
    pt = P.PT_RAW[f]
    need = max(TX.advance_width(l, pt) for l in labels_cb
               if l not in P.STOCK_WRAPS)
    box_cb = max(P.sc(P.TXW0 - P.CBW0, f), int(math.ceil(need)))
    strip = P.sc(P.CBW0, f) + P.sc(P.CBG, f) + P.sc(P.SWW, f) + \
        P.sc(P.SWG, f) + box_cb + P.sc(P.RM, f)
    box = box_cb if c else strip - P.sc(P.CBG, f) - P.sc(P.SWW, f) - \
        P.sc(P.SWG, f) - P.sc(P.RM, f)
    plot_r = W - P.sc(P.PLOTG, f) - strip
    return {"W": W, "strip": strip, "box": box, "plot_r": plot_r,
            "cbox_l": W - strip, "text_l": W - P.sc(P.RM, f) - box}


def a7():
    print()
    print(SEP)
    print("A7  CONCRETE COUNTEREXAMPLE SEARCH - a label set for which the")
    print("    CERTIFIED candidate E2-FONTBOX fails at f=1.5 and passes at")
    print("    f=1, f=2 and f=3")
    print(SEP)
    # search space: n copies of a wide glyph + k spaces (the only shape that
    # can satisfy the r = T/n >= 20.5 requirement derived from the 2x and 3x
    # constraints while still failing the 1.5x one).
    best = None
    for glyph in ("W", "M", "A", "D", "G", "T", "m"):
        if glyph not in TX.ADV26:
            continue
        for n in range(2, 60):
            for k in range(0, 8):
                lab = (glyph * n)
                if k:
                    step = max(1, n // (k + 1))
                    lab = " ".join([glyph * step] * k + [glyph * (n - step * k)])
                    if any(len(p) == 0 for p in lab.split(" ")):
                        continue
                if lab.count(" ") != k:
                    continue
                res = {}
                for f in P.TIERS:
                    g = e2_geom(f, P.CHECKBOX, P.LABELS[P.CHECKBOX] + [lab],
                                P.LABELS[P.PLAIN])
                    res[f] = g
                fails = {f: (res[f]["plot_r"] <= 0) for f in P.TIERS}
                if fails[1.5] and not fails[1.0] and not fails[2.0] \
                        and not fails[3.0]:
                    score = min(res[1.0]["plot_r"], res[2.0]["plot_r"],
                                res[3.0]["plot_r"]) + (-res[1.5]["plot_r"])
                    if best is None or score > best[0]:
                        best = (score, lab, res)
    if best is None:
        print("  no I4 counterexample found in the searched family")
        return None
    score, lab, res = best
    print("  FOUND.  extra legend label = %r  (%d chars, %d spaces)"
          % (lab, len(lab), lab.count(" ")))
    print("  every other label unchanged (the stock Garbage set).")
    print()
    print("    %-6s %-6s %-6s %-6s %-8s %-8s %-8s %s"
          % ("tier", "pt", "winW", "box", "strip", "cbox.L", "plot.R", "I4"))
    for f in P.TIERS:
        g = res[f]
        print("    %-6s %-6d %-6d %-6d %-8d %-8d %-8d %s"
              % ("%gx" % f, P.PT_RAW[f], g["W"], g["box"], g["strip"],
                 g["cbox_l"], g["plot_r"],
                 "FAIL (plot_r<=0)" if g["plot_r"] <= 0 else "pass"))
    print()
    print("  WHY 1.5x AND ONLY 1.5x: the box is font-driven, and the raw font")
    print("  ratio is 20/13 = %.4f at f=1.5 against a geometry ratio of 1.50."
          % (20 / 13.))
    print("  At f=2 and f=3 the font ratio is exactly 2.00 and 3.00.  The")
    print("  1.5x tier is the only place where round-half-up on 13*1.5 = 19.5")
    print("  makes the TEXT outgrow the WINDOW.")
    return lab


# ---------------------------------------------------------------------------
# A8  Execute it: does the real gate go red?
# ---------------------------------------------------------------------------
def a8(lab):
    print()
    print(SEP)
    print("A8  EXECUTE the counterexample through the REAL prover")
    print(SEP)
    if lab is None:
        print("  (no counterexample to run)")
        return None
    sys.modules.pop("prove_chart_legend", None)
    m = importlib.import_module("prove_chart_legend")
    m.LABELS[m.CHECKBOX] = list(m.LABELS[m.CHECKBOX]) + [lab]
    m.SEPS[m.CHECKBOX] = list(m.SEPS[m.CHECKBOX]) + [0]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = m.main()
    out = buf.getvalue()
    print("  prover exit code = %d  (%s)" % (rc, "RED" if rc else "GREEN"))
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("x ") or "E2-FONTBOX" in line:
            print("   ", s[:150])
    per_f = {}
    for inv, cand, hyp, f, kind, name, st, det in m.L.rows:
        if cand == "E2-FONTBOX" and st == "FAIL":
            per_f.setdefault(f, set()).add(inv)
    print("  E2-FONTBOX failures by tier: %s"
          % ({("%gx" % f): sorted(v) for f, v in sorted(per_f.items())}))
    # restore
    sys.modules.pop("prove_chart_legend", None)
    return rc


# ---------------------------------------------------------------------------
# A9  FALSE NEGATIVE: does I8 REJECT a physically-motivated correct fix at 1.5?
#     I8 hard-asserts swatch.T-rowTop == sc(3,f) and swatchH == sc(6,f).
#     The rival rule - the swatch keeps its PROPORTION of the LINE, which is
#     what the vertical sibling oracle argues for ("the swatch should go
#     6->12") - agrees at f=1 and f=2 (the only measured tiers) and diverges
#     elsewhere.  Two rules agreeing only where they were fitted.
# ---------------------------------------------------------------------------
def a9():
    print()
    print(SEP)
    print("A9  I8 OVER-CONSTRAINT: sc(3,f)/sc(6,f) vs line-proportional")
    print(SEP)
    print("    %-10s %-7s %-8s %-14s %-14s %s"
          % ("tier/hyp", "pt", "lineH", "I8 demands", "proportional", "verdict"))
    LH = {13: 15, 18: 21, 20: 23, 24: 28, 26: 28, 36: 42, 39: 45}
    diverge = []
    for f in P.TIERS:
        for tag, pm in (("SQZ", P.PT_SQUEEZED), ("RAW", P.PT_RAW)):
            pt = pm[f]
            lh = LH[pt]
            i8 = (P.sc(3, f), P.sc(6, f))
            pr = (int(round(3 * lh / 15.0)), int(round(6 * lh / 15.0)))
            same = i8 == pr
            meas = pt in P.LINEH_BY_PT
            print("    %-10s %-7d %-8s %-14s %-14s %s"
                  % ("%gx/%s" % (f, tag), pt,
                     "%d%s" % (lh, "" if meas else "*"),
                     "dy=%d h=%d" % i8, "dy=%d h=%d" % pr,
                     "agree" if same else "DIVERGE - I8 would REJECT it"))
            if not same:
                diverge.append("%gx/%s" % (f, tag))
    print("    * lineH not measured at this pt (U1) - value is the 15/13 rule")
    print("  -> the two rules agree at EXACTLY the tiers where lineH was")
    print("     measured (1x, 2x) and diverge at %s." % ", ".join(diverge))
    print("     I8 is a hard equality, so a fix that sizes the swatch from the")
    print("     LINE instead of from f is failed by the gate at 1.5x/SQZ - and")
    print("     SQZ is the font make_fontstyle.py actually SHIPS.")
    print("     This is the dangerous direction: a FALSE NEGATIVE on a good fix,")
    print("     produced by extrapolating a 2-point fit (law: two blind")
    print("     instruments agreeing = one instrument).")
    return diverge


def main():
    print(SEP)
    print("attack_15x - RED TEAM, TIER 1.5 LENS, against prove_chart_legend.py")
    print(SEP)
    a1()
    a2()
    a3()
    a4()
    a5()
    a6()
    lab = a7()
    a8(lab)
    a9()
    print()
    print(SEP)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
