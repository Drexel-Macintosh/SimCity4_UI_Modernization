#!/usr/bin/env python3
"""
Test-SubFlyoutPlacement - the sub-flyout birth-hook placement chain, proven
as MATH before any of it runs on screen.

WHY THIS EXISTS: a first bottom-anchor attempt (rolled back the same session
it shipped) computed a new formula, deployed it, and only THEN found out on
screen that it regressed every approved menu by 232px. This gate exists so
every attempt is proven against MEASURED goldens before a single build is
deployed. Every formula below is transcribed from src/UiSpike.cpp - if
either drifts from the source, this gate and the DLL disagree and must be
reconciled, not silenced.

THIRD PASS (2026-08-23), ROOT CAUSE: the v4.0.36 fix (SubSharedBottom, a
per-bar mB-clamp gate + a hypothetical-8-row cyRef substitution + the flat
empirical bornshift SubContainerShiftPx) reproduced the approved Build
Park/Green Spaces case exactly, but a fresh 1x/2x click-through census
(Police/Fire/Education/Hospitals, all cnt<8) showed it was STILL reported
broken - unchanged from before the fix, because none of those bars clamp,
so they fall through to the OLD per-button formula untouched.

Deriving the real bottoms by hand (not eyeballing) turned up the actual
root cause: SubPlaceTop's own bottom margin was `gLastViewH - marginT` -
the DESKTOP height - not the game's own measured `mB` (a raw Place()
parameter, logged directly, never re-derived). Measured 2026-08-23: mB in
this session's SubPlaceTop-conditioning at f=2 the mB=1166 measured
against gLastViewH=1600 sits on a 1600-tall desktop, a 434px gap that is
the game's own bottom HUD/toolbar reserving screen space, not a scaling
artifact. Feeding SubPlaceTop the wrong (larger) margin meant its OWN
bottom clamp fired at the wrong threshold, and the flat 232px bornshift
that "corrected" it back was only ever tuned against ONE content height
(874, the 8-row cap) - it does not cancel the same way for a shorter
container, which is exactly why Police/Fire/Education/Hospitals stayed
broken through two "fixes."

CONFIRMED four independent ways before this was ever built:
  1. Hand arithmetic (this file, below).
  2. The REAL disassembled sub_79AD00, queried directly under Unicorn
     (tools/uimap/emu/emu_subplace_model.py's harness, fed fully-scaled
     item metrics + the RAW measured mT=10/mB=1166): reproduces this
     file's SubPlaceTopMb output bit-exact for cy in
     {397,497,595,697,797,895,997}.
  3. At f=1, SubPlaceTopMb (mB used directly) is algebraically identical
     to the OLD SubPlaceTop for any case that never reaches the margin
     clamp - and reproduces three numbers ALREADY on record from a
     completely different measurement (case 7 below): Hospitals top=598,
     Education top=423, Rewards top=674.
  4. Every cnt>=8 (visually 8-row-capped) button - Landmarks, Rewards,
     Parks - independently converges on the SAME bottom (1166) with NO
     per-bar gate and NO hypothetical container: any bar whose own real
     content is tall enough to reach mB clamps there, by construction.
     This is the user's law ("the bottom part of the flyout should be
     identical in all of these menus") falling out of the corrected
     formula for free.

WHAT THIS ASSERTS
  1. SubPlaceTop() (the OLD, viewH-margin formula) still reproduces the
     game's measured birth numbers for the two APPROVED containers (Build
     Park cnt=11, Green Spaces cnt=12) at 2x, bit-exact: dy == -453,
     final top == 276, bottom == 1150. This is NOT what ships any more
     (see #4/#5) - it is kept as the historical regression anchor so a
     future reader can see exactly what the old chain produced and why a
     16px difference from the new one is an EXPECTED, understood change,
     not a silent drift.
  2. SubContainerShiftPx() still reproduces the measured 232px shift at
     f=2.0 the OLD chain carried - unchanged, still used by the disaster
     twin, which this fix does not touch.
  3. full8H equals 874 at 2x - the height every cnt>=8 container measures
     at, confirmed against tools/uimap/SUBFLYOUT-BUILDER.md's own
     independently-derived height table.
  4. THE ROOT-CAUSE FIX: SubPlaceTopMb(contentH, cy, mT, mB, f) - the same
     four clamps, but marg_b = mB directly (never re-derived from a
     desktop viewH). Every cnt>=8 Civic Tools button (Landmarks, Rewards,
     Parks) converges on the SAME bottom (1166) - the "identical bottom"
     law, achieved with NO per-bar branch.
  5. Every cnt<8 Civic Tools button (Police, Fire, Education, Hospitals -
     all reported broken under BOTH prior attempts) now centers within a
     few px of its own button (cy), the natural, unclamped, correctly-
     scaled position - no off-screen values, no per-button inconsistency.
  6. f=1.0 sanity: SubPlaceTopMb, at f=1, exactly reproduces three
     ALREADY-recorded native measurements (Hospitals/Education/Rewards)
     that predate this fix and were never derived with it in mind -
     independent confirmation, not a tautology.
  7. NEGATIVE CONTROL: the OLD per-button-broken numbers (documented as
     BROKEN_PREFIX_* below) must NOT equal the new formula's output - if
     they do, this gate would not actually have caught the original
     defect.

This is a MODEL of the C++ chain, not a call into it (no build required to
run this file). Keep the constants and formulas below byte-identical to
src/UiSpike.cpp; a mismatch between this file and the source is itself a
defect this gate cannot see, so re-check by hand whenever SubPlaceTop,
SubPlaceTopMb, or SubContainerShiftPx change.

Exit 0 = pass. Run from anywhere.
"""

import math
import sys


def round_half_up(v):
    # UiSpike.cpp RoundHalfUp: floor(v + 0.5) - NOT the same as round() for
    # negative half values, but every input here is positive.
    return int(math.floor(v + 0.5))


def sub_place_top(content_h, cy, view_h, f):
    """Transcribed from UiSpike.cpp SubPlaceTop() (~line 1173) - the OLD,
    viewH-margin formula. Still used by the disaster twin; kept here ONLY
    as the historical regression anchor for the approved cnt>=8 case (see
    module docstring point 1) - NOT what the regular sub-flyout ships with
    any more."""
    f_e8 = round_half_up(25 * f)
    f_f4 = round_half_up(53 * f)
    f_100 = round_half_up(29 * f)
    marg_t = round_half_up(10 * f)
    marg_b = view_h - marg_t
    top = (f_f4 >> 1) - (content_h >> 1) + cy - f_100
    if top < marg_t:
        top = marg_t
    if view_h > 0 and top > marg_b - content_h:
        top = marg_b - content_h
    if top > cy - f_100 - f_e8:
        top = cy - f_100 - f_e8
    floor_t = cy + f_f4 - content_h + f_e8 - f_100
    if top < floor_t:
        top = floor_t
    return top


def sub_place_top_mb(content_h, cy, mT, mB, f):
    """Transcribed from UiSpike.cpp SubPlaceTopMb() (2026-08-23, root-cause
    pass) - THE FORMULA THAT SHIPS for the regular (non-disaster)
    sub-flyout. Same four clamps as sub_place_top, but mT/mB are the raw,
    LIVE, measured Place() parameters - never re-derived from a desktop
    resolution. Ground-truth verified against the real sub_79AD00 under
    Unicorn (tools/uimap/emu), 2026-08-23."""
    f_e8 = round_half_up(25 * f)
    f_f4 = round_half_up(53 * f)
    f_100 = round_half_up(29 * f)
    top = (f_f4 >> 1) - (content_h >> 1) + cy - f_100
    if top < mT:
        top = mT
    if top > mB - content_h:
        top = mB - content_h
    if top > cy - f_100 - f_e8:
        top = cy - f_100 - f_e8
    floor_t = cy + f_f4 - content_h + f_e8 - f_100
    if top < floor_t:
        top = floor_t
    return top


def sub_container_shift_px(f):
    """Transcribed from UiSpike.cpp SubContainerShiftPx() (~line 1279).
    Still used by the disaster twin only - the regular sub-flyout path no
    longer calls this."""
    if f <= 1.0:
        return 0
    est = f * f * 73.0 - 60.0
    if est <= 0.0:
        return 0
    return round_half_up(est)


def full8h(f, item_h_1x=44, spacing_1x=5, cap_h_1x=25):
    """8-row container height at scale f. full8H = 2*capHs +
    8*(itemHs+spacingS) - spacingS, matching tools/uimap/SUBFLYOUT-
    BUILDER.md's independently-derived height table (206/286/384/482/580/
    678/776/874 at 2x for n=1..8)."""
    cap_hs = round_half_up(cap_h_1x * f)
    item_hs = round_half_up(item_h_1x * f)
    spacing_s = round_half_up(spacing_1x * f)
    row_pitch = item_hs + spacing_s
    return 2 * cap_hs + 8 * row_pitch - spacing_s


def scaled_content_h(cnt, f):
    """The container's REAL content height for an actual item count,
    disassembly-confirmed (SUBFLYOUT-BUILDER.md ss3.3):
    contentH = max((itemH+spacing)*n - spacing, ringH) + 2*capH. Matches
    win->GetH() (read live at the birth hook) scaled by f - not a separate
    reconstruction, the SAME formula the game's own builder uses."""
    cap_hs = round_half_up(25 * f)
    item_hs = round_half_up(44 * f)
    spacing_s = round_half_up(5 * f)
    ring_hs = round_half_up(53 * f)
    strip_h = (item_hs + spacing_s) * cnt - spacing_s
    return max(strip_h, ring_hs) + 2 * cap_hs


# ---- measured goldens, 2x, from the live SUBPLACE/SUBBORN capture of
# 2026-08-23 (Build Park, Green Spaces, Sports Grounds all opened in one
# instrumented session; log grep is the source). ------------------------
F = 2.0
NATIVE_T_BP_GS = 729
NATIVE_T_SPORTS = 849
APPROVED_H = 874
OLD_APPROVED_BOTTOM = 1150   # what the v4.0.9-v4.0.36 chain produced
OLD_APPROVED_DY = -453
SPORTS_H = 580
SPORTS_WRONG_BOTTOM = 1050
SPORTS_DY = -379
# mT/mB are GLOBAL - the SAME raw value on every sub-flyout regardless of
# WHICH first-level flyout bar spawned it (re-confirmed across 3 measurement
# rounds, 17 distinct cy values total). Only cy varies, and it varies PER
# BAR/BUTTON, not per menu-within-a-bar.
MEASURED_MB = 1166
MEASURED_MT = 10
MEASURED_CY_CLAMPING_BAR = 997   # Parks (Build Park/Green Spaces/Sports Grounds/Plazas)

# ---- Round 2 (2026-08-23): ALL SEVEN Civic Tools buttons walked one at a
# time, user-confirmed click order top-to-bottom = name, with a live pass/
# fail report on four of them. This is the census that proved the defect is
# UNIVERSAL-SHORT-COUNT, not per-bar: every cnt<8 button was reported
# broken, every cnt>=8 button was reported correct, with ZERO exceptions
# across bars with four different native cy values. The v4.0.36 fix
# (SubSharedBottom) left the cnt<8 buttons STILL reported broken - this
# round's data is what led to the root-cause fix below.
CIVIC_TOOLS = [
    # (name, cy, cnt, reported under v4.0.9..v4.0.36)
    ("Police",    397, 5,  "broken"),
    ("Fire",      497, 3,  "broken"),
    ("Education", 595, 6,  "broken"),
    ("Hospitals", 697, 3,  "broken"),
    ("Landmarks", 797, 43, "correct"),
    ("Rewards",   895, 36, "correct"),
    ("Parks",     997, 11, "correct"),
]


def cy_from_native_top(native_t, ch_1x):
    # SubPlaceDetour's own OLD inversion (disaster twin only, post-fix):
    # cy = nativeT + (ch>>1) + 3. Used here ONLY to reproduce the historical
    # pre-fix approved-chain numbers for regression-anchoring.
    return native_t + (ch_1x >> 1) + 3


def main():
    failures = []

    full8 = full8h(F)
    print("Test-SubFlyoutPlacement")
    print("  full8H(f=%.1f) = %d" % (F, full8))
    if full8 != APPROVED_H:
        failures.append(
            "full8H(f=2.0) = %d, expected %d (the measured cnt>=8 container "
            "height). itemH/spacing/capH constants have drifted from "
            "UiSpike.cpp." % (full8, APPROVED_H))
    else:
        print("  [full8H matches measured 874]                        ok")

    shift = sub_container_shift_px(F)
    print("  SubContainerShiftPx(f=%.1f) = %d (disaster twin only)" % (F, shift))
    if shift != 232:
        failures.append(
            "SubContainerShiftPx(2.0) = %d, expected 232 (f*f*73-60 at "
            "f=2). The bornshift formula has drifted from UiSpike.cpp."
            % shift)
    else:
        print("  [bornshift matches measured 232]                     ok")

    # ---- 1: the OLD chain (SubPlaceTop + bornshift, recovered cy) still
    # reproduces its own historical measured numbers - the regression
    # anchor that proves this file's transcription of the OLD formula
    # hasn't silently drifted, so the "16px different, understood" claim
    # below has a real baseline to be different FROM.
    if APPROVED_H % 2 or SPORTS_H % 2:
        failures.append(
            "APPROVED_H/SPORTS_H is not evenly divisible by 2 - the "
            "1x-height derivation below assumes an exact integer tier and "
            "needs a real 1x measurement instead of a naive halving.")
    ch_1x_bp = APPROVED_H // 2
    ch_1x_sports = SPORTS_H // 2
    cy_bp = cy_from_native_top(NATIVE_T_BP_GS, ch_1x_bp)
    VIEW_H = 1600   # gLastViewH, measured (SELRES desktop 2400x1600) - the
                     # OLD formula's (wrong) margin source, kept only to
                     # reproduce what the OLD chain actually computed.
    model_top_bp = sub_place_top(APPROVED_H, cy_bp, VIEW_H, F)
    dy_bp = model_top_bp - shift - NATIVE_T_BP_GS
    print("  Build Park (OLD chain): cy=%d modelTop=%d dy=%d (expect %d)"
          % (cy_bp, model_top_bp, dy_bp, OLD_APPROVED_DY))
    if dy_bp != OLD_APPROVED_DY:
        failures.append(
            "Build Park/Green Spaces (cnt>=8) OLD-chain reproduction dy=%d, "
            "measured dy=%d. This anchor is broken - fix this BEFORE "
            "trusting the 'expected 16px difference' claim below."
            % (dy_bp, OLD_APPROVED_DY))
    else:
        print("  [OLD chain still reproduces its own measured -453]    ok")

    cy_sports = cy_from_native_top(NATIVE_T_SPORTS, ch_1x_sports)
    model_top_sports = sub_place_top(SPORTS_H, cy_sports, VIEW_H, F)
    dy_sports = model_top_sports - shift - NATIVE_T_SPORTS
    sports_bottom_current = NATIVE_T_SPORTS + dy_sports + SPORTS_H
    print("  Sports Grounds (OLD chain, wrong): dy=%d bottom=%d "
          "(measured wrong bottom %d)"
          % (dy_sports, sports_bottom_current, SPORTS_WRONG_BOTTOM))
    if dy_sports != SPORTS_DY or sports_bottom_current != SPORTS_WRONG_BOTTOM:
        failures.append(
            "Sports Grounds OLD-chain model (dy=%d, bottom=%d) no longer "
            "matches the historically measured pre-fix defect (dy=%d, "
            "bottom=%d)." % (dy_sports, sports_bottom_current, SPORTS_DY,
                              SPORTS_WRONG_BOTTOM))
    else:
        print("  [OLD chain still reproduces its own measured defect]  ok")

    # ---- 2: THE ROOT-CAUSE FIX - SubPlaceTopMb, mB used directly --------
    print()
    print("  === SubPlaceTopMb (mB direct) - what SHIPS now ===")
    print("  %-10s %6s %5s %6s %7s %8s %8s" %
          ("name", "cy", "cnt", "newH", "top", "bottom", "reported"))
    bottoms_by_cnt8 = {}
    centers = {}
    for name, cy, cnt, reported in CIVIC_TOOLS:
        eff_cnt = min(cnt, 8)
        newh = scaled_content_h(eff_cnt, F)
        top = sub_place_top_mb(newh, cy, MEASURED_MT, MEASURED_MB, F)
        bottom = top + newh
        center = top + newh // 2
        centers[name] = (cy, center)
        print("  %-10s %6d %5d %6d %7d %8d %8s"
              % (name, cy, cnt, newh, top, bottom, reported))
        if cnt >= 8:
            bottoms_by_cnt8[name] = bottom

    print()
    print("  identical-bottom check (every cnt>=8 Civic Tools button):")
    distinct_bottoms = set(bottoms_by_cnt8.values())
    print("    %s -> %s" % (bottoms_by_cnt8, distinct_bottoms))
    if len(distinct_bottoms) != 1:
        failures.append(
            "cnt>=8 Civic Tools buttons do NOT share one bottom under "
            "SubPlaceTopMb: %s. The 'identical bottom' law must fall out "
            "of the plain formula with no per-bar gate - if it does not, "
            "the root-cause claim is wrong." % bottoms_by_cnt8)
    else:
        print("    [all cnt>=8 buttons converge on ONE shared bottom, no "
              "gate needed]                                          ok")

    print()
    print("  own-button centering check (every cnt<8 Civic Tools button):")
    max_center_drift = 0
    for name, cy, cnt, reported in CIVIC_TOOLS:
        if cnt >= 8:
            continue
        b_cy, center = centers[name]
        drift = abs(center - b_cy)
        max_center_drift = max(max_center_drift, drift)
        print("    %-10s cy=%-4d center=%-4d drift=%-3d" % (name, b_cy, center, drift))
    if max_center_drift > 10:
        failures.append(
            "A cnt<8 button's container center drifted %dpx from its own "
            "cy under SubPlaceTopMb - expected a small (<=10px, integer "
            "rounding) drift, not a real positioning error."
            % max_center_drift)
    else:
        print("    [every cnt<8 button centers within %dpx of its own "
              "button]                                          ok"
              % max_center_drift)

    # ---- 3: negative control - the OLD per-button-broken numbers must NOT
    # equal the new formula's output, or this gate would not have caught
    # the original defect it was written to catch.
    print()
    old_broken_tops = {}
    for name, cy, cnt, reported in CIVIC_TOOLS:
        if cnt >= 8:
            continue
        eff_cnt = min(cnt, 8)
        newh = scaled_content_h(eff_cnt, F)
        old_top = sub_place_top(newh, cy, VIEW_H, F) - shift
        old_broken_tops[name] = old_top
    new_tops = {name: sub_place_top_mb(
        scaled_content_h(min(cnt, 8), F), cy, MEASURED_MT, MEASURED_MB, F)
        for name, cy, cnt, reported in CIVIC_TOOLS if cnt < 8}
    print("  negative control: %s" % {
        n: (old_broken_tops[n], new_tops[n]) for n in old_broken_tops})
    if old_broken_tops == new_tops:
        failures.append(
            "SubPlaceTopMb reproduces the OLD, reported-broken per-button "
            "formula exactly for every cnt<8 button - this gate would not "
            "have caught the original defect. Investigate why (likely mB "
            "or the margin logic did not actually change)."
        )
    else:
        print("  [new formula genuinely diverges from the OLD broken "
              "output for every cnt<8 button]                       ok")

    # ---- 4: f=1.0 sanity - THREE numbers on record BEFORE this fix -----
    # existed, from a completely different measurement/reasoning chain
    # (a live SUBPLACE census cross-check). If SubPlaceTopMb, at f=1,
    # does not reproduce them, either this file's transcription or the
    # historical record is wrong - find out which before trusting f=2.
    print()
    NAMED_UNCLAMPED_CASES = [
        # (name, cy, ch_1x, measured_native_top)
        ("Rewards (cnt=36, 8-row cap)", 895, 437, 674),
        ("Hospitals (cnt=3)",           697, 192, 598),
        ("Education (cnt=6)",           595, 339, 423),
    ]
    for name, cy, ch1x, expected_native_top in NAMED_UNCLAMPED_CASES:
        got = sub_place_top_mb(ch1x, cy, MEASURED_MT, MEASURED_MB, 1.0)
        ok = got == expected_native_top
        print("  %-28s cy=%-4d ch1x=%-4d SubPlaceTopMb(f=1)=%-4d "
              "(measured %d)  %s"
              % (name, cy, ch1x, got, expected_native_top,
                 "ok" if ok else "*** MISMATCH ***"))
        if not ok:
            failures.append(
                "%s: SubPlaceTopMb(f=1) gives native top %d, measured %d - "
                "either this file's transcription of the C++ or the "
                "historical record has drifted." % (name, got,
                                                      expected_native_top))

    # ---- 5: 1.5x / 3x sanity - no off-screen or absurd values ----------
    print()
    print("  1.5x / 3x spot check (Police, cnt=5):")
    for f in (1.5, 3.0):
        newh = scaled_content_h(5, f)
        top = sub_place_top_mb(newh, 397, MEASURED_MT, MEASURED_MB, f)
        bottom = top + newh
        print("    f=%.1f: newH=%d top=%d bottom=%d" % (f, newh, top, bottom))
        if top < 0 or bottom > MEASURED_MB + 50:
            failures.append(
                "Police at f=%.1f gives top=%d bottom=%d - outside a "
                "plausible on-screen range (mB=%d). The formula may not "
                "generalize past f=2 the way the fractional-tier law "
                "requires." % (f, top, bottom, MEASURED_MB))
    if not any("f=%.1f" % fv in str(failures) for fv in (1.5, 3.0)):
        print("  [1.5x/3x stay on-screen, no absurd values]            ok")

    print()
    if failures:
        print("FAIL: %d problem(s):" % len(failures))
        for f in failures:
            print("  - %s" % f)
        return 1
    print("ALL PASS (SubPlaceTopMb reproduces the shared-bottom law with no "
          "per-bar gate, centers every short button on its own cy, "
          "genuinely diverges from the old broken output, and matches "
          "three independently-recorded native measurements at f=1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
