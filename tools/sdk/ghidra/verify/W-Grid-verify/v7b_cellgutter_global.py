# W-Grid-verify step 7b: global sweep for SetCellGutters-shaped calls (vt+0x68 with >=4 pushes)
# that sit near other grid-only vtable offsets (+0x104 SetColumnWidth, +0x1C0 SetCellTextValue,
# +0x10C SetRowHeight, +0x108 SetDefaultRowHeight) within +-0x300 bytes. Heuristic, prints candidates.
from vpe import PE
pe = PE()
t = pe.text()
base, size = t[1], min(t[2], t[4])
blob = pe.data[t[3]:t[3]+t[4]]
calls = []  # (addr, disp, pushes)
va = base
end = base + size
pushes = 0
while va < end:
    got = False
    for ins in pe.md.disasm(blob[va-base:va-base+0x4000], va):
        got = True
        m = ins.mnemonic
        if m == 'push':
            pushes += 1
        elif m == 'call':
            op = ins.op_str
            if op.startswith('dword ptr [') and '+ 0x' in op and op.endswith(']'):
                try:
                    disp = int(op.split('+')[-1].strip(' ]'), 16)
                    calls.append((ins.address, disp, pushes))
                except ValueError:
                    pass
            pushes = 0
        elif m in ('ret', 'jmp', 'int3') or m.startswith('j'):
            pushes = 0
        va = ins.address + ins.size
    if not got:
        va += 1; pushes = 0
import bisect
addrs = [c[0] for c in calls]
GRIDONLY = {0x104, 0x1c0, 0x10c, 0x108, 0x1c8, 0x1d0}
cands = []
for a, d, p in calls:
    if d == 0x68 and p >= 4:
        lo = bisect.bisect_left(addrs, a - 0x300); hi = bisect.bisect_right(addrs, a + 0x300)
        near = sorted(set(hex(calls[k][1]) for k in range(lo, hi) if calls[k][1] in GRIDONLY))
        if near:
            cands.append((hex(a), p, near))
print('vt+0x68 calls with >=4 pushes (whole .text):', sum(1 for c in calls if c[1] == 0x68 and c[2] >= 4))
print('of those near grid-only offsets:', len(cands))
for c in cands:
    print('  ', c)
# positive control: same heuristic for +0x60 SetGutters (4 pushes) near grid-only offsets
pc = []
for a, d, p in calls:
    if d == 0x60 and p >= 4:
        lo = bisect.bisect_left(addrs, a - 0x300); hi = bisect.bisect_right(addrs, a + 0x300)
        near = sorted(set(hex(calls[k][1]) for k in range(lo, hi) if calls[k][1] in GRIDONLY))
        if near:
            pc.append(hex(a))
print('positive control +0x60 4-push near grid-only offsets:', pc)
