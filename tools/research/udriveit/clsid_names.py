#!/usr/bin/env python3
r"""Resolve save-file subfile TYPE ids to C++ class names using the exe's RTTI.

Method (each step is checkable):
 1. A persisted class implements cIGZSerializable::GetGZCLSID, which MSVC
    compiles to `B8 <imm32> C3`  (mov eax,CLSID / ret).  Find those stubs.
 2. Find every vtable slot in .rdata/.data holding that stub's VA.
 3. Walk back from the vtable start to the MSVC RTTI Complete Object Locator
    pointer at vtable[-1], then ->pTypeDescriptor -> the mangled name
    ".?AVcSC4Whatever@@".
Read-only on the exe.
"""
import struct, sys, re, collections

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

data = open(EXE, "rb").read()
pe = struct.unpack_from("<I", data, 0x3C)[0]
nsec = struct.unpack_from("<H", data, pe + 6)[0]
optsz = struct.unpack_from("<H", data, pe + 20)[0]
base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + optsz + i * 40
    nm = data[o:o + 8].rstrip(b"\0").decode("latin1")
    vs, va, rs, ra = struct.unpack_from("<IIII", data, o + 8)
    secs.append((nm, va, vs, ra, rs))

def va2off(va):
    r = va - base
    for nm, sva, vs, ra, rs in secs:
        if sva <= r < sva + max(vs, rs):
            d = r - sva
            if d < rs:
                return ra + d
    return None

def off2va(off):
    for nm, sva, vs, ra, rs in secs:
        if ra <= off < ra + rs:
            return base + sva + (off - ra)
    return None

# --- RTTI type descriptors --------------------------------------------------
# TypeDescriptor: void* pVFTable; void* spare; char name[];  name starts ".?AV"
tds = {}   # VA of type descriptor -> demangled-ish name
for m in re.finditer(rb"\.\?A[VU][\x21-\x7e]{1,200}?@@", data):
    nm_off = m.start()
    td_off = nm_off - 8
    va = off2va(td_off)
    if va:
        tds[va] = m.group().decode("latin1")

# --- Complete Object Locators ----------------------------------------------
# COL: u32 sig; u32 off; u32 cdOff; u32 pTypeDescriptor; u32 pClassDescriptor
col2name = {}
for td_va in tds:
    pat = struct.pack("<I", td_va)
    s = 0
    while True:
        k = data.find(pat, s)
        if k < 0:
            break
        s = k + 1
        col_off = k - 12
        if col_off >= 0 and struct.unpack_from("<I", data, col_off)[0] == 0:
            va = off2va(col_off)
            if va:
                col2name[va] = tds[td_va]

# --- vtables: a slot preceded by a COL pointer ------------------------------
vtables = {}   # vtable VA -> class name
for col_va, nm in col2name.items():
    pat = struct.pack("<I", col_va)
    s = 0
    while True:
        k = data.find(pat, s)
        if k < 0:
            break
        s = k + 1
        vt = off2va(k + 4)
        if vt:
            vtables[vt] = nm

# index: function VA -> list of vtables containing it
slot_owner = collections.defaultdict(set)
for vt, nm in vtables.items():
    off = va2off(vt)
    if off is None:
        continue
    for j in range(0, 400):          # walk the vtable until it stops looking like code ptrs
        p = off + j * 4
        if p + 4 > len(data):
            break
        f = struct.unpack_from("<I", data, p)[0]
        if not (0x401000 <= f < 0x900000):
            break
        if j > 0 and off2va(p) in vtables:
            break
        slot_owner[f].add(nm)


def stubs_for(clsid):
    """VAs of `mov eax,clsid / ret` stubs."""
    out = []
    pat = b"\xB8" + struct.pack("<I", clsid) + b"\xC3"
    s = 0
    while True:
        k = data.find(pat, s)
        if k < 0:
            break
        s = k + 1
        out.append(off2va(k))
    return out


def imm_hits(clsid):
    out = []
    pat = struct.pack("<I", clsid)
    s = 0
    while True:
        k = data.find(pat, s)
        if k < 0:
            break
        s = k + 1
        va = off2va(k)
        if va:
            sec = [nm for nm, sva, vs, ra, rs in secs if ra <= k < ra + rs][0]
            out.append((va, sec))
    return out


if __name__ == "__main__":
    print("RTTI: %d type descriptors, %d COLs, %d vtables" % (len(tds), len(col2name), len(vtables)))
    for a in sys.argv[1:]:
        cid = int(a, 0)
        st = stubs_for(cid)
        nms = set()
        for v in st:
            nms |= slot_owner.get(v, set())
        hits = imm_hits(cid)
        print("0x%08X  stubs=%s  classes=%s  imm_hits=%d %s" %
              (cid, ",".join("0x%X" % v for v in st) or "-",
               ",".join(sorted(nms)) or "-", len(hits),
               " ".join("0x%X(%s)" % h for h in hits[:6])))
