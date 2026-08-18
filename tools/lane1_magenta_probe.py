"""Adversarial probe #4: is any part of the dock recess MAGENTA-KEYED or
alpha-transparent?  The patch's detector scores magenta as saturation 0, so a
keyed hole inside the rect would be invisible to it AND would be painted over
with opaque plate.  Measure it.  Uses PIL (independent of the patch's decoder).
Throwaway; read-only.
"""
import os
from collections import Counter
from PIL import Image

PROJ = r"<HOME>\OneDrive\Projects\Surface 1 Project\1 Completed Projects\SC4TouchControls"
P3 = os.path.join(PROJ, "tools", "selective-safe", "stage-3x",
                  "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png")
P1 = os.path.join(PROJ, "tools", "dbpf", "extracted", "SimCity_1",
                  "T-856ddbac_G-46a006b0_I-13d14ca0.png")

for path, (l, t, w, h), label in ((P1, (18, 71, 64, 64), "1x extract"),
                                  (P3, (54, 213, 192, 192), "3x staged")):
    im = Image.open(path).convert("RGBA")
    px = im.load()
    mag = trans = semi = grey = 0
    alphas = Counter()
    for y in range(t, t + h):
        for x in range(l, l + w):
            r, g, b, a = px[x, y]
            alphas[a] += 1
            if (r, g, b) == (255, 0, 255):
                mag += 1
            if a == 0:
                trans += 1
            elif a != 255:
                semi += 1
            if max(r, g, b) - min(r, g, b) <= 60 and (r, g, b) != (255, 0, 255):
                grey += 1
    print("%-11s rect (%d,%d) %dx%d  n=%d" % (label, l, t, w, h, w * h))
    print("   magenta key px : %d" % mag)
    print("   alpha==0 px    : %d" % trans)
    print("   0<alpha<255 px : %d" % semi)
    print("   low-sat px     : %d" % grey)
    print("   alpha histogram: %s" % dict(alphas.most_common(5)))
    # what do the flank columns look like?
    fl = 3 if "1x" in label else 9
    for band, xs in (("left flank", range(l - fl, l)),
                     ("right flank", range(l + w, l + w + fl))):
        vals = [px[x, t + h // 2] for x in xs]
        print("   %s @ mid row: %s" % (band, vals))
    # whole-sheet alpha survey
    W, H = im.size
    a0 = sum(1 for y in range(H) for x in range(W) if px[x, y][3] == 0)
    mg = sum(1 for y in range(H) for x in range(W) if px[x, y][:3] == (255, 0, 255))
    print("   WHOLE SHEET: alpha==0 %d, magenta %d, of %d px\n" % (a0, mg, W * H))
