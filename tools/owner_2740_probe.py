#!/usr/bin/env python3
"""Q1/Q2: WHO OWNS 0x007A2740, and where does its rect argument come from?
Walks UP the call graph from the fault chain until a vtable slot / known VA.
Read-only."""
import sys, struct
from pe109_probe import *

FAULT = 0x00910010
MEMSET32 = 0x00910003
ROWFILL = 0x0079ED90
MID = 0x007A2380
TOP = 0x007A2740
MM_DRAW = 0x007A79B0

data, secs = load()
starts = function_starts(data, secs)
print(f"exe {len(data):,} bytes; {len(starts):,} distinct call-rel32 targets (fn starts)\n")


def where_is(va):
    """Is this VA listed as a dword anywhere (vtable / jump table / data)?"""
    return find_dword_refs(data, secs, va)


print("=" * 78)
print("A. VERIFY THE LEAD'S CALLER COUNTS (independent re-measure)")
print("=" * 78)
for nm, va in (("memset32 0x00910003", MEMSET32),
               ("rowfill  0x0079ED90", ROWFILL),
               ("mid      0x007A2380", MID),
               ("top      0x007A2740", TOP),
               ("mmdraw   0x007A79B0", MM_DRAW)):
    c = callers_of(data, secs, va)
    j = jmp_callers_of(data, secs, va)
    refs = where_is(va)
    print(f"{nm}: {len(c)} call-sites {[hex(x) for x in c[:20]]}")
    if j:
        print(f"    + {len(j)} tail-jmp sites {[hex(x) for x in j[:8]]}")
    print(f"    dword-refs (vtable/jumptable candidates): "
          f"{[(n, hex(v)) for n, v in refs[:12]]}")
print()

print("=" * 78)
print("B. WALK UP FROM 0x007A2740")
print("=" * 78)
level = {TOP}
seen = set()
for depth in range(6):
    nxt = set()
    print(f"\n--- level {depth} ---")
    for f in sorted(level):
        if f in seen:
            continue
        seen.add(f)
        cs = callers_of(data, secs, f)
        encl = sorted({enclosing_function(data, secs, s, starts) for s in cs} - {None})
        refs = where_is(f)
        vt = [(n, hex(v)) for n, v in refs if n in (".rdata", ".data")]
        print(f"  fn {hex(f)}: {len(cs)} call-sites -> enclosing fns "
              f"{[hex(x) for x in encl]}")
        if vt:
            print(f"      *** appears as a DWORD in {vt[:10]}  <= vtable slot?")
        for e in encl:
            nxt.add(e)
    level = nxt
    if not level:
        break
    if depth >= 3:
        break

print()
print("=" * 78)
print("C. FULL DISASSEMBLY 0x007A2740 (the 'top')")
print("=" * 78)
TAGS = {0x34: "rect.L", 0x38: "rect.T", 0x3C: "rect.R", 0x40: "rect.B",
        0xE4: "blitSize", 0xF0: "surface", 0x104: "zoom", 0xFC: "flags32",
        0x114: "rasterBase", 0x118: "rasterW", 0x11C: "rasterH", 0x120: "dirty",
        0x174: "vt+0x174 GetDim", 0x178: "vt+0x178"}
def dump(va, n=0x300, label=""):
    print(f"\n>>> {label} {hex(va)}")
    for ins in disasm(data, secs, va, n):
        tag = ""
        for op in ins.operands:
            if op.type == X86_OP_MEM and op.mem.disp in TAGS:
                tag = "   <<< " + TAGS[op.mem.disp]
        print(f"  0x{ins.address:08X}  {ins.bytes.hex():<16} {ins.mnemonic:<8}{ins.op_str}{tag}")

dump(TOP, 0x220, "TOP")
print()
dump(0x007A3240, 0x120, "context around known caller site 0x7a3267 (guessed start)")
