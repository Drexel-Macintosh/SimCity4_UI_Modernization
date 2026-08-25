#!/usr/bin/env python3
r"""Generate the ZCarbon enrollment tables from the measured collision data.

Inputs (all already on disk, produced by the carbon analysis arc):
- _tests\captures\2026-08-25-carbon\carbon-vs-ours-intersection.txt
  (494 colliding TGIs with ours=/carbon= source attribution)
- tools\research\carbon\builder-inputs\thirdparty-src\*.ui   (206, winner-resolved)
- tools\research\carbon\builder-inputs\thirdparty-art\*.png  (404, winner-resolved)
- the live packages' own TGI lists (via DbpfPack --list) for clone analysis
- tools\selective-safe\refmap-15x.csv (clone map: which shared refs were
  retargeted to clone TGIs = iid ^ 0x53430001)

Outputs -> tools\research\carbon\enrollment\:
- enrollment.json   the machine tables, keyed by target package
- ENROLLMENT.md     the human report (counts, ownership moves, clone set)

Package assignment law (one package per owning SOURCE DAT, so the gate can
mirror reality):
  scoty_Carbon_Files/scoty_carbon_PNG      -> ZCarbonUI (dialog-static
                                              targets) / ZCarbonArt
                                              (selective-safe targets)
  w_scoty_Carbon_CB_SaveWarning_optA       -> ZCarbonSaveWarning
  y_scoty_CAM_Extended_Essentials          -> ZCarbonCamUI
  z_scoty_Carbon_BuildingStyles            -> ZCarbonStyles
  w_scoty_Carbon_SubMenu-Essential         -> ZCarbonSubmenus (if any collide)
  y_scoty_Carbon_NAM                       -> ZCarbonNam (if any collide)
Art follows its referencing script's package where owned; core art with no
add-on owner goes with the builder that stages that TGI today (ours= column).
"""
import json
import os
import re
import struct
import subprocess
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
CAP = os.path.join(PROJ, "_tests", "captures", "2026-08-25-carbon")
INTER = os.path.join(CAP, "carbon-vs-ours-intersection.txt")
SRC = os.path.join(BASE, "builder-inputs", "thirdparty-src")
ART = os.path.join(BASE, "builder-inputs", "thirdparty-art")
OUT = os.path.join(BASE, "enrollment")
DBPF = os.path.join(PROJ, "tools", "dbpf", "DbpfPack.exe")
PLUG = os.path.join(os.environ["USERPROFILE"], "OneDrive", "Documents",
                    "SimCity 4", "Plugins")
REFMAP = os.path.join(PROJ, "tools", "selective-safe", "refmap-15x.csv")
CLONE_XOR = 0x53430001

# carbon source dat -> target package (add-on-sourced entries)
ADDON_PKG = {
    "w_scoty_Carbon_CB_SaveWarning_optA": "ZCarbonSaveWarning",
    "y_scoty_CAM_Extended_Essentials": "ZCarbonCamUI",
    "z_scoty_Carbon_BuildingStyles": "ZCarbonStyles",
    "w_scoty_Carbon_SubMenu-Essential": "ZCarbonSubmenus",
    "y_scoty_Carbon_NAM": "ZCarbonNam",
    # 2026-08-25 (user installed warrior + region-census): GodMod redeclares
    # exactly WarriorUI's four TGIs -> its own Z-late package. The
    # RegionCensus dat is one .UI in the census DLL's private group
    # 0x9CB6053F - zero overlap with us, no package (un-pruned only).
    "z_scoty_Carbon_GodMod": "ZCarbonGodMod",
}
# ZCarbonIcons already covers these instances (built package) - exclude.
ICONS_DONE = {0x4BB1305D, 0x4BB1305E, 0x4BB1305F, 0x4BB13060,
              0x0C0305C3, 0x0C0305C4, 0x0C0305C5, 0x0C0305C6,
              0x00001111, 0x144161EC}
WEBTEXT_SKIP = {(0x2026960B, 0x6A231EAA, 0x0A5128F3)}  # deliberate no-build

ROW = re.compile(r"^0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8})"
                 r"\s+(OURS|CARBON)\s+ours=(\S+)\s+carbon=(\S+)")


def carbon_winner_pkg(carbon_dats):
    """Package for a TGI given the carbon dats that declare it (the LAST in
    load order is the winning source)."""
    winner = sorted(carbon_dats, key=str.lower)[-1]
    return ADDON_PKG.get(winner), winner


def list_dat(path):
    out = subprocess.run([DBPF, "--list", path], capture_output=True,
                         text=True, errors="replace").stdout
    rows = []
    for line in out.splitlines():
        m = re.match(r"^0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8})", line.strip())
        if m:
            rows.append((int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)))
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for line in open(INTER, encoding="utf-8"):
        m = ROW.match(line.strip())
        if m:
            t, g, i = int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)
            rows.append({
                "t": t, "g": g, "i": i,
                "ours": m.group(5).split(";"),
                "carbon": m.group(6).split(";"),
            })
    # Floor, not an exact pin: the collision set grows as the user installs
    # more of Carbon's target mods (494 measured 2026-08-25 with 10 kept
    # dats; +GodMod/RegionCensus moved it). A parse far below the floor
    # means the intersection file format drifted, not the tree.
    if len(rows) < 400:
        print("FATAL: parsed only %d intersection rows - the census file "
              "format has drifted" % len(rows))
        sys.exit(1)

    # sanity: every colliding payload exists in builder-inputs
    missing = []
    for r in rows:
        if r["t"] == 0x00000000:
            p = os.path.join(SRC, "T-00000000_G-%08x_I-%08x.ui" % (r["g"], r["i"]))
        elif r["t"] == 0x856DDBAC:
            p = os.path.join(ART, "T-856ddbac_G-%08x_I-%08x.png" % (r["g"], r["i"]))
        else:
            continue
        if not os.path.isfile(p):
            missing.append(p)
    if missing:
        print("FATAL: %d colliding payloads missing from builder-inputs, e.g. %s"
              % (len(missing), missing[0]))
        sys.exit(1)

    # classify each row
    pkgs = defaultdict(lambda: {"scripts": [], "art": []})
    moves = []      # ownership notes: TGIs the existing TP packages claim
    skipped = []
    for r in rows:
        tgi = (r["t"], r["g"], r["i"])
        if tgi in WEBTEXT_SKIP:
            skipped.append((tgi, "WebText - deliberate carbon win"))
            continue
        if r["t"] == 0x856DDBAC and r["i"] in ICONS_DONE:
            skipped.append((tgi, "covered by built ZCarbonIcons"))
            continue
        addon_pkg, winner_dat = carbon_winner_pkg(r["carbon"])
        ours = ";".join(r["ours"])
        if addon_pkg:
            pkg = addon_pkg
        elif r["t"] == 0x00000000:
            pkg = ("ZCarbonUI" if "DialogStatic" in ours else "ZCarbonArt")
        else:
            pkg = ("ZCarbonArt" if "SelectiveArt" in ours
                   else "ZCarbonUI" if "DialogStatic" in ours
                   else "ZCarbonArt")
        kind = "scripts" if r["t"] == 0x00000000 else "art"
        pkgs[pkg][kind].append({
            "g": "%08x" % r["g"], "i": "%08x" % r["i"],
            "carbon_src": winner_dat, "ours": r["ours"],
        })
        if any(("CamUI" in o or "SaveWarningUI" in o or "ThirdPartyUI" in o
                or "ItemIconsSub" in o or "CsiIcons" in o) for o in r["ours"]):
            moves.append((tgi, pkg, r["ours"]))

    # clone analysis: which clone TGIs do root scripts reference whose SOURCE
    # art carbon owns? Those clone TGIs need carbon-scaled pixels in the same
    # package as the script that references them.
    # ⛔ THIS PASS WAS A FALSE NULL AND SHIPPED ONE (2026-08-25 adversarial
    # sweep). The old matcher tested `"gid" in k` / `"iid" in k` against the
    # REAL header `TypeID,GroupID,InstanceID,...` - "gid" is NOT a substring
    # of "groupid" and "iid" is NOT a substring of "instanceid", so every row
    # fell out at `if not gid or not iid: continue` and the report printed
    # "clone TGIs needing carbon pixels: 0" forever. Eleven stock-styled
    # clone sheets shipped inside carbon dialogs behind that zero.
    # NULL IS NOT EVIDENCE: this pass now asserts its own positive control -
    # it must SEE clone rows at all, or it refuses rather than reporting none.
    # "Carbon owns this art" = CARBON SHIPS THE PAYLOAD, which is a superset
    # of "it collides with our packages". Keying the clone pass on the
    # collision set missed e2b66db8 - carbon restyles it, but it was not in
    # the intersection, so its clone kept stock pixels inside a carbon
    # dialog. The file on disk is the authority (same test the dialog-static
    # lane uses).
    carbon_art_iids = set()
    for fn in os.listdir(ART):
        if fn.lower().startswith("t-856ddbac_g-") and fn.lower().endswith(".png"):
            try:
                parts = fn[:-4].split("_")
                carbon_art_iids.add((int(parts[1].split("-")[1], 16),
                                     int(parts[2].split("-")[1], 16)))
            except (IndexError, ValueError):
                continue
    if not carbon_art_iids:
        print("FATAL: zero carbon art payloads found in %s - the clone pass "
              "would report a false zero" % ART)
        sys.exit(1)
    clones = []
    if os.path.isfile(REFMAP):
        import csv
        n_clone_rows = 0
        with open(REFMAP, newline="", encoding="utf-8", errors="replace") as f:
            rd = csv.DictReader(f)
            need = {"GroupID", "InstanceID", "action", "clone_InstanceID"}
            missing = need - set(rd.fieldnames or [])
            if missing:
                print("FATAL: refmap header changed - missing columns %s; the "
                      "clone pass cannot measure and must not report zero"
                      % sorted(missing))
                sys.exit(1)
            for rec in rd:
                act = (rec.get("action") or "").strip()
                if not act.startswith("clone"):
                    continue
                n_clone_rows += 1
                try:
                    g = int(rec["GroupID"], 16)
                    i = int(rec["InstanceID"], 16)
                    ci = int(rec["clone_InstanceID"], 16)
                except (ValueError, TypeError):
                    continue
                # INT keys both sides - carbon_art_iids is built from the
                # parsed intersection rows, which hold ints. (The first
                # repair of this pass compared hex strings to ints and
                # produced a SECOND false zero; the positive control above
                # is what exposed it.)
                if (g, i) in carbon_art_iids:
                    clones.append({"g": "%08x" % g, "src_i": "%08x" % i,
                                   "clone_i": "%08x" % ci})
        # POSITIVE CONTROL: the refmap is known to carry clone+retarget rows
        # (12 at every tier as of 2026-08-25). Zero rows SEEN means the
        # instrument is blind again, not that there are no clones.
        if n_clone_rows == 0:
            print("FATAL: clone pass saw ZERO clone rows in %s - the action "
                  "vocabulary changed and this pass is blind (it reported a "
                  "false zero once already)" % REFMAP)
            sys.exit(1)
        print("clone pass: %d clone rows read, %d carbon-owned"
              % (n_clone_rows, len(clones)))
    else:
        print("note: refmap-15x.csv absent; clone pass deferred to the builder")

    result = {
        "generated": "2026-08-25",
        "packages": {k: {"scripts": sorted(v["scripts"], key=lambda x: x["i"]),
                         "art": sorted(v["art"], key=lambda x: x["i"]),
                         "n_scripts": len(v["scripts"]), "n_art": len(v["art"])}
                     for k, v in sorted(pkgs.items())},
        "clones_carbon_sourced": clones,
        "skipped": [{"tgi": "%08x/%08x/%08x" % t, "why": w} for t, w in skipped],
        "ownership_moves": [{"tgi": "%08x/%08x/%08x" % t, "to": p, "ours": o}
                            for t, p, o in moves],
    }
    with open(os.path.join(OUT, "enrollment.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)

    lines = ["# ZCarbon enrollment (generated %s)" % result["generated"], ""]
    total_s = total_a = 0
    for pkg, v in sorted(result["packages"].items()):
        lines.append("- **%s**: %d scripts + %d art" % (pkg, v["n_scripts"], v["n_art"]))
        total_s += v["n_scripts"]; total_a += v["n_art"]
    lines.append("")
    lines.append("total: %d scripts + %d art (+18 in built ZCarbonIcons; %d skipped)"
                 % (total_s, total_a, len(skipped)))
    lines.append("clone TGIs needing carbon pixels: %d" % len(clones))
    lines.append("")
    lines.append("## Ownership moves (TGIs the existing gated packages claim)")
    for mv in result["ownership_moves"]:
        lines.append("- %s -> %s (ours: %s)" % (mv["tgi"], mv["to"], ";".join(mv["ours"])))
    with open(os.path.join(OUT, "ENROLLMENT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines[:12]))
    print("wrote %s" % os.path.join(OUT, "enrollment.json"))


if __name__ == "__main__":
    main()
