"""emu_subsharedbottom_model.py - #95 Phase 3: ground-truth proof for the
BOTTOM-ANCHOR LAW (SubSharedBottom / SubBarClampsAt8Rows in UiSpike.cpp,
added 2026-08-23), run against SimCity 4's OWN sub_79AD00 under Unicorn -
the SAME real machine code emu_subplace_model.py already validates
SubPlaceTop/SubPlaceLeft against, not a second, independent re-derivation.

RETIRED, 2026-08-23 (same day, later pass): SubSharedBottom/
SubBarClampsAt8Rows are no longer called from the live birth-hook path -
see SubPlaceTopMb's comment in src/UiSpike.cpp for why (their margin
source, gLastViewH, was itself wrong). They are kept as dead code, not
deleted, so this file still validates something real (the retired
formulas still exist in the binary and this still proves they were never
internally inconsistent) - but it is NOT the load-bearing proof for what
ships any more. That is emu_subplacetopmb_model.py, which also fixes this
file's own gap (an adversarial review caught it): every case below is
hardcoded to n=8, so none of it ever emulated the ACTUAL content height of
the four short-count buttons (cnt=5/3/6/3) the whole fix exists for.
Run emu_subplacetopmb_model.py to verify what actually ships.

WHY THIS EXISTS: Test-SubFlyoutPlacement.py proves the C++ formulas are
*internally* consistent (SubSharedBottom reduces to the plain formula for
an unclamped bar, etc.) but it is a pure Python re-implementation - it
would happily agree with itself if the ORIGINAL closed-form margin clamp
(`top = min(top, margB - contentH)`) were subtly wrong. This file instead
asks the real emulated game function: for the two live-measured cy values
that anchor the whole law - Parks (cy=997, the ONE clamping bar) and
Police (cy=397, a confirmed non-clamping bar) - does an 8-row-equivalent
container ACTUALLY clamp against the margin the way SubBarClampsAt8Rows
predicts?

MEASURED, 2026-08-23 (Civic Tools census, live SUBPLACE log, mB=1166,
mT=10, viewH=1600, all at f=2.0 - see research/laws/
project-sc4-flyout-bottom-anchor.md):
  Parks   cy=997  (Build Park/Green Spaces/Sports Grounds/Plazas bar) - CLAMPS
  Police  cy=397  - does NOT clamp
  Fire    cy=497  - does NOT clamp
  Education cy=595 - does NOT clamp
  Hospitals cy=697 - does NOT clamp
  Landmarks cy=797 - does NOT clamp
  Rewards cy=895  - does NOT clamp

Run after any change to SubSharedBottom, SubBarClampsAt8Rows, or SubPlaceTop.
Exit 0 = every predicted clamp/no-clamp verdict, for every named button,
matches what the REAL emulated function does.
"""
import os
import struct
import sys
import importlib.util

EMU = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "emu_subflyout", os.path.join(EMU, "emu_subflyout.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

RHU = m.round_half_up
VIEW_H = 1600   # measured gLastViewH (2400x1600 desktop, 2x session)
MB = 1166       # measured raw Place() mB - GLOBAL across every bar
MT = 10         # measured raw Place() mT - GLOBAL across every bar
CX = 205        # measured raw Place() cx - GLOBAL across every bar

# (name, cy, expected clamp verdict) - the full Civic Tools census plus Parks.
BUTTONS = [
    ("Parks",     997, True),
    ("Police",    397, False),
    ("Fire",      497, False),
    ("Education", 595, False),
    ("Hospitals", 697, False),
    ("Landmarks", 797, False),
    ("Rewards",   895, False),
]


def sub_bar_clamps_at_8_rows(cy, mB):
    """UiSpike.cpp SubBarClampsAt8Rows(), transcribed - the prediction
    under test."""
    full8_1x = 2 * 25 + 8 * (44 + 5) - 5   # = 437
    hyp_native_top8 = 26 - (full8_1x >> 1) + cy - 29
    return hyp_native_top8 > (mB - full8_1x)


def emu_place_at(emu, n, f, cy, margT, margB):
    """Same harness as emu_subplace_model.emu_place, parameterized by cy
    and the real margins instead of the fixed CY/VIEW_H module globals -
    this is what lets the SAME real function answer the clamp question
    for every measured button, not just the one cy the original file
    hardcodes."""
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX
    uc = emu.uc
    obj, vt = m.HEAP + 0x1000, m.HEAP + 0x8000
    uc.mem_write(obj, b"\x00" * 0x400)
    uc.mem_write(vt, b"\x00" * 0x400)
    uc.mem_write(vt + 0xDC, struct.pack("<I", m.SETAREA_STUB))
    uc.mem_write(obj + 4, struct.pack("<I", vt))
    for off, val in m.STOCK_FIELDS.items():
        uc.mem_write(obj + off, struct.pack("<i", RHU(val * f)))
    itemW, itemH, spacing = (RHU(m.ITEM_W * f), RHU(m.ITEM_H * f),
                              RHU(m.SPACING * f))
    args = (itemW, (itemH + spacing) * n - spacing, CX, cy, margT, margB)
    esp = m.STACK + m.STACKSZ - 0x100
    for a in reversed(args):
        esp -= 4
        uc.mem_write(esp, struct.pack("<i", a))
    esp -= 4
    uc.mem_write(esp, struct.pack("<I", m.MAGIC_RET))
    uc.reg_write(UC_X86_REG_ESP, esp)
    uc.reg_write(UC_X86_REG_ECX, obj)
    emu.setarea = None
    uc.emu_start(m.PLACE_FN, m.MAGIC_RET)
    return emu.setarea


def main():
    emu = m.PlaceEmu()
    emu.fields = m.STOCK_FIELDS
    f = 2.0
    n = 8   # the 8-row-equivalent container the whole law is defined on
    margT = MT   # the REAL raw mT, not RHU(10*f) - the model's own margin
    margB = MB   # guess this simulator's predecessor never had to question,
                 # since it only ever ran one cy that happened not to need it

    print("Test-SubSharedBottom (ground truth, sub_79AD00 under Unicorn)")
    print("  f=%.1f n=%d mT=%d mB=%d cx=%d viewH=%d"
          % (f, n, MT, MB, CX, VIEW_H))
    print("  %-10s %6s %8s %8s %10s" %
          ("name", "cy", "predict", "real", "verdict"))

    failures = []
    for name, cy, expect_clamp in BUTTONS:
        e = emu_place_at(emu, n, f, cy, margT, margB)
        if e is None:
            failures.append("%s: emulator never reached SetArea - the "
                             "harness itself is broken, not the law."
                             % name)
            continue
        el, et, er, eb = e
        eH = eb - et
        # Reconstruct the UNCLAMPED naive top the same way the real
        # function's first line does, so we can tell WHICH clamp (if any)
        # bound - margin-bottom is the one this law's gate is about.
        f_e8 = RHU(25 * f)
        f_f4 = RHU(53 * f)
        f_100 = RHU(29 * f)
        naive_top = (f_f4 >> 1) - (eH >> 1) + cy - f_100
        margin_bound = margB - eH
        really_clamped_at_margin = (naive_top > margin_bound) and (
            et == margin_bound)
        predicted = sub_bar_clamps_at_8_rows(cy, MB)
        ok = predicted == expect_clamp == really_clamped_at_margin
        print("  %-10s %6d %8s %8s %10s"
              % (name, cy, predicted, really_clamped_at_margin,
                 "ok" if ok else "*** MISMATCH ***"))
        if not ok:
            failures.append(
                "%s (cy=%d): SubBarClampsAt8Rows predicts clamp=%s, "
                "census expects %s, REAL emulated Place() shows clamp=%s "
                "(top=%d vs naive=%d, marginBound=%d). These must all "
                "agree." % (name, cy, predicted, expect_clamp,
                            really_clamped_at_margin, et, naive_top,
                            margin_bound))

    print()
    if failures:
        print("FAIL: %d problem(s):" % len(failures))
        for fail in failures:
            print("  - %s" % fail)
        return 1
    print("ALL PASS (SubBarClampsAt8Rows' predictions match the REAL "
          "emulated sub_79AD00 for every named Civic Tools button)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
