# disp_writes.py - sweep ALL executable sections for memory WRITES whose displacement is in a set,
# optionally only byte-sized. usage: python disp_writes.py 0x14c,0x74 [byte]
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *
from capstone.x86 import X86_OP_MEM
from capstone import CS_AC_WRITE

disps = set(int(x, 16) for x in sys.argv[1].split(","))
only_byte = len(sys.argv) > 2 and sys.argv[2] == "byte"
md.skipdata = True
n = 0
for a, b in text_ranges():
    code = rd(a, b - a)
    for ins in md.disasm(code, a):
        if ins.mnemonic == ".byte":
            continue
        try:
            ops = ins.operands
        except Exception:
            continue
        for op in ops:
            if op.type == X86_OP_MEM and op.mem.disp in disps:
                try:
                    acc = op.access
                except Exception:
                    acc = 0
                if acc & CS_AC_WRITE:
                    if only_byte and op.size != 1:
                        continue
                    print(fmt(ins))
                    n += 1
print("total", n)
