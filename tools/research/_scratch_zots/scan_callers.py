#!/usr/bin/env python3
"""Scratch scanner for the Zot investigation (2026-08-23).

1. Enumerate every E8 rel32 call in .text to a set of targets:
   0x7F6690 (px->world), 0x6C98C0 (zot spawn helper), 0x4A24D0 (marker
   factory), 0x5ED400 (marker SetSize), 0x5ECA10 (GetSize), 0x6C9780,
   0x6C9AD0.
2. Dump the float at .rdata 0xA85074 (the fadd height nudge).
3. Find imm32 refs to 0x48E95539, 0xC999C45E, and the four Zot instance ids.
Positive control: the known signpost call sites 0x5F20B6/0x5F20C6 must appear
in the 0x7F6690 caller list, and the seven known spawn sites in 0x6C98C0's.
"""
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

text = next(s for s in secs if s[0] == ".text")
tname, tva, tvs, tra, trs = text
tsize = min(tvs, trs)

def off2va(off):
    return base + tva + (off - tra)

def va2off(va):
    for name, sva, vs, ra, rs in secs:
        rva = va - base
        if sva <= rva < sva + max(vs, rs):
            return ra + (rva - sva)
    return None

targets = {0x7F6690: "px->world", 0x6C98C0: "zot-spawn", 0x4A24D0: "marker-factory",
           0x5ED400: "SetSize", 0x5ECA10: "GetSize", 0x6C9780: "zot-remove?",
           0x6C9AD0: "fn6C9AD0"}
hits = {t: [] for t in targets}
i = tra
end = tra + tsize - 5
while i < end:
    if data[i] == 0xE8:
        rel = struct.unpack_from("<i", data, i + 1)[0]
        dest = off2va(i) + 5 + rel
        if dest in targets:
            hits[dest].append(off2va(i))
    i += 1

for t in sorted(targets):
    print("callers of 0x%X (%s): %d" % (t, targets[t], len(hits[t])))
    for va in hits[t]:
        print("   0x%08X" % va)

# float at 0xA85074
o = va2off(0xA85074)
print("float @0xA85074 =", struct.unpack_from("<f", data, o)[0],
      "bytes", data[o:o+4].hex())

# imm32 refs
for imm, label in [(0x48E95539, "prop 0x48E95539"), (0xC999C45E, "iid 0xC999C45E"),
                   (0x0FD10000, "NoPower"), (0x107A0000, "NoCar"),
                   (0x1C430000, "NoWater"), (0x1C440000, "NoWork")]:
    pat = struct.pack("<I", imm)
    refs = []
    j = tra
    while True:
        j = data.find(pat, j, tra + tsize)
        if j < 0:
            break
        refs.append(off2va(j))
        j += 1
    print("imm32 %s (0x%08X): %d .text refs:" % (label, imm, len(refs)),
          " ".join("0x%08X" % r for r in refs))
