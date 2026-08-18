r"""
emu_chart_font.py - the DATA/FONT knob on top of emu_chart_legend.py (#57).

QUESTION IT ANSWERS: the Graphs legend labels are drawn in the FontStyle style
ChartLabel (GUID 0xE9C86B5E) - byte-verified this session at

    0x0076DD8A  call 0x913c72          ; style manager
    0x0076DD91  push 0xe9c86b5e        ; <-- ChartLabel
    0x0076DD98  call [edx+0x14]        ; -> font object
    0x0076DDA2  mov [esp+0x34], eax    ; frame[0x30]  (one pending push)
    ...
    0x0076E2DA  mov eax,[esp+0x30]     ; SAME slot, the loop's font
    0x0076E2FD  call [eax+0xB8]        ; FitRectToText(str,len,&rect,1,1)

so the legend's ROW HEIGHTS are 100% data-driven from FontStyle.ini.
This file asks: what ChartLabel size / advance scale makes the MEASURED stock
proportions hold at 2x, for a given legend column width?

FONT MODEL (two measured anchors, everything else flagged)
  lineHeight(size) = size + linespacing        MEASURED: 13+2=15, 26+2=28
                     (linespacing=2 is in the ChartLabel line at every tier;
                      make_fontstyle.py deliberately does NOT scale it)
  ink(label,size)  = ink13(label) * adv(size)/adv(13)
                     MEASURED: "Income" 33px @13pt, 70px @26pt -> the ratio is
                     2.1212, NOT 2.00.  Per-point advance is 6.06% larger at
                     26pt than at 13pt (glyph-advance rounding).
                     MODELLED for every other size: adv grows linearly in size
                     between those two anchors and is extrapolated beyond.
                     ANY size other than 13 or 26 is printed with a "~".

SCOPE: layout only, exactly as emu_chart_legend.py.  Nothing here proves a
rect reaches the screen, and it says nothing about the swatch or the checkbox
(neither is font-driven).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu_chart_legend as E   # noqa: E402

STOCK_SIZE = 13          # ChartLabel stock point size
LINESPACING = 2          # from the ChartLabel params, all tiers
K26 = E.INK_RATIO_2X / 2.0        # 1.0606: per-pt advance growth 13pt -> 26pt


def adv(size):
    """Per-point advance factor, normalised to 1.0 at 13pt."""
    return 1.0 + (K26 - 1.0) * (size - STOCK_SIZE) / float(26 - STOCK_SIZE)


def install_font(size, xadv=1.0):
    """Drive emu_chart_legend's two font inputs from a point size."""
    ratio = (size / float(STOCK_SIZE)) * adv(size) * xadv
    E.line_height = lambda f, _s=size: int(_s + LINESPACING)
    E.ink_ratio = lambda f, _r=ratio: _r
    return ratio


def exact(size):
    return size in (STOCK_SIZE, 26)


def run(name, f, size, xadv=1.0, iv=None, rows=None, kind_rows=None):
    iv = iv or E.Interventions()
    out = {}
    ratio = install_font(size, xadv)
    for kind, rws in (("cbox", E.GARBAGE_ROWS), ("plain", E.PLAIN_ROWS)):
        lay = E.predict(f, iv, rows=rws)
        ok, bad = E.verdict(lay)
        out[kind] = (lay, ok, bad)
    return name, size, xadv, ratio, out


def show(res):
    name, size, xadv, ratio, out = res
    tag = "" if exact(size) and xadv == 1.0 else "~"
    print("\n--- %s   ChartLabel %dpt xadv %.3f -> ink ratio %s%.3f, "
          "lineH %d" % (name, size, xadv, tag, ratio, size + LINESPACING))
    for kind in ("cbox", "plain"):
        lay, ok, bad = out[kind]
        cx = lay["cbox_x"]
        print("    %-5s cbox %-12s swatch %-12s text %-12s boxW %-4d "
              "lines %s bottom %d/%d  %s"
              % (kind,
                 ("%d..%d" % cx) if cx else "-",
                 "%d..%d" % lay["swatch_x"],
                 "%d..%d" % lay["text_x"],
                 lay["box_w"],
                 [r["lines"] for r in lay["rows"]],
                 lay["bottom"], lay["win_h"],
                 "OK" if ok else "BROKEN"))
        for b in bad:
            print("            ! " + b)


def max_size_for_box(box_w, widest_ink13, xadv=1.0):
    """Largest integer point size whose widest must-fit label still fits."""
    s = STOCK_SIZE
    while True:
        if widest_ink13 * (s + 1) / float(STOCK_SIZE) * adv(s + 1) * xadv > box_w:
            return s
        s += 1
        if s > 200:
            return s


def main():
    print("=" * 76)
    print("A. THE MEASURED FONT LAW")
    print("=" * 76)
    for s in (13, 26):
        print("   %2dpt  lineHeight %2d   ink('Income') %5.1f   "
              "ink('Total Garbage') %5.1f   ink('Expenses') %5.1f"
              % (s, s + LINESPACING,
                 33 * s / 13.0 * adv(s),
                 68 * s / 13.0 * adv(s),
                 42 * s / 13.0 * adv(s)))
    print("   (both rows MEASURED: 33/70 for Income, 15/28 line height)")

    print("\n" + "=" * 76)
    print("B. HEADROOM IN THE **UNCHANGED** 1x COLUMN (box 72 cbox / 88 plain)")
    print("=" * 76)
    print("   cbox  widest must-fit label 'Total Garbage' 68px@13 in a 72px box")
    print("         -> max ChartLabel size = %dpt   (headroom %.1f%%)"
          % (max_size_for_box(72, 68), 100.0 * (72 / 68.0 - 1)))
    print("   plain widest must-fit label 'Expenses'      42px@13 in an 88px box")
    print("         -> max ChartLabel size = %dpt   (headroom %.1f%%)"
          % (max_size_for_box(88, 42), 100.0 * (88 / 42.0 - 1)))
    print("   at the SHIPPED 26pt: 'Expenses' = %.1f px in an 88px box -> WRAPS"
          % (42 * 2 * adv(26)))
    print("   (that is the user's 'Income / Expense s' screenshot, reproduced)")

    print("\n" + "=" * 76)
    print("C. HEADROOM IN A BUDGET-SCALED COLUMN (box 144 cbox / 176 plain)")
    print("=" * 76)
    print("   cbox  -> max ChartLabel size = %dpt  ('Total Garbage' %.1f px "
          "in 144)" % (max_size_for_box(144, 68), 68 * 2 * adv(26)))
    print("   plain -> max ChartLabel size = %dpt" % max_size_for_box(176, 42))
    print("   NOTE 68*2.1212 = %.1f > 144 by %.1f px: at the shipped 26pt the "
          "budget fix\n        still wraps ONE extra label vs stock."
          % (68 * 2 * adv(26), 68 * 2 * adv(26) - 144))
    for x in (0.99, 0.985, 0.98, 0.95):
        print("        xadvancescale factor %.3f -> 'Total Garbage' %.1f px %s"
              % (x, 68 * 2 * adv(26) * x,
                 "FITS" if 68 * 2 * adv(26) * x <= 144 else "wraps"))

    print("\n" + "=" * 76)
    print("D. CANDIDATES ADJUDICATED (f=2, Garbage + Income/Expenses)")
    print("=" * 76)
    budget = E.Interventions(scale_budget=True)
    today = E.Interventions(sweep_cbox_size=True, earlychart=True,
                            legendfix_2544=True)
    show(run("D0 today (v2.54.4), ChartLabel 26", 2.0, 26, iv=today))
    sweep = E.Interventions(sweep_cbox_size=True)
    show(run("D1 DATA ONLY 26pt condensed to 1x ink, sweep STILL doubling",
             2.0, 26, xadv=13 / 26.0 / adv(26), iv=sweep))
    show(run("D2 DATA ONLY ChartLabel pinned to stock 13, sweep doubling",
             2.0, 13, iv=sweep))
    show(run("D3 budget x2 + ChartLabel 26 (as shipped)", 2.0, 26, iv=budget))
    show(run("D4 budget x2 + ChartLabel 25", 2.0, 25, iv=budget))
    show(run("D5 budget x2 + 26pt, xadvancescale 0.99->0.98", 2.0, 26,
             xadv=0.98 / 0.99, iv=budget))
    show(run("D6 budget x2 + 26pt, xadvancescale 0.99->0.97", 2.0, 26,
             xadv=0.97 / 0.99, iv=budget))

    print("\n" + "=" * 76)
    print("F. PER-TIER ChartLabel CEILING in a BUDGET-SCALED column")
    print("   (widest must-fit label as the model measures it: "
          "'Total ' + 'Garbage' = 69 px @13pt)")
    print("=" * 76)
    for f, cur in ((1.0, 13), (1.5, 20), (2.0, 26), (3.0, 39)):
        box = int(round(72 * f))
        cap = max_size_for_box(box, 69)
        print("   f=%.1f  box %3d  make_fontstyle ships %2dpt  ceiling %2dpt  %s"
              % (f, box, cur, cap,
                 "OK" if cur <= cap else "OVER by %d pt" % (cur - cap)))

    print("\n" + "=" * 76)
    print("E. SELF-CHECK: f=1, ChartLabel 13 must reproduce stock")
    print("=" * 76)
    install_font(13)
    lay = E.predict(1.0, E.Interventions(), rows=E.GARBAGE_ROWS)
    ok = (lay["tops"] == [20, 39, 73, 92, 126, 145, 164, 183, 217]
          and lay["cbox_x"] == (380, 396) and lay["swatch_x"] == (398, 408)
          and lay["text_x"] == (412, 484))
    print("   tops %s\n   cbox %s swatch %s text %s -> %s"
          % (lay["tops"], lay["cbox_x"], lay["swatch_x"], lay["text_x"],
             "PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
