#!/usr/bin/env python3
r"""Rebuild the Web Button Improvement Mod art override, all three tiers.

The cyclone-boom "Web Button Improvement Mod" ships its own web-button bitmap
{856DDBAC,46A006B0,14416302} (320x60). Our runtime region scaling enlarges the
button's WINDOW, so a 1x bitmap inside a scaled window stretches soft. This
package carries 1.5x/2x/3x copies upscaled from THE MOD'S OWN bitmap (never a
stock lookalike), gated on the mod still being installed (kThirdPartyDeps row
"WebButtonUI"). The mod's region .UI (0xAA920991) is left to runtime scaling -
doubling it here would double-scale.

Pipeline: Upscale2x -> snap width to a multiple of 4 -> DbpfPack. Same shape as
rebuild_namicons.py. The 1x source lives in webbutton-1x\ (extracted from the
mod's dat; third-party art is not committed).

Run from tools\itemicons.
"""
import os
import shutil
import struct
import subprocess
import sys
from collections import Counter

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "webbutton-1x")
UPSCALE = os.path.join(HERE, "..", "upscale", "Upscale2x.exe")
PACKER = os.path.join(HERE, "..", "dbpf", "DbpfPack.exe")
TIERS = [("1.5", "15x"), ("2", "2x"), ("3", "3x")]
# The mod's OWN WebButtonUI .ui (0xAA920991) with the website button id
# cleared to 0 - exactly what makes Option A "Click Prevented" do nothing.
# Shipping it here (gated on the mod by SyncDat) means that at scaled factors
# our package overrides the live-id .ui the SelectiveArt dat carries, so the
# game's web-launch routine never fires: no browser AND no minimize. When the
# mod is absent this whole dat is disabled and the live button + Simtropolis
# redirect take over.
INERT_UI = os.path.join(HERE, "webbutton-inert-ui",
                        "T-0x00000000_G-0x96a006b0_I-0xaa920991.ui")


def main():
    if not os.path.isdir(SRC) or not os.listdir(SRC):
        sys.exit("webbutton-1x\\ is empty - extract the mod's 14416302 PNG first")
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)

    for factor, tag in TIERS:
        out = os.path.join(HERE, "webbutton-up-%s" % factor)
        os.makedirs(out, exist_ok=True)
        for f in os.listdir(out):
            os.remove(os.path.join(out, f))

        r = subprocess.run([UPSCALE, SRC, out, "--factor", factor,
                            "--normalize-names"], capture_output=True, text=True)
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
            # #200: NEAREST - a width snap must not soften the whole sheet.
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
        if os.path.exists(INERT_UI):
            shutil.copy(INERT_UI, os.path.join(out, os.path.basename(INERT_UI)))
        dat = os.path.join(HERE, "out", "z_SC4UIScale_WebButtonUI-%s.dat" % tag)
        r = subprocess.run([PACKER, out, dat], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("PACK FAILED %s:\n%s" % (tag, r.stderr or r.stdout))

        print("x%-4s %3d files  snapped %3d  non-div4 %d  %s  -> %s (%.1f KB)"
              % (factor, len(os.listdir(out)), snapped, bad,
                 " ".join("%dx%d:%d" % (w, h, n) for (w, h), n in c.most_common()),
                 os.path.basename(dat), os.path.getsize(dat) / 1e3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
