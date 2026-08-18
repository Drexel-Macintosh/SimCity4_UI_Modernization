"""scan_budget_forward.py - #103: FORWARD direct-call closure from the budget
popup builder sub_78B120, asking one question: can it reach sub_76D3D0 (the
Graphs panel builder v2.55.0 patched)?

POSITIVE CONTROL (law: a null is only measured if the control covers the path):
the same walk is run from the KNOWN graphs entry sub_7F0A70, which MUST reach
sub_76D3D0.  If the control fails, the walker is broken and the budget null
means nothing.

READ-ONLY on the exe.
"""
import os
import sys
import struct
import bisect
import json
from collections import deque

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
import common as C                                     # noqa: E402

STARTS = sorted(int(x) for x in
                json.load(open(os.path.join(os.path.dirname(_HERE),
                                            "funcs.json")))["starts"])
text = C.text_blob()
LO = C.TEXT_LO


def fn_of(va):
    i = bisect.bisect_right(STARTS, va) - 1
    return STARTS[i] if i >= 0 else None


def fn_end(f):
    i = bisect.bisect_right(STARTS, f) - 1
    return STARTS[i + 1] if i + 1 < len(STARTS) else C.TEXT_HI


# --- build the direct rel32 call/jmp edge list ONCE -------------------------
edges = {}
for op, sz in ((0xE8, 5), (0xE9, 5)):
    i = 0
    while True:
        i = text.find(bytes([op]), i)
        if i < 0 or i + sz > len(text):
            break
        rel = struct.unpack_from("<i", text, i + 1)[0]
        va = LO + i
        tgt = va + sz + rel
        if C.TEXT_LO <= tgt < C.TEXT_HI:
            src = fn_of(va)
            if src is not None:
                edges.setdefault(src, set()).add(tgt)
        i += 1
print("call-graph edges built: %d source functions" % len(edges))


def reaches(root, target, cap=200000):
    seen = {root}
    q = deque([(root, [root])])
    while q:
        f, path = q.popleft()
        if len(seen) > cap:
            return None, None
        for t in edges.get(f, ()):
            tf = fn_of(t)
            if t == target or tf == target:
                return True, path + [t]
            if tf is not None and tf not in seen:
                seen.add(tf)
                q.append((tf, path + [tf]))
    return False, len(seen)


TARGET = 0x0076D3D0

print("\n--- POSITIVE CONTROL: graphs ctor sub_7F0A70 -> sub_76D3D0 ---")
ok, info = reaches(0x007F0A70, TARGET)
print("  reaches:", ok)
if ok:
    print("  path:", " -> ".join("%08X" % x for x in info))
else:
    print("  functions explored:", info)

print("\n--- graphs vtable ctor site owner sub_7F1140 -> sub_76D3D0 ---")
ok2, info2 = reaches(0x007F1140, TARGET)
print("  reaches:", ok2)
if ok2:
    print("  path:", " -> ".join("%08X" % x for x in info2))
else:
    print("  functions explored:", info2)

print("\n--- THE QUESTION: budget popup builder sub_78B120 -> sub_76D3D0 ---")
ok3, info3 = reaches(0x0078B120, TARGET)
print("  reaches:", ok3)
if ok3:
    print("  path:", " -> ".join("%08X" % x for x in info3))
else:
    print("  functions explored (exhausted, no path):", info3)

print("\n--- also: budget fill/text branch owner sub_779660 -> sub_76D3D0 ---")
ok4, info4 = reaches(0x00779660, TARGET)
print("  reaches:", ok4)
print("  functions explored:", info4 if not ok4 else "")

# Does the budget builder reach the GRAPHS WINDOW CTORS at all?
print("\n--- budget builder -> graphs vtable install sites ---")
for t in (0x007F0A70, 0x007F1140):
    o, i2 = reaches(0x0078B120, t)
    print("  sub_78B120 -> %08X : %s" % (t, o))
