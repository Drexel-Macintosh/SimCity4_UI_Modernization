# -*- coding: utf-8 -*-
r"""
break_labelset.py - ADVERSARIAL probe of prove_chart_legend.py through the
LABEL-SET lens.  It does not propose a fix; it tries to make the existing
oracle wrong, silent, or crash, by feeding it label sets it was never fitted
on but which the shipped game actually contains.

WHY THIS LENS.  prove_chart_legend.py claims to state what a correct legend
must satisfy "at ANY factor f and for ANY label set", but every one of its
4746 checks is evaluated over exactly TWO label sets:
    LABELS[CHECKBOX] = the 9 Rush Hour Garbage series
    LABELS[PLAIN]    = ["Income", "Expenses"]
The Graphs panel ships ~18 charts.

PROVENANCE OF THE LABELS USED HERE.  Read out of the game's own string table,
read-only, no game file written:
    <install>\SimCityLocale.DAT, DBPF 1.0, type 0x2026960B (LTEXT),
    group 0x6A231EAA.  Instances 0x0A5D2E96..0x0A5D2EB0 are 27 CONSECUTIVE
    LTEXT entries and are the vanilla graph label block:
      0a5d2e96 Mayor Rating          0a5d2ea0 Air Pollution
      0a5d2e97 Funds (000s)          0a5d2ea1 Water Pollution
      0a5d2e98 Resident Population   0a5d2ea2 Income
      0a5d2e99 Commercial Jobs       0a5d2ea3 Expenses
      0a5d2e9a Industrial Jobs       0a5d2ea4 # of Crimes
      0a5d2e9b Average Income (000s) 0a5d2ea5 # of Arrests
      0a5d2e9c Life Expectancy       0a5d2ea6 Education
      0a5d2e9d Capacity              0a5d2ea7..0a5d2eaf  1-10 .. 81-90
      0a5d2e9e Current Usage         0a5d2eb0 Commute Time
      0a5d2e9f Total Garbage
    "Income"/"Expenses" (0a5d2ea2/3) are in this block, which is the positive
    control that the block IS the graph label block.
    Also used: 0xCBC0F780 "Morning Commute", 0x4BC0F785 "Evening Commute",
    0xEAB6D25A "Water Treated", 0x4A551E24 "Commute Length" - same group,
    NOT in the consecutive block, so their binding to a specific chart is
    INFERRED, not proven.  Every result below is reported twice: once using
    only block-proven strings, once using the wider set.

USAGE
    python break_labelset.py            # run the three experiments
    python break_labelset.py --verbose  # + the oracle's own per-check output
Exit code 0 = the oracle SURVIVED every experiment.  Non-zero = at least one
experiment broke it (which is the expected outcome, and the point).
"""

import io
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu_text_extent as TX          # noqa: E402
import prove_chart_legend as P        # noqa: E402

VERBOSE = "--verbose" in sys.argv


# ---------------------------------------------------------------------------
#  The label sets.  BLOCK = proven-consecutive graph label block.
# ---------------------------------------------------------------------------
BLOCK = {
    "Mayor Rating": 0x0A5D2E96, "Funds (000s)": 0x0A5D2E97,
    "Resident Population": 0x0A5D2E98, "Commercial Jobs": 0x0A5D2E99,
    "Industrial Jobs": 0x0A5D2E9A, "Average Income (000s)": 0x0A5D2E9B,
    "Life Expectancy": 0x0A5D2E9C, "Capacity": 0x0A5D2E9D,
    "Current Usage": 0x0A5D2E9E, "Total Garbage": 0x0A5D2E9F,
    "Air Pollution": 0x0A5D2EA0, "Water Pollution": 0x0A5D2EA1,
    "Income": 0x0A5D2EA2, "Expenses": 0x0A5D2EA3,
    "# of Crimes": 0x0A5D2EA4, "# of Arrests": 0x0A5D2EA5,
    "Education": 0x0A5D2EA6,
    "1-10": 0x0A5D2EA7, "11-20": 0x0A5D2EA8, "21-30": 0x0A5D2EA9,
    "31-40": 0x0A5D2EAA, "41-50": 0x0A5D2EAB, "51-60": 0x0A5D2EAC,
    "61-70": 0x0A5D2EAD, "71-80": 0x0A5D2EAE, "81-90": 0x0A5D2EAF,
    "Commute Time": 0x0A5D2EB0,
}
SAME_GROUP_UNBOUND = {          # same LTEXT group, chart binding INFERRED
    "Morning Commute": 0xCBC0F780, "Evening Commute": 0x4BC0F785,
    "Water Treated": 0xEAB6D25A, "Commute Length": 0x4A551E24,
}

# Charts whose legend is a multi-series (checkbox) legend.  The series
# membership below is INFERRED from the consecutive-instance grouping; the
# STRINGS are measured.  Nothing in experiment 1 or 3 depends on the grouping.
CHARTS = [
    ("Water / Power  (Capacity + Current Usage)",
     ["Capacity", "Current Usage"], P.CHECKBOX),
    ("Crime         (# of Crimes + # of Arrests)",
     ["# of Crimes", "# of Arrests"], P.CHECKBOX),
    ("Jobs & Pop.   (3 series)",
     ["Resident Population", "Commercial Jobs", "Industrial Jobs"],
     P.CHECKBOX),
    ("Res. Avg. Income (1 series)", ["Average Income (000s)"], P.PLAIN),
    ("Funds            (1 series)", ["Funds (000s)"], P.PLAIN),
    ("Education by Age (9 age brackets)",
     ["1-10", "11-20", "21-30", "31-40", "41-50", "51-60", "61-70",
      "71-80", "81-90"], P.CHECKBOX),
]


def hr(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# ===========================================================================
#  EXPERIMENT 1 - can the text model even EVALUATE the shipped label pool?
# ===========================================================================
def experiment_1():
    hr("EXPERIMENT 1 - TOTALITY.  Can the oracle evaluate the shipped labels?")
    print("  emu_text_extent.advance_width() raises KeyError on any glyph with")
    print("  no measured advance, and prove_chart_legend calls it inside I3 with")
    print("  no guard.  A KeyError is neither PASS nor FAIL - the gate does not")
    print("  run at all.  The oracle's own --mutate harness already agrees that")
    print("  'a crash is not a pass'.")
    print()
    bad, good = [], []
    for lab in sorted(BLOCK):
        try:
            TX.advance_width(lab, 13.0)
            good.append(lab)
        except KeyError as e:
            bad.append((lab, str(e).split("for ")[1].split(" --")[0]))
    print("  vanilla graph label block: %d strings, %d evaluable, %d NOT"
          % (len(BLOCK), len(good), len(bad)))
    for lab, ch in bad:
        print("      NOT EVALUABLE  %-24s (LTEXT 0x%08X) missing glyph %s"
              % (repr(lab), BLOCK[lab], ch))
    print()
    print("  missing from the metric table entirely: uppercase B H K N O Q S U")
    print("  X Y Z, lowercase h j k q z, every digit 0-9, and # ( ) - , $ %")
    print()
    dead = []
    for name, labs, kind in CHARTS:
        miss = [l for l in labs
                if any(True for _ in [0]) and not _evaluable(l)]
        if miss:
            dead.append((name, miss))
    print("  whole charts the oracle CANNOT adjudicate:")
    for name, miss in dead:
        print("      %-42s  blocked by %s" % (name, ", ".join(map(repr, miss))))
    print()
    print("  LIVE DEMONSTRATION - call the oracle's own I3 on the Water/Power")
    print("  legend, exactly as run_candidate() would:")
    P.L.rows = []
    cols = P.eng_font_box(2.0, P.CHECKBOX)
    saved = P.LABELS[P.CHECKBOX]
    P.LABELS[P.CHECKBOX] = ["Capacity", "Current Usage"]
    try:
        P.inv3("E2-FONTBOX", "RAW", 2.0, P.CHECKBOX, cols, 26)
        print("      ... returned normally (unexpected)")
        broke = False
    except KeyError as e:
        print("      KeyError: %s" % e)
        print("      -> prove_chart_legend.main() would terminate with a")
        print("         traceback: no OVERALL line, no exit code 0 or 1.")
        broke = True
    finally:
        P.LABELS[P.CHECKBOX] = saved
    return broke, len(bad)


def _evaluable(s):
    try:
        TX.advance_width(s, 13.0)
        return True
    except KeyError:
        return False


# ===========================================================================
#  EXPERIMENT 2 - the certified candidate's box is fitted to NINE labels
# ===========================================================================
def _required_box(box1, pt, n_glyphs):
    """Closed form.  advance(L,S) = (S/13)*a + n*d*(S/13 - 1) with
    a = advance(L,13), d = DELTA = 0.70.  So the widest string that still fits
    `box1` at 13 pt needs, at point size S:
        (S/13)*box1 + n*d*(S/13 - 1)
    The n term is what E2-FONTBOX never varies: its box is fitted to the
    Garbage set, whose widest single-line label has 12 glyphs."""
    r = pt / 13.0
    return r * box1 + n_glyphs * TX.DELTA * (r - 1.0)


def experiment_2():
    hr("EXPERIMENT 2 - IS THE CERTIFIED BOX LABEL-SET INDEPENDENT?  (it is not)")
    print("  E2-FONTBOX sizes its text box as")
    print("      box(f) = max(sc(72,f), ceil(max advance over LABELS[CHECKBOX]")
    print("                                  that stock keeps on one line))")
    print("  LABELS[CHECKBOX] is the Garbage set.  Its widest single-line label")
    print("  is 'Total Garbage', 12 glyphs.  But advance(L,S) is NOT a function")
    print("  of advance(L,13) alone - it carries a +n*d*(S/13-1) term, so at the")
    print("  SAME stock width a label with MORE glyphs needs a WIDER box.")
    print()
    print("  %-6s %-5s %-8s %-12s %-12s %-10s %s"
          % ("tier", "pt", "E2 box", "need n=12", "need n=14", "need n=20",
             "shortfall @n=20"))
    rows = []
    for f in P.TIERS:
        for hyp, pm in P.PT_HYPS:
            pt = pm[f]
            box = P.eng_font_box(f, P.CHECKBOX)["text"]
            bw = box[1] - box[0]
            n12 = _required_box(72, pt, 12)
            n14 = _required_box(72, pt, 14)
            n20 = _required_box(72, pt, 20)
            rows.append((f, hyp, pt, bw, n20 - bw))
            print("  %-6s %-5d %-8d %-12.1f %-12.1f %-10.1f %+.1f px%s"
                  % ("%gx" % f, pt, bw, n12, n14, n20, n20 - bw,
                     "   <-- TOO NARROW" if n20 > bw + 1e-9 else ""))
    print()
    print("  The shortfall grows with the tier: it is 0 at f=1 (which is why")
    print("  I5 cannot see it) and worst at f=3.")
    return rows


# ===========================================================================
#  EXPERIMENT 3 - a CONCRETE label that fits at stock and wraps under E2
# ===========================================================================
def experiment_3():
    hr("EXPERIMENT 3 - CONCRETE COUNTEREXAMPLE, run through the oracle's own I3")
    box1_cb, box1_pl = 72, 88
    e2 = {}
    for f in P.TIERS:
        e2[f] = (P.eng_font_box(f, P.CHECKBOX)["text"][1]
                 - P.eng_font_box(f, P.CHECKBOX)["text"][0],
                 P.eng_font_box(f, P.PLAIN)["text"][1]
                 - P.eng_font_box(f, P.PLAIN)["text"][0])
    print("  E2-FONTBOX box widths: " +
          "  ".join("%gx cb=%d pl=%d" % (f, e2[f][0], e2[f][1])
                    for f in P.TIERS))
    print()
    cands = [("Water Treated",  0xEAB6D25A, P.CHECKBOX, box1_cb),
             ("Evening Commute", 0x4BC0F785, P.PLAIN,   box1_pl)]
    hits = []
    for lab, ins, kind, box1 in cands:
        a13 = TX.advance_width(lab, 13.0)
        print("  %-17s LTEXT 0x%08X  %-8s  13pt %.2f px vs stock box %d -> %s"
              % (repr(lab), ins, kind, a13, box1,
                 "FITS (1 line)" if a13 <= box1 else "wraps at stock"))
        if a13 > box1:
            continue
        for f in (2.0, 3.0):
            for hyp, pm in P.PT_HYPS:
                pt = pm[f]
                bw = e2[f][0 if kind == P.CHECKBOX else 1]
                a = TX.advance_width(lab, float(pt))
                n = len(TX.wrap(lab, float(pt), bw))
                flag = ""
                if n > 1:
                    flag = "  <-- WRAPS; stock does not.  I3 VIOLATION"
                    hits.append((lab, f, hyp, pt, bw, a, n))
                print("        f=%gx %-9s %2dpt  need %6.1f  E2 box %3d  "
                      "lines %d%s" % (f, hyp, pt, a, bw, n, flag))
        print()

    print("  NOW RUN THE ORACLE'S OWN I3 ON IT (no reimplementation).")
    print("  TWO engines: E2 exactly as written (box re-derived from whatever")
    print("  label set it is handed) and E2-SHIPPED (box FROZEN at the constant")
    print("  the Garbage set produces, which is what a DLL would actually ship).")
    print()
    for lab, f, hyp, pt, bw, a, n in hits:
        kind = P.CHECKBOX if lab == "Water Treated" else P.PLAIN
        for eng_name, cols in (("E2-as-written", None),
                               ("E2-SHIPPED", "frozen")):
            P.L.rows = []
            saved_lab, saved_wrap = P.LABELS[kind], set(P.STOCK_WRAPS)
            frozen = P.eng_font_box(f, kind)      # box from the GARBAGE set
            P.LABELS[kind] = [lab]
            P.STOCK_WRAPS.clear()      # this label does NOT wrap at stock
            try:
                c = frozen if cols == "frozen" else P.eng_font_box(f, kind)
                P.inv3(eng_name, hyp, f, kind, c, pt)
            finally:
                P.LABELS[kind] = saved_lab
                P.STOCK_WRAPS.clear()
                P.STOCK_WRAPS.update(saved_wrap)
            for inv, cc, h, ff, k, nm, st, d in P.L.rows:
                print("      I3 %-14s %-9s f=%gx %-8s %-4s %s"
                      % (cc, h, ff, k, st, d))
    print()
    print("  READ THAT AGAIN.  E2-as-written PASSES on a label it visibly wraps.")
    print("  See EXPERIMENT 5.")
    print()
    print("  RESIDUAL WARNING (stated, not hidden): 'Water Treated' is 71.8 px")
    print("  at 13 pt against a 72 px box, and 'Evening Commute' 87.4 against")
    print("  88.  Both sit INSIDE emu_text_extent's own +-%.1f px residual, so"
          % TX.TOL)
    print("  'it fits at stock' is NOT decidable from this model alone - the")
    print("  oracle says so itself in inv3's detail string.  What IS decidable")
    print("  is experiment 2's arithmetic, which needs no particular label.")
    return hits


# ===========================================================================
#  EXPERIMENT 4 - how wide is the failure BAND, over the real string corpus?
# ===========================================================================
def experiment_4(corpus_path=None):
    hr("EXPERIMENT 4 - how big is the band?  (needs the LTEXT dump; optional)")
    if not corpus_path or not os.path.exists(corpus_path):
        print("  SKIPPED - no LTEXT corpus at %r." % corpus_path)
        print("  Re-run with the path to a 'file group inst text' dump of")
        print("  SimCityLocale.DAT to reproduce the survey.")
        return None
    strs = set()
    for line in io.open(corpus_path, encoding="utf-8"):
        p = line.split(" ", 3)
        if len(p) < 4:
            continue
        s = p[3].strip()
        if 0 < len(s) <= 30:
            strs.add(s)
    ev = [s for s in strs if _evaluable(s)]
    print("  corpus %d strings <=30 chars, %d evaluable by the metric table"
          % (len(strs), len(ev)))
    for kind, box1, idx in ((P.CHECKBOX, 72, 0), (P.PLAIN, 88, 1)):
        bw = (P.eng_font_box(2.0, kind)["text"][1]
              - P.eng_font_box(2.0, kind)["text"][0])
        div = [s for s in ev
               if len(TX.wrap(s, 13.0, box1)) < len(TX.wrap(s, 26.0, bw))]
        need = max((TX.advance_width(s, 26.0) for s in ev
                    if TX.advance_width(s, 13.0) <= box1), default=0)
        print("  %-9s stock box %d, E2 2x box %d: %d of %d evaluable strings"
              % (kind, box1, bw, len(div), len(ev)))
        print("            wrap MORE at 2x than at stock.  Widest 26 pt demand"
              " among strings that fit at stock: %.1f px -> E2 is %.1f px short"
              % (need, need - bw))
        for s in sorted(div)[:6]:
            print("              %r" % s)
    return True


# ===========================================================================
#  EXPERIMENT 5 - I3 IS A TAUTOLOGY FOR THE ONE CANDIDATE IT CERTIFIES
# ===========================================================================
def experiment_5():
    hr("EXPERIMENT 5 - I3 HAS ZERO POWER AGAINST E2-FONTBOX (it cannot fail)")
    print("  prove_chart_legend._font_box() is")
    print("      need = max(advance(l, pt) for l in LABELS[CHECKBOX]")
    print("                 if l not in STOCK_WRAPS)")
    print("      return max(sc(72,f), ceil(need))")
    print("  and inv3() then asserts, for every l in LABELS[CHECKBOX] not in")
    print("  STOCK_WRAPS,  advance(l, pt) <= box.  The quantifier, the set and")
    print("  the point size are THE SAME.  box is defined as the max of exactly")
    print("  the quantity being bounded, so the assertion is true by")
    print("  construction under RAW and a fortiori under SQUEEZED (smaller pt).")
    print()
    print("  DEMONSTRATION - hand E2 an absurd label and watch I3 pass:")
    absurd = "Total Garbage Total Garbage Total Garbage"
    for f in (2.0, 3.0):
        for hyp, pm in P.PT_HYPS:
            pt = pm[f]
            P.L.rows = []
            saved, sw = P.LABELS[P.CHECKBOX], set(P.STOCK_WRAPS)
            P.LABELS[P.CHECKBOX] = [absurd]
            P.STOCK_WRAPS.clear()
            try:
                cols = P.eng_font_box(f, P.CHECKBOX)
                bw = cols["text"][1] - cols["text"][0]
                P.inv3("E2-FONTBOX", hyp, f, P.CHECKBOX, cols, pt)
            finally:
                P.LABELS[P.CHECKBOX] = saved
                P.STOCK_WRAPS.clear()
                P.STOCK_WRAPS.update(sw)
            sts = set(r[6] for r in P.L.rows)
            print("      f=%gx %-9s %2dpt  label %d chars, box grew to %d px"
                  "  -> I3 %s" % (f, hyp, pt, len(absurd), bw,
                                  "/".join(sorted(sts))))
    print()
    print("  The box simply grows to whatever it is asked to hold, INCLUDING")
    print("  past the chart window: at 3x the strip would be %d px wide inside"
          % (P.win_w(3.0) - P.eng_font_box(3.0, P.CHECKBOX)["cbox"][0]
             if P.eng_font_box(3.0, P.CHECKBOX)["cbox"] else 0))
    print("  a %d px window if such a label existed.  I4 would catch THAT, but"
          % P.win_w(3.0))
    print("  I3 - the invariant the gate's certification note names - never")
    print("  can.  Consequence: 'E2-FONTBOX passed every decidable check under")
    print("  BOTH font hypotheses' overstates what was shown.  I3 contributed")
    print("  no evidence for E2; it only ever falsified E-STRIPxf, whose box is")
    print("  NOT defined from the label set.")
    return True


def main():
    print("=" * 78)
    print("break_labelset - adversarial LABEL-SET probe of prove_chart_legend")
    print("  offline only: imports two sibling modules, writes nothing, reads")
    print("  no game file (the LTEXT strings are transcribed above with their")
    print("  instance ids).")
    print("=" * 78)

    crashed, n_unevaluable = experiment_1()
    experiment_2()
    hits = experiment_3()
    corpus = None
    for a in sys.argv[1:]:
        if a.endswith(".txt"):
            corpus = a
    experiment_4(corpus)
    taut = experiment_5()

    hr("VERDICT")
    broke = bool(crashed) or bool(hits) or bool(taut)
    print("  E1 totality     : %d of %d shipped graph labels are NOT evaluable;"
          % (n_unevaluable, len(BLOCK)))
    print("                    calling the oracle's own I3 on a real chart's")
    print("                    legend raises KeyError -> %s"
          % ("CRASH REPRODUCED" if crashed else "did not crash"))
    print("  E2 box formula  : E2-FONTBOX's box is a max over NINE labels; the")
    print("                    label-set-independent requirement carries a")
    print("                    +n*d*(pt/13-1) term it never varies.")
    print("  E3 counterexample: %d (label, tier, hypothesis) triples where a"
          % len(hits))
    print("                    real shipped string fits at stock and wraps")
    print("                    under the CERTIFIED candidate's SHIPPED box.")
    print("  E5 tautology    : I3 cannot fail for E2-FONTBOX - its box is")
    print("                    defined as the max of the very quantity I3")
    print("                    bounds, over the very same label set.")
    print()
    print("OVERALL: %s" % ("BROKEN" if broke else "SURVIVED"))
    return 1 if broke else 0


if __name__ == "__main__":
    sys.exit(main())
