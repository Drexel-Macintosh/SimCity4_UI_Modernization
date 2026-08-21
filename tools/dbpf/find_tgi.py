#!/usr/bin/env python3
r"""Scan every shipped DBPF archive's index for the given INSTANCE ids, any type.

Written for task #55: three .UI image refs ({46a006b0,ea32f104},
{46a006b0,6b998f30}, {46a006b0,ea7f0eae}) were reported LEFT1X by the
dialog-static builder because no 2x asset existed in the upscale preview set.
The 1x source was ALSO absent from tools\dbpf\extracted-png-tgi.csv -- but that
inventory was filtered to type 0x856DDBAC, so absence there is not evidence of
absence in the game.  This scans the raw index of EVERY archive in the install
with NO type filter, which is the only way to tell "stored under another type"
from "dangling reference".

    python find_tgi.py ea32f104 6b998f30 ea7f0eae
    SC4_GAME_DIR=... python find_tgi.py ea7f0eae      (non-default install)

Read-only.  Never writes to the game directory.

WHY THE ARCHIVE LIST IS DISCOVERED, NOT HARD-CODED (2026-08-05, task #140).
This file used to carry a literal list of SEVEN archives, and its own docstring
said "all seven" - which read as a complete census and was not one.  The
install also ships **Intro.dat**, an EIGHTH archive nothing here ever opened.
{46a006b0,ea7f0eae} - the startup splash background - lives in it.  Because the
scan could not see it, the TGI reported as absent, the builder's guard was
relaxed to let a "dangling" ref through, and the shipped splash used CAM's
768x600 background tiled 2x2 across a doubled root.  99.72% of the splash's
pixels differed from stock, and the tool that was supposed to catch it printed
a confident negative.

The lesson is not "add Intro.dat".  It is that a hand-maintained list of what
exists is a claim about the filesystem that ages badly and fails SILENTLY.
Enumerate the directory instead: an add-on, a patch, or an expansion that drops
a ninth archive is then covered for free.  A hard-coded list would have to be
noticed, and nobody notices a list that is only wrong in the case you needed.
"""

import glob
import os
import struct
import sys

GAME = os.environ.get(
    "SC4_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe")


def discover_archives(game_dir):
    """Every DBPF archive shipped in the install root, in load order.

    Case-insensitive on the extension (the install mixes `.dat` and `.DAT` -
    SimCityLocale.DAT is upper-case), de-duplicated, and sorted so runs are
    reproducible.  Returns bare filenames.
    """
    seen = {}
    for pat in ("*.dat", "*.DAT"):
        for p in glob.glob(os.path.join(game_dir, pat)):
            seen[os.path.basename(p).lower()] = os.path.basename(p)
    return [seen[k] for k in sorted(seen)]


def read_index(path):
    """Yield (type, group, instance, offset, size) for a DBPF 1.0 / index 7.0."""
    with open(path, "rb") as f:
        hdr = f.read(96)
        if hdr[:4] != b"DBPF":
            raise SystemExit("%s: not DBPF" % path)
        # 0x24 index entry count, 0x28 index offset, 0x2C index size
        count, idx_off, idx_size = struct.unpack_from("<III", hdr, 0x24)
        f.seek(idx_off)
        blob = f.read(idx_size)
    stride = 20
    if count and idx_size // count != stride:
        raise SystemExit("%s: unexpected index stride %d" % (path, idx_size // count))
    for k in range(count):
        yield struct.unpack_from("<IIIII", blob, k * stride)


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    wanted = {}
    for a in argv:
        wanted[int(a, 16) & 0xFFFFFFFF] = a
    hits = {v: [] for v in wanted.values()}
    archives = discover_archives(GAME)
    if not archives:
        raise SystemExit(
            "no DBPF archives found in %s\n"
            "set SC4_GAME_DIR to the SimCity 4 Deluxe install root." % GAME)
    print("discovered %d archive(s) in %s\n" % (len(archives), GAME))
    for name in archives:
        p = os.path.join(GAME, name)
        if not os.path.isfile(p):
            print("MISSING %s" % p)
            continue
        n = 0
        for (t, g, i, off, size) in read_index(p):
            n += 1
            if i in wanted:
                hits[wanted[i]].append((name, t, g, i, off, size))
        print("scanned %-20s %6d index entries" % (name, n))
    print()
    for a in argv:
        rows = hits[a]
        if not rows:
            # NEVER call this "dangling" from this tool alone. It scans the
            # GAME ARCHIVES and NOTHING ELSE - no Plugins, no mods.
            # 2026-07-31: {46a006b0,ea7f0eae} was declared dangling on exactly
            # this line, a build-time guard was relaxed to let it through, and
            # the startup splash then TILED CAM's 768x600 background 2x2 across
            # a doubled root. TWO separate causes, and both had to be fixed:
            # CAM_Intro.dat supplied the art in Plugins, AND the stock art was
            # in the install's own Intro.dat, which this scan did not open
            # because the archive list was hard-coded to seven names (#140).
            print("0x%-10s not in the %d GAME ARCHIVES scanned (any type)."
                  % (a.upper(), len(archives)))
            print("%-12s   ^ THIS IS NOT 'dangling'. Plugins were NOT scanned."
                  % "")
            print("%-12s     Run: python who_owns_tgi.py %s"
                  % ("", a.lower()))
            continue
        for (name, t, g, i, off, size) in rows:
            print("0x%-10s %-20s T=0x%08X G=0x%08X off=%d size=%d"
                  % (a.upper(), name, t, g, off, size))


if __name__ == "__main__":
    main(sys.argv[1:])
