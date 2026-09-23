"""Resolve every slot of a Windows vtable: follow adjustor thunks, report the
callee-cleaned byte count (ret N -> N/4 stack args under __thiscall), and the
first instructions. Compare against the Mac slot list from SimCity4.gdt.json.
usage: python slots.py <vtable_va_hex> <count> [MacVftableName]"""
import sys, json, re
from pe import *

GDT = r"C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json"

def resolve(va, depth=0):
    """follow 'sub ecx,N ; jmp X' / 'jmp X' / 'add ecx,N; jmp X' thunks"""
    adj = 0
    for _ in range(4):
        ins = dis(va, 16, maxins=2)
        if not ins: break
        i0 = ins[0]
        if i0.mnemonic == 'jmp' and i0.op_str.startswith('0x'):
            va = int(i0.op_str, 16); continue
        if i0.mnemonic in ('sub', 'add') and i0.op_str.startswith('ecx, ') and len(ins) > 1 and ins[1].mnemonic == 'jmp' and ins[1].op_str.startswith('0x'):
            n = int(i0.op_str.split(', ')[1], 16)
            if n > 0x7fffffff: n -= 0x100000000
            adj += (-n if i0.mnemonic == 'sub' else n)
            va = int(ins[1].op_str, 16); continue
        break
    return va, adj

def retn(va, limit=0x1800):
    """first ret in linear sweep; returns imm (0 for plain ret)"""
    for ins in dis(va, limit):
        if ins.mnemonic == 'ret':
            return int(ins.op_str, 16) if ins.op_str else 0
        if ins.mnemonic == 'int3':
            return None
    return None

def mac_argbytes(name):
    # crude Itanium arg-count from the mangled tail
    m = re.search(r'E([^E]*)$', name)
    return None

def mac_slots(vname):
    d = json.load(open(GDT))
    for t in d['types']:
        if t['path'] == '/' + vname:
            return {f['off'] // 4: f['name'] for f in t['fields']}
    return {}

if __name__ == '__main__':
    base = int(sys.argv[1], 16); n = int(sys.argv[2])
    mac = mac_slots(sys.argv[3]) if len(sys.argv) > 3 else {}
    for i in range(n):
        p = u32(base + 4 * i)
        tgt, adj = resolve(p)
        r = retn(tgt)
        head = '; '.join('%s %s' % (x.mnemonic, x.op_str) for x in dis(tgt, 0x40, maxins=6))
        mn = mac.get(i, '')
        mn = re.sub(r'^__ZThn\d+_N\d+', '', mn)
        print('%2d %08X -> %08X adj%+5d ret%-4s | %-60s | %s' % (i, p, tgt, adj, r, mn[:60], head[:150]))
