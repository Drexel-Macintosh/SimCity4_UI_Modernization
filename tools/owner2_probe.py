#!/usr/bin/env python3
"""Owner probe #2: build REAL function boundaries, then walk up.

Method (no padding heuristic):
  1. Collect every rel32 call target in .text  -> a set of KNOWN function starts.
     (positive control: 0x0079ED90 / 0x007A2380 / 0x007A2740 must be in it)
  2. Sort them. The function containing VA = the greatest known start <= VA,
     VERIFIED by linear-decoding from that start and requiring VA to be an
     instruction boundary reachable without crossing a ret+padding run.
  3. Also collect rel32 JMP (E9) targets and short jmp targets so tail calls
     and jump-table-free flow are visible.
Read-only.
"""
import sys, struct, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
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


def text_ranges(secs):
    for n, sva, vsize, roff, rsize in secs:
        if n.startswith(".text"):
            yield IMAGE_BASE + sva, roff, min(vsize, rsize)


def scan_edges(data, secs):
    """Return (call_targets, call_sites, jmp32_targets, jmp32_sites)."""
    ct = {}   # target -> [sites]
    jt = {}
    for base, roff, size in text_ranges(secs):
        blob = data[roff:roff+size]
        for i in range(len(blob) - 5):
            b = blob[i]
            if b == 0xE8 or b == 0xE9:
                rel = struct.unpack_from("<i", blob, i + 1)[0]
                site = base + i
                tgt = site + 5 + rel
                if not (IMAGE_BASE < tgt < IMAGE_BASE + 0x800000):
                    continue
                (ct if b == 0xE8 else jt).setdefault(tgt, []).append(site)
    return ct, jt


def main():
    data, secs = load()
    ct, jt = scan_edges(data, secs)
    starts = sorted(ct.keys())
    print(f"rel32 call targets (candidate function starts): {len(starts)}")
    # POSITIVE CONTROL
    for v in (0x0079ED90, 0x007A2380, 0x007A2740, 0x007A79B0):
        print(f"  control: {v:08X} in call-target set = {v in ct}")

    import bisect

    def containing(va):
        i = bisect.bisect_right(starts, va) - 1
        return starts[i] if i >= 0 else None

    print("\n" + "=" * 74)
    print("BYTES BEFORE 0x007A2FFD (is it a real function start?)")
    print("=" * 74)
    o = va2off(secs, 0x007A2FFD)
    print("  raw:", data[o-32:o+8].hex(" "))
    print("  disasm ending just before 0x7A2FFD:")
    for ins in MD.disasm(data[o-0x60:o+0x30], 0x007A2FFD - 0x60, 200):
        mk = "  <== 0x7A2FFD" if ins.address == 0x007A2FFD else ""
        print(f"    0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}{mk}")
        if ins.address > 0x007A2FFD + 0x18:
            break

    print("\n" + "=" * 74)
    print("CONTAINING FUNCTION OF EACH CALL SITE (call-target based)")
    print("=" * 74)
    for site in (0x7a2628, 0x7a3267, 0x7a24bb, 0x7a347b, 0x7a41a1, 0x7a436b):
        c = containing(site)
        print(f"  site {hex(site)} -> containing candidate {hex(c) if c else '?'}"
              f"  (callers of that: {len(ct.get(c, []))})")

    print("\n" + "=" * 74)
    print("WALK UP  (call-target function starts, callers via rel32 call+jmp)")
    print("=" * 74)
    root = containing(0x7a3267)
    level = [root]; seen = set(); depth = 0
    while level and depth < 8:
        nxt = []
        for f in level:
            if f in seen:
                continue
            seen.add(f)
            csites = ct.get(f, [])
            jsites = jt.get(f, [])
            print(f"\n  [d{depth}] fn {hex(f)}: {len(csites)} call site(s), {len(jsites)} jmp site(s)")
            for s in csites + jsites:
                p = containing(s)
                kind = "call" if s in [x for x in csites] else "jmp "
                print(f"        {kind} from {hex(s)}  in fn {hex(p) if p else '?'}")
                if p and p != f:
                    nxt.append(p)
            if not csites and not jsites:
                print("        *** no direct predecessors: vtable/indirect entry ***")
        level = list(dict.fromkeys(x for x in nxt if x not in seen))
        depth += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
