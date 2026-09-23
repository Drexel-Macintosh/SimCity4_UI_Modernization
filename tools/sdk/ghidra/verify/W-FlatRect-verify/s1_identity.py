"""Step 1: sections, IID/CLSID hits, class QI, ctor, factory, registration."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vpe import *

print("BASE", hex(BASE), "size", len(RAW))
for s in SECS:
    print(f"  {s[0]:8} {s[1]:08X}-{s[2]:08X} raw@{s[3]:X} rsz={s[4]:X} vsz={s[5]:X}")

for val in (0xC2AFA76F, 0xC2AFA76E, 0xC2AF0F1A):
    hits = find_imm32(val)
    print(f"\n== {val:#010x}: {len(hits)} raw hits in .text")
    for h in hits:
        ins = insn_containing(h)
        print(f"   hit {h:08X}  insn: " + (f"{ins.address:08X} {ins.mnemonic} {ins.op_str}" if ins else "?"))
    for sn in (".rdata", ".data"):
        try:
            hh = find_imm32(val, sn)
            print(f"   in {sn}: {[hex(x) for x in hh]}")
        except IndexError:
            pass

print("\n== class QI 0x009CD1D2")
print(show(0x9CD1D2, 30))
print("\n== ctor 0x009CD842")
print(show(0x9CD842, 45))
print("\n== factory 0x0099899E")
print(show(0x99899E, 20, stop_ret=False))
print("\n== registration region 0x00998BFB")
print(show(0x998BE0, 30, stop_ret=False))
