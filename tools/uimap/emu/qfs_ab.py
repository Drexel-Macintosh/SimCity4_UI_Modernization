"""qfs_ab.py - read-only QFS (RefPack) decompressor + DBPF LUA dumper.

Used once, to read the shipped tutorial Lua out of SimCity_1.dat without
touching the game.  READ ONLY: opens the archives 'rb' and never writes.
"""
import os
import struct
import sys


def qfs(data):
    # DBPF-style: dword compressed-size, word 0x10FB signature, 3-byte usize BE
    p = 0
    if len(data) > 9 and data[4] == 0x10 and data[5] == 0xFB:
        p = 4
    if not (data[p] == 0x10 and data[p + 1] == 0xFB):
        return None
    usize = (data[p + 2] << 16) | (data[p + 3] << 8) | data[p + 4]
    i = p + 5
    out = bytearray()
    while i < len(data):
        b0 = data[i]
        if b0 < 0x80:
            b1 = data[i + 1]
            i += 2
            n = b0 & 3
            out += data[i:i + n]
            i += n
            off = ((b0 & 0x60) << 3) + b1 + 1
            cnt = ((b0 >> 2) & 7) + 3
        elif b0 < 0xC0:
            b1 = data[i + 1]
            b2 = data[i + 2]
            i += 3
            n = (b1 >> 6) & 3
            out += data[i:i + n]
            i += n
            off = ((b1 & 0x3F) << 8) + b2 + 1
            cnt = (b0 & 0x3F) + 4
        elif b0 < 0xE0:
            b1 = data[i + 1]
            b2 = data[i + 2]
            b3 = data[i + 3]
            i += 4
            n = b0 & 3
            out += data[i:i + n]
            i += n
            off = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1
            cnt = ((b0 & 0x0C) << 6) + b3 + 5
        elif b0 < 0xFC:
            i += 1
            n = ((b0 & 0x1F) + 1) * 4
            out += data[i:i + n]
            i += n
            continue
        else:
            i += 1
            n = b0 & 3
            out += data[i:i + n]
            i += n
            break
        s = len(out) - off
        for k in range(cnt):
            out.append(out[s + k])
    return bytes(out[:usize])


GAME = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"


def dump(dat, tid, want=None, grep=None):
    p = os.path.join(GAME, dat)
    f = open(p, "rb")
    d = f.read(96)
    cnt = struct.unpack_from("<I", d, 36)[0]
    io = struct.unpack_from("<I", d, 40)[0]
    isz = struct.unpack_from("<I", d, 44)[0]
    f.seek(io)
    blob = f.read(isz)
    for k in range(cnt):
        t, g, i, o, s = struct.unpack_from("<IIIII", blob, k * 20)
        if t != tid:
            continue
        if want is not None and i not in want:
            continue
        f.seek(o)
        raw = f.read(s)
        txt = qfs(raw)
        if txt is None:
            txt = raw
        if grep and grep.encode() not in txt:
            continue
        sys.stdout.buffer.write(b"\n===== %s G=%08X I=%08X (%d -> %d) =====\n"
                                % (dat.encode(), g, i, s, len(txt)))
        sys.stdout.buffer.write(txt)
    f.close()


if __name__ == "__main__":
    ids = set(int(a, 16) for a in sys.argv[1:] if not a.startswith("--"))
    grep = None
    for a in sys.argv[1:]:
        if a.startswith("--grep="):
            grep = a.split("=", 1)[1]
    dump("SimCity_1.dat", 0xCA63E2A3, ids or None, grep)
