"""Step 8: the 0x42B7C351 bar: ctor 0x99A67E, its vtables, AutoSize override,
0x998F1D min-size helper, dtor; plus cGZWinGen vt/iface claims."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

print("==== bar ctor 0x99A67E")
print(fmt(fn(0x99A67E, 120), "   "))

for vt in (0xADC398, 0xADC348):
    n = 0
    while is_text(u32(vt + 4 * n)):
        n += 1
    print(f"\n==== vt {vt:08X}: run {n} .text ptrs; refs {[hex(x) for x in find_imm32(vt)]}; prev dword {u32(vt-4):08X} ({secname(u32(vt-4))})")

FRB = 0xADC348
print("\n==== bar FR-iface vt 0xADC348 vs FlatRect FR-iface vt 0xAE2050 (20 slots)")
for s in range(21):
    a = u32(FRB + 4 * s)
    b = u32(0xAE2050 + 4 * s) if s < 20 else None
    fa = resolve(a)
    print(f"  slot {s:2}: bar {a:08X} -> {fa[0]:08X} (this{fa[1]:+#x})   flatrect {'' if b is None else f'{b:08X}'} {'SAME' if a == b else 'DIFF'}")
print("\n==== bar class vt 0xADC398 vs FlatRect class vt 0xAE20A0 (diff)")
for s in range(155):
    a = u32(0xADC398 + 4 * s)
    b = u32(0xAE20A0 + 4 * s)
    if not is_text(a):
        print("  end at slot", s, hex(a))
        break
    if a != b:
        print(f"  slot {s:3}: bar {a:08X}  flatrect {b:08X}")

print("\n==== bar AutoSize override 0x9994BF")
print(fmt(fn(0x9994BF, 150), "   "))
print("\n==== min-size helper 0x998F1D")
print(fmt(fn(0x998F1D, 150), "   "))
