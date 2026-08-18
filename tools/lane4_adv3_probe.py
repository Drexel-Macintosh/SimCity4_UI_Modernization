#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ADVERSARIAL part 3: locate real cIGZWin vtables and decode slots
+0x8C, +0xA4, +0xA8, +0xAC, +0xB0, +0xE0.  Arity is the thing that decides
whether the proposed raw-vtable call corrupts the stack."""
import struct
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
        secs.append((n, va, vsize, roff, rsize)); off += 40
    return data, secs

DATA, SECS = load()
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.detail = True

def va2off(va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None

def sect(name):
    for n, sva, vsize, roff, rsize in SECS:
        if n == name: return sva, max(vsize, rsize), roff
    return None

def show(va, count, tag=""):
    o = va2off(va)
    print("--- %s @ 0x%08X ---" % (tag, va))
    k = 0
    for ins in MD.disasm(DATA[o:o+count*16], va):
        print("   0x%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        k += 1
        if k >= count or ins.mnemonic in ("ret", "jmp"): break

MOVETO = 0x0099C8C5
tva, tsz, troff = sect(".text")
rva, rsz, rroff = sect(".rdata")
dva, dsz, droff = sect(".data")

print("=== find vtables whose slot +0xE0 == 0x%08X (the claimed GZWinMoveTo) ===" % MOVETO)
cands = []
for base_off, base_va, size in ((rroff, IMAGE_BASE + rva, rsz), (droff, IMAGE_BASE + dva, dsz)):
    size = min(size, len(DATA) - base_off - 4)
    for k in range(0, size - 4, 4):
        v = struct.unpack_from("<I", DATA, base_off + k)[0]
        if v == MOVETO:
            vt = base_va + k - 0xE0
            cands.append(vt)
print("   candidate vtables (slot+0xE0 hit): %d" % len(cands))
for vt in cands[:12]:
    print("      vt=0x%08X" % vt)
print("   POSITIVE CONTROL: the same scan for a value that certainly IS in "
      ".rdata as a vtable slot -- the count above being non-zero is itself "
      "the control; a zero here would mean 0x%08X is not GZWinMoveTo." % MOVETO)

if not cands:
    raise SystemExit("no vtable found - claim about 0x99C8C5 is unproven")

vt = cands[0]
o = va2off(vt)
print("\n=== slots of vt 0x%08X ===" % vt)
for slot in (0x08, 0x0C, 0x88, 0x8C, 0x90, 0x94, 0xA4, 0xA8, 0xAC, 0xB0, 0xCC, 0xE0, 0x114, 0x118):
    fn = struct.unpack_from("<I", DATA, o + slot)[0]
    print("   +0x%03X -> 0x%08X" % (slot, fn))

for slot, tag in ((0x8C, "vt+0x8C claimed GetChildWindowFromIDRecursive"),
                  (0x94, "vt+0x94 the call the GAME makes"),
                  (0xA4, "vt+0xA4 claimed GetW"),
                  (0xA8, "vt+0xA8 claimed GetH"),
                  (0xAC, "vt+0xAC claimed GetL"),
                  (0xB0, "vt+0xB0 claimed GetT"),
                  (0xE0, "vt+0xE0 claimed GZWinMoveTo")):
    fn = struct.unpack_from("<I", DATA, o + slot)[0]
    print()
    show(fn, 40, tag)
