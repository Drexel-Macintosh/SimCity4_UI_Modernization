# Count 'call/jmp dword ptr [reg + disp32]' sites for given vtable offsets,
# verifying each byte hit decodes as that instruction under majority-vote sync.
import sys, re
from v_pe import PE
from v_insn_at import insn_containing
p = PE()
text = [s for s in p.secs if s[0] == '.text'][0]
raw = p.data[text[3]:text[3]+text[4]]
base = text[1]

def sites(disp, kinds=('call', 'jmp')):
    out = []
    d = disp.to_bytes(4, 'little')
    for modrm_base, kind in ((0x90, 'call'), (0xA0, 'jmp')):
        if kind not in kinds: continue
        for r in range(8):
            if r == 4: continue  # SIB form, skip
            pat = bytes([0xFF, modrm_base | r]) + d
            start = 0
            while True:
                i = raw.find(pat, start)
                if i < 0: break
                va = base + i
                ins, votes = insn_containing(p, va + 1)
                real = ins is not None and ins.address == va and ins.mnemonic == kind
                out.append((va, kind, real, ins.op_str if ins else None))
                start = i + 1
    return sorted(out)

if __name__ == '__main__':
    for a in sys.argv[1:]:
        disp = int(a, 16)
        s = sites(disp)
        real = [x for x in s if x[2]]
        print('disp 0x%X (slot %d): %d byte hits, %d real' % (disp, disp // 4, len(s), len(real)))
        for va, kind, ok, op in s:
            print('   %08X %s %s %s' % (va, kind, op, '' if ok else '(NOT an instruction start)'))
