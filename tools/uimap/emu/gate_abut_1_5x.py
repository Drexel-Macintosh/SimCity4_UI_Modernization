r"""Find window pairs that ABUT at 1x but separate at 1.5x (#162).

WHY THIS EXISTS, and why it should have been the FIRST instrument. A hairline
between two pieces of UI IS two abutting windows that stopped abutting. Four
hypotheses were shipped before this was written - art snapping, tiled sizing,
9-slice sizing, a runtime-bitmap underfill - each reasoned from a MECHANISM
rather than from the geometry, and each missed. The user's report never changed:
"a line under the advisor portraits", "a line under the mayor's hat", "they
don't exist at 2x".

This computes it directly and offline. For every `.UI`:

  * walk the tree accumulating ABSOLUTE design rects;
  * scale every rect the way the shipped sweep does - edge-derived, rounded IN
    THE PARENT'S ABSOLUTE FRAME (#161):
        newT = R(pAbsT + t) - R(pAbsT)
        newH = R(pAbsT + t + h) - R(pAbsT + t)
    with R = llround, matching UiSpike.cpp::ScaleRound;
  * report every pair whose design edges are EQUAL (they touch) but whose scaled
    edges are not - that gap is the line.

AN INTEGER FACTOR CANNOT PRODUCE ONE. R is exact there, so equal design edges
stay equal. 2x and 3x are run anyway as the POSITIVE CONTROL: if they report any
separation, this model is wrong and nothing it says about 1.5x can be trusted.

    python gate_abut_1_5x.py [--ui <8-hex-iid>] [--top N]

Offline, read-only.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
UI_DIR = os.path.join(TOOLS, "uiscripts", "extracted")

ATTR = re.compile(r'(\w+)=("[^"]*"|\{[^}]*\}|\([^)]*\)|\S+)')
TAG = re.compile(r"<(/?)(LEGACY|CHILDREN)([^>]*)>")
RECT = re.compile(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
# #162: R was llround (half AWAY from zero) because ScaleRound was. That was
# the defect - a span straddling the origin had both edges pushed outward and
# came out a pixel longer than the art. `scale_rules.llround_scale` keeps the
# refuted rule available as this gate's negative control.
from scale_rules import scale_round as R          # noqa: E402


def parse(text):
    """[(depth, attrs)] with CHILDREN nesting tracked."""
    out, depth = [], 0
    for m in TAG.finditer(text):
        close, tag, body = m.group(1), m.group(2), m.group(3)
        if tag == "CHILDREN":
            depth += -1 if close else 1
            continue
        out.append((depth, dict(ATTR.findall(body))))
    return out


def build(nodes, f):
    """-> [(id, absDesignRect, absScaledRect)] for every node."""
    out = []
    # stack[d] = (absDesignOriginX, absDesignOriginY, absScaledOriginX, absScaledOriginY)
    stack = {0: (0, 0, 0, 0)}
    for depth, a in nodes:
        m = RECT.match(a.get("area", ""))
        if not m:
            continue
        l, t, r, b = (int(x) for x in m.groups())
        pdx, pdy, psx, psy = stack.get(depth, (0, 0, 0, 0))
        adl, adt = pdx + l, pdy + t
        adr, adb = pdx + r, pdy + b
        # #161: round in the PARENT's absolute frame
        sl = psx + (R(adl, f) - R(pdx, f))
        st = psy + (R(adt, f) - R(pdy, f))
        sr = sl + (R(adr, f) - R(adl, f))
        sb = st + (R(adb, f) - R(adt, f))
        stack[depth + 1] = (adl, adt, sl, st)
        out.append((a.get("id", "-"), (adl, adt, adr, adb), (sl, st, sr, sb)))
    return out


def check(path, f):
    with open(path, "r", encoding="latin-1") as fh:
        nodes = parse(fh.read())
    wins = build(nodes, f)
    bad = []
    for i in range(len(wins)):
        for j in range(len(wins)):
            if i == j:
                continue
            ai, di, si = wins[i]
            aj, dj, sj = wins[j]
            # vertical stack: i's bottom touches j's top, and they overlap in x
            if di[3] == dj[1] and di[0] < dj[2] and dj[0] < di[2]:
                gap = sj[1] - si[3]
                if gap != 0:
                    bad.append(("V", ai, aj, di[3], gap))
            # horizontal: i's right touches j's left, overlapping in y
            if di[2] == dj[0] and di[1] < dj[3] and dj[1] < di[3]:
                gap = sj[0] - si[2]
                if gap != 0:
                    bad.append(("H", ai, aj, di[2], gap))
    return bad


def main():
    only = None
    if "--ui" in sys.argv:
        only = sys.argv[sys.argv.index("--ui") + 1].lower()
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 20

    files = [f for f in sorted(os.listdir(UI_DIR)) if f.endswith(".ui")]
    if only:
        files = [f for f in files if only in f.lower()]
    if not files:
        print("no .UI matched - refusing to report a clean run over nothing")
        return 1

    totals = {}
    per_file_15 = []
    for f in (1.0, 1.5, 2.0, 3.0):
        n = 0
        for fn in files:
            bad = check(os.path.join(UI_DIR, fn), f)
            n += len(bad)
            if f == 1.5 and bad:
                per_file_15.append((len(bad), fn, bad))
        totals[f] = n

    print("scanned %d .UI file(s)\n" % len(files))
    print("abutting pairs that SEPARATE, by factor:")
    for f in (1.0, 2.0, 3.0, 1.5):
        tag = "  <- POSITIVE CONTROL, must be 0" if f in (1.0, 2.0, 3.0) else "  <- the defect"
        print("   f=%-4s %6d%s" % (f, totals[f], tag))
    if totals[1.0] or totals[2.0] or totals[3.0]:
        print("\nMODEL IS WRONG: an integer factor cannot separate equal edges. "
              "Nothing this says about 1.5x is usable until that reads 0.")
        return 1

    per_file_15.sort(reverse=True)
    print("\nworst files at 1.5x:")
    for n, fn, bad in per_file_15[:top]:
        iid = fn.split("_I-")[-1][:8]
        print("\n  %s  (%d separations)" % (iid, n))
        for kind, a, b, edge, gap in bad[:6]:
            print("     %s  %s | %s  design edge %d  gap %+d px"
                  % (kind, a, b, edge, gap))
    return 0


sys.exit(main())
