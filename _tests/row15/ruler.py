"""In-frame ruler: measure a FIXED world object in both passes, so the arrow
ratio can be corrected for any framing difference between the two sessions.

The player cannot restore the camera (SC4 has no save/restore), and although
pan is free at a fixed zoom, nothing guarantees the two passes were shot at the
same zoom step just because both were called "Z5". So the arrow ratio is NOT
read raw. It is divided by the ratio of an object the probe does not touch.

Ruler chosen: the RED POWER PYLONS. They are a fixed-size world model, present
in both frames, and their saturated red is separable from the amber arrows (the
arrows carry a high green channel, the pylons do not). The probe overrides only
the connection-arrow S3D family and two UI bitmaps, so the pylon is untouched
by construction - that is what makes it a legitimate ruler rather than a second
unknown.

POSITIVE CONTROL: the pylon detector must find pylons in BOTH frames. If it
finds them in only one, no ratio is reported - a ruler that exists in one frame
measures nothing.
"""
import os, sys
from collections import deque
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "measure_arrows.py"), encoding="utf-8").read()
_g = {"__name__": "notmain"}
exec(compile(src, "measure_arrows.py", "exec"), _g)
components = _g["components"]
in_chrome = _g["in_chrome"]


def is_pylon(p):
    """Pylon red: red channel dominant, green AND blue both near-dead.

    REJECTED FIRST VERSION (2026-08-31): it tested r-g>=45 and g<110, which the
    arrows' shadowed amber rim satisfies (r=150,g=100,b=40 passes every clause).
    The "ruler" was therefore locking onto the ARROWS - the baseline's biggest
    "pylon" was (1111,623)-(1215,657), and the baseline's arrow was at
    (1149,623)-(1192,641). It returned a confident 1.854 that was pure
    circularity: the correction factor and the thing being corrected were the
    same pixels. A ruler made of the object under test measures nothing.

    The arrows are AMBER - they carry a strong green channel even in shadow.
    The pylon lattice is a near-pure red. Demanding a dead green channel is what
    separates them, and the mean-colour dump below is what proves it did.
    """
    r, g, b = p
    return r >= 105 and g <= 70 and b <= 75 and r - g >= 70


def pylons(path):
    im = Image.open(path).convert("RGB")
    cs = components(im, (0, 0, im.width, im.height), 40, is_pylon)
    cs = [c for c in cs
          if (c[3] - c[1] + 1) < im.width * 0.25
          and (c[4] - c[2] + 1) < im.height * 0.25]
    cs = [c for c in cs if not in_chrome(c, im.width, im.height)]
    return im, cs


def main(a, b):
    out = {}
    for tag, path in (("baseline", a), ("probe", b)):
        im, cs = pylons(path)
        print("\n%-9s %s" % (tag, os.path.basename(path)))
        print("  pylon blobs: %d" % len(cs))
        px = im.load()
        for n, x0, y0, x1, y1 in cs[:6]:
            # Mean colour of the blob, printed so a stray amber blob is
            # visible as amber rather than being taken on trust as red.
            rs = gs = bs = k = 0
            for yy in range(y0, y1 + 1, 2):
                for xx in range(x0, x1 + 1, 2):
                    if is_pylon(px[xx, yy]):
                        c = px[xx, yy]
                        rs += c[0]; gs += c[1]; bs += c[2]; k += 1
            k = max(k, 1)
            print("    px=%-5d (%4d,%4d)-(%4d,%4d) w=%-4d h=%-4d  mean rgb=(%d,%d,%d)"
                  % (n, x0, y0, x1, y1, x1 - x0 + 1, y1 - y0 + 1,
                     rs // k, gs // k, bs // k))
        if cs:
            hs = sorted(c[4] - c[2] + 1 for c in cs)
            out[tag] = (hs[-1], hs[len(hs) // 2], len(cs))
            print("  tallest pylon h=%d   median h=%d" % (hs[-1], hs[len(hs) // 2]))
    print()
    if len(out) < 2:
        print("REFUSING to report a ruler ratio: pylons were not found in both")
        print("frames, so there is nothing to correct against.")
        return
    print("RULER (pylon height)  baseline=%d  probe=%d  ->  zoom ratio %.3f"
          % (out["baseline"][0], out["probe"][0],
             out["probe"][0] / out["baseline"][0]))
    print()
    print("Any arrow growth must be DIVIDED by this to remove the framing")
    print("difference between the two sessions.")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
