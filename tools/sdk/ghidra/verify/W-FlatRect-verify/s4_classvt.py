"""Step 4: class vtable diff FlatRect 0xAE20A0 vs AlertBorder 0xAB5B48 (151 slots each),
GZPaint body, dtor, base-QI fallthrough, cIGZWin slots named by the finder."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

CVT = 0xAE20A0
AB = 0xAB5B48
diff = [i for i in range(151) if u32(CVT + 4 * i) != u32(AB + 4 * i)]
print("class-vt slots where FlatRect != AlertBorder:", diff)
for i in diff:
    a, b = u32(CVT + 4 * i), u32(AB + 4 * i)
    fa, da, ca = resolve(a)
    print(f"  slot {i:3} (+{4*i:#05x}) FR {a:08X} -> {fa:08X}   AB {b:08X}")

# what does the finder's file say?
p = r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-FlatRect\classvt_vs_alertborder.txt"
print("\n(finder's file head, for comparison)")
print(open(p).read()[:1500])

# is AlertBorder the right base reference? find a plain cGZWin class vtable: whose ctor 0x99D938 stores?
print("\n== base ctor 0x99D938 (called by FlatRect ctor) vtable stores")
b = fn(0x99D938, 200)
for i in b:
    if i.mnemonic == "mov" and "0x" in i.op_str and "dword ptr [" in i.op_str.split(",")[0]:
        try:
            v = int(i.op_str.split(",")[1].strip(), 16)
            if secname(v) == ".rdata":
                print(f"  {i.address:08X}: {i.mnemonic} {i.op_str}")
        except ValueError:
            pass
