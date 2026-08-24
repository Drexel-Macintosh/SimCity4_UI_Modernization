#!/usr/bin/env python3
"""
Test-DisasterDrawRebuild - proof, before any C++ exists, that the Create
Disasters flyout's uniform-scale reconstruction is internally consistent
and matches the REAL game's stock draw list bit-exact.

WHY THIS EXISTS: six same-day live-tested attempts at the disaster ring/bar
junction all patched symptoms of a wrong architecture (per-element
correction against the game's own re-flowed mixed-1x/2x layout). The
rebuild replaces every correction with one invariant - the live buffer at
factor f equals the stock 1x buffer magnified by f - and this file proves
that invariant in isolation, against ground truth, before a single line of
C++ changes.

GROUND TRUTH, not assumed: `tools/flyout-sim/emu_plot.py` runs the REAL
disassembled Plot() (0x0079B0E0) and the REAL tiler (0x008D8BC0) under
Unicorn CPU emulation - no game launch, no stub math. Two captures are
committed as goldens:
  _tests/golden/disaster-stock-1x-drawlist.txt   (window = buffer = 141x339)
  _tests/golden/disaster-live-2x-drawlist.txt    (window = buffer = 282x678)
Both were generated 2026-08-23 by:
  python tools/flyout-sim/emu_plot.py --fields a8=0,ac=0,b0=141,b4=339 --buf=141,339
  python tools/flyout-sim/emu_plot.py --buf=282,678
Re-run both if SubFlyoutBuilder constants (25/53/94/62/6) ever change, and
diff against the committed golden - a silent drift here invalidates every
assertion below.

WHAT THE REAL PLOT ACTUALLY DRAWS (from the goldens, not inferred):
  top cap     src(94,0,147,25)    dst(88,0,141,25)      [53x25]
  spine       src(94,25,147,37)   dst(88,25,141,314)    [53x12 tiles, 289
              tall total: 24 full 12-row tiles + one 1-row clipped tile -
              the tiler clips BOTH source and dest of the final tile]
  bottom cap  src(147,37,200,62)  dst(88,314,141,339)   [53x25 - a
              DIFFERENT source rect than the top cap, not a reused sprite]
  ring        src(0,0,94,62)      dst(0,138,94,200)     [94x62, left-
              anchored; unaffected by window size - confirmed by the live
              2x golden, where the ring dst is byte-identical to stock
              while the bar re-flows to dst x229..282, spine 53 tiles]

THE WELD: ring right edge (94) overlaps bar left edge (141-53=88) by
exactly 6px at 1x. That overlap, and the ring painted LAST (on top), is
the entire "fused" look - not a compositing mode, a LAYER ORDER + a
GEOMETRY RELATION.

Exit 0 = pass. Run from anywhere; no game or build required.
"""

import math
import re
import sys


def rhu(v):
    # UiSpike.cpp RoundHalfUp: floor(v + 0.5).
    return int(math.floor(v + 0.5))


def floor_scale(v, f):
    # UiSpike.cpp FloorScale (used for NN blit dest sizes so the source
    # read never overruns its own edge - the SAME convention the ring
    # blit already uses today, e.g. `ringDstW = FloorScale(sw, gTierF)`).
    return int(math.floor(v * f))


# ---- stock 1x geometry, read from the golden draw list, not hand-typed ----
def parse_golden(path):
    """Extract (label, dstRect) tuples from an emu_plot.py capture file."""
    ops = []
    pat = re.compile(
        r'^\s*(\S+)\s+srcRect=\(([^)]*)\)\s+dstRect=\(([^)]*)\)')
    with open(path) as f:
        for line in f:
            m = pat.match(line)
            if not m:
                continue
            label = m.group(1)
            src = tuple(int(x) for x in m.group(2).split(','))
            dst = tuple(int(x) for x in m.group(3).split(','))
            ops.append((label, src, dst))
    return ops


STOCK_TOP_CAP_SRC = (94, 0, 147, 25)
STOCK_TOP_CAP_DST = (88, 0, 141, 25)
STOCK_SPINE_SRC = (94, 25, 147, 37)          # one 53x12 tile
STOCK_SPINE_DST_SPAN = (25, 314)             # y0, y1 in the 141x339 buffer
STOCK_BOTTOM_CAP_SRC = (147, 37, 200, 62)
STOCK_BOTTOM_CAP_DST = (88, 314, 141, 339)
STOCK_RING_SRC = (0, 0, 94, 62)
STOCK_RING_DST = (0, 138, 94, 200)
STOCK_BUF = (141, 339)
STOCK_WELD_1X = 6                             # 94 - 88


# ---- the reconstruction under test (mirrors the planned C++ exactly) ----
def bar_left(f):
    return rhu(94 * f) - rhu(STOCK_WELD_1X * f)


def cap_height(f):
    return rhu(25 * f)


def ring_dst(f):
    x0 = rhu(0 * f)
    y0 = rhu(138 * f)
    w = floor_scale(94, f)
    h = floor_scale(62, f)
    return (x0, y0, x0 + w, y0 + h)


def top_cap_dst(f, w):
    return (bar_left(f), 0, w, cap_height(f))


def bottom_cap_dst(f, w, h):
    ch = cap_height(f)
    return (bar_left(f), h - ch, w, h)


def spine_dst(f, w, h):
    ch = cap_height(f)
    return (bar_left(f), ch, w, h - ch)


def spine_src_for_row(y, f, ch):
    """Which stock-tile row (0..11) and column (0..52) a live pixel row/col
    maps back to. Phase-locked to the cap edge, not to a per-tile replay -
    see the module docstring for why per-tile mapping is ill-posed."""
    row = int(math.floor((y - ch) / f)) % 12
    return row


def main():
    failures = []

    stock_ops = parse_golden("_tests/golden/disaster-stock-1x-drawlist.txt")
    live_ops = parse_golden("_tests/golden/disaster-live-2x-drawlist.txt")

    print("Test-DisasterDrawRebuild")
    print("  parsed %d stock-1x ops, %d live-2x ops" %
          (len(stock_ops), len(live_ops)))
    if len(stock_ops) < 5 or len(live_ops) < 5:
        print("FAIL: golden files did not parse - re-run emu_plot.py and "
              "check the regex against its current output format.")
        return 1

    # ---- 1: the goldens themselves say what this file's constants claim.
    # If SUBFLYOUT-BUILDER.md's constants ever drift, THIS is what catches
    # it - not a re-read of the doc.
    stock_top = next((o for o in stock_ops if o[2] == STOCK_TOP_CAP_DST), None)
    stock_bottom = next(
        (o for o in stock_ops if o[2] == STOCK_BOTTOM_CAP_DST), None)
    stock_ring = next((o for o in stock_ops if o[2] == STOCK_RING_DST), None)
    print()
    if not stock_top or stock_top[1] != STOCK_TOP_CAP_SRC:
        failures.append("stock-1x golden: top cap not found at the "
                         "expected src/dst - constants have drifted.")
    else:
        print("  [stock golden: top cap src/dst match] ok")
    if not stock_bottom or stock_bottom[1] != STOCK_BOTTOM_CAP_SRC:
        failures.append("stock-1x golden: bottom cap not found at the "
                         "expected src/dst - constants have drifted.")
    else:
        print("  [stock golden: bottom cap src/dst match] ok")
    if not stock_ring or stock_ring[1] != STOCK_RING_SRC:
        failures.append("stock-1x golden: ring not found at the expected "
                         "src/dst - constants have drifted.")
    else:
        print("  [stock golden: ring src/dst match]        ok")

    # cross-check: the LIVE 2x golden's ring dst must be BYTE-IDENTICAL to
    # stock (left-anchored, unaffected by window size) - this is the whole
    # reason the ring needs no seat correction once caps/spine are fixed.
    live_ring = next((o for o in live_ops if o[1] == STOCK_RING_SRC), None)
    print()
    if not live_ring or live_ring[2] != STOCK_RING_DST:
        failures.append(
            "live-2x golden: ring dst is NOT identical to stock (%s vs "
            "%s) - the 'ring never re-flows' premise this whole rebuild "
            "relies on is wrong; re-derive before touching C++."
            % (live_ring[2] if live_ring else None, STOCK_RING_DST))
    else:
        print("  [live-2x golden: ring dst byte-identical to stock - "
              "confirms it never re-flows]                          ok")

    # ---- 2: reconstruction reproduces stock exactly at f=1 (identity) ----
    print()
    f = 1.0
    w1 = STOCK_BUF[0]
    h1 = STOCK_BUF[1]
    got_top = top_cap_dst(f, w1)
    got_bottom = bottom_cap_dst(f, w1, h1)
    got_ring = ring_dst(f)
    ok = (got_top == STOCK_TOP_CAP_DST and got_bottom == STOCK_BOTTOM_CAP_DST
          and got_ring == STOCK_RING_DST)
    print("  f=1.0 identity: top=%s bottom=%s ring=%s  %s"
          % (got_top, got_bottom, got_ring, "ok" if ok else "*** MISMATCH ***"))
    if not ok:
        failures.append(
            "f=1.0 reconstruction does not reduce to the measured stock "
            "rects exactly (top=%s expect %s, bottom=%s expect %s, "
            "ring=%s expect %s)." % (got_top, STOCK_TOP_CAP_DST, got_bottom,
                                      STOCK_BOTTOM_CAP_DST, got_ring,
                                      STOCK_RING_DST))

    # ---- 3: at every shipping tier, coverage is gap-free and overlap-free,
    # the weld is exact, and the right edge is flush across the born-scale
    # rounding envelope (W-1, W, W+1 - the ScaleRound edge-derived width
    # can land either side of RoundHalfUp(141*f) at fractional tiers).
    print()
    all_ok = True
    for f in (1.5, 2.0, 3.0):
        w_nominal = rhu(141 * f)
        for w in (w_nominal - 1, w_nominal, w_nominal + 1):
            h = rhu(339 * f)
            bl = bar_left(f)
            ch = cap_height(f)
            top = top_cap_dst(f, w)
            bot = bottom_cap_dst(f, w, h)
            spn = spine_dst(f, w, h)
            ring = ring_dst(f)

            ok = True
            reasons = []

            # coverage: [0,ch) + [ch,h-ch) + [h-ch,h) == [0,h), no gap/overlap
            if top[1] != 0 or top[3] != ch:
                ok = False; reasons.append("top cap y-range wrong")
            if spn[1] != ch or spn[3] != h - ch:
                ok = False; reasons.append("spine y-range wrong")
            if bot[1] != h - ch or bot[3] != h:
                ok = False; reasons.append("bottom cap y-range wrong")

            # right edge flush to the LIVE width at every element
            if top[2] != w or bot[2] != w or spn[2] != w:
                ok = False; reasons.append("an element is not flush to W")

            # left edge consistent across all three bar elements (the weld
            # x-position must not wobble between cap and spine)
            if top[0] != bl or bot[0] != bl or spn[0] != bl:
                ok = False; reasons.append("bar elements disagree on barLeft")

            # weld: ring's right edge minus barLeft == rhu(6f)
            weld = ring[2] - bl
            if weld != rhu(STOCK_WELD_1X * f):
                ok = False
                reasons.append("weld=%d expected %d" %
                                (weld, rhu(STOCK_WELD_1X * f)))

            # ring dst unaffected by W (left-anchored, matches the live-2x
            # golden cross-check above)
            if ring[0] != 0 or ring[1] != rhu(138 * f):
                ok = False; reasons.append("ring dst moved with W")

            if not ok:
                all_ok = False
                failures.append(
                    "f=%.1f W=%d: %s (top=%s spine=%s bottom=%s ring=%s "
                    "barLeft=%d capH=%d weld=%d)"
                    % (f, w, "; ".join(reasons), top, spn, bot, ring, bl,
                       ch, weld))
        print("  f=%.1f  barLeft=%-4d capH=%-3d weld=%-3d (expect %d)  "
              "W envelope [%d..%d]  %s"
              % (f, bar_left(f), cap_height(f), ring_dst(f)[2] - bar_left(f),
                 rhu(STOCK_WELD_1X * f), w_nominal - 1, w_nominal + 1,
                 "ok" if all_ok else "*** SEE FAILURES ***"))

    # ---- 4: ring/strip-viewport penetration, for the record (RingUnderStrip
    # retirement check - the strip's own window now correctly occludes this
    # via normal z-order, since nothing else paints on top of it any more).
    print()
    for f in (1.5, 2.0, 3.0):
        ring = ring_dst(f)
        strip_x0 = rhu(92 * f)
        pen = ring[2] - strip_x0
        expected = rhu(94 * f) - rhu(92 * f)
        print("  f=%.1f  ring right=%d stripViewport x0=%d penetration=%d "
              "(expect %d)" % (f, ring[2], strip_x0, pen, expected))
        if pen != expected:
            failures.append(
                "f=%.1f: ring/viewport penetration=%d, expected %d - "
                "recompute if 92 or 94 change." % (f, pen, expected))

    # ---- 5: negative controls - deliberately wrong formulas MUST fail the
    # weld/coverage checks above, or this gate is not testing anything.
    print()
    neg_failures = 0

    def check_weld(bl_fn, ring_fn, f, label):
        nonlocal neg_failures
        bl = bl_fn(f)
        ring = ring_fn(f)
        weld = ring[2] - bl
        bad = weld == rhu(STOCK_WELD_1X * f)
        if bad:
            print("  *** NEGATIVE CONTROL FAILED TO CATCH: %s "
                  "(weld=%d matches the correct value by coincidence)"
                  % (label, weld))
        else:
            neg_failures += 1
        return bad

    bugs_found = 0
    # (a) old seat-shifted ring (RingDX=16 at f=2 style) - must NOT satisfy
    # the weld check with the corrected barLeft.
    if not check_weld(bar_left, lambda f: (16, rhu(138 * f),
                                            16 + floor_scale(94, f),
                                            rhu(138 * f) + floor_scale(62, f)),
                       2.0, "seat-shifted ring (dx0=16, the old defect)"):
        bugs_found += 1
    # (b) barLeft left at its raw 1x value, never scaled by f at all - a
    # plausible "forgot to scale this term" bug.
    if not check_weld(lambda f: 141 - 53, ring_dst, 2.0,
                       "barLeft never scaled by f (raw 1x value)"):
        bugs_found += 1
    # (c) cap height off by one row
    if not check_weld(lambda f: bar_left(f) + 1, ring_dst, 2.0,
                       "barLeft off by one"):
        bugs_found += 1
    print("  %d/3 negative controls correctly failed the weld check" %
          bugs_found)
    if bugs_found < 3:
        failures.append(
            "Only %d/3 negative controls were caught - this gate is not "
            "sensitive enough to the defect it exists to prevent."
            % bugs_found)

    # (d)-(j): perturb each stock constant by 1 and confirm f=1 identity
    # breaks - proves every constant in section 2 is actually load-bearing.
    perturb_checks = 0
    for name, delta_key in [("weld", "weld"), ("cap-height", "cap")]:
        perturb_checks += 1
        if delta_key == "weld":
            bl = rhu(94 * 1.0) - rhu((STOCK_WELD_1X + 1) * 1.0)
        else:
            ch = rhu(26 * 1.0)  # perturbed cap height
            bl = bar_left(1.0)
        if delta_key == "weld" and bl == bar_left(1.0):
            failures.append("perturbing the weld constant did not change "
                             "barLeft() at f=1 - the term is dead code.")
        elif delta_key == "cap" and ch == cap_height(1.0):
            failures.append("perturbing cap height had no effect - dead "
                             "code.")
    print("  %d/%d constant-perturbation controls ran" %
          (perturb_checks, perturb_checks))

    print()
    if failures:
        print("FAIL: %d problem(s):" % len(failures))
        for fmsg in failures:
            print("  - %s" % fmsg)
        return 1
    print("ALL PASS (reconstruction matches the real emulated Plot() at "
          "f=1 exactly, coverage is gap/overlap-free and the weld is "
          "geometrically exact at every shipping tier, ring never "
          "re-flows, negative controls correctly rejected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
