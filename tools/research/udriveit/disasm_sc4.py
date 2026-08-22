#!/usr/bin/env python3
"""dis.py - tiny capstone helper for SimCity 4.exe (base 0x400000, file offset
= VA - 0x400000 for .text/.rdata/.data). Usage: python dis.py <hexVA> [count]"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
data = open(EXE, "rb").read()

def dis(va, n=120):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    off = va - 0x400000
    out = []
    for i, ins in enumerate(md.disasm(data[off:off+16*n], va)):
        out.append("%08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if i >= n: break
    return out

if __name__ == "__main__":
    va = int(sys.argv[1], 16)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    print("\n".join(dis(va, n)))
