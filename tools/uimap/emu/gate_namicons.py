#!/usr/bin/env python3
r"""GATE #139 - NAM ItemIcon 2x/1.5x/3x override packages. Offline, read-only.

Proves WITHOUT launching the game that:
  1. every uncovered NAM ItemIcon TGI is present in each tier package;
  2. each packed PNG is EXACTLY tier x the 1x source it came from (a
     mis-scaled strip re-introduces the very tiling this fixes);
  3. every entry is a FOUR-STATE strip - width divisible by 4 - because the
     button picks its cell by imageWidth/4 (ITEMICONS.md:24-29);
  4. we ship no TGI the mod does not actually have (no orphan overrides);
  5. LOAD ORDER still works: our folder must sort AFTER the mod's folder,
     or the override silently loses (ScaleTier.cpp load-order law).

NEGATIVE CONTROLS are mandatory - a gate that cannot fail proves nothing.

    python gate_namicons.py      exit 0 = green
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ICONS = os.path.join(ROOT, "tools", "itemicons")
SRC_1X = os.path.join(ICONS, "nam-1x")
import sys as _sys
_TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _TOOLS not in _sys.path:
    _sys.path.insert(0, _TOOLS)
from sc4paths import plugins_dir     # noqa: E402
# Resolved, not hard-coded: $SC4_PLUGINS, else the shell's Documents,
# else the OneDrive-redirected or plain %USERPROFILE% variant. See
# tools/sc4paths.py for why a literal path here was a bug, not a shortcut.
PLUGINS = plugins_dir(require=True)

PNG_TYPE = 0x856DDBAC
ICON_GROUP = 0x6A386D26
TIERS = [("15x", 1.5), ("2x", 2.0), ("3x", 3.0)]
NAM_FOLDER = "770-network-addon-mod"
OUR_FOLDER = "zzz-SC4UIScale"

fails = []


def check(cond, msg):
    print(("   ok   " if cond else "   FAIL ") + msg)
    if not cond:
        fails.append(msg)
    return cond


def dbpf_index(path):
    # NAM nests dats past Windows' 260-char MAX_PATH (e.g. "...\Legacy Road
    # Viaduct Puzzle Piece Menu Button Access#\..."), so a plain open() throws
    # FileNotFoundError on files that plainly exist. The \\?\ prefix lifts the
    # limit. Without this the orphan check dies mid-walk and the gate exits 0
    # having proved nothing.
    if os.name == "nt" and len(path) > 240 and not path.startswith("\\\\?\\"):
        path = "\\\\?\\" + os.path.abspath(path)
    with open(path, "rb") as f:
        hdr = f.read(96)
        if hdr[:4] != b"DBPF":
            return {}
        count, off = struct.unpack_from("<II", hdr, 36)
        f.seek(off)
        blob = f.read(count * 20)
        out = {}
        for i in range(count):
            t, g, inst, o, s = struct.unpack_from("<IIIII", blob, i * 20)
            out[(t, g, inst)] = (o, s)
        return out


def png_dims_at(path, off):
    with open(path, "rb") as f:
        f.seek(off)
        b = f.read(26)
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", b[16:24])


# ONE SOURCE FOR THE SCALING RULES (scale_rules.py). This file used to
# carry its own copy; #162 changed ScaleRound in the DLL and every private
# copy in this folder had to be found by hand. `scale_rules.py --drift`
# hunts any that come back.
from scale_rules import round_half_up as lround  # noqa: E402


def main():
    if not os.path.isdir(SRC_1X):
        print("SKIP: %s missing - run scan_thirdparty_icons.py first "
              "(this is a SKIP, not a pass)." % SRC_1X)
        return 2

    src = {}
    for fn in os.listdir(SRC_1X):
        p = os.path.join(SRC_1X, fn)
        with open(p, "rb") as f:
            b = f.read(26)
        inst = int(fn.split("_I-")[1].split(".")[0], 16)
        src[inst] = struct.unpack(">II", b[16:24])
    print("1x sources: %d" % len(src))

    print("\n1. EVERY tier package carries every source TGI, at tier size, "
          "4-state divisible")
    for tag, f in TIERS:
        dat = os.path.join(ICONS, "out", "z_SC4UIScale_NamIcons-%s.dat" % tag)
        if not os.path.isfile(dat):
            check(False, "%s exists" % os.path.basename(dat))
            continue
        idx = dbpf_index(dat)
        got = {k[2] for k in idx if k[0] == PNG_TYPE and k[1] == ICON_GROUP}
        check(got == set(src),
              "%-4s carries all %d TGIs (has %d, missing %d, extra %d)"
              % (tag, len(src), len(got), len(set(src) - got), len(got - set(src))))
        bad_dim, bad_quad = [], []
        for inst, (w0, h0) in src.items():
            key = (PNG_TYPE, ICON_GROUP, inst)
            if key not in idx:
                continue
            d = png_dims_at(dat, idx[key][0])
            if d is None:
                bad_dim.append(inst)
                continue
            w, h = d
            # WIDTH IS SNAPPED TO A MULTIPLE OF 4, NOT just rounded. The button
            # picks its state cell by imageWidth/4, so a width off the 4-grid
            # gives fractional cells and smears the states - which is the very
            # bug this package fixes, reappearing at another tier. NAM's 356
            # wide strips are the case that forced this: 356*1.5 = 534, and
            # 534/4 = 133.5. Caught by this gate on its first run.
            if (w, h) != (4 * round(w0 * f / 4), lround(h0 * f)):
                bad_dim.append(inst)
            if w % 4:
                bad_quad.append(inst)
        check(not bad_dim, "%-4s all %d entries are exactly x%.1f (%d wrong)"
              % (tag, len(src), f, len(bad_dim)))
        check(not bad_quad, "%-4s all widths divisible by 4 (%d not)"
              % (tag, len(bad_quad)))

    print("\n2. NO ORPHANS - every TGI we override is really supplied by SOMEONE")
    # THE PREMISE OF THIS CHECK WAS STALE AND IT MADE THE GATE PERMANENTLY
    # RED (392 "orphans"). It used to assert `set(src) <= nam` - every icon we
    # override must exist in the NAM folder - which was the right invariant
    # back when our ItemIcons override was built FROM NAM and nothing else.
    #
    # Uncovered third-party icons are now handled by the boot scan + resource
    # enlargement, which discovers icons from ANY supplier on disk (custom
    # lots, other mods), not just NAM. So our override set legitimately
    # contains icons NAM never shipped, and measuring it against NAM alone
    # condemns correct data - the instrument's fault, not the build's
    # (law 88: a model that would condemn a correct build is broken).
    #
    # THE SURVIVING INVARIANT is narrower and still worth asserting: we must
    # never override a TGI that NOBODY supplies. That is a real orphan - a
    # dangling override shipping pixels for an icon no installed content can
    # ever request. Measured against the WHOLE third-party supply on disk.
    supply_all = set()
    nam = set()
    if os.path.isdir(PLUGINS):
        for root, _d, files in os.walk(PLUGINS):
            for fn in files:
                if os.path.splitext(fn)[1].lower() not in (
                        ".dat", ".sc4lot", ".sc4desc", ".sc4model", ".sc4"):
                    continue
                if fn.startswith("z_SC4UIScale_"):
                    continue                   # ours is not "supply"
                p = os.path.join(root, fn)
                in_nam = (os.sep + NAM_FOLDER + os.sep) in (p + os.sep)
                for (t, g, i) in dbpf_index(p):
                    if t == PNG_TYPE and g == ICON_GROUP:
                        supply_all.add(i)
                        if in_nam:
                            nam.add(i)
        orphans = set(src) - supply_all
        print("   info supply: %d icon TGIs on disk (%d of them from %s); "
              "we override %d" % (len(supply_all), len(nam), NAM_FOLDER, len(src)))
        # GATE ON THE CONDITION YOU DEPEND ON, AND MEASURE IT BY CONTENT.
        # The old guard was `os.path.isdir(<NAM folder>)`, which is TRUE on
        # this machine while the folder holds ZERO .dat files - NAM is not
        # actually installed. So the orphan check ran against an empty supply
        # and reported all 392 of our overrides as orphans, every run, for
        # weeks. The package itself was fine the whole time: ScaleTier's
        # dependency gate had correctly parked NamIcons as
        # `.dat.x1-disabled` ("none - dependency-gated off").
        #
        # A directory can exist and supply nothing. Decide on the SUPPLY.
        if not nam:
            print("   SKIP %s supplies 0 icons of group 0x%08X - NAM is not "
                  "installed, so our NamIcons override is dependency-gated "
                  "OFF and there is nothing to be an orphan OF. Re-run this "
                  "with NAM installed to actually exercise the check."
                  % (NAM_FOLDER, ICON_GROUP))
        else:
            check(not orphans,
                  "all %d overridden TGIs are supplied by installed content "
                  "(%d orphans)" % (len(src), len(orphans)))
    else:
        print("   SKIP Plugins not present - orphan check not run")

    print("\n3. LOAD ORDER - our folder must sort after the mod's")
    check(OUR_FOLDER > NAM_FOLDER,
          "'%s' > '%s' so our override wins" % (OUR_FOLDER, NAM_FOLDER))

    print("\n3b. PER-TGI LOAD ORDER - no mod may win any icon we claim to cover")
    # THE FOLDER CHECK ABOVE IS NOT ENOUGH, and believing it cost a visible
    # defect. 0x2A3ED76A is a STOCK icon we double in the ROOT ItemIcons dat;
    # NAM also ships it from a subfolder, and root FILES load before
    # SUBFOLDERS - so NAM won and the Rail button rendered wrong while every
    # coverage count said "covered". Coverage must be decided by which file
    # loads LAST, per TGI, not by "is it in any package of ours".
    def order_key(path):
        rel = os.path.relpath(path, PLUGINS)
        parts = rel.split(os.sep)
        return [(0 if i == len(parts) - 1 else 1, p.lower())
                for i, p in enumerate(parts)]

    if os.path.isdir(PLUGINS):
        supply = {}
        for root, _d, files in os.walk(PLUGINS):
            for fn in files:
                if os.path.splitext(fn)[1].lower() not in (
                        ".dat", ".sc4lot", ".sc4desc", ".sc4model", ".sc4"):
                    continue
                p = os.path.join(root, fn)
                mine = fn.startswith("z_SC4UIScale_")
                for (t, g, i) in dbpf_index(p):
                    if t == PNG_TYPE and g == ICON_GROUP:
                        supply.setdefault(i, []).append((p, mine))
        losers = []
        for i, v in supply.items():
            if all(m for _p, m in v):
                continue                       # nobody else supplies it
            win_path, win_mine = max(v, key=lambda x: order_key(x[0]))
            if not win_mine:
                losers.append((i, os.path.basename(win_path)))
        check(not losers,
              "no third-party file wins any icon (%d losing: %s)"
              % (len(losers),
                 ", ".join("0x%08X<-%s" % (i, n) for i, n in losers[:5])))
    else:
        print("   SKIP Plugins not present")

    print("\n4. NEGATIVE CONTROLS (each MUST fail)")
    neg = 0

    def expect_fail(cond, label):
        nonlocal neg
        if cond:
            print("   BROKEN GATE: %s did NOT fail" % label)
            fails.append("negative control did not fail: " + label)
        else:
            print("   ok   failed-as-expected: %s" % label)
            neg += 1

    any_inst = next(iter(src))
    w0, h0 = src[any_inst]
    expect_fail((lround(w0 * 2.0), lround(h0 * 2.0)) == (w0, h0),
                "2x dims equal 1x dims")
    expect_fail(177 % 4 == 0, "a width of 177 is 4-state divisible")
    expect_fail(OUR_FOLDER < NAM_FOLDER, "our folder sorts BEFORE the mod's")
    expect_fail(os.path.isfile(os.path.join(ICONS, "out",
                "z_SC4UIScale_NamIcons-9x.dat")), "a bogus 9x package exists")
    expect_fail(0xDEADBEEF in src, "a bogus TGI is in the source set")
    print("   %d negative controls fired" % neg)

    print("\n" + "=" * 62)
    if fails:
        print("GATE #139 RED - %d failure(s):" % len(fails))
        for f_ in fails:
            print("   - %s" % f_)
        return 1
    print("GATE #139 GREEN - %d icons x %d tiers verified." % (len(src), len(TIERS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
