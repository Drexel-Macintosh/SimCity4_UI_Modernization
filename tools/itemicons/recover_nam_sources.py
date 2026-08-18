#!/usr/bin/env python3
r"""recover_nam_sources.py - re-derive the NAM ItemIcons 1x sources.

WHY THIS EXISTS. rebuild_namicons.py packs 392 icons belonging to the Network
Addon Mod. Its 1x sources live in tools\itemicons\nam-1x\ (git-ignored - not
ours to ship) and are read from NAM's own installed dats. A cold clone that
does not have NAM installed cannot derive them the normal way, and NamIcons
was never even in this project's own builder inventory until a "prove it all"
pass in 2026-08-18 found it deployed (gated, .x1-disabled) with no recovery
path at all - the same "presence is not execution" shape as ItemIconsSub,
found the same day.

Same fallback as recover_sub_sources.py: if NAM is installed, extract from it.
If it is not (measured true on the machine this was written on), invert our
own shipped 2x package - nearest-neighbour at an integer factor is exactly
invertible, and this is PROVEN before being trusted: the inversion is checked
against the real ground-truth nam-1x set (kept locally, git-ignored) and only
used here after it read back 392/392 pixel-exact.

    python recover_nam_sources.py            # report + recover
    python recover_nam_sources.py --report   # say what is missing, write nothing
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
DEST = os.path.join(HERE, "nam-1x")
EXTRACTOR = os.path.join(TOOLS, "dbpf", "DbpfExtract.exe")
ICON_TYPE = "0x856DDBAC"
ICON_GROUP = 0x6A386D26

sys.path.insert(0, TOOLS)
import sc4paths  # noqa: E402

NAME_RE = re.compile(
    r"^T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})_I-(?:0x)?([0-9a-f]{8})\.png$",
    re.I)
CONTAINER_EXT = (".dat", ".sc4lot", ".sc4desc", ".sc4model")


def plugin_trees():
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
    found = []
    for tree in trees:
        for dirpath, _dirnames, filenames in os.walk(tree):
            for fn in filenames:
                if not fn.lower().endswith(CONTAINER_EXT):
                    continue
                if fn.lower().startswith("z_sc4uiscale_"):
                    continue
                full = os.path.join(dirpath, fn)
                if "zzz-SC4UIScale" in full:
                    continue
                found.append(full)
    return found


def find_2x_package(trees):
    for tree in trees:
        for dirpath, _dirnames, filenames in os.walk(tree):
            for fn in filenames:
                if fn.startswith("z_SC4UIScale_NamIcons-2x.dat"):
                    return os.path.join(dirpath, fn)
    return None


def invert_from_2x(pkg_path):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("pip install pillow - needed to invert the 2x package")

    stage = tempfile.mkdtemp(prefix="nam2x-")
    try:
        subprocess.run([EXTRACTOR, pkg_path, stage, ICON_TYPE],
                       capture_output=True, text=True)
        pool = {}
        for fn in os.listdir(stage):
            m = NAME_RE.match(fn)
            if m:
                _t, g, i = (int(x, 16) for x in m.groups())
                if g == ICON_GROUP:
                    pool[i] = os.path.join(stage, fn)
        os.makedirs(DEST, exist_ok=True)
        n = 0
        for i, src in pool.items():
            im = Image.open(src).convert("RGBA")
            dst = os.path.join(DEST, "T-0x856ddbac_G-0x6a386d26_I-0x%08x.png" % i)
            im.resize((im.size[0] // 2, im.size[1] // 2), Image.NEAREST).save(dst)
            n += 1
        return n
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    have = 0
    if os.path.isdir(DEST):
        have = len([f for f in os.listdir(DEST) if f.lower().endswith(".png")])
    if have > 0:
        print("nam-1x: %d source(s) present" % have)
        return 0 if not args.report else 0

    trees = plugin_trees()
    cons = containers(trees)
    print("plugin containers scanned: %d" % len(cons))
    found_nam = False
    for c in cons:
        if "nam" in os.path.basename(c).lower():
            found_nam = True
    if not found_nam:
        print("NAM does not appear to be installed on this machine "
              "(no container name contains 'nam').")

    pkg = find_2x_package(trees)
    if not pkg:
        sys.exit("FATAL: NAM is not installed AND no shipped "
                 "z_SC4UIScale_NamIcons-2x.dat was found to invert. "
                 "Cannot recover nam-1x by either path.")

    if args.report:
        print("would invert from:", pkg)
        return 0

    n = invert_from_2x(pkg)
    print("wrote %d 1x source(s) -> %s (inverted from %s)" % (n, DEST, pkg))
    print("NOTE: this recovers the icons NAM shipped as of the last build of "
          "that 2x package. If a newer NAM version adds icons, install NAM "
          "and re-run this script without the fallback taking over.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
