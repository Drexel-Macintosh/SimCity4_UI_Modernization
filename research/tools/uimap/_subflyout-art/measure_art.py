#!/usr/bin/env python3
"""Measure every extracted UI image (type 0x856DDBAC) from SimCity_1.dat.

Read-only. Writes an inventory CSV of TGI -> format/width/height so the
sub-flyout question ("does 258 / 88 / 382 equal an art dimension?") can be
answered from measurement instead of inference.
"""
import os
import struct
import csv
import sys

_TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
EXTRACT = os.path.join(_TOOLS, "dbpf", "extracted", "SimCity_1")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art-dims.csv")


def dims(path):
    with open(path, "rb") as f:
        head = f.read(64)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        # IHDR is always the first chunk
        w, h = struct.unpack(">II", head[16:24])
        return "PNG", w, h
    if head[:2] == b"\xff\xd8":
        # JPEG: walk segments for SOFn
        with open(path, "rb") as f:
            data = f.read()
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            m = data[i + 1]
            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                     0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return "JPEG", w, h
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                i += 2
                continue
            seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seglen
        return "JPEG", 0, 0
    if head[:2] == b"BM":
        w, h = struct.unpack("<ii", head[18:26])
        return "BMP", w, abs(h)
    if head[:4] == b"SHPI":
        # EA FSH: directory of entries; first entry header has w,h at +4,+6
        with open(path, "rb") as f:
            data = f.read()
        try:
            nent = struct.unpack("<I", data[8:12])[0]
            off = struct.unpack("<I", data[0x14:0x18])[0]
            w, h = struct.unpack("<HH", data[off + 4:off + 8])
            return "FSH(%d)" % nent, w, h
        except Exception:
            return "FSH", 0, 0
    return "?" + head[:4].hex(), 0, 0


def main():
    rows = []
    for name in sorted(os.listdir(EXTRACT)):
        if not name.startswith("T-"):
            continue
        p = os.path.join(EXTRACT, name)
        try:
            fmt, w, h = dims(p)
        except Exception as e:
            fmt, w, h = "ERR:%s" % e, 0, 0
        # T-<type>_G-<group>_I-<inst>.png
        base = name[:-4] if name.lower().endswith(".png") else name
        parts = base.split("_")
        t = parts[0][2:]
        g = parts[1][2:]
        i = parts[2][2:]
        rows.append((t, g, i, fmt, w, h, os.path.getsize(p), name))
    with open(OUT, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["type", "group", "inst", "fmt", "w", "h", "bytes", "file"])
        wr.writerows(rows)
    print("wrote", OUT, len(rows), "rows")


if __name__ == "__main__":
    main()
