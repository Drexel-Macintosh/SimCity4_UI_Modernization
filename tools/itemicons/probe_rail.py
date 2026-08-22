#!/usr/bin/env python3
r"""Which TGI is the Rail button, and is our override for it actually visible?

The first blank-sweep tested ALPHA only. An opaque near-black strip passes that
test and still reads as "invisible" on screen, so the clean result proved less
than it looked. This adds a luminance/variance check and dumps the icon set
NAM's RealRailway pack ships, which is where the Rail button's art comes from.
"""
import os
import struct
import sys

from PIL import Image, ImageStat

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
            f.seek(off)
            blob = f.read(count * 20)
            for i in range(count):
                yield struct.unpack_from("<IIIII", blob, i * 20)
    except (OSError, struct.error):
        return


def main():
    print("=== icons shipped by RealRailway_Icons.dat (the rail button's pack) ===")
    rail_tgis = []
    for root, _d, files in os.walk(PLUGINS):
        for fn in files:
            if fn != "RealRailway_Icons.dat":
                continue
            p = os.path.join(root, fn)
            for t, g, i, _o, _s in index(p):
                if t == PNG_TYPE and g == ICON_GROUP:
                    rail_tgis.append(i)
    rail_tgis = sorted(set(rail_tgis))
    print("   %d icon TGIs: %s"
          % (len(rail_tgis), ", ".join("0x%08X" % i for i in rail_tgis)))

    print("\n=== do WE override each, and is our 2x art visibly non-empty? ===")
    up = os.path.join(HERE, "nam-up-2")
    for i in rail_tgis:
        name = "T-0x%08x_G-0x%08x_I-0x%08x.png" % (PNG_TYPE, ICON_GROUP, i)
        p = os.path.join(up, name)
        if not os.path.isfile(p):
            print("   0x%08X  NOT OVERRIDDEN by us" % i)
            continue
        im = Image.open(p).convert("RGBA")
        w, h = im.size
        cw = w // 4
        cell = im.crop((0, 0, cw, h))          # the NORMAL state - what you see
        a = cell.getchannel("A")
        rgb = cell.convert("RGB")
        st = ImageStat.Stat(rgb, mask=a)
        mean = sum(st.mean) / 3 if a.getextrema()[1] else 0
        opaque = sum(1 for px in a.getdata() if px > 8)
        pct = 100.0 * opaque / (cw * h)
        flag = ""
        if pct < 2:
            flag = "  <-- effectively EMPTY"
        elif mean < 18:
            flag = "  <-- near-BLACK"
        print("   0x%08X  cell %dx%d  opaque %5.1f%%  mean-lum %5.1f%s"
              % (i, cw, h, pct, mean, flag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
