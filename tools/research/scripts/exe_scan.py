#!/usr/bin/env python3
"""Scan SimCity 4.exe .text for 32-bit immediates (rebuilt after scratchpad wipe).

Usage: exe_scan.py <hex-imm> [hex-imm ...]
Prints every VA where the little-endian dword appears in .text.
ImageBase 0x400000; .text raw offset == RVA for 0x7000..0x680000.
"""
import sys
import struct

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
BASE = 0x400000
TEXT_LO, TEXT_HI = 0x7000, 0x680000

def main():
    with open(EXE, "rb") as f:
        data = f.read()
    text = data[TEXT_LO:TEXT_HI]
    for arg in sys.argv[1:]:
        imm = int(arg, 16)
        needle = struct.pack("<I", imm)
        hits = []
        i = text.find(needle)
        while i != -1:
            hits.append(BASE + TEXT_LO + i)
            i = text.find(needle, i + 1)
        print("0x%08X: %d hit(s): %s" % (
            imm, len(hits), " ".join("0x%X" % h for h in hits[:40])))

if __name__ == "__main__":
    main()
