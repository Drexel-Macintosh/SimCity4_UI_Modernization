"""A2 CONTROL (2026-09-07): from2x_box vs box, pixel for pixel, on stock sheets.

"Take the 2x art and shrink it by 3/4" integrates the same image over the same
output box as the x3 area average, with every weight exactly 4x - so it must
be `box` to the bit. This prints the direct pixel diff on the bench's own
sheet sample (unkeyed first, then keyed, so the key rule is exercised), at
THREE stages, because the lab `box` candidate carries no nearest key mask
while from2x_box (as specified) does:

    A  from2x_box RAW (no key mask)  vs  box                 -> the arithmetic
    B  from2x_box (masked)           vs  nn_key_mask(box)    -> same stage
    C  from2x_box (masked)           vs  box                 -> as registered;
       the difference is the mask step, split into alpha-only-on-key-pixels
       and colour differences so nothing hides in "5%"

Per pair: identical % (RGBA byte-equal), |d|==1 % (largest channel delta
exactly 1 - integer tie-break would live here if the weights were not exact),
|d|>1 % (anything larger).

    python from2x_diff.py [n_unkeyed=15] [n_keyed=10] [seed=7]
"""
import sys
import numpy as np

import bench as B
import x3_candidates as X


def _diff(o1, o2):
    d = np.abs(o1.astype(np.int16) - o2.astype(np.int16))
    dm = d.max(-1)
    return d, dm


def main(nu=15, nk=10, seed=7):
    uk, kk = B.sample(nu, nk, seed=seed)
    sheets = [(n, a, False) for n, a in uk] + [(n, a, True) for n, a in kk]
    pairs = {"A raw vs box": [0, 0, 0, 0], "B masked vs masked box": [0, 0, 0, 0],
             "C masked vs box (as registered)": [0, 0, 0, 0]}
    c_alpha_only_key = 0        # C: pixels differing in alpha only, on nearest-key pixels
    c_colour = 0                # C: pixels differing in RGB
    per_sheet = []
    for n, a, keyed in sheets:
        oh, ow = B.load(B.os.path.join(B.TIER["1.5"], n)).shape[:2]
        box = X.CANDIDATES["box"](a, ow, oh)
        box_m = X._nn_key_mask(box, a, ow, oh)
        raw = X._per_cell(a, ow, oh, 0, 0, X._from2x_box_raw)
        f2 = X.CANDIDATES["from2x_box"](a, ow, oh)
        rows = {}
        for key, (o1, o2) in (("A raw vs box", (raw, box)),
                              ("B masked vs masked box", (f2, box_m)),
                              ("C masked vs box (as registered)", (f2, box))):
            d, dm = _diff(o1, o2)
            s, o, b = int((dm == 0).sum()), int((dm == 1).sum()), int((dm > 1).sum())
            acc = pairs[key]
            acc[0] += dm.size; acc[1] += s; acc[2] += o; acc[3] += b
            rows[key] = (s, o, b)
            if key.startswith("C"):
                rgb = d[..., :3].max(-1) > 0
                aonly = (dm > 0) & ~rgb
                nn = B.R.nearest(a, ow, oh, 1.5)
                nnk = (nn[..., 0] == 255) & (nn[..., 1] == 0) & (nn[..., 2] == 255)
                c_alpha_only_key += int((aonly & nnk).sum())
                c_colour += int(rgb.sum())
        per_sheet.append((n, keyed, dm.size, rows))
    print("from2x_box vs box on %d stock sheets (%d unkeyed, %d keyed), %d output px"
          % (len(sheets), len(uk), len(kk), pairs["A raw vs box"][0]))
    fails = 0
    for key, (tot, s, o, b) in pairs.items():
        print("  %-34s identical %9.4f%%   |d|==1 %8.4f%%   |d|>1 %8.4f%%"
              % (key, 100.0 * s / tot, 100.0 * o / tot, 100.0 * b / tot))
        if key.startswith(("A", "B")) and s != tot:
            fails += 1
    tot = pairs["C masked vs box (as registered)"][0]
    print("  C split: alpha-only on nearest-key pixels %d (%.4f%%), RGB differs %d (%.4f%%)"
          % (c_alpha_only_key, 100.0 * c_alpha_only_key / tot, c_colour, 100.0 * c_colour / tot))
    diff_sheets = [r for r in per_sheet if any(v[1] or v[2] for v in r[3].values())]
    if diff_sheets:
        print("  sheets with any difference (A/B/C: |d|==1 / |d|>1):")
        for n, keyed, px, rows in diff_sheets:
            print("    %-48s %-7s px %8d  A %d/%d  B %d/%d  C %d/%d"
                  % (n, "keyed" if keyed else "unkeyed", px,
                     rows["A raw vs box"][1], rows["A raw vs box"][2],
                     rows["B masked vs masked box"][1], rows["B masked vs masked box"][2],
                     rows["C masked vs box (as registered)"][1], rows["C masked vs box (as registered)"][2]))
    else:
        print("  every sheet byte-identical at every stage")
    print("A and B: %s" % ("IDENTICAL" if fails == 0 else "FAIL (%d)" % fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    args = [int(v) for v in sys.argv[1:]]
    sys.exit(main(*args))
