#!/usr/bin/env python3
"""Function boundaries around the data-view switch, + who calls it.

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


def main():
    data, secs = load()

    # int3 padding runs between 0x7A2700 and 0x7A4800 -> function boundaries
    lo, hi = 0x007A2700, 0x007A4900
    o = va2off(secs, lo)
    blob = data[o:o + (hi - lo)]
    print("### function boundaries (start of code after an int3 run >= 2):")
    bounds = []
    i = 0
    while i < len(blob):
        if blob[i] == 0xCC:
            j = i
            while j < len(blob) and blob[j] == 0xCC:
                j += 1
            if j - i >= 2 and j < len(blob):
                bounds.append(lo + j)
            i = j
        else:
            i += 1
    for b in bounds:
        print("   ", hex(b))
    print()

    # callers of each boundary
    def callers_of(target):
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

    def dword_refs(value):
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

    print("### callers / vtable refs per boundary")
    for b in bounds:
        c = callers_of(b)
        r = dword_refs(b)
        if c or r:
            print(f"  {hex(b)}: calls={len(c)} {', '.join(hex(x) for x in c[:6])} | dwordrefs={len(r)} {', '.join(f'{s}:{hex(v)}' for s,v in r[:6])}")
    print()

    # dump the head of the function that contains 0x7a3267
    cand = [b for b in bounds if b <= 0x007A3267]
    start = cand[-1] if cand else None
    print("### start of the fn containing 0x7a3267 =", hex(start))
    print()
    off = va2off(secs, start)
    for ins in MD.disasm(data[off:off+0x260], start):
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
