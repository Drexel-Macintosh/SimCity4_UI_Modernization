"""Step 12: enumerate every (iid -> applier) registration into map 0xB6358C,
and locate the applier containing the 'autosize' token use 0x94F82D."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *
from s7_sites import synced_start

regs = []
for h in find_imm32(0xB6358C):
    ins = insn_containing(h)
    if not ins or ins.mnemonic != "mov" or not ins.op_str.startswith("ecx"):
        continue
    st = synced_start(ins.address, 0x30)
    win = disrange(st, ins.address + 16)
    iid = app = None
    for i in win:
        if i.mnemonic == "mov" and "[ebp - 8]" in i.op_str:
            v = i.op_str.split(",")[1].strip()
            iid = v
        if i.mnemonic == "mov" and "[ebp - 4]" in i.op_str:
            v = i.op_str.split(",")[1].strip()
            app = v
    regs.append((ins.address, iid, app))
for r in regs:
    print(f"  reg@{r[0]:08X} iid={r[1]} applier={r[2]}")

# which applier function contains 0x94F82D? find the nearest registered applier start <= 0x94F82D
starts = []
for r in regs:
    try:
        starts.append(int(r[2], 16))
    except (TypeError, ValueError):
        pass
starts = sorted(set(starts))
cand = [s for s in starts if s <= 0x94F82D]
print("\nnearest applier start <= 0x94F82D:", hex(max(cand)) if cand else None)
print("appliers sorted:", [hex(s) for s in starts])
