#!/usr/bin/env python3
"""Walk UP from the #109 fault chain until we hit a vtable-referenced function.

The chain (0x0079ED90 <- 0x007A2380 <- 0x007A2740 <- 0x7a3267) is reached only
by direct calls - measured, positive control passed. So the entry point into
this subsystem is above it. Find the first ancestor that IS in a vtable: that
names the class, and its vtable address tells us whether it is the minimap
(vt 0x00AB8518) or something else.
"""
import sys, struct

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
START = 0x007A2740
MM_VT = 0x00AB8518   # cSC4WinMiniMap's vtable slot holding its draw override


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs, off = [], pe + 24 + opt
    for _ in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


def build_call_index(data, secs):
    """target -> [call sites]  for every call rel32 in .text"""
    idx = {}
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base, blob = IMAGE_BASE + sva, data[roff:roff+rsize]
        for i in range(len(blob) - 5):
            if blob[i] != 0xE8:
                continue
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            tgt = base + i + 5 + rel
            if IMAGE_BASE < tgt < IMAGE_BASE + 0x800000:
                idx.setdefault(tgt, []).append(base + i)
    return idx


def build_dword_index(data, secs):
    """code VA -> [addresses in any section holding it as a dword] (vtables)"""
    idx = {}
    for n, sva, vsize, roff, rsize in secs:
        base, blob = IMAGE_BASE + sva, data[roff:roff+rsize]
        for i in range(0, len(blob) - 4, 4):
            v = struct.unpack_from("<I", blob, i)[0]
            if 0x407000 + IMAGE_BASE - 0x400000 <= v < IMAGE_BASE + 0x700000:
                idx.setdefault(v, []).append((n, base + i))
    return idx


def fn_start(data, secs, site):
    """Scan back from a call site for a plausible function prologue."""
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        if not (base <= site < base + rsize):
            continue
        o = roff + (site - base)
        for back in range(0, 0x900):
            p = o - back
            if p < roff:
                break
            b = data[p:p+3]
            # sub esp,imm8/32 | push ebp; mov ebp,esp | push ebx/esi/edi run
            if b[:3] == b"\x83\xec" [:2] + data[p+2:p+3] and data[p] == 0x83 and data[p+1] == 0xEC:
                return base + (p - roff)
            if data[p] == 0x81 and data[p+1] == 0xEC:
                return base + (p - roff)
            if data[p] == 0x55 and data[p+1] == 0x8B and data[p+2] == 0xEC:
                return base + (p - roff)
    return None


def main():
    data, secs = load()
    print("indexing…")
    calls = build_call_index(data, secs)
    dwords = build_dword_index(data, secs)
    print(f"  {len(calls):,} call targets, {len(dwords):,} dword-referenced VAs\n")

    # POSITIVE CONTROL: the minimap draw must show up as dword-referenced.
    if 0x007A79B0 not in dwords:
        print("*** CONTROL FAILED: 0x007A79B0 not dword-referenced. Probe blind."); return 3
    print(f"positive control: 0x007A79B0 dword-referenced at "
          f"{', '.join(hex(a) for _, a in dwords[0x007A79B0][:3])}  OK\n")

    print("=" * 72)
    print("UPWARD WALK FROM 0x007A2740")
    print("=" * 72)
    cur, depth, seen = START, 0, set()
    while cur and depth < 10:
        vt = dwords.get(cur)
        mark = ""
        if vt:
            mark = "   <<< IN A VTABLE: " + ", ".join(f"{s}@{a:#x}" for s, a in vt[:3])
            if any(a == MM_VT for _, a in vt):
                mark += "  == cSC4WinMiniMap!"
        print(f"  depth {depth}: {cur:#010x}{mark}")
        if vt:
            print("\n  => reached a vtable-referenced function. That names the owner.")
            break
        sites = calls.get(cur, [])
        if not sites:
            print("     no direct callers -> entry is indirect (vtable/callback) or data-driven")
            break
        print(f"     {len(sites)} caller site(s): {', '.join(hex(s) for s in sites[:6])}")
        nxt = fn_start(data, secs, sites[0])
        if nxt is None or nxt in seen:
            print("     could not resolve containing function start; stopping")
            break
        seen.add(nxt)
        cur, depth = nxt, depth + 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
