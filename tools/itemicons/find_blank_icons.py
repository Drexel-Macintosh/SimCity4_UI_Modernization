#!/usr/bin/env python3
r"""Find ItemIcon strips that would render INVISIBLE - fully transparent, or
transparent in the state cells the button actually draws.

WHY (2026-08-05). After the NAM override shipped, one button (Rail) went from
DOUBLED to INVISIBLE. Invisible means our override IS winning - the game is
drawing OUR art - and our art has nothing to draw. So the defect is in a
source we extracted or in the upscale, not in the gating.

Checks both the 1x sources and the packed 2x output, and reports per-CELL
alpha (the button shows one 1/4-width cell at a time, ITEMICONS.md:24-29), so
a strip whose first cell is empty but whose others are fine is still caught.
"""
import os
import sys
from collections import Counter

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))


def scan(dirname):
    d = os.path.join(HERE, dirname)
    if not os.path.isdir(d):
        print("  (missing: %s)" % dirname)
        return []
    bad = []
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".png"):
            continue
        p = os.path.join(d, fn)
        try:
            im = Image.open(p).convert("RGBA")
        except Exception as e:
            bad.append((fn, "UNREADABLE: %s" % e))
            continue
        w, h = im.size
        a = im.getchannel("A")
        if a.getextrema()[1] == 0:
            bad.append((fn, "fully transparent %dx%d" % (w, h)))
            continue
        cw = w // 4
        empties = []
        for c in range(4):
            cell = a.crop((c * cw, 0, (c + 1) * cw, h))
            if cell.getextrema()[1] == 0:
                empties.append(c)
        if 0 in empties:
            bad.append((fn, "state cell 0 (normal) empty; empty cells %s" % empties))
        elif empties:
            bad.append((fn, "empty state cells %s (normal cell ok)" % empties))
    return bad


def main():
    for d in ("nam-1x", "nam-up-2"):
        print("=== %s ===" % d)
        bad = scan(d)
        if not bad:
            print("   no blank/unreadable strips")
        for fn, why in bad[:40]:
            inst = fn.split("_I-")[-1].split(".")[0]
            print("   %s  %s" % (inst, why))
        if len(bad) > 40:
            print("   ... and %d more" % (len(bad) - 40))
        print("   total flagged: %d" % len(bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
