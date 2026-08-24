#!/usr/bin/env python3
"""For each dword ref to a global, look at preceding opcode bytes and flag
likely WRITES (mov [g],reg / mov [g],imm) vs reads. Prints VA and 8 bytes
before + 4 after."""
import struct, sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\research\_scratch_zots")
from find_refs import load, off_to_va

GAME_EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

def main():
    data, base, secs = load(GAME_EXE)
    for arg in sys.argv[1:]:
        t = int(arg, 0)
        needle = struct.pack("<I", t)
        i = 0
        print(f"=== {t:#010x} ===")
        while True:
            i = data.find(needle, i)
            if i < 0:
                break
            va, sec = off_to_va(i, base, secs)
            if sec == ".text":
                pre = data[i-2:i]
                tag = ""
                if pre[1:] == b"\xA3":
                    tag = "WRITE mov [g],eax"
                elif pre[0:1] == b"\x89" and pre[1] in (0x05,0x0D,0x15,0x1D,0x25,0x2D,0x35,0x3D):
                    tag = f"WRITE mov [g],r{(pre[1]>>3)&7}"
                elif pre == b"\xC7\x05":
                    tag = "WRITE mov [g],imm(next4)"
                if tag:
                    ctx = data[i-6:i+8].hex()
                    print(f"  {va:#010x} {tag}  ctx {ctx}")
            i += 1

if __name__ == "__main__":
    main()
