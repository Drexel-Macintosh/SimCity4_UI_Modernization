#!/usr/bin/env python3
"""WHO OWNS 0x007A2740 and where does its rect come from?

Read-only. Disassembles the shipped exe; writes nothing.
Reuses the PE mapping / caller-scan from disasm_109_faultchain.py.
"""
import sys, struct, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

FAULT   = 0x00910010
ROWFILL = 0x0079ED90
MID     = 0x007A2380
TOP     = 0x007A2740
MM_DRAW = 0x007A79B0


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
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


def va2off(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def sec_of(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            return n
    return None


MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = False


def disasm(data, secs, va, count=90):
    o = va2off(secs, va)
    if o is None:
        return []
    return list(MD.disasm(data[o:o+count*10], va, count))


def callers_of(data, secs, target):
    hits = []
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff+rsize]
        for i in range(len(blob) - 5):
            if blob[i] != 0xE8:
                continue
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            site = base + i
            if site + 5 + rel == target:
                hits.append(site)
    return hits


# ---- function start finder -------------------------------------------------
# Scan backwards from a call site for a plausible prologue. MSVC 6/7 x86 code in
# this binary uses:  push ebp; mov ebp,esp   OR   sub esp,imm  OR  push reg runs
# preceded by int3/nop padding or a `ret`+alignment.
PROLOGUES = [
    bytes([0x55, 0x8B, 0xEC]),          # push ebp; mov ebp,esp
    bytes([0x53, 0x8B, 0xDC]),          # push ebx; mov ebx,esp
    bytes([0x6A]),                      # push imm8 (frame-less)
]


def func_start(data, secs, va, back=0x1200):
    """Find the function start containing va.

    Method: walk backwards looking for an alignment/padding boundary (a run of
    0xCC or 0x90) whose FOLLOWING byte begins an instruction stream that
    linearly decodes all the way to `va` (i.e. `va` is an instruction boundary
    in that stream). Take the LAST (highest) such boundary <= va.
    """
    o = va2off(secs, va)
    if o is None:
        return None
    lo = max(0, o - back)
    blob = data[lo:o + 16]
    cands = []
    i = 0
    while i < len(blob) - 1:
        b = blob[i]
        if b in (0xCC, 0x90):
            j = i
            while j < len(blob) and blob[j] in (0xCC, 0x90):
                j += 1
            if j < len(blob):
                cands.append(lo + j)
            i = j
        else:
            i += 1
    cands = [c for c in cands if c <= o]
    for c in sorted(cands, reverse=True):
        cva = va - (o - c)
        # linear-decode from c and see whether we land exactly on va
        boundaries = set()
        for ins in MD.disasm(data[c:o + 16], cva, 4000):
            boundaries.add(ins.address)
            if ins.address > va:
                break
        if va in boundaries:
            return cva
    return None


def find_dword_refs(data, secs, value, sections=None):
    """Every 4-byte-aligned dword in the given sections equal to `value`."""
    out = []
    tgt = struct.pack("<I", value)
    for n, sva, vsize, roff, rsize in secs:
        if sections and not any(n.startswith(s) for s in sections):
            continue
        blob = data[roff:roff+rsize]
        start = 0
        while True:
            k = blob.find(tgt, start)
            if k < 0:
                break
            va = IMAGE_BASE + sva + k
            out.append((n, va, va % 4 == 0))
            start = k + 1
    return out


def dump_dwords(data, secs, va, before=8, after=12):
    o = va2off(secs, va)
    if o is None:
        return
    for k in range(-before, after + 1):
        a = va + k * 4
        oo = o + k * 4
        if oo < 0 or oo + 4 > len(data):
            continue
        d = struct.unpack_from("<I", data, oo)[0]
        mark = "  <== " if k == 0 else "       "
        s = sec_of(secs, d) or ""
        print(f"    [{a:08X}] = {d:08X} {('(' + s + ')') if s else ''}{mark}")


def show(data, secs, va, n, title, tags=None):
    print(f"\n--- {title}  @ 0x{va:08X} ---")
    tags = tags or {}
    for ins in disasm(data, secs, va, n):
        t = ""
        for off, what in tags.items():
            if f"+ 0x{off:x}]" in ins.op_str or f"+ {off}]" in ins.op_str:
                t = f"   <<< {what}"
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}{t}")


def main():
    data, secs = load()
    print(f"exe {len(data):,} bytes")
    for n, sva, vsize, roff, rsize in secs:
        print(f"  {n:<9} VA {IMAGE_BASE+sva:08X}-{IMAGE_BASE+sva+vsize:08X} raw {roff:08X}+{rsize:X}")

    print("\n" + "=" * 74)
    print("A. VERIFY THE LEAD'S CALLER COUNTS")
    print("=" * 74)
    for name, va in (("0x0079ED90 rowfill", ROWFILL),
                     ("0x007A2380 mid", MID),
                     ("0x007A2740 top", TOP)):
        c = callers_of(data, secs, va)
        print(f"  {name}: {len(c)} caller(s): " + ", ".join(hex(x) for x in c))

    print("\n" + "=" * 74)
    print("B. FUNCTION STARTS")
    print("=" * 74)
    for site in (0x7a2628, 0x7a3267):
        fs = func_start(data, secs, site)
        print(f"  call site {hex(site)} lives in function {hex(fs) if fs else 'UNKNOWN'}")

    print("\n" + "=" * 74)
    print("C. WALK UP FROM THE FUNCTION CONTAINING 0x7a3267")
    print("=" * 74)
    level = [func_start(data, secs, 0x7a3267)]
    seen = set()
    for depth in range(6):
        nxt = []
        for f in level:
            if f is None or f in seen:
                continue
            seen.add(f)
            cs = callers_of(data, secs, f)
            starts = []
            for c in cs:
                s = func_start(data, secs, c)
                starts.append((c, s))
            print(f"  depth {depth}: fn {hex(f)} <- {len(cs)} call site(s)")
            for c, s in starts:
                print(f"      site {hex(c)} in fn {hex(s) if s else '?'}")
                if s:
                    nxt.append(s)
            if not cs:
                print(f"      *** NO rel32 CALLERS -> vtable / indirect entry point ***")
        level = list(dict.fromkeys(nxt))
        if not level:
            break

    print("\n" + "=" * 74)
    print("D. .rdata SEARCH FOR EVERY CHAIN VA (vtable membership)")
    print("=" * 74)
    chain = [ROWFILL, MID, TOP, MM_DRAW]
    f1 = func_start(data, secs, 0x7a3267)
    if f1:
        chain.append(f1)
    for va in chain:
        refs = find_dword_refs(data, secs, va)
        print(f"\n  VA {va:08X}: {len(refs)} dword occurrence(s) in the whole image")
        for n, at, aligned in refs:
            print(f"    at {at:08X} in {n} (aligned={aligned})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
