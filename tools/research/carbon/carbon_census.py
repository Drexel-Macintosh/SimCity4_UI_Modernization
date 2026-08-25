#!/usr/bin/env python3
"""Carbon Skin vs SC4UIScale per-TGI intersection census.

Parses the DbpfPack --list captures of every Scoty Carbon Skin 1.5 dat
(_tests/captures/2026-08-25-carbon/*.tgi.txt), enumerates our live armed
packages (010-SC4UIScale + zzz-SC4UIScale), and reports every TGI both
sides declare, with the folder-order winner for the proposed placement
(010-SC4UIScale < z____scoty_mods < zzz-SC4UIScale).

Offline by construction: reads dats and captures, launches nothing.
"""
import os
import re
import subprocess
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DBPF = os.path.join(REPO, "tools", "dbpf", "DbpfPack.exe")
CAP = os.path.join(REPO, "_tests", "captures", "2026-08-25-carbon")
PLUG = os.path.join(os.environ["USERPROFILE"], "OneDrive", "Documents", "SimCity 4", "Plugins")

ROW = re.compile(r"^0x([0-9A-Fa-f]{8})\s+0x([0-9A-Fa-f]{8})\s+0x([0-9A-Fa-f]{8})\s+0x[0-9A-Fa-f]+\s+(\d+)")

# Carbon dats whose target mod is installed on this machine (measured
# 2026-08-25: both Plugins trees swept; Steam tree empty).
KEEP = {
    "scoty_Carbon_Files", "scoty_Carbon_FSH", "scoty_carbon_PNG",
    "scoty_Carbon_Txt", "scoty_Carbon_Txt_NoLatin",
    "w_scoty_Carbon_CB_SaveWarning_optA",
    "w_scoty_Carbon_SubMenu-Essential",
    "y_scoty_CAM_Extended_Essentials",
    "y_scoty_Carbon_NAM",
    # un-pruned 2026-08-25: user installed region-view-census-ui + warrior's
    # god-terraforming-in-mayor-mode.
    "y_scoty_Carbon_RegionCensusDLL",
    "z_scoty_Carbon_BuildingStyles",
    "z_scoty_Carbon_GodMod",
}

TYPE_NAMES = {
    0x00000000: "UI script",
    0x2026960B: "LTEXT",
    0x856DDBAC: "PNG",
    0x7AB50E44: "FSH",
    0x00000600: "INI/cursor?",
    0xCA63E2A3: "LUA",
    0x29A5D1EC: "exemplar-cohort?",
    0x6534284A: "exemplar",
    0x05342861: "cohort",
    0xEA5118B0: "effect-dir",
}


def parse_capture(path):
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = ROW.match(line.strip())
            if m:
                t, g, i, size = (int(m.group(1), 16), int(m.group(2), 16),
                                 int(m.group(3), 16), int(m.group(4)))
                rows.append(((t, g, i), size))
    return rows


def list_dat(path):
    out = subprocess.run([DBPF, "--list", path], capture_output=True,
                         text=True, errors="replace").stdout
    rows = []
    for line in out.splitlines():
        m = ROW.match(line.strip())
        if m:
            rows.append(((int(m.group(1), 16), int(m.group(2), 16),
                          int(m.group(3), 16)), int(m.group(4))))
    return rows


def tname(t):
    return TYPE_NAMES.get(t, "0x%08X" % t)


def main():
    # 1. Carbon side, from the captures
    carbon = defaultdict(list)   # tgi -> [datbase]
    carbon_kept = defaultdict(list)
    for fn in sorted(os.listdir(CAP)):
        if not fn.endswith(".tgi.txt"):
            continue
        base = fn[:-8]
        for tgi, size in parse_capture(os.path.join(CAP, fn)):
            carbon[tgi].append(base)
            if base in KEEP:
                carbon_kept[tgi].append(base)

    # 2. Our side, live enumeration - ARMED AND DISARMED both. A gate-dark
    # package (.dat.x1-disabled, e.g. WarriorUI before its mod arrived) is
    # still ours and still collides the day its gate opens; the first census
    # missed the GodMod<->WarriorUI overlap exactly this way (2026-08-25).
    ours = defaultdict(list)     # tgi -> [relpath]
    for sub in ("010-SC4UIScale", "zzz-SC4UIScale"):
        d = os.path.join(PLUG, sub)
        for fn in sorted(os.listdir(d)):
            low = fn.lower()
            if not (low.endswith(".dat") or low.endswith(".dat.x1-disabled")):
                continue
            rel = sub + "\\" + fn
            for tgi, size in list_dat(os.path.join(d, fn)):
                ours[tgi].append(rel)

    print("Carbon TGIs total: %d unique (%d in kept dats)" % (len(carbon), len(carbon_kept)))
    print("Our TGIs total:    %d unique" % len(ours))

    # 3. Intersection, full drop and kept subset
    inter = sorted(set(carbon) & set(ours))
    inter_kept = sorted(set(carbon_kept) & set(ours))
    print("\nINTERSECTION (any Carbon dat): %d TGIs" % len(inter))
    print("INTERSECTION (kept dats only): %d TGIs" % len(inter_kept))

    # 4. Detail on the kept intersection: who wins where
    by_bucket = defaultdict(list)
    for tgi in inter_kept:
        our_files = ours[tgi]
        c_files = carbon_kept[tgi]
        # folder order: 010 < z____scoty_mods < zzz
        in_zzz = any(f.startswith("zzz-") for f in our_files)
        winner = "OURS(zzz)" if in_zzz else "CARBON"
        loser_side = "carbon art lost" if in_zzz else "OUR SCALED ART LOST"
        by_bucket[(tname(tgi[0]), winner)].append((tgi, our_files, c_files, loser_side))

    for (tn, winner), items in sorted(by_bucket.items()):
        print("\n--- type %-10s  winner=%s  (%d TGIs) ---" % (tn, winner, len(items)))
        pkg_count = defaultdict(int)
        for tgi, our_files, c_files, note in items:
            for f in our_files:
                pkg_count[f] += 1
        for f, n in sorted(pkg_count.items(), key=lambda kv: -kv[1]):
            print("    %4d  in %s" % (n, f))

    # 5. Full row dump for the record
    out = os.path.join(CAP, "carbon-vs-ours-intersection.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# Carbon(kept) x SC4UIScale intersection, %d rows\n" % len(inter_kept))
        f.write("# winner column assumes 010-SC4UIScale < z____scoty_mods < zzz-SC4UIScale\n")
        for tgi in inter_kept:
            in_zzz = any(p.startswith("zzz-") for p in ours[tgi])
            f.write("0x%08X 0x%08X 0x%08X  %-9s  ours=%s  carbon=%s\n" % (
                tgi[0], tgi[1], tgi[2],
                "OURS" if in_zzz else "CARBON",
                ";".join(ours[tgi]), ";".join(carbon_kept[tgi])))
        f.write("\n# TGIs in DELETED carbon dats that also hit ours: %d\n" % (len(inter) - len(inter_kept)))
        for tgi in sorted(set(inter) - set(inter_kept)):
            f.write("# pruned: 0x%08X 0x%08X 0x%08X carbon=%s ours=%s\n" % (
                tgi[0], tgi[1], tgi[2], ";".join(carbon[tgi]), ";".join(ours[tgi])))
    print("\nwrote %s" % out)

    # 6. Carbon-only profile: what does carbon carry per type (kept dats)
    prof = defaultdict(int)
    for tgi in carbon_kept:
        prof[tname(tgi[0])] += 1
    print("\nCarbon kept-dat type profile:")
    for tn, n in sorted(prof.items(), key=lambda kv: -kv[1]):
        print("    %5d  %s" % (n, tn))


if __name__ == "__main__":
    main()
