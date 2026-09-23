"""Step 4b: compare FlatRect class vt against the cGZWin base vtable stored by the
base ctor 0x99D938 (0xADC8D8), not just against AlertBorder."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

CVT = 0xAE20A0
AB = 0xAB5B48
GZ = 0xADC8D8
n = 0
while is_text(u32(GZ + 4 * n)):
    n += 1
print("cGZWin base vt 0xADC8D8 run of .text ptrs:", n, "refs:", [hex(x) for x in find_imm32(GZ)])
print("prev dword", hex(u32(GZ - 4)), secname(u32(GZ - 4)))
dFR = [i for i in range(151) if u32(CVT + 4 * i) != u32(GZ + 4 * i)]
dAB = [i for i in range(151) if u32(AB + 4 * i) != u32(GZ + 4 * i)]
print("FlatRect differs from cGZWin base at:", dFR)
print("AlertBorder differs from cGZWin base at:", dAB)
for i in sorted(set(dFR) | set(dAB)):
    g = u32(GZ + 4 * i)
    f = u32(CVT + 4 * i)
    a = u32(AB + 4 * i)
    print(f"  slot {i:3} base {g:08X} ({secname(g)})  FR {f:08X} -> {resolve(f)[0]:08X}   AB {a:08X}")
# is base slot 0 purecall?
print("purecall = 0x5D4A10; base slots that are purecall:", [i for i in range(151) if u32(GZ + 4 * i) == 0x5D4A10])
