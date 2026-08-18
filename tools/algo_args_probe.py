#!/usr/bin/env python3
"""ROWFILL's argument origin + walk UP from TOP's sole caller 0x7a3267.

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
MD.detail = False


def dis_range(data, secs, lo, hi):
    o = va2off(secs, lo)
    return list(MD.disasm(data[o:o + (hi - lo) + 16], lo))


def show(data, secs, lo, hi, title):
    print("=" * 78)
    print(title)
    print("=" * 78)
    for ins in dis_range(data, secs, lo, hi):
        if ins.address > hi:
            break
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
    print()


def callers_of(data, secs, target):
    hits = []
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff+rsize]
        for i in range(len(blob) - 5):
            if blob[i] != 0xE8:
                continue
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            site = base + i
            if site + 5 + rel == target:
                hits.append(site)
    return hits


def dword_refs(data, secs, value):
    needle = struct.pack("<I", value & 0xFFFFFFFF)
    out = []
    for n, sva, vsize, roff, rsize in secs:
        blob = data[roff:roff+rsize]
        s = 0
        while True:
            i = blob.find(needle, s)
            if i < 0:
                break
            out.append((n, IMAGE_BASE + sva + i))
            s = i + 1
    return out


def prev_ret_before(data, secs, va, back=0x900):
    """Nearest preceding C3 / C2 imm16 (ret) => function boundary candidate."""
    o = va2off(secs, va)
    blob = data[o - back:o]
    best = None
    i = 0
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    # linear scan backwards for C3 followed by int3/nop padding or a prologue
    for i in range(len(blob) - 1, 0, -1):
        b = blob[i]
        if b in (0xC3,) or (b == 0xC2):
            cand = va - back + i + (1 if b == 0xC3 else 3)
            # skip alignment padding
            j = cand - (va - back)
            while j < len(blob) and blob[j] in (0xCC, 0x90):
                j += 1
            return va - back + j
    return None


def main():
    data, secs = load()

    show(data, secs, 0x007A2505, 0x007A2740,
         "MID 0x007A2380 -- SECOND HALF (0x7A2505..) contains the ROWFILL call 0x7a2628")

    # TOP's sole caller
    st = prev_ret_before(data, secs, 0x007A3267)
    print("### function containing 0x7a3267 starts at", hex(st or 0))
    show(data, secs, st, 0x007A3300, f"caller of TOP: function @ {hex(st)}")

    print("=" * 78)
    print("WHO CALLS THAT FUNCTION")
    print("=" * 78)
    c = callers_of(data, secs, st)
    print(f"  direct call rel32 callers: {len(c)} -> {', '.join(hex(x) for x in c[:20])}")
    r = dword_refs(data, secs, st)
    print(f"  dword refs (vtable slots): {len(r)} -> {', '.join(f'{s}:{hex(v)}' for s, v in r[:20])}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
