#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ADVERSARIAL part 5: is vt+0xE0 absolute or relative, and does any nearby
slot implement a RELATIVE move?  UiSpike passes DELTAS to GZWinMoveTo."""
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
MD = Cs(CS_ARCH_X86, CS_MODE_32)

def va2off(va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None

def body(va, maxn=26):
    o = va2off(va)
    if o is None: return []
    out = []
    for ins in MD.disasm(DATA[o:o+maxn*16], va):
        out.append("%s %s" % (ins.mnemonic, ins.op_str))
        if ins.mnemonic in ("ret", "jmp"): break
        if len(out) >= maxn: break
    return out

# The GZWinBMP class vtable named in project memory.
for vtname, vt in (("GZWinBMP-ish 0x00ADF6A0", 0x00ADF6A0),
                   ("generic 0x00A8D000", 0x00A8D000)):
    o = va2off(vt)
    print("=" * 70)
    print("%s" % vtname)
    for slot in (0xC8, 0xCC, 0xD0, 0xD4, 0xD8, 0xDC, 0xE0, 0xE4):
        fn = struct.unpack_from("<I", DATA, o + slot)[0]
        print("  +0x%03X -> 0x%08X : %s" % (slot, fn, " | ".join(body(fn, 14))))
