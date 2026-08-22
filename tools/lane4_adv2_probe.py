#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ADVERSARIAL verify part 2: full sub_7E8510 body + callers + builder."""
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

def dis(va, count=60):
    o = va2off(va); out = []
    for ins in MD.disasm(DATA[o:o+count*16], va):
        out.append(ins)
        if len(out) >= count: break
    return out

def show(va, count, tag=""):
    print("--- %s @ 0x%08X ---" % (tag, va))
    for ins in dis(va, count):
        print("  0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

print("=== callers of sub_7E8510 (rel32 e8/e9) ===")
for n, sva, vsize, roff, rsize in SECS:
    if n != ".text": continue
    tsz = max(vsize, rsize)
    for k in range(tsz - 5):
        c = DATA[roff + k]
        if c in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", DATA, roff + k + 1)[0]
            tgt = IMAGE_BASE + sva + k + 5 + rel
            if tgt == 0x7E8510:
                print("   caller site 0x%08X (%s)" % (IMAGE_BASE + sva + k,
                      "call" if c == 0xE8 else "jmp"))

print("\n=== FULL BODY sub_7E8510 (0x7E8510..0x7E8A83) ===")
va = 0x7E8510
o = va2off(va)
buf = DATA[o:o + (0x7E8A90 - 0x7E8510)]
for ins in MD.disasm(buf, va):
    if ins.address >= 0x7E8A83: break
    print("  0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
