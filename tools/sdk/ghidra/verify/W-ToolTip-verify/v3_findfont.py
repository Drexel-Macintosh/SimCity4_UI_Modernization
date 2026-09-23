# V3: locate the cGZFont-style vtable (cIGZFont implementer) to read the semantics of
# vt+0xB4 (6-arg CalculateTextArea) used by the callout GZPaint: args (buf,len,rect&,0,250,ebx).
# Heuristic: a vtable (dword run of code pointers referenced by a 'mov [reg],imm32') with >=57 slots
# where slot 47 (TextArea) returns with 'ret 0xC' and slot 52 (DrawTextParagraph) with 'ret 0x24'.
import sys, struct
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-ToolTip-verify")
from vpe import PE
p = PE()

def first_ret_imm(va, maxins=600):
    for ins in p.dis(va, 0x1800, maxins=maxins):
        if ins.mnemonic == 'ret':
            return int(ins.op_str, 16) if ins.op_str else 0
        if ins.mnemonic == 'jmp' and ins.op_str.startswith('0x') and ins.address == va:
            # thunk: follow
            return first_ret_imm(int(ins.op_str, 16))
    return None

rdata = [s for s in p.sections if s['name'] == '.rdata'][0]
base = rdata['va']; blob = p.data[rdata['rawptr']:rdata['rawptr'] + rdata['rawsize']]
n = len(blob) // 4
isc = [False] * n
vals = [0] * n
for i in range(n):
    v = struct.unpack_from('<I', blob, 4 * i)[0]
    vals[i] = v
    isc[i] = p.is_text(v)
res = []
i = 0
while i < n:
    if isc[i]:
        j = i
        while j < n and isc[j]:
            j += 1
        L = j - i
        if L >= 57:
            # try each start in the run such that 57 slots fit
            for s in range(i, j - 56):
                va = base + 4 * s
                r47 = first_ret_imm(vals[s + 47])
                r52 = first_ret_imm(vals[s + 52])
                if r47 == 0xC and r52 == 0x24:
                    r45 = first_ret_imm(vals[s + 45]); r46 = first_ret_imm(vals[s + 46])
                    res.append((va, L, r45, r46))
        i = j
    else:
        i += 1
for va, L, r45, r46 in res:
    refs = p.scan_dword(va)
    print('cand vt %08X run=%d slot45 ret %s slot46 ret %s refs=%s' % (va, L, r45, r46, [hex(a) for a, s in refs[:4]]))
