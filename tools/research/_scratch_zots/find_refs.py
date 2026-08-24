#!/usr/bin/env python3
"""Scan SimCity 4.exe for (a) E8 rel32 calls to given targets, (b) dword
immediate/pointer references to given values (vtable slots, globals, constants).
Prints VA of each hit. Read-only."""
import struct, sys

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
    return None, None

def main():
    data, base, secs = load(GAME_EXE)
    mode = sys.argv[1]
    targets = [int(x, 0) for x in sys.argv[2:]]
    if mode == "call":
        # find E8 rel32 whose destination is target
        for t in targets:
            hits = []
            i = 0
            while True:
                i = data.find(b"\xE8", i)
                if i < 0 or i + 5 > len(data):
                    break
                rel = struct.unpack_from("<i", data, i + 1)[0]
                va, sec = off_to_va(i, base, secs)
                if va is not None and sec == ".text" and (va + 5 + rel) == t:
                    hits.append(va)
                i += 1
            print(f"calls to {t:#010x}: {len(hits)}")
            for va in hits:
                print(f"  E8 @ {va:#010x}")
    elif mode == "dd":
        # find little-endian dword refs anywhere; report section
        for t in targets:
            needle = struct.pack("<I", t)
            hits = []
            i = 0
            while True:
                i = data.find(needle, i)
                if i < 0:
                    break
                va, sec = off_to_va(i, base, secs)
                if va is not None:
                    hits.append((va, sec))
                i += 1
            print(f"dd {t:#010x}: {len(hits)} refs")
            for va, sec in hits:
                print(f"  @ {va:#010x} ({sec})")

if __name__ == "__main__":
    main()
