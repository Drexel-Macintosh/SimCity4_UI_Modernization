"""GH5 prototype: x3 NEAREST -> 2:1 BOX  (net 1.5x), key-aware.

WHY THIS SHAPE. A direct x1.5 resample must distribute one extra pixel per two,
which no arrangement makes even - that is the arithmetic reason 1.5x looks
softer/lumpier than 2x and 3x. Going x3 first is LOSSLESS (an exact 3x3 block
replicate; nearest only ever COPIES, so the FF00FF colour key survives
byte-perfect), and the following reduction is an INTEGER 2:1, so every output
pixel is the mean of exactly four source pixels - even weighting by
construction.

KEY HANDLING, and the #175 lesson baked in. --hq failed because Graphics.DrawImage
averaged an exact FF00FF with its neighbours, produced 0xFE01FE, the engine's key
test missed it and the key DREW (pink). And the #175 second half failed for the
MIRROR reason: a belt-and-braces line nudged a legitimately-key result off the key
(FF00FF -> FF01FF), which the key test also missed, and it drew pink again. So:

  * key pixels contribute ZERO to the average (never enter it),
  * each output pixel divides by the coverage it actually accumulated,
  * a pixel with less than half coverage is re-emitted as an EXACT FF00FF,
  * and NOTHING nudges an exact key off the key afterwards.

Both failure modes are the same bug wearing different clothes: a pixel that is
ALMOST the key. The gate below therefore scans for near-key pixels, which is the
one measurement that would have caught either.
"""
import os
import sys
import struct
from collections import Counter

from PIL import Image

KEY = (255, 0, 255)


def near_key(px):
    """A pixel that is close to the key but not exactly it - the failure signature."""
    r, g, b = px[0], px[1], px[2]
    if (r, g, b) == KEY:
        return False
    return abs(r - 255) <= 12 and abs(g - 0) <= 12 and abs(b - 255) <= 12


def has_key(im):
    return any(p[:3] == KEY for p in im.convert("RGBA").getdata())


def nn(im, f):
    w, h = im.size
    return im.resize((int(w * f + 0.5), int(h * f + 0.5)), Image.NEAREST)


def supersample_15x(im):
    """x3 nearest (lossless), then a key-aware 2:1 box reduction."""
    im = im.convert("RGBA")
    w, h = im.size
    big = im.resize((w * 3, h * 3), Image.NEAREST)   # lossless block replicate
    bw, bh = big.size
    ow, oh = (bw + 1) // 2, (bh + 1) // 2
    src = big.load()
    out = Image.new("RGBA", (ow, oh))
    dst = out.load()
    for y in range(oh):
        for x in range(ow):
            rs = gs = bs = as_ = 0
            n = 0
            total = 0
            for dy in (0, 1):
                for dx in (0, 1):
                    sx, sy = x * 2 + dx, y * 2 + dy
                    if sx >= bw or sy >= bh:
                        continue
                    total += 1
                    p = src[sx, sy]
                    if p[:3] == KEY:
                        continue          # key contributes NOTHING to the average
                    rs += p[0]; gs += p[1]; bs += p[2]; as_ += p[3]
                    n += 1
            if total == 0 or n * 2 < total:
                dst[x, y] = (255, 0, 255, 255)     # EXACT key, never nudged
            else:
                dst[x, y] = (rs // n, gs // n, bs // n, as_ // n)
    return out


def runs_along_row(im, row):
    """Run lengths of constant colour along one row - the stroke-width metric."""
    px = im.convert("RGBA").load()
    w, h = im.size
    if row >= h:
        return []
    out, cur, prev = [], 0, None
    for x in range(w):
        p = px[x, row]
        if p == prev:
            cur += 1
        else:
            if prev is not None:
                out.append(cur)
            cur, prev = 1, p
    out.append(cur)
    return out


def report(path, label):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    keyed = has_key(im)
    a = nn(im, 1.5)
    b = supersample_15x(im)
    row1x = h // 2
    r_src = runs_along_row(im, row1x)
    r_nn = runs_along_row(a, int(row1x * 1.5))
    r_ss = runs_along_row(b, int(row1x * 1.5))

    def spread(rs):
        rs = [r for r in rs if r > 0]
        if not rs:
            return 0.0, Counter()
        m = sum(rs) / len(rs)
        var = sum((r - m) ** 2 for r in rs) / len(rs)
        return var ** 0.5, Counter(rs)

    s_src, c_src = spread(r_src)
    s_nn, c_nn = spread(r_nn)
    s_ss, c_ss = spread(r_ss)
    nk_nn = sum(1 for p in a.getdata() if near_key(p))
    nk_ss = sum(1 for p in b.getdata() if near_key(p))
    k_src = sum(1 for p in im.getdata() if p[:3] == KEY)
    k_nn = sum(1 for p in a.getdata() if p[:3] == KEY)
    k_ss = sum(1 for p in b.getdata() if p[:3] == KEY)
    print(f"\n=== {label}  {w}x{h}  keyed={keyed} ===")
    print(f"  size      NN {a.size}   SS {b.size}   {'MATCH' if a.size == b.size else '*** DIFFER ***'}")
    print(f"  run-length sd (lower = more even strokes)")
    print(f"      1x source {s_src:6.3f}   most common {c_src.most_common(4)}")
    print(f"      NN  1.5x  {s_nn:6.3f}   most common {c_nn.most_common(4)}")
    print(f"      SS  1.5x  {s_ss:6.3f}   most common {c_ss.most_common(4)}")
    print(f"  key pixels  1x {k_src}   NN {k_nn}   SS {k_ss}")
    print(f"  NEAR-KEY (the pink bug)  NN {nk_nn}   SS {nk_ss}   "
          f"{'OK' if nk_ss == 0 else '*** SS LEAKS NEAR-KEY ***'}")
    return nk_ss


if __name__ == "__main__":
    bad = 0
    for p in sys.argv[1:]:
        bad += report(p, os.path.basename(p))
    print(f"\nTOTAL near-key pixels emitted by the supersampler: {bad}")
    print("PASS - no near-key leak" if bad == 0 else "FAIL - would repeat the #143/#175 pink bug")
