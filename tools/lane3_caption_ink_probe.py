# -*- coding: utf-8 -*-
r"""LANE 3 probe: measure the INK BOX of the "Graphs" caption in the captures we
already have, so the caption-clip question can be decided WITHOUT the game.

The caption is GZWinText id=0x4a2871e1, font=GenHeader, forecolor=(63,73,103),
declared box 448x26 (expanded root) / 448x22 (collapsed root) at f=1.

POSITIVE CONTROL, stated because a null here would otherwise be worthless:
the scan must find a run of forecolor pixels whose WIDTH is in the ballpark of
the word "Graphs" (>= 30 design px, i.e. >= 30*f). If it finds nothing, or a
1-2 px speck, the colour key is wrong and the "no clip" reading is STRUCTURAL,
not measured - the probe says so and exits non-zero.
"""
import sys
from PIL import Image

FORE = (63, 73, 103)
TOL = 26


def inkbox(im, box, tol=TOL):
    """Bounding box of near-FORE pixels inside box=(l,t,r,b), in image coords."""
    l, t, r, b = box
    px = im.convert("RGB").crop((l, t, r, b)).load()
    W, H = r - l, b - t
    xs, ys, n = [], [], 0
    for y in range(H):
        for x in range(W):
            p = px[x, y]
            if (abs(p[0] - FORE[0]) <= tol and abs(p[1] - FORE[1]) <= tol
                    and abs(p[2] - FORE[2]) <= tol):
                xs.append(x); ys.append(y); n += 1
    if not xs:
        return None, 0
    return (l + min(xs), t + min(ys), l + max(xs) + 1, t + max(ys) + 1), n


def main():
    jobs = [
        # path, factor, search window in IMAGE coords, label
        ("_tests/captures/graphs-stock-ref.png", 1.0, None, "1x stock ref"),
        ("_tests/captures/graphs-stock-garbage.png", 1.0, None, "1x stock garbage"),
        ("_tests/captures/graphs-ours-2x.png", 2.0, None, "2x ours"),
    ]
    ok = True
    for path, f, win, label in jobs:
        im = Image.open(path)
        W, H = im.size
        # Search the whole image for the caption colour - cheap enough and it
        # avoids baking a guessed origin into the measurement.
        bb, n = inkbox(im, (0, 0, W, H))
        print("%-22s %-42s size=%s" % (label, path, (W, H)))
        if bb is None:
            print("    NO forecolor pixels found -> STRUCTURAL NULL, colour key wrong.")
            ok = False
            continue
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        print("    forecolor ink bbox=%s  %dx%d  npix=%d" % (bb, w, h, n))
        if w < 30 * f:
            print("    CONTROL FAILED: ink too narrow to be the word 'Graphs'.")
            ok = False
        else:
            print("    control ok: ink is at least word-wide.")
        print("    declared caption box at this tier: 448x26 -> %dx%d (expanded)"
              % (round(448 * f), round(26 * f)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
