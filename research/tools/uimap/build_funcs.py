"""build_funcs.py - STAGE 1b: derive the function map of .text.

Inputs : _work/calls/*.json (scan_text.py)
Outputs: funcs.json  {starts:[...], meta:{start:{callers, kind, size}}}
         _work/edges.json  (aggregated call/jmp edge list, cached)

METHOD (evidence, not guesswork)
--------------------------------
A VA is accepted as a function start when it is the target of at least one
`E8 rel32` CALL *and* the bytes immediately before it end the previous
function.  Accepted terminators, all checked as bytes:

    ..CC      int3 padding (MSVC release inter-function filler)
    ..C3      ret
    C2 ii ii  ret imm16
    E9 rr*4   jmp rel32     (tail call)
    ..EB rr   jmp rel8
    ..90      nop padding

E9 (jmp) targets are deliberately NOT used as function starts: a long
conditional/unconditional jump inside a big function would split it and
mis-attribute its call sites.  Virtual methods that are never called
directly are recovered separately from .rdata/.data vtable dwords, under
the same terminator test.

A false split is the dangerous failure here (it would hide a builder's
call sites under a phantom owner), so the terminator test is required for
*every* candidate; a bare "N callers" heuristic is only reported, never
used to split.

Work units: 'agg' (aggregate edges), 'vtab' (vtable sweep), 'build'.

Usage:
    python build_funcs.py --resume
"""
import os
import struct
import sys

import common as C

TERM_HINT = (0xCC, 0xC3, 0x90)


def preceded_by_terminator(blob, off):
    """off is a .text-relative offset of the candidate start."""
    if off <= 0:
        return True
    b1 = blob[off - 1]
    if b1 in TERM_HINT:
        return True
    if off >= 3 and blob[off - 3] == 0xC2:          # ret imm16
        return True
    if off >= 2 and blob[off - 2] == 0xEB:          # jmp rel8
        return True
    if off >= 5 and blob[off - 5] == 0xE9:          # jmp rel32
        return True
    if off >= 6 and blob[off - 6] == 0xFF and (blob[off - 5] & 0x38) == 0x20:
        return True                                  # jmp dword ptr [...]
    return False


def load_edges(st, resume):
    path = os.path.join(C.WORK, "edges.json")
    if resume and st.done("funcs", "agg") and os.path.exists(path):
        return C.jload(path)
    d = os.path.join(C.WORK, "calls")
    edges = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json"):
            edges.extend(C.jload(os.path.join(d, fn), []))
    edges.sort()
    C.jdump(path, edges)
    st.mark("funcs", "agg", "done", edges=len(edges))
    return edges


def vtable_starts(st, resume, blob):
    """Dwords in .rdata/.data that point at a terminator-preceded .text VA."""
    path = os.path.join(C.WORK, "vtab.json")
    if resume and st.done("funcs", "vtab") and os.path.exists(path):
        return set(C.jload(path))
    data = C.exe_bytes()
    out = set()
    for lo, hi, off, raw in ((C.RDATA_LO, C.RDATA_HI, C.RDATA_OFF, C.RDATA_RAW),
                             (C.DATA_LO, C.DATA_HI, C.DATA_OFF, C.DATA_RAW)):
        # vsz can exceed the raw size (uninitialised tail); only scan raw.
        n = min(hi - lo, raw, len(data) - off)
        for i in range(0, n - 4, 4):
            v = struct.unpack_from("<I", data, off + i)[0]
            if C.va_ok(v) and preceded_by_terminator(blob, v - C.TEXT_LO):
                out.add(v)
    C.jdump(path, sorted(out))
    st.mark("funcs", "vtab", "done", starts=len(out))
    return out


def main():
    resume = "--resume" in sys.argv
    st = C.State()
    C.ensure_work()
    blob = C.text_blob()

    edges = load_edges(st, resume)
    print("edges: %d" % len(edges))

    callers = {}
    for site, tgt, kind in edges:
        if kind == "call":
            callers.setdefault(tgt, set()).add(site)

    accepted, rejected = {}, 0
    for tgt, cs in callers.items():
        if preceded_by_terminator(blob, tgt - C.TEXT_LO):
            accepted[tgt] = {"callers": len(cs), "kind": "call-target"}
        else:
            rejected += 1
    print("call targets: %d accepted, %d rejected (no terminator before)"
          % (len(accepted), rejected))

    vt = vtable_starts(st, resume, blob)
    nvt = 0
    for v in vt:
        if v not in accepted:
            accepted[v] = {"callers": 0, "kind": "vtable-only"}
            nvt += 1
    print("vtable-only starts added: %d (of %d vtable dwords)" % (nvt, len(vt)))

    starts = sorted(accepted)
    meta = {}
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else C.TEXT_HI
        m = dict(accepted[s])
        m["size"] = e - s
        meta[str(s)] = m
    C.jdump(os.path.join(C.HERE, "funcs.json"), {"starts": starts, "meta": meta})
    st.mark("funcs", "build", "done", functions=len(starts))
    print("funcs.json: %d functions" % len(starts))


if __name__ == "__main__":
    main()
