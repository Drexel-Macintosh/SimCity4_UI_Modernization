r"""FALSIFIED LAW, kept as an instrument: "a button's art cell must equal its
window width". IT DOES NOT. Measured, 2026-08-06.

READ THE RESULT BEFORE THE THEORY.

    1.5x   709 state-strip buttons whose cell != edge-derived window width
    2x     420      "
    3x     420      "

2x and 3x are USER-CONFIRMED PERFECT, and `ScaleDim` returns early at an integer
factor - so those 420 are stock-shaped, not scaling damage. The extremes are not
marginal either: {14416241} is a 24x6 sheet (cell 12 at 2x) drawn into a
996-wide window, and {14015583} is cell 68 in a 48-wide window. GZWinBtn plainly
STRETCHES its state cell to the window; a 1px disagreement is nothing to it.

THEREFORE: a cell/window mismatch at 1.5x is NOT EVIDENCE OF A DEFECT, and this
tool must never be used to justify changing `ScaleDim` or `ScaleSubtree`.

WHY IT WAS BUILT (the tenth failed theory for the 1.5x Day/Night lines): the
Day/Night buttons measure
    1x     window 47x37   cell 47x37   exact
    1.5x   window 70x56   cell 71x56   CELL 1px WIDER
    2x     window 94x74   cell 94x74   exact
    3x                                 exact
which is the exact tier signature of the reported bug - broken at 1.5x, perfect
at the integer tiers. It was still wrong. The signature is a property of ALL
fractional-factor rounding, so EVERY 1.5x-only arithmetic discrepancy will match
it; matching it is worth almost nothing on its own.

The two scalers it compares, both correct, neither changeable on this evidence:

    the WINDOW  UiSpike::ScaleSubtree (src/UiSpike.cpp:15546) - EDGE-DERIVED
                    newW = ScaleRound(l+w, f) - ScaleRound(l, f)
                so siblings that abut before scaling still abut after. That
                makes newW depend on the child's LEFT EDGE: for w*f = N.5 it
                lands on floor or ceil according to the parity of l.
    the ART     Upscale2x.cs::ScaleDim - RoundHalfUp, then (since #143) SNAPPED
                to a multiple of CellUnit(v) so `sheetW / states` stays whole.
                One number per sheet; it cannot know l.

It still earns its place: it is the only instrument that measures those two
against each other, and it reports what the opposite tie-break would cost
(701 vs 709 at 1.5x - an 8-button difference, i.e. the tie-break is nearly
irrelevant, which is its own useful answer).

ORIGINAL (WRONG) PREMISE, kept for the record:

    the WINDOW  UiSpike::ScaleSubtree (src/UiSpike.cpp:15546) - EDGE-DERIVED
                    newW = ScaleRound(l+w, f) - ScaleRound(l, f)
                so that siblings which abut before scaling still abut after.
                Deliberate; do not "fix" it. It means newW depends on the
                child's LEFT EDGE, and for w*f = N.5 it lands on floor OR ceil
                depending on the parity of l.
    the ART     Upscale2x.cs::ScaleDim - RoundHalfUp, then (since #143) SNAPPED
                to a multiple of CellUnit(v) so `sheetW / states` stays whole.
                The cell is one number for the whole sheet; it cannot know l.

A GZWinBtn with `image={g,i}` and NO `imagerect` uses the WHOLE sheet as a
4-state strip and cuts state cells at `sheetW / 4`. So when the snapped cell and
the edge-derived window disagree, the drawn state does not fill its window - or
overhangs it.

MEASURED (2026-08-06), the Day/Night buttons 0xCA35CB74/76/78:
    1x     window 47x37   cell 47x37   exact
    1.5x   window 70x56   cell 71x56   CELL 1px WIDER THAN THE WINDOW
    2x     window 94x74   cell 94x74   exact
    3x                                 exact
`ScaleDim` snapped 188*1.5 = 282 to 284 rather than 280: `CellUnit(188) = 4`,
the two candidates are equidistant, and the tie-break resolves UP.

THIS GATE DOES NOT ASSERT ZERO. Some mismatch is UNAVOIDABLE at a fractional
factor: one sheet serves buttons that may sit at different left-edge parities,
and the two parities want cell widths that differ by 1. What it does is COUNT
the mismatches under the shipped tie-break and under the opposite one, so the
choice is made on a measurement instead of on a story. It FAILS only if a
fractional tier is worse than the integer tiers, which must be clean by
construction (`ScaleDim` returns early at an integer factor).

    python gate_btn_cell_vs_window.py [--tier 15x|2x|3x] [--list N]

Offline. Reads the 1x scripts and the staged art; no game, no exe.
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SS = os.path.join(ROOT, "tools", "selective-safe")
SRC1X_UI = os.path.join(ROOT, "tools", "uiscripts", "extracted")
SRC1X_ART = os.path.join(ROOT, "tools", "dbpf", "extracted", "SimCity_1")

TIERS = {"15x": ("stage-15x", 1.5), "2x": ("stage", 2.0), "3x": ("stage-3x", 3.0)}

# mirrors Upscale2x.cs::kCellCounts
CELL_COUNTS = (2, 3, 4, 6, 8, 12, 16, 24)

RE_NODE = re.compile(r"<LEGACY\s+(.*?)>", re.S)
RE_AREA = re.compile(r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
RE_IMAGE = re.compile(r"image=\{([0-9a-fA-F]+),([0-9a-fA-F]+)\}")
RE_RECT = re.compile(r"imagerect=\(")
RE_ID = re.compile(r"\bid=(0x[0-9a-fA-F]+)")


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to carry
# three private copies - rhu, cell_unit and the body of scale_dim. #162 changed
# ScaleRound in the DLL and every private copy in this folder had to be found by
# hand. `scale_rules.py --drift` hunts any that come back.
#
# scale_dim STAYS LOCAL, deliberately: this gate exists to explore the TIE-BREAK
# (`ties_up`), which the shipped rule fixes to UP. It is built out of the shared
# primitives so only the knob is local, never the arithmetic.
from scale_rules import round_half_up as rhu    # noqa: E402
from scale_rules import cell_unit as _cell_unit  # noqa: E402


def cell_unit(v):
    return _cell_unit(v, CELL_COUNTS)


def scale_dim(v, f, ties_up=True):
    """Mirror of Upscale2x.cs::ScaleDim, with the tie-break as a knob."""
    s = rhu(v * f)
    if f == math.floor(f):
        return s
    k = cell_unit(v)
    if k <= 1 or s % k == 0:
        return s
    down = s - (s % k)
    up = down + k
    if ties_up:
        snapped = down if (s - down) < (up - s) else up
    else:
        snapped = up if (up - s) < (s - down) else down
    if snapped < k:
        snapped = k
    if abs(snapped - s) * 8 > s:
        return s
    return snapped


def png_wh(path):
    try:
        with open(path, "rb") as f:
            head = f.read(33)
    except OSError:
        return None
    if len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))


def find_art(d, gid, iid):
    for n in ("T-0x856ddbac_G-0x%08x_I-0x%08x.png" % (gid, iid),
              "T-856ddbac_G-%08x_I-%08x.png" % (gid, iid)):
        p = os.path.join(d, n)
        if os.path.isfile(p):
            return p
    return None


def collect():
    """Every GZWinBtn with a state strip and NO imagerect: (id, area, tgi)."""
    out = []
    for fn in os.listdir(SRC1X_UI):
        if not fn.lower().endswith(".ui"):
            continue
        try:
            with open(os.path.join(SRC1X_UI, fn), "r", encoding="latin-1") as f:
                txt = f.read()
        except OSError:
            continue
        for m in RE_NODE.finditer(txt):
            a = m.group(1)
            if "GZWinBtn" not in a or RE_RECT.search(a):
                continue
            ar, im = RE_AREA.search(a), RE_IMAGE.search(a)
            if not ar or not im:
                continue
            wid = RE_ID.search(a)
            out.append((fn, wid.group(1) if wid else "-",
                        tuple(int(x) for x in ar.groups()),
                        (int(im.group(1), 16), int(im.group(2), 16))))
    return out


def run(tier, btns, limit, states=4):
    sub, f = TIERS[tier]
    stage = os.path.join(SS, sub)
    if not os.path.isdir(stage):
        print("  SKIP - no stage dir: %s" % stage)
        return None

    seen = checked = 0
    mism_ship = []
    mism_alt = 0
    for fn, wid, area, tgi in btns:
        l, t, r, b = area
        seen += 1
        p1 = find_art(SRC1X_ART, *tgi)
        if not p1:
            continue
        o = png_wh(p1)
        if not o or o[0] % states:
            continue          # not a clean N-state strip at 1x: not our shape
        ps = find_art(stage, *tgi)
        if not ps:
            continue          # this tier does not override that sheet
        s = png_wh(ps)
        if not s:
            continue
        checked += 1

        win_w = rhu(r * f) - rhu(l * f)
        cell = s[0] // states
        if cell != win_w:
            mism_ship.append((fn, wid, area, tgi, o, s, win_w, cell))
        alt_w = scale_dim(o[0], f, ties_up=False)
        if alt_w // states != win_w:
            mism_alt += 1

    print("  state-strip buttons with no imagerect : %d (checked %d)"
          % (seen, checked))
    print("  CELL != EDGE-DERIVED WINDOW WIDTH     : %d   (shipped tie-break)"
          % len(mism_ship))
    print("  same, if the tie-break resolved DOWN  : %d" % mism_alt)
    for fn, wid, area, tgi, o, s, win_w, cell in mism_ship[:limit]:
        print("     %-12s {%08X,%08X} 1x %dx%d area=%s -> win w=%d  cell=%d  (%+d)"
              % (wid, tgi[0], tgi[1], o[0], o[1], area, win_w, cell, cell - win_w))
    if len(mism_ship) > limit:
        print("     ... and %d more" % (len(mism_ship) - limit))
    return len(mism_ship), mism_alt, checked


def main():
    tiers = ["15x", "2x", "3x"]
    limit = 12
    if "--tier" in sys.argv:
        tiers = [sys.argv[sys.argv.index("--tier") + 1]]
    if "--list" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--list") + 1])

    btns = collect()
    res = {}
    for tier in tiers:
        print("=" * 76)
        print("TIER %s" % tier)
        print("=" * 76)
        r = run(tier, btns, limit)
        print()
        if r:
            res[tier] = r

    # NO ASSERTION HERE, ON PURPOSE. The first version of this tool failed
    # when the integer tiers were not exact - and they are NOT exact: 420
    # mismatches each, on tiers the user has confirmed perfect. GZWinBtn
    # stretches its cell to the window, so this quantity does not gate anything.
    # It is REPORTED so the numbers are on record and drift is visible.
    base = max([res[k][0] for k in res if float(TIERS[k][1]).is_integer()] or [0])
    print("integer-tier baseline (STOCK-SHAPED, not damage): %d" % base)
    for k in sorted(res):
        n, alt, checked = res[k]
        print("   %-4s  shipped tie-break %4d   ties-down %4d   of %d checked"
              % (k, n, alt, checked))
    print("REPORT ONLY - a cell/window mismatch is NOT a defect. See the header "
          "before drawing any conclusion from these numbers.")
    sys.exit(0)


main()
