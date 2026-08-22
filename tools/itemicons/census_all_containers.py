#!/usr/bin/env python3
r"""ItemIcon census across EVERY DBPF container type, not just .dat.

WHY (2026-08-05, #139 follow-up). The first NAM icon pass scanned `*.dat`
only and shipped 381 overrides - and icons were still doubling. TRIAGE.md:23
says it outright: "ship 2x art (check .SC4Lot/.SC4Desc, not just .dat)".
`.SC4Lot`, `.SC4Desc`, `.SC4Model` are DBPF archives exactly like `.dat`, and
plugin lots routinely carry their menu icon inside the lot file itself.
Filtering on one extension is the same shallow-probe mistake as scanning
Plugins non-recursively.

Also handles paths past Windows MAX_PATH (NAM nests well beyond 260 chars);
without the \\?\ prefix those files raise FileNotFoundError and vanish from
the census silently.
"""
import os
import struct
import sys
from collections import defaultdict, Counter

import sys as _sys
_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS not in _sys.path:
    _sys.path.insert(0, _TOOLS)
from sc4paths import plugins_dir     # noqa: E402
# Resolved, not hard-coded: $SC4_PLUGINS, else the shell's Documents,
# else the OneDrive-redirected or plain %USERPROFILE% variant. See
# tools/sc4paths.py for why a literal path here was a bug, not a shortcut.
PLUGINS = plugins_dir(require=True)
PNG_TYPE = 0x856DDBAC
ICON_GROUP = 0x6A386D26
OURS_PREFIX = "z_SC4UIScale_"
DBPF_EXTS = (".dat", ".sc4lot", ".sc4desc", ".sc4model", ".sc4")


def longpath(p):
    if os.name == "nt" and len(p) > 240 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(p)
    return p


def index(path):
    try:
        with open(longpath(path), "rb") as f:
            hdr = f.read(96)
            if len(hdr) < 96 or hdr[:4] != b"DBPF":
                return
            count, off = struct.unpack_from("<II", hdr, 36)
            if count == 0 or count > 2_000_000:
                return
            f.seek(off)
            blob = f.read(count * 20)
            for i in range(count):
                yield struct.unpack_from("<IIIII", blob, i * 20)
    except (OSError, struct.error):
        return


def main():
    ours = set()
    theirs = defaultdict(set)          # ext -> instances
    where = defaultdict(set)           # instance -> source paths
    holders = Counter()

    for root, _d, files in os.walk(PLUGINS):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in DBPF_EXTS:
                continue
            p = os.path.join(root, fn)
            hit = False
            for t, g, i, _o, _s in index(p):
                if t != PNG_TYPE or g != ICON_GROUP:
                    continue
                hit = True
                if fn.startswith(OURS_PREFIX):
                    ours.add(i)
                else:
                    theirs[ext].add(i)
                    where[i].add(p)
            if hit:
                holders[ext] += 1

    print("containers holding ItemIcons, by extension:")
    for e, n in holders.most_common():
        print("   %-10s %4d file(s)" % (e, n))

    allt = set().union(*theirs.values()) if theirs else set()
    gap = allt - ours
    print("\nthird-party ItemIcons : %d" % len(allt))
    print("we override           : %d" % len(ours))
    print("STILL UNCOVERED       : %d" % len(gap))

    for e in sorted(theirs):
        g = theirs[e] - ours
        if g:
            print("   from %-10s %4d uncovered" % (e, len(g)))

    if gap:
        folders = Counter()
        for i in gap:
            for p in where[i]:
                folders[os.path.relpath(p, PLUGINS).split(os.sep)[0]] += 1
        print("\nuncovered by top-level folder:")
        for k, n in folders.most_common(10):
            print("   %-30s %4d" % (k, n))
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gap2.txt")
        with open(out, "w") as f:
            for i in sorted(gap):
                f.write("%08X\t%s\n" % (i, sorted(where[i])[0]))
        print("\nwrote %d uncovered TGIs -> %s" % (len(gap), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
