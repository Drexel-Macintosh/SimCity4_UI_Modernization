"""Step 18: bound the 'no SetSizeMode 1/2/3/4/6' null better.
(a) every 'call [reg+0x74]' within 0x200 bytes after a cIGZWinGen IID
    (0x5386D516) immediate - candidate cIGZWinGen slot 29 (FlatRect creator)
    calls - print the 4 pushes before it.
(b) every 'push imm8 ; call [reg+0x48]' in .text with imm in 1..6, printed
    with context, as the raw universe of SetSizeMode(1..6)-shaped calls
    (noisy: vt+0x48 is slot 18 of EVERY interface)."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *
from s7_sites import synced_start

T = TEXT
blob = RAW[T[3]:T[3] + T[4]]
IIDG = 0x5386D516
hits = find_imm32(IIDG)
print(f"cIGZWinGen IID {IIDG:#x}: {len(hits)} .text hits")
seen = set()
for h in hits:
    ins = insn_containing(h)
    if not ins:
        continue
    win = disrange(ins.address, ins.address + 0x200)
    for i in win:
        if i.mnemonic == "call" and i.op_str.endswith("+ 0x74]") and i.address not in seen:
            seen.add(i.address)
            st = synced_start(i.address, 0x20)
            pre = [x for x in disrange(st, i.address) if x.address < i.address][-6:]
            print(f"  iid@{ins.address:08X} -> {i.address:08X}: " + " ; ".join(f"{x.mnemonic} {x.op_str}" for x in pre))

print("\n(b) push imm8 1..6 then call [reg+0x48] within 12 bytes:")
cnt = 0
for m in re.finditer(rb"\x6a([\x01-\x06])", blob):
    va = T[1] + m.start()
    for i in disrange(va, va + 14):
        if i.address == va:
            continue
        if i.mnemonic == "call":
            if i.op_str.endswith("+ 0x48]"):
                cnt += 1
                st = synced_start(va, 0x18)
                pre = [x for x in disrange(st, i.address + 1)][-6:]
                print(f"  {va:08X}: " + " ; ".join(f"{x.mnemonic} {x.op_str}" for x in pre))
            break
print("total:", cnt)
