"""Step 14: locate the Windows draw-context class vtable(s) and read slot 25
(vt+0x64, Mac 'SetLineThickness'). Heuristic filter on arg counts:
slot 34 Line(x0,y0,x1,y1) ret 0x10, slot 35 Fill(rect*) ret 4, slot 25 ret 4,
slot 21 SetColor ret 4."""
import sys, os, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

T = TEXT
blob = RAW[T[3]:T[3] + T[4]]
cands = set()
for m in re.finditer(rb"\xc7[\x00-\x03\x06\x07](....)", blob, re.S):
    v = struct.unpack("<I", m.group(1))[0]
    if secname(v) == ".rdata":
        cands.add(v)
for m in re.finditer(rb"\xc7[\x40-\x43\x46\x47].(....)", blob, re.S):
    v = struct.unpack("<I", m.group(1))[0]
    if secname(v) == ".rdata":
        cands.add(v)
print("vtable-store candidates:", len(cands))
out = []
for v in sorted(cands):
    n = 0
    while n < 80 and is_text(u32(v + 4 * n)):
        n += 1
    if n < 48:
        continue
    try:
        r34 = rets(resolve(u32(v + 4 * 34))[0])
        r35 = rets(resolve(u32(v + 4 * 35))[0])
        r25 = rets(resolve(u32(v + 4 * 25))[0])
        r21 = rets(resolve(u32(v + 4 * 21))[0])
    except Exception:
        continue
    if r34 == [0x10] and r35 == [4] and r25 == [4] and r21 == [4]:
        out.append(v)
print("DC-shaped vtables:", [hex(v) for v in out])
for v in out:
    print(f"\n=== vt {v:08X}  refs {[hex(x) for x in find_imm32(v)]}")
    for s in (19, 20, 21, 25, 34, 35):
        f = resolve(u32(v + 4 * s))[0]
        print(f"  slot {s} {f:08X} rets {rets(f)}")
        print(fmt(fn(f, 45), "      "))
