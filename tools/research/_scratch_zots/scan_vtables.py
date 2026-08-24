#!/usr/bin/env python3
"""Find .rdata/.data dword pointers to given function VAs (vtable slots),
and print vtable context around 0xAA4900. Also list E8 callers of the
function containing 0x426E31 (marker-exemplar TGI fetch)."""
import struct

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
data = open(EXE, "rb").read()
pe = struct.unpack_from("<I", data, 0x3C)[0]
n = struct.unpack_from("<H", data, pe + 6)[0]
opt = struct.unpack_from("<H", data, pe + 20)[0]
base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
secs = []
for i in range(n):
    o = pe + 24 + opt + i * 40
    name = data[o:o + 8].rstrip(b"\0").decode("latin1")
    vs, va, rs, ra = struct.unpack_from("<IIII", data, o + 8)
    secs.append((name, va, vs, ra, rs))

def va2off(va):
    for name, sva, vs, ra, rs in secs:
        rva = va - base
        if sva <= rva < sva + max(vs, rs):
            return ra + (rva - sva)
    return None

def off2va(off):
    for name, sva, vs, ra, rs in secs:
        if ra <= off < ra + min(vs, rs) + max(0, max(vs, rs) - min(vs, rs)):
            pass
    # generic: find section containing off
    for name, sva, vs, ra, rs in secs:
        if ra <= off < ra + rs:
            return base + sva + (off - ra)
    return None

# 1. pointer refs to these functions anywhere in the file
for target in (0x4A24D0, 0x4A2670, 0x5ED400, 0x5ECA10, 0x6C98C0):
    pat = struct.pack("<I", target)
    refs = []
    j = 0
    while True:
        j = data.find(pat, j)
        if j < 0:
            break
        va = off2va(j)
        if va:
            refs.append(va)
        j += 1
    print("ptr refs to 0x%X:" % target, " ".join("0x%08X" % r for r in refs))

# 2. dump vtable 0xAA4900 (24 slots) and 0xAA4868 (24 slots)
for vt in (0xAA4900, 0xAA4868):
    o = va2off(vt)
    print("\nvtable 0x%X:" % vt)
    for s in range(26):
        fn = struct.unpack_from("<I", data, o + s * 4)[0]
        print("  slot %2d (+0x%02X) -> 0x%08X" % (s, s * 4, fn))

# 3. function containing 0x426E31: find its start (int3 padding scan back)
text = next(s for s in secs if s[0] == ".text")
tname, tva, tvs, tra, trs = text
tsize = min(tvs, trs)
o = va2off(0x426E31)
i = o
while data[i] != 0xCC or data[i-1] != 0xCC:
    i -= 1
    if o - i > 0x2000:
        break
# walk forward past int3s
while data[i] == 0xCC:
    i += 1
fn_start = base + tva + (i - tra)
print("\nfunction around 0x426E31 starts ~0x%08X" % fn_start)
# E8 callers of that start
pat_target = fn_start
hits = []
j = tra
end = tra + tsize - 5
while j < end:
    if data[j] == 0xE8:
        rel = struct.unpack_from("<i", data, j + 1)[0]
        dest = (base + tva + (j - tra)) + 5 + rel
        if dest == pat_target:
            hits.append(base + tva + (j - tra))
    j += 1
print("E8 callers of 0x%08X:" % fn_start, " ".join("0x%08X" % h for h in hits))
# also pointer refs
pat = struct.pack("<I", fn_start)
refs = []
j = 0
while True:
    j = data.find(pat, j)
    if j < 0:
        break
    va = off2va(j)
    if va:
        refs.append(va)
    j += 1
print("ptr refs to 0x%08X:" % fn_start, " ".join("0x%08X" % r for r in refs))
