#!/usr/bin/env python3
"""LENS: THE ALGORITHM. What 0x007A2740 / 0x007A2380 / 0x0079ED90 compute,
and what changes at dest 768 vs 512.

Read-only. Disassembles the shipped exe; writes nothing.
"""
import sys, struct, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

FAULT   = 0x00910003
ROWFILL = 0x0079ED90
MID     = 0x007A2380
TOP     = 0x007A2740


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


def dis(data, secs, va, count=200, stop_at_ret_depth=None):
    o = va2off(secs, va)
    if o is None:
        return []
    return list(MD.disasm(data[o:o+count*10], va, count))


def dump(data, secs, va, count, title, tags=()):
    print("=" * 78)
    print(title)
    print("=" * 78)
    for ins in dis(data, secs, va, count):
        s = f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}"
        t = ""
        for off, what in tags:
            for form in (f"+ 0x{off:x}]", f"+ {off}]", f"0x{off:x}"):
                if form in ins.op_str:
                    t = f"   <<< {what}"
                    break
        print(s + t)
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


def find_dword_refs(data, secs, value):
    """Every 4-byte little-endian occurrence of `value` in the image, as VA."""
    needle = struct.pack("<I", value & 0xFFFFFFFF)
    out = []
    for n, sva, vsize, roff, rsize in secs:
        blob = data[roff:roff+rsize]
        start = 0
        while True:
            i = blob.find(needle, start)
            if i < 0:
                break
            out.append((n, IMAGE_BASE + sva + i))
            start = i + 1
    return out


def main():
    data, secs = load()
    print(f"exe {len(data):,} bytes\n")

    tags = [(0xE4, "blitSize"), (0xF0, "surface"), (0x104, "zoom"),
            (0x114, "rasterBase"), (0x118, "rasterW"), (0x11C, "rasterH"),
            (0x120, "dirtyMask"), (0x34, "rect.L"), (0x38, "rect.T"),
            (0x3C, "rect.R"), (0x40, "rect.B"), (0x174, "vt+0x174 GetDim"),
            (0x178, "vt+0x178")]

    dump(data, secs, TOP, 260, "0x007A2740  TOP", tags)
    dump(data, secs, MID, 260, "0x007A2380  MID", tags)
    dump(data, secs, ROWFILL, 300, "0x0079ED90  ROWFILL", tags)
    dump(data, secs, FAULT, 20, "0x00910003  memset32", [])

    print("=" * 78)
    print("CALLERS")
    print("=" * 78)
    for nm, va in (("ROWFILL", ROWFILL), ("MID", MID), ("TOP", TOP)):
        c = callers_of(data, secs, va)
        print(f"{nm} {va:#x}: {len(c)} -> {', '.join(hex(x) for x in c[:20])}")
    print()

    print("=" * 78)
    print("DISPATCH TABLE AT 0x0079EFC0 (4 entries per lead)")
    print("=" * 78)
    o = va2off(secs, 0x0079EFC0)
    for i in range(8):
        v = struct.unpack_from("<I", data, o + 4*i)[0]
        print(f"  [{i}] 0x{0x0079EFC0+4*i:08X} -> 0x{v:08X}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
