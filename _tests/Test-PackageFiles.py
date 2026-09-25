"""Test-PackageFiles.py - the one package list stays the one list (audit B12).

    python _tests/Test-PackageFiles.py

_packaging/PackageFiles.psd1 names every file a working install holds, and
both _tests/Deploy-OnGameClose.ps1 and _packaging/Build-Dist.ps1 copy from it.
This gate checks:
  1. every row parses: Src, Dir (plug/our/zzz), Name, and only known flags -
     and the parsed count equals the number of rows in the file, so a row
     written in another shape fails instead of vanishing;
  2. no two rows write the same destination; exactly one Selector row;
  3. tier names follow the arming convention: a -15x or -3x .dat ships
     .x1-disabled, a -2x .dat ships armed (the CsiIcons rows once shipped
     inverted, 2026-08-18, and every gate asked only "is it present?"). The
     SelectiveArt tier sources are the documented exception: all three ship
     suffixed and the DLL copies one onto the stable name;
  4. both scripts read the list, and neither carries a literal
     `Copy-Item "$proj\\...` package line that would bypass it.
A negative control re-runs check 3 on a copy with one row inverted and must
see it fail.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(REPO, "_packaging", "PackageFiles.psd1")
DEPLOY = os.path.join(REPO, "_tests", "Deploy-OnGameClose.ps1")
BUILD = os.path.join(REPO, "_packaging", "Build-Dist.ps1")

ROW = re.compile(r"@\{\s*Src\s*=\s*'([^']+)';\s*Dir\s*=\s*'([^']+)';\s*Name\s*=\s*'([^']+)'"
                 r"((?:\s*;\s*\w+\s*=\s*\$true)*)\s*\}")
FLAGS = {"Optional", "Carbon", "Selector", "DeployOnly"}
# SelectiveArt: all three tier sources are permanently suffixed (v4.0.3 stable
# filename); the DLL's SyncDatStable copies the right one onto the stable name.
SUFFIXED_2X = {"z_SC4UIScale_SelectiveArt-2x.dat.x1-disabled"}


def parse(text):
    rows = []
    for m in ROW.finditer(text):
        flags = set(re.findall(r"(\w+)\s*=\s*\$true", m.group(4)))
        rows.append({"Src": m.group(1), "Dir": m.group(2), "Name": m.group(3), "flags": flags})
    return rows


def tier_errors(rows):
    bad = []
    for r in rows:
        n = r["Name"]
        m = re.search(r"-(15x|2x|3x)\.dat(\.x1-disabled)?$", n)
        if not m:
            continue
        tier, disabled = m.group(1), bool(m.group(2))
        if tier in ("15x", "3x") and not disabled:
            bad.append("%s: a %s tier must ship .x1-disabled" % (n, tier))
        if tier == "2x" and disabled and n not in SUFFIXED_2X:
            bad.append("%s: the 2x tier ships armed" % n)
    return bad


def main():
    fails = []
    text = open(LIST, encoding="utf-8").read()
    rows = parse(text)
    declared = len(re.findall(r"^\s*@\{\s*Src\s*=", text, re.M))
    print("rows parsed: %d, rows in the file: %d" % (len(rows), declared))
    if not rows or len(rows) != declared:
        fails.append("parsed %d of %d rows - a row is written in a shape this gate "
                     "(and a reader) cannot see" % (len(rows), declared))
    # 1. fields
    for r in rows:
        if r["Dir"] not in ("plug", "our", "zzz"):
            fails.append("%s: Dir %r is not plug/our/zzz" % (r["Name"], r["Dir"]))
        if r["flags"] - FLAGS:
            fails.append("%s: unknown flag(s) %s" % (r["Name"], sorted(r["flags"] - FLAGS)))
        if r["Dir"] == "plug" and not r["Name"].lower().endswith(".dll"):
            fails.append("%s: only the DLL belongs at the Plugins root" % r["Name"])
    # 2. destinations
    seen = {}
    for r in rows:
        key = (r["Dir"], r["Name"].lower())
        if key in seen:
            fails.append("%s/%s is written by two rows" % key)
        seen[key] = r
    sel = [r for r in rows if "Selector" in r["flags"]]
    if len(sel) != 1:
        fails.append("expected exactly one Selector row, found %d" % len(sel))
    # 3. tier naming, with its negative control
    fails += tier_errors(rows)
    inverted = [dict(r) for r in rows]
    for r in inverted:
        if r["Name"].endswith("-15x.dat.x1-disabled"):
            r["Name"] = r["Name"][:-len(".x1-disabled")]
            break
    if not tier_errors(inverted):
        fails.append("NEGATIVE CONTROL: an inverted 15x row passed the tier check")
    else:
        print("negative control: an inverted 15x row is rejected, as required")
    # 4. both scripts read the list, neither bypasses it
    for path in (DEPLOY, BUILD):
        src = open(path, encoding="utf-8").read()
        rel = os.path.relpath(path, REPO)
        if "PackageFiles.psd1" not in src or "Import-PowerShellDataFile" not in src:
            fails.append("%s does not read _packaging/PackageFiles.psd1" % rel)
        lit = re.findall(r'^\s*Copy-Item\s+(?:-Path\s+)?"\$proj\\', src, re.M)
        if lit:
            fails.append("%s has %d literal Copy-Item \"$proj\\...\" line(s): add the "
                         "file to _packaging/PackageFiles.psd1 instead" % (rel, len(lit)))
    counts = (len(rows), sum(1 for r in rows if "DeployOnly" not in r["flags"]),
              sum(1 for r in rows if "Carbon" in r["flags"]))
    if fails:
        print("\n".join("FAIL: " + f for f in fails))
        print("OVERALL: FAIL")
        return 1
    print("OVERALL: PASS (%d rows, %d in the bundle, %d Carbon; one list, both scripts read it)" % counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
