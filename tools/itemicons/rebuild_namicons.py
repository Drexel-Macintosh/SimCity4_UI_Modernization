#!/usr/bin/env python3
r"""Rebuild the NAM ItemIcon override packages from nam-1x, all three tiers.

Pipeline: Upscale2x -> snap width to a multiple of 4 -> DbpfPack.

WHY THE SNAP. The menu button picks its state cell by imageWidth/4
(ITEMICONS.md:24-29), so a width off the 4-grid gives fractional cells and
smears the four states - the very defect this package exists to remove,
reappearing at another tier. NAM's 356-wide strips are the case that forces
it: 356*1.5 = 534, and 534/4 = 133.5. Caught by gate_namicons.py on its first
run, before anything shipped.

Run from tools\itemicons.
"""
import os
import struct
import subprocess
import sys
from collections import Counter

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "nam-1x")
UPSCALE = os.path.join(HERE, "..", "upscale", "Upscale2x.exe")
PACKER = os.path.join(HERE, "..", "dbpf", "DbpfPack.exe")
TIERS = [("1.5", "15x"), ("2", "2x"), ("3", "3x")]


def main():
    n_src = len(os.listdir(SRC))
    print("sources: %d" % n_src)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)

    for factor, tag in TIERS:
        out = os.path.join(HERE, "nam-up-%s" % factor)
        os.makedirs(out, exist_ok=True)
        for f in os.listdir(out):
            os.remove(os.path.join(out, f))

        r = subprocess.run([UPSCALE, SRC, out, "--factor", factor,
                            "--normalize-names",
                        "--height-exact-group", "6A386D26"], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("UPSCALE FAILED x%s:\n%s" % (factor, r.stderr or r.stdout))

        snapped = 0
        for fn in os.listdir(out):
            p = os.path.join(out, fn)
            with open(p, "rb") as fh:
                b = fh.read(26)
            w, h = struct.unpack(">II", b[16:24])
            if w % 4 == 0:
                continue
            tw = 4 * round(w / 4)
            # #200: NEAREST, not LANCZOS. This builder bypasses Upscale2x, so it never
            # got the resampler discipline the corpus has: LANCZOS is a smoothing
            # filter and softens at EVERY factor, including 2x/3x where the rest of
            # the UI is pixel-exact. Measured corpus-wide, an averaging resample
            # costs ~1 hard edge in 3 at 1.5x; here it cost them at all tiers.
            Image.open(p).convert("RGBA").resize((tw, h), Image.NEAREST).save(p)
            snapped += 1

        c = Counter()
        bad = 0
        for fn in os.listdir(out):
            with open(os.path.join(out, fn), "rb") as fh:
                b = fh.read(26)
            w, h = struct.unpack(">II", b[16:24])
            c[(w, h)] += 1
            if w % 4:
                bad += 1
        dat = os.path.join(HERE, "out", "z_SC4UIScale_NamIcons-%s.dat" % tag)
        r = subprocess.run([PACKER, out, dat], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("PACK FAILED %s:\n%s" % (tag, r.stderr or r.stdout))

        print("x%-4s %3d files  snapped %3d  non-div4 %d  %s  -> %s (%.1f MB)"
              % (factor, len(os.listdir(out)), snapped, bad,
                 " ".join("%dx%d:%d" % (w, h, n) for (w, h), n in c.most_common()),
                 os.path.basename(dat), os.path.getsize(dat) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
