#!/usr/bin/env python3
r"""GATE #149 - the ICONFIT blit-rewriting PREDICATE. Offline, pure arithmetic.

Adjudicates - WITHOUT launching the game and WITHOUT opening a pixel - whether a
proposed src-rect rewrite fires on the blits it must fire on and, far more
important, NEVER on the ones it must not. The first attempt shipped a VISIBLE
REGRESSION (a white line through UI art) because its predicate was satisfied by
an ordinary FULL-BITMAP 1:1 blit. This file exists so that class of miss is
machine-checked before a build, not after a user reports it.

  python gate_iconfit_rule.py             # the corpus; exit 0 = green
  python gate_iconfit_rule.py --selftest  # + MANDATORY negative controls
  python gate_iconfit_rule.py --emit      # the C++-ready predicate
  python gate_iconfit_rule.py -v          # per-fixture condition traces

THE ENGINE RULE (measured, not inferred). A menu item icon is a FOUR-STATE
horizontal strip. GZWinBtn picks its cell as `stateW = imageWidth / 4` -
proportional, no pixel constants (#49, `_tests\REGRESSION.md:1387`;
`SC4-UI-ENGINE.md:305`). The state count can NEVER be derived from geometry:
32% of the 837 real icons are 356x58, and 356/58 = 6.14.

THE BLIT (MEASURED from the DSTRIP probe, `UiSpike.cpp:2412`, across the shipped
capture set - this is what makes this gate different from the shipped guess):

    DSTRIP src 88x88  ( 88,0,176, 88) dst 88x88   srcTex=352x88   <- art at tier
    DSTRIP src 88x88  ( 88,0,176, 88) dst 88x88   srcTex=176x44   <- THE DEFECT
    DSTRIP src 132x132(396,0,528,132) dst 132x132 srcTex=176x44   <- THE DEFECT

  * the blit is 1:1: srcW == dstW AND srcH == dstH, always (25/25 shapes);
  * src.top == 0 and src.left == state * dstW - the engine offsets by the
    DESTINATION cell width, not by stateW;
  * so 1x art in an f-scaled cell over-reads on BOTH axes by exactly f.

THREE FACTS THE SHIPPED PREDICATE GOT WRONG, each provable from those lines:

  1. `srcH == bmpH` is the condition that SELECTS full-bitmap 1:1 blits (the two
     real regressions have srcH == bmpH) and REJECTS every real over-read
     (measured srcH = 88 with bmpH = 44). The shipped predicate could therefore
     only ever fire on the wrong thing. It is not merely unsafe - it is inert on
     its own target class, and this gate proves it (`V1_SHIPPED` fires on 0 of
     the MEASURED must-fire fixtures).
  2. `srcW % stateW == 0` is true only for INTEGER ratios, so the whole 1.5x
     tier is structurally unreachable by the V1 family. Machine-checked below.
  3. The rewrite `src.right = src.left + stateW` is wrong even where it matches:
     src.left is in CELL units, so the state index is `src.left / srcW`, and
     src.bottom is the CELL height, not bmpH. All four coordinates must move.

THE FIX THE BRIEF ASKS FOR - `srcW != bmpW` - is necessary and it does exclude
both real regressions, but it is NOT sufficient: a plain half-bitmap crop drawn
1:1 (bmp 24x6, src 12x6, dst 12x6 - an edge/9-slice shape) satisfies every V1
condition plus the fix. What excludes that, with no pixel constant and no tier
named, is UNIFORMITY: an over-read is the same over-read on both axes,
`srcW/stateW == srcH/bmpH`. That is condition C9 in V2 below.

NEGATIVE CONTROLS ARE MANDATORY. A gate that cannot fail proves nothing. See
`--selftest`: it reverts `srcW != bmpW` and asserts the gate then FAILS on the
two real full-bitmap firings, and it ablates every V2 condition one at a time
and prints which fixtures each one is load-bearing for.

STATUS BUCKETS ARE NEVER BLURRED: PASS / FAIL / SKIP / UNDECIDED, counted and
printed separately. A SKIP is not a pass and an UNDECIDED is not a pass.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CAPTURES = os.path.join(ROOT, "_tests", "captures")
CENSUS_DIRS = [
    os.path.join(ROOT, "tools", "itemicons", "nam-1x"),
    os.path.join(ROOT, "tools", "itemicons", "_work", "submenus-1x"),
    os.path.join(ROOT, "tools", "itemicons", "_work", "plugins-1x"),
    os.path.join(ROOT, "tools", "itemicons", "_work", "pack-321"),
]
# The recorded census. Verified against disk at run time (see census()); a
# disagreement is a FAILURE, not a silent update - the fixture corpus must not
# drift away from the art it claims to model.
CENSUS_EXPECT = {(352, 88): 321, (356, 58): 270, (176, 44): 246}

VERBOSE = False
fails = []
undecided = []
skips = []


def check(cond, msg):
    print(("   ok   " if cond else "   FAIL ") + msg)
    if not cond:
        fails.append(msg)
    return bool(cond)


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import round_half_up as rhu    # noqa: E402


# ---------------------------------------------------------------------------
# THE PREDICATES.  Each returns (fired, newsrc_or_None, trace) where trace is
# an ordered list of (condition_name, bool) so any verdict can be explained and
# any single condition can be ablated by name.
# ---------------------------------------------------------------------------

def _dims(bmp, src, dst):
    bmpW, bmpH = bmp
    sl, st, sr, sb = src
    dl, dt, dr, db = dst
    return dict(bmpW=bmpW, bmpH=bmpH, sl=sl, st=st,
                srcW=sr - sl, srcH=sb - st, dstW=dr - dl, dstH=db - dt,
                stateW=(bmpW // 4) if bmpW > 0 else 0)


def _run(conds, ctx, skip=None):
    """SHORT-CIRCUITS at the first false, exactly like the C++ `&&` chain it
    models. A later condition may divide by an earlier one's operand (bmpW/4),
    so evaluating past a false is not merely wasteful - it faults."""
    trace = []
    for name, fn in conds:
        v = True if (skip and name in skip) else bool(fn(ctx))
        trace.append((name, v))
        if not v:
            trace += [(n, None) for n, _f in conds[len(trace):]]
            return False, trace
    return True, trace


# --- V1_SHIPPED: exactly what src\UiSpike.cpp:1817-1843 ships today ---------
V1_CONDS = [
    ("A-sane", lambda c: c["bmpW"] > 0 and c["bmpH"] > 0 and c["bmpW"] <= 4096
     and c["bmpH"] <= 4096 and c["srcW"] > 0 and c["srcH"] > 0
     and c["dstW"] > 0 and c["dstH"] > 0),
    ("B-bmpW%4", lambda c: (c["bmpW"] % 4) == 0),
    ("C-stateW>0", lambda c: c["stateW"] > 0),
    ("D-srcW>stateW", lambda c: c["srcW"] > c["stateW"]),
    ("E-srcW%stateW", lambda c: (c["srcW"] % c["stateW"]) == 0),
    ("F-srcH==bmpH", lambda c: c["srcH"] == c["bmpH"]),
    ("G-dstW==srcW", lambda c: c["dstW"] == c["srcW"]),
]
# --- V1_FIXED: V1 plus the single condition the brief names -----------------
V1F_CONDS = V1_CONDS + [("H-srcW!=bmpW", lambda c: c["srcW"] != c["bmpW"])]


def v1(bmp, src, dst, skip=None, conds=None):
    c = _dims(bmp, src, dst)
    ok, trace = _run(conds or V1_CONDS, c, skip)
    if not ok:
        return False, None, trace
    # the shipped rewrite: right edge only.
    return True, (src[0], src[1], src[0] + c["stateW"], src[3]), trace


# --- V2: the measured model -------------------------------------------------
# Every condition is arithmetic on the four operands. No tier is named, no
# pixel constant appears, and nothing is derived from the art's aspect.
V2_CONDS = [
    # the upper bounds are not decoration: C10 multiplies two of these operands
    # and an unbounded srcH would overflow a 32-bit int in the C++ before any
    # condition could reject it.
    ("C1-sane", lambda c: c["bmpW"] > 0 and c["bmpH"] > 0 and c["bmpW"] <= 4096
     and c["bmpH"] <= 4096 and c["srcW"] > 0 and c["srcH"] > 0
     and c["dstW"] > 0 and c["dstH"] > 0
     and c["srcW"] <= 16384 and c["srcH"] <= 16384
     and c["sl"] >= 0 and c["st"] >= 0),
    ("C2-bmpW%4", lambda c: (c["bmpW"] % 4) == 0),
    ("C3-stateW>0", lambda c: c["stateW"] > 0),
    # the blit on this path is 1:1 - MEASURED, 25/25 DSTRIP shapes. A blit that
    # already stretches is not the defect and must never be touched.
    ("C4-oneToOne", lambda c: c["srcW"] == c["dstW"] and c["srcH"] == c["dstH"]),
    ("C5-topAligned", lambda c: c["st"] == 0),
    # horizontal over-read: the cell is wider than a state.
    ("C6-srcW>stateW", lambda c: c["srcW"] > c["stateW"]),
    # vertical over-read: a state strip is FULL HEIGHT, so reading past bmpH is
    # only possible when the cell was scaled and the art was not.
    ("C7-srcH>bmpH", lambda c: c["srcH"] > c["bmpH"]),
    # THE FIX the brief names, in its strongest form. srcW == bmpW is the ratio
    # 4 case = "draw the whole bitmap", which is what an ordinary image blit
    # looks like; srcW > bmpW is past the end of a strip in cell units.
    ("C8-srcW<bmpW", lambda c: c["srcW"] < c["bmpW"]),
    # the read starts on a CELL boundary and names a state in 0..3. src.left is
    # in cell units (MEASURED: 88,264 at cell 88; 132,264,396 at cell 132).
    ("C9-cellAligned", lambda c: c["srcW"] > 0 and (c["sl"] % c["srcW"]) == 0
     and 0 <= c["sl"] // c["srcW"] <= 3),
    # UNIFORMITY - the condition the shipped predicate never had. The over-read
    # must be the SAME over-read on both axes: srcW/stateW == srcH/bmpH.
    # Cross-multiplied to stay in integers; the tolerance is derived from the
    # operands (never a pixel constant) because at f=1.5 the two axes round
    # independently (356x58 -> cell 134x87: 134/89 = 1.506, 87/58 = 1.500).
    ("C10-uniform", lambda c: abs(c["srcW"] * c["bmpH"] - c["srcH"] * c["stateW"])
     <= (c["stateW"] + c["bmpH"])),
]


def v2(bmp, src, dst, skip=None):
    c = _dims(bmp, src, dst)
    ok, trace = _run(V2_CONDS, c, skip)
    if not ok:
        return False, None, trace
    state = c["sl"] // c["srcW"]
    new = (state * c["stateW"], 0, (state + 1) * c["stateW"], c["bmpH"])
    return True, new, trace


PREDICATES = [
    ("V1_SHIPPED", lambda b, s, d, k=None: v1(b, s, d, k, V1_CONDS)),
    ("V1_FIXED", lambda b, s, d, k=None: v1(b, s, d, k, V1F_CONDS)),
    ("V2", v2),
]


# ---------------------------------------------------------------------------
# THE FIXTURE CORPUS
#   MEASURED - mined back out of the shipped capture logs at run time
#   DERIVED  - built by the measured blit model from the icon census
#   ASSUMED  - shape is real, one operand is attributed by co-occurrence
# ---------------------------------------------------------------------------

def cell(state, cw, ch):
    """The measured blit: src = (state*cellW, 0, +cellW, cellH), dst 1:1."""
    return (state * cw, 0, state * cw + cw, ch), (0, 0, cw, ch)


def fixtures():
    F = []

    def add(name, bmp, src, dst, verdict, origin, note=""):
        F.append(dict(name=name, bmp=bmp, src=src, dst=dst,
                      verdict=verdict, origin=origin, note=note))

    # ---- MUST FIRE, MEASURED (DSTRIP, srcTex=176x44 = uncovered 1x art) ----
    for st, cw in ((1, 88), (3, 88)):
        s, d = cell(st, cw, cw)
        add("M/2x 176x44 state%d cell%d" % (st, cw), (176, 44), s, d,
            "FIRE", "MEASURED", "DSTRIP, 2x tier")
    for st in (1, 2, 3):
        s, d = cell(st, 132, 132)
        add("M/3x 176x44 state%d cell132" % st, (176, 44), s, d,
            "FIRE", "MEASURED", "DSTRIP, 3x tier")

    # ---- MUST FIRE, DERIVED from the census x the measured blit model ------
    # 1x cell = (stateW, bmpH); at tier f the cell is RoundHalfUp of each axis.
    # The census has three dims but only TWO distinct 1x bases: 352x88 IS the
    # 2x package of the stock 176x44, while NAM ships 356x58 as its own 1x.
    for base in ((176, 44), (356, 58)):
        b1w, b1h = base
        sw1, sh1 = b1w // 4, b1h
        for f in (1.5, 2.0, 3.0):
            cw, ch = rhu(sw1 * f), rhu(sh1 * f)
            for st in (0, 3):
                s, d = cell(st, cw, ch)
                add("D/%gx %dx%d state%d cell%dx%d" % (f, b1w, b1h, st, cw, ch),
                    base, s, d, "FIRE", "DERIVED",
                    "1x art in an f=%g cell" % f)
            if (b1w, b1h) == (356, 58):
                # the OTHER rounding of 89*1.5 - the predicate must not depend
                # on which way the cell width rounded.
                cw2 = int(sw1 * f)
                if cw2 != cw:
                    s, d = cell(1, cw2, ch)
                    add("D/%gx 356x58 state1 cell%dx%d (floor)" % (f, cw2, ch),
                        base, s, d, "FIRE", "DERIVED", "alternate rounding")

    # ---- MUST NOT FIRE: the two REAL firings that shipped the regression ----
    # src.left is DERIVED, not assumed: srcW == bmpW and the read is in bounds,
    # so left can only be 0.
    add("R/full-bitmap 300x120", (300, 120), (0, 0, 300, 120), (0, 0, 300, 120),
        "NOFIRE", "MEASURED", "ICONFIT log 13:01:17.854 - shipped regression")
    add("R/full-bitmap 152x38", (152, 38), (0, 0, 152, 38), (0, 0, 152, 38),
        "NOFIRE", "MEASURED", "ICONFIT log 13:01:39.319 - shipped regression")

    # ---- MUST NOT FIRE: art already at the tier (MEASURED, DSTRIP) ---------
    for (tex, cw) in (((352, 88), 88), ((528, 132), 132), ((264, 66), 66)):
        for st in (0, 1, 3):
            s, d = cell(st, cw, cw)
            add("N/at-tier %dx%d state%d" % (tex[0], tex[1], st), tex, s, d,
                "NOFIRE", "MEASURED", "srcW == stateW, nothing to do")
    # the CellUnit-snapped tier art seen at 1.5x: the cell is SMALLER than the
    # state (under-read). Must be left alone - a rewrite would crop it further.
    for tex in ((264, 68), (272, 68)):
        s, d = cell(1, 66, 66)
        add("N/snapped %dx%d cell66" % tex, tex, s, d, "NOFIRE", "MEASURED",
            "1.5x snapped art, under-read")

    # ---- MUST NOT FIRE: src already exactly one state ----------------------
    add("N/one-state 1:1", (176, 44), (44, 0, 88, 44), (0, 0, 44, 44),
        "NOFIRE", "DERIVED", "1x art, 1x cell - the f=1 reduction")
    add("N/one-state already-stretching", (176, 44), (44, 0, 88, 44),
        (0, 0, 88, 88), "NOFIRE", "DERIVED", "the CURED shape; must be idempotent")

    # ---- MUST NOT FIRE: 9-slice / edge-style thin strips -------------------
    add("N/edge 24x6 whole", (24, 6), (0, 0, 24, 6), (0, 0, 24, 6),
        "NOFIRE", "MEASURED", "real sheet T-856ddbac_G-46a006b0_I-14416241")
    add("N/edge 24x6 half-read", (24, 6), (0, 0, 12, 6), (0, 0, 12, 6),
        "NOFIRE", "DERIVED",
        "THE COUNTEREXAMPLE the brief's minimal fix does NOT exclude")
    add("N/edge 24x6 quarter+stretch", (24, 6), (0, 0, 12, 6), (0, 0, 24, 6),
        "NOFIRE", "DERIVED", "already stretching")
    add("N/nineslice third", (96, 96), (0, 0, 32, 96), (0, 0, 32, 96),
        "NOFIRE", "DERIVED", "width/3 slice of a square sheet")
    add("N/nineslice edge stretched", (96, 96), (32, 0, 64, 96), (0, 0, 200, 96),
        "NOFIRE", "DERIVED", "edges stretch; not a 1:1 blit")

    # ---- MUST NOT FIRE: square blits and dst != src ------------------------
    add("N/square 1:1", (64, 64), (0, 0, 64, 64), (0, 0, 64, 64),
        "NOFIRE", "DERIVED", "plain image draw")
    add("N/square half 1:1", (64, 64), (0, 0, 32, 64), (0, 0, 32, 64),
        "NOFIRE", "DERIVED", "half of a square sheet, 1:1")
    add("N/dst>src", (176, 44), (0, 0, 88, 44), (0, 0, 176, 88),
        "NOFIRE", "DERIVED", "dst != src - the engine is already stretching")
    add("N/dst<src", (176, 44), (0, 0, 88, 44), (0, 0, 44, 22),
        "NOFIRE", "DERIVED", "dst != src - shrinking")

    # ---- MUST NOT FIRE: atlas element draws seen in the same session -------
    # ASSUMED: the bitmap is attributed by co-occurrence in the log frame, not
    # by pointer identity. Held for a SWEEP of plausible bitmaps so the verdict
    # does not depend on the attribution.
    for bw, bh in ((300, 120), (344, 128), (410, 92)):
        for (sw, sh) in ((18, 18), (18, 16), (10, 2)):
            add("N/atlas %dx%d src %dx%d" % (bw, bh, sw, sh), (bw, bh),
                (252, 18, 252 + sw, 18 + sh), (252, 18, 252 + sw, 18 + sh),
                "NOFIRE", "ASSUMED", "DCBUF element draw, same session")

    # ---- MUST NOT FIRE: odd / hostile shapes -------------------------------
    add("N/bmpW not div4", (177, 44), (0, 0, 88, 88), (0, 0, 88, 88),
        "NOFIRE", "DERIVED", "not a 4-state strip")
    add("N/zero src", (176, 44), (0, 0, 0, 0), (0, 0, 88, 88),
        "NOFIRE", "DERIVED", "degenerate")
    add("N/garbage bmp", (0, 0), (0, 0, 88, 88), (0, 0, 88, 88),
        "NOFIRE", "DERIVED", "a1 misread - must fail safe")
    add("N/huge bmp", (99999, 99999), (0, 0, 88, 88), (0, 0, 88, 88),
        "NOFIRE", "DERIVED", "a1 misread - must fail safe")
    add("N/state4 overrun", (176, 44), (352, 0, 440, 88), (0, 0, 88, 88),
        "NOFIRE", "DERIVED", "state index 4 - impossible for a 4-state strip")
    add("N/unaligned left", (176, 44), (37, 0, 125, 88), (0, 0, 88, 88),
        "NOFIRE", "DERIVED", "src.left is not a cell multiple")

    # ---- UNDECIDED - listed, never guessed ---------------------------------
    add("U/uniform 2x non-strip", (200, 50), (0, 0, 100, 100), (0, 0, 100, 100),
        "UNDECIDED", "DERIVED",
        "a non-strip sheet drawn at a uniform 2x over-read is arithmetically "
        "identical to the defect; only the CALLER can tell them apart")
    add("U/8-state strip", (128, 16), (32, 0, 64, 32), (0, 0, 32, 32),
        "UNDECIDED", "DERIVED",
        "the Audio playlist checkbox slices by imageWidth/8 "
        "(SC4-UI-ENGINE.md:305); bmpW/4 is the wrong unit there")
    return F


# ---------------------------------------------------------------------------
# PER-CONDITION ADVERSARIES. Not claims about blits the game makes - each is a
# shape built so that EXACTLY ONE V2 condition rejects it. They exist to prove
# every condition can still decide something; a condition with no adversary is
# decoration and should be deleted, not admired.
# ---------------------------------------------------------------------------
ADVERSARIES = [
    dict(cond="C1-sane", name="a1 misread as a huge rect",
         bmp=(400000, 100000), src=(0, 0, 200000, 200000),
         dst=(0, 0, 200000, 200000),
         note="a perfectly uniform 2x over-read of a bitmap no UI sheet can "
              "be. Only the 4096 sanity bound stops it - this is the fail-safe "
              "for the operand-identity hypothesis."),
    dict(cond="C2-bmpW%4", name="177x44 - not a 4-state strip",
         bmp=(177, 44), src=(88, 0, 176, 88), dst=(0, 0, 88, 88),
         note="integer division would hand back stateW=44 and 4*44 != 177."),
    dict(cond="C4-oneToOne", name="the engine is already stretching",
         bmp=(176, 44), src=(88, 0, 176, 88), dst=(0, 0, 176, 88),
         note="dst != src means something else already owns the scale."),
    dict(cond="C5-topAligned", name="read starts below the top row",
         bmp=(176, 44), src=(88, 10, 176, 98), dst=(0, 0, 88, 88),
         note="a 4-state strip is always read from y=0."),
    dict(cond="C6-srcW>stateW", name="1px vertical over-read, none horizontal",
         bmp=(176, 132), src=(0, 0, 44, 133), dst=(0, 0, 44, 133),
         note="found by the B3 sweep, not by hand: when the two axes round "
              "independently the vertical over-read can be 1px while the "
              "horizontal one rounds to zero. C6 is NOT implied by C7 & C10."),
    dict(cond="C7-srcH>bmpH", name="1px horizontal over-read, none vertical",
         bmp=(176, 132), src=(0, 0, 45, 132), dst=(0, 0, 45, 132),
         note="the mirror of the C6 adversary. Both axes must be asked; "
              "`srcH == bmpH` - the shipped condition - would have ACCEPTED "
              "this and rewritten a blit that is 1px wide of correct."),
    dict(cond="C8-srcW<bmpW", name="ratio 4 - the whole strip in one cell",
         bmp=(176, 44), src=(0, 0, 176, 176), dst=(0, 0, 176, 176),
         note="THE BRIEF'S FIX, isolated. srcW == bmpW is indistinguishable "
              "from 'draw the whole bitmap', so it must stay excluded - which "
              "means this predicate is DELIBERATELY BLIND at a 4x tier."),
    dict(cond="C9-cellAligned", name="src.left off the cell grid",
         bmp=(176, 44), src=(37, 0, 125, 88), dst=(0, 0, 88, 88),
         note="state index must be an exact multiple of the cell width."),
    dict(cond="C9-cellAligned", name="state index 4 on a 4-state strip",
         bmp=(176, 44), src=(352, 0, 440, 88), dst=(0, 0, 88, 88),
         note="impossible for a strip the engine slices by 4."),
    dict(cond="C10-uniform", name="356x58 art in a SQUARE 3x cell",
         bmp=(356, 58), src=(132, 0, 264, 132), dst=(0, 0, 132, 132),
         note="over-read 1.48x wide but 2.28x tall. Realistic (a NAM 89x58 "
              "icon in a stock 44x44 menu slot) and decided by C10 alone. The "
              "on-screen right answer here is UNDECIDED, so the predicate "
              "takes the fail-safe branch and leaves the blit alone."),
]


# ---------------------------------------------------------------------------
# EVIDENCE: the fixture corpus must still be present in the artefacts it
# claims to be mined from. A corpus that quietly stops matching reality is the
# failure mode this whole folder exists to prevent.
# ---------------------------------------------------------------------------

RE_DSTRIP = re.compile(
    r"DSTRIP src (\d+)x(\d+) \((\d+),(\d+),(\d+),(\d+)\) "
    r"dst (\d+)x(\d+) \((\d+),(\d+),(\d+),(\d+)\) "
    r"a1=\w+ srcTex=(\d+)x(\d+) isBuf=(\d)")
RE_ICONFIT = re.compile(
    r"ICONFIT bmp (\d+)x(\d+) stateW=(\d+) src (\d+)x(\d+) -> \d+x\d+ "
    r"dst (\d+)x(\d+)")


def mine_logs():
    """Returns (dstrip_shapes, iconfit_shapes) or None if the captures are
    absent. NEVER a pass - absence is a SKIP with a named reason."""
    if not os.path.isdir(CAPTURES):
        return None
    ds, ic = set(), set()
    for fn in os.listdir(CAPTURES):
        if not fn.lower().endswith(".log"):
            continue
        p = os.path.join(CAPTURES, fn)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "DSTRIP" in line:
                        m = RE_DSTRIP.search(line)
                        if m:
                            g = [int(x) for x in m.groups()]
                            ds.add(((g[12], g[13]), (g[2], g[3], g[4], g[5]),
                                    (g[6], g[7]), g[14]))
                    elif "ICONFIT" in line:
                        m = RE_ICONFIT.search(line)
                        if m:
                            g = [int(x) for x in m.groups()]
                            ic.add(((g[0], g[1]), (g[3], g[4]), (g[5], g[6])))
        except OSError:
            continue
    return ds, ic


def census():
    """Re-derive the icon dimensions from disk. PNG MAGIC is checked, never the
    extension - DbpfExtract names every output .png regardless of type."""
    got = {}
    missing = []
    for d in CENSUS_DIRS:
        if not os.path.isdir(d):
            missing.append(d)
            continue
        for root, _dirs, files in os.walk(d):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    with open(p, "rb") as f:
                        b = f.read(26)
                except OSError:
                    continue
                if b[:8] != b"\x89PNG\r\n\x1a\n":
                    continue
                w, h = struct.unpack(">II", b[16:24])
                got[(w, h)] = got.get((w, h), 0) + 1
    return got, missing


# ---------------------------------------------------------------------------
# THE RUN
# ---------------------------------------------------------------------------

def evaluate(F):
    """Runs every predicate over every fixture. Returns per-predicate tallies."""
    res = {}
    for pname, pfn in PREDICATES:
        tally = dict(fire_ok=0, fire_miss=[], nofire_ok=0, nofire_bad=[],
                     undecided=[])
        for fx in F:
            fired, new, trace = pfn(fx["bmp"], fx["src"], fx["dst"])
            if fx["verdict"] == "UNDECIDED":
                tally["undecided"].append((fx["name"], fired))
                continue
            if fx["verdict"] == "FIRE":
                if fired:
                    tally["fire_ok"] += 1
                else:
                    tally["fire_miss"].append((fx["name"], trace))
            else:
                if fired:
                    tally["nofire_bad"].append((fx["name"], new, trace))
                else:
                    tally["nofire_ok"] += 1
        res[pname] = tally
    return res


def first_false(trace):
    for n, v in trace:
        if v is False:
            return n
    return "-"


def main(argv):
    global VERBOSE
    VERBOSE = "-v" in argv or "--verbose" in argv
    F = fixtures()
    n_fire = sum(1 for f in F if f["verdict"] == "FIRE")
    n_nofire = sum(1 for f in F if f["verdict"] == "NOFIRE")
    n_und = sum(1 for f in F if f["verdict"] == "UNDECIDED")
    print("GATE #149 - ICONFIT predicate. %d fixtures: %d FIRE, %d NOFIRE, "
          "%d UNDECIDED." % (len(F), n_fire, n_nofire, n_und))
    print("   origins: %d MEASURED, %d DERIVED, %d ASSUMED"
          % (sum(1 for f in F if f["origin"] == "MEASURED"),
             sum(1 for f in F if f["origin"] == "DERIVED"),
             sum(1 for f in F if f["origin"] == "ASSUMED")))

    # -- 0. the corpus is still the corpus ---------------------------------
    print("\n0. THE ART CENSUS THE FIXTURES ARE BUILT FROM (PNG magic, not "
          "extension)")
    got, missing = census()
    if missing:
        skips.append("census dirs absent: %d of %d"
                     % (len(missing), len(CENSUS_DIRS)))
        print("   SKIP %d census dir(s) absent - fixture dims not re-derived "
              "(this is a SKIP, not a pass)" % len(missing))
        for m in missing:
            print("        %s" % os.path.relpath(m, ROOT))
    else:
        tot = sum(got.values())
        check(got == CENSUS_EXPECT,
              "census matches the recorded corpus: %s (%d icons)"
              % (", ".join("%dx%d=%d" % (w, h, n)
                           for (w, h), n in sorted(got.items())), tot))
        nonsquare = got.get((356, 58), 0)
        check(nonsquare * 100 // max(tot, 1) == 32,
              "356x58 (NON-SQUARE, 89x58 states) is 32%% of %d icons" % tot)
        check(all(w % 4 == 0 for w, _h in got),
              "every real icon width divides by 4 (the ONLY state-count source: "
              "356/58 = 6.14, so geometry can never give it)")

    # -- 1. the log evidence still exists ----------------------------------
    print("\n1. THE MEASURED FIXTURES ARE STILL IN THE SHIPPED CAPTURES")
    mined = mine_logs()
    if mined is None:
        skips.append("_tests\\captures absent - log evidence not re-verified")
        print("   SKIP %s absent (this is a SKIP, not a pass)" % CAPTURES)
    else:
        ds, ic = mined
        check(len(ds) > 0, "DSTRIP evidence present: %d distinct blit shapes"
              % len(ds))
        check(all(isbuf == 1 for _t, _s, _d, isbuf in ds),
              "every DSTRIP source passed the a1 VTABLE identity check "
              "(isBuf=1) - the operand layout is corroborated, not assumed")
        check(all(s[2] - s[0] == d[0] and s[3] - s[1] == d[1]
                  for _t, s, d, _b in ds),
              "every measured blit on this path is 1:1 (srcW==dstW, "
              "srcH==dstH) - %d/%d shapes" % (len(ds), len(ds)))
        over = {(t, s, d) for t, s, d, _b in ds
                if s[2] - s[0] > t[0] // 4 and t[0] % 4 == 0}
        check(len(over) >= 5,
              "%d measured OVER-READ shapes (1x art in a scaled cell)"
              % len(over))
        check(all((s[3] - s[1]) > t[1] for t, s, d in over),
              "every measured over-read reads PAST the bitmap VERTICALLY too "
              "(srcH > bmpH) - which is why `srcH == bmpH` could never match")
        # the two regressions
        check(((300, 120), (300, 120), (300, 120)) in ic
              and ((152, 38), (152, 38), (152, 38)) in ic,
              "both real full-bitmap ICONFIT firings still in the log "
              "(%d distinct ICONFIT shapes total)" % len(ic))
        check(all(b == s for b, s, _d in ic),
              "EVERY ICONFIT firing ever logged had srcW == bmpW - i.e. 100% "
              "of the shipped predicate's firings were the regression class")
        # nothing measured may be uncovered by the corpus
        modeled = {(f["bmp"], (f["src"][2] - f["src"][0],
                               f["src"][3] - f["src"][1])) for f in F}
        unc = {(t, (s[2] - s[0], s[3] - s[1])) for t, s, _d, _b in ds} - modeled
        check(not unc, "no measured DSTRIP shape is outside the corpus "
              "(%d uncovered: %s)" % (len(unc), sorted(unc)[:3]))

    # -- 2. the predicates over the corpus ---------------------------------
    print("\n2. PREDICATES OVER THE CORPUS")
    res = evaluate(F)
    for pname, t in res.items():
        print("   %-11s FIRE %2d/%-2d   NOFIRE %2d/%-2d   %s"
              % (pname, t["fire_ok"], n_fire, t["nofire_ok"], n_nofire,
                 "clean" if not t["nofire_bad"] else
                 "%d WRONG FIRINGS" % len(t["nofire_bad"])))
        if VERBOSE or t["nofire_bad"]:
            for nm, new, tr in t["nofire_bad"]:
                print("        fires on %-34s -> src %s" % (nm, new))
            for nm, tr in t["fire_miss"]:
                print("        misses   %-34s (first false: %s)"
                      % (nm, first_false(tr)))

    print("\n2a. CALIBRATION - the gate must be able to see the SHIPPED defect")
    t1 = res["V1_SHIPPED"]
    check(len(t1["nofire_bad"]) >= 2,
          "V1_SHIPPED (as shipped) fires on the real full-bitmap blits "
          "(%d wrong firings) - the gate reproduces the live regression"
          % len(t1["nofire_bad"]))
    check(t1["fire_ok"] == 0,
          "V1_SHIPPED fires on 0 of %d must-fire fixtures - it was INERT on "
          "its own target class (`srcH == bmpH` is false for every real "
          "over-read: measured srcH=88 vs bmpH=44)" % n_fire)

    print("\n2b. THE BRIEF'S MINIMAL FIX IS NECESSARY BUT NOT SUFFICIENT")
    t2 = res["V1_FIXED"]
    real = [nm for nm, _n, _t in t2["nofire_bad"] if nm.startswith("R/")]
    check(not real, "V1_FIXED no longer fires on either real regression")
    check(t2["fire_ok"] == 0,
          "V1_FIXED still fires on 0 of %d must-fire fixtures - the minimal "
          "fix removes the regression and cures NOTHING" % n_fire)
    check(len(t2["nofire_bad"]) > 0,
          "V1_FIXED still fires on %d must-not-fire fixture(s): %s"
          % (len(t2["nofire_bad"]),
             ", ".join(nm for nm, _n, _t in t2["nofire_bad"])))

    print("\n2c. V2 - the measured model")
    t3 = res["V2"]
    check(t3["fire_ok"] == n_fire,
          "V2 fires on all %d must-fire fixtures (measured AND derived, "
          "1.5x / 2x / 3x, square AND 356x58)" % n_fire)
    check(not t3["nofire_bad"],
          "V2 fires on none of the %d must-not-fire fixtures" % n_nofire)

    print("\n3. INVARIANTS OF THE REWRITE (V2)")
    bad_bounds, bad_state, bad_idem, bad_noop = [], [], [], []
    for fx in F:
        if fx["verdict"] != "FIRE":
            continue
        fired, new, _tr = v2(fx["bmp"], fx["src"], fx["dst"])
        if not fired:
            continue
        bw, bh = fx["bmp"]
        if not (0 <= new[0] < new[2] <= bw and 0 <= new[1] < new[3] <= bh):
            bad_bounds.append((fx["name"], new))
        srcW = fx["src"][2] - fx["src"][0]
        if new[0] != (fx["src"][0] // srcW) * (bw // 4):
            bad_state.append((fx["name"], new))
        again, _n2, _t2 = v2(fx["bmp"], new, fx["dst"])
        if again:
            bad_idem.append(fx["name"])
    check(not bad_bounds,
          "every rewrite lands INSIDE the bitmap (%d out of bounds) - state<=3 "
          "so right <= 4*stateW == bmpW, bottom == bmpH, by construction"
          % len(bad_bounds))
    check(not bad_state,
          "every rewrite keeps the ENGINE's state index (state = src.left / "
          "srcW, because src.left is in CELL units) (%d wrong)" % len(bad_state))
    check(not bad_idem,
          "the rewrite is IDEMPOTENT - re-running V2 on its own output never "
          "fires again (%d re-fired; this runs in a per-frame draw path)"
          % len(bad_idem))
    # f=1 reduction
    for st in range(4):
        s, d = cell(st, 44, 44)
        fired, _n, _t = v2((176, 44), s, d)
        if fired:
            bad_noop.append(st)
    check(not bad_noop,
          "f=1 REDUCTION: with 1x art in a 1x cell the predicate is false for "
          "all four states (%s) - it cannot fight the static packages"
          % ("clean" if not bad_noop else bad_noop))

    print("\n4. TWO STRUCTURAL CLAIMS, MACHINE-CHECKED")
    # 4a: the modulo condition can never be true at a fractional ratio
    mod_15 = []
    for (bw, bh) in ((176, 44), (352, 88), (356, 58)):
        sw = bw // 4
        cw = rhu(sw * 1.5)
        if cw % sw == 0:
            mod_15.append((bw, bh))
    check(not mod_15,
          "`srcW % stateW == 0` is FALSE for every census dim at f=1.5 "
          "(44->66, 88->132, 89->134) - the V1 family is structurally blind to "
          "the entire 1.5x tier, at every icon size")
    # 4b: the counterexample class the brief's minimal fix cannot exclude is
    # excluded TWICE by V2, by two conditions with independent reasons. Neither
    # alone is a single point of failure.
    twice = []
    for fx in F:
        if fx["verdict"] != "NOFIRE":
            continue
        if not v1(fx["bmp"], fx["src"], fx["dst"], conds=V1F_CONDS)[0]:
            continue          # V1_FIXED already excludes it; not this class
        a = v2(fx["bmp"], fx["src"], fx["dst"], skip={"C7-srcH>bmpH"})[0]
        b = v2(fx["bmp"], fx["src"], fx["dst"], skip={"C10-uniform"})[0]
        c2 = v2(fx["bmp"], fx["src"], fx["dst"],
                skip={"C7-srcH>bmpH", "C10-uniform"})[0]
        twice.append((fx["name"], a, b, c2))
    check(twice and all((not a) and (not b) and c
                        for _n, a, b, c in twice),
          "every fixture V1_FIXED still gets wrong (%s) is excluded by C7 AND "
          "by C10 INDEPENDENTLY - drop either and V2 stays silent, drop both "
          "and it fires. No single condition is a point of failure here"
          % ", ".join(n for n, _a, _b, _c in twice))

    print("\n5. UNDECIDED - listed, never guessed")
    for nm, fired in res["V2"]["undecided"]:
        fx = next(f for f in F if f["name"] == nm)
        undecided.append(nm)
        print("   UNDECIDED %-26s V2 would %-9s : %s"
              % (nm, "FIRE" if fired else "NOT FIRE", fx["note"]))

    print("\n" + "=" * 70)
    print("buckets: %d FAIL, %d SKIP, %d UNDECIDED "
          "(a SKIP is not a pass; an UNDECIDED is not a pass)"
          % (len(fails), len(skips), len(undecided)))
    for s in skips:
        print("   SKIP: %s" % s)
    if fails:
        print("GATE #149 RED - %d failure(s):" % len(fails))
        for f_ in fails:
            print("   - %s" % f_)
        return 1
    print("GATE #149 GREEN - V2 certified over %d fixtures. V1_SHIPPED and "
          "V1_FIXED are NOT certified (see 2a/2b)." % len(F))
    return 0


# ---------------------------------------------------------------------------
# NEGATIVE CONTROLS.  A gate that cannot fail proves nothing.
# ---------------------------------------------------------------------------

def selftest():
    print("NEGATIVE CONTROLS - each MUST make the gate go red.\n")
    F = fixtures()
    real = [f for f in F if f["name"].startswith("R/")]
    fired_n = 0
    broken = []

    def expect_fail(cond, label):
        nonlocal fired_n
        if cond:
            print("   BROKEN GATE: %s did NOT fail" % label)
            broken.append(label)
        else:
            print("   ok   failed-as-expected: %s" % label)
            fired_n += 1

    print("A. THE MANDATORY ONE - revert `srcW != bmpW` on V1_FIXED.")
    print("   (run on V1_FIXED, because that is the predicate the brief's fix")
    print("    defines. See control B for why it is NOT the load-bearing")
    print("    condition in V2 - stating that plainly is the point.)")
    for fx in real:
        ok_with, _n, _t = v1(fx["bmp"], fx["src"], fx["dst"], conds=V1F_CONDS)
        ok_without, new, _t = v1(fx["bmp"], fx["src"], fx["dst"],
                                 skip={"H-srcW!=bmpW"}, conds=V1F_CONDS)
        print("     %-24s with fix: %-9s | reverted: %-9s -> src %s"
              % (fx["name"], "fires" if ok_with else "silent",
                 "fires" if ok_without else "silent", new))
        expect_fail(not ok_without,
                    "reverted `srcW != bmpW` on %s" % fx["name"])
        expect_fail(ok_with, "the FIXED predicate on %s" % fx["name"])

    print("\nB. ABLATION - drop each V2 condition; which fixtures flip?")
    base = evaluate(F)["V2"]
    if base["nofire_bad"] or base["fire_ok"] != sum(
            1 for f in F if f["verdict"] == "FIRE"):
        print("   BROKEN GATE: V2 is not clean before ablation")
        broken.append("V2 not clean pre-ablation")
    load_bearing = {}
    for cname, _fn in V2_CONDS:
        newly = []
        for fx in F:
            if fx["verdict"] != "NOFIRE":
                continue
            fired, _n, _t = v2(fx["bmp"], fx["src"], fx["dst"], skip={cname})
            if fired:
                newly.append(fx["name"])
        load_bearing[cname] = newly
        tag = ("LOAD-BEARING for %d" % len(newly)) if newly else \
              "redundant over the real corpus"
        print("   %-16s %s%s" % (cname, tag,
                                 (": " + ", ".join(newly[:4])) if newly else ""))
    print("   NOTE the brief's `srcW != bmpW` (C8) and the uniformity condition")
    print("        (C10) are BOTH redundant over the real corpus, because C7")
    print("        (srcH > bmpH) already excludes every real counterexample.")
    print("        Redundant is not the same as useless - control B2 gives each")
    print("        condition a case only it can decide. Saying this out loud")
    print("        beats dressing a passing control up as proof.")

    print("\nB2. PER-CONDITION ADVERSARIES - a shape that ONLY that condition")
    print("    excludes. Each must be (i) silent under V2 and (ii) FIRE the")
    print("    moment its one condition is dropped. A condition with no such")
    print("    shape cannot decide anything and is decoration.")
    for a in ADVERSARIES:
        silent, _n, _t = v2(a["bmp"], a["src"], a["dst"])
        loud, new, _t = v2(a["bmp"], a["src"], a["dst"], skip={a["cond"]})
        okpair = (not silent) and loud
        print("   %-14s %-30s V2 %-7s | without %s: %-7s %s"
              % (a["cond"], a["name"], "silent" if not silent else "FIRES",
                 a["cond"], "FIRES" if loud else "silent",
                 "" if okpair else "  <-- BROKEN"))
        if not okpair:
            broken.append("adversary for %s did not isolate it" % a["cond"])
        else:
            fired_n += 1
        if a["note"]:
            print("                  %s" % a["note"])

    print("\nB3. THE ONE CONDITION WITH NO ADVERSARY IS IMPLIED, NOT MISSING -")
    print("    and the near-miss pair is swept, not eyeballed.")
    bad = [w for w in range(1, 4097) if w % 4 == 0 and w // 4 <= 0]
    if bad:
        print("   BROKEN GATE: C3 is not implied by C1 & C2")
        broken.append("C3 implication")
    else:
        print("   ok   C3 (stateW > 0) is IMPLIED by C1 & C2 over 1..4096: "
              "bmpW > 0 and bmpW % 4 == 0 force bmpW >= 4. It is the only "
              "V2 condition that can decide nothing, and it is kept because "
              "the division below it must never be by zero.")
    ctr = 0
    tested = 0
    for stateW in (6, 16, 38, 44, 66, 75, 88, 89, 132):
        for bmpH in (2, 6, 16, 38, 44, 58, 66, 88, 120, 132):
            tol = stateW + bmpH
            for srcH in range(bmpH + 1, bmpH + 300):     # C7 holds by range
                lo = (srcH * stateW - tol + bmpH - 1) // bmpH
                hi = (srcH * stateW + tol) // bmpH
                for srcW in range(max(lo, 1), hi + 1):
                    tested += 1
                    if not (srcW > stateW):              # C6 must follow
                        ctr += 1
    print("   ok   C6 (srcW > stateW) is NOT implied by C7 & C10: %d of %d "
          "swept shapes satisfy both and still fail C6 (the vertical "
          "over-read is 1px while the horizontal one rounds to zero). C6 "
          "stays, and its B2 adversary came out of this sweep." % (ctr, tested))
    if not ctr:
        print("   NOTE the sweep found none - C6 would then be redundant and "
              "its adversary above must be re-derived.")

    print("\nC. MUTATION - perturb every certified must-fire fixture by 1px.")
    mut_total = mut_flip = 0
    for fx in F:
        if fx["verdict"] != "FIRE":
            continue
        for axis in range(4):
            src = list(fx["src"])
            src[axis] += 1
            mut_total += 1
            fired, _n, _t = v2(fx["bmp"], tuple(src), fx["dst"])
            if not fired:
                mut_flip += 1
    print("   %d of %d single-pixel src perturbations turn the verdict OFF "
          "(%.0f%%) - the predicate is not a wide net" %
          (mut_flip, mut_total, 100.0 * mut_flip / max(mut_total, 1)))
    expect_fail(mut_flip == 0, "a predicate no perturbation can silence")

    print("\nD. A PREDICATE THAT CANNOT FAIL - the control on the controls.")
    always = [("always", lambda c: True)]
    bad = 0
    for fx in F:
        if fx["verdict"] == "NOFIRE":
            ok, _t = _run(always, _dims(fx["bmp"], fx["src"], fx["dst"]))
            if ok:
                bad += 1
    expect_fail(bad == 0,
                "an always-true predicate over %d NOFIRE fixtures" % bad)

    print("\n" + "=" * 70)
    if broken:
        print("SELFTEST RED - %d control(s) did not fire:" % len(broken))
        for b in broken:
            print("   - %s" % b)
        return 1
    print("SELFTEST GREEN - %d negative controls fired." % fired_n)
    return 0


CPP = r"""
// ---- ICONFIT (task #149), the CERTIFIED predicate ------------------------
// Gate #149 (tools\uimap\emu\gate_iconfit_rule.py) certifies exactly this.
// PRECONDITION, not arithmetic: a1's rect fields may only be trusted after
// the VTABLE identity check BltStripThunk already does -
//     if (!a1 || *reinterpret_cast<void**>(a1) != kBufClassVt) return pass;
// ICONFIT shipped without it and read [5..8] out of any object handed in.
const int32_t* sb = reinterpret_cast<const int32_t*>(a1);
const int bmpW = sb[7] - sb[5],  bmpH = sb[8] - sb[6];
const int srcL = s[0], srcT = s[1];
const int srcW = s[2] - s[0], srcH = s[3] - s[1];
const int dstW = d[2] - d[0], dstH = d[3] - d[1];
if (bmpW > 0 && bmpH > 0 && bmpW <= 4096 && bmpH <= 4096          // C1
    && srcW > 0 && srcH > 0 && dstW > 0 && dstH > 0               // C1
    && srcW <= 16384 && srcH <= 16384 && srcL >= 0 && srcT >= 0   // C1
    && (bmpW % 4) == 0)                                           // C2
{
    // the C1 bounds are load-bearing: C10 multiplies srcH by stateW, and an
    // unbounded srcH from a misread operand would overflow int32 before any
    // condition could reject it.
    const int stateW = bmpW / 4;                                  // C3
    const int lhs = srcW * bmpH, rhs = srcH * stateW;             // C10 parts
    if (stateW > 0
        && srcW == dstW && srcH == dstH   // C4  1:1 blit (MEASURED, 25/25)
        && srcT == 0                      // C5  strips are read from the top
        && srcW > stateW                  // C6  horizontal over-read
        && srcH > bmpH                    // C7  vertical over-read  <-- NOT
                                          //     srcH == bmpH, which selected
                                          //     full-bitmap blits and rejected
                                          //     every real over-read
        && srcW < bmpW                    // C8  THE FIX: an over-read is a
                                          //     PARTIAL read, never the whole
                                          //     bitmap (srcW == bmpW is ratio 4)
        && (srcL % srcW) == 0 && (srcL / srcW) <= 3   // C9 cell-aligned state
        && (lhs > rhs ? lhs - rhs : rhs - lhs) <= (stateW + bmpH))   // C10
    {
        // UNIFORM over-read on both axes == 1x art in an f-scaled cell.
        // Rewrite ALL FOUR coordinates: src.left is in CELL units, so the
        // state index is srcL/srcW, and src.bottom is the CELL height.
        const int state = srcL / srcW;
        s[0] = state * stateW;
        s[1] = 0;
        s[2] = s[0] + stateW;   // <= 4*stateW == bmpW, provably in bounds
        s[3] = bmpH;
        // dst is UNTOUCHED - the engine stretches the one state across the
        // cell (in-game confirmed mechanism, BltThunkCtx v2.7.94).
    }
}
"""

if __name__ == "__main__":
    if "--emit" in sys.argv:
        print(CPP)
        sys.exit(0)
    rc = main(sys.argv)
    if "--selftest" in sys.argv:
        print()
        rc = selftest() or rc
    sys.exit(rc)
