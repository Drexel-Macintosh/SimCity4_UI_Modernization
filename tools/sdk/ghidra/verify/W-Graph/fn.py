"""Recursive-descent function dump (follows jcc/jmp inside the function, not
calls; stops at ret / indirect jmp). Annotates call targets and pixel-looking
immediates.  usage: python fn.py <va_hex> [...]"""
import sys
from pe import *

JCC = {'je','jne','jz','jnz','ja','jae','jb','jbe','jg','jge','jl','jle','js','jns','jo','jno','jp','jnp','jpe','jpo','jcxz','jecxz','loop'}

def fn_insns(va, maxbytes=0x3000):
    seen = {}
    work = [va]
    while work:
        a = work.pop()
        while a not in seen:
            if a < va - 0x100 or a > va + maxbytes: break
            code = rd(a, 16)
            ins = next(md.disasm(code, a), None)
            if ins is None: break
            seen[a] = ins
            m = ins.mnemonic
            if m in ('ret', 'retn'): break
            if m == 'jmp':
                if ins.op_str.startswith('0x'):
                    t = int(ins.op_str, 16)
                    if va - 0x100 <= t <= va + maxbytes: work.append(t)
                break
            if m in JCC and ins.op_str.startswith('0x'):
                work.append(int(ins.op_str, 16))
            a += ins.size
    return [seen[k] for k in sorted(seen)]

def show(va, f=sys.stdout):
    ins = fn_insns(va)
    print('==== fn %08X  (%d insns, span %08X..%08X)' % (va, len(ins), ins[0].address, ins[-1].address + ins[-1].size), file=f)
    prev_end = None
    for i in ins:
        if prev_end is not None and i.address != prev_end:
            print('  ---- gap', file=f)
        note = ''
        if i.mnemonic == 'call' and i.op_str.startswith('0x'):
            note = ' ; -> sub_%s' % i.op_str[2:].upper()
        print('  %08X  %-22s %s %s%s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str, note), file=f)
        prev_end = i.address + i.size

if __name__ == '__main__':
    for a in sys.argv[1:]:
        show(int(a, 16))
