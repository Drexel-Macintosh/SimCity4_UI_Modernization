# lin.py - linear disassembly of [start,end) to stdout (skipdata on), used for call-site reads.
# usage: python lin.py 0x76D3D0 0x76E400 > out.txt
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

a = int(sys.argv[1], 16)
b = int(sys.argv[2], 16)
md.skipdata = True
code = rd(a, b - a)
for ins in md.disasm(code, a):
    print(fmt(ins))
