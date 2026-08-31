"""Measure the no-power ZOT rings - the probe's role E control.

Role E multiplies every vertex position in a second 20-record S3D family by 3.0.
Its question is not about the arrow at all: "does an S3D override authored by us,
loaded from Plugins, reach the model renderer AT ALL?" If the zots grow, the
answer is yes and every negative result elsewhere in the probe becomes readable
as a real negative rather than as a delivery failure.

The zot is a RED RING with a yellow bolt. The ring is measured, not the bolt:
the ring is a closed curve so its bounding box is its diameter, whereas the bolt
is a thin diagonal whose box depends on how much of it is occluded.

RULER NOTE: zots are world-space, so their pixel size depends on zoom, and the
two passes were shot from different cameras. The raw ratio below is therefore an
UPPER bound on nothing and a lower bound on nothing until corrected. What makes
it readable anyway is the sheer margin - role E predicts x3, and a zoom step is
only x2, so even a full step of camera error cannot turn a null into a x3.
"""
import os, sys
from collections import deque
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image


def is_zot_ring(p):
    """The zot ring red: strong red, dead green and blue.

    Deliberately stricter than the arrow test on the green channel. The amber
    arrows carry a high green and must not be counted here; nor must the yellow
    bolt inside the ring, which is r-high AND g-high.
    """
    r, g, b = p
    return r >= 140 and g <= 85 and b <= 85 and r - g >= 80


def rings(path, min_px=300):
    im = Image.open(path).convert("RGB")
    w, h = im.width, im.height
    px = im.load()
    seen = bytearray(w * h)
    out = []
    for yy in range(h):
        base = yy * w
        for xx in range(w):
            if seen[base + xx] or not is_zot_ring(px[xx, yy]):
                continue
            q = deque([(xx, yy)])
            seen[base + xx] = 1
            mnx = mxx = xx
            mny = mxy = yy
            n = 0
            while q:
                cx, cy = q.popleft()
                n += 1
                if cx < mnx: mnx = cx
                if cx > mxx: mxx = cx
                if cy < mny: mny = cy
                if cy > mxy: mxy = cy
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]:
                        if is_zot_ring(px[nx, ny]):
                            seen[ny * w + nx] = 1
                            q.append((nx, ny))
            bw, bh = mxx - mnx + 1, mxy - mny + 1
            # A ring is roughly as wide as it is tall. Reject long thin streaks
            # (the red car tail-lights and the red land-value bars in the HUD).
            if n >= min_px and 0.55 <= bw / max(bh, 1) <= 1.8:
                out.append((n, mnx, mny, mxx, mxy))
    out.sort(reverse=True)
    return im, out


def main(base, probe):
    res = {}
    for tag, path in (("baseline", base), ("probe", probe)):
        im, cs = rings(path)
        # HUD sits along the bottom; zots are in the world above it.
        cs = [c for c in cs if c[2] < im.height * 0.75]
        print("\n%-9s %s" % (tag, os.path.basename(path)))
        print("  zot rings: %d   <- POSITIVE CONTROL, zero = REFUSAL" % len(cs))
        for n, x0, y0, x1, y1 in cs[:6]:
            print("    px=%-6d (%4d,%4d)-(%4d,%4d)  d=%dx%d"
                  % (n, x0, y0, x1, y1, x1 - x0 + 1, y1 - y0 + 1))
        if not cs:
            continue
        ds = sorted(max(c[3] - c[1] + 1, c[4] - c[2] + 1) for c in cs)
        res[tag] = ds[len(ds) // 2]
        print("  MEDIAN ring diameter = %d px  (n=%d)" % (res[tag], len(ds)))
    print()
    if len(res) == 2:
        print("RAW zot growth = %d / %d = %.2fx"
              % (res["probe"], res["baseline"], res["probe"] / res["baseline"]))
        print()
        print("role E predicts x3.0. One zoom step of camera error is x2.0, so")
        print("a raw ratio above ~1.5 cannot be explained by framing alone.")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
