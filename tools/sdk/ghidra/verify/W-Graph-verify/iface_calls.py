# iface_calls.py - heuristic whole-exe scan for calls through the cIGZGraph interface:
# 'call [reg+DISP]' where one of the 6 preceding instructions forms ecx = X+0xD8
# ('lea ecx,[r+0xd8]' or 'add ecx,0xd8'). usage: python iface_calls.py 0xc4,0xcc
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

want = set(int(x, 16) for x in sys.argv[1].split(","))
md.skipdata = True
for a, b in text_ranges():
    window = []
    for ins in md.disasm(rd(a, b - a), a):
        if ins.mnemonic == ".byte":
            window = []
            continue
        if ins.mnemonic == "call" and ins.op_str.startswith("dword ptr [e") and "+ 0x" in ins.op_str:
            try:
                d = int(ins.op_str.split("+ ")[1].rstrip("]"), 16)
            except ValueError:
                d = None
            if d in want:
                ctx = " | ".join("%s %s" % (w.mnemonic, w.op_str) for w in window[-6:])
                graphy = any((w.mnemonic == "lea" and w.op_str.startswith("ecx,") and "+ 0xd8]" in w.op_str) or
                             (w.mnemonic == "add" and w.op_str == "ecx, 0xd8") for w in window[-6:])
                if graphy:
                    print("0x%08X call vt+0x%X   ctx: %s" % (ins.address, d, ctx[:160]))
        window.append(ins)
        if len(window) > 8:
            window.pop(0)
