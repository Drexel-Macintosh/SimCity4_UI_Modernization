"""Step 3: disassemble slot implementations.
usage: python s3_dis.py <vt_hex> <slot> [<slot> ...]     (slot ranges like 118-128 ok)
       python s3_dis.py va <hex_va> [maxins]"""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from pe import *

def slots(args):
    for a in args:
        if "-" in a:
            x, y = a.split("-")
            yield from range(int(x), int(y) + 1)
        else:
            yield int(a)

if __name__ == "__main__":
    if sys.argv[1] == "va":
        va = int(sys.argv[2], 16)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        print(f"--- {va:#x}")
        print(fmt(dis_fn(va, maxins=n)))
        sys.exit()
    vt = int(sys.argv[1], 16)
    tab = vtable(vt)
    for s in slots(sys.argv[2:]):
        f = tab[s]
        print(f"--- slot {s} (+{s*4:#x}) -> {f:#x}")
        print(fmt(dis_fn(f, maxins=120)))
