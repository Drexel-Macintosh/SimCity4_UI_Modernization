"""Step 15: call sites of cIGZWin fill-colour slots 102..107 (vt+0x198..0x1AC)
and 125/126 (0x1F4/0x1F8): print the 3 instructions before each call so the
argument shape (pointer vs value vs 3 bytes) is visible."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

T = TEXT
blob = RAW[T[3]:T[3] + T[4]]
for disp in (0x198, 0x19C, 0x1A0, 0x1A4, 0x1A8, 0x1AC, 0x1F4):
    pat = re.compile(rb"\xff[\x90-\x93\x95-\x97]" + disp.to_bytes(4, "little"))
    sites = [T[1] + m.start() for m in pat.finditer(blob)]
    print(f"\n== vt+{disp:#x} (slot {disp // 4}): {len(sites)} call sites")
    for s in sites[:12]:
        st = s - 0x18
        win = disrange(st, s + 6)
        if not any(i.address == s for i in win):
            st = s - 0x19
            win = disrange(st, s + 6)
        pre = [i for i in win if i.address < s][-4:]
        print(f"  {s:08X}: " + " ; ".join(f"{i.mnemonic} {i.op_str}" for i in pre))
