#!/usr/bin/env python3
"""Identify the owning class of a set of VAs via MSVC RTTI.
Builds: vtable VA -> class name, by reading the COL at vtable[-1].
Then answers "which vtable(s) contain VA X, and at what slot".
Read-only."""
import sys, struct
from pe109_probe import *

data, secs = load()

# ---- 1. Locate all RTTI Complete Object Locators ------------------------
# TypeDescriptor: [vftable of type_info][spare][name ".?AV...@@\0"]
# COL: sig, offset, cdOffset, pTypeDescriptor, pClassDescriptor
# vtable[-1] == &COL

def sec_of(va):
    for n, sva, vsize, roff, rsize in secs:
        if IMAGE_BASE + sva <= va < IMAGE_BASE + sva + max(vsize, rsize):
            return n
    return None

# find type descriptors: search for b".?AV" and b".?AU" in .data/.rdata
tds = {}   # VA of TypeDescriptor -> name
for n, sva, vsize, roff, rsize in secs:
    blob = data[roff:roff + rsize]
    for pat in (b".?AV", b".?AU"):
        i = blob.find(pat)
        while i != -1:
            end = blob.find(b"\0", i)
            if end != -1 and end - i < 200:
                name = blob[i:end].decode("latin1")
                # TypeDescriptor starts 8 bytes before the name
                td_va = IMAGE_BASE + sva + i - 8
                tds[td_va] = name
            i = blob.find(pat, i + 1)

print(f"type descriptors found: {len(tds)}")

# find COLs: 20-byte struct in .rdata whose [12] is a known TD VA
cols = {}
for n, sva, vsize, roff, rsize in secs:
    if n not in (".rdata", ".data"):
        continue
    blob = data[roff:roff + rsize]
    for off in range(0, len(blob) - 20, 4):
        td = struct.unpack_from("<I", blob, off + 12)[0]
        if td in tds:
            sig = struct.unpack_from("<I", blob, off)[0]
            if sig == 0:
                cols[IMAGE_BASE + sva + off] = tds[td]
print(f"complete object locators: {len(cols)}")

# vtables: any dword slot preceded by a COL pointer
vt = {}   # vtable VA -> class name
for n, sva, vsize, roff, rsize in secs:
    if n not in (".rdata", ".data"):
        continue
    blob = data[roff:roff + rsize]
    for off in range(0, len(blob) - 8, 4):
        p = struct.unpack_from("<I", blob, off)[0]
        if p in cols:
            vt[IMAGE_BASE + sva + off + 4] = cols[p]
print(f"vtables with RTTI: {len(vt)}\n")

# ---- 2. build slot map: function VA -> list of (vtable, class, slot) ----
slot_of = {}
for vva, cname in vt.items():
    o = va2off(secs, vva)
    for s in range(0, 400):
        d = struct.unpack_from("<I", data, o + s * 4)[0]
        if not (0x401000 <= d < 0x400000 + 0x800000):
            break
        # stop if we hit another vtable start
        if (vva + s * 4) in vt and s > 0:
            break
        slot_of.setdefault(d, []).append((vva, cname, s * 4))

targets = [int(x, 16) for x in sys.argv[1:]] or [
    0x007A2740, 0x007A2380, 0x0079ED90, 0x007A2F60, 0x007A49B0, 0x007A5610,
    0x007A79B0, 0x007A7840, 0x007A8640, 0x007A7FF0, 0x007A04F0, 0x007A8560,
]
print("=" * 78)
for t in targets:
    ent = slot_of.get(t)
    print(f"{hex(t)}: " + (", ".join(f"{c} vt {hex(v)} slot+{hex(s)}" for v, c, s in ent[:6])
                           if ent else "not a virtual (no vtable slot)"))

# ---- 3. class name for the vtables named in the brief -------------------
print()
for v in (0x00ADF6A0, 0x00AB8518):
    print(f"vtable {hex(v)} -> {vt.get(v, 'UNKNOWN (no RTTI at that VA)')}")
    # 0xab8518 is where mmdraw appears as a dword: find enclosing vtable
for probe in (0x00AB8518,):
    best = max([x for x in vt if x <= probe], default=None)
    print(f"  enclosing vtable of {hex(probe)}: {hex(best)} = {vt.get(best)} "
          f"(slot +{hex(probe-best)})")

# dump any class name containing MiniMap / SC4Win / DataView
print()
print("classes matching MiniMap/Terrain/DataView:")
for vva, c in sorted(vt.items(), key=lambda kv: kv[1]):
    if any(k in c for k in ("MiniMap", "Minimap", "DataView", "Terrain", "Query")):
        print(f"  {hex(vva)}  {c}")
