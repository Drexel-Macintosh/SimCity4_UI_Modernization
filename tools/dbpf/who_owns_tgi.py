#!/usr/bin/env python3
r"""WHO ACTUALLY SUPPLIES THIS RESOURCE? - load-order resolver.

TRIAGE.md step 3: when a live window's rect matches NEITHER the stock script
NOR our staged copy, a THIRD FILE owns that TGI. A stock-vs-ours diff is blind
to that, and the blind spot cost five days on task #79c - the winner differed
from stock by ONE PIXEL (270x162 vs 270x161).

This lists every archive on disk that carries a TGI, in LOAD ORDER, so the
actual winner is the last line printed. For uncompressed .UI entries it also
prints the root `area=`, which is usually enough to identify the owner on sight.

    python who_owns_tgi.py 6a553aa4 0a55161d          # instances, any group
    python who_owns_tgi.py --group 96a006b0 6a553aa4  # pin the group too

THE LOAD-ORDER LAW (proven, see README.md / SCENARIOS.md / REGRESSION.md):
game archives load first, then Plugins ROOT files, then Plugins SUBFOLDERS.
A root dat can NEVER override a subfolder dat - which is why overrides of
another mod's data must ship from `zzz-SC4UIScale\`.

Read-only. Never writes to the game or Plugins directories.
"""

import argparse
import os
import struct
import sys

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
import sys as _sys
_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS not in _sys.path:
    _sys.path.insert(0, _TOOLS)
from sc4paths import plugins_dir     # noqa: E402
# Resolved, not hard-coded: $SC4_PLUGINS, else the shell's Documents,
# else the OneDrive-redirected or plain %USERPROFILE% variant. See
# tools/sc4paths.py for why a literal path here was a bug, not a shortcut.
PLUG = plugins_dir(require=True)
# ⛔ THIS USED TO BE A HAND-WRITTEN LIST OF SEVEN, and it was blind to two of
# the nine archives the install actually ships - Intro.dat and Sound.dat, the
# latter holding 1,680 LTEXT records. A "not found in the game archives" answer
# from this tool was therefore never quite the claim it appeared to be.
#
# find_tgi.py already discovers archives instead of listing them; so does the
# row15-probe core. Same approach here: a written-down inventory of a directory
# fails silently the moment the directory changes, which is exactly the failure
# this project has recorded against a nine-archive set before.
def discover_archives(game_dir):
    """Every DBPF archive in the install root, case-insensitively, sorted."""
    import glob
    seen = {}
    for pat in ("*.dat", "*.DAT", "*.Dat"):
        for p in glob.glob(os.path.join(game_dir, pat)):
            seen[os.path.basename(p).lower()] = os.path.basename(p)
    return [seen[k] for k in sorted(seen)]
PLUGIN_EXTS = (".dat", ".sc4lot", ".sc4desc", ".sc4model")


def entries(path):
    """Yield (type, group, instance, offset, size) from a DBPF 1.0 index."""
    with open(path, "rb") as f:
        hdr = f.read(96)
        if hdr[:4] != b"DBPF":
            return
        count, idx_off, idx_size = struct.unpack_from("<III", hdr, 0x24)
        if not count:
            return
        stride = idx_size // count
        f.seek(idx_off)
        blob = f.read(idx_size)
    for k in range(count):
        yield struct.unpack_from("<IIIII", blob, k * stride)


def root_area(path, off, size):
    """The first `area=` in an UNCOMPRESSED entry, or why we can't show one."""
    with open(path, "rb") as f:
        f.seek(off)
        raw = f.read(size)
    if len(raw) > 9 and raw[4:6] == b"\x10\xfb":
        return "<qfs-compressed - extract with DbpfExtract.exe to read>"
    txt = raw.decode("latin-1", "replace")
    k = txt.find("area=")
    return txt[k:k + 26] if k >= 0 else "<no area=>"


def scan(path, label, want_i, want_g, hits):
    try:
        for t, g, i, off, sz in entries(path):
            if i in want_i and (want_g is None or g == want_g):
                hits.append((label, t, g, i))
                print("  %-70s T=%08X G=%08X I=%08X  %s"
                      % (label[:70], t, g, i, root_area(path, off, sz)))
    except Exception as exc:                       # a corrupt dat must not stop the sweep
        print("  !! %s: %s" % (label, exc))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("instances", nargs="+", help="instance ids in hex")
    ap.add_argument("--group", help="restrict to one group id (hex)")
    a = ap.parse_args()
    want_i = {int(x, 16) for x in a.instances}
    want_g = int(a.group, 16) if a.group else None
    hits = []

    archives = discover_archives(GAME)
    print("=== GAME ARCHIVES (load FIRST - lowest priority) ===")
    print("    %d archive(s) discovered in %s" % (len(archives), GAME))
    for name in archives:
        p = os.path.join(GAME, name)
        if os.path.exists(p):
            scan(p, name, want_i, want_g, hits)

    print("=== PLUGINS ROOT (loads before every subfolder) ===")
    for fn in sorted(os.listdir(PLUG), key=str.lower):
        p = os.path.join(PLUG, fn)
        if os.path.isfile(p) and fn.lower().endswith(PLUGIN_EXTS):
            scan(p, fn, want_i, want_g, hits)

    print("=== PLUGINS SUBFOLDERS (alphabetical - the LAST line WINS) ===")
    subs = []
    for root, _dirs, files in os.walk(PLUG):
        if os.path.normcase(root) == os.path.normcase(PLUG):
            continue
        for fn in files:
            if fn.lower().endswith(PLUGIN_EXTS):
                subs.append(os.path.join(root, fn))
    for p in sorted(subs, key=lambda q: os.path.relpath(q, PLUG).lower()):
        scan(p, os.path.relpath(p, PLUG), want_i, want_g, hits)

    print()
    if not hits:
        print("NO HOLDER FOUND - check the instance id (and --group).")
        return 1
    print("WINNER (last loaded): %s  I=%08X" % (hits[-1][0], hits[-1][3]))
    if len(hits) > 1:
        print("%d file(s) carry it; everything above the winner is shadowed."
              % len(hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
