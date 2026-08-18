#!/usr/bin/env python3
r"""Contrast/alpha-BOOSTED view of the 58 distinct type-1 textures.

WHY: a faint low-alpha glyph inside an otherwise plain disc would be invisible
on the plain dark composite. This normalises alpha AND luminance per texture so
any hidden shape has to show itself. Also prints alpha statistics.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_type1 as RT                                         # noqa: E402
from index_all import index                                       # noqa: E402
from PIL import Image, ImageDraw, ImageOps                        # noqa: E402

T = 200
COLS = 8
LAB = 30


def boost(im):
    r, g, b, a = im.split()
    a2 = ImageOps.autocontrast(a, cutoff=0)
    rgb = ImageOps.autocontrast(Image.merge("RGB", (r, g, b)), cutoff=0)
    return Image.merge("RGBA", rgb.split() + (a2,))


def main():
    rows = RT.parse_table()
    use = {}
    for r in rows:
        use.setdefault(r["rid"], []).append(r)
    rids = sorted(k for k in use if k)
    g = index()
    log = []
    cache = {}
    for iid in rids:
        im = RT.decode(iid, g, log)
        if im is not None:
            cache[iid] = im
    n = len(rids)
    rn = (n + COLS - 1) // COLS
    sheet = Image.new("RGBA", (COLS * (T + 8) + 8, 40 + rn * (T + LAB + 8) + 8),
                      RT.BG)
    d = ImageDraw.Draw(sheet)
    f = RT.font(13)
    d.text((10, 10), "TYPE-1 DECALS - ALPHA+LUMA BOOSTED (hidden-glyph hunt)",
           font=RT.font(20), fill=(235, 235, 245, 255))
    print("%-10s %6s %8s %8s %8s" % ("rid", "size", "a_min", "a_max", "a_mean"))
    for k, iid in enumerate(rids):
        cx = 8 + (k % COLS) * (T + 8)
        cy = 40 + (k // COLS) * (T + LAB + 8)
        cell = Image.new("RGBA", (T, T), RT.CELL_BG)
        im = cache.get(iid)
        if im is not None:
            a = im.split()[3]
            ex = a.getextrema()
            mean = sum(a.getdata()) / float(a.width * a.height)
            print("%08X   %3dx%-3d %8d %8d %8.1f"
                  % (iid, im.width, im.height, ex[0], ex[1], mean))
            cell.alpha_composite(RT.on_dark(boost(im), None, T - 6), (3, 3))
        sheet.alpha_composite(cell, (cx, cy))
        d.rectangle([cx, cy, cx + T - 1, cy + T - 1], outline=(70, 70, 84, 255))
        d.text((cx + 2, cy + T + 3), "%08X x%d" % (iid, len(use[iid])),
               font=f, fill=(235, 235, 245, 255))
    p = os.path.join(HERE, "type1-boosted.png")
    sheet.convert("RGB").save(p)
    print("wrote", p)


if __name__ == "__main__":
    main()
