#!/usr/bin/env python3
"""LANE 4 - mayor-rating DECLINE ARROW detached at 3x.

Read-only disassembly of the shipped exe. Dumps the rating-bar builder /
handler region around the three known imul-7 sites so we can see what
POSITIONS the arrow (as opposed to what sizes its reveal).

Positive control for this probe: the three imul sites 0x7E87B1 / 0x7E89D7 /
0x7E8A02 are KNOWN to contain `6B ?? 07`. If the dump does not show
`imul ..., 7` at those exact VAs, the probe is mis-mapping VA->offset and
every other line it prints is worthless. That assertion is printed first.
"""
import struct, sys
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
    for _ in range(nsec):
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


def dump(data, secs, start, end, label=""):
    o = va2off(secs, start)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    print("=" * 78)
    print(f"{label}  0x{start:08X} .. 0x{end:08X}")
    print("=" * 78)
    for i in md.disasm(data[o:o + (end - start) + 16], start):
        if i.address >= end:
            break
        raw = " ".join(f"{b:02X}" for b in i.bytes)
        print(f"0x{i.address:08X}  {raw:<24} {i.mnemonic} {i.op_str}")


def control(data, secs):
    print("### POSITIVE CONTROL ###")
    ok = True
    for va in (0x7E87B1, 0x7E89D7, 0x7E8A02):
        o = va2off(secs, va)
        b = data[o:o+3]
        hit = (b[0] == 0x6B and b[2] == 0x07)
        ok &= hit
        print(f"  0x{va:08X}: {b.hex(' ').upper()}  imul-imm8-7 = {hit}")
    print(f"  CONTROL {'PASS' if ok else 'FAIL - ABORT'}\n")
    return ok


if __name__ == "__main__":
    data, secs = load()
    if not control(data, secs):
        sys.exit(1)
    lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x7E8510
    hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x7E8B40
    dump(data, secs, lo, hi, sys.argv[3] if len(sys.argv) > 3 else "region")
