#!/usr/bin/env python3
"""Owner probe #7: who allocates the 4-vptr object, how big is it, and what
GZCOM clsid does it answer to.  Read-only."""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IB = 0x400000
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.detail = False


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []; off = pe + 24 + opt
    for i in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize)); off += 40
    return data, secs


DATA, SECS = load()


def rng(name):
    for n, sva, vsize, roff, rsize in SECS:
        if n.startswith(name):
            return IB + sva, roff, min(vsize, rsize)


TVA, TOFF, TSZ = rng(".text")
TEXT = DATA[TOFF:TOFF+TSZ]


def va2off(va):
    rva = va - IB
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def sec_of(va):
    rva = va - IB
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return n
    return None


def dw(va):
    o = va2off(va)
    return struct.unpack_from("<I", DATA, o)[0] if o is not None else None


def callers(target):
    out = []
    for i in range(len(TEXT) - 5):
        if TEXT[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", TEXT, i + 1)[0]
        s = TVA + i
        if s + 5 + rel == target:
            out.append(s)
    return out


def ctx(site, before=0x50, after=0x20):
    lo = site - before
    o = va2off(lo)
    for ins in MD.disasm(DATA[o:o + before + after + 16], lo, 500):
        if ins.address > site + after:
            break
        mk = "   <====" if ins.address == site else ""
        print(f"      0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}{mk}")


for name, fn in (("CTOR 0x007A0D50", 0x007A0D50),
                 ("RENDERER 0x007A2F60", 0x007A2F60)):
    c = callers(fn)
    print("=" * 74)
    print(f"{name}: {len(c)} rel32 caller(s): " + ", ".join(hex(x) for x in c))
    print("=" * 74)
    for s in c:
        print(f"  --- call site {s:08X} ---")
        ctx(s)
        print()

print("=" * 74)
print("VTABLE SLOT 0 OF EACH OF THE 4 VPTRS (identity probes)")
print("=" * 74)
for b, off in ((0x00AB8150, 0x00), (0x00AB8140, 0x04),
               (0x00AB7EE0, 0x08), (0x00AB7E60, 0xE0)):
    print(f"\n  vptr stored at this+0x{off:X} -> vtable {b:08X}")
    for i in range(12):
        print(f"    +0x{i*4:02X} = {dw(b+i*4):08X}")
