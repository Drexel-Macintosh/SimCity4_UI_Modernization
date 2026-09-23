# iid_scan.py - scan every section for the claimed graph IIDs + positive control 0xC2AFA76F.
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

IIDS = {
    "CONTROL cIGZWinFlatRect": 0xC2AFA76F,
    "cIGZGraph?": 0x02CF2351,
    "cIGZLineGraph?": 0x12CF2351,
    "type2?": 0x22CF2351,
    "cIGZScatterGraph?": 0x32CF2351,
    "type3?": 0x42CF2351,
    # neighbours, to see if the family has more members
    "0x52CF2351": 0x52CF2351,
    "0x62CF2351": 0x62CF2351,
    "0x72CF2351": 0x72CF2351,
    "0x82CF2351": 0x82CF2351,
    "0x92CF2351": 0x92CF2351,
    "0xA2CF2351": 0xA2CF2351,
    "0xB2CF2351": 0xB2CF2351,
    "0xC2CF2351": 0xC2CF2351,
    "0xD2CF2351": 0xD2CF2351,
    "0xE2CF2351": 0xE2CF2351,
    "0xF2CF2351": 0xF2CF2351,
}
for name, v in IIDS.items():
    hits = scan_dword_all(v)
    print("== %s 0x%08X : %d hits" % (name, v, len(hits)))
    for sec, va in hits:
        line = "   %s 0x%08X" % (sec, va)
        if is_exec(va):
            for ins in insn_covering(va):
                line += "\n        cand " + fmt(ins)
        print(line)
