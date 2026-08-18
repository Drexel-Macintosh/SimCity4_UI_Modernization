#!/usr/bin/env python3
"""Owner probe #3: precise boundaries + full disassembly of the owner chain.

Function starts = rel32 call targets  UNION  aligned .rdata dwords that point
into .text (vtable slots).  That closes the hole probe #2 had (functions that
are only ever reached through a vtable were invisible as boundaries, so
`containing()` merged them into the preceding function).
Read-only.
"""
import sys, struct, bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IB = 0x400000
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.detail = False


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []; off = pe + 24 + opt
    for i in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize)); off += 40
    return data, secs


DATA, SECS = load()


def va2off(va):
    rva = va - IB
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def sec_of(va):
    rva = va - IB
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return n
    return None


def rng(name):
    for n, sva, vsize, roff, rsize in SECS:
        if n.startswith(name):
            return IB + sva, roff, min(vsize, rsize)
    return None


TEXT_VA, TEXT_OFF, TEXT_SZ = rng(".text")
RD_VA, RD_OFF, RD_SZ = rng(".rdata")


def build():
    ct, jt = {}, {}
    blob = DATA[TEXT_OFF:TEXT_OFF+TEXT_SZ]
    for i in range(len(blob) - 5):
        b = blob[i]
        if b in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            site = TEXT_VA + i
            t = site + 5 + rel
            if TEXT_VA <= t < TEXT_VA + TEXT_SZ:
                (ct if b == 0xE8 else jt).setdefault(t, []).append(site)
    # vtable slots: aligned dwords in .rdata pointing into .text
    vt = {}
    rb = DATA[RD_OFF:RD_OFF+RD_SZ]
    for i in range(0, len(rb) - 4, 4):
        d = struct.unpack_from("<I", rb, i)[0]
        if TEXT_VA <= d < TEXT_VA + TEXT_SZ:
            vt.setdefault(d, []).append(RD_VA + i)
    return ct, jt, vt


CT, JT, VT = build()
STARTS = sorted(set(CT) | set(VT))


def containing(va):
    i = bisect.bisect_right(STARTS, va) - 1
    return STARTS[i] if i >= 0 else None


def dis(va, n=200, stop=None):
    o = va2off(va)
    out = []
    for ins in MD.disasm(DATA[o:o+n*10], va, n):
        out.append(ins)
        if stop and ins.address >= stop:
            break
    return out


def show(va, n, title, hi=()):
    print(f"\n--- {title} @ 0x{va:08X} ---")
    for ins in dis(va, n):
        m = ""
        for h in hi:
            if h in ins.op_str:
                m = "   <<<"
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}{m}")


def rdata_hits(value):
    out = []
    tgt = struct.pack("<I", value)
    for n, sva, vsize, roff, rsize in SECS:
        blob = DATA[roff:roff+min(vsize, rsize)]
        s = 0
        while True:
            k = blob.find(tgt, s)
            if k < 0: break
            out.append((n, IB + sva + k))
            s = k + 1
    return out


print("STARTS:", len(STARTS), " (call targets", len(CT), "+ vtable slots", len(VT), ")")
print("control: 0x007A79B0 in VT =", 0x007A79B0 in VT, VT.get(0x007A79B0))
print("control: 0x007A2740 in CT =", 0x007A2740 in CT)

print("\n" + "=" * 74)
print("1. CONTAINING FUNCTIONS, refined")
print("=" * 74)
for s in (0x7a2628, 0x7a3267, 0x7a4b19, 0x7a53d7, 0x7a55d1, 0x7a5f1b, 0x7a5649,
          0x7a5e36, 0x7a5eb4, 0x7a6212, 0x7a625b, 0x7a627a, 0x7a64b9, 0x7a656d):
    c = containing(s)
    print(f"  site {hex(s)} -> fn {hex(c)}  callers={len(CT.get(c,[]))} vtslots={len(VT.get(c,[]))}")

print("\n" + "=" * 74)
print("2. WALK UP FROM fn(0x7a3267)")
print("=" * 74)
root = containing(0x7a3267)
level = [root]; seen = set(); d = 0
while level and d < 8:
    nxt = []
    for f in level:
        if f in seen: continue
        seen.add(f)
        cs = CT.get(f, []); js = JT.get(f, []); vs = VT.get(f, [])
        print(f"\n  [d{d}] fn {hex(f)}  calls={len(cs)} jmps={len(js)} VTABLE_SLOTS={len(vs)}")
        for v in vs:
            print(f"        *** VTABLE slot at .rdata {v:08X} ***")
        for s in cs:
            p = containing(s)
            print(f"        call from {hex(s)} in fn {hex(p)}")
            if p and p != f: nxt.append(p)
        for s in js:
            p = containing(s)
            print(f"        jmp  from {hex(s)} in fn {hex(p)}")
            if p and p != f: nxt.append(p)
        if not cs and not js and not vs:
            print("        *** NO predecessor of any kind ***")
    level = [x for x in dict.fromkeys(nxt) if x not in seen]
    d += 1

print("\n" + "=" * 74)
print("3. .rdata / whole-image dword hits for every chain VA")
print("=" * 74)
for va in (0x0079ED90, 0x007A2380, 0x007A2740, 0x007A2F60, 0x007A79B0):
    h = rdata_hits(va)
    print(f"  {va:08X}: {len(h)} hit(s) " + ", ".join(f"{n}@{a:08X}" for n, a in h))
