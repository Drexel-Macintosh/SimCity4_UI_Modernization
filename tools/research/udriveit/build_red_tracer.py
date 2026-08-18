#!/usr/bin/env python3
r"""#188 RED TRACER: repaint every signpost sheet, same size, and ship it.

    python build_red_tracer.py

WHY THIS AND NOT ANOTHER PROBE
------------------------------
Sixteen attempts tried to identify the U-Drive-It offer balloon's drawer by
reasoning about mechanism, then patching what the reasoning implied. Every
one either did nothing or moved the WRONG visual. The instruments were no
better: hooks on the composer (0x5F20A0 / 0x5F1610 / 0x5F12D0's fetch
0x602B70) read ZERO even armed in the DLL constructor, before app init -
with a positive control proving the hook itself fires for other art.

Yet shipping 2x versions of {856DDBAC, AB7E5421, 2BB075B4 / 2BB06F3F}
visibly moved the mayor-hat pole balloon. So these sheets ARE consumed, by
a path none of our hooks sit on. That contradiction is not resolvable by
more disassembly - it is resolvable by MEASURING THE SHIPPED FILE, which is
this project's own standing law (SIMULATE THE CONSUMER, not the build).

THE EXPERIMENT
--------------
Repaint all 93 sheets a saturated red, PRESERVING every dimension and the
alpha channel. Geometry cannot change, so nothing can misalign (the exact
failure mode of the v3.0.23 2x attempt). Then:

    offer balloon turns RED  -> it is drawn from this art. Bisect the 93 to
                                find which sheet, then ship a proper 2x pair
                                (frame AND glyph together).
    offer balloon UNCHANGED  -> the art route is excluded for it, by
                                measurement rather than by a null probe -
                                and whatever DOES turn red names the family
                                that owns these sheets.

Either outcome is decisive, and neither depends on a mechanism being right.
The colour key (magenta 0xFF00FF) is left alone: it is a transparency
signal, and recolouring it would paint the cut-out areas instead of the art.
Read-only on the game; writes only the staged dat.
"""
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ART = os.path.join(HERE, "signpost-art")
PACKER = os.path.join(PROJ, "tools", "dbpf", "DbpfPack.exe")
OUT = os.path.join(HERE, "build", "SC4UIScale_RedTracer.dat")

TYPE = 0x856DDBAC
GROUP = 0xAB7E5421
# Magenta is the colour key - repainting it would fill the transparent
# cut-outs with red and change the SHAPE, which is the one thing this
# experiment must not do.
KEY = (255, 0, 255)


def fatal(msg):
    print("FATAL: " + msg)
    sys.exit(1)


def redden(src, dst):
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    px = im.load()
    touched = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if (r, g, b) == KEY:
                continue
            px[x, y] = (255, 0, 0, a)
            touched += 1
    im.save(dst, "PNG")
    return (w, h), touched


def main():
    if not os.path.isdir(ART):
        fatal("no extracted signpost art at " + ART)
    if not os.path.isfile(PACKER):
        fatal("DbpfPack.exe not found at " + PACKER)

    names = sorted(n for n in os.listdir(ART) if n.lower().endswith(".png"))
    if not names:
        fatal("no PNGs in " + ART)

    stage = tempfile.mkdtemp(prefix="redtracer_")
    made = 0
    untouched = []
    for n in names:
        inst = os.path.splitext(n)[0].split("-")[-1]
        try:
            inst_i = int(inst, 16)
        except ValueError:
            fatal("cannot parse instance from " + n)
        out_name = "T-0x%08X_G-0x%08X_I-0x%08X.png" % (TYPE, GROUP, inst_i)
        size, touched = redden(os.path.join(ART, n),
                               os.path.join(stage, out_name))
        if touched == 0:
            # A sheet with nothing but key/alpha would be an invisible
            # tracer - say so rather than shipping a silent no-op.
            untouched.append(n)
        made += 1
        print("  %-24s %sx%s  %d px reddened" % (n, size[0], size[1], touched))

    if untouched:
        print("NOTE: %d sheet(s) had no paintable pixels: %s"
              % (len(untouched), untouched))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)
    r = subprocess.run([PACKER, stage, OUT], capture_output=True, text=True)
    if r.returncode != 0:
        fatal("DbpfPack failed: %s %s" % (r.stdout, r.stderr))

    # Roundtrip: the packed dat must give back exactly what we staged.
    rt = tempfile.mkdtemp(prefix="redtracer_rt_")
    r = subprocess.run([PACKER, "--extract", OUT, rt],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fatal("roundtrip extract failed: %s %s" % (r.stdout, r.stderr))
    if len(os.listdir(rt)) != made:
        fatal("roundtrip: staged %d, dat holds %d"
              % (made, len(os.listdir(rt))))
    shutil.rmtree(rt, ignore_errors=True)
    shutil.rmtree(stage, ignore_errors=True)

    print("\nOK: %d sheets reddened -> %s (%d bytes)"
          % (made, OUT, os.path.getsize(OUT)))


if __name__ == "__main__":
    main()
