"""Step 7: call-site windows. For each anchor, find a decode start that lands
exactly on the anchor, print [anchor-back .. anchor+fwd]."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *


def synced_start(anchor, back):
    for b in range(back, back + 40):
        st = anchor - b
        for ins in md.disasm(rd(st, b + 8), st):
            if ins.address == anchor:
                return st
            if ins.address > anchor:
                break
    return anchor


def window(anchor, back=0x60, fwd=0x120):
    st = synced_start(anchor, back)
    return fmt(disrange(st, anchor + fwd), "   ")


if __name__ == "__main__":
    for a in sys.argv[1:]:
        parts = a.split(":")
        anc = int(parts[0], 16)
        back = int(parts[1], 16) if len(parts) > 1 else 0x60
        fwd = int(parts[2], 16) if len(parts) > 2 else 0x120
        print(f"\n==== window around {anc:08X}")
        print(window(anc, back, fwd))
