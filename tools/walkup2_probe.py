#!/usr/bin/env python3
"""Walk UP from the fault chain, identifying each level by (a) vtable membership
(any .rdata/.data dword equal to the fn VA) and (b) ASCII strings referenced
inside the function. Read-only."""
import sys, struct, bisect
from pe109_probe import *

data, secs = load()
starts = function_starts(data, secs)
S = sorted(starts)

def encl(va):
    i = bisect.bisect_right(S, va) - 1
    return S[i] if i >= 0 else None

def strings_in(va, span=0x1200):
    out = []
    for ins in disasm(data, secs, va, span):
        cands = []
        for op in ins.operands:
            if op.type == X86_OP_IMM:
                cands.append(op.imm)
            elif op.type == X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
                cands.append(op.mem.disp)
        for c in cands:
            if not (0x400000 < c < 0x400000 + 0x800000):
                continue
            o = va2off(secs, c)
            if o is None:
                continue
            b = data[o:o + 80]
            e = b.find(b"\0")
            if e < 5:
                continue
            s = b[:e]
            if all(32 <= ch < 127 for ch in s):
                out.append((ins.address, c, s.decode("latin1")))
    return out

def vt_refs(va):
    return [(n, hex(v)) for n, v in find_dword_refs(data, secs, va)
            if n in (".rdata", ".data")]

def report(va, label):
    cs = callers_of(data, secs, va)
    js = jmp_callers_of(data, secs, va)
    parents = sorted({encl(s) for s in cs} | {encl(s) for s in js})
    print(f"\n### {label} {hex(va)}")
    print(f"   call sites: {[hex(x) for x in cs][:20]}")
    if js: print(f"   tail-jmp  : {[hex(x) for x in js][:12]}")
    print(f"   parents   : {[hex(x) for x in parents if x]}")
    v = vt_refs(va)
    if v: print(f"   *** VTABLE/DATA dword refs: {v[:8]}")
    ss = strings_in(va)
    if ss:
        seen2 = set(); uniq = []
        for a, c, s in ss:
            if s not in seen2:
                seen2.add(s); uniq.append(s)
        print(f"   strings   : {uniq[:16]}")
    return [p for p in parents if p]

frontier = [(0x007A2740, "TOP")]
seen = set()
lvl = 0
while frontier and lvl < 7:
    print("=" * 78)
    print(f"LEVEL {lvl}")
    print("=" * 78)
    nxt = []
    for va, lab in frontier:
        if va in seen: continue
        seen.add(va)
        for p in report(va, lab):
            if p not in seen:
                nxt.append((p, f"L{lvl+1}"))
    frontier = nxt
    lvl += 1
