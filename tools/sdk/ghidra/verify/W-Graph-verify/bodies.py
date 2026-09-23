# bodies.py - dump function bodies (linear, up to the first ret) for semantic slot checks.
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

FUNCS = [int(x, 16) for x in sys.argv[1:]]
for va in FUNCS:
    print("===== 0x%08X" % va)
    n = 0
    code = rd(va, 0x400)
    for ins in md.disasm(code, va):
        print(fmt(ins))
        n += 1
        if ins.mnemonic == "ret" or n > 160:
            break
        if ins.mnemonic == "int3":
            break
    print()
