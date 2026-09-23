"""Step 2: raw dwords around the interface vtable 0xAE2050, class vtable 0xAE20A0,
abstract vtable 0xAE2300, AlertBorder vtable 0xAB5B48. Classify each dword
(.text code / .rdata / other) and who references each vtable start."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vpe import *


def dump(lo, n, label):
    print(f"\n== {label}: {n} dwords from {lo:08X}")
    for i in range(n):
        va = lo + 4 * i
        v = u32(va)
        refs = find_imm32(va)
        rs = ",".join(f"{r:08X}" for r in refs[:6]) + ("..." if len(refs) > 6 else "")
        print(f"  {va:08X} [{(va - 0xAE2050) // 4 if 0xAE2050 <= va < 0xAE20A0 else '':>3}] = {v:08X} ({secname(v)}) xrefs-to-this-addr: {rs}")


dump(0xAE2030, 8 + 20 + 2, "around FR iface vt 0xAE2050")
# class vt 0xAE20A0: how long is it?
print("\n== class vt 0xAE20A0 length (consecutive .text pointers)")
n = 0
while is_text(u32(0xAE20A0 + 4 * n)):
    n += 1
print("  run of .text pointers:", n, " next dword:", hex(u32(0xAE20A0 + 4 * n)), secname(u32(0xAE20A0 + 4 * n)))
print("  refs to 0xAE20A0:", [hex(x) for x in find_imm32(0xAE20A0)])
print("\n== AlertBorder class vt 0xAB5B48 length")
m = 0
while is_text(u32(0xAB5B48 + 4 * m)):
    m += 1
print("  run of .text pointers:", m, " prev dword:", hex(u32(0xAB5B48 - 4)), secname(u32(0xAB5B48 - 4)))

dump(0xAE22F0, 4 + 20 + 4, "abstract vt 0xAE2300 area")
print("\n== purecall target?")
pc = u32(0xAE2300)
print(show(pc, 8))
print("refs to 0xAE2350:", [hex(x) for x in find_imm32(0xAE2350)])
for r in find_imm32(0xAE2350):
    print(show(r - 12, 8, stop_ret=False))
print("refs to 0xAE2300:", [hex(x) for x in find_imm32(0xAE2300)])
print("refs to 0xAE2050:", [hex(x) for x in find_imm32(0xAE2050)])
