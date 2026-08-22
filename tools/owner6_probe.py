#!/usr/bin/env python3
"""Owner probe #6: true vtable bases + who constructs `this` (size >= 0x9DA).

A vtable BASE is an address that .text materialises as an immediate (the ctor
does `mov [this], offset vtbl`).  Interior slots are never immediates.  That is
the boundary test - the walk-back-until-not-.text test is wrong here because
this binary packs vtables adjacently with no null terminator.

POSITIVE CONTROL: 0x00AB83B8 (= minimap draw slot 0xAB8518 - 0x160) MUST show
up as a .text immediate; if it does not, this test is blind and every base
below is worthless.
Read-only.
"""
import struct
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
RVA, ROFF, RSZ = rng(".rdata")
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


def text_imm_sites(value):
    """Every byte position in .text holding this dword (an immediate)."""
    tgt = struct.pack("<I", value)
    out, s = [], 0
    while True:
        k = TEXT.find(tgt, s)
        if k < 0: break
        out.append(TVA + k)
        s = k + 1
    return out


print("=" * 74)
print("A. WHICH ADDRESSES IN 0xAB7C00..0xAB8700 ARE MATERIALISED IN .text?")
print("   (= real vtable bases; interior slots are not)")
print("=" * 74)
bases = []
for va in range(0x00AB7C00, 0x00AB8700, 4):
    sites = text_imm_sites(va)
    if sites:
        bases.append((va, sites))
        print(f"  base {va:08X}  materialised {len(sites)}x, e.g. " +
              ", ".join(f"{s:08X}" for s in sites[:4]))
print(f"\n  POSITIVE CONTROL 0x00AB83B8 (minimap vtable base) present: "
      f"{any(b == 0x00AB83B8 for b, _ in bases)}")

blist = [b for b, _ in bases]


def base_of(slot):
    c = [b for b in blist if b <= slot]
    return max(c) if c else None


print("\n" + "=" * 74)
print("B. RE-ANCHOR THE CHAIN SLOTS ONTO REAL BASES")
print("=" * 74)
slots = {0x00AB7EEC: "fn 0x7a56e0 (calls the renderer)",
         0x00AB7FF4: "fn 0x7a6290",
         0x00AB814C: "fn 0x7a54d0 (calls the renderer)",
         0x00AB815C: "fn 0x7a6270",
         0x00AB8160: "fn 0x7a61e0",
         0x00AB8164: "fn 0x7a6220",
         0x00AB8518: "fn 0x7a79b0  MINIMAP DRAW (control)"}
for s, who in sorted(slots.items()):
    b = base_of(s)
    print(f"  slot {s:08X} = {who}")
    print(f"      -> vtable {b:08X}  slot index +0x{s-b:X} (#{(s-b)//4})")

print("\n" + "=" * 74)
print("C. CTOR SITES: where each base is stored, and the `new` size nearby")
print("=" * 74)
for b in sorted({base_of(s) for s in slots}):
    print(f"\n  ---- vtable {b:08X} ----")
    for site in text_imm_sites(b):
        # disassemble a window around the site
        lo = site - 0x60
        o = va2off(lo)
        ctx = []
        for ins in MD.disasm(DATA[o:o+0x90], lo, 200):
            ctx.append(ins)
        txt = [f"      0x{i.address:08X}  {i.mnemonic:<7} {i.op_str}" for i in ctx
               if i.address >= site - 0x40 and i.address <= site + 0x14]
        print(f"    site {site:08X}:")
        for t in txt:
            print(t)


print("\n" + "=" * 74)
print("D. GLOBAL SERVICE POINTERS USED BY THE RENDERER / 0x7A2740")
print("=" * 74)
for g in (0xB43CEC, 0xB43D60, 0xB43D7C, 0xB43D88, 0xB43DA0, 0xB43DA4, 0xB43DD0):
    sites = text_imm_sites(g)
    print(f"  [{g:08X}] section={sec_of(g)}  referenced from {len(sites)} site(s)")
