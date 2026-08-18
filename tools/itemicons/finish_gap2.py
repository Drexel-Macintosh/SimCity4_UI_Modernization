#!/usr/bin/env python3
r"""Finish the NAM ItemIcon override: MAX_PATH stragglers + the Rail correction.

Three defects this closes, all found by measurement after round 1 shipped:

1. MAX_PATH IN OUR SCANNER - 10 icons in dats nested past 260 chars were
   silently skipped by a bare `except OSError`.
2. MAX_PATH IN DbpfExtract.exe - it ERRORS on a 298-char path ("The specified
   path, file name, or both are too long"), so the 8 Legacy Road Viaduct
   puzzle-piece buttons could not be pulled even once found. Cure: copy the
   archive to a short path first, then extract.
3. LOAD-ORDER LOSER - {856DDBAC,6A386D26,6A47A005} is shipped by TWO NAM files
   with DIFFERENT art. Round 1 took first-found (os.walk order) instead of
   last-loaded, so we overrode the button with the copy the game never uses.
   That is the "Rail icon is MIA" the user reported. Winner: RealRailway_Icons.dat.

Run from tools\itemicons. Read-only w.r.t. the game; writes only nam-1x\.
"""
import os
import re
import shutil
import struct
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "..", "dbpf", "DbpfExtract.exe")
PNG_TYPE = 0x856DDBAC
ICON_GROUP = 0x6A386D26
RAIL_TGI = 0x6A47A005
SHORT_TMP = r"C:\Windows\Temp\_sc4icon.dat"
RX = re.compile(r"T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})"
                r"_I-(?:0x)?([0-9a-f]{8})\.png", re.I)


def lp(p):
    if os.name == "nt" and len(p) > 240 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(p)
    return p


def extract_via_short_path(src, outdir):
    """DbpfExtract cannot open a >260-char path. Copy, extract, delete."""
    with open(lp(src), "rb") as f, open(SHORT_TMP, "wb") as o:
        shutil.copyfileobj(f, o)
    try:
        r = subprocess.run([EXTRACT, SHORT_TMP, outdir, "0x%08X" % PNG_TYPE],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("   extract failed: " + (r.stderr or r.stdout).strip()[:160])
    finally:
        if os.path.exists(SHORT_TMP):
            os.remove(SHORT_TMP)


def main():
    gap_file = os.path.join(HERE, "gap2.txt")
    want, sources = set(), {}
    for line in open(gap_file):
        if not line.strip():
            continue
        inst, path = line.rstrip("\n").split("\t")
        want.add(int(inst, 16))
        sources[int(inst, 16)] = path
    want.add(RAIL_TGI)
    print("targets: %d (%d gap + Rail load-order correction)"
          % (len(want), len(want) - 1))

    out = os.path.join(HERE, "nam2-qfs")
    os.makedirs(out, exist_ok=True)

    for src in sorted(set(sources.values())):
        if len(src) > 250:
            print("   long path (%d) -> short-path extract: %s"
                  % (len(src), os.path.basename(src)))
            extract_via_short_path(src, out)
        else:
            subprocess.run([EXTRACT, src, out, "0x%08X" % PNG_TYPE],
                           capture_output=True)

    dest = os.path.join(HERE, "nam-1x")
    merged = 0
    for d in ("nam2-qfs", "nam2-1x"):
        dd = os.path.join(HERE, d)
        if not os.path.isdir(dd):
            continue
        for fn in os.listdir(dd):
            m = RX.match(fn)
            if not m:
                continue
            t, g, i = (int(x, 16) for x in m.groups())
            if t != PNG_TYPE or g != ICON_GROUP or i not in want:
                continue
            shutil.copy2(os.path.join(dd, fn),
                         os.path.join(dest, "T-0x%08x_G-0x%08x_I-0x%08x.png"
                                      % (t, g, i)))
            merged += 1

    have = set()
    for fn in os.listdir(dest):
        m = RX.match(fn)
        if m:
            have.add(int(m.group(3), 16))
    missing = sorted(want - have)
    print("merged %d; nam-1x now holds %d icons" % (merged, len(os.listdir(dest))))
    print("targets still missing: %d %s"
          % (len(missing), ", ".join("0x%08X" % m for m in missing[:10])))

    c = Counter()
    for fn in os.listdir(dest):
        with open(os.path.join(dest, fn), "rb") as f:
            b = f.read(26)
        c[struct.unpack(">II", b[16:24])] += 1
    for (w, h), n in c.most_common():
        print("   %4dx%-4d %4d" % (w, h, n))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
