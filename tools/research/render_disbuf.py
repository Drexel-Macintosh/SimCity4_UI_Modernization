#!/usr/bin/env python3
"""render_disbuf.py - render the DISBUFDUMP container-buffer dumps
(SC4UIScale-disbuf*.bin, written beside the DLL by the 2026-08-23 disaster
seam investigation) to PNGs, three ways:

  <name>-rgb.png     the raw BGRA colour channels (alpha ignored)
  <name>-alpha.png   the alpha channel as grayscale
  <name>-navy.png    the buffer alpha-composited over a flat navy backdrop
                     (what the flyout SHOULD look like when it sits on the
                     god sidebar panel)
  <name>-grass.png   composited over a flat bright green (what it looks
                     like hanging over lit terrain)

If -navy looks correct/fused and -grass shows the reported bright seam,
the buffer is proven right and the on-screen defect is the BACKDROP (the
2x flyout extending past the navy sidebar panel), not the compositing.

Usage: python render_disbuf.py <path-to-disbuf.bin> [more .bin files]
Requires Pillow (pip install Pillow).
"""
import struct
import sys
import os

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow required: pip install Pillow")

NAVY = (43, 49, 88)      # approximate god-sidebar navy
GRASS = (118, 176, 90)   # approximate lit-terrain green


def render(path):
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"DBUF":
            print(f"{path}: bad magic {magic!r}, skipped")
            return
        w, h, stride = struct.unpack("<iii", f.read(12))
        data = f.read(w * h * 4)
    if len(data) < w * h * 4:
        print(f"{path}: truncated ({len(data)} bytes for {w}x{h}), skipped")
        return
    base = os.path.splitext(path)[0]

    rgb = Image.new("RGB", (w, h))
    alpha = Image.new("L", (w, h))
    over_navy = Image.new("RGB", (w, h))
    over_grass = Image.new("RGB", (w, h))
    prgb = rgb.load()
    pa = alpha.load()
    pn = over_navy.load()
    pg = over_grass.load()
    for y in range(h):
        row = y * w * 4
        for x in range(w):
            i = row + x * 4
            b, g, r, a = data[i], data[i + 1], data[i + 2], data[i + 3]
            prgb[x, y] = (r, g, b)
            pa[x, y] = a
            pn[x, y] = tuple(
                (c * a + bg * (255 - a) + 127) // 255
                for c, bg in zip((r, g, b), NAVY))
            pg[x, y] = tuple(
                (c * a + bg * (255 - a) + 127) // 255
                for c, bg in zip((r, g, b), GRASS))
    rgb.save(base + "-rgb.png")
    alpha.save(base + "-alpha.png")
    over_navy.save(base + "-navy.png")
    over_grass.save(base + "-grass.png")
    print(f"{path}: {w}x{h} -> {base}-{{rgb,alpha,navy,grass}}.png")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        render(p)
