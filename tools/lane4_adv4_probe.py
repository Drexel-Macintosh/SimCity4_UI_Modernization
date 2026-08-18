#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ADVERSARIAL part 4: vt+0x8C ret form / AddRef, and the builder snapshot."""
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

def show(va, hi, tag=""):
    o = va2off(va)
    print("--- %s @ 0x%08X ---" % (tag, va))
    for ins in MD.disasm(DATA[o:o + (hi - va) + 16], va):
        if ins.address >= hi: break
        print("   0x%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

print("### vt+0x8C GetChildWindowFromIDRecursive body -> ret form + AddRef? ###")
show(0x0099DEC4, 0x0099DF70, "0x0099DEC4")

print("\n### builder sub_7ECF60: snapshot region 0x7ECF60 .. 0x7ED340 ###")
show(0x007ECF60, 0x007ED340, "sub_7ECF60")
