#!/usr/bin/env python3
r"""extract_fsh.py - #188: pull FSH textures by instance id from any shipped
archive (discovered, not listed), QFS-decompress, decode to PNG with Pillow.

Decodes the SC4 FSH entry codes seen in practice: 0x60 DXT1, 0x61 DXT3,
0x7D A8R8G8B8, 0x7F R8G8B8, 0x7B 8-bit indexed (+ palette entry 0x2D/0x22/0x24).
Usage: python extract_fsh.py 6c23be66 e92073ca ...
Writes fsh-<iid>-<n>.png next to this script. Read-only on the game.
"""
import glob, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(TOOLS, "tools", "uimap", "emu"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "uimap", "emu"))
from qfs_ab import qfs  # proven RefPack decoder
from PIL import Image

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
FSH_TYPE = 0x7AB50E44

def iter_archives():
    for root, dirs, files in os.walk(GAME):
        if "Plugins" in root:
            continue
        for f in files:
            if f.lower().endswith(".dat"):
                yield os.path.join(root, f)

def find_entry(iid):
    for dat in iter_archives():
        with open(dat, "rb") as f:
            hdr = f.read(96)
            if hdr[:4] != b"DBPF":
                continue
            cnt = struct.unpack_from("<I", hdr, 36)[0]
            io_ = struct.unpack_from("<I", hdr, 40)[0]
            isz = struct.unpack_from("<I", hdr, 44)[0]
            f.seek(io_); idx = f.read(isz)
            per = isz // max(cnt, 1)
            for k in range(cnt):
                t, g, i, off, size = struct.unpack_from("<5I", idx, k * per)
                if i == iid and t == FSH_TYPE:
                    f.seek(off)
                    raw = f.read(size)
                    out = qfs(raw)
                    return os.path.basename(dat), t, g, (out if out else raw)
    return None

def decode_fsh(data, iid):
    assert data[:4] == b"SHPI", "not SHPI: %s" % data[:4].hex()
    nent = struct.unpack_from("<I", data, 8)[0]
    imgs = []
    for e in range(nent):
        tag = data[16 + 8*e:20 + 8*e].decode("ascii", "replace")
        off = struct.unpack_from("<I", data, 20 + 8*e)[0]
        code = data[off] & 0x7F
        # block size bits 8..31 (next-entry chain), header:
        w, h = struct.unpack_from("<2H", data, off + 4)
        print("  entry %d tag=%r code=%#x w=%d h=%d at %#x" % (e, tag, code, w, h, off))
        p = off + 16
        img = None
        if code == 0x7D:
            img = Image.frombytes("RGBA", (w, h), data[p:p + w*h*4], "raw", "BGRA")
        elif code == 0x7F:
            img = Image.frombytes("RGB", (w, h), data[p:p + w*h*3], "raw", "BGR")
        elif code == 0x60:
            img = Image.frombytes("RGBA", (w, h), data[p:p + w*h//2], "bcn", 1)
        elif code == 0x61:
            img = Image.frombytes("RGBA", (w, h), data[p:p + w*h], "bcn", 2)
        elif code == 0x7B:
            # indexed; palette is usually the NEXT entry
            pix = data[p:p + w*h]
            img = Image.frombytes("P", (w, h), pix)
            imgs.append(("indexed", img))
            continue
        elif code == 0x78:
            # R5G6B5
            img = Image.frombytes("RGB", (w, h), data[p:p + w*h*2], "raw", "BGR;16")
        elif code in (0x2D, 0x22, 0x24):
            print("    (palette entry, %d colors)" % w)
            continue
        else:
            print("    UNHANDLED code %#x" % code)
            continue
        imgs.append(("rgba", img))
    outs = []
    for n, (kind, img) in enumerate(imgs):
        out = os.path.join(HERE, "fsh-%08x-%d.png" % (iid, n))
        img.save(out)
        outs.append(out)
    return outs

for arg in sys.argv[1:]:
    iid = int(arg, 16)
    hit = find_entry(iid)
    if not hit:
        print("%08x: NOT FOUND in any archive (positive control: find_tgi.py saw it)" % iid)
        continue
    dat, t, g, payload = hit
    print("%08x: %s T=%08X G=%08X payload %d bytes, magic %r" % (iid, dat, t, g, len(payload), payload[:4]))
    try:
        outs = decode_fsh(payload, iid)
        for o in outs:
            print("  wrote", o)
    except Exception as ex:
        print("  DECODE FAILED:", ex)
        open(os.path.join(HERE, "fsh-%08x.bin" % iid), "wb").write(payload)
        print("  raw payload saved for manual decode")
