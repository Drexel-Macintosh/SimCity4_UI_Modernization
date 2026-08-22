#!/usr/bin/env python3
"""Identify the module that owns 0x007A2740: strings referenced from
0x0079E000..0x007A9000, and the entry of the switch fn containing 0x7a3267.

Read-only.
"""
import sys, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000


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


def cstr(data, secs, va, n=120):
    o = va2off(secs, va)
    if o is None:
        return None
    e = data.find(b"\0", o, o + n)
    if e < 0:
        return None
    s = data[o:e]
    if len(s) < 4:
        return None
    try:
        t = s.decode("ascii")
    except Exception:
        return None
    if all(32 <= c < 127 for c in s):
        return t
    return None


def main():
    data, secs = load()
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    LO, HI = 0x0079E000, 0x007A9000
    o = va2off(secs, LO)
    blob = data[o:o + (HI - LO)]

    # 1. push imm32 (0x68) whose operand is a readable C string
    print("### strings pushed inside 0x0079E000..0x007A9000")
    seen = {}
    for i in range(len(blob) - 5):
        if blob[i] != 0x68:
            continue
        v = struct.unpack_from("<I", blob, i + 1)[0]
        if not (IMAGE_BASE < v < IMAGE_BASE + 0x800000):
            continue
        s = cstr(data, secs, v)
        if s and len(s) >= 5:
            seen.setdefault(s, []).append(LO + i)
    for s, at in sorted(seen.items(), key=lambda x: x[1][0]):
        print(f"  {hex(at[0])}  {s!r}  x{len(at)}")
    print()

    # 2. entry of the switch fn containing 0x7a3267:
    #    any E8 target that lands in [0x7A2E00, 0x7A3267]
    print("### call targets landing in [0x7A2E00, 0x7A3268)")
    tgts = {}
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        bl = data[roff:roff+rsize]
        for k in range(len(bl) - 5):
            if bl[k] != 0xE8:
                continue
            rel = struct.unpack_from("<i", bl, k + 1)[0]
            site = base + k
            t = site + 5 + rel
            if 0x007A2E00 <= t < 0x007A3268:
                tgts.setdefault(t, []).append(site)
    for t, sites in sorted(tgts.items()):
        print(f"  {hex(t)} <- {len(sites)}: {', '.join(hex(x) for x in sites[:10])}")
    print()

    # 3. dword refs (vtable slots) to anything in [0x7A2E00, 0x7A3268)
    print("### dword (vtable) refs into [0x7A2E00, 0x7A3268)")
    for n, sva, vsize, roff, rsize in secs:
        if n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        bl = data[roff:roff+rsize]
        for k in range(0, len(bl) - 4, 4):
            v = struct.unpack_from("<I", bl, k)[0]
            if 0x007A2E00 <= v < 0x007A3268:
                print(f"  {n}:{hex(base+k)} -> {hex(v)}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
