#!/usr/bin/env python3
"""Compare Carbon PNG payload dimensions against our SelectiveArt/DialogStatic
payloads for every shared instance ID. Ratio 1.5 on both axes proves Carbon art
is authored at stock 1x dimensions and our x-factor pipeline applies cleanly."""
import os
import struct
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
CARBON_DIRS = ["scoty_carbon_PNG", "scoty_Carbon_Files",
               "w_scoty_Carbon_CB_SaveWarning_optA", "w_scoty_Carbon_SubMenu-Essential",
               "y_scoty_CAM_Extended_Essentials", "y_scoty_Carbon_NAM",
               "z_scoty_Carbon_BuildingStyles"]


def png_dim(p):
    with open(p, "rb") as f:
        d = f.read(33)
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", d[16:24])
    return (w, h)


def tgi_of(fn):
    # T-0x856DDBAC_G-0x1ABE787D_I-0x0C0E0F3C.bin
    parts = fn[:-4].split("_")
    return tuple(p.split("-")[1].lower() for p in parts)


def load_dir(d):
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        if fn.endswith(".bin"):
            out[tgi_of(fn)] = os.path.join(d, fn)
    return out


def main():
    ours_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "extracted", "_ours-selective")
    ours = load_dir(ours_dir)
    carbon = {}
    for cd in CARBON_DIRS:
        carbon.update(load_dir(os.path.join(BASE, "extracted", cd)))

    both = sorted(set(carbon) & set(ours))
    png_both = [t for t in both if t[0] == "0x856ddbac"]
    print("shared TGIs with %s: %d (%d PNG)" % (os.path.basename(ours_dir), len(both), len(png_both)))

    ratios = {}
    bad = []
    for t in png_both:
        cd = png_dim(carbon[t])
        od = png_dim(ours[t])
        if not cd or not od:
            bad.append((t, "non-PNG payload", cd, od))
            continue
        r = (round(od[0] / cd[0], 3), round(od[1] / cd[1], 3))
        ratios.setdefault(r, []).append((t, cd, od))

    for r, items in sorted(ratios.items(), key=lambda kv: -len(kv[1])):
        t, cd, od = items[0]
        print("ratio %-14s x%-4d e.g. %s carbon=%s ours=%s" % (r, len(items), t[2], cd, od))
    for b in bad[:10]:
        print("BAD:", b)


if __name__ == "__main__":
    main()
