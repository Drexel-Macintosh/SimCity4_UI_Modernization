#!/usr/bin/env python3
r"""#162 INSTRUMENTED-ART PROBE builder — one launch, tier 1.5x, eyes-on.

THE QUESTION: which sheet (and for the nine-slice, which band) supplies the
one surviving thin line at the bottom-right of the mayor's-hat button at
1.5x. Every candidate sheet is recoloured to an unmissable flat marker hue;
the line's colour in a screenshot names its source. If the line keeps its
current colour while the whole dock is marker-coloured, NONE of these sheets
draws it and the mechanism is code-drawn/runtime-composed.

METHOD: copy the SHIPPED 1.5x sheets from selective-safe\stage-15x (NOT
preview-15x — two post-upscale passes rewrite some sheets), recolour RGB on
pixels with alpha >= 128 only (stock colour-key is a==0 and the engine guard
is 0 < a < 128 — alpha is left byte-identical everywhere), keep dimensions
identical, pack with DbpfPack.exe.

PALETTE (photo-distinct, none used by the stock dock):
  14015555 hat button          RED     (255,0,0)
  13d14ca0 dock plate/band     MAGENTA (255,0,255)   <- the band under the hat
  4bbe9c7d composite panel     CYAN    (0,255,255)
  14015547 query '?'           YELLOW  (255,255,0)   <- known 1.5x-only row residual
  4b8da4a4 route-query '?'     ORANGE  (255,128,0)
  13f15230 My Sim button       GREEN   (0,255,0)
  14415860 God button          BLUE    (0,64,255)
  13e14fb3 options button      TEAL    (0,128,128)
  14015558 nine-slice 54x54    per-third: top WHITE (255,255,255),
           (the PRIME SUSPECT)            middle VIOLET (128,0,255),
                                          bottom PINK (255,0,128)
           REGRESSION.md 14070-14118: its middle third x18..36 matches the
           captured 18x2 band src(18,36,36,38) exactly; consumer unknown.
           The thirds are 18px at 1.5x (54/3); the captured band y36..38 is
           the TOP EDGE of the bottom third -> a PINK line = bottom band of
           this sheet, VIOLET = middle, WHITE = top.

OUTPUT: out\zzzz_162probe.dat — deploy to Plugins\zzzz-162probe\ (subfolder:
root-vs-root alphabetical order is collation-ambiguous on '_' vs 'z'; a
subfolder always loads after every root file and wins deterministically).
NEVER commit the dat (Sync-Check fails on tracked .dat); revert = DELETE the
folder (a stash inside Plugins disables nothing).
"""
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STAGE = os.path.join(ROOT, "tools", "selective-safe", "stage-15x")
PACKER = os.path.join(ROOT, "tools", "dbpf", "DbpfPack.exe")
WORK = os.path.join(HERE, "out", "stage")
OUT_DAT = os.path.join(HERE, "out", "zzzz_162probe.dat")

FLAT = {
    "14015555": (255, 0, 0),      # hat button        RED
    # NEAR-magenta, deliberately: pure 0xFF00FF is the GAME'S TRANSPARENCY
    # KEY (RUNBOOK.md:158-160) and would be punched to alpha, vanishing the
    # whole dock plate instead of marking it.
    "13d14ca0": (254, 0, 254),    # dock plate        NEAR-MAGENTA
    "4bbe9c7d": (0, 255, 255),    # composite panel   CYAN
    "14015547": (255, 255, 0),    # query ?           YELLOW
    "4b8da4a4": (255, 128, 0),    # route query ?     ORANGE
    "13f15230": (0, 255, 0),      # My Sim            GREEN
    "14415860": (0, 64, 255),     # God               BLUE
    "13e14fb3": (0, 128, 128),    # options           TEAL
    # S3 (dossier): the toolbar panel art in I-2bc90671 - the census's ONE
    # 1.5x-only art-vs-window disagreement (157x488, dW -1 on 0x69e40a1f);
    # "that this 1px paints a short bright run was never measured". Now it
    # is markable in the same shot.
    "14015546": (150, 75, 0),     # toolbar panel     BROWN
    # --- probe v2 (2026-08-24 late): the survivors' sheets. Round 1 proved
    # the box+arc come from NONE of the ten .ui-declared sheets; these are
    # the CODE-FETCHED / undeclared candidates found by the sparse-ink scan.
    "1401554c": (0, 0, 0),        # hollow box outlines (code-drawn) BLACK
    "140155b6": (100, 255, 200),  # eye/label strip     MINT
    "140155b7": (100, 255, 200),  # 1320x18 thin strip  MINT
    "00000019": (100, 255, 200),  # sparse 104x26       MINT
    "14015586": (100, 255, 200),  # sparse 84x21        MINT
    "13d14c10": (128, 128, 255),  # speed/rotate cluster PERIWINKLE
    "13d14c20": (128, 128, 255),
    "13d14c30": (128, 128, 255),
    "13d14c40": (128, 128, 255),
    "13d14c50": (128, 128, 255),
    "13d14c60": (128, 128, 255),
    "13d14c70": (128, 128, 255),
    "13d14c80": (128, 128, 255),
    "13d14c90": (128, 128, 255),
    "2bb075b4": (255, 255, 255),  # sparse 256x256s     WHITE
    "2bb06f3f": (255, 255, 255),
    "2bb07130": (255, 255, 255),
}
NINESLICE = "14015558"            # per-third: WHITE / VIOLET / PINK
THIRDS = [(255, 255, 255), (128, 0, 255), (255, 0, 128)]

# Every pixel that can draw AT ALL carries the marker: only a==0 (the stock
# colour key) is left untouched. The first cut used a >= 128 and would have
# missed the prime suspect's own band rows - 14015558's rows 36-38 hold just
# 4 nonzero pixels each, 2 of them low-alpha; a sparse frame edge tiled 19x
# IS the thin-line shape, so low-alpha pixels are the last place an
# instrument may go blind.
ALPHA_FLOOR = 1


def marked(img, iid):
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    third = max(1, h // 3)
    n = 0
    for y in range(h):
        if iid == NINESLICE:
            colour = THIRDS[min(y // third, 2)]
        else:
            colour = FLAT[iid]
        for x in range(w):
            r, g, b, a = px[x, y]
            if a >= ALPHA_FLOOR:
                px[x, y] = (colour[0], colour[1], colour[2], a)
                n += 1
    return img, n, w, h


def main():
    os.makedirs(WORK, exist_ok=True)
    for old in os.listdir(WORK):
        os.remove(os.path.join(WORK, old))
    total = 0
    for iid in list(FLAT) + [NINESLICE]:
        name = "T-0x856ddbac_G-0x46a006b0_I-0x%s.png" % iid
        src = os.path.join(STAGE, name)
        origin = "15x"
        if not os.path.exists(src):
            # Not tier-shipped: the game serves the STOCK 1x sheet at every
            # tier - itself a suspect property. Mark the stock copy.
            src = os.path.join(ROOT, "tools", "dbpf", "extracted",
                               "SimCity_1",
                               "T-856ddbac_G-46a006b0_I-%s.png" % iid)
            origin = "STOCK-1x(not tier-shipped)"
        if not os.path.exists(src):
            sys.exit("MISSING everywhere: %s" % iid)
        img, n, w, h = marked(Image.open(src), iid)
        print("  [%s]" % origin, end=" ")
        if n == 0:
            sys.exit("REFUSED: zero opaque pixels recoloured in %s "
                     "(instrument would be invisible)" % iid)
        img.save(os.path.join(WORK, name))
        total += 1
        print("  %s  %dx%d  %d px marked" % (iid, w, h, n))
    r = subprocess.run([PACKER, WORK, OUT_DAT],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit("PACK FAILED: %s" % r.stderr.strip())
    print("OK: %d sheets -> %s (%d bytes)"
          % (total, OUT_DAT, os.path.getsize(OUT_DAT)))


if __name__ == "__main__":
    main()
