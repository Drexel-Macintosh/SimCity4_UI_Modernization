#!/usr/bin/env python3
r"""recover_sub_sources.py - re-derive the ItemIconsSub 1x sources from Plugins.

WHY THIS EXISTS. build_itemicons_sub.py packs 130 submenu icons. 129 of them
belong to OTHER MODS (memo.submenus-dll, CAM and Maxis landmark plugins, and
five Maxis .SC4Lot icons); the 130th, the Missing Thumb 0x144161EC, is stock
art taken from the upscale preview set. None of the 129 can live in this repo -
they are not ours - so a cold clone has the builder and none of its inputs.
That was one of the failures the 2026-08-18 cold-clone test found; the audit
before it had checked only that the BUILDER was present.

The historical split into three folders (submenus-1x / plugins-1x /
lots-icons-1x) records where each icon was FOUND across three passes in July.
The builder merges all three into one pool and refuses duplicate names, so this
script writes everything into submenus-1x and leaves the other two present and
empty. The provenance story stays in REPORT.md, where it belongs; re-deriving
the three-way split would be inventing history, not preserving it.

WHAT IS AUTHORITATIVE: _work\pack-sub-manifest.txt, the 130 canonical names of
the user-confirmed 2x package. It is a derived list, it is ours, and it is in
the repo. This script asks it what to look for; nothing is hard-coded here.

    python recover_sub_sources.py            # report + recover
    python recover_sub_sources.py --report   # say what is missing, write nothing
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
WORK = os.path.join(HERE, "_work")
MANIFEST = os.path.join(WORK, "pack-sub-manifest.txt")
EXTRACTOR = os.path.join(TOOLS, "dbpf", "DbpfExtract.exe")
ICON_TYPE = "0x856DDBAC"

# Stock-pool art, deliberately NOT recovered from Plugins: the builder takes it
# from the tier's own upscale preview set. Sourcing it from a mod instead would
# silently ship a mod's copy of a stock image.
MISSING_THUMB_IID = 0x144161EC

sys.path.insert(0, TOOLS)
import sc4paths  # noqa: E402

NAME_RE = re.compile(
    r"^T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})_I-(?:0x)?([0-9a-f]{8})\.png$",
    re.I)

# Containers SC4 loads. .SC4Lot / .SC4Desc / .SC4Model are DBPF archives too -
# five of the 129 icons live in Maxis .SC4Lot files, and a scan that only looked
# at *.dat would come back short by exactly those five and look like a clean run.
CONTAINER_EXT = (".dat", ".sc4lot", ".sc4desc", ".sc4model")


def wanted_tgis():
    if not os.path.isfile(MANIFEST):
        sys.exit("FATAL: %s missing. It is the derived name set of the shipped\n"
                 "  2x package and this script cannot know what to look for "
                 "without it." % MANIFEST)
    out = {}
    with open(MANIFEST, "r", encoding="utf-8") as f:
        for line in f:
            m = NAME_RE.match(line.strip())
            if not m:
                continue
            t, g, i = (int(x, 16) for x in m.groups())
            if i == MISSING_THUMB_IID:
                continue
            out[(g, i)] = "T-0x%08x_G-0x%08x_I-0x%08x.png" % (t, g, i)
    if not out:
        sys.exit("FATAL: %s parsed to 0 entries - the manifest format changed." % MANIFEST)
    return out


def plugin_trees():
    """BOTH trees. A claim about what is installed that only enumerated the
    user's Documents tree has been wrong here before - the install-side
    <game>\\Plugins is the one that gets forgotten."""
    trees = []
    for fn in (sc4paths.game_plugins_dir, sc4paths.plugins_dir):
        try:
            p = fn()
        except Exception:
            p = None
        if p and os.path.isdir(p):
            trees.append(p)
    return trees


def containers(trees):
    """Every loadable container, root-first per tree so a deeper file - which
    the game loads later and therefore WINS - overwrites it in the stage."""
    found = []
    for tree in trees:
        hits = []
        for dirpath, _dirnames, filenames in os.walk(tree):
            for fn in filenames:
                if not fn.lower().endswith(CONTAINER_EXT):
                    continue
                # Never read our own output back in as if it were a mod's source.
                if fn.lower().startswith("z_sc4uiscale_"):
                    continue
                full = os.path.join(dirpath, fn)
                if "zzz-SC4UIScale" in full:
                    continue
                depth = os.path.relpath(full, tree).count(os.sep)
                hits.append((depth, full))
        found += [f for _d, f in sorted(hits)]
    return found


def _find_2x_packages(trees):
    """Our own shipped ItemIconsSub packages, enabled or tier-disabled.

    ScaleTier renames the inactive tiers to '<name>.x1-disabled', so a scan
    that only matched '*.dat' would miss the very file it needs and report a
    clean null."""
    hits = []
    for t in trees:
        for dp, _dn, fns in os.walk(t):
            for fn in fns:
                if fn.startswith("z_SC4UIScale_ItemIconsSub-2x.dat"):
                    hits.append(os.path.join(dp, fn))
    return hits


def invert_from_2x(have, want, missing):
    """Recover 1x sources by inverting our own 2x package. Returns
    (recovered {key: path}, control_ok, control_bad).

    The control is the point: every icon already recovered from Plugins is
    downscaled from the 2x twin and compared BYTE FOR BYTE against the real 1x.
    Only if every one matches is the inversion trusted for the icons that have
    no other source. A single mismatch means the 2x package was not a pure
    nearest-neighbour replication and the whole fallback is refused.
    """
    try:
        from PIL import Image
    except ImportError:
        print("   (no pillow - cannot invert the 2x package; pip install pillow)")
        return {}, 0, 0

    trees = plugin_trees()
    pkgs = _find_2x_packages(trees)
    if not pkgs:
        print("   (no z_SC4UIScale_ItemIconsSub-2x package installed - "
              "nothing to invert)")
        return {}, 0, 0

    stage = tempfile.mkdtemp(prefix="sub2x-")
    try:
        for p in pkgs:
            subprocess.run([EXTRACTOR, p, stage, ICON_TYPE],
                           capture_output=True, text=True)
        pool = {}
        for fn in os.listdir(stage):
            m = NAME_RE.match(fn)
            if m:
                _t, g, i = (int(x, 16) for x in m.groups())
                pool[(g, i)] = os.path.join(stage, fn)

        ok = bad = 0
        for k in sorted(have):
            if k not in want or k not in pool:
                continue
            a = Image.open(have[k]).convert("RGBA")
            b = Image.open(pool[k]).convert("RGBA")
            if b.size != (a.size[0] * 2, a.size[1] * 2):
                bad += 1
                print("   CONTROL size mismatch {%08x,%08x}: 1x%s vs 2x%s"
                      % (k[0], k[1], a.size, b.size))
                continue
            if b.resize(a.size, Image.NEAREST).tobytes() == a.tobytes():
                ok += 1
            else:
                bad += 1
                print("   CONTROL pixel mismatch {%08x,%08x}" % k)
        if bad or ok == 0:
            # ok == 0 is also a refusal: an "exact" verdict from zero
            # comparisons is not evidence, it is an absent instrument.
            if ok == 0 and not bad:
                print("   CONTROL ran on 0 icons - refusing (a null from an "
                      "instrument that never fired is not a pass).")
            return {}, ok, max(bad, 1)

        out_dir = os.path.join(WORK, "_recovered-1x")
        os.makedirs(out_dir, exist_ok=True)
        rec = {}
        for k in missing:
            src = pool.get(k)
            if not src:
                continue
            im = Image.open(src).convert("RGBA")
            dst = os.path.join(out_dir, "T-0x856ddbac_G-0x%08x_I-0x%08x.png" % k)
            im.resize((im.size[0] // 2, im.size[1] // 2), Image.NEAREST).save(dst)
            rec[k] = dst
        return rec, ok, 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="say what would be recovered; write nothing")
    args = ap.parse_args()

    if not os.path.isfile(EXTRACTOR):
        sys.exit("FATAL: %s missing. Build it - see RUNBOOK.md section 0." % EXTRACTOR)

    want = wanted_tgis()
    trees = plugin_trees()
    if not trees:
        sys.exit("FATAL: no Plugins folder found. Set SC4_PLUGINS. "
                 "These icons come from your own installed mods; there is "
                 "nowhere else to get them.")
    for t in trees:
        print("plugin tree: %s" % t)

    cons = containers(trees)
    print("containers to scan: %d" % len(cons))
    if not cons:
        # A null here is a REFUSAL, not a pass: zero containers means the scan
        # never looked, and reporting "0 of 129 found" would read as a finding.
        sys.exit("FATAL: 0 containers found under the Plugins trees. The scan "
                 "did not look; that is not evidence the icons are absent.")

    stage = tempfile.mkdtemp(prefix="sub1x-")
    try:
        for c in cons:
            subprocess.run([EXTRACTOR, c, stage, ICON_TYPE],
                           capture_output=True, text=True)

        have = {}
        for fn in os.listdir(stage):
            m = NAME_RE.match(fn)
            if not m:
                continue
            _t, g, i = (int(x, 16) for x in m.groups())
            have[(g, i)] = os.path.join(stage, fn)

        found = sorted(k for k in want if k in have)
        missing = sorted(k for k in want if k not in have)
        print("wanted %d, found %d, missing %d" % (len(want), len(found), len(missing)))
        for (g, i) in missing:
            print("   MISSING {%08x,%08x} - the owning mod is not installed" % (g, i))

        # ---- fallback: invert our own shipped 2x package ------------------
        # MEASURED 2026-08-18 on this machine: 30 of the 129 exist NOWHERE in
        # either Plugins tree, at any group id - only inside our own
        # ItemIconsSub packages, at 2x/1.5x/3x. The mods that supplied them are
        # no longer installed. That is not a reason to ship a short package.
        #
        # The 2x package was built by NEAREST-NEIGHBOUR block replication at an
        # integer factor, which is exactly invertible: pixel (x,y) of the 1x
        # source is pixel (2x,2y) of the 2x image, losslessly. This is
        # recovery, not reconstruction.
        #
        # PROVEN, NOT ASSUMED: the inversion is checked against every icon this
        # run already recovered from Plugins. If a single one disagrees the
        # premise is wrong and the whole fallback is refused - a downscale that
        # is not exact would quietly bake a resampling error into every tier.
        if missing and not args.report:
            recovered_2x, ctrl_ok, ctrl_bad = invert_from_2x(have, want, missing)
            if ctrl_bad:
                print("   CONTROL FAILED on %d icon(s) - refusing the 2x "
                      "inversion entirely." % ctrl_bad)
            elif recovered_2x:
                print("   2x inversion control: %d/%d exact" % (ctrl_ok, ctrl_ok))
                for k, img in recovered_2x.items():
                    have[k] = img
                found = sorted(k for k in want if k in have)
                missing = sorted(k for k in want if k not in have)
                print("   recovered %d more by inverting our own 2x package "
                      "(nearest-neighbour is exactly invertible)"
                      % len(recovered_2x))

        if args.report:
            return 0 if not missing else 1

        dest = os.path.join(WORK, "submenus-1x")
        os.makedirs(dest, exist_ok=True)
        for fn in os.listdir(dest):
            if fn.lower().endswith(".png"):
                os.remove(os.path.join(dest, fn))
        for k in found:
            shutil.copy2(have[k], os.path.join(dest, want[k]))
        # The builder iterates all three historical dirs and refuses a duplicate
        # name across them, so the other two must exist and stay empty.
        for d in ("plugins-1x", "lots-icons-1x"):
            os.makedirs(os.path.join(WORK, d), exist_ok=True)
        print("wrote %d 1x source(s) -> %s" % (len(found), dest))

        if missing:
            print("\nbuild_itemicons_sub.py will REFUSE until every name in the "
                  "manifest resolves.\nThat refusal is correct: a tier package "
                  "silently short an icon is the failure\nthe name-set check "
                  "exists to catch.")
            return 1
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
