# Small recursive-descent walker: collects every ret imm reachable inside a function
# without following calls; unconditional jmps outside [entry, entry+span) are recorded as tail jumps.
from capstone import CS_GRP_JUMP

def walk(pe, entry, span=0x1800, maxins=6000):
    seen = set()
    rets = set()
    tails = []
    ind = []
    work = [entry]
    insns = {}
    while work and len(insns) < maxins:
        va = work.pop()
        while va not in seen:
            if not (entry - 0x40 <= va < entry + span):
                tails.append(va)
                break
            ins = pe.dis(va, 1, stop_at_ret=False)
            if not ins:
                break
            i = ins[0]
            seen.add(va)
            insns[va] = i
            m = i.mnemonic
            if m in ('ret', 'retn'):
                rets.add(int(i.op_str, 0) if i.op_str else 0)
                break
            if m == 'int3':
                break
            if m == 'jmp':
                op = i.op_str
                try:
                    tgt = int(op, 0)
                except ValueError:
                    ind.append((i.address, op))
                    break
                if entry <= tgt < entry + span and tgt != entry:
                    va = tgt
                    continue
                tails.append(tgt)
                break
            if m.startswith('j') or m in ('loop', 'loope', 'loopne', 'jecxz'):
                try:
                    tgt = int(i.op_str, 0)
                    work.append(tgt)
                except ValueError:
                    pass
            va = va + i.size
    return {'rets': sorted(rets), 'tails': tails, 'indirect': ind, 'insns': [insns[k] for k in sorted(insns)]}

def fmt(r, maxn=60):
    out = []
    for i in r['insns'][:maxn]:
        out.append('%08X: %s %s' % (i.address, i.mnemonic, i.op_str))
    return '\n'.join(out)
