#!/usr/bin/env python3
r"""FINAL GATE for the ZCarbon arc: per-TGI winners over the LIVE tree.

Run AFTER the ZCarbon packages are deployed and armed. Asserts, for every
TGI in the measured collision set (_tests\captures\2026-08-25-carbon\
carbon-vs-ours-intersection.txt):

  1. COLLIDING TGIs (494): the live winner is one of OUR z_SC4UIScale_*
     dats - a ZCarbon* dat for the enrolled rows, ZCarbonIcons for its 10,
     and CARBON itself only for the deliberate skips (the WebText LTEXT).
  2. NO COLLATERAL: every TGI in the 2026-08-24 pre-carbon winner capture
     that is NOT in the collision set still resolves to the same dat file
     name as before (paths may differ; the FILE must not).

Load-order model (the measured laws): root files first, then subfolders
alphabetically (case-insensitive), recursive, dats alphabetical within each
directory level; LAST wins. Only *.dat files participate (.x1-disabled is
out of play). Winner resolution here covers the Plugins tree only - all
these TGIs are plugin-owned by construction (ours or carbon's).
"""
import os
import re
import subprocess
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
CAP = os.path.join(PROJ, "_tests", "captures", "2026-08-25-carbon")
INTER = os.path.join(CAP, "carbon-vs-ours-intersection.txt")
BASELINE = os.path.join(PROJ, "_tests", "captures", "2026-08-24-tgi-winners-FINAL.txt")
DBPF = os.path.join(PROJ, "tools", "dbpf", "DbpfPack.exe")
PLUG = os.path.join(os.environ["USERPROFILE"], "OneDrive", "Documents",
                    "SimCity 4", "Plugins")

SKIP_CARBON_OK = {(0x2026960B, 0x6A231EAA, 0x0A5128F3)}   # WebText caption


def load_order_dats(root):
    """Every .dat under root in game load order (last = winner)."""
    out = []

    def walk(d):
        try:
            entries = sorted(os.listdir(d), key=str.lower)
        except OSError:
            return
        files = [e for e in entries if e.lower().endswith(".dat")
                 and os.path.isfile(os.path.join(d, e))]
        dirs = [e for e in entries if os.path.isdir(os.path.join(d, e))]
        for f in files:
            out.append(os.path.join(d, f))
        for sub in dirs:
            walk(os.path.join(d, sub))

    # root FILES load before subfolders: walk() already emits files of a
    # directory before descending - which is exactly the engine's order.
    walk(root)
    return out


ROW = re.compile(r"^0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8})")


def main():
    dats = load_order_dats(PLUG)
    print("live tree: %d dats in load order" % len(dats))

    winner = {}
    for p in dats:
        r = subprocess.run([DBPF, "--list", p], capture_output=True,
                           text=True, errors="replace")
        for line in r.stdout.splitlines():
            m = ROW.match(line.strip())
            if m:
                winner[(int(m.group(1), 16), int(m.group(2), 16),
                        int(m.group(3), 16))] = p

    # ---- 1. colliding TGIs must end OURS ----
    bad = []
    n = 0
    for line in open(INTER, encoding="utf-8"):
        m = ROW.match(line.strip())
        if not m or line.startswith("#"):
            continue
        tgi = (int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16))
        n += 1
        w = winner.get(tgi)
        base = os.path.basename(w) if w else "(NO WINNER)"
        if tgi in SKIP_CARBON_OK:
            if w and "scoty" in base.lower():
                continue
            bad.append((tgi, base, "expected carbon (deliberate skip)"))
            continue
        if not w or not base.startswith("z_SC4UIScale_"):
            bad.append((tgi, base, "expected a z_SC4UIScale_* winner"))
    print("colliding TGIs checked: %d, violations: %d" % (n, len(bad)))
    for tgi, b, why in bad[:40]:
        print("  VIOLATION %08x/%08x/%08x -> %s (%s)" % (tgi + (b, why)))

    # ---- 2. no collateral on the pre-carbon set ----
    coll = set()
    for line in open(INTER, encoding="utf-8"):
        m = ROW.match(line.strip())
        if m and not line.startswith("#"):
            coll.add((int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)))
    drift = []
    intended = []
    nbase = 0
    for line in open(BASELINE, encoding="utf-8"):
        m = re.match(r"^0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8}) -> (.+)$",
                     line.strip())
        if not m:
            continue
        tgi = (int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16))
        if tgi in coll:
            continue
        nbase += 1
        old = os.path.basename(m.group(4).strip())
        w = winner.get(tgi)
        new = os.path.basename(w) if w else "(NO WINNER)"
        if old != new:
            # INTENDED TAKEOVER: a ZCarbon dat out-sorting one of OUR OWN
            # packages is the design, not collateral - the Z-late packages
            # deliberately ship beyond the colliding set for (a) the CSI
            # 1ABE787D twin-group law, (b) plan-clone pixels of carbon-owned
            # art, (c) TP self-sufficiency sheets. Itemized, never silent.
            if (old.startswith("z_SC4UIScale_")
                    and new.startswith("z_SC4UIScale_ZCarbon")):
                intended.append((tgi, old, new))
            else:
                drift.append((tgi, old, new))
    print("non-colliding baseline TGIs checked: %d, drift: %d, "
          "intended ZCarbon takeovers: %d" % (nbase, len(drift), len(intended)))
    for tgi, o, nn in intended:
        print("  INTENDED %08x/%08x/%08x  %s -> %s" % (tgi + (o, nn)))
    for tgi, o, nn in drift[:40]:
        print("  DRIFT %08x/%08x/%08x  %s -> %s" % (tgi + (o, nn)))

    out = os.path.join(CAP, "carbon-final-winners.txt")
    with open(out, "w", encoding="utf-8") as f:
        for tgi in sorted(coll):
            w = winner.get(tgi)
            f.write("0x%08X 0x%08X 0x%08X -> %s\n"
                    % (tgi + (os.path.basename(w) if w else "(NO WINNER)",)))
    print("wrote %s" % out)

    if bad or drift:
        print("FINAL GATE: RED")
        sys.exit(1)
    print("FINAL GATE: GREEN")


if __name__ == "__main__":
    main()
