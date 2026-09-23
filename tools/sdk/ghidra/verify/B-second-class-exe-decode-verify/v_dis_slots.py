# Disassemble the base cGZWin implementation of a list of slots (to ret).
import sys, re
from v_pe import PE
p = PE()
BASE = 0xADC8D8

def body(va, maxbytes=0x300, stop_at_first_ret=True):
    out = []
    for ins in p.md.disasm(p.bytes(va, maxbytes), va):
        out.append(ins)
        if ins.mnemonic == 'ret' and stop_at_first_ret:
            break
        if ins.mnemonic == 'jmp' and not ins.op_str.startswith('0x9') and stop_at_first_ret and False:
            break
    return out

def annotate(ins):
    s = '  %08X  %-7s %s' % (ins.address, ins.mnemonic, ins.op_str)
    m = re.search(r'\[(e[a-d]x|e[sd]i) \+ (0x[0-9a-f]+)\]', ins.op_str)
    if ins.mnemonic == 'call' and m:
        off = int(m.group(2), 16)
        if off % 4 == 0 and off < 0x400:
            s += '    ; vt slot %d?' % (off // 4)
    return s

if __name__ == '__main__':
    slots = [int(a) for a in sys.argv[1:]]
    for s in slots:
        va = p.u32(BASE + 4*s)
        print('==== slot %d  vt+0x%X  base %08X' % (s, 4*s, va))
        for i in body(va):
            print(annotate(i))
