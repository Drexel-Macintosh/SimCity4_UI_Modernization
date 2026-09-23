# vt_check.py - for every claimed graph vtable: extent (exec pointers until a non-exec dword),
# the dwords before/after, and every .text instruction that references the table address.
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

CLAIMS = [
    ("cSC4LineGraph main", 0xAB4D08, 178),
    ("cSC4LineGraph cIGZGraph", 0xAB4C28, 55),
    ("cSC4LineGraph cIGZLineGraph", 0xAB4B98, 35),
    ("cGZLineGraph main", 0xADF2E8, 178),
    ("cGZLineGraph cIGZGraph", 0xADF208, 55),
    ("cGZLineGraph cIGZLineGraph", 0xADF5B0, 35),
    ("pure cIGZLineGraph", 0xADE0F0, 35),
    ("type2 main", 0xADE648, 178),
    ("type2 cIGZGraph", 0xADE568, 55),
    ("type2 iface", 0xADE910, 40),
    ("pure type2", 0xADDE50, 40),
    ("scatter main", 0xADEA90, 178),
    ("scatter cIGZGraph", 0xADE9B0, 55),
    ("scatter iface", 0xADED58, 33),
    ("pure scatter", 0xADDEF0, 33),
    ("type3 main", 0xADEEC0, 178),
    ("type3 cIGZGraph", 0xADEDE0, 55),
    ("type3 iface", 0xADF188, 31),
    ("pure type3", 0xADDF78, 31),
    ("cGZGraph main", 0xADE188, 178),
    ("cGZGraph cIGZGraph", 0xADE450, 55),
    ("pure cIGZGraph", 0xADDFF8, 55),
    ("control cSC4WinAlertBorder main", 0xAB5B48, 148),
]

def xrefs(va):
    out = []
    for h in scan_dword(va):
        for ins in insn_covering(h):
            # keep only decodes whose immediate/disp equals va
            if ("0x%x" % va) in ins.op_str:
                out.append(fmt(ins))
    return out

for name, va, claimed in CLAIMS:
    t = vtable(va, 400)
    prev = u32(va - 4)
    print("== %-32s 0x%08X claimed %3d | exec-run %3d | dword@-4 = 0x%08X (%s) | first non-exec after run = 0x%08X" % (
        name, va, claimed, len(t), prev, sec_of(prev) or "-", u32(va + 4 * len(t))))
    for x in xrefs(va):
        print("      xref " + x)
