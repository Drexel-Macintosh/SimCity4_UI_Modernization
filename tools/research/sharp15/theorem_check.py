"""THE ODD/EVEN THEOREM, CHECKED ON SYNTHETIC SHEETS.

At f = 3/2 a source run of width w wants 1.5w output pixels, an integer only
for even w. Every position-independent rule therefore lands on one side:

    rule                      1px          2px        3px          4px
    nearest (phase-fixed)     1 or 2       3          4 or 5       6
    naive tie -> longer run   1            2 or 3     4            5 or 6
    naive tie -> shorter run  2            3 or 4     5            6 or 7
    edge-claim thin           1            3          4            6
    edge-claim bold           2            3          5            6
    area-average (box)        1 + half     3 (+halves) 4 + half    6

"edge-claim": an even run at half-offset owns two tie blocks and takes exactly
its LEFT one (net 1.5w, exact); an odd run owns exactly one tie block and the
policy decides it (thin: never, bold: always); long runs (>= 5) absorb.

This script builds a sheet holding strokes of width 1..4 at EVERY phase
(origin parity), pushes it through every candidate in resamplers.CANDIDATES,
and prints the output widths it measured. Widths are measured with
stroke_width.sheet_stats, so this is also the instrument's own selftest: the
`nearest` row MUST read cv_1 > 0, cv_2 == 0, cv_3 > 0, cv_4 == 0 and the
integer-factor rows MUST read all zeros, or the instrument is wrong.

    python theorem_check.py            # 1.5 and the 2x/3x controls
"""
import sys
import numpy as np

import resamplers as R
import stroke_width as SW

BG = np.array([40, 40, 48, 255], np.uint8)
INK = np.array([230, 230, 220, 255], np.uint8)


def sheet(widths=(1, 2, 3, 4), gap=7, rows=24):
    """Vertical strokes of each width at both origin parities, on a wide
    background; and the same as horizontal strokes below, so both axes are
    exercised. Returns HxWx4."""
    cols = []
    x = gap
    for w in widths:
        for parity in (0, 1):
            while x % 2 != parity:
                x += 1
            cols.append((x, w))
            x += w + gap
    W = x + gap
    a = np.empty((rows, W, 4), np.uint8)
    a[...] = BG
    for x0, w in cols:
        a[:, x0:x0 + w] = INK
    # horizontal strokes: transpose the same pattern
    b = np.transpose(a, (1, 0, 2)).copy()
    H = a.shape[0] + b.shape[0] + gap
    Wt = max(a.shape[1], b.shape[1])
    out = np.empty((H, Wt, 4), np.uint8)
    out[...] = BG
    out[:a.shape[0], :a.shape[1]] = a
    out[a.shape[0] + gap:, :b.shape[1]] = b
    return out


def widths_table(src, out, f):
    st = SW.sheet_stats(src, out, f)
    return st


def main():
    src = sheet()
    h, w = src.shape[:2]
    print("synthetic sheet %dx%d, strokes 1..4px at both parities, both axes" % (w, h))
    fails = 0
    for f in (1.5, 2.0, 3.0):
        ow, oh = int(np.floor(w * f + 0.5)), int(np.floor(h * f + 0.5))
        print("\n=== factor %.1f  (out %dx%d) ===" % (f, ow, oh))
        print("%-18s %s" % ("candidate", "output widths per source width (L: {out:count})"))
        for name, fn in R.CANDIDATES.items():
            try:
                o = fn(src, ow, oh, factor=f)
            except TypeError:
                o = fn(src, ow, oh)
            st = SW.sheet_stats(src, o, f)
            cells = []
            for L in range(1, 5):
                cells.append("%d:%s" % (L, st.get("hist_%d" % L, {})))
            print("%-18s %s   swc %.3f blended %d" % (name, "  ".join(cells), st["swc"], st["blended"]))
            if f != 1.5:
                # integer control: every candidate must be nearest and every CV 0
                if st["swc"] != 0.0 or st["blended"] != 0:
                    print("   ^ FAIL: integer factor is not a clean replicate")
                    fails += 1
                nn = R.nearest(src, ow, oh, factor=f)
                if not np.array_equal(nn, o):
                    print("   ^ FAIL: differs from nearest at an integer factor")
                    fails += 1
            elif name == "nearest":
                ok = (st["cv_1"] > 0 and st["cv_2"] == 0 and st["cv_3"] > 0
                      and st["cv_4"] == 0)
                if not ok:
                    print("   ^ FAIL: nearest does not show the predicted odd/even profile"
                          " - the INSTRUMENT is wrong")
                    fails += 1
    print("\n%s" % ("THEOREM CHECK PASS" if fails == 0 else "THEOREM CHECK FAIL (%d)" % fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
