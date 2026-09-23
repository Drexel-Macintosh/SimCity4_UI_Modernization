# qi_check.py - disassemble the claimed QueryInterface bodies and the cGZWin QI they chain to.
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

for name, va in [("cGZGraph QI? 0x9B1E73", 0x9B1E73),
                 ("cGZLineGraph QI? 0x9B28CE", 0x9B28CE),
                 ("type2 QI? 0x9B2943", 0x9B2943),
                 ("cGZScatterGraph QI? 0x9B2A38", 0x9B2A38),
                 ("type3 QI? 0x9B2BEF", 0x9B2BEF),
                 ("cGZWin QI? 0x99B774", 0x99B774)]:
    print("=====", name)
    dump(va, 40, stop_at_ret=False)
    print()
