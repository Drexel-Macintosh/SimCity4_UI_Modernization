#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LANE 2 adversarial verify - step 5: is the change GENUINELY a no-op at the
shipped sub-2.5 factors?

Simulates the EMITTED WRITE SET of v2.73.3's ApplyOrdinanceInsetScale and of
the patched pair (ApplyOrdinanceInsetScale + ApplyOrdinanceNameColumnScale),
transcribed line by line from the patch text, and diffs them per factor.

POSITIVE CONTROL: at f = 3.00 the two write sets MUST differ (that is the
whole point of the patch). A simulator that reports "identical" everywhere is
comparing nothing. A second control injects a deliberately wrong gate
(>=200 instead of >=250) and asserts f=2.00 then DOES differ.

Also disassembles the instructions that set up eax before the income window,
to name what [edx+0x1C] is called on.
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IB = 0x400000

# ---- v2.73.3 (current, read off src/CodePatches.cpp lines 193-208, 911-954)
OLD_SITES = [
    (0x77C998, 0x12, 0x68), (0x77CA88, 0x12, 0x51), (0x77CAE0, 0x22, 0x41),
    (0x77CE3E, 0x12, 0x55), (0x77CF16, 0x12, 0x51), (0x77CF6E, 0x22, 0x41),
    (0x77CC23, 0x44, 0x55), (0x77D0E0, 0x44, 0x55),
]
# ---- v2.74.0 (the patch): six + two split, plus the two blocks
NEW_INSET = OLD_SITES[:6]
NEW_NAMEX = OLD_SITES[6:]
BLOCKS = [(0x0077CBFC, 43), (0x0077D0B9, 43)]
STOCK_X = 68


def lround(x):
    # C's lround: half away from zero. Python's round() is banker's.
    import math
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def imm8_loop(sites, f):
    """Exactly ApplyInsetSiteArray / the old loop body."""
    out = []
    for site, stock, ctx in sites:
        v = lround(stock * f)
        if v == stock:
            continue
        if v < 1:
            continue
        if v > 127:
            v = 127
        out.append((site, bytes([0x6A, v, ctx])))
    return out


def old_emit(f):
    return imm8_loop(OLD_SITES, f)


def new_emit(f, gate_pct=250):
    uses_block = lround(f * 100.0) >= gate_pct
    out = imm8_loop(NEW_INSET, f)
    if not uses_block:
        out += imm8_loop(NEW_NAMEX, f)
    if uses_block:
        x = lround(STOCK_X * f)
        if 127 < x <= 4096:
            for site, ln in BLOCKS:
                out.append((site, ("BLOCK-%d-bytes imm32=%d" % (ln, x)).encode()))
    return out


def show(tag, e):
    return "{" + ", ".join("0x%08X:%s" % (s, b.hex(" ") if len(b) <= 8 else b.decode())
                           for s, b in sorted(e)) + "}"


FACTORS = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
print("SHIPPED TIERS (src/ScaleTier.cpp kPackages): 4.0, 3.0, 2.0, 1.5 - there")
print("is NO 2.5 package, so the gate only ever separates {1.5, 2.0} from {3.0, 4.0}.")
print()
fail = []
for f in FACTORS:
    o = sorted(old_emit(f))
    n = sorted(new_emit(f))
    same = (o == n)
    print("f=%.2f  lround(68*f)=%-4d gate(lround(f*100)>=250)=%-5s  write sets %s"
          % (f, lround(68 * f), str(lround(f * 100.0) >= 250), "IDENTICAL" if same else "DIFFER"))
    print("        v2.73.3 : %s" % show("old", o))
    print("        v2.74.0 : %s" % show("new", n))
    if f <= 2.0 and not same:
        fail.append("f=%.2f is NOT a no-op" % f)
    if f >= 2.5 and same:
        fail.append("f=%.2f is unchanged - the patch does nothing at the tier it targets" % f)

print("\nPOSITIVE CONTROL 1: f=3.00 must DIFFER -> %s"
      % ("PASS" if sorted(old_emit(3.0)) != sorted(new_emit(3.0)) else "FAIL"))
c2 = sorted(old_emit(2.0)) != sorted(new_emit(2.0, gate_pct=200))
print("POSITIVE CONTROL 2: with a deliberately wrong gate (>=200) f=2.00 must")
print("                    DIFFER, proving the comparison can see a 2x change")
print("                    -> %s" % ("PASS" if c2 else "FAIL"))
if not c2:
    fail.append("no-op comparison is blind (control 2 failed)")

# gate boundary behaviour on values an ini could produce
print("\nGATE BOUNDARY (manual ScaleFactor= in the ini bypasses the tier table):")
for f in (2.49, 2.495, 2.4999, 2.5, 2.501, 2.55):
    print("   f=%-7s lround(f*100)=%-4d  block=%-5s  x=%d"
          % (f, lround(f * 100.0), lround(f * 100.0) >= 250, lround(68 * f)))

# ----------------------------------------------------------- lead-in disasm
print("\nWHAT SETS eax BEFORE THE INCOME WINDOW (what [edx+0x1C] is called on)")
data = open(EXE, "rb").read()
pe = struct.unpack_from("<I", data, 0x3C)[0]
nsec = struct.unpack_from("<H", data, pe + 6)[0]
opt = struct.unpack_from("<H", data, pe + 20)[0]
secs, off = [], pe + 24 + opt
for _ in range(nsec):
    nm = data[off:off+8].rstrip(b"\0").decode("latin1")
    vs, va, rs, ro = struct.unpack_from("<IIII", data, off + 8)
    secs.append((nm, va, vs, ro, rs)); off += 40
def v2o(va):
    r = va - IB
    for nm, sva, vs, ro, rs in secs:
        if sva <= r < sva + max(vs, rs):
            return ro + (r - sva)
md = Cs(CS_ARCH_X86, CS_MODE_32)
start = 0x0077CBC0
o = v2o(start)
for i in md.disasm(data[o:o+0x50], start):
    if i.address >= 0x0077CBFC + 6:
        break
    mark = "  <== WINDOW STARTS" if i.address == 0x0077CBFC else ""
    print("   0x%08X  %-7s %s%s" % (i.address, i.mnemonic, i.op_str, mark))

print()
if fail:
    print("RESULT: %d PROBLEM(S)" % len(fail))
    for m in fail: print("  - " + m)
    sys.exit(1)
print("RESULT: no-op / gate simulation GREEN")
sys.exit(0)
