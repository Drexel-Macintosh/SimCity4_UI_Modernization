#!/usr/bin/env python3
"""Walk UP from 0x007A2F60 (candidate entry of the data-view switch) to a
vtable slot / identifiable owner.  Includes positive controls.

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


MD = Cs(CS_ARCH_X86, CS_MODE_32)


def show(data, secs, lo, n, title):
    print("=" * 78)
    print(title)
    print("=" * 78)
    o = va2off(secs, lo)
    for ins in MD.disasm(data[o:o + n * 10], lo):
        if ins.address >= lo + n * 10:
            break
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
    print()


def callers_of(data, secs, target):
    hits = []
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
            if site + 5 + rel == target:
                hits.append(site)
    return hits


def dword_refs(data, secs, value):
    needle = struct.pack("<I", value & 0xFFFFFFFF)
    out = []
    for n, sva, vsize, roff, rsize in secs:
        bl = data[roff:roff+rsize]
        s = 0
        while True:
            k = bl.find(needle, s)
            if k < 0:
                break
            out.append((n, IMAGE_BASE + sva + k))
            s = k + 1
    return out


def cstr(data, secs, va, n=120):
    o = va2off(secs, va)
    if o is None:
        return None
    e = data.find(b"\0", o, o + n)
    if e < 0:
        return None
    s = data[o:e]
    if len(s) < 5 or not all(32 <= c < 127 for c in s):
        return None
    return s.decode("ascii")


def strings_in(data, secs, lo, hi, label):
    o = va2off(secs, lo)
    blob = data[o:o + (hi - lo)]
    seen = {}
    for i in range(len(blob) - 5):
        if blob[i] not in (0x68, 0xB8, 0xB9, 0xBA):   # push imm32 / mov r32,imm32
            continue
        v = struct.unpack_from("<I", blob, i + 1)[0]
        if not (IMAGE_BASE < v < IMAGE_BASE + 0x800000):
            continue
        s = cstr(data, secs, v)
        if s:
            seen.setdefault(s, []).append(lo + i)
    print(f"### strings referenced in {label} [{hex(lo)},{hex(hi)}): {len(seen)}")
    for s, at in list(sorted(seen.items(), key=lambda x: x[1][0]))[:60]:
        print(f"    {hex(at[0])}  {s!r}")
    print()


def main():
    data, secs = load()

    show(data, secs, 0x007A2F60, 40, "candidate switch entry 0x007A2F60")

    print("### callers of 0x007A2F60")
    for c in callers_of(data, secs, 0x007A2F60):
        print("   ", hex(c))
    print()

    for site in (0x7a4b19, 0x7a53d7, 0x7a55d1, 0x7a5f1b):
        show(data, secs, site - 0x60, 30, f"context around call site {hex(site)}")

    # POSITIVE CONTROL for the string scan: a region known to log
    strings_in(data, secs, 0x007A9000, 0x007AC000, "POSITIVE-CONTROL region")
    strings_in(data, secs, 0x0079E000, 0x007A9000, "the data-view module")

    return 0


if __name__ == "__main__":
    sys.exit(main())
