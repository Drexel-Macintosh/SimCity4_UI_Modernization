#!/usr/bin/env python3
r"""sheet.py - render a labelled contact sheet of ranked roundel candidates.
Each cell shows the component CROP (padded), on a checkerboard so alpha is
visible, with TGI + archive + metrics burned in.
"""
import csv, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "..", "uimap", "emu"))
from qfs_ab import qfs
from PIL import Image, ImageDraw
import index_all, fshlib

G = index_all.index()
_cache = {}


def load_imgs(t, g, i):
    k = (t, g, i)
    if k in _cache:
        return _cache[k]
    hit = G["by_tgi"].get(k)
    if not hit:
        _cache[k] = []
        return []
    p, o, s = hit
    with open(p, "rb") as f:
        f.seek(o); raw = f.read(s)
    try:
        if t == 0x856DDBAC:
            d = raw if raw[:4] == b"\x89PNG" else (qfs(raw) or raw)
            out = [("png", Image.open(io.BytesIO(d)).convert("RGBA"))]
        else:
            d = qfs(raw) or raw
            out = fshlib.decode_fsh(d)
    except Exception:
        out = []
    _cache[k] = out
    return out


def checker(size):
    ck = Image.new("RGBA", size, (255, 255, 255, 255))
    d = ImageDraw.Draw(ck)
    for y in range(0, size[1], 8):
        for x in range(0, size[0], 8):
            if ((x // 8) + (y // 8)) % 2:
                d.rectangle([x, y, x + 7, y + 7], fill=(185, 185, 195, 255))
    return ck


def render(rows, out, cols=10, cell=132, note=""):
    n = len(rows)
    rws = (n + cols - 1) // cols
    TXT = 34
    sh = Image.new("RGBA", (cols * cell, rws * (cell + TXT) + 22), (28, 28, 34, 255))
    dr = ImageDraw.Draw(sh)
    dr.text((6, 6), note, fill=(255, 255, 255, 255))
    for k, r in enumerate(rows):
        cx = (k % cols) * cell
        cy = (k // cols) * (cell + TXT) + 22
        t = int(r["type"], 16); g = int(r["group"], 16); i = int(r["inst"], 16)
        imgs = load_imgs(t, g, i)
        e = int(r["entry"])
        if e < len(imgs):
            im = imgs[e][1]
            x0, y0 = int(r["bx"]), int(r["by"])
            bw, bh = int(r["bw"]), int(r["bh"])
            pad = 3
            crop = im.crop((max(0, x0 - pad), max(0, y0 - pad),
                            min(im.width, x0 + bw + pad), min(im.height, y0 + bh + pad)))
            sc = max(1, min(6, (cell - 8) // max(1, max(crop.size))))
            crop = crop.resize((crop.width * sc, crop.height * sc), Image.NEAREST)
            if max(crop.size) > cell - 8:
                crop.thumbnail((cell - 8, cell - 8), Image.NEAREST)
            ck = checker(crop.size); ck.alpha_composite(crop)
            sh.paste(ck, (cx + (cell - ck.width) // 2, cy + (cell - ck.height) // 2))
        dr.rectangle([cx, cy, cx + cell - 1, cy + cell + TXT - 1], outline=(70, 70, 80, 255))
        dr.text((cx + 3, cy + cell + 1), "#%s %s" % (r.get("trank", "?"), r["inst"]), fill=(255, 235, 150, 255))
        dr.text((cx + 3, cy + cell + 11), "G%s %s" % (r["group"][:8], r["archive"][:13]), fill=(150, 210, 255, 255))
        dr.text((cx + 3, cy + cell + 21), "rs%.2f h%.2f g%.2f %dx%d" % (
            float(r["rs"]), float(r["hole"]), float(r["gblob"]), int(r["bw"]), int(r["bh"])), fill=(190, 190, 190, 255))
    sh.save(out)
    print("wrote", out, sh.size)
