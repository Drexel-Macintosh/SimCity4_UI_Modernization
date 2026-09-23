"""Step 3: every cIGZWinFlatRect iface slot at 0xAE2050 -> resolve thunk
chain -> print final body with its ret-N set. Also which class-vt slots
(FlatRect 0xAE20A0, AlertBorder 0xAB5B48) hold each chain element."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

FR = 0xAE2050
CVT = 0xAE20A0
AB = 0xAB5B48


def slots_of(t):
    a = [i for i in range(151) if u32(CVT + 4 * i) == t]
    b = [i for i in range(151) if u32(AB + 4 * i) == t]
    return f"FlatRect-cls{a} AlertBorder-cls{b}"


for s in range(20):
    va = u32(FR + 4 * s)
    final, delta, chain = resolve(va)
    print(f"\n######## iface slot {s} (vt+{4*s:#x}) = {va:08X}  chain {' -> '.join(f'{c:08X}' for c in chain)}  this{delta:+#x}")
    for c in chain:
        print(f"    {c:08X}: {slots_of(c)}")
    print(f"    final rets: {rets(final)}")
    print(fmt(fn(final, 120), "      "))
