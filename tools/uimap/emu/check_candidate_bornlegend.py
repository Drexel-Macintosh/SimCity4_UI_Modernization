"""#57 candidate adjudicator: BORNLEGEND (origin-scaling inside sub_76D3D0).

Runs the shipped model (emu_chart_legend.py) with EXACTLY the constants the
BORNLEGEND candidate produces, and prints the predicted columns for both chart
kinds at f=1 (self-check, must reduce to stock) and f=2.

The candidate, restated as constants:
  patched in sub_76D3D0 (game's own layout, so BORN correct):
    SWATCH_MARGIN_PLAIN  106 -> round(106*f)     (delta trampoline @0x0076E0F0)
    SWATCH_MARGIN_CBOX    90 -> round(90*f)      (delta trampoline @0x0076E1EF)
    CBOX_L_MARGIN        108 -> round(108*f)     (delta trampoline @0x0076E155)
    CBOX_R_MARGIN         92 -> round(108*f)-16  (same trampoline: edx biased,
                                                  so the code still writes a
                                                  16-wide box)
    SWATCH_W              10 -> round(10*f)      imm8 @0x0076E23C
    SWATCH_DY              3 -> round(3*f)       imm8 @0x0076E233
    SWATCH_H               6 -> round(6*f)       imm8 @0x0076E239 (dy+h)
    TEXT_GAP               4 -> round(4*f)       imm8 @0x0076E2AF
    TEXT_R_MARGIN          4 -> round(4*f)       imm8 @0x0076E2C8
    ROW0_TOP              20 -> round(20*f)      imm32 @0x0076DE79
    ROW_PAD                4 -> 4   UNTOUCHED (it is the STEP - #78 rule 1)
  done by us at birth (chart main vt+0x38 AddChildWindow detour):
    CBOX_H/W              16 -> round(16*f)      (art-sized control, law 13)
  unchanged:
    PLOT_R_MARGIN        110 -> round(110*f)     via the EXISTING ChartStoreThunk
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu_chart_legend as M


def candidate_consts(f):
    C = M.STOCK.copy()
    r = lambda v: int(round(v * f))
    C.SWATCH_MARGIN_PLAIN = r(106)
    C.SWATCH_MARGIN_CBOX = r(90)
    C.CBOX_L_MARGIN = r(108)
    C.CBOX_R_MARGIN = r(108) - 16      # game still writes a 16-wide window
    C.SWATCH_W = r(10)
    C.SWATCH_DY = r(3)
    C.SWATCH_H = r(6)
    C.TEXT_GAP = r(4)
    C.TEXT_R_MARGIN = r(4)
    C.ROW0_TOP = r(20)
    C.CBOX_H = 16                      # the game's write; our detour fixes it
    C.PLOT_R_MARGIN = r(110)           # EARLYCHART, unchanged
    C.PLOT_L = r(45)                   # EARLYCHART, unchanged
    C.PLOT_T = r(20)                   # EARLYCHART, unchanged
    C.PLOT_B_MARGIN = r(20)            # EARLYCHART, unchanged
    return C


def born_checkbox_resize(lay, f):
    """Our chart-AddChildWindow detour: size-only, at birth, art-sized rule."""
    w = int(round(16 * f))
    if lay["cbox_x"]:
        l, _ = lay["cbox_x"]
        lay["cbox_x"] = (l, l + w)
    for row in lay["rows"]:
        if row["cbox"]:
            l, t, _, _ = row["cbox"]
            row["cbox"] = (l, t, l + w, t + w)
    return lay


def run(f, rows, name):
    win_w = int(round(M.STOCK_WIN_W * f))
    win_h = int(round(M.STOCK_WIN_H * f))
    C = candidate_consts(f)
    lay = M.game_layout(win_w, win_h, rows, f, C)
    lay = born_checkbox_resize(lay, f)
    ok, bad = M.verdict(lay)
    print("-" * 76)
    print("%s  f=%.2f  window %dx%d" % (name, f, win_w, win_h))
    print("  plot      %s" % (lay["plot"],))
    print("  checkbox  %s" % (lay["cbox_x"],))
    print("  swatch    %s  (%dx%d, dy %d)"
          % (lay["swatch_x"], C.SWATCH_W, C.SWATCH_H, C.SWATCH_DY))
    print("  text      %s  boxW %d" % (lay["text_x"], lay["box_w"]))
    if lay["cbox_x"]:
        print("  gaps      plot->cbox %d   cbox->swatch %d   swatch->text %d"
              % (lay["cbox_x"][0] - lay["plot"][2],
                 lay["swatch_x"][0] - lay["cbox_x"][1],
                 lay["text_x"][0] - lay["swatch_x"][1]))
    else:
        print("  gaps      plot->swatch %d   swatch->text %d"
              % (lay["swatch_x"][0] - lay["plot"][2],
                 lay["text_x"][0] - lay["swatch_x"][1]))
    print("  row tops  %s" % lay["tops"])
    print("  lines     %s" % [r["lines"] for r in lay["rows"]])
    print("  bottom    %d  (window %d, spare %d)"
          % (lay["bottom"], win_h, win_h - lay["bottom"]))
    print("  VERDICT   %s" % ("OK" if ok else "BROKEN"))
    for b in bad:
        print("            - " + b)
    return ok, lay


def main():
    allok = True
    for f in (1.0, 2.0):
        for rows, nm in ((M.GARBAGE_ROWS, "GARBAGE (cbox)"),
                         (M.PLAIN_ROWS, "INCOME/EXPENSES (plain)")):
            ok, _ = run(f, rows, nm)
            allok = allok and ok
    # SELF-CHECK (law 27 / #88): at f=1 the whole set must reduce to stock.
    print("=" * 76)
    C1 = candidate_consts(1.0)
    same = all(getattr(C1, k) == getattr(M.STOCK, k)
               for k in ("SWATCH_MARGIN_PLAIN", "SWATCH_MARGIN_CBOX",
                         "CBOX_L_MARGIN", "SWATCH_W", "SWATCH_DY", "SWATCH_H",
                         "TEXT_GAP", "TEXT_R_MARGIN", "ROW0_TOP",
                         "PLOT_R_MARGIN", "PLOT_L", "PLOT_T", "PLOT_B_MARGIN"))
    print("f=1 reduces to stock exactly: %s" % same)
    print("f=1 CBOX_R_MARGIN %d (stock 92): %s"
          % (C1.CBOX_R_MARGIN, C1.CBOX_R_MARGIN == 92))
    # 3x encoding audit: which imm8 sites overflow.
    print("-" * 76)
    print("imm8 encoding audit (sign-extended imm8 range -128..127):")
    for nm, stock in (("SWATCH_W @0x0076E23C", 10), ("SWATCH_DY @0x0076E233", 3),
                      ("SWATCH_DY+H @0x0076E239", 9),
                      ("TEXT_GAP @0x0076E2AF", 4),
                      ("TEXT_R_MARGIN @0x0076E2C8", 4)):
        for f in (1.5, 2.0, 3.0):
            v = int(round(stock * f))
            if v > 127:
                print("  OVERFLOW %s at f=%.1f -> %d" % (nm, f, v))
    print("  (all fit through 3x)")
    print("=" * 76)
    print("OVERALL: %s" % ("PASS" if allok else "FAIL"))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
