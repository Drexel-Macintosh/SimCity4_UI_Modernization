#!/usr/bin/env python3
"""ADJUDICATOR probe - re-verify the load-bearing claims of the three lenses.

Read-only. Disassembles the shipped exe; writes nothing.
Usage: python adjudicate_768_probe.py [section]
"""
import sys, struct, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IB = 0x400000


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    off = pe + 24 + opt
    for _ in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


D, S = load()


def va2off(va):
    rva = va - IB
    for n, sva, vsize, roff, rsize in S:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def off2va(o):
    for n, sva, vsize, roff, rsize in S:
        if roff <= o < roff + rsize:
            return IB + sva + (o - roff)
    return None


def dw(va):
    o = va2off(va)
    return None if o is None else struct.unpack_from("<I", D, o)[0]


MD = Cs(CS_ARCH_X86, CS_MODE_32)


def dis(va, n=60, stop_ret=False):
    o = va2off(va)
    out = []
    for ins in MD.disasm(D[o:o+n*10], va, n):
        out.append(ins)
        if stop_ret and ins.mnemonic.startswith("ret"):
            break
    return out


def show(va, n=60, stop_ret=False, tags=()):
    for ins in dis(va, n, stop_ret):
        t = ""
        for pat, what in tags:
            if pat in ins.op_str:
                t = "   <<< " + what
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<8}{ins.op_str}{t}")


def callers_of(target):
    hits = []
    for n, sva, vsize, roff, rsize in S:
        if not n.startswith(".text"):
            continue
        base = IB + sva
        blob = D[roff:roff+rsize]
        i = 0
        while True:
            i = blob.find(b"\xE8", i)
            if i < 0 or i + 5 > len(blob):
                break
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            if base + i + 5 + rel == target:
                hits.append(base + i)
            i += 1
    return hits


def dword_refs(value):
    """every occurrence of `value` as a LE dword anywhere in the file (any alignment)"""
    pat = struct.pack("<I", value)
    out, i = [], 0
    while True:
        i = D.find(pat, i)
        if i < 0:
            break
        va = off2va(i)
        if va is not None:
            out.append(va)
        i += 1
    return out


def sect_of(va):
    rva = va - IB
    for n, sva, vsize, roff, rsize in S:
        if sva <= rva < sva + max(vsize, rsize):
            return n
    return "?"


def part(title):
    print("\n" + "=" * 74)
    print(title)
    print("=" * 74)


sel = sys.argv[1] if len(sys.argv) > 1 else "all"

if sel in ("all", "1"):
    part("V1  cIGZWin geometry getters - is the rect at +0xA8 or +0x34?")
    for name, va in (("GetL?", 0x0099BC53), ("GetT?", 0x00994EE4), ("GetR?", 0x0099BC5A),
                     ("GetB?", 0x0099BC61), ("GetW?", 0x0099C81B), ("GetH?", 0x0099C82A),
                     ("GetArea?", 0x0099BCEC), ("GetAreaAbs?", 0x0099BD01)):
        print(f"-- {name} {va:#010x}")
        show(va, 8, stop_ret=True)
    print("\n-- cSC4WinMiniMap window vtable 0x00AB83B8 slots +0xA4..+0xC0:")
    for off in range(0xA4, 0xC4, 4):
        print(f"   vt+0x{off:03X} = {dw(0x00AB83B8+off):#010x}")
    print(f"   vt+0x160     = {dw(0x00AB83B8+0x160):#010x}   (should be 0x007A79B0)")
    print(f"   vt+0x0DC     = {dw(0x00AB83B8+0xDC):#010x}    (SetArea override?)")

if sel in ("all", "2"):
    part("V2  0x0079ED90 halving loops + the memset32 call")
    show(0x0079ED90, 34)
    print("  ...")
    show(0x0079EF00, 30)
    print("\n-- memset32 0x00910003")
    show(0x00910003, 8)
    print("\n-- raw bytes of the two halving loops")
    for lo, hi in ((0x0079ED9E, 0x0079EDBE), (0x0079EDC6, 0x0079EDDC)):
        o = va2off(lo)
        print(f"   {lo:#010x}..{hi:#010x} file {o:#08x}: {D[o:o+(hi-lo)].hex()}")

if sel in ("all", "3"):
    part("V3  0x007A2380 -> 0x0079ED90 call site: what are args 5/6 (dest W/H)?")
    show(0x007A2380, 20)
    print("  ...")
    show(0x007A25F8, 22)

if sel in ("all", "4"):
    part("V4  0x007A2F60 - the 0x4203 fetch, GetArea, and the buffer Init")
    for base in (0x007A2FE0, 0x007A3020, 0x007A3060, 0x007A3240):
        show(base, 22)
        print("  ...")

if sel in ("all", "5"):
    part("V5  cSC4WinMiniMap::SetArea 0x007A8E30 - how blitSize (+0xE4) is derived")
    show(0x007A8E30, 45, tags=(("0xe4", "blitSize"),))

if sel in ("all", "6"):
    part("V6  OWNERSHIP: walk up from 0x007A2740")
    for name, va in (("0x0079ED90", 0x0079ED90), ("0x007A2380", 0x007A2380),
                     ("0x007A2740", 0x007A2740), ("0x007A2F60", 0x007A2F60),
                     ("0x007A54D0", 0x007A54D0), ("0x007A56E0", 0x007A56E0),
                     ("0x007A49B0", 0x007A49B0), ("0x007A0D50 ctor", 0x007A0D50),
                     ("0x00466080 fact", 0x00466080)):
        c = callers_of(va)
        print(f"  callers_of({name}) = {len(c)}: {[hex(x) for x in c[:16]]}")
    print("\n-- ctor 0x007A0D50 head (vptr stores)")
    show(0x007A0D50, 30)
    print("\n-- factory 0x00466080")
    show(0x00466080, 16, stop_ret=True)
    print("\n-- clsid registration: sites pushing 0x466080")
    for va in dword_refs(0x00466080):
        print(f"   {va:#010x} [{sect_of(va)}]")
    print("\n-- around 0x00466310")
    show(0x00466310, 14)

if sel in ("all", "7"):
    part("V7  dword refs (vtable membership) - POSITIVE CONTROL FIRST")
    for name, va in (("0x007A79B0 CONTROL", 0x007A79B0), ("0x0079ED90", 0x0079ED90),
                     ("0x007A2380", 0x007A2380), ("0x007A2740", 0x007A2740),
                     ("0x007A2F60", 0x007A2F60), ("0x007A54D0", 0x007A54D0),
                     ("0x007A56E0", 0x007A56E0), ("0x007A0D50", 0x007A0D50)):
        r = dword_refs(va)
        print(f"  {name}: {len(r)} hit(s) {[(hex(x), sect_of(x)) for x in r[:6]]}")
    print("\n  0x00AB8518 - 0x00AB83B8 = 0x%X" % (0x00AB8518 - 0x00AB83B8))
    print("  0x00AB814C - 0x00AB8140 = 0x%X ; 0x00AB7EEC - 0x00AB7EE0 = 0x%X"
          % (0x00AB814C - 0x00AB8140, 0x00AB7EEC - 0x00AB7EE0))
    print("  0x00AB814C - 0x00AB7E14 = 0x%X ; 0x00AB7EEC - 0x00AB7E14 = 0x%X"
          % (0x00AB814C - 0x00AB7E14, 0x00AB7EEC - 0x00AB7E14))

if sel in ("all", "8"):
    part("V8  minimap draw 0x007A79B0 - does the dest rect use blitSize or the window rect?")
    show(0x007A79B0, 40, tags=(("0xe4", "blitSize"), ("0xf0", "surface")))
    print("  ...")
    show(0x007A7A10, 30, tags=(("0xe4", "blitSize"), ("0xf0", "surface"),
                               ("0x34", "?+0x34"), ("0x3c", "?+0x3c")))
    print("  ...")
    show(0x007A7A80, 30, tags=(("0xe4", "blitSize"), ("0xf0", "surface")))

if sel in ("all", "9"):
    part("V9  handler transfer 0x007A8640 region + 0x007A66F0")
    show(0x007A8690, 32, tags=(("0xc", "+0xE4 blitSize?"), ("0x18", "+0xF0 surf?")))
    print("\n-- 0x007A66F0 head")
    show(0x007A66F0, 20)

if sel in ("all", "10"):
    part("V10 replication law, executed")
    def mult(dest, src):
        m = 1
        d = dest
        while d > src:
            d >>= 1
            m <<= 1
        return m, d
    for W in (256, 384, 512, 768, 1024):
        for dim in (64, 128, 256):
            m, red = mult(W, dim)
            print(f"   W={W:5d} dim={dim:4d} reduced={red:5d} mult={m:3d} painted={dim*m:5d} "
                  f"{'EXACT' if dim*m == W else 'OVER +%d' % (dim*m - W)}")
