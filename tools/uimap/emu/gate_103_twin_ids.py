#!/usr/bin/env python3
"""#103 OFFLINE GATE - the TWIN DISCRIMINATOR only.

SCOPE (read this before quoting the exit code):
  This gate proves ONE thing: that window 0x0423278D is built by exactly two
  functions, and that the outer backdrop-container id (0x484 vs 0x485) tells
  them apart UNAMBIGUOUSLY in the shipped exe.  It is the offline half of the
  #103 fix - the half that says "the runtime test the patch uses is sound".

  It does NOT and CANNOT adjudicate:
    * whether the POPBOX sweep ever reaches either popup (needs a live log),
    * the live hit rect of any window (needs the game),
    * whether the close-X works (that is gate_103_closepath.py).

Exit 0 = every check passed.  Any FAIL -> exit 1.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common                                        # noqa: E402

EXE = common.EXE
BASE = 0x400000
# RE-PINNED 2026-08-05 (was 1189720d5e15b0e1). The game was wiped and
# reinstalled from Steam, and the new exe is a DIFFERENT binary of the same
# size (7,876,608) - so the build this gate was originally derived from no
# longer exists on disk and cannot be diffed against.
# THE RE-PIN WAS EARNED, NOT ASSUMED: every byte-level site assertion in this
# gate was run against the new exe FIRST, with the fingerprint check bypassed,
# and all of them passed - the instructions this gate reasons about are
# identical. Re-pinning a fingerprint because a tool said no, without checking
# the bytes, is exactly how the #140 splash shipped CAM art. Do not do it.
# The value below is the LAA-MASKED hash (see common.exe_fingerprint): the
# 4GB patch flips one header bit and used to move this hash on its own.
EXPECT_FP = ("f9b059d29940d1a2", 7876608)

ORD_LO, ORD_HI = 0x0078B120, 0x0078BCA0   # sub_78B120  ordinance description popup
LED_LO, LED_HI = 0x0077BEC0, 0x0077C360   # sub_77BEC0  empty-ledger box

fails = []


def check(name, ok, detail=""):
    print("  %-58s %s %s" % (name, "PASS" if ok else "FAIL", detail))
    if not ok:
        fails.append(name)


def main():
    # This used to hash the file itself, a THIRD private copy of
    # exe_fingerprint. Copies diverge: when common.py learned to mask the LAA
    # bit (the 4GB patch flips it and it cannot change an instruction), the two
    # that shared common.py came back green and this one stayed red on the same
    # binary. One implementation, imported.
    raw = common.exe_bytes()
    fp = common.exe_fingerprint()
    print("exe fingerprint: %s" % (fp,))
    check("exe is the shipped 1.1.641.0", fp == EXPECT_FP, str(EXPECT_FP))

    def find_all(pat):
        out, i = [], 0
        while True:
            j = raw.find(pat, i)
            if j < 0:
                return out
            out.append(BASE + j)
            i = j + 1

    # 1. The popup id exists at exactly two CREATE sites (push imm32).
    sites = find_all(b"\x68" + struct.pack("<I", 0x0423278D))
    check("0x0423278D pushed at exactly 2 sites", len(sites) == 2,
          [hex(s) for s in sites])
    check("  one site inside sub_78B120 (ordinance)",
          any(ORD_LO <= s < ORD_HI for s in sites))
    check("  one site inside sub_77BEC0 (empty-ledger)",
          any(LED_LO <= s < LED_HI for s in sites))

    # 2. Each builder's own ids, as CREATE-site pushes.
    def pushes(imm):
        if imm < 0x80:
            return find_all(bytes([0x6A, imm]))
        return find_all(b"\x68" + struct.pack("<I", imm))

    for label, imm, lo, hi, other_lo, other_hi in (
            ("ordinance backdrop 0x384", 0x384, ORD_LO, ORD_HI, LED_LO, LED_HI),
            ("ordinance outer     0x484", 0x484, ORD_LO, ORD_HI, LED_LO, LED_HI),
            ("ordinance close-X   0x068", 0x68, ORD_LO, ORD_HI, LED_LO, LED_HI),
            ("ledger    backdrop 0x385", 0x385, LED_LO, LED_HI, ORD_LO, ORD_HI),
            ("ledger    outer    0x485", 0x485, LED_LO, LED_HI, ORD_LO, ORD_HI),
            ("ledger    close-X  0x0CC", 0xCC, LED_LO, LED_HI, ORD_LO, ORD_HI),
    ):
        p = pushes(imm)
        inside = [x for x in p if lo <= x < hi]
        crossed = [x for x in p if other_lo <= x < other_hi]
        check("%s present in its own builder" % label, len(inside) > 0,
              [hex(x) for x in inside])
        check("%s ABSENT from the twin" % label, len(crossed) == 0,
              [hex(x) for x in crossed])

    # 3. THE DISCRIMINATOR the patch relies on.
    check("0x484 never referenced inside sub_77BEC0",
          not [x for x in pushes(0x484) if LED_LO <= x < LED_HI])
    check("0x485 never referenced inside sub_78B120",
          not [x for x in pushes(0x485) if ORD_LO <= x < ORD_HI])

    # 4. The five SetSize sites we byte-patch are still stock 300x100.
    stock = bytes([0x6A, 0x64, 0x68, 0x2C, 0x01, 0x00, 0x00])
    for s in (0x77C19E, 0x77C1B0, 0x77C1D9, 0x77C2E0, 0x77C301):
        check("kBizBoxSizeSites %s == push 0x64/push 0x12C" % hex(s),
              raw[s - BASE:s - BASE + 7] == stock,
              raw[s - BASE:s - BASE + 7].hex())
    check("kBizBoxCloseY 0x77C2BA == push 0x0B",
          raw[0x77C2BA - BASE:0x77C2BA - BASE + 2] == bytes([0x6A, 0x0B]))
    check("kBizBoxCloseX 0x77C2BC == push 0x10D",
          raw[0x77C2BC - BASE:0x77C2BC - BASE + 5] ==
          bytes([0x68, 0x0D, 0x01, 0x00, 0x00]))
    check("close-X id push 0x77C2C1 == push 0xCC (WE NEVER WRITE THIS)",
          raw[0x77C2C1 - BASE:0x77C2C1 - BASE + 5] ==
          bytes([0x68, 0xCC, 0x00, 0x00, 0x00]))

    # 5. The tier table the brief pre-commits to.
    print("\n  TIER TABLE - what CodePatches builds the empty-ledger box as:")
    print("    factor   bw    bh(raw)  bh(shipped, imm8 clamp)   closeX  closeY")
    for f in (1.0, 1.5, 2.0, 3.0):
        bw = round(300 * f)
        raw_h = round(100 * f)
        bh = min(raw_h, 127)
        cx = bw - round(31 * f)
        cy = min(round(11 * f), 127)
        if bw == 300:
            print("    %-6s   %-5d %-8d %-25s %-7s %s"
                  % (f, bw, raw_h, "(patch SKIPPED - stock)", "-", "-"))
        else:
            print("    %-6s   %-5d %-8d %-25d %-7d %d" % (f, bw, raw_h, bh, cx, cy))
    print("\n  POPBOX pins wantH = round(125*f) = %s"
          % [round(125 * f) for f in (1.0, 1.5, 2.0, 3.0)])
    print("  DEAD BAND (hit rect minus drawn frame) if the pin is applied to")
    print("  the empty-ledger twin: %s px at 1x/1.5x/2x/3x"
          % [round(125 * f) - (100 if f == 1.0 else min(round(100 * f), 127))
             for f in (1.0, 1.5, 2.0, 3.0)])

    print("\nOVERALL: %s" % ("PASS" if not fails else "FAIL -> %s" % fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
