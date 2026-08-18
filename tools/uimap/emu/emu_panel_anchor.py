r"""
emu_panel_anchor.py - OFFLINE MODEL OF *OUR* PANEL ANCHOR (task #101).

Every other emulator under tools\uimap\emu\ models SIMCITY 4's code. This one
models OURS: the per-axis anchor block inside UiSpike::ScalePanelRoot
(src\UiSpike.cpp, anchor text "Scaled-gap anchoring: uniform scaling about the
nearer frame"). It exists because #101 - the 1.5x city dashboard being
unusable - was a defect in that block, and nothing offline could have caught
it: the whole tools\uimap\emu\ suite models the game, not the mod.

WHAT IS REAL AND WHAT IS MODELLED (be honest about this line)
------------------------------------------------------------
REAL (transcribed line for line from src\UiSpike.cpp, and CHECKED against it):
    the edge-derived newW/newH, the double-scale guard, cMinX/cMinY, the
    three-way per-axis branch, and the four per-edge conditional clamps.
MODELLED / NOT COVERED:
    EARLYDOCK (0x0987B48F takes a different path on some boots), the
    kCityDialogIds re-centre at "nl = baseL + w / 2 - newW / 2", the
    AlreadyScaled / carry-over bookkeeping, and anything that decides WHICH
    windows reach ScalePanelRoot. This model answers "given a design rect and
    a frame, where does the panel land" and nothing else.

THE POSITIVE CONTROL - state it, do not assume it
-------------------------------------------------
The emitter this replays is uncapped and unbanded:
    Logger::Get().WriteLine(LogLevel::Debug, "UiSpike: panel 0x%08X (%d,%d
    %dx%d) -> (%d,%d %dx%d)%s", ...)
so a panel that WAS scaled is always in the log. `--check` therefore compares
against a complete population, and a 0-mismatch result is a real pass, not a
null.

As of 2026-08-03 it reproduces 39/39 panels in the 2400x1600 f=2.0 capture and
39/39 in the 1400x1050 f=1.5 capture, with zero mismatches, under `--law cur`.

USAGE
-----
  # regression gate: the model must still match every capture we hold
  python tools\uimap\emu\emu_panel_anchor.py --check ^
      _tests\captures\2026-07-31-task89-ours-baseline-SC4UIScale.log 2400 1600 2.0
  python tools\uimap\emu\emu_panel_anchor.py --check ^
      _tests\captures\2026-08-03-TIER15X-dashboard-broken-SC4UIScale.log 1400 1050 1.5

  # adjudicate a candidate fix BEFORE building it: what moves at each tier?
  python tools\uimap\emu\emu_panel_anchor.py --blast ^
      _tests\captures\2026-07-31-task89-ours-baseline-SC4UIScale.log 2400 1600 2.0 --law fam
  # ^ MUST print "0 panels move" for the 2400x1600 f=2.0 capture. That capture
  #   is the user-confirmed shipping tier; a candidate that moves ANY panel
  #   there is rejected without a build.

  # the dashboard occlusion adjudicator, at any frame, with no game
  python tools\uimap\emu\emu_panel_anchor.py --dash 1920 1080 1.5 --law fam
"""

import argparse
import math
import re
import sys

# ---------------------------------------------------------------- primitives


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to carry
# its own copy; #162 changed ScaleRound in the DLL and every private copy in
# this folder had to be found by hand. `scale_rules.py --drift` hunts any that
# come back.
#
# #162: this was llround (half AWAY from zero) to match ScaleRound, and
# ScaleRound itself was wrong - a span straddling the origin got both edges
# pushed outward and came out a pixel longer than the art. The whole tier
# pipeline (Upscale2x dimensions, the .UI builders' scale_len) is half-up, so
# half-up is the rule. Identical at f=2 and f=3, where v*f is exact.
from scale_rules import scale_round             # noqa: E402


SR = scale_round

# ------------------------------------------------------- the family constants
#
# LEADER = the composite mayor HUD 0xE9889775. Its design rect is the ONLY
# pair of constants the family law uses, and both come from ONE window, so
# `python tools\sdk\lookup.py 0xE9889775` verifies the whole table:
#   .UI root  880x180   (T-00000000_G-96a006b0_I-2bc90671.ui, the LIVE variant)
#   design l  139       (code-placed; MEASURED identical in the 1400-wide and
#                        the 2400-wide capture, i.e. frame-independent)
FAM_LEADER_L = 139
FAM_LEADER_R = 1019  # 139 + 880

# The city bottom-HUD cluster: every root the game places at a FRAME-INDEPENDENT
# design x on the dashboard row. Membership is MEASURED - each id below has the
# same design l in the 1400x1050 capture and the 2400x1600 capture.
# (0xABC619D2 appears only in the 1.5x capture; flagged, not assumed.)
FAMILY = {
    0xE9889775: (139, "composite status HUD  <-- LEADER"),
    0x698894D3: (139, "My Sims outer root"),
    0xCA1F1D9C: (149, "My Sims content panel"),
    0xEA1F1E4E: (153, "find-sim overlay"),
    0xEA1F1E4D: (195, "Sim detail / news strip"),
    0x6A15C767: (209, "Advisors console strip"),
    0xAA15EF06: (209, "advisor briefing (compact)"),
    0xAA3AC000: (210, "budget compact bar"),
    0xC98F49F1: (232, "city panel variant"),
    0xCA2AEDC0: (232, "news ticker strip"),
    0xAA1F1EC5: (263, "My Sims dialog"),
    0xABBAA2D3: (321, "Sim actions strip"),
    0x6A61E29F: (321, "Sim profile strip"),
    0x2A1D96B1: (482, "advisor briefing (expanded)"),
    0xAA3AC001: (483, "budget expanded"),
    0xABC619D2: (489, "Building Style Control   [no 2x observation]"),
    0xAA32BCE6: (494, "Data Views panel"),
    0x0A4A8176: (494, "graphs/data root C"),
    0x8A8B5B71: (495, "graphs/data root A"),
    0x8A8B5B72: (495, "graphs/data MIDDLE root"),
    0x6A64E3C0: (501, "City Opinion Polls"),
}

# Children of the composite, design-relative, from the LIVE declaring script
# T-00000000_G-96a006b0_I-2bc90671.ui.  MEASURED to be the live variant, not
# assumed: at f=1.5 with the composite at x=80 the log's DPROBE reports
# 0xAA9211B3 abs(464,793) 63x177 and 0x09D27EB0 abs(475,853) 12x107, and this
# table + SR() reproduces both exactly. The other 880-wide variant
# (I-898897de, RCI at rel 278) does NOT.
COMPOSITE_CHILDREN = {
    0xAA9211B3: (256, 16, 42, 118, "RCI meter button"),
    0x09D27EB0: (263, 56, 8, 71, "RCI column R"),
    0x29D27EC0: (273, 56, 8, 71, "RCI column C"),
    0x49D27ED0: (283, 56, 8, 71, "RCI column I"),
    0xABC54125: (299, 27, 34, 35, "button: Building Style"),
    0x49EDF9B7: (299, 62, 34, 35, "button"),
    0x00000041: (299, 97, 34, 35, "button"),
    0x99887755: (326, 27, 34, 35, "button"),
    0x15200002: (326, 62, 34, 35, "button"),
    0x15200003: (326, 97, 34, 35, "button"),
}

# ------------------------------------------------------------------ the laws


def anchor(l, t, w, h, frame_w, frame_h, f, law="cur"):
    """Return ((x,y,w,h), branch_tag) or (None,'SKIP') for the guard."""
    new_w = SR(l + w, f) - SR(l, f)
    new_h = SR(t + h, f) - SR(t, f)
    if new_w > frame_w or new_h > frame_h:
        return None, "SKIP"

    gap_l, gap_r = l, frame_w - (l + w)
    gap_t, gap_b = t, frame_h - (t + h)
    c_min_x, c_min_y = frame_w // 4, frame_h // 4

    # --- X ---------------------------------------------------------------
    if law == "cur":
        if gap_l > c_min_x and gap_r > c_min_x:
            new_x, bx = l + w // 2 - new_w // 2, "C"
        elif gap_l <= gap_r:
            new_x, bx = SR(gap_l, f), "L"
        else:
            new_x, bx = frame_w - SR(gap_r, f) - new_w, "R"
    elif law == "fam":
        # Candidate #101: the family co-anchors off the LEADER, so overlapping
        # siblings transform identically - which is exactly what the shipping
        # comment already promises and does not deliver.
        origin = SR(FAM_LEADER_L, f)
        span = SR(FAM_LEADER_R, f) - SR(FAM_LEADER_L, f)
        if origin + span > frame_w:
            origin = frame_w - span
        if origin < 0:
            origin = 0
        new_x = origin + SR(l, f) - SR(FAM_LEADER_L, f)
        bx = "F"
        # The family's X fit was already decided by the origin clamp above.
        # Re-clamping each member INDIVIDUALLY is what shears them apart, so
        # the per-edge X clamps below are suppressed for family members. The
        # price is stated, not hidden: at a frame narrower than SR(1049,f)
        # the widest members hang off the right edge (30 px for the polls
        # panel, 45 px for the advisors strip, at 1400x1050 f=1.5).
        gap_l, gap_r = -1, -1
    else:
        raise SystemExit("unknown --law %r" % law)

    # --- Y (unchanged by every #101 candidate; CENTER is never taken in
    #        either capture - the tallies are EDGE-B 28/29, EDGE-T 11/10) ---
    if gap_t > c_min_y and gap_b > c_min_y:
        new_y, by = t + h // 2 - new_h // 2, "C"
    elif gap_t <= gap_b:
        new_y, by = SR(gap_t, f), "T"
    else:
        new_y, by = frame_h - SR(gap_b, f) - new_h, "B"

    # --- per-edge conditional clamps (a NEGATIVE design gap is an intentional
    #     overhang and is never clamped) ------------------------------------
    if gap_r >= 0 and new_x + new_w > frame_w:
        new_x, bx = frame_w - new_w, bx + "!"
    if gap_l >= 0 and new_x < 0:
        new_x, bx = 0, bx + "0"
    if gap_b >= 0 and new_y + new_h > frame_h:
        new_y, by = frame_h - new_h, by + "!"
    if gap_t >= 0 and new_y < 0:
        new_y, by = 0, by + "0"

    return (new_x, new_y, new_w, new_h), bx + by


def place(win_id, l, t, w, h, frame_w, frame_h, f, law):
    """Apply `law` only to family members; everything else keeps the shipping law."""
    if law == "fam" and win_id not in FAMILY:
        return anchor(l, t, w, h, frame_w, frame_h, f, "cur")
    return anchor(l, t, w, h, frame_w, frame_h, f, law)


# ------------------------------------------------------------------- capture

PANEL_RE = re.compile(
    r"panel 0x([0-9A-Fa-f]{8}) \((-?\d+),(-?\d+) (\d+)x(\d+)\)"
    r" -> \((-?\d+),(-?\d+) (\d+)x(\d+)\)")


def parse_capture(path):
    """id -> (design(l,t,w,h), logged(x,y,w,h)). Arrow form only: the SKIPPED
    guard line also starts 'panel 0x...' and must not be counted as present."""
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = PANEL_RE.search(line)
            if m:
                g = [int(x) for x in m.groups()[1:]]
                out[int(m.group(1), 16)] = (tuple(g[:4]), tuple(g[4:]))
    return out


# --------------------------------------------------------------------- modes


def mode_check(path, W, H, f, law):
    caps = parse_capture(path)
    bad = 0
    for wid, (design, logged) in sorted(caps.items()):
        pred, tag = place(wid, *design, W, H, f, law)
        if pred != logged:
            bad += 1
            print("  MISMATCH 0x%08X design%s logged%s predicted%s [%s]"
                  % (wid, design, logged, pred, tag))
    print("%s: %d panels, %d match, %d MISMATCH   (%dx%d f=%s law=%s)"
          % (path, len(caps), len(caps) - bad, bad, W, H, f, law))
    return 1 if bad else 0


def mode_blast(path, W, H, f, law):
    caps = parse_capture(path)
    moved = 0
    for wid, (design, logged) in sorted(caps.items()):
        base, _ = place(wid, *design, W, H, f, "cur")
        cand, tag = place(wid, *design, W, H, f, law)
        if base != cand:
            moved += 1
            name = FAMILY.get(wid, (None, ""))[1]
            print("  MOVES 0x%08X %-34s %s -> %s [%s]"
                  % (wid, name, base, cand, tag))
    print("%d panels move of %d   (%dx%d f=%s, law %s vs cur)"
          % (moved, len(caps), W, H, f, law))
    return moved


def mode_dash(W, H, f, law):
    """The dashboard occlusion adjudicator: does the polls panel cover the RCI
    meter or the button cluster? This is the #101 acceptance test, offline.

    X ONLY. The design `t` fed in below is the 1050-tall one from the 1.5x
    capture; the game bottom-anchors the dashboard, so at another frame height
    the real design `t` differs and the Y tag printed here is meaningless.
    #101 is an X defect, the Y branch tally is EDGE-B/EDGE-T in both captures
    with CENTER never taken, and no candidate touches Y - so X alone decides."""
    comp, ctag = place(0xE9889775, 139, 863, 880, 180, W, H, f, law)
    polls, ptag = place(0x6A64E3C0, 501, 862, 538, 135, W, H, f, law)
    print("frame %dx%d  f=%s  law=%s" % (W, H, f, law))
    print("  composite 0xE9889775 x %d..%d  [%s]" % (comp[0], comp[0] + comp[2], ctag))
    print("  polls     0x6A64E3C0 x %d..%d  [%s]" % (polls[0], polls[0] + polls[2], ptag))
    worst = None
    for cid, (rl, rt, rw, rh, name) in sorted(COMPOSITE_CHILDREN.items(),
                                              key=lambda kv: kv[1][0]):
        x0 = comp[0] + SR(rl, f)
        x1 = comp[0] + SR(rl + rw, f)
        clear = polls[0] - x1
        worst = clear if worst is None else min(worst, clear)
        print("    0x%08X %-24s x %4d..%-4d   clearance to polls %+5d%s"
              % (cid, name, x0, x1, clear, "   <-- OCCLUDED" if clear < 0 else ""))
    ideal = round(2 * f)  # design gap between the button column (ends 499) and polls (501)
    print("  WORST clearance %+d px (design gap 2 -> want ~%+d).  %s"
          % (worst, ideal, "PASS" if worst >= 0 else "FAIL - dashboard unusable"))
    off = polls[0] + polls[2] - W
    if off > 0:
        print("  NOTE: polls right edge hangs %d px off the frame (1.5x of the"
              " design right edge 1039 = %d > %d)." % (off, SR(1039, f), W))
    return 0 if worst >= 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", nargs=4, metavar=("LOG", "W", "H", "F"))
    ap.add_argument("--blast", nargs=4, metavar=("LOG", "W", "H", "F"))
    ap.add_argument("--dash", nargs=3, metavar=("W", "H", "F"))
    ap.add_argument("--law", default="cur", choices=["cur", "fam"])
    a = ap.parse_args()
    if a.check:
        return mode_check(a.check[0], int(a.check[1]), int(a.check[2]),
                          float(a.check[3]), a.law)
    if a.blast:
        return mode_blast(a.blast[0], int(a.blast[1]), int(a.blast[2]),
                          float(a.blast[3]), a.law)
    if a.dash:
        return mode_dash(int(a.dash[0]), int(a.dash[1]), float(a.dash[2]), a.law)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
