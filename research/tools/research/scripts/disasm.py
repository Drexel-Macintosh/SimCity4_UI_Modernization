#!/usr/bin/env python3
"""Disassemble a VA range of SimCity 4.exe (rebuilt after scratchpad wipe).

Usage: disasm.py <startVA> <endVA>
File offset = VA - 0x400000 for .text (raw==RVA there).
"""
import sys
import capstone

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
BASE = 0x400000

def main():
    lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
    with open(EXE, "rb") as f:
        f.seek(lo - BASE)
        code = f.read(hi - lo)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.skipdata = True
    for ins in md.disasm(code, lo):
        print("0x%X\t%s\t%s" % (ins.address, ins.mnemonic, ins.op_str))

if __name__ == "__main__":
    main()
