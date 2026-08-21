#!/usr/bin/env python3
r"""Census + extract the ItemIcons shipped by PLUGINS that we do NOT yet override.

WHY (2026-08-05, task #139). With NAM installed the transport flyouts show each
button icon TWICE, and hovering blanks it. TRIAGE.md:23 names the family:
a MULTI-STATE STRIP at 1x inside a doubled cell. ITEMICONS.md:24 gives the
mechanism - every ItemIcon is a 176x44 FOUR-STATE strip (44x44 normal / hover /
pressed / disabled) and the button picks a cell by imageWidth/4. Double the cell
but not the strip and two 1x states show at once; hover indexes past the art and
draws nothing.

    ItemIcon TGI = { type 0x856DDBAC, group 0x6A386D26, instance = <Item Icon> }

!! COVERAGE MUST BE MEASURED AGAINST OUR SHIPPED PACKAGES, NOT A STAGING DIR.
The first version of this script asked "is there a PNG in tools\upscale\preview"
and also counted our own root dat as a plugin - both wrong, and it reported 480
missing when the real gap is 381. Ours are identified by the `z_SC4UIScale_`
filename prefix and excluded from the plugin side.

!! LOAD ORDER decides where the fix can live. Root Plugins FILES load before
SUBFOLDERS (ScaleTier.cpp:669), so our root ItemIcons dat can never override a
mod that lives in a subfolder. NAM is `770-network-addon-mod\`, so the override
must ship from `zzz-SC4UIScale\` - which sorts after `770-`. Same reason
ItemIconsSub exists for the submenus mod's 55.

    python scan_thirdparty_icons.py                 census only
    python scan_thirdparty_icons.py --extract OUT   dump the uncovered 1x PNGs
    python scan_thirdparty_icons.py --only 770      restrict to one mod folder

Read-only with respect to the game and the plugins.
"""
import argparse
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


def read_index(path):
    """Yield (type, group, instance, offset, size). DBPF 1.0 / index 7.0."""
    try:
        with open(path, "rb") as f:
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", metavar="OUTDIR")
    ap.add_argument("--only", help="restrict to plugin folders containing this")
    ap.add_argument("--plugins", default=PLUGINS)
    a = ap.parse_args()

    ours = set()                       # icon TGIs WE already override
    theirs = defaultdict(dict)         # mod folder -> {instance: (path, off, size)}
    # Every DBPF container that can legally hold art at an icon TGI (#49).
    DBPF_EXTS = (".dat", ".sc4lot", ".sc4desc", ".sc4model")
    n_dats = 0

    for root, _dirs, files in os.walk(a.plugins):
        for fn in files:
            # #49's STANDING RULE, finally applied to this tool (2026-08-14).
            # .SC4Lot / .SC4Desc / .SC4Model are ALL DBPF archives and any of
            # them can supply art at an icon TGI. Globbing "*.dat" is what made
            # the Grutzehaus sweep report "no art anywhere" for five landmarks
            # whose 176x44 strips were sitting inside .SC4Lot files, and it is
            # why this scanner reported 0 uncovered icons for a custom lot whose
            # icon it could not physically see. An extension-filtered audit that
            # reports absence is not evidence of absence.
            if not fn.lower().endswith(DBPF_EXTS):
                continue
            p = os.path.join(root, fn)
            n_dats += 1
            mine = fn.startswith(OURS_PREFIX)
            top = os.path.relpath(p, a.plugins).split(os.sep)[0]
            for t, g, i, off, size in read_index(p):
                if t != PNG_TYPE or g != ICON_GROUP:
                    continue
                if mine:
                    ours.add(i)
                else:
                    theirs[top].setdefault(i, (p, off, size))

    print("scanned %d DBPF containers %s" % (n_dats, str(DBPF_EXTS)))
    print("our override packages already supply %d icon TGIs\n" % len(ours))

    gap_all = {}
    for top in sorted(theirs, key=lambda x: -len(theirs[x])):
        icons = theirs[top]
        gap = {i: v for i, v in icons.items() if i not in ours}
        print("  %-28s %4d icons   covered %4d   GAP %4d"
              % (top, len(icons), len(icons) - len(gap), len(gap)))
        if a.only and a.only not in top:
            continue
        gap_all.update(gap)

    label = ("matching '%s'" % a.only) if a.only else "across all plugins"
    print("\nUNCOVERED %s: %d icon(s) - these are what tile 2-up in a doubled cell"
          % (label, len(gap_all)))
    if not gap_all:
        return 0

    if not a.extract:
        print("(re-run with --extract OUTDIR to dump them)")
        return 0

    os.makedirs(a.extract, exist_ok=True)
    ok = 0
    skipped = []
    for inst in sorted(gap_all):
        p, off, size = gap_all[inst]
        with open(p, "rb") as f:
            f.seek(off)
            blob = f.read(size)
        # Only raw PNG can be upscaled directly. A QFS-compressed entry would
        # need decompressing first - report it rather than silently dropping it
        # (a silent cap reads as "covered everything" when it did not).
        if blob[:8] != b"\x89PNG\r\n\x1a\n":
            skipped.append((inst, os.path.basename(p)))
            continue
        name = "T-0x%08x_G-0x%08x_I-0x%08x.png" % (PNG_TYPE, ICON_GROUP, inst)
        with open(os.path.join(a.extract, name), "wb") as f:
            f.write(blob)
        ok += 1

    print("\nextracted %d PNG(s) -> %s" % (ok, a.extract))
    if skipped:
        # QFS-compressed entries need DbpfExtract.exe (it decompresses); this
        # scanner deliberately does NOT silently drop them - see law "no silent caps".
        print("!! %d NOT raw PNG (QFS) - use DbpfExtract.exe for these:" % len(skipped))
        for inst, src in skipped[:10]:
            print("     0x%08X in %s" % (inst, src))
    return 0


if __name__ == "__main__":
    sys.exit(main())
