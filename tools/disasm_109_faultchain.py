#!/usr/bin/env python3
"""#109 follow-up: WHOSE code is the fault chain?

The tier-3 / tier-1.5 data-view crash faults at 0x00910010 (rep stosd inside
memset32), reached per the exception-report stack from:

    0x0079ED90  (row fill)  <-  0x007A2380  <-  0x007A2740

THE QUESTION THAT DECIDES THE "STRETCH THE MAP TO FILL THE FRAME" PLAN:
is that chain reachable from cSC4WinMiniMap's OWN draw override (0x007A79B0)?

  * If YES  -> hooking that draw replaces the drawing entirely, so we can put
               the window back to 768, blit the legal 512 surface scaled, and
               the faulting path never runs.
  * If NO   -> some other consumer reads the window rect independently, the
               crash returns the moment the window goes back to 768, and the
               stretch plan is OFF.

Read-only. Disassembles the shipped exe; writes nothing.
"""
import sys, struct, io, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

FAULT      = 0x00910010   # rep stosd
ROWFILL    = 0x0079ED90
MID        = 0x007A2380
TOP        = 0x007A2740
MM_DRAW    = 0x007A79B0   # cSC4WinMiniMap draw override (window vt+0x160)
MM_CLASSVT = 0x00ADF6A0   # (GZWinBMP class vt, for contrast)


def load():
    data = open(EXE, "rb").read()
    # PE section table -> map VA to file offset
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


def disasm(data, secs, va, count=90):
    o = va2off(secs, va)
    if o is None:
        return []
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    return list(md.disasm(data[o:o+count*8], va, count))


def calls_from(data, secs, va, span=0x800):
    """Every `call rel32` in the `span` bytes from va.

    NOTE: deliberately does NOT stop at the first `ret`. The earlier version
    did, and since 0x007A79B0 opens with an early-out it only ever saw a
    handful of calls - a STRUCTURAL NULL dressed up as 'not reachable'.
    Scanning raw bytes for E8 over-approximates (it can catch a call in a
    neighbouring function), which is the safe direction here: this probe is
    being used to look for reachability, so over-reach risks a FALSE POSITIVE,
    never a false 'unreachable'.
    """
    o = va2off(secs, va)
    if o is None:
        return []
    blob = data[o:o+span]
    out = []
    for i in range(len(blob) - 5):
        if blob[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", blob, i + 1)[0]
        out.append(va + i + 5 + rel)
    return out


def callers_of(data, secs, target):
    """Every `call rel32` in .text whose destination == target."""
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


def main():
    if not os.path.exists(EXE):
        print("EXE NOT FOUND:", EXE); return 2
    data, secs = load()
    print(f"exe {len(data):,} bytes, {len(secs)} sections\n")

    print("=" * 72)
    print("1. CALLERS OF EACH LINK IN THE FAULT CHAIN")
    print("=" * 72)
    for name, va in (("rowfill 0x0079ED90", ROWFILL),
                     ("mid     0x007A2380", MID),
                     ("top     0x007A2740", TOP)):
        c = callers_of(data, secs, va)
        print(f"{name}: {len(c)} caller(s) -> " +
              (", ".join(hex(x) for x in c[:12]) if c else "NONE (vtable/indirect only)"))
    print()

    def reaches(root, targets, maxdepth=4):
        seen, frontier, depth_of = set(), [root], {root: 0}
        while frontier:
            cur = frontier.pop(0)
            if cur in seen or depth_of[cur] > maxdepth:
                continue
            seen.add(cur)
            for t in calls_from(data, secs, cur):
                if t in targets:
                    return (cur, t), seen
                if t not in depth_of and IMAGE_BASE < t < IMAGE_BASE + 0x800000:
                    depth_of[t] = depth_of[cur] + 1
                    frontier.append(t)
        return None, seen

    print("=" * 72)
    print("2. IS THE CHAIN REACHABLE FROM THE MINIMAP DRAW 0x007A79B0?")
    print("=" * 72)
    # POSITIVE CONTROL FIRST. 0x7a3267 is the measured sole caller of TOP, so a
    # walk rooted at the function containing it MUST find TOP. If the control
    # fails, the probe is blind and any 'not reachable' below is meaningless.
    ctl_hit, ctl_seen = reaches(0x007A3240, {TOP}, maxdepth=2)
    print(f"  positive control (walk from 0x007A3240, which contains the known "
          f"call site 0x7a3267):")
    print(f"    {'FOUND ' + hex(ctl_hit[1]) if ctl_hit else '*** CONTROL FAILED - PROBE IS BLIND ***'}"
          f"   ({len(ctl_seen)} fns walked)")
    if not ctl_hit:
        print("  Refusing to report a null from a probe that cannot see a known edge.")
        return 3
    hit, seen = reaches(MM_DRAW, {TOP, MID, ROWFILL, FAULT}, maxdepth=4)
    print(f"\n  minimap draw walk: {len(seen)} functions to depth 4")
    if hit:
        print(f"  *** REACHABLE ***  {hex(hit[0])} calls {hex(hit[1])}")
        print("  => the minimap's own draw leads into the faulting chain.")
    else:
        print("  NOT reachable.")
        print("  => the faulting chain is NOT under the minimap draw override.")
    print()

    print("=" * 72)
    print("3. WHAT 0x007A2740 READS (window rect vs blitSize vs raster)")
    print("=" * 72)
    for ins in disasm(data, secs, TOP, 60):
        s = f"  0x{ins.address:08X}  {ins.mnemonic:<7} {ins.op_str}"
        tag = ""
        for off, what in ((0xE4, "blitSize"), (0xF0, "surface"), (0x104, "zoom"),
                          (0x114, "rasterBase"), (0x118, "rasterW"), (0x11C, "rasterH"),
                          (0x34, "rect.L"), (0x38, "rect.T"), (0x3C, "rect.R"), (0x40, "rect.B")):
            if f"+ 0x{off:x}" in ins.op_str or f"+ {off}" in ins.op_str:
                tag = f"   <<< {what}"
        print(s + tag)
        if ins.mnemonic == "ret":
            break
    print()

    print("=" * 72)
    print("4. THE MINIMAP DRAW ITSELF (0x007A79B0), first 45")
    print("=" * 72)
    for ins in disasm(data, secs, MM_DRAW, 45):
        tag = ""
        for off, what in ((0xE4, "blitSize"), (0xF0, "surface"), (0x114, "rasterBase"),
                          (0x118, "rasterW"), (0x34, "rect.L"), (0x38, "rect.T"),
                          (0x3C, "rect.R"), (0x40, "rect.B")):
            if f"+ 0x{off:x}" in ins.op_str:
                tag = f"   <<< {what}"
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<7} {ins.op_str}{tag}")
        if ins.mnemonic == "ret":
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
