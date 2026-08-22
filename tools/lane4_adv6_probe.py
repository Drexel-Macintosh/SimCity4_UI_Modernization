#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ADVERSARIAL part 6: census of window vtables.
POSITIVE CONTROL for 'no override exists': identify vtables by a slot we have
PROVEN (+0xAC == GetL body 'mov eax,[ecx+0xA8]; ret'), then tabulate what each
of those vtables holds at +0xE0 and +0xE4.  If a relative-move override
existed, it would show up as a second function at +0xE0."""
import struct
from collections import Counter
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    off = pe + 24 + opt
    for i in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize)); off += 40
    return data, secs

DATA, SECS = load()
MD = Cs(CS_ARCH_X86, CS_MODE_32)

def sect(name):
    for n, sva, vsize, roff, rsize in SECS:
        if n == name: return IMAGE_BASE + sva, max(vsize, rsize), roff
    return None

def va2off(va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None

GETL_IMPLS = set()
# find every function body that is exactly `mov eax,[ecx+0xA8]; ret`
PAT = bytes.fromhex("8b81a8000000c3")
tva, tsz, troff = sect(".text")
tsz = min(tsz, len(DATA) - troff)
i = 0
while True:
    j = DATA.find(PAT, troff + i, troff + tsz)
    if j < 0: break
    GETL_IMPLS.add(tva + (j - troff))
    i = j - troff + 1
print("GetL-shaped bodies in .text:", [hex(x) for x in sorted(GETL_IMPLS)])

vts = []
for nm in (".rdata", ".data"):
    base_va, size, roff = sect(nm)
    size = min(size, len(DATA) - roff - 4)
    for k in range(0, size - 4, 4):
        v = struct.unpack_from("<I", DATA, roff + k)[0]
        if v in GETL_IMPLS:
            vt = base_va + k - 0xAC
            o = va2off(vt)
            if o is None or o + 0x120 > len(DATA): continue
            vts.append((vt, o))

print("candidate window vtables (identified by proven GetL at +0xAC):", len(vts))
c_e0 = Counter(); c_e4 = Counter(); c_cc = Counter()
for vt, o in vts:
    c_e0[struct.unpack_from("<I", DATA, o + 0xE0)[0]] += 1
    c_e4[struct.unpack_from("<I", DATA, o + 0xE4)[0]] += 1
    c_cc[struct.unpack_from("<I", DATA, o + 0xCC)[0]] += 1
print("\n+0xE0 (claimed GZWinMoveTo) distribution:")
for fn, n in c_e0.most_common(8): print("   0x%08X  x%d" % (fn, n))
print("+0xE4 distribution:")
for fn, n in c_e4.most_common(8): print("   0x%08X  x%d" % (fn, n))
print("+0xCC (SetW) distribution:")
for fn, n in c_cc.most_common(8): print("   0x%08X  x%d" % (fn, n))
