#!/usr/bin/env python3
r"""Large per-DISTINCT-TEXTURE sheet for the type-1 decals, so glyphs are
legible (the 310-tile sheet is for the record; this is for LOOKING).
Also dumps each distinct texture at native size to type1-tex/.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_type1 as RT                                         # noqa: E402
from index_all import index                                       # noqa: E402
from PIL import Image, ImageDraw                                  # noqa: E402

OUT = os.path.join(HERE, "type1-tex")
T = 200
LAB = 34
COLS = 8


def main():
    rows = RT.parse_table()
    os.makedirs(OUT, exist_ok=True)
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
            im.save(os.path.join(OUT, "tex-%08X.png" % iid))
    n = len(rids)
    rn = (n + COLS - 1) // COLS
    W = COLS * (T + 8) + 8
    H = 40 + rn * (T + LAB + 8) + 8
    sheet = Image.new("RGBA", (W, H), RT.BG)
    d = ImageDraw.Draw(sheet)
    f = RT.font(13)
    d.text((10, 10), "TYPE-1 DECALS - %d DISTINCT TEXTURES (raw, on dark)" % n,
           font=RT.font(20), fill=(235, 235, 245, 255))
    for k, iid in enumerate(rids):
        cx = 8 + (k % COLS) * (T + 8)
        cy = 40 + (k // COLS) * (T + LAB + 8)
        cell = Image.new("RGBA", (T, T), RT.CELL_BG)
        im = cache.get(iid)
        if im is not None:
            cell.alpha_composite(RT.on_dark(im, None, T - 6), (3, 3))
        else:
            d.text((cx + 10, cy + 90), "MISSING", font=f, fill=(220, 90, 90, 255))
        sheet.alpha_composite(cell, (cx, cy))
        d.rectangle([cx, cy, cx + T - 1, cy + T - 1], outline=(70, 70, 84, 255))
        ent = use[iid]
        d.text((cx + 2, cy + T + 2), "%08X  x%d" % (iid, len(ent)),
               font=f, fill=(235, 235, 245, 255))
        d.text((cx + 2, cy + T + 17),
               "e:" + ",".join(str(e["idx"]) for e in ent[:9]),
               font=f, fill=(150, 190, 235, 255))
    p = os.path.join(HERE, "type1-distinct-rids.png")
    sheet.convert("RGB").save(p)
    print("wrote", p, n, "tiles")
    for iid in rids:
        ent = use[iid]
        print("%08X used by %d entries: %s" % (iid, len(ent),
              ",".join(str(e["idx"]) for e in ent)))


if __name__ == "__main__":
    main()
