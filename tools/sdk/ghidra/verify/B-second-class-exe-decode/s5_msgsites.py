"""Step 5: find message-construction sites in the GZ framework range (0x940000-0xA00000):
a store of a small immediate (candidate GZ message type) into a stack/struct slot, followed
within 30 instructions by a call through a vtable at +0xC (DoMessage), +0x240/+0x244
(SendMsg), +0x248/+0x24C (PostMsg), or +0x3C (window manager post). Prints the site, the
immediate, and the call. Candidate finder only - each hit is then read with s3_dis.py."""
import re, sys
from collections import defaultdict
here = __file__.rsplit("\\", 1)[0]
L = open(here + "\\sweep.txt").read().splitlines()
TYPES = {3, 4, 16, 17, 18, 19, 20, 14, 5, 6, 7, 8, 10, 11, 13, 1}
store = re.compile(r"^([0-9A-F]{8}) mov dword ptr \[([a-z]+) ([-+]) (0x[0-9a-f]+)\], (0x[0-9a-f]+|\d+)$")
call = re.compile(r"call dword ptr \[[a-z]+ \+ (0xc|0x240|0x244|0x248|0x24c|0x3c)\]$")
lo, hi = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x940000, int(sys.argv[2], 16) if len(sys.argv) > 2 else 0xA00000
res = defaultdict(list)
for i, l in enumerate(L):
    m = store.match(l)
    if not m:
        continue
    a = int(m.group(1), 16)
    if not (lo <= a < hi):
        continue
    v = int(m.group(5), 16) if m.group(5).startswith("0x") else int(m.group(5))
    if v not in TYPES:
        continue
    for j in range(i + 1, min(i + 30, len(L))):
        c = call.search(L[j])
        if c:
            res[v].append((m.group(1), m.group(2) + m.group(3) + m.group(4), L[j]))
            break
        if " ret" in L[j]:
            break
for v in sorted(res):
    print(f"type {v}: {len(res[v])} sites")
    for s in res[v][:25]:
        print("   ", s)
