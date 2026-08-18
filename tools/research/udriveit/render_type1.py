#!/usr/bin/env python3
r"""render_type1.py - decode EVERY distinct FSH backing the 310 type-1 decal
entries and build two contact sheets (raw + runtime-tinted).

Reuses:
  extract_fsh.decode_fsh   (proven FSH decoder; PNG side-effect is fine)
  index_all.index          (one-pass global DBPF index, cached)

POSITIVE CONTROL: entry 268 rid=6C23BE66 must render as a RING OUTLINE.
If it does not, the decoder path is wrong and every verdict below is void.

Outputs (next to this script):
  type1-contactsheet.png          raw texture on dark ground
  type1-contactsheet-tinted.png   same, cols[0] multiplied in
  type1-render-log.txt            per-rid decode result
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))

_argv = sys.argv
sys.argv = [_argv[0]]                     # extract_fsh runs a loop on argv
import extract_fsh as EF                                          # noqa: E402
sys.argv = _argv

from index_all import index, T_FSH                                # noqa: E402
from PIL import Image, ImageDraw, ImageFont                       # noqa: E402

TABLE = os.path.join(HERE, "type1-table.txt")
BG = (18, 18, 24, 255)
CELL_BG = (34, 34, 42, 255)
TILE = 96
LABEL = 30
COLS = 14

ROW_RE = re.compile(
    r"^\s*(\d+) @file:0x([0-9a-f]+) rid=([0-9A-F]{8}) flags=0x([0-9a-f]+) "
    r"b8=(\d+) b9=(\d+) f0=(\S+)\s+cols=\[(.*?)\] tail=\((.*?)\)")


def parse_table():
    rows = []
    for line in open(TABLE, encoding="utf-8"):
        m = ROW_RE.match(line)
        if not m:
            continue
        cols = []
        for c in re.findall(r"\(([^)]*)\)", m.group(8)):
            cols.append(tuple(float(x) for x in c.split(",")))
        rows.append(dict(idx=int(m.group(1)), off=m.group(2),
                         rid=int(m.group(3), 16), flags=int(m.group(4), 16),
                         b8=int(m.group(5)), b9=int(m.group(6)),
                         f0=m.group(7), cols=cols))
    return rows


def font(sz):
    for p in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def load_payload(iid, g):
    hits = g["by_ti"].get((T_FSH, iid))
    if not hits:
        return None, None
    grp, path, off, sz = hits[0]
    for h in hits:                        # prefer the effects group
        if h[0] == 0x1ABE787D:
            grp, path, off, sz = h
            break
    with open(path, "rb") as fh:
        fh.seek(off)
        raw = fh.read(sz)
    out = EF.qfs(raw)
    return (out if out else raw), (os.path.basename(path), grp)


def decode(iid, g, log):
    payload, src = load_payload(iid, g)
    if payload is None:
        log.append("%08X: NOT FOUND in any archive" % iid)
        return None
    try:
        outs = EF.decode_fsh(payload, iid)
    except Exception as ex:
        log.append("%08X: DECODE FAILED %s (%s)" % (iid, ex, src[0]))
        return None
    if not outs:
        log.append("%08X: no decodable entries (%s)" % (iid, src[0]))
        return None
    im = Image.open(outs[0])
    im.load()
    if im.mode == "P":                    # palette entry lives elsewhere in FSH
        im = palette_fix(payload, im)
    im = im.convert("RGBA")
    log.append("%08X: OK %dx%d %s (%s G=%08X)"
               % (iid, im.width, im.height, im.mode, src[0], src[1]))
    return im


def palette_fix(data, img):
    """Find a palette entry (code 0x2D/0x22/0x24) in the SHPI and apply it."""
    import struct
    nent = struct.unpack_from("<I", data, 8)[0]
    for e in range(nent):
        off = struct.unpack_from("<I", data, 20 + 8 * e)[0]
        code = data[off] & 0x7F
        if code in (0x2D, 0x22, 0x24):
            n = struct.unpack_from("<H", data, off + 4)[0]
            p = off + 16
            pal = []
            for k in range(min(n, 256)):
                b, gg, r, _a = data[p + k * 4: p + k * 4 + 4]
                pal += [r, gg, b]
            pal += [0] * (768 - len(pal))
            img.putpalette(pal)
            return img.convert("RGB")
    return img


def on_dark(im, tint=None, box=TILE - 6):
    cell = Image.new("RGBA", (box, box), CELL_BG)
    s = im.copy()
    if tint:
        px = s.load()
        for y in range(s.height):
            for x in range(s.width):
                r, gg, b, a = px[x, y]
                px[x, y] = (int(r * tint[0]), int(gg * tint[1]),
                            int(b * tint[2]), a)
    if max(s.size) < box:                 # ENLARGE small textures (32x32 etc.)
        k = box // max(s.size)
        s = s.resize((s.width * k, s.height * k), Image.NEAREST)
    s.thumbnail((box, box), Image.LANCZOS)
    cell.alpha_composite(s, ((box - s.width) // 2, (box - s.height) // 2))
    return cell


def build(rows, cache, path, tinted, title):
    f_lab = font(10)
    f_hdr = font(18)
    n = len(rows)
    cols = min(COLS, max(1, n))
    rn = (n + cols - 1) // cols
    W = cols * (TILE + 8) + 8
    H = 44 + rn * (TILE + LABEL + 8) + 8
    sheet = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((10, 12), title, font=f_hdr, fill=(235, 235, 245, 255))
    for k, r in enumerate(rows):
        cx = 8 + (k % cols) * (TILE + 8)
        cy = 44 + (k // cols) * (TILE + LABEL + 8)
        im = cache.get(r["rid"])
        cell = Image.new("RGBA", (TILE, TILE), CELL_BG)
        if im is not None:
            t = (r["cols"][0] if (tinted and r["cols"]) else None)
            cell.alpha_composite(on_dark(im, t), (3, 3))
        else:
            d.text((cx + 6, cy + 40), "no tex", font=f_lab, fill=(200, 90, 90, 255))
        sheet.alpha_composite(cell, (cx, cy))
        d.rectangle([cx, cy, cx + TILE - 1, cy + TILE - 1], outline=(70, 70, 84, 255))
        d.text((cx + 1, cy + TILE + 1), "%d %08X" % (r["idx"], r["rid"]),
               font=f_lab, fill=(225, 225, 238, 255))
        c = r["cols"][0] if r["cols"] else (1, 1, 1)
        d.text((cx + 1, cy + TILE + 12), "f0=%s" % r["f0"][:8],
               font=f_lab, fill=(150, 190, 235, 255))
        d.text((cx + 1, cy + TILE + 21),
               "%.1f,%.1f,%.1f" % c, font=f_lab,
               fill=(int(80 + 175 * c[0]), int(80 + 175 * c[1]), int(80 + 175 * c[2]), 255))
    sheet.convert("RGB").save(path)
    print("wrote %s (%d tiles, %d cols)" % (path, n, cols))


def main():
    rows = parse_table()
    rids = sorted({r["rid"] for r in rows})
    print("parsed %d type-1 entries, %d distinct rids" % (len(rows), len(rids)))
    g = index()
    log = []
    cache = {}
    ok = fail = 0
    for iid in rids:
        if iid == 0:
            log.append("00000000: null rid (no texture)")
            continue
        im = decode(iid, g, log)
        if im is None:
            fail += 1
        else:
            ok += 1
            cache[iid] = im
    print("decoded %d / %d distinct textures (%d failed)" % (ok, len(rids), fail))
    with open(os.path.join(HERE, "type1-render-log.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    build(rows, cache, os.path.join(HERE, "type1-contactsheet.png"), False,
          "TYPE-1 DECALS - RAW texture on dark ground (%d entries, %d distinct FSH)"
          % (len(rows), len(rids)))
    build(rows, cache, os.path.join(HERE, "type1-contactsheet-tinted.png"), True,
          "TYPE-1 DECALS - RUNTIME TINT cols[0] multiplied (%d entries)" % len(rows))


if __name__ == "__main__":
    main()
