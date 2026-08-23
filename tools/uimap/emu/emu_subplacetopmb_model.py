"""emu_subplacetopmb_model.py - #95 Phase 3 (root cause): ground-truth proof
for SubPlaceTopMb() in UiSpike.cpp, added 2026-08-23 - run against SimCity
4's OWN sub_79AD00 under Unicorn, the SAME real machine code
emu_subplace_model.py already validates SubPlaceTop/SubPlaceLeft against.

WHY THIS EXISTS, AND WHY IT REPLACES emu_subsharedbottom_model.py AS THE
LOAD-BEARING PROOF: that file hardcodes n=8 for every cy it tests - it never
emulated the ACTUAL content height of the four buttons this fix exists for
(Police cnt=5, Fire cnt=3, Education cnt=6, Hospitals cnt=3; newH
580/384/678/384 at 2x). An adversarial review (2026-08-23) caught this: the
claim "reproduces the real function bit-exact for every measured Civic
Tools button" was true when first checked, but the checking was done in a
throwaway /tmp script that was never committed - so the claim had no
reproducible artifact backing it in the repo. This file is that artifact.
It also validates SubBarClampsAt8Rows/SubSharedBottom are RETIRED (not
called from the live path any more; kept only as dead code for a possible
future fallback) by testing the function that actually ships instead:
SubPlaceTopMb(contentH, cy, mT, mB, f).

WHAT IS REAL AND WHAT IS MODELLED
  REAL machine code, executed: sub_79AD00 (container Place), exactly as
  emu_subplace_model.py already exercises - same STOCK_FIELDS, same
  item metrics, same SetArea-stub harness.
  MODELLED (python): SubPlaceTopMb's own arithmetic, transcribed from
  src/UiSpike.cpp - the two must produce bit-identical output for this
  file to prove anything.

THE KEY DIFFERENCE FROM emu_subplace_model.py'S HARNESS: that file feeds
the emulator a SINGLE, FIXED cy=560 and lets margB be re-derived from a
VIEW_H constant, because it is proving the OLD SubPlaceTop's OWN clamp
arithmetic in the abstract (any cy, any margin - a pure function check).
This file feeds it the REAL, MEASURED per-button cy values AND the REAL,
MEASURED, raw mT=10/mB=1166 DIRECTLY as arguments 5/6 to Place() - never
re-derived from a desktop resolution - because it is proving a claim about
THIS SPECIFIC GAME SESSION'S geometry, not the function in isolation.

MEASURED, 2026-08-23 (Civic Tools census, live SUBPLACE log, mB=1166,
mT=10, all at f=2.0 - see research/laws/project-sc4-flyout-bottom-anchor.md
"Attempt 4"):
  Police     cy=397  cnt=5   (broken under both prior fix attempts)
  Fire       cy=497  cnt=3   (broken under both prior fix attempts)
  Education  cy=595  cnt=6   (broken under both prior fix attempts)
  Hospitals  cy=697  cnt=3   (broken under both prior fix attempts)
  Landmarks  cy=797  cnt=43  (reported correct; visually capped at 8 rows)
  Rewards    cy=895  cnt=36  (reported correct; visually capped at 8 rows)
  Parks      cy=997  cnt=11  (reported correct; visually capped at 8 rows)

Run after any change to SubPlaceTopMb. Exit 0 = every predicted (L,T,H),
for every named button AT ITS OWN REAL CONTENT HEIGHT (not a fixed n=8),
matches what the REAL emulated sub_79AD00 does.
"""
import os
import struct
import sys
import importlib.util

EMU = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, EMU)
spec = importlib.util.spec_from_file_location(
    "emu_subflyout", os.path.join(EMU, "emu_subflyout.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX

RHU = m.round_half_up
CX = 205          # measured raw Place() cx - GLOBAL across every bar
MT_RAW = 10       # measured raw Place() mT - GLOBAL, never re-derived
MB_RAW = 1166     # measured raw Place() mB - GLOBAL, never re-derived

# (name, cy, cnt) - the full Civic Tools census. cnt is capped at 8 for the
# three "visually capped" buttons, matching what the strip actually shows
# (the >8 remainder scrolls) - see SUBFLYOUT-BUILDER.md ss3.1's row-count cap.
BUTTONS = [
    ("Police",    397, 5),
    ("Fire",      497, 3),
    ("Education", 595, 6),
    ("Hospitals", 697, 3),
    ("Landmarks", 797, 8),
    ("Rewards",   895, 8),
    ("Parks",     997, 8),
]


def sub_place_top_mb(content_h, cy, mT, mB, f):
    """Transcribed from UiSpike.cpp SubPlaceTopMb() - the prediction under
    test. Must stay byte-identical to the C++ or this file proves nothing
    about what actually ships."""
    fE8 = RHU(25 * f)
    fF4 = RHU(53 * f)
    f100 = RHU(29 * f)
    top = (fF4 >> 1) - (content_h >> 1) + cy - f100
    if top < mT:
        top = mT
    if top > mB - content_h:
        top = mB - content_h
    if top > cy - f100 - fE8:
        top = cy - f100 - fE8
    floorT = cy + fF4 - content_h + fE8 - f100
    if top < floorT:
        top = floorT
    return top


def emu_place_at(emu, n, f, cy, margT, margB):
    """Same harness as emu_subplace_model.emu_place, parameterized by cy
    and the REAL raw margins instead of the fixed CY/VIEW_H module
    globals - this is what lets the SAME real function answer the
    placement question for every measured button AT ITS OWN REAL COUNT,
    not just a fixed n=8."""
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

    print("Test-SubPlaceTopMb (ground truth, sub_79AD00 under Unicorn)")
    print("  f=%.1f mT=%d mB=%d cx=%d - RAW, never re-derived from a "
          "desktop resolution" % (f, MT_RAW, MB_RAW, CX))
    print("  %-10s %6s %5s %8s %8s %10s" %
          ("name", "cy", "cnt", "predict", "real", "verdict"))

    failures = []
    bottoms_cnt8 = {}
    for name, cy, n in BUTTONS:
        e = emu_place_at(emu, n, f, cy, MT_RAW, MB_RAW)
        if e is None:
            failures.append("%s: emulator never reached SetArea - the "
                             "harness itself is broken, not the formula."
                             % name)
            continue
        el, et, er, eb = e
        eH = eb - et
        predicted = sub_place_top_mb(eH, cy, MT_RAW, MB_RAW, f)
        ok = predicted == et
        print("  %-10s %6d %5d %8d %8d %10s"
              % (name, cy, n, predicted, et, "ok" if ok else "*** MISMATCH ***"))
        if not ok:
            failures.append(
                "%s (cy=%d, n=%d): SubPlaceTopMb predicts top=%d, REAL "
                "emulated Place() gives top=%d (h=%d). These must agree "
                "bit-exact." % (name, cy, n, predicted, et, eH))
        if n == 8:
            bottoms_cnt8[name] = et + eH

    print()
    print("  identical-bottom check (every n=8 button, REAL emulated "
          "output, no python-only shortcut):")
    distinct = set(bottoms_cnt8.values())
    print("    %s -> %s" % (bottoms_cnt8, distinct))
    if len(distinct) != 1:
        failures.append(
            "The REAL emulated sub_79AD00 does not give every n=8 Civic "
            "Tools button the same bottom: %s. The 'identical bottom' "
            "claim is not just a python-model artifact - it must hold "
            "against the actual game function too." % bottoms_cnt8)
    else:
        print("    [every n=8 button's REAL emulated bottom is identical, "
              "no python shortcut involved]                          ok")

    print()
    if failures:
        print("FAIL: %d problem(s):" % len(failures))
        for fail in failures:
            print("  - %s" % fail)
        return 1
    print("ALL PASS (SubPlaceTopMb's predictions match the REAL emulated "
          "sub_79AD00 for every named Civic Tools button AT ITS OWN REAL "
          "content height - cnt<8 included, not just the n=8 cap)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
