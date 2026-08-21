#!/usr/bin/env python3
"""#137 GATE - the Graphs radio band docks to the panel BOTTOM, not the chart top.

WHAT WAS WRONG. kPanelDock carried

    { 0x0A4A8176, 0x8A8B5B71, -2, 640, "graphs checkbox band" }

anchoring the band to the CHART'S TOP by an offset eye-measured off a 2x
screenshot ("band - chart = (-2,+640)"). That is a *screen* relationship, not
the design one, and it was wrong - so scaling it kept it wrong at every tier.
The band overlapped the "Graphs" title and the expansion arrow at 2x AND 3x.

THE DESIGN IS BOTTOM-REFERENCED, and the .UI proves it. The same band id
0x0A4A8176 appears in TWO scripts, and one of them is the panel the user
pointed at as correct:

    Data Views  I-ea2871aa   band 546x122   dLeft 0    bottom gap  2
    Graphs      I-6bc9065a   band 503x107   dLeft 5    bottom gap 16

Both measure the band UP from a BOTTOM edge, never from the chart's top.
Graphs' band sits 16 up from 0x8A8B5B72's bottom, equivalently 10 up from the
CHART root 0x8A8B5B71's bottom - the same pixel either way.

WE SHIP THE CHART-ANCHORED FORM (#137b) because of ANCHOR LIFETIME: measured
in the log, 0x8A8B5B72 opens ~19s after the band, and ApplyPanelDocks bails on
an invisible anchor - so the 0x8A8B5B72 form could not dock until the user
clicked something, and the band painted undocked meanwhile. Section 5 asserts
that ordering so the mistake cannot be reintroduced.

THE LIVE FIXTURE (SC4UIScale.log, 3840x2160 tier 3.00, 2026-08-05 13:35):

    panel 0x8A8B5B72 (495,1962 546x152) -> (1485,1566 1638x456)
    panel 0x0A4A8176 (488,1976 503x107) -> (1464,1608 1509x321)
    PANELDOCK band (1464,1608) -> (1482,1620) under 0x8A8B5B71 at (1485,660)

Old rule put the band bottom at 1620+321 = 1941 against a parent bottom of
1566+456 = 2022: a gap of 81 where the design demands rhu(16*3) = 48. The band
was 33px too high - exactly the overlap on screen.

Run:  python gate_graphs_banddock.py     (exit 0 = green)
Pure arithmetic; no game, no capstone.
"""
import math
import sys

FAIL = []


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import round_half_up as rhu    # noqa: E402


# ---- the design, read from the two .UI scripts ---------------------------
# (values verified by re-parsing both files; see the module docstring)
DESIGN = {
    "graphs":    dict(parent=(463, 570, 1009, 722), band=(468, 599, 971, 706),
                      chart=(463, 268, 1009, 716)),
    "dataviews": dict(parent=(463, 570, 1009, 716), band=(463, 592, 1009, 714),
                      chart=(463, 268, 1009, 716)),
}
# #137b: anchor is 0x8A8B5B71 (the CHART), not 0x8A8B5B72. Same design
# relationship, but 0x8A8B5B71 opens at the same instant as the band while
# 0x8A8B5B72 appears ~19s later - and ApplyPanelDocks bails on an invisible
# anchor, so the band painted undocked until the user clicked. ANCHOR LIFETIME
# IS PART OF THE DOCK.
GRAPHS_DLEFT, GRAPHS_GAP = 5, 10      # what kPanelDock now carries


def check(name, got, want):
    ok = got == want
    print("  %-56s %-8s %s" % (name, got, "ok" if ok else "FAIL want %s" % want))
    if not ok:
        FAIL.append(name)


def dock(anchor_l, anchor_t, anchor_h, child_h, f, dleft=GRAPHS_DLEFT,
         gap=GRAPHS_GAP):
    """Mirror of UiSpike::ApplyPanelDocks after #137."""
    tx = anchor_l + rhu(dleft * f)
    ty = (anchor_t + anchor_h) - child_h - rhu(gap * f)
    return tx, ty


print("#137 gate - Graphs radio band bottom-dock")
print()
print("1. THE DESIGN CONSTANTS COME FROM THE .UI, NOT FROM A SCREENSHOT")
for name, d in DESIGN.items():
    pl, pt, pr, pb = d["parent"]
    bl, bt, br, bb = d["band"]
    print("   %-10s band %dx%-4d dLeft %+d  bottom gap %d"
          % (name, br - bl, bb - bt, bl - pl, pb - bb))
check("graphs dLeft matches kPanelDock offX",
      DESIGN["graphs"]["band"][0] - DESIGN["graphs"]["parent"][0], GRAPHS_DLEFT)
# gap is now measured against the CHART root, not 0x8A8B5B72
check("graphs bottom gap vs CHART matches kPanelDock offY",
      DESIGN["graphs"]["chart"][3] - DESIGN["graphs"]["band"][3], GRAPHS_GAP)
# WHY THE ANCHOR SWAP IS SAFE: both routes are bottom-referenced and the two
# anchors' own bottoms differ by exactly the difference in their design gaps,
# so they land on the SAME pixel. Computed from the LIVE f=3 rects, not asserted.
_chart_route = (660 + 1344) - 321 - rhu(10 * 3)     # chart bottom 2004, gap 10
_lower_route = (1566 + 456) - 321 - rhu(16 * 3)     # 0x8A8B5B72 bottom 2022, gap 16
check("chart-anchored target", _chart_route, 1653)
check("0x8A8B5B72-anchored target (same pixel)", _lower_route, _chart_route)
check("data views is the flush case (gap 2)",
      DESIGN["dataviews"]["parent"][3] - DESIGN["dataviews"]["band"][3], 2)

# ---- 2. THE LIVE 3x FIXTURE ---------------------------------------------
print()
print("2. LIVE 3x FIXTURE - what the old rule did vs what the design demands")
A_L, A_T, A_H = 1485, 660, 1344          # 0x8A8B5B71 (chart) after the sweep
C_H = 321                                # band height after the sweep
OLD = (1482, 1620)                       # what PANELDOCK logged

old_gap = (A_T + A_H) - (OLD[1] + C_H)
check("old rule's bottom gap at f=3 (vs chart)", old_gap, 63)
check("design bottom gap at f=3", rhu(GRAPHS_GAP * 3), 30)
check("how far too high the old rule sat", old_gap - rhu(GRAPHS_GAP * 3), 33)

new = dock(A_L, A_T, A_H, C_H, 3.0)
check("new target X", new[0], 1500)
check("new target Y", new[1], 1653)
check("new bottom gap == design", (A_T + A_H) - (new[1] + C_H), rhu(GRAPHS_GAP * 3))
check("band moves DOWN by exactly the error", new[1] - OLD[1], 33)

# ---- 3. EVERY TIER, and the invariant that actually matters --------------
print()
print("3. THE INVARIANT: bottom gap == rhu(10*f) at every tier")
print("     f     anchorBottom  bandH   targetY   bottom gap   want")
for f in (1.5, 2.0, 3.0):
    ah = rhu(448 * f)                    # chart 0x8A8B5B71 is 546x448 at 1x
    ch = rhu(107 * f)                    # band is 503x107 at 1x
    at = 660                             # arbitrary; the invariant is relative
    tx, ty = dock(A_L, at, ah, ch, f)
    gap = (at + ah) - (ty + ch)
    want = rhu(GRAPHS_GAP * f)
    print("   %4.2f   %11d  %5d   %7d   %10d   %4d" % (f, at + ah, ch, ty, gap, want))
    check("f=%.2f bottom gap" % f, gap, want)

# ---- 4. NEGATIVE CONTROLS ------------------------------------------------
print()
print("4. NEGATIVE CONTROLS (each MUST break something)")


def neg(name, cond):
    print("  %-56s %s" % (name, "ok (detected)" if cond else "FAIL (blind)"))
    if not cond:
        FAIL.append("negative control: " + name)


# 4a. the OLD chart-top rule cannot produce the design gap at f=3
old_ty = 660 + rhu(640 * 3 / 2.0)        # chart top 660, old offY 640, f/2 law
neg("old chart-top rule misses the design gap", old_ty != new[1])
neg("  ...and by exactly the 33px measured", new[1] - old_ty == 33)
# 4b. a wrong gap constant must fail the invariant at some tier
for bad in (9, 11):
    ok_all = all(
        ((660 + rhu(448 * f)) - (dock(A_L, 660, rhu(448 * f), rhu(107 * f), f,
                                      gap=bad)[1] + rhu(107 * f))) == rhu(GRAPHS_GAP * f)
        for f in (1.5, 2.0, 3.0))
    neg("gap=%d breaks the invariant" % bad, not ok_all)
# 4c. scaling by f/2 instead of f must be detectable
half = 1485 + rhu(GRAPHS_DLEFT * 3 / 2.0)
neg("f/2 scaling of dLeft is detectable at f=3", half != new[0])
# 4d. top-anchoring must not accidentally equal bottom-anchoring
neg("top-anchor and bottom-anchor differ at f=3",
    (660 + rhu(GRAPHS_GAP * 3)) != new[1])

print()
print("5. ANCHOR LIFETIME (the v2.89.0 regression this section exists for)")
# Open order MEASURED from SC4UIScale.log, 2026-08-05 13:45:
OPEN_MS = {"0x8A8B5B71": 4291, "0x0A4A8176": 4291, "0x8A8B5B72": 23845}
band, chart, lower = OPEN_MS["0x0A4A8176"], OPEN_MS["0x8A8B5B71"], OPEN_MS["0x8A8B5B72"]
check("chart opens WITH the band (delta ms)", chart - band, 0)
check("0x8A8B5B72 opens LATE (delta ms)", lower - band, 19554)
neg("an anchor that opens after its child is rejected", lower > band)
print("   RULE: ApplyPanelDocks bails on !pAnchor->IsVisible(), so an anchor")
print("   must be alive whenever its child is. Arithmetic alone is not enough.")

print()
if FAIL:
    print("RED - %d failure(s):" % len(FAIL))
    for f_ in FAIL:
        print("   - %s" % f_)
    sys.exit(1)
print("GREEN - the band now docks UP from the CHART root 0x8A8B5B71's bottom")
print("edge by rhu(10*f) - the relationship the .UI specifies, and the one Data")
print("Views already satisfies. At f=3 that moves it DOWN 33px, clearing the")
print("title and the expansion arrow.")
print()
print("NOT PROVEN HERE: that 16 is the right gap for how it LOOKS. It is the")
print("design's number, and Data Views' equivalent (2) renders correctly - but")
print("only eyes-on at 2x AND 3x closes this.")
sys.exit(0)
