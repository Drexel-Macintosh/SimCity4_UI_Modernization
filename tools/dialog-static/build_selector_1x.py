#!/usr/bin/env python
"""Build z_SC4UIScale_SelectorUI-1x.dat - the scale selector at the STOCK tier.

WHY THIS PACKAGE EXISTS
-----------------------
At the stock tier the DLL stashes every art package, which is correct: 1x must
look and behave like an unmodded game. But the in-game scale selector lives in
DATA (the nodes injected into the Graphic Options script), so stashing every
package also removes the ONE control that lets a player leave 1x. That makes
the stock tier a one-way door, and the whole point of the selector is that it
is not.

So this package carries EXACTLY ONE script - Graphic Options, at STOCK
geometry, with our nodes injected and nothing else changed. Every other
widget keeps its authored 1x rect, so the dialog is pixel-identical to stock
apart from the selector.

ONE OWNER FOR THE INJECTION. The nodes come from build_dialog_static's own
inject_res_readout(), imported rather than copied. If the injection changes,
this package changes with it; a second copy of that template would rot the
moment the first one moved (law: a hand-list rots, key on the derived one).

GEOMETRY IS NOT SCALED HERE ON PURPOSE. The injected areas are already authored
in stock design pixels, which is what the 1x dialog wants. The scaled tiers get
their copies from build_dialog_static.py at factor 1.5 / 2 / 3.

Usage:  python tools/dialog-static/build_selector_1x.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)

sys.path.insert(0, HERE)
import build_dialog_static as BDS          # noqa: E402  (path set above)

IID = BDS.RES_READOUT_IID                  # 8a7e052f - Graphic Options
SRC_FN = "T-00000000_G-96a006b0_I-%s.ui" % IID
OUT_FN = "T-0x00000000_G-0x96a006b0_I-0x%s.ui" % IID
STAGE = os.path.join(HERE, "stage-selector-1x")
OUT_DAT = os.path.join(TOOLS, "packages", "1x", "z_SC4UIScale_SelectorUI-1x.dat")
PACKER = BDS.PACKER


def main():
    src = os.path.join(BDS.UI_DIR, SRC_FN)
    if not os.path.isfile(src):
        sys.exit("FATAL: stock script not found: %s" % src)
    with open(src, "r", encoding="latin-1", newline="") as f:
        text = f.read()

    text, n = BDS.inject_res_readout(text, SRC_FN)
    if n == 0:
        sys.exit("FATAL: nothing injected. inject_res_readout is the ONE owner "
                 "of these nodes - if it became a no-op for this script the "
                 "anchor moved, and guessing a new one is how #192 clipped a "
                 "row. Re-measure the dialog.")
    print("injected %d node(s) into %s" % (n, SRC_FN))

    # PROVE the ids are present and their rects are the AUTHORED stock ones.
    # A silent scale here would put the selector somewhere else in a dialog
    # whose every other widget stayed 1x - the half-patched shape of law 108.
    # Two nodes since 2026-08-19: the combo took the readout row and the
    # separate readout label + "UI Scale" caption were retired, so the closed
    # combo IS the readout. This assertion is the reason that reshape could
    # not ship half-done here - it failed the moment the shapes diverged.
    want = {
        "0x5ca1e002": (270, 320, 286, 336),   # radio, beside the row
        "0x5ca1e005": (292, 319, 458, 342),   # 1px frame around the combo
        "0x5ca1e004": (293, 320, 457, 341),   # combo, ON the readout row
    }
    seen = {}
    for ln in text.split("\n"):
        m = re.search(r"id=(0x5ca1e00\d)\b", ln)
        if not m:
            continue
        a = re.search(r"area=\((\d+),(\d+),(\d+),(\d+)\)", ln)
        if not a:
            sys.exit("FATAL: %s has no area=" % m.group(1))
        seen[m.group(1)] = tuple(int(x) for x in a.groups())
    if seen != want:
        sys.exit("FATAL: injected geometry is not the authored stock geometry.\n"
                 "  want %s\n  got  %s" % (sorted(want.items()), sorted(seen.items())))
    print("verified: %d selector node(s) at authored stock rects" % len(want))

    if not os.path.isdir(STAGE):
        os.makedirs(STAGE)
    for old in os.listdir(STAGE):
        os.remove(os.path.join(STAGE, old))
    with open(os.path.join(STAGE, OUT_FN), "w", encoding="latin-1", newline="") as f:
        f.write(text)

    outdir = os.path.dirname(OUT_DAT)
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    r = subprocess.run([PACKER, STAGE, OUT_DAT], capture_output=True, text=True)
    print((r.stdout or "").strip())
    if r.returncode != 0:
        sys.exit("PACK FAILED:\n" + (r.stderr or ""))

    r = subprocess.run([PACKER, "--list", OUT_DAT], capture_output=True, text=True)
    lines = [ln for ln in (r.stdout or "").splitlines()
             if re.match(r"0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} 0x[0-9A-Fa-f]{8} ", ln)]
    if len(lines) != 1:
        sys.exit("FATAL: package has %d entries, expected exactly 1. This "
                 "package must carry ONE script - anything else is scaling "
                 "the stock tier." % len(lines))
    print("Package: %s (1 entry, %d bytes)" % (OUT_DAT, os.path.getsize(OUT_DAT)))


if __name__ == "__main__":
    main()
