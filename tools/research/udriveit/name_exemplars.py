#!/usr/bin/env python3
r"""Name the marker exemplars the live MARKERID log identified. Read-only.

    python name_exemplars.py 1e680000 1e6d0000 ...

#188: every U-Drive-It-era marker occupant carries a resource key
{T=0x6534284A, G=0xC977C536, I=<instance>} naming the exemplar it was built
from. The sibling family member 0x29F10000 is "UI8x1x3_ConnectArrow_29F1" -
the NAME ENCODES THE SIZE - so naming our 13 instances tells us which one is
the offer balloon and what its size record says.

Prints the ExemplarName plus every ASCII run, and the OccupantSize property
(0x27812810, three floats) when present.
"""
import glob
import os
import struct
import sys

GAME = os.environ.get(
    "SC4_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe")
EXEMPLAR_T = 0x6534284A
EXEMPLAR_G = 0xC977C536
PROP_NAME = 0x00000020
PROP_OCCUPANT_SIZE = 0x27812810


def qfs_decompress(data):
    """QFS/RefPack. Returns None if the blob is not QFS."""
    if len(data) < 9:
        return None
    if data[4:6] == b"\x10\xfb":
        body, hdr = data, 4
    elif data[0:2] == b"\x10\xfb":
        body, hdr = data, 0
    else:
        return None
    out_len = int.from_bytes(body[hdr + 2:hdr + 5], "big")
    src = hdr + 5
    out = bytearray()
    while src < len(body):
        c = body[src]
        if c < 0x80:
            if src + 1 >= len(body):
                break
            b1 = body[src + 1]
            n_plain = c & 3
            out += body[src + 2:src + 2 + n_plain]
            src += 2 + n_plain
            n_copy = ((c & 0x1C) >> 2) + 3
            off = ((c & 0x60) << 3) + b1 + 1
        elif c < 0xC0:
            if src + 2 >= len(body):
                break
            b1, b2 = body[src + 1], body[src + 2]
            n_plain = (b1 >> 6) & 3
            out += body[src + 3:src + 3 + n_plain]
            src += 3 + n_plain
            n_copy = (c & 0x3F) + 4
            off = ((b1 & 0x3F) << 8) + b2 + 1
        elif c < 0xE0:
            if src + 3 >= len(body):
                break
            b1, b2, b3 = body[src + 1], body[src + 2], body[src + 3]
            n_plain = c & 3
            out += body[src + 4:src + 4 + n_plain]
            src += 4 + n_plain
            n_copy = ((c & 0x0C) << 6) + b3 + 5
            off = ((c & 0x10) << 12) + (b1 << 8) + b2 + 1
        elif c < 0xFC:
            n_plain = ((c & 0x1F) + 1) * 4
            out += body[src + 1:src + 1 + n_plain]
            src += 1 + n_plain
            continue
        else:
            n_plain = c & 3
            out += body[src + 1:src + 1 + n_plain]
            src += 1 + n_plain
            break
        start = len(out) - off
        if start < 0:
            break
        for k in range(n_copy):
            out.append(out[start + k])
    return bytes(out[:out_len]) if out_len else bytes(out)


def index_entries(path):
    """Yield (t, g, i, offset, size) for every index entry."""
    with open(path, "rb") as fh:
        head = fh.read(96)
        if head[:4] != b"DBPF":
            return
        cnt = struct.unpack_from("<I", head, 36)[0]
        off = struct.unpack_from("<I", head, 40)[0]
        fh.seek(off)
        raw = fh.read(cnt * 20)
    for k in range(cnt):
        yield struct.unpack_from("<IIIII", raw, k * 20)


def ascii_runs(data, minlen=4):
    runs, cur = [], bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= minlen:
                runs.append(cur.decode("latin1"))
            cur = bytearray()
    if len(cur) >= minlen:
        runs.append(cur.decode("latin1"))
    return runs


def parse_props(data):
    """Binary exemplar EQZB1###. Returns {propId: (typeCode, values)}."""
    if data[:8] not in (b"EQZB1###", b"CQZB1###"):
        return None
    # parent cohort TGI (12 bytes) then u32 property count
    pos = 8 + 12
    if pos + 4 > len(data):
        return None
    count = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    props = {}
    for _ in range(count):
        if pos + 9 > len(data):
            break
        pid, vtype, keytype = struct.unpack_from("<IIH", data, pos)
        pos += 10  # id(4) type(4) keytype(2) unused(1)... layout varies
        pos -= 0
        # keytype 0x80 = array (u32 reps follow), else single value
        sizes = {0x100: 1, 0x200: 1, 0x700: 2, 0x800: 2, 0x900: 4,
                 0xB00: 1, 0xC00: 1, 0x0B: 1, 0x0C: 1}
        vsize = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4, 8: 8, 9: 1,
                 0xB: 1, 0xC: 1}.get(vtype, 4)
        if keytype == 0x80:
            if pos + 4 > len(data):
                break
            reps = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        else:
            reps = 1
        raw = data[pos:pos + reps * vsize]
        pos += reps * vsize
        props[pid] = (vtype, raw)
    return props


def main():
    want = [int(a, 16) for a in sys.argv[1:]]
    dats = sorted(glob.glob(os.path.join(GAME, "**", "*.dat"), recursive=True)
                  + glob.glob(os.path.join(GAME, "**", "*.DAT"), recursive=True))
    found = {}
    for path in dats:
        for (t, g, i, off, size) in index_entries(path):
            if t == EXEMPLAR_T and g == EXEMPLAR_G and i in want:
                with open(path, "rb") as fh:
                    fh.seek(off)
                    blob = fh.read(size)
                dec = qfs_decompress(blob)
                found[i] = (os.path.basename(path), blob, dec or blob)
    for i in want:
        if i not in found:
            print("0x%08X  NOT FOUND as {0x6534284A,0xC977C536,*}" % i)
            continue
        src, blob, data = found[i]
        runs = ascii_runs(data)
        magic = data[:8].decode("latin1", "replace")
        print("0x%08X  %-16s magic=%-9r  strings=%s"
              % (i, src, magic, runs if runs else "<none>"))


if __name__ == "__main__":
    main()
