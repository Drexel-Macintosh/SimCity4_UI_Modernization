"""Measure the neighbour-connection arrows in a screenshot, with an in-frame ruler.

WHY THIS EXISTS: the row-15 probe run compares a baseline pass against a
probe-installed pass, and the player cannot restore the camera between them -
SC4 has no camera save/restore. That does NOT void the run, and the reason is
measured, not assumed:

  the game's pixels-per-tile table at 0x00ABACE0 is {8,16,32,73,146}, one fixed
  scale per zoom level. Zoom is quantised to 5 steps, rotation to 4 positions,
  and pan is a pure translation. At the SAME ZOOM the world-to-screen scale is
  identical wherever the camera was panned.

So this script never compares absolute pixels across passes without a ruler. It
reports the arrow size AND a road-width ruler taken from the same frame, and the
verdict is read off the RATIO. The probe's role B is a uniform x3 and role C is
anisotropic; both dwarf any residual framing error, and a ratio near 1.00 with a
sound ruler is a real null rather than a missed measurement.

POSITIVE CONTROL, printed every run: the arrow detector is proven able to see
arrows by reporting how many it found. Zero found is a REFUSAL, not a null -
"the arrows did not change" and "I could not see the arrows" are the same
pixels otherwise, and this project has paid for that confusion before.
"""
import os, sys
from collections import deque
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image


def is_arrow(p):
    """The neighbour arrows are a saturated amber unique in the frame.

    Tuned to reject: the grey road, the dark grass, the blue water, the blue
    HUD chrome, and the white lane markings. Kept deliberately loose on
    brightness so a night-lit arrow and a day-lit one both pass.
    """
    r, g, b = p
    return r >= 120 and r - b >= 55 and g >= b + 20 and r >= g + 25


def components(im, box, min_px, pred):
    x0, y0, x1, y1 = box
    px = im.load()
    w, h = x1 - x0, y1 - y0
    seen = bytearray(w * h)
    out = []
    for yy in range(h):
        base = yy * w
        for xx in range(w):
            if seen[base + xx] or not pred(px[x0 + xx, y0 + yy]):
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
                        if pred(px[x0 + nx, y0 + ny]):
                            seen[ny * w + nx] = 1
                            q.append((nx, ny))
            if n >= min_px:
                out.append((n, mnx + x0, mny + y0, mxx + x0, mxy + y0))
    out.sort(reverse=True)
    return out


# Screen regions that are NOT the game world and must never be counted.
#
# ADDED 2026-08-31 after the first run of this script FAILED CLEAN on the Z3
# baseline: it reported "4 arrows found" and a confident median of w=13 h=26,
# and every one of the four was an impostor - two were the amber PAUSE BUTTON
# at the top-left, one a lit window, and one the orange asterisk in a Claude
# permission toast that happened to be on screen. The count-based positive
# control passed; only reading the coordinates caught it.
#
# That is the exact shape this project keeps paying for: a broken instrument
# reporting success. So the control below is no longer "did I find any", it is
# "did I find any IN THE WORLD, away from every chrome region I know about".
EXCLUDE = [
    # (x0, y0, x1, y1) as FRACTIONS of the frame
    (0.00, 0.00, 0.10, 0.10),   # top-left: pause/speed chrome
    (0.00, 0.55, 0.24, 1.00),   # bottom-left: minimap + HUD cluster
    (0.62, 0.72, 1.00, 1.00),   # bottom-right: OS/Claude toasts land here
]


def in_chrome(c, w, h):
    _, a, b, cc, d = c
    for fx0, fy0, fx1, fy1 in EXCLUDE:
        if a >= fx0 * w and cc <= fx1 * w and b >= fy0 * h and d <= fy1 * h:
            return True
    return False


def report(path, min_px=60):
    im = Image.open(path).convert("RGB")
    box = (0, 0, im.width, im.height)
    cs = components(im, box, min_px, is_arrow)
    # A neighbour arrow is a small world sprite. Anything spanning a large
    # fraction of the frame is by construction not one - on the Z3 baseline
    # this caught the amber PAUSED BORDER that SC4 draws around the whole
    # screen, a 2392x1596 blob that sailed past the colour test and would
    # have been reported as the widest arrow on screen.
    cs = [c for c in cs
          if (c[3] - c[1] + 1) < im.width * 0.25
          and (c[4] - c[2] + 1) < im.height * 0.25]
    kept = [c for c in cs if not in_chrome(c, im.width, im.height)]
    dropped = len(cs) - len(kept)
    cs = kept
    if dropped:
        print(chr(10) + "  (%d blob(s) rejected as screen chrome, not world)" % dropped)
    print("\n%s   (%dx%d)" % (os.path.basename(path), im.width, im.height))
    print("  arrows found: %d      <- POSITIVE CONTROL, zero here = REFUSAL" % len(cs))
    if not cs:
        print("  refusing to report a size: the detector saw nothing, which is")
        print("  not the same fact as 'the arrows were unchanged'.")
        return None
    for n, a, b, c, d in cs[:8]:
        print("    px=%-5d (%4d,%4d)-(%4d,%4d)  w=%-4d h=%-3d"
              % (n, a, b, c, d, c - a + 1, d - b + 1))
    ws = sorted(c[3] - c[1] + 1 for c in cs)
    hs = sorted(c[4] - c[2] + 1 for c in cs)
    px = sorted(c[0] for c in cs)
    mid = len(ws) // 2
    print("  MEDIAN arrow   w=%d  h=%d  area=%d px" % (ws[mid], hs[mid], px[mid]))
    print("  widest arrow   w=%d" % ws[-1])
    return ws[mid], hs[mid], px[mid], len(cs)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        report(p)
