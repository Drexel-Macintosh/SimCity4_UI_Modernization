#!/usr/bin/env python3
r"""Build the blue-disc contact sheet + text index from family-pixels.tsv.

    python contact_sheet.py                 # survivors of the blue+white filter
    python contact_sheet.py --all-markers   # every UI/Zot/Tag-shaped member,
                                            # colour-blind (the widened pass)
    python contact_sheet.py --chunks        # also emit viewable 40-tile pages

Each tile is composited on a dark ground so alpha and colour-key areas read.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from PIL import Image, ImageDraw, ImageFont                     # noqa: E402
from index_all import index                                     # noqa: E402
import render_family as RF                                      # noqa: E402

TSV = os.path.join(HERE, "family-pixels.tsv")
SHEET = os.path.join(HERE, "blue-disc-candidates.png")
INDEX = os.path.join(HERE, "blue-disc-candidates.txt")
BG = (18, 18, 24, 255)
TILE = 108
LABEL = 26
COLS = 10


def font(sz):
    for p in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def sprite_for(r, by_ti):
    im = RF.atlas(int(r["tex"], 16), by_ti)
    if im is None:
        return None
    sp, _rect, _c = RF.crop_sprite(im, r)
    return sp


def build(rows, sheet_path, index_path, title):
    g = index()
    by_ti = g["by_ti"]
    f_lab = font(11)
    f_hdr = font(18)
    n = len(rows)
    cols = min(COLS, max(1, n))
    rowsn = (n + cols - 1) // cols
    W = cols * (TILE + 8) + 8
    H = 44 + rowsn * (TILE + LABEL + 8) + 8
    sheet = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((10, 12), title, font=f_hdr, fill=(235, 235, 245, 255))

    lines = []
    for k, r in enumerate(rows):
        cx = 8 + (k % cols) * (TILE + 8)
        cy = 44 + (k // cols) * (TILE + LABEL + 8)
        cell = Image.new("RGBA", (TILE, TILE), (34, 34, 42, 255))
        sp = sprite_for(r, by_ti)
        if sp is not None:
            s = sp.copy()
            s.thumbnail((TILE - 6, TILE - 6),
                        Image.NEAREST if max(s.size) < TILE else Image.LANCZOS)
            cell.alpha_composite(s, ((TILE - s.width) // 2, (TILE - s.height) // 2))
        sheet.alpha_composite(cell, (cx, cy))
        d.rectangle([cx, cy, cx + TILE - 1, cy + TILE - 1], outline=(70, 70, 84, 255))
        nm = r["name"] or "(unnamed)"
        d.text((cx + 1, cy + TILE + 1), nm[:20], font=f_lab, fill=(220, 220, 232, 255))
        d.text((cx + 1, cy + TILE + 13),
               "I=%s F=%s" % (r["ex_inst"][:8], r["tex"][:8]),
               font=f_lab, fill=(150, 190, 235, 255))
        lines.append("%3d  %-46s I=0x%s  model=0x%s  FSH=0x%s  %sx%s  "
                     "blue=%.3f white=%.3f red=%.3f  %s"
                     % (k + 1, nm[:46], r["ex_inst"], r["model"], r["tex"],
                        r["w"], r["h"], float(r["blue"]), float(r["white"]),
                        float(r["red"]), r["archive"]))
    sheet.convert("RGB").save(sheet_path)
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(title + "\n")
        fh.write("exemplar type 0x6534284A, group 0xC977C536\n")
        fh.write("tile order = rank order in the sheet, left-to-right\n\n")
        fh.write("\n".join(lines) + "\n")
    print("wrote %s  (%d tiles)" % (sheet_path, n))
    print("wrote %s" % index_path)
    return sheet


def chunks(rows, tag):
    g = index()
    by_ti = g["by_ti"]
    f_lab = font(12)
    per = 40
    outs = []
    for c0 in range(0, len(rows), per):
        part = rows[c0:c0 + per]
        cols = 8
        rowsn = (len(part) + cols - 1) // cols
        T = 124
        W = cols * (T + 6) + 6
        H = rowsn * (T + 24 + 6) + 6
        im = Image.new("RGBA", (W, H), BG)
        d = ImageDraw.Draw(im)
        for k, r in enumerate(part):
            cx = 6 + (k % cols) * (T + 6)
            cy = 6 + (k // cols) * (T + 30)
            cell = Image.new("RGBA", (T, T), (34, 34, 42, 255))
            sp = sprite_for(r, by_ti)
            if sp is not None:
                s = sp.copy()
                s.thumbnail((T - 6, T - 6),
                            Image.NEAREST if max(s.size) < T else Image.LANCZOS)
                cell.alpha_composite(s, ((T - s.width) // 2, (T - s.height) // 2))
            im.alpha_composite(cell, (cx, cy))
            d.text((cx + 1, cy + T + 2), "#%d %s" % (c0 + k + 1, (r["name"] or "?")[:17]),
                   font=f_lab, fill=(225, 225, 238, 255))
        p = os.path.join(HERE, "chunk-%s-%02d.png" % (tag, c0 // per))
        im.convert("RGB").save(p)
        outs.append(p)
    print("chunks: %s" % ", ".join(os.path.basename(o) for o in outs))
    return outs


def main():
    rows = list(csv.DictReader(open(TSV, encoding="utf-8"), delimiter="\t"))
    keep = [r for r in rows if int(r["vis"]) >= RF.MIN_VIS
            and float(r["blue"]) >= RF.KEEP_BLUE
            and float(r["white"]) >= RF.KEEP_WHITE]
    keep.sort(key=lambda r: -(float(r["blue"]) * 2 + float(r["white"])))
    build(keep, SHEET, INDEX,
          "BLUE-DISC CANDIDATES  -  %d of %d marker-family sprites survived "
          "blue>=%.2f AND white>=%.2f" % (len(keep), len(rows),
                                          RF.KEEP_BLUE, RF.KEEP_WHITE))
    if "--chunks" in sys.argv:
        chunks(keep, "blue")


if __name__ == "__main__":
    main()
