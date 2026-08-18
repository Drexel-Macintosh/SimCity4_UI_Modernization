#!/usr/bin/env python3
r"""Find direct E8 callers of a VA, and any vtable slot holding it. Read-only.

    python find_callers.py 0x004FBFE0

#188: the balloon builder at 0x4FBFE0 is NOT in any vtable (0 dword hits),
so it must be reached by a direct `call rel32`. Its callers tell us which
class owns `edi` (the object whose vtable slot +0x3C actually constructs the
visual) - the last hop to the balloon's SIZE.
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


def main():
    target = int(sys.argv[1], 0)
    data, base, secs = load(GAME_EXE)
    text = next(s for s in secs if s[0] == ".text")
    _, sva, vs, ra, rs = text
    n = 0
    for off in range(ra, ra + rs - 5):
        if data[off] != 0xE8:
            continue
        rel = struct.unpack_from("<i", data, off + 1)[0]
        va = base + sva + (off - ra)
        if va + 5 + rel == target:
            n += 1
            print("  call at VA 0x%08X" % va)
    print("direct E8 callers of 0x%08X: %d" % (target, n))


if __name__ == "__main__":
    main()
