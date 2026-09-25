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
     `Copy-Item "$proj\\...` package line that would bypass it;
  5. _tests/Test-DatIntegrity.ps1 reads the list too: it derives its
     deployed == built pairs from the rows (no hand-written pair table), and
     every entry-count row it keeps names a package the list deploys - the
     same check that suite makes at run time, made here without a Plugins tree.
     A Live row (the DLL rewrites it at boot) must be an untagged .dat with a
     tier-tagged sibling.
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
DATINT = os.path.join(REPO, "_tests", "Test-DatIntegrity.ps1")

ROW = re.compile(r"@\{\s*Src\s*=\s*'([^']+)';\s*Dir\s*=\s*'([^']+)';\s*Name\s*=\s*'([^']+)'"
                 r"((?:\s*;\s*\w+\s*=\s*\$true)*)\s*\}")
FLAGS = {"Optional", "Carbon", "Selector", "DeployOnly", "Live"}
# SelectiveArt: all three tier sources are permanently suffixed (v4.0.3 stable
# filename); the DLL's SyncDatStable copies the right one onto the stable name.
SUFFIXED_2X = {"z_SC4UIScale_SelectiveArt-2x.dat.x1-disabled"}


def parse(text):
    rows = []
    for m in ROW.finditer(text):
        flags = set(re.findall(r"(\w+)\s*=\s*\$true", m.group(4)))
        rows.append({"Src": m.group(1), "Dir": m.group(2), "Name": m.group(3), "flags": flags})
    return rows


PKG = re.compile(r"^(z_SC4UIScale_[A-Za-z0-9]+?)(?:-(15x|2x|3x|1x))?\.dat(?:\.x1-disabled)?$")
FOLDER = {"our": "010-SC4UIScale", "zzz": "zzz-SC4UIScale"}


def list_keys(rows):
    """The (folder\\base, tag) packages Test-DatIntegrity derives from the rows
    (its ConvertTo-ListPair): Optional and Live rows have no fixed deployed
    bytes, an untagged package is tag 'on'."""
    keys = set()
    for r in rows:
        if r["flags"] & {"Optional", "Live"} or not r["Name"].startswith("z_SC4UIScale_"):
            continue
        m = PKG.match(r["Name"])
        if m:
            keys.add((FOLDER.get(r["Dir"], "") + "\\" + m.group(1), m.group(2) or "on"))
    return keys


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
    # 5. Test-DatIntegrity reads the list; its count rows name listed packages
    for r in rows:
        if "Live" in r["flags"]:
            m = PKG.match(r["Name"])
            if not m or m.group(2):
                fails.append("%s: a Live row must be an untagged .dat" % r["Name"])
            elif not any(PKG.match(o["Name"]) and PKG.match(o["Name"]).group(1) == m.group(1)
                         and PKG.match(o["Name"]).group(2) for o in rows):
                fails.append("%s: a Live row needs a tier-tagged sibling" % r["Name"])
        if r["Name"].startswith("z_SC4UIScale_") and not PKG.match(r["Name"]):
            fails.append("%s: not a package name Test-DatIntegrity can resolve" % r["Name"])
    di = open(DATINT, encoding="utf-8").read()
    if "PackageFiles.psd1" not in di or "Import-PowerShellDataFile" not in di:
        fails.append("_tests/Test-DatIntegrity.ps1 does not read _packaging/PackageFiles.psd1")
    hand = re.findall(r'^\s*@\{\s*b\s*=\s*"', di, re.M)
    if hand:
        fails.append("_tests/Test-DatIntegrity.ps1 has %d hand-written deployed==built row(s): "
                     "they derive from _packaging/PackageFiles.psd1 now" % len(hand))
    exp = re.findall(r'@\{\s*rel\s*=\s*"([^"]+)";\s*tag\s*=\s*"([^"]+)"', di)
    exp_declared = len(re.findall(r'^\s*@\{\s*rel\s*=', di, re.M))
    if not exp or len(exp) != exp_declared:
        fails.append("parsed %d of %d entry-count rows in Test-DatIntegrity.ps1" % (len(exp), exp_declared))
    keys = list_keys(rows)
    stale = sorted("%s [%s]" % (rel, tag) for rel, tag in exp
                   if (rel, "on" if tag == "plain" else tag) not in keys)
    if stale:
        fails.append("Test-DatIntegrity.ps1 entry-count row(s) for packages the list does not "
                     "deploy: " + ", ".join(stale))
    counted = {(rel, "on" if tag == "plain" else tag) for rel, tag in exp}
    uncounted = sorted("%s [%s]" % k for k in keys - counted)
    print("Test-DatIntegrity: %d entry-count row(s), all name listed packages: %s; "
          "%d listed package file(s) without a count row%s"
          % (len(exp), "yes" if not stale else "NO", len(uncounted),
             (" (" + ", ".join(uncounted) + ")") if uncounted else ""))

    counts = (len(rows), sum(1 for r in rows if "DeployOnly" not in r["flags"]),
              sum(1 for r in rows if "Carbon" in r["flags"]))
    if fails:
        print("\n".join("FAIL: " + f for f in fails))
        print("OVERALL: FAIL")
        return 1
    print("OVERALL: PASS (%d rows, %d in the bundle, %d Carbon; one list, read by Deploy, Build-Dist and Test-DatIntegrity)" % counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
