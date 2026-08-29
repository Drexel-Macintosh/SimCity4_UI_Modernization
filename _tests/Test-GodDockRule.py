#!/usr/bin/env python3
r"""#198 REGRESSION TEST - the god-flyout dock rule, checked against the corpora.

The three LOCKED god dock constants in src/UiSpike.cpp are not hand-tuned
numbers: each one IS the alignment-marker rule evaluated on stock art,

    offset = godToolbarButtonLocal - flyoutAlignmentMarkerLocal

This test re-derives all three from the actual .UI payloads and asserts they
equal the shipped constants. That triple is the regression net for #198: if
the derivation ever stops reproducing the locked values on STOCK, the runtime
derivation would move a user-verified dock, and this goes red first.

It also reports what the rule yields on whatever WINNING scripts are present
(e.g. a skin), which is the number the runtime will use.

    python _tests\Test-GodDockRule.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
STOCK = os.path.join(PROJ, "tools", "uiscripts", "extracted")
CARBON = os.path.join(PROJ, "tools", "research", "carbon", "builder-inputs",
                      "thirdparty-src")

# (label, flyout script iid, god toolbar button design pos, shipped constant)
# Button positions come from the god toolbar script {0,96A006B0,69E3D347}:
# root (5,185,79,536), children at l=10, t=10/70/130/190/250, 74x58.
CASES = [
    ("terraform",  "e9923283", (10, 10),  (6, -80)),
    ("terrain-fx", "aaa44448", (10, 70),  (6, 40)),
    ("day/night",  "aa356502", (10, 250), (6, 160)),
]
MARKER_RE = re.compile(
    r"id=0x0000[aA]{4}[^>]*?area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")


def marker_of(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="latin-1") as f:
        m = MARKER_RE.search(f.read())
    return (int(m.group(1)), int(m.group(2))) if m else None


def main():
    if not os.path.isdir(STOCK):
        print("SKIP: stock .UI corpus absent (%s) - run tools/Bootstrap-Corpus.ps1"
              % STOCK)
        return 0
    failures = []
    print("#198 god dock rule: offset = buttonLocal - markerLocal\n")
    for label, iid, (bl, bt), want in CASES:
        sp = os.path.join(STOCK, "T-00000000_G-96a006b0_I-%s.ui" % iid)
        mk = marker_of(sp)
        if mk is None:
            failures.append("%s: no 0x0000AAAA marker in stock %s" % (label, iid))
            continue
        got = (bl - mk[0], bt - mk[1])
        ok = (got == want)
        print("  %-10s stock marker %-9s -> derived %-10s shipped %-10s %s"
              % (label, str(mk), str(got), str(want), "OK" if ok else "MISMATCH"))
        if not ok:
            failures.append(
                "%s: rule derives %s but src/UiSpike.cpp ships %s - the "
                "runtime derivation would MOVE a locked, user-verified dock"
                % (label, got, want))
        # informational: what the rule yields on a skin's replacement script
        cp = os.path.join(CARBON, "T-00000000_G-96a006b0_I-%s.ui" % iid)
        cmk = marker_of(cp)
        if cmk is not None:
            cgot = (bl - cmk[0], bt - cmk[1])
            delta = (cgot[0] - want[0], cgot[1] - want[1])
            note = "unchanged" if delta == (0, 0) else (
                "dock corrected by (%+d,%+d) design px = %+d px at 1.5x"
                % (delta[0], delta[1], round(delta[1] * 1.5)))
            print("             skin  marker %-9s -> derived %-10s %s"
                  % (str(cmk), str(cgot), note))
    print()
    if failures:
        for f in failures:
            print("FAIL: " + f)
        return 1
    print("ALL PASS (%d locked constants re-derived from the corpus)" % len(CASES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
