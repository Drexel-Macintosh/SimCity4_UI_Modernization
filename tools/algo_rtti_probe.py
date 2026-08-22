#!/usr/bin/env python3
"""RTTI map: which class vtables point into 0x0079E000..0x007A9000, plus the
switch function that calls TOP.

Read-only.
"""
import sys, struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
LO, HI = 0x0079E000, 0x007A9000


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    off = pe + 24 + opt
    for i in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


def va2off(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def rd(data, secs, va):
    o = va2off(secs, va)
    if o is None or o + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, o)[0]


def cstr(data, secs, va, n=160):
    o = va2off(secs, va)
    if o is None:
        return None
    e = data.find(b"\0", o, o + n)
    if e < 0:
        return None
    return data[o:e].decode("latin1", "replace")


def main():
    data, secs = load()

    # --- 1. build a vtable -> class-name map from RTTI ---
    # A COL is referenced at vftable[-1]. Scan all 4-aligned dwords in data
    # sections; if dword at (va-4) points to a plausible COL whose +0x0C is a
    # TypeDescriptor whose +8 is a ".?AV" string, record it.
    named = {}          # vtable VA -> class name
    for n, sva, vsize, roff, rsize in secs:
        if n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff+rsize]
        for i in range(0, len(blob) - 4, 4):
            col = struct.unpack_from("<I", blob, i)[0]
            if not (IMAGE_BASE < col < IMAGE_BASE + 0x800000):
                continue
            sig = rd(data, secs, col)
            if sig != 0:
                continue
            td = rd(data, secs, col + 0x0C)
            if td is None or not (IMAGE_BASE < td < IMAGE_BASE + 0x800000):
                continue
            s = cstr(data, secs, td + 8)
            if s and s.startswith(".?AV"):
                named[base + i + 4] = s
    print(f"### RTTI: {len(named)} vtables named\n")

    # --- 2. which named vtables have a slot pointing into [LO,HI) ---
    hits = {}
    for vt, name in named.items():
        slots = []
        for k in range(0, 400):
            v = rd(data, secs, vt + 4*k)
            if v is None:
                break
            if not (IMAGE_BASE < v < IMAGE_BASE + 0x800000):
                break
            if LO <= v < HI:
                slots.append((k*4, v))
        if slots:
            hits[vt] = (name, slots)
    print("### named vtables with slots in 0x0079E000..0x007A9000")
    for vt, (name, slots) in sorted(hits.items(), key=lambda x: x[1][0]):
        print(f"  {hex(vt)}  {name}   {len(slots)} slots  "
              f"first={[(hex(o), hex(v)) for o, v in slots[:6]]}")
    print()

    # --- 3. globals used by the switch ---
    print("### references to the data-source globals")
    for g in (0xB43CEC, 0xB43D60, 0xB43D7C, 0xB43DA0, 0xB43DA4):
        needle = struct.pack("<I", g)
        cnt = 0
        where = []
        for n, sva, vsize, roff, rsize in secs:
            blob = data[roff:roff+rsize]
            s = 0
            while True:
                i = blob.find(needle, s)
                if i < 0:
                    break
                cnt += 1
                if len(where) < 8:
                    where.append(hex(IMAGE_BASE + sva + i))
                s = i + 1
        print(f"  {hex(g)}: {cnt} refs  {where}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
