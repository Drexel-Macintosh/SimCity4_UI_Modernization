#!/usr/bin/env python3
"""Stage the Carbon Skin's WINNING payloads, decompressed, into one tree.

Rules measured 2026-08-25:
- Only the KEEP dats participate (add-ons whose target mod is installed).
- Within z__Scoty_Carbon_Skin the game loads dats alphabetically
  (case-insensitive), LAST wins - so add-on redeclarations (w_/y_/z_)
  override the core skin. We resolve the same order here.
- Payloads may be QFS/RefPack-compressed (Files.dat is; DIR entry type
  0xE86B1EEF present). Decode via tools/uimap/emu/qfs_ab.qfs.

Output: extracted-plain/T-..._G-..._I-....bin (decompressed winner payloads)
        extracted-plain/MANIFEST.txt (tgi, source dat, kind, sizes)
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(BASE))) if BASE.endswith("carbon") else BASE
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(BASE)), "uimap", "emu"))
from qfs_ab import qfs  # noqa: E402

KEEP = [
    # game-load alphabetical order, case-insensitive: last wins
    "scoty_Carbon_Files", "scoty_Carbon_FSH", "scoty_carbon_PNG",
    "scoty_Carbon_Txt", "scoty_Carbon_Txt_NoLatin",
    "w_scoty_Carbon_CB_SaveWarning_optA",
    "w_scoty_Carbon_SubMenu-Essential",
    "y_scoty_CAM_Extended_Essentials",
    "y_scoty_Carbon_NAM",
    # un-pruned 2026-08-25: user installed region-view-census-ui + warrior's
    # god-terraforming; both carbon add-ons re-kept.
    "y_scoty_Carbon_RegionCensusDLL",
    "z_scoty_Carbon_BuildingStyles",
    "z_scoty_Carbon_GodMod",
]


def kind_of(b):
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    head = b[:256].lstrip(b"\xef\xbb\xbf \t\r\n")
    if head.startswith(b"#") or head.startswith(b"<"):
        return "UI-text"
    if len(b) >= 2 and b[0] in (0,) and b[1] == 0:
        return "LTEXT?"
    return "bin"


def main():
    src_root = os.path.join(BASE, "extracted")
    out_root = os.path.join(BASE, "extracted-plain")
    os.makedirs(out_root, exist_ok=True)

    winner = {}   # filename -> (datbase, payload_path)
    order = sorted(KEEP, key=str.lower)
    for datbase in order:            # later assignment = later dat = winner
        d = os.path.join(src_root, datbase)
        for fn in os.listdir(d):
            if fn.endswith(".bin"):
                winner[fn] = (datbase, os.path.join(d, fn))

    rows = []
    ndec = 0
    for fn in sorted(winner):
        datbase, p = winner[fn]
        raw = open(p, "rb").read()
        plain = qfs(raw)
        if plain is not None:
            ndec += 1
        else:
            plain = raw
        with open(os.path.join(out_root, fn), "wb") as f:
            f.write(plain)
        rows.append("%-52s %-38s %-8s raw=%-7d plain=%d" % (
            fn[:-4], datbase, kind_of(plain), len(raw), len(plain)))

    with open(os.path.join(out_root, "MANIFEST.txt"), "w", encoding="utf-8") as f:
        f.write("# Carbon winning payloads, decompressed. %d TGIs, %d were QFS.\n"
                % (len(winner), ndec))
        f.write("\n".join(rows) + "\n")
    print("staged %d payloads (%d QFS-decoded) -> %s" % (len(winner), ndec, out_root))

    # kind profile
    from collections import Counter
    prof = Counter(r.split()[2] for r in rows)
    print("kinds:", dict(prof))


if __name__ == "__main__":
    main()
