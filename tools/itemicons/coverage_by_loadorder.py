#!/usr/bin/env python3
r"""Coverage measured by LOAD ORDER, not by "is it in any package of ours".

THE DEFECT THIS EXISTS TO CATCH (2026-08-05, found via the invisible Rail
button). Round 1 and round 2 both asked "does ANY z_SC4UIScale_ package
contain this TGI?" - and counted the ROOT ItemIcons dat as coverage. But SC4
loads root Plugins FILES before SUBFOLDERS, so for an icon a mod also ships
from a subfolder, our ROOT copy LOSES and the mod's 1x wins. The icon reads as
covered and renders wrong.

    0x2A3ED76A - stock icon we double in the ROOT package, ALSO shipped by
    NAM's RealRailway_Icons.dat from a subfolder. NAM wins. This is the Rail
    button the user reported as invisible.

Correct rule: an override covers an icon only if OUR file that supplies it
loads AFTER every third-party file that supplies it.
"""
import os
import struct
import sys
from collections import defaultdict

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
    except (OSError, struct.error):
        return


def order_key(path):
    """SC4 load order: alphabetical walk; at each directory level FILES load
    before SUBFOLDERS. Later = wins."""
    rel = os.path.relpath(path, PLUGINS)
    parts = rel.split(os.sep)
    return [(0 if i == len(parts) - 1 else 1, p.lower())
            for i, p in enumerate(parts)]


def main():
    supply = defaultdict(list)     # instance -> [(path, is_ours)]
    for root, _d, files in os.walk(PLUGINS):
        for fn in files:
            if os.path.splitext(fn)[1].lower() not in DBPF_EXTS:
                continue
            p = os.path.join(root, fn)
            mine = fn.startswith(OURS_PREFIX)
            seen = False
            for t, g, i, _o, _s in index(p):
                if t == PNG_TYPE and g == ICON_GROUP:
                    supply[i].append((p, mine))
                    seen = True
            del seen

    total = len(supply)
    third = {i for i, v in supply.items() if any(not m for _p, m in v)}
    losing = []
    for i in sorted(third):
        winner = max(supply[i], key=lambda x: order_key(x[0]))
        if not winner[1]:
            losing.append((i, winner[0]))

    print("icon TGIs seen            : %d" % total)
    print("supplied by a third party : %d" % len(third))
    print("WHERE A MOD WINS THE LOAD : %d" % len(losing))
    for i, p in losing:
        ours = [q for q, m in supply[i] if m]
        note = ("we ship it in %s but that loses"
                % os.path.basename(ours[0])) if ours else "we do not ship it"
        print("   0x%08X  winner=%s   (%s)" % (i, os.path.basename(p), note))

    if losing:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "gap3.txt")
        with open(out, "w") as f:
            for i, p in losing:
                f.write("%08X\t%s\n" % (i, p))
        print("\nwrote %d -> %s" % (len(losing), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
