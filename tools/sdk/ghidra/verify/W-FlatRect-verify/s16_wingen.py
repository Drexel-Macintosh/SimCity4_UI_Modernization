"""Step 16: cIGZWinGen iface vtable 0xADC5F8 - slots 0..32, esp. 24..30;
which vtables carry 0x9999BA; the gutter setter 0x99919B."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

V = 0xADC5F8
n = 0
while is_text(u32(V + 4 * n)):
    n += 1
print(f"vt {V:08X}: run {n}; refs {[hex(x) for x in find_imm32(V)]}; prev {u32(V-4):08X} ({secname(u32(V-4))})")
for s in range(min(n, 34)):
    va = u32(V + 4 * s)
    f, d, ch = resolve(va)
    b = fn(f, 12)
    print(f"  slot {s:2} {va:08X} -> {f:08X} (this{d:+#x}) rets {rets(f)} :: " + " ; ".join(f"{i.mnemonic} {i.op_str}" for i in b)[:230])

# which rdata dwords hold 0x9999BA?
hold = find_imm32(0x9999BA, ".rdata")
print("\n.rdata dwords == 0x9999BA:", len(hold), [hex(h) for h in hold])
print("\n.text refs to 0x9999BA (direct calls use rel32, so this only finds imm uses):", [hex(h) for h in find_imm32(0x9999BA)])
