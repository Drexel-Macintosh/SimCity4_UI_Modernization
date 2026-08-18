#!/usr/bin/env python3
"""
PREDICTIVE DEFECT SWEEP helper -- blast radius of the CENTER-IN-SLOT rule.

UiSpike::ScaleMenuFlyouts() is called with pMenu = kGZWin_MenuContainer =
0xAA32BCE6, which UiSpike.cpp itself documents (v2.21.0 comment) is NOT
"plop-menu machinery" but the DATA VIEWS panel.  Every non-baselined child is
swept with ScaleSubtree(..., centerLeaves=TRUE), and that branch keeps any
childless window with w<=CenterLeafMaxPx AND h<=CenterLeafMaxPx at its STOCK
SIZE, merely centering it in the doubled slot -- then records
scaledW==origW, so Classify() reports AlreadyScaled forever after and the
generic city sweep can never correct it.

This lists every leaf that rule can freeze, and whether its art ships at 2x
(if it does, the premise of the rule -- "1x art that cannot grow" -- is false
for that window and the result is 2x art inside a 1x window).
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools", "selective-safe"))
import build_selective_safe as B  # noqa: E402

UI_DIR = os.path.join(PROJ, "tools", "uiscripts", "extracted")
MAXPX = 48          # [UiSpike] CenterLeafMaxPx default and live-ini value
ROOT = 0xAA32BCE6   # kGZWin_MenuContainer


def refmap():
    m = {}
    with open(os.path.join(PROJ, "tools", "selective-safe", "refmap.csv"),
              newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m[(int(r["GroupID"], 16), int(r["InstanceID"], 16))] = (
                r["classification"], r["action"])
    return m


def main():
    rm = refmap()
    # I-2bc9060f is the LIVE Data Views copy (rect-matched to the runtime dump;
    # I-ea287193 / I-0b72f276 are the stale copies -- UiSpike.cpp v2.21.0 note).
    path = os.path.join(UI_DIR, "T-00000000_G-96a006b0_I-2bc9060f.ui")
    roots = B.parse_ui(open(path, encoding="latin-1", newline="").read())
    root = next(r for r in roots if r.wid == ROOT)

    def walk(nd, chain):
        yield nd, chain
        for c in nd.children:
            yield from walk(c, chain + [nd])

    print("CENTER-IN-SLOT blast radius under 0x%08X (CenterLeafMaxPx=%d)" % (ROOT, MAXPX))
    print("=" * 88)
    print("%-12s %-14s %-9s %-7s %s" % ("id", "clsid", "stock", "frozen?", "art (classification -> action)"))
    print("-" * 88)
    n_frozen = n_2xart = 0
    for nd, chain in walk(root, []):
        if nd.children:
            continue                      # rule requires GetChildCount()==0
        if nd.imagerect is None and not nd.images and nd.clsid is None:
            continue
        a = None
        # recover the declared area from the parsed node's own tag text
        # (parse_ui keeps offsets; re-read the attribute directly)
        raw = open(path, encoding="latin-1", newline="").read()[nd.tag_start:nd.tag_end]
        import re
        m = re.search(r"area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)", raw)
        if not m:
            continue
        l, t, r_, b = (int(x) for x in m.groups())
        w, h = r_ - l, b - t
        if w <= 0 or h <= 0:
            continue
        frozen = (w <= MAXPX and h <= MAXPX)
        if not frozen:
            continue
        n_frozen += 1
        arts = []
        for (g, i, _, _) in nd.images:
            cls, act = rm.get((g, i), ("-", "-"))
            arts.append("%08x/%08x %s->%s" % (g, i, cls, act))
            if act in ("2x-in-place", "clone+retarget"):
                n_2xart += 1
        print("0x%08X %-14s %4dx%-4d %-7s %s"
              % (nd.wid or 0, nd.clsid or "?", w, h, "YES", "; ".join(arts) or "(no art)"))
    print("-" * 88)
    print("leaves the rule can freeze at 1x: %d   of which carry art we ship at 2x: %d"
          % (n_frozen, n_2xart))
    return 0


if __name__ == "__main__":
    sys.exit(main())
