# W-Grid-verify step 7: independent null test for SetCellGutters (grid vt+0x68, 4 args).
# Method (different from the finder's "420 insns after each site"):
#  1. linear-sweep the WHOLE .text once (capstone, resync on failure), collect every
#     'call dword ptr [reg + 0x68]' and 'call dword ptr [reg + 0x60]' and count the pushes
#     since the previous call/ret/jmp (arg-count proxy).
#  2. grid-context windows = [site-0x1000, site+0x1800] around every grid acquisition
#     (49 IID push sites, 10 ctor call sites).
#  3. report 4-push +0x68 calls inside grid windows (candidates) and, as positive control,
#     4-push +0x60 (SetGutters) calls inside the same windows.
#  4. also: E8 calls straight to 0x9A6462 (SetCellGutters impl) / 0x9A63F4 (SetGutters impl).
import struct
from vpe import PE
pe = PE()
t = pe.text()
base, size = t[1], t[2]
blob = pe.data[t[3]:t[3]+t[4]]

calls68, calls60 = [], []
va = base
end = base + min(size, t[4])
pushes = 0
md = pe.md
while va < end:
    off = va - base
    got = False
    for ins in md.disasm(blob[off:off+0x4000], va):
        got = True
        m = ins.mnemonic
        if m == 'push':
            pushes += 1
        elif m == 'call':
            op = ins.op_str
            if op.startswith('dword ptr [') and op.endswith('+ 0x68]'):
                calls68.append((ins.address, pushes))
            elif op.startswith('dword ptr [') and op.endswith('+ 0x60]'):
                calls60.append((ins.address, pushes))
            pushes = 0
        elif m in ('ret', 'jmp', 'int3') or m.startswith('j'):
            pushes = 0
        va = ins.address + ins.size
    if not got:
        va += 1
        pushes = 0

grid_sites = [s for s in pe.find_bytes(b'\x68' + struct.pack('<I', 0xDAA6B9BE), '.text')]
ctor_sites = pe.call_targets_to(0x9ABC95)
anchors = sorted(set(grid_sites + ctor_sites))
def in_win(a):
    return any(s - 0x1000 <= a <= s + 0x1800 for s in anchors)

print('whole .text: call [reg+0x68] =', len(calls68), ' call [reg+0x60] =', len(calls60))
c68 = [(a, p) for a, p in calls68 if in_win(a)]
c60 = [(a, p) for a, p in calls60 if in_win(a)]
print('inside grid windows: +0x68 calls', len(c68), ' of which >=4 pushes:', [(hex(a), p) for a, p in c68 if p >= 4])
print('inside grid windows: +0x60 calls', len(c60), ' of which >=4 pushes:', [(hex(a), p) for a, p in c60 if p >= 4])
print('E8 calls to 0x9A6462 (SetCellGutters impl):', [hex(x) for x in pe.call_targets_to(0x9A6462)])
print('E8 calls to 0x9A63F4 (SetGutters impl):', [hex(x) for x in pe.call_targets_to(0x9A63F4)])
print('E8 calls to 0x9A642D (GetCellGutters impl):', [hex(x) for x in pe.call_targets_to(0x9A642D)])
print('imm32 refs to 0x9A6462 anywhere:', [hex(x) for x in pe.find_bytes(struct.pack('<I', 0x9A6462))])
# any direct writes to grid +0x100..+0x10C outside the grid's own code range 0x9A5C00..0x9B0000?
