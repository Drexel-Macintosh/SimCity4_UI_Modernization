"""scan_graphs_callchain.py - #103: walk UP from sub_76D3D0 to find every
class/vtable that can reach it, so 'Graphs-only' is MEASURED, not assumed.

READ-ONLY on the exe.
"""
import os
import struct
import sys
import bisect

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
import common as C                                    # noqa: E402

text = C.text_blob()
TEXT_LO = C.TEXT_LO

import json
_f = json.load(open(os.path.join(os.path.dirname(_HERE), "funcs.json")))
STARTS = sorted(int(x) for x in _f["starts"])


def fn_of(va):
    i = bisect.bisect_right(STARTS, va) - 1
    return STARTS[i] if i >= 0 else None


def rel_callers(target):
    """every E8/E9 rel32 in .text whose target == `target`."""
    out = []
    for op in (0xE8, 0xE9):
        i = 0
        while True:
            i = text.find(bytes([op]), i)
            if i < 0 or i + 5 > len(text):
                break
            rel = struct.unpack_from("<i", text, i + 1)[0]
            va = TEXT_LO + i
            if va + 5 + rel == target:
                out.append((va, "call" if op == 0xE8 else "jmp"))
            i += 1
    return out


def abs_refs(target):
    """every 4-byte little-endian occurrence of `target` in text/rdata/data."""
    needle = struct.pack("<I", target)
    out = []
    for nm, lo, hi, off, raw in C.sections():
        if nm not in (".text", ".rdata", ".data"):
            continue
        blob = C.exe_bytes()[off:off + min(raw, hi - lo)]
        i = 0
        while True:
            i = blob.find(needle, i)
            if i < 0:
                break
            out.append((nm, lo + i))
            i += 1
    return out


ROOT = 0x0076D3D0
seen = set()
frontier = [ROOT]
level = 0
print("Walking callers up from %08X\n" % ROOT)
while frontier and level < 6:
    print("---- level %d : %d function(s) ----" % (level, len(frontier)))
    nxt = []
    for fn in sorted(frontier):
        if fn in seen:
            continue
        seen.add(fn)
        rc = rel_callers(fn)
        ar = abs_refs(fn)
        print("  fn %08X   rel-callers=%d  abs-refs=%d" % (fn, len(rc), len(ar)))
        for va, kind in rc:
            owner = fn_of(va)
            print("      %-4s from %08X  (in fn %08X)" % (kind, va, owner))
            if owner is not None:
                nxt.append(owner)
        for nm, va in ar:
            print("      ABS  %-7s %08X" % (nm, va))
    frontier = [f for f in set(nxt) if f not in seen]
    level += 1
print("\nfunctions reached: %d" % len(seen))
