#!/usr/bin/env python3
r"""Round 2 of the NAM ItemIcon override: the MAX_PATH stragglers + a
load-order correctness audit of round 1.

TWO THINGS THIS EXISTS TO CATCH.

1. MAX_PATH. Round 1 scanned with a plain open() and a bare `except OSError`,
   so every NAM dat nested past 260 characters vanished from the census
   SILENTLY - 10 icons, and they are exactly the ones the user still saw
   doubling (Legacy Road Viaduct puzzle buttons; the two NOB Dentei
   Tram-in-Avenue station lots). A swallowed error is not an absence.

2. LOAD-ORDER CORRECTNESS. Round 1 took the FIRST copy of a TGI found in
   os.walk order. SC4 resolves duplicates by LOAD order (later wins:
   alphabetical by path, files before subfolders at each level), so if a mod
   ships the same icon twice with different art we may have upscaled the copy
   the game never uses - which renders as a wrong or blank button.
   This audits every duplicate and reports whether round 1 picked the winner.

Read-only except for the output dirs.
"""
import os
import struct
import sys
import hashlib
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
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


def lp(p):
    if os.name == "nt" and len(p) > 240 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(p)
    return p


def index(path):
    try:
        with open(lp(path), "rb") as f:
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
    except (OSError, struct.error) as e:
        print("   READ FAIL (not silent): %s -- %s" % (path[-70:], e))
        return


def load_order_key(path):
    """SC4 load order: walk the tree alphabetically; at each level FILES load
    before SUBFOLDERS. Later load wins. Approximated by (depth-aware) parts."""
    rel = os.path.relpath(path, PLUGINS)
    parts = rel.split(os.sep)
    # directories sort after files at the same level -> tag dirs with 1
    key = []
    for i, p in enumerate(parts):
        key.append((0 if i == len(parts) - 1 else 1, p.lower()))
    return key


def main():
    occ = defaultdict(list)      # instance -> [(path, off, size)]
    ours = set()
    for root, _d, files in os.walk(PLUGINS):
        for fn in files:
            if os.path.splitext(fn)[1].lower() not in DBPF_EXTS:
                continue
            p = os.path.join(root, fn)
            for t, g, i, off, size in index(p):
                if t != PNG_TYPE or g != ICON_GROUP:
                    continue
                if fn.startswith(OURS_PREFIX):
                    ours.add(i)
                else:
                    occ[i].append((p, off, size))

    print("third-party icon TGIs: %d" % len(occ))
    dups = {i: v for i, v in occ.items() if len(v) > 1}
    print("TGIs supplied by MORE THAN ONE file: %d" % len(dups))

    differing = 0
    for i, lst in sorted(dups.items()):
        hs = set()
        for p, off, size in lst:
            with open(lp(p), "rb") as f:
                f.seek(off)
                hs.add(hashlib.sha256(f.read(size)).hexdigest())
        if len(hs) > 1:
            differing += 1
            winner = max(lst, key=lambda x: load_order_key(x[0]))
            print("   0x%08X differs across %d copies -> winner by load order: %s"
                  % (i, len(lst), os.path.basename(winner[0])))
    print("   of those, byte-DIFFERENT copies: %d" % differing)
    if differing == 0:
        print("   => round 1's first-found pick was harmless: every duplicate "
              "is byte-identical.")

    gap = sorted(set(occ) - ours)
    print("\nstill uncovered: %d" % len(gap))
    if not gap:
        return 0

    out = os.path.join(HERE, "nam2-1x")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))
    ok = 0
    need_qfs = []
    for i in gap:
        # pick the LOAD-ORDER WINNER, not the first found
        p, off, size = max(occ[i], key=lambda x: load_order_key(x[0]))
        with open(lp(p), "rb") as f:
            f.seek(off)
            blob = f.read(size)
        if blob[:8] != b"\x89PNG\r\n\x1a\n":
            need_qfs.append((i, p))
            continue
        name = "T-0x%08x_G-0x%08x_I-0x%08x.png" % (PNG_TYPE, ICON_GROUP, i)
        with open(os.path.join(out, name), "wb") as f:
            f.write(blob)
        ok += 1
    print("extracted raw: %d -> %s" % (ok, out))
    if need_qfs:
        print("QFS (need DbpfExtract): %d" % len(need_qfs))
        with open(os.path.join(HERE, "gap2_qfs.txt"), "w") as f:
            for i, p in need_qfs:
                f.write("%08X\t%s\n" % (i, p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
