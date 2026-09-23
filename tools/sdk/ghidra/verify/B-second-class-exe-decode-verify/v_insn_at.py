# Find the instruction that contains a given code address, by majority vote over
# many linear-sweep start points (x86 self-synchronises within a few bytes).
from collections import Counter

def insn_containing(p, site, lo=0x60, hi=0x20):
    votes = Counter(); keep = {}
    for st in range(site - lo, site - hi):
        for ins in p.md.disasm(p.bytes(st, (site - st) + 16), st):
            if ins.address <= site < ins.address + ins.size:
                key = (ins.address, ins.size)
                votes[key] += 1; keep[key] = ins
                break
            if ins.address > site:
                break
    if not votes:
        return None, 0
    key, n = votes.most_common(1)[0]
    return keep[key], n
