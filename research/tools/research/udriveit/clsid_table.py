#!/usr/bin/env python3
r"""Extract SimCity 4.exe's own {GZCLSID -> class name} table from .data.

The table is a flat array of 8-byte pairs (u32 clsid, u32 char* name) living in
.data.  It is the game's OWN naming of every registered COM class, so a name
read from it is authoritative - unlike an RTTI guess or a string near a call.
Discovered by noticing that the immediates for three save subfile types
(0xA9BD882D, 0xA9C05C85, 0xC97F987C) all landed in .data within 0xB089F0-0xB08CC8.
Read-only.
"""
import struct, sys, json

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
d = open(EXE, "rb").read()
pe = struct.unpack_from("<I", d, 0x3C)[0]
n = struct.unpack_from("<H", d, pe + 6)[0]
optsz = struct.unpack_from("<H", d, pe + 20)[0]
base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
secs = []
for i in range(n):
    o = pe + 24 + optsz + i * 40
    nm = d[o:o + 8].rstrip(b"\0").decode("latin1")
    vs, va, rs, ra = struct.unpack_from("<IIII", d, o + 8)
    secs.append((nm, va, vs, ra, rs))


def va2off(va):
    r = va - base
    for nm, sva, vs, ra, rs in secs:
        if sva <= r < sva + max(vs, rs):
            k = r - sva
            if k < rs:
                return ra + k
    return None


def cstr(va, maxlen=96):
    o = va2off(va)
    if o is None:
        return None
    e = d.find(b"\0", o, o + maxlen)
    if e < 0:
        return None
    s = d[o:e]
    if len(s) < 3 or not all(32 <= c < 127 for c in s):
        return None
    return s.decode("ascii")


def build(lo=0xB00000, hi=0xB20000):
    """Walk .data in 8-byte steps; keep pairs whose 2nd word is a C string."""
    tab = {}
    va = lo
    while va < hi:
        o = va2off(va)
        if o is None or o + 8 > len(d):
            va += 8
            continue
        cid, pname = struct.unpack_from("<II", d, o)
        s = cstr(pname) if 0xA00000 <= pname < 0xB00000 else None
        if s and cid > 0xFFFF:
            tab[cid] = s
        va += 8
    return tab


TABLE = build()

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--all":
        print("%d named classes" % len(TABLE))
        for c, nm in sorted(TABLE.items(), key=lambda kv: kv[1]):
            print("0x%08X  %s" % (c, nm))
    elif args and args[0] == "--grep":
        pats = [a.lower() for a in args[1:]]
        for c, nm in sorted(TABLE.items(), key=lambda kv: kv[1]):
            if any(p in nm.lower() for p in pats):
                print("0x%08X  %s" % (c, nm))
    else:
        for a in args:
            c = int(a, 0)
            print("0x%08X  %s" % (c, TABLE.get(c, "<not in table>")))
