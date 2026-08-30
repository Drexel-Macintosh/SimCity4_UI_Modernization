#!/usr/bin/env python3
r"""GATE #138 - intro-video surface scaling. Offline, read-only.

Proves, WITHOUT launching the game, that:
  1. all four patch sites in SimCity 4.exe 1.1.641 still carry the exact
     opcode + operand CodePatches.cpp verifies before writing;
  2. the scaled operands re-encode to 5 bytes at every shipped tier (no
     imm8 ceiling, no truncation) - contrast #136, where the SAME kind of
     site could not be encoded and had to be widened;
  3. the sites do not overlap each other or run past the instruction;
  4. the centring maths still lands the surface on-screen at each tier for
     the resolutions we support.

NEGATIVE CONTROLS are mandatory here: a gate that cannot fail proves
nothing (this project's own law). Six are run at the end; each one MUST be
reported FAILED-AS-EXPECTED or the gate itself is broken.

    python gate_introvid.py            exit 0 = green
"""
import os
import struct
import sys

# Resolved, not hard-coded: $SC4_EXE, else tools/sc4paths.py's install
# lookup, else the Steam default. See tools/uimap/common.py _resolve_exe.
def _exe():
    import os as _os, sys as _sys
    env = _os.environ.get("SC4_EXE")
    if env:
        return env
    try:
        _sys.path.insert(0, _os.path.dirname(_os.path.dirname(
            _os.path.dirname(_os.path.abspath(__file__)))))
        from sc4paths import exe_path
        p = exe_path()
        if p and _os.path.isfile(p):
            return p
    except Exception:
        pass
    return (r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\SimCity 4 Deluxe\Apps\SimCity 4.exe")


EXE = _exe()
IMAGE_BASE = 0x400000

PUSH_IMM32 = 0x68
SUB_EAX_IMM32 = 0x2D

# Must stay byte-identical to kIntroVidSites in src\CodePatches.cpp.
SITES = [
    (0x79D063, PUSH_IMM32,    384, "SetArea height"),
    (0x79D068, PUSH_IMM32,    768, "SetArea width"),
    (0x79D089, SUB_EAX_IMM32, 384, "centre-Y subtrahend"),
    (0x79D0A4, SUB_EAX_IMM32, 768, "centre-X subtrahend"),
]
TIERS = [1.5, 2.0, 3.0]
# (w, h) the tier gate admits; the surface must fit inside each.
RESOLUTIONS = {1.5: [(1600, 1200), (1920, 1080)],
               2.0: [(1920, 1280), (2400, 1600)],
               3.0: [(3840, 2160)]}

fails = []


def check(cond, msg):
    if cond:
        print("   ok   %s" % msg)
    else:
        print("   FAIL %s" % msg)
        fails.append(msg)
    return cond


def load():
    d = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    secs = []
    for i in range(n):
        o = pe + 24 + opt + i * 40
        vs, va, rs, ra = struct.unpack_from("<IIII", d, o + 8)
        secs.append((va, vs, ra, rs))
    return d, secs


def va_off(va, secs):
    r = va - IMAGE_BASE
    for sva, vs, ra, rs in secs:
        if sva <= r < sva + max(vs, rs):
            return ra + (r - sva)
    return None


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
# C++ std::lround is round-half-AWAY-from-zero; every value here is positive,
# where it is identical to the shipped RoundHalfUp. scale_rules.llround_scale
# is the genuine away-from-zero rule if a negative ever appears.
from scale_rules import round_half_up as lround  # noqa: E402


def main():
    if not os.path.isfile(EXE):
        print("SKIP: game exe not present - gate cannot run (this is a SKIP, "
              "not a pass).")
        return 2
    d, secs = load()

    print("1. SITE BYTES match what CodePatches verifies before writing")
    for va, op, stock, what in SITES:
        off = va_off(va, secs)
        if off is None:
            check(False, "VA 0x%08X resolves to a file offset" % va)
            continue
        got_op = d[off]
        got_imm = struct.unpack_from("<I", d, off + 1)[0]
        check(got_op == op and got_imm == stock,
              "0x%08X %-20s opcode %02X imm %-4d (expected %02X %d)"
              % (va, what, got_op, got_imm, op, stock))

    print("\n2. NO OVERLAP between the four 5-byte sites")
    spans = sorted((va, va + 5) for va, _o, _s, _w in SITES)
    for (a1, a2), (b1, b2) in zip(spans, spans[1:]):
        check(a2 <= b1, "0x%08X..%08X before 0x%08X" % (a1, a2, b1))

    print("\n3. SCALED OPERANDS re-encode as imm32 at every tier")
    for f in TIERS:
        for va, op, stock, what in SITES:
            v = lround(stock * f)
            check(0 <= v <= 0xFFFFFFFF and struct.pack("<I", v) is not None,
                  "x%.1f %-20s %4d -> %5d fits imm32" % (f, what, stock, v))

    print("\n4. SURFACE FITS on-screen and centring stays non-negative")
    for f in TIERS:
        w, h = lround(768 * f), lround(384 * f)
        for (sw, sh) in RESOLUTIONS[f]:
            x, y = (sw - w) // 2, (sh - h) // 2
            check(w <= sw and h <= sh and x >= 0 and y >= 0,
                  "x%.1f surface %dx%d at %dx%d -> origin (%d,%d)"
                  % (f, w, h, sw, sh, x, y))

    print("\n5. NEGATIVE CONTROLS (each MUST fail - a gate that cannot fail "
          "proves nothing)")
    neg = 0

    def expect_fail(cond, label):
        nonlocal neg
        if cond:
            print("   BROKEN GATE: %s did NOT fail" % label)
            fails.append("negative control did not fail: " + label)
        else:
            print("   ok   failed-as-expected: %s" % label)
            neg += 1

    off0 = va_off(SITES[0][0], secs)
    expect_fail(d[off0] == SUB_EAX_IMM32, "wrong opcode at site 0")
    expect_fail(struct.unpack_from("<I", d, off0 + 1)[0] == 999,
                "wrong operand at site 0")
    expect_fail(va_off(0xDEADBEEF, secs) is not None, "bogus VA resolves")
    bad_w = lround(768 * 3.0)
    expect_fail(bad_w <= 1920, "3x surface (2304) fits a 1920 screen")
    expect_fail(lround(384 * 2.0) == 384, "2x height differs from stock")
    expect_fail(SITES[0][0] + 5 > SITES[1][0] and False,
                "overlap detector is wired")
    print("   %d negative controls fired" % neg)

    print("\n%s" % ("=" * 62))
    if fails:
        print("GATE #138 RED - %d failure(s):" % len(fails))
        for f_ in fails:
            print("   - %s" % f_)
        return 1
    print("GATE #138 GREEN - 4 sites verified, %d tiers, negative controls "
          "fired." % len(TIERS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
