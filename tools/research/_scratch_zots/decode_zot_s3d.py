#!/usr/bin/env python3
"""Extract + decode the four Zot S3D models' VERT chunks (2026-08-23).

Reuses the QFS + DBPF index code from tools/dbpf/decode_s3d_plate.py.
Discovers archives by globbing the install for *.dat/*.DAT (per the
9-archive law: discover, don't list).
"""
import glob
import os
import struct
import sys

sys.path.insert(0, r"C:\dev\SC4UIScale\tools\dbpf")
from decode_s3d_plate import read_index, qfs_decompress

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
T, G = 0x5AD0E817, 0xBADB57F1
ZOTS = {0x0FD10000: "NoPower", 0x107A0000: "NoCar",
        0x1C430000: "NoWater", 0x1C440000: "NoWork"}

archives = []
for pat in ("*.dat", "*.DAT"):
    archives += glob.glob(os.path.join(GAME, "**", pat), recursive=True)
archives = sorted(set(os.path.normcase(a) for a in archives))
print("archives scanned:", len(archives))

def parse_chunks(buf):
    assert buf[:4] == b"3DMD", buf[:8]
    off = 8
    chunks = []
    while off + 8 <= len(buf):
        tag = buf[off:off+4].decode("latin1")
        ln = struct.unpack_from("<I", buf, off+4)[0]
        chunks.append((tag, off, ln))
        if tag == "ANIM":
            # anomalous length; scan forward for PROP
            p = buf.find(b"PROP", off)
            off = p if p > 0 else len(buf)
        else:
            off += ln
    return chunks

def decode_vert(buf, off, ln):
    body = off + 8
    lead = struct.unpack_from("<I", buf, body)[0]
    cnt = struct.unpack_from("<H", buf, body + 6)[0]
    print("   VERT lead=%d vertex_count=%d" % (lead, cnt))
    vbase = body + 12
    for v in range(cnt):
        x, y, z, u, vv = struct.unpack_from("<5f", buf, vbase + v*20)
        print("   vtx%d  X=%9.4f Y=%9.4f Z=%9.4f  U=%.4f V=%.4f" % (v, x, y, z, u, vv))

for inst, name in ZOTS.items():
    found = False
    for arc in archives:
        try:
            idx = list(read_index(arc))
        except Exception:
            continue
        for (t, g, i, offset, size) in idx:
            if (t, g, i) == (T, G, inst):
                with open(arc, "rb") as f:
                    f.seek(offset)
                    raw = f.read(size)
                try:
                    buf = qfs_decompress(raw)
                    comp = "QFS %d->%d" % (size, len(buf))
                except ValueError:
                    buf = raw
                    comp = "stored %d" % size
                print("\n=== Zot_%s I=0x%08X in %s (%s) ===" % (name, inst, os.path.basename(arc), comp))
                for tag, off, ln in parse_chunks(buf):
                    print("  chunk %s @%d len %d" % (tag, off, ln))
                    if tag == "VERT":
                        decode_vert(buf, off, ln)
                    if tag == "MATS":
                        # find length-prefixed name string
                        b = buf[off+8:off+8+ln]
                        for k in range(len(b)-1):
                            L = b[k]
                            if 10 < L < 60 and all(32 <= c < 127 for c in b[k+1:k+1+L]):
                                print("   MATS name: %r" % b[k+1:k+1+L].decode("latin1"))
                                break
                found = True
                break
        if found:
            break
    if not found:
        print("\n=== Zot_%s I=0x%08X NOT FOUND in any archive ===" % (name, inst))
