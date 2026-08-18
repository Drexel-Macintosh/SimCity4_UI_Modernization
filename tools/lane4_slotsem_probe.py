#!/usr/bin/env python3
"""LANE 4 part 3 - what do window vtable slots 0xA4..0xB8 and 0xE0 actually DO?

The whole diagnosis hinges on two things the docs disagree about:
  * is [vt+0xAC] GetL and [vt+0xB0] GetT (header order) - or something else?
  * is [vt+0xE0] GZWinMoveTo ABSOLUTE (move TO) or RELATIVE (move BY)?
    UiSpike.cpp asserts RELATIVE as law; the SC4 handler at 0x007E8A0A calls it
    with what looks like an absolute composed coordinate.

POSITIVE CONTROL: the rect is known to live at cIGZWin+0xA8(L) +0xAC(T)
+0xB0(R) +0xB4(B). Slot 0xA4 MUST therefore decode as (R - L) i.e. touching
+0xB0 and +0xA8, and slot 0xA8 as (B - T) i.e. +0xB4 and +0xAC. If those two
do not come out that way, the vtable address is wrong and every other line
below is meaningless.
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
VTABLES = {
    "cSC4WinRCI(cIGZWin sub)": 0x00AB8628,
    "cSC4WinGenTransparent": 0x00AB7358,
    "cSC4WinTrendBar": 0x00ABA430,
}
SLOTS = [0xA4, 0xA8, 0xAC, 0xB0, 0xB4, 0xB8, 0xCC, 0xE0, 0x110, 0x114, 0x118]


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


def show(data, secs, va, n=14, indent="      "):
    o = va2off(secs, va)
    if o is None:
        print(indent + "<unmapped>")
        return
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for i in md.disasm(data[o:o + n * 10], va, n):
        print(f"{indent}0x{i.address:08X}  {i.mnemonic} {i.op_str}")
        if i.mnemonic in ("ret", "jmp"):
            break


if __name__ == "__main__":
    data, secs = load()
    for name, vt in VTABLES.items():
        o = va2off(secs, vt)
        print("#" * 74)
        print(f"# {name}  vtable 0x{vt:08X}")
        print("#" * 74)
        for s in SLOTS:
            fn = struct.unpack_from("<I", data, o + s)[0]
            print(f"  [vt+0x{s:03X}] -> 0x{fn:08X}")
            show(data, secs, fn)
            print()
        break  # first vtable is enough unless it fails the control
