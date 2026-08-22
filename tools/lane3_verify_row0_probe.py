#!/usr/bin/env python3
"""ADVERSARIAL VERIFY of LANE 3's ROW0_TOP claim.

POSITIVE CONTROL (stated up front, per project law):
  Before believing anything this probe says about 0x0076DE79, it re-reads the
  EIGHT sites CodePatches.cpp already ships and asserts they match the byte
  arrays in that source file. Those eight are user-confirmed live (#57), so if
  the PE load / VA->offset math were wrong, the control MUST fail. A pass on
  8/8 proves this probe can see the shipped bytes at this exact address range.

Read-only. Writes nothing.
"""
import sys, struct, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

SITE = 0x0076DE79
CLAIM = bytes([0xC7, 0x44, 0x24, 0x18, 0x14, 0x00, 0x00, 0x00])

# --- control set, transcribed from src/CodePatches.cpp ------------------------
IMM_SITES = [
    (0x0076E233, (0x8D, 0x48, 3), "swatch dy"),
    (0x0076E239, (0x83, 0xC0, 9), "swatch bot"),
    (0x0076E23C, (0x83, 0xC3, 10), "swatch w"),
    (0x0076E2AF, (0x83, 0xC1, 4), "swatch->txt"),
    (0x0076E2C8, (0x83, 0xEA, 4), "text right"),
]
B1 = bytes([0x8B,0x5C,0x24,0x50, 0x8B,0x54,0x24,0x48, 0x8B,0x41,0x44, 0x2B,0xDA,
            0x83,0xEB,0x6A, 0x83,0xF8,0x02, 0x0F,0x86,0xFF,0x00,0x00,0x00])
B2 = bytes([0x8B,0x5C,0x24,0x48, 0x8B,0x54,0x24,0x50, 0x8B,0x4C,0x24,0x18,
            0x83,0xC1,0x10, 0x51, 0x2B,0xD3, 0x8B,0x18, 0x8D,0x4A,0xA4, 0x51,
            0x8B,0x4C,0x24,0x20, 0x51, 0x83,0xC2,0x94, 0x52, 0x8B,0xC8,
            0xFF,0x93,0xDC,0x00,0x00,0x00])
B3 = bytes([0x8B,0x1E, 0x8B,0x17, 0x8B,0x2B, 0x8B,0xCF, 0xFF,0x52,0x0C, 0x50,
            0x8B,0xCB, 0xFF,0x55,0x38, 0x8B,0x4C,0x24,0x48, 0x8B,0x5C,0x24,0x50,
            0x2B,0xD9, 0x8D,0x8C,0x24,0xF8,0x00,0x00,0x00, 0x83,0xEB,0x5A,
            0xE8,0xE0,0x49,0xE9,0xFF])
BLOCKS = [(0x0076E0E8, B1, "B1"), (0x0076E145, B2, "B2"), (0x0076E1D6, B3, "B3")]

FN = 0x0076D3D0   # sub_76D3D0, the legend/panel builder
FN_END_HINT = 0x0076E600


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


def va2off(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def rd(data, secs, va, n):
    o = va2off(secs, va)
    return data[o:o+n] if o is not None else None


def main():
    if not os.path.exists(EXE):
        print("EXE NOT FOUND"); return 2
    data, secs = load()
    print(f"exe {len(data):,} bytes\n")

    # ---------------- POSITIVE CONTROL ---------------------------------
    print("=" * 74)
    print("0. POSITIVE CONTROL - can this probe see the 8 SHIPPED sites?")
    print("=" * 74)
    ok = 0
    for va, exp, name in IMM_SITES:
        got = rd(data, secs, va, 3)
        good = tuple(got) == exp
        ok += good
        print(f"  0x{va:08X} {name:<14} got {got.hex(' ')}  expect "
              f"{bytes(exp).hex(' ')}  {'OK' if good else '*** MISMATCH ***'}")
    for va, exp, name in BLOCKS:
        got = rd(data, secs, va, len(exp))
        good = got == exp
        ok += good
        print(f"  0x{va:08X} {name:<14} {len(exp)}B  {'OK' if good else '*** MISMATCH ***'}")
    print(f"  CONTROL: {ok}/8")
    if ok != 8:
        print("  *** PROBE IS BLIND - refusing to report anything below. ***")
        return 3

    # ---------------- 1. the claimed stock bytes ------------------------
    print("\n" + "=" * 74)
    print("1. STOCK BYTES AT 0x0076DE79")
    print("=" * 74)
    got = rd(data, secs, SITE, 16)
    print(f"  file @0x{va2off(secs, SITE):08X}: {got.hex(' ')}")
    print(f"  claimed first 8      : {CLAIM.hex(' ')}")
    print(f"  MATCH: {got[:8] == CLAIM}")

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    print("\n  disasm around the site (-0x30 .. +0x30):")
    o = va2off(secs, SITE - 0x30)
    for ins in md.disasm(data[o:o+0x70], SITE - 0x30):
        mark = "  <== SITE" if ins.address == SITE else ""
        inside = (SITE < ins.address < SITE + 8)
        if inside:
            mark = "  <== INSIDE REPLACED WINDOW"
        print(f"   0x{ins.address:08X}  {ins.bytes.hex(' '):<26}"
              f"{ins.mnemonic:<7} {ins.op_str}{mark}")

    # ---------------- 2. every write/read of [esp+0x18] in the fn -------
    print("\n" + "=" * 74)
    print("2. EVERY reference to [esp+0x18] / esp-relative 0x18 in sub_76D3D0")
    print("=" * 74)
    o = va2off(secs, FN)
    span = FN_END_HINT - FN
    for ins in md.disasm(data[o:o+span], FN):
        if "esp + 0x18" in ins.op_str or "esp + 0x18]" in ins.op_str:
            print(f"   0x{ins.address:08X}  {ins.mnemonic:<7} {ins.op_str}")

    # ---------------- 3. branch targets landing INSIDE the window -------
    print("\n" + "=" * 74)
    print("3. ANY branch/call in .text whose TARGET lands inside "
          "0x0076DE7A..0x0076DE80")
    print("=" * 74)
    lo, hi = SITE + 1, SITE + 8   # strictly inside the replaced window
    hits = []
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff+rsize]
        for i in range(len(blob) - 6):
            b = blob[i]
            if b in (0xE8, 0xE9):                       # call/jmp rel32
                rel = struct.unpack_from("<i", blob, i + 1)[0]
                t = base + i + 5 + rel
            elif b == 0x0F and 0x80 <= blob[i+1] <= 0x8F:  # jcc rel32
                rel = struct.unpack_from("<i", blob, i + 2)[0]
                t = base + i + 6 + rel
            elif b == 0xEB or (0x70 <= b <= 0x7F):      # short jmp/jcc
                rel = struct.unpack_from("<b", blob, i + 1)[0]
                t = base + i + 2 + rel
            else:
                continue
            if lo <= t < hi or t == SITE:
                hits.append((base + i, t, b))
    if hits:
        for s, t, b in hits:
            tag = "INSIDE (CRASH)" if lo <= t < hi else "== SITE (fine)"
            print(f"   0x{s:08X} -> 0x{t:08X}  op {b:02X}  {tag}")
    else:
        print("   none")
    # control for section 3: prove the scanner CAN find a known target
    known = 0x0076E200   # B1's jbe destination, from the source comment
    ctl = []
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff+rsize]
        for i in range(len(blob) - 6):
            b = blob[i]
            if b == 0x0F and 0x80 <= blob[i+1] <= 0x8F:
                rel = struct.unpack_from("<i", blob, i + 2)[0]
                if base + i + 6 + rel == known:
                    ctl.append(base + i)
    print(f"   [control] jcc-rel32 branches found targeting 0x{known:08X}: "
          f"{len(ctl)} -> {[hex(x) for x in ctl[:6]]}")
    ctlmsg = "PASS - scanner can see a real branch target" if ctl else "*** FAIL - scanner blind ***"
    print("   [control] " + ctlmsg)

    # ---------------- 4. absolute imm32 references to the site ----------
    print("\n" + "=" * 74)
    print("4. ANY absolute dword in the image equal to a VA inside the window")
    print("=" * 74)
    found = []
    for cand in range(SITE, SITE + 8):
        pat = struct.pack("<I", cand)
        idx = data.find(pat)
        while idx != -1:
            found.append((cand, idx))
            idx = data.find(pat, idx + 1)
    for cand, idx in found[:20]:
        print(f"   VA 0x{cand:08X} appears as a literal at file offset 0x{idx:X}")
    if not found:
        print("   none")

    # ---------------- 5. overlap with the 3 re-encoded blocks -----------
    print("\n" + "=" * 74)
    print("5. OVERLAP with the three re-encoded blocks")
    print("=" * 74)
    for va, blob, name in BLOCKS:
        a0, a1 = SITE, SITE + 8
        b0, b1 = va, va + len(blob)
        ov = not (a1 <= b0 or b1 <= a0)
        print(f"   {name} [0x{b0:08X},0x{b1:08X})  overlap with "
              f"[0x{a0:08X},0x{a1:08X}) : {ov}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
