#!/usr/bin/env python3
r"""Find every occurrence of a 32-bit immediate in SimCity 4.exe. Read-only.

    python find_imm.py 0xABB90E58 [more ids...]

#188: the U-Drive-It marker exemplars (Tag1x1x3_Helicopter,
Tag1x1x3_MarinaUDISpawn, ...) bind a NULL S3D model and carry property
0xABB90E58 "TagKind" instead. So their on-screen visual - the blue offer
balloon - is drawn by CODE keyed on that byte, which is why fifteen
asset-side searches (PNG, FSH, S3D, EFFDIR, windows) all returned honest
nulls. Whoever reads 0xABB90E58 is the drawer.

Prints VA + section for each hit so it can be fed straight to disasm_at.py.
"""
import struct
import sys

GAME_EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"


def load(path):
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    n = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    secs = []
    for i in range(n):
        o = pe + 24 + opt + i * 40
        name = data[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, ra = struct.unpack_from("<IIII", data, o + 8)
        secs.append((name, va, vs, ra, rs))
    return data, base, secs


def off_to_va(off, base, secs):
    for name, sva, vs, ra, rs in secs:
        if ra <= off < ra + rs:
            return base + sva + (off - ra), name
    return None, "?"


def main():
    ids = [int(a, 0) for a in sys.argv[1:]]
    if not ids:
        print("usage: find_imm.py 0xABB90E58 [...]")
        return
    data, base, secs = load(GAME_EXE)
    for val in ids:
        pat = struct.pack("<I", val)
        hits = []
        start = 0
        while True:
            k = data.find(pat, start)
            if k < 0:
                break
            hits.append(k)
            start = k + 1
        print("0x%08X : %d occurrence(s)" % (val, len(hits)))
        for k in hits:
            va, sec = off_to_va(k, base, secs)
            ctx = data[max(0, k - 1):k + 4]
            print("    file 0x%08X  VA 0x%08X  [%s]  prevbyte=%02X"
                  % (k, va if va else 0, sec, ctx[0] if len(ctx) > 4 else 0))
        print()


if __name__ == "__main__":
    main()
