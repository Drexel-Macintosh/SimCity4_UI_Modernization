"""Step 6: vtable LENGTHS. A vtable ends at the first of:
  (a) a dword that is not a .text pointer, or
  (b) an address that code stores as an imm32 into memory (mov dword ptr [..], imm32) = the
      start of another vtable (ctor/dtor stores).
Also reports where each class vtable sits in its object (offset of the store in the ctor)."""
import sys, re
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from pe import *
from s1_vtables import CLASSES

here = __file__.rsplit("\\", 1)[0]
starts = set()
pat = re.compile(r"mov dword ptr \[[^\]]+\], (0x[0-9a-f]{6,8})$")
rlo, rhi = [(a, b) for n, a, b in SECTIONS if n == ".rdata"][0]
for l in open(here + "\\sweep.txt"):
    m = pat.search(l)
    if m:
        v = int(m.group(1), 16)
        if rlo <= v < rhi:
            starts.add(v)
print("vtable-start candidates stored by code:", len(starts))

def vlen(va):
    n = 0
    while True:
        p = u32(va + 4 * n)
        if not is_code(p):
            return n, "non-code dword %#x" % p
        if n > 0 and (va + 4 * n) in starts:
            return n, "next vtable %#x (code-stored)" % (va + 4 * n)
        n += 1

if __name__ == "__main__":
    for name, va in CLASSES:
        n, why = vlen(va)
        print(f"{name:28s} {va:#x}: {n:3d} slots (0..{n-1}); ends at {why}")
