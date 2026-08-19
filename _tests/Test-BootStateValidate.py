#!/usr/bin/env python
"""Gate: the BOOT-STATE VALIDATOR's truth table.

WHY THIS EXISTS
---------------
A hand-edited SC4UIScale.ini can put the mod into states that are not merely
wrong but INESCAPABLE - the UI ends up too large to navigate, or the art is
armed while the geometry sweep is off, and the in-game control that would fix
it is gone or cannot write the key that matters. An audit of the ini surface
confirmed 26 such states, several of which trapped the user with no way back.

ScaleTier::ValidateBootState answers "is [AutoScale, ScaleFactor, ScaleAll,
packages, resolution] coherent?" and repairs it. This gate pins the answers.

⚠ THIS MIRRORS THE PREDICATE, IT DOES NOT CALL IT - the same shape as
Test-ScaleTierDecide against Decide(). That is a real limitation and it is
stated rather than hidden: this proves the RULE is what we intend and that it
behaves on every case the audit found, not that the C++ says the same thing.
The structural half is Test-StockTierContract; the runtime half is a boot.

The rows below are the audit's findings, one row per confirmed failure mode,
plus the cases that must NOT be repaired - which are the ones worth guarding,
because a validator that flips too eagerly destroys a 1x reference capture or
invents a small screen out of a number it never measured.

PASS = exit 0.
"""
import math
import sys

# Mirrors src/ScaleTier.cpp: kPackages[] largest-first, and the fit constants.
KNOWN_TIERS = [4.0, 3.0, 2.0, 1.5]
WIDEST, TALLEST = 880, 558


def fits(f, w, h):
    if w <= 0 or h <= 0 or f <= 1.01:
        return f <= 1.01
    cap = min(w / 800.0, h / 600.0)
    return WIDEST * f <= w and TALLEST * f <= h and f <= cap


def known(f):
    return any(abs(f - t) <= 0.01 for t in KNOWN_TIERS)


def available(f, installed):
    return known(f) and any(abs(f - t) <= 0.01 for t in installed)


def decide(installed, w, h):
    if w <= 0 or h <= 0:
        return 1.0
    for t in sorted(KNOWN_TIERS, reverse=True):
        if not any(abs(t - i) <= 0.01 for i in installed):
            continue
        if fits(t, w, h):
            return t
    return 1.0


def validate(auto, factor, scale_all, installed, w, h, section_ok=True):
    """Returns (coherent, auto_after, factor_after, wrote_ini)."""
    measured = w > 0 and h > 0
    # C0 - could we read the section at all?
    if not section_ok:
        return (False, False, 1.0, False)
    # C1 - ScaleAll off while the factor asks for a tier
    effective = decide(installed, w, h) if auto else factor
    if not scale_all and not math.isnan(effective) and effective > 1.01:
        return (False, False, 1.0, False)
    if auto:
        # ⚠ THE EFFECTIVE FACTOR UNDER AUTO IS Decide(), NOT THE INI'S.
        # ValidateBootState returns early here without touching st.factor, and
        # the director's AutoScale branch then overwrites spikeScaleFactor with
        # Decide() on the very next lines. Modelling it as "the ini value
        # survives" made the swept invariant report 15052 violations that the
        # real code cannot produce - the mirror was wrong, not the rule. Which
        # is the point of sweeping: the truth table passed all 16 rows while
        # the model was still wrong about the commonest configuration.
        return (True, True, decide(installed, w, h), False)
    # C2 - finite
    if math.isnan(factor) or abs(factor) > 1.0e6:
        t = decide(installed, w, h)
        return (False, True, t, True)
    # C3 - below stock: clamp, never flip
    if factor < 1.0:
        return (False, auto, 1.0, False)
    # C4 - manual stock is coherent, short-circuit
    if factor <= 1.01:
        return (True, auto, factor, False)
    # C5 - a tier the table knows
    if not known(factor):
        t = decide(installed, w, h)
        return (False, True, t, True)
    # C6 - and its art is on disk
    if not available(factor, installed):
        t = decide(installed, w, h)
        return (False, True, t, True)
    # C7 - and the screen can carry it
    if not measured:
        return (True, auto, factor, False)
    if not fits(factor, w, h):
        t = decide(installed, w, h)
        return (False, True, t, True)
    return (True, auto, factor, False)


ALL3 = [1.5, 2.0, 3.0]
INF = float("inf")
NAN = float("nan")

# (name, auto, factor, scaleAll, installed, w, h, section_ok,
#  expect coherent, expect auto_after, expect factor_after, expect wrote)
ROWS = [
    # ---- must REPAIR (each row is a confirmed audit finding) -------------
    ("4x is a table row no package was ever built for",
     False, 4.0, True, ALL3, 5120, 2880, True, False, True, 3.0, True),
    ("3x requested, only 1.5/2 installed",
     False, 3.0, True, [1.5, 2.0], 3840, 2160, True, False, True, 2.0, True),
    ("2.5 fits geometrically but is not a tier",
     False, 2.5, True, ALL3, 3840, 2160, True, False, True, 3.0, True),
    ("infinity accepted by wcstod",
     False, INF, True, ALL3, 3840, 2160, True, False, True, 3.0, True),
    ("NaN slips past every > comparison",
     False, NAN, True, ALL3, 3840, 2160, True, False, True, 3.0, True),
    ("3x on a screen that cannot carry it (the off-screen dialog trap)",
     False, 3.0, True, ALL3, 1920, 1080, True, False, True, 1.5, True),
    ("4x with NO resolution - the package check needs no screen",
     False, 4.0, True, ALL3, 0, 0, True, False, True, 1.0, True),
    ("ScaleAll=0 under AutoScale: tier art, no geometry",
     True, 2.0, False, ALL3, 3840, 2160, True, False, False, 1.0, False),
    ("ScaleAll=0 with a manual tier: same trap, manual branch",
     False, 2.0, False, ALL3, 3840, 2160, True, False, False, 1.0, False),
    ("a BOM ate the [UiSpike] section",
     True, 2.0, True, ALL3, 3840, 2160, False, False, False, 1.0, False),
    ("negative factor clamps, and must NOT flip",
     False, -2.0, True, ALL3, 3840, 2160, True, False, False, 1.0, False),

    # ---- must NOT repair - the rows that matter most ---------------------
    ("MANUAL 1x - a stock reference capture, must never be flipped",
     False, 1.0, True, ALL3, 1024, 768, True, True, False, 1.0, False),
    ("3x with NO resolution - unmeasured is not evidence of a small screen",
     False, 3.0, True, ALL3, 0, 0, True, True, False, 3.0, False),
    # Auto picks 3x here, not the 2.0 sitting in the ini - 880*3=2640 <= 3840
    # and 558*3=1674 <= 2160. The ini's ScaleFactor is inert under AutoScale.
    ("AutoScale with everything installed",
     True, 2.0, True, ALL3, 3840, 2160, True, True, True, 3.0, False),
    ("manual 2x on a 3x-capable screen is a PREFERENCE, not a defect",
     False, 2.0, True, ALL3, 3840, 2160, True, True, False, 2.0, False),
    ("manual 1.5x that fits",
     False, 1.5, True, ALL3, 2400, 1600, True, True, False, 1.5, False),
]


def main():
    failures = []
    print("Test-BootStateValidate")
    print("  mirrors ScaleTier::ValidateBootState (see the docstring caveat)")
    print()
    for row in ROWS:
        (name, auto, factor, sa, inst, w, h, sect,
         xc, xa, xf, xw) = row
        got = validate(auto, factor, sa, inst, w, h, sect)
        want = (xc, xa, xf, xw)
        ok = (got[0] == want[0] and got[1] == want[1] and got[3] == want[3]
              and abs(got[2] - want[2]) <= 0.01)
        print("  [%s] %s" % ("ok  " if ok else "FAIL", name))
        if not ok:
            failures.append("%s\n      want coherent=%s auto=%s factor=%.2f wrote=%s"
                            "\n      got  coherent=%s auto=%s factor=%.2f wrote=%s"
                            % (name, want[0], want[1], want[2], want[3],
                               got[0], got[1], got[2], got[3]))

    # ---- the invariants, over a sweep -----------------------------------
    # A truth table proves the rows it lists. These prove the properties that
    # must hold for rows nobody thought to write down.
    print()
    bad_never, bad_stock, bad_write = 0, 0, 0
    factors = [NAN, INF, -2.0, 0.0, 0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 8.0]
    for w in range(320, 9000, 137):
        for h in range(240, 6000, 149):
            for f in factors:
                for auto in (False, True):
                    c, a, fa, wr = validate(auto, f, True, ALL3, w, h)
                    # I1: whatever comes out must be runnable - stock, or a
                    # tier that is installed AND fits the screen we measured.
                    if fa > 1.01 and not (available(fa, ALL3) and fits(fa, w, h)):
                        bad_never += 1
                    # I2: a manual stock request is never turned back on.
                    if not auto and f == 1.0 and (fa > 1.01 or a):
                        bad_stock += 1
                    # I3: nothing is ever written unless a repair happened.
                    if wr and c:
                        bad_write += 1
    for label, n, why in (
            ("I1 output is always runnable (stock, or installed AND fits)",
             bad_never, "a repair produced a factor that would fail again"),
            ("I2 manual 1x is never flipped on", bad_stock,
             "a stock reference capture would be destroyed"),
            ("I3 the ini is written only on a repair", bad_write,
             "a coherent boot would rewrite the user's file")):
        print("  [%s] %s" % ("ok  " if n == 0 else "FAIL", label))
        if n:
            failures.append("%s: %d violation(s) - %s" % (label, n, why))

    print()
    if failures:
        print("FAIL: %d problem(s):" % len(failures))
        for f in failures:
            print("  - %s" % f)
        return 1
    print("ALL PASS (%d truth-table rows + 3 swept invariants)" % len(ROWS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
