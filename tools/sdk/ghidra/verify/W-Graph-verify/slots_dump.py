# slots_dump.py - per-slot dump of the graph vtables: entry VA, thunk chain, final target,
# first ret found (arg bytes), first instructions of the target.
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

TABLES = {
    "sc4_line_iface": (0xAB4B98, 35),
    "gz_line_iface": (0xADF5B0, 35),
    "sc4_graph_iface": (0xAB4C28, 55),
    "gzline_graph_iface": (0xADF208, 55),
    "base_graph_iface": (0xADE450, 55),
    "type2_graph_iface": (0xADE568, 55),
    "scat_graph_iface": (0xADE9B0, 55),
    "type3_graph_iface": (0xADEDE0, 55),
    "scat_iface": (0xADED58, 33),
    "type2_iface": (0xADE910, 40),
    "type3_iface": (0xADF188, 31),
    "sc4_line_main": (0xAB4D08, 178),
    "gz_line_main": (0xADF2E8, 178),
    "base_main": (0xADE188, 178),
    "type2_main": (0xADE648, 178),
    "scat_main": (0xADEA90, 178),
    "type3_main": (0xADEEC0, 178),
    "alert_main_control": (0xAB5B48, 148),
}

which = sys.argv[1:] or list(TABLES)
for key in which:
    va, n = TABLES[key]
    print("######## %s 0x%08X (%d)" % (key, va, n))
    for s in range(n):
        e = u32(va + 4 * s)
        tgt, adj, chain = resolve_thunk(e)
        r, ra = ret_n(tgt, 300)
        ins = dis(tgt, 5, stop_at_ret=True)
        body = " | ".join("%s %s" % (i.mnemonic, i.op_str) for i in ins)
        ch = " ".join("%s" % c[1] for c in chain)
        print("%3d vt+0x%03X  0x%08X -> 0x%08X adj=%-6s ret=%-4s [%s] %s" % (
            s, 4 * s, e, tgt, ("%d" % adj) if chain else "", r, ch, body[:150]))
