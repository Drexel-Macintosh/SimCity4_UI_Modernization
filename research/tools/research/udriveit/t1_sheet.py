#!/usr/bin/env python3
r"""t1_sheet.py - #188 lane: render EVERY distinct texture used by the 310-entry
type-1 decal table into one labelled contact sheet, so the "is any type-1 decal
a blue disc with a white vehicle glyph?" question is answered by LOOKING.

Reuses extract_fsh.py's proven decoder verbatim (imported, not rewritten).
Positive control: rid 6C23BE66 must render as a dashed ring outline.
Read-only on the game. Writes t1-sheet-NN.png + t1-sheet.txt.
"""
import os, struct, sys, collections, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "uimap", "emu"))
from qfs_ab import qfs
from PIL import Image, ImageDraw

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
FSH_TYPE = 0x7AB50E44

# ---- index every archive ONCE (discovered recursively, not listed) ----
index = {}   # (type, iid) -> (dat, off, size)
dats = []
for root, dirs, files in os.walk(GAME):
    if "Plugins" in root:
        continue
    for f in files:
        if f.lower().endswith(".dat"):
            dats.append(os.path.join(root, f))
print("archives discovered: %d" % len(dats))
for d in dats:
    print("   ", d)
    with open(d, "rb") as f:
        hdr = f.read(96)
        if hdr[:4] != b"DBPF": continue
        cnt = struct.unpack_from("<I", hdr, 36)[0]
        io_ = struct.unpack_from("<I", hdr, 40)[0]
        isz = struct.unpack_from("<I", hdr, 44)[0]
        f.seek(io_); idx = f.read(isz)
        per = isz // max(cnt, 1)
        for k in range(cnt):
            t, g, i, off, size = struct.unpack_from("<5I", idx, k*per)
            if t == FSH_TYPE:
                index.setdefault((g, i), (d, off, size))
print("FSH entries indexed: %d" % len(index))

def fetch(iid):
    hits = [(g, v) for (g, i), v in index.items() if i == iid]
    if not hits: return None, None
    g, (d, off, size) = hits[0]
    with open(d, "rb") as f:
        f.seek(off); raw = f.read(size)
    out = qfs(raw)
    return (out if out else raw), (os.path.basename(d), g)

def decode(data):
    if data[:4] != b"SHPI": return []
    nent = struct.unpack_from("<I", data, 8)[0]
    imgs, pal = [], None
    ents = []
    for e in range(nent):
        tag = data[16+8*e:20+8*e].decode("ascii", "replace")
        off = struct.unpack_from("<I", data, 20+8*e)[0]
        ents.append((tag, off))
    for tag, off in ents:
        code = data[off] & 0x7F
        w, h = struct.unpack_from("<2H", data, off+4)
        p = off+16
        if code in (0x2D, 0x22, 0x24):
            n = w or 256
            raw = data[p:p+n*4]
            pal = [tuple(raw[k*4:k*4+4]) for k in range(n)]
            continue
    for tag, off in ents:
        code = data[off] & 0x7F
        w, h = struct.unpack_from("<2H", data, off+4)
        p = off+16
        img = None
        try:
            if code == 0x7D:   img = Image.frombytes("RGBA", (w,h), data[p:p+w*h*4], "raw", "BGRA")
            elif code == 0x7F: img = Image.frombytes("RGB", (w,h), data[p:p+w*h*3], "raw", "BGR").convert("RGBA")
            elif code == 0x60: img = Image.frombytes("RGBA", (w,h), data[p:p+w*h//2], "bcn", 1)
            elif code == 0x61: img = Image.frombytes("RGBA", (w,h), data[p:p+w*h], "bcn", 2)
            elif code == 0x78: img = Image.frombytes("RGB", (w,h), data[p:p+w*h*2], "raw", "BGR;16").convert("RGBA")
            elif code == 0x7B:
                pix = data[p:p+w*h]
                im = Image.frombytes("P", (w,h), pix)
                if pal:
                    flat = []
                    for c in pal[:256]: flat += [c[2], c[1], c[0]]
                    flat += [0]*(768-len(flat))
                    im.putpalette(flat)
                    a = Image.frombytes("L", (w,h), bytes(pal[b][3] if b < len(pal) else 255 for b in pix))
                    img = im.convert("RGB").convert("RGBA"); img.putalpha(a)
                else:
                    img = im.convert("RGBA")
            else:
                continue
        except Exception as ex:
            print("    decode fail code %#x %dx%d: %s" % (code, w, h, ex)); continue
        if img: imgs.append((tag, code, img))
    return imgs

# ---- rids from the type-1 table, with the entries that use them ----
T1 = re.compile(r"^\s*(\d+) @file:(0x[0-9a-f]+) rid=([0-9A-F]{8}) flags=(\S+) b8=(\d+) b9=(\d+) f0=(\S+)\s+cols=(\[.*?\])")
use = collections.OrderedDict()
for line in open(os.path.join(HERE, "type1-table.txt"), encoding="utf-8"):
    m = T1.match(line)
    if m:
        use.setdefault(m.group(3), []).append((int(m.group(1)), m.group(7), m.group(8)))

CELL, COLS = 160, 8
rows = (len(use) + COLS - 1)//COLS
sheet = Image.new("RGBA", (CELL*COLS, (CELL+34)*rows), (32,32,40,255))
dr = ImageDraw.Draw(sheet)
log = open(os.path.join(HERE, "t1-sheet.txt"), "w", encoding="utf-8")
for n, rid in enumerate(sorted(use)):
    iid = int(rid, 16)
    payload, src = fetch(iid)
    cx, cy = (n % COLS)*CELL, (n//COLS)*(CELL+34)
    label = rid
    if payload is None:
        log.write("%s: NOT FOUND in any of the %d archives\n" % (rid, len(dats)))
        dr.text((cx+4, cy+4), rid+"\nMISSING", fill=(255,80,80,255))
    else:
        imgs = decode(payload)
        log.write("%s: %s g=%08X entries=%d %s  uses=%s\n"
                  % (rid, src[0], src[1], len(imgs),
                     [(t, hex(c), im.size) for t, c, im in imgs], use[rid][:6]))
        if imgs:
            _, _, im = imgs[0]
            # checkerboard so alpha is visible
            bg = Image.new("RGBA", im.size, (0,0,0,255))
            for yy in range(0, im.size[1], 8):
                for xx in range(0, im.size[0], 8):
                    if ((xx//8)+(yy//8)) % 2 == 0:
                        bg.paste((70,70,80,255), (xx,yy,min(xx+8,im.size[0]),min(yy+8,im.size[1])))
            comp = Image.alpha_composite(bg, im.convert("RGBA"))
            s = min(CELL/comp.size[0], CELL/comp.size[1])
            comp = comp.resize((max(1,int(comp.size[0]*s)), max(1,int(comp.size[1]*s))), Image.NEAREST)
            sheet.paste(comp, (cx + (CELL-comp.size[0])//2, cy + (CELL-comp.size[1])//2))
            label = "%s %dx%d" % (rid, im.size[0], im.size[1])
    dr.rectangle([cx, cy, cx+CELL-1, cy+CELL+33], outline=(90,90,110,255))
    dr.text((cx+4, cy+CELL+2), label, fill=(255,255,255,255))
    dr.text((cx+4, cy+CELL+14), "t1 %s f0=%s" % (",".join(str(u[0]) for u in use[rid][:4]), use[rid][0][1]),
            fill=(180,220,255,255))
out = os.path.join(HERE, "t1-sheet.png")
sheet.save(out)
log.close()
print("wrote", out, sheet.size)
