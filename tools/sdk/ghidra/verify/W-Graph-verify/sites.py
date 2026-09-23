# sites.py - for each claimed constant site, print the instruction AT that VA plus the following
# instructions up to and including the next call (to see which call consumes it).
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

SITES = {
    "axes w1 a": 0x9B250B, "axes w1 b": 0x9B253A, "win border": 0x9B396A, "plot frame": 0x9B3A58,
    "vtick1": 0x9B3B65, "vtick2": 0x9B3BA2, "vtick3": 0x9B3CB9, "vtick4": 0x9B3CF7,
    "ctick1": 0x9B473D, "ctick2": 0x9B4784, "ctick3": 0x9B4893, "ctick4": 0x9B48D3,
    "bar frame": 0x9B5581, "textitem frame": 0x9B408E, "swatch frame (builder)": 0x76E250,
    "Ylabel dec dec": 0x9B7FE0, "Xlabel +2": 0x9B7E4C, "hpad a": 0x9B7E50, "hpad b": 0x9B8063,
    "cat pad a": 0x9B8507, "cat pad b": 0x9B8508, "cat pad c": 0x9B86CF,
    "title margin 4": 0x9B3884, "minor tick 2": 0x9B768D, "major tick 4": 0x9B7686, "title band 32": 0x9B75B4,
    "line item w": 0x9B5A6B, "rect item w": 0x9B40FF, "arc item w": 0x9B4117,
    "series line width": 0x76C3B8, "bottom gutter 20 (0x76DD4B)": 0x76DD4B,
}
for name, va in SITES.items():
    ins = one(va)
    print("== %-28s 0x%08X : %s" % (name, va, ("%s %s  [%s]" % (ins.mnemonic, ins.op_str, ins.bytes.hex())) if ins else "??"))
    for i in dis(va, 14, stop_at_ret=False)[1:]:
        print("      " + fmt(i))
        if i.mnemonic == "call" or i.mnemonic == "ret":
            break
