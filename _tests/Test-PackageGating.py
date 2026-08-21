#!/usr/bin/env python3
"""
Test-PackageGating - every third-party package must actually BE gated, and the
font preservation must not mistake our own font for the user's.

TWO DEFECTS THIS EXISTS TO CATCH (both were live in shipped code):

  #119  z_SC4UIScale_WarriorUI had a kThirdPartyDeps row - so depOk was computed
        for it on every boot - and NO SyncDat call anywhere. The result was
        computed and discarded. The dat was therefore never tier-gated: it
        stayed active at the stock tier, and stayed active with warrior's mod
        REMOVED, which is precisely the state its own comment says must disable
        us (our copy hard-codes that mod's rects). MEASURED: the deployed
        Plugins folder had z_SC4UIScale_WarriorUI-2x.dat live with no
        .x1-disabled twin while every other subfolder package had one.

  #118  SyncFont snapshotted the live FontStyle.ini as ".user-original" whenever
        no snapshot existed. On an UPGRADE INSTALL the live file is already OUR
        scaled font (written by an older build), so we preserved our own 2x font
        as "the user's original" and then restored it over their file at stock
        tier - the exact data loss the block was added to prevent.

WHAT THIS ASSERTS (source-level, no game required):
  1. Every package named in kThirdPartyDeps has a SyncDat call.       (#119)
  2. Every gated SyncDat call passes DepOkByName with ITS OWN name - not a
     neighbour's (the v2.38.3 index-vs-name bug, generalised).
  3. Every package with a kThirdPartyDeps row is gated on DepOkByName, not
     merely called.
  4. SyncFont's snapshot is guarded by a check that the live file is not one of
     our own tier fonts.                                              (#118)
  5. That guard's helper compares CONTENT, not just size - the three tier fonts
     are all the same byte length, so a size-only test cannot tell them apart.

POSITIVE CONTROL
  The parser must find the packages it already knows exist (SelectiveArt,
  DialogStatic, ItemIcons). If it finds none, the regexes have rotted and a
  "pass" would mean nothing.

Exit 0 = pass. Run from anywhere.
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "ScaleTier.cpp")

# Packages that intentionally have no dependency row (they are ours alone).
UNGATED_BY_DESIGN = {
    # DORMANT since v4.0.3: SelectiveArt no longer appears in `calls` at all
    # (SyncDatStable, not SyncDat - see the wiring check below), so this
    # entry is never consulted any more. Left in rather than removed: if
    # SelectiveArt ever grows a genuine third-party dependency, whoever adds
    # that row will find this set already has an entry to delete, not one to
    # discover is missing.
    "z_SC4UIScale_SelectiveArt",
    "z_SC4UIScale_DialogStatic",
    "z_SC4UIScale_ItemIcons",
    "zzz-SC4UIScale\\z_SC4UIScale_ItemIconsSub",
    # CsiIcons (#188/#196): built from the player's OWN Maxis archives, so
    # there is no upstream mod whose presence it could be conditioned on.
    # Tier-gated only - exactly the ItemIconsSub shape above.
    "zzz-SC4UIScale\\z_SC4UIScale_CsiIcons",
    # UncoveredIcons (#149): rediscovered from the player's own Plugins tree
    # every build, so its CONTENT depends on third-party lots but its
    # correctness does not depend on any one of them being present. A
    # dependency gate would fail the whole package on a harmless upstream
    # re-release; ScaleTier.cpp records that reasoning at the call site.
    "zzz-SC4UIScale\\z_SC4UIScale_UncoveredIcons",
    # SelectorUI-1x (2026-08-19): one script of OURS - Graphic Options at
    # stock geometry with the scale-selector nodes. Nothing upstream to gate
    # on, and it is armed by the ABSENCE of a tier rather than by one.
    "zzz-SC4UIScale\\z_SC4UIScale_SelectorUI",
}


def norm(name):
    return name.replace("\\\\", "\\").strip()


def main():
    if not os.path.isfile(SRC):
        print("FAIL: %s not found" % SRC)
        return 1
    src = open(SRC, encoding="utf-8", errors="replace").read()

    print("Test-PackageGating")
    print("  source: src/ScaleTier.cpp (%d bytes)" % len(src))
    print()

    failures = []

    # ---- parse kThirdPartyDeps rows -------------------------------------
    dep_block = re.search(r"kThirdPartyDeps\[\]\s*=\s*\{(.*?)\n\t\};", src, re.S)
    if not dep_block:
        print("FAIL: could not locate kThirdPartyDeps[] - the parser has rotted.")
        return 1
    dep_names = [norm(m) for m in
                 re.findall(r'\{\s*L"([^"]+)"', dep_block.group(1))]

    # ---- parse SyncDat call sites ---------------------------------------
    calls = {}
    for m in re.finditer(
            # THE THIRD ARGUMENT IS NOT ALWAYS pkg.tag (2026-08-19). This
            # pattern used to demand it literally, so SelectorUI-1x - which
            # passes its own L"-1x" because it is armed by the ABSENCE of a
            # tier - was INVISIBLE to this gate: a package that ships a
            # script into the game and no gate could see it. Law 42, a gate
            # is only as honest as its scope. Accept any tag expression.
            r'SyncDat\(\s*docPlugins\s*,\s*L"([^"]+)"\s*,\s*([^,]+?)\s*,\s*([^;]+?)\);',
            src, re.S):
        calls[norm(m.group(1))] = " ".join(m.group(3).split())

    print("  kThirdPartyDeps rows : %d" % len(dep_names))
    print("  SyncDat call sites   : %d" % len(calls))
    print()

    # positive control -----------------------------------------------------
    # SelectiveArt EXCLUDED (v4.0.3): it moved from SyncDat(...) to
    # SyncDatStable(...) (the stable-filename pilot, see ScaleTier.cpp), a
    # different call this regex does not match by design - checked
    # separately below instead of broadening this one to match both shapes.
    known = {"z_SC4UIScale_DialogStatic", "z_SC4UIScale_ItemIcons"}
    found_known = known & set(calls)
    if len(found_known) != len(known):
        print("FAIL: positive control - the SyncDat parser found only %s of the "
              "%d packages known to exist. A pass would prove nothing."
              % (sorted(found_known), len(known)))
        return 1
    print("  positive control: parser found all %d always-present packages." % len(known))
    print()

    # ---- SelectiveArt's own wiring check (v4.0.3 pilot) -------------------
    # The #119 shape, one mechanism later: a call that is WRITTEN but never
    # actually reached is indistinguishable from no call at all until
    # something asserts it is wired. SyncDatStable takes activeTag directly
    # (not pkg.tag/match like SyncDat), so it cannot be found by the regex
    # above - this checks its own call site exists, once.
    stable_call = re.search(
        r'SyncDatStable\(\s*docPlugins\s*,\s*L"z_SC4UIScale_SelectiveArt"\s*,'
        r'\s*activeTag\s*\)', src)
    if not stable_call:
        failures.append(
            "SyncDatStable(docPlugins, L\"z_SC4UIScale_SelectiveArt\", "
            "activeTag) not found - SelectiveArt's stable-filename sync may "
            "be computed and never actually called (the #119 shape).")
        print("  [z_SC4UIScale_SelectiveArt (stable)                 ] *** NOT WIRED ***")
    else:
        print("  [z_SC4UIScale_SelectiveArt (stable)                 ] wired")

    # ---- 1 + 3: every dep row has a gated call ---------------------------
    for name in dep_names:
        if name not in calls:
            failures.append(
                "#119 SHAPE: '%s' has a kThirdPartyDeps row but NO SyncDat call. "
                "Its depOk is computed and DISCARDED, so the package is never "
                "tier-gated and never disabled when its owning mod is removed."
                % name)
            print("  [%-52s] *** NO SyncDat CALL ***" % name)
            continue
        expr = calls[name]
        if "DepOkByName" not in expr:
            failures.append(
                "'%s' has a dependency row but its SyncDat is not gated on "
                "DepOkByName (expr: %s)" % (name, expr))
            print("  [%-52s] *** NOT GATED ***" % name)
        else:
            print("  [%-52s] gated" % name)

    # ---- 2: each gate names ITSELF ---------------------------------------
    print()
    for name, expr in sorted(calls.items()):
        m = re.search(r'DepOkByName\(\s*L"([^"]+)"', expr)
        if not m:
            if name in dep_names:
                pass  # already reported above
            elif name not in UNGATED_BY_DESIGN:
                failures.append(
                    "'%s' is neither gated nor listed as ungated-by-design. If "
                    "it is genuinely ours alone, add it to UNGATED_BY_DESIGN "
                    "with a reason; if it derives from another mod, gate it."
                    % name)
            continue
        gated_on = norm(m.group(1))
        if gated_on != name:
            failures.append(
                "'%s' is gated on '%s' - a DIFFERENT package's dependency. This "
                "is the v2.38.3 index-vs-name bug in name form." % (name, gated_on))
            print("  cross-gate: %s -> %s   *** MISMATCH ***" % (name, gated_on))

    # ---- 4 + 5: the #118 font guard --------------------------------------
    print()
    helper = re.search(r"MatchesAnyTierFontSource\s*\([^)]*\)\s*\{(.*?)\n\t\}",
                       src, re.S)
    guard = re.search(r"!FileExists\(userOrig\)\s*\)\s*\{(.*?)CopyFileW\(live,\s*userOrig",
                      src, re.S)
    if not helper:
        failures.append(
            "#118: MatchesAnyTierFontSource() is missing. Without it SyncFont "
            "will snapshot OUR OWN scaled font as .user-original on any upgrade "
            "install, then restore it over the user's file at stock tier.")
        print("  [#118 font guard] *** HELPER MISSING ***")
    elif not guard or "MatchesAnyTierFontSource" not in guard.group(1):
        failures.append(
            "#118: the .user-original snapshot is NOT guarded by "
            "MatchesAnyTierFontSource - the helper exists but nothing calls it "
            "on the path that matters.")
        print("  [#118 font guard] *** HELPER NOT ON THE SNAPSHOT PATH ***")
    else:
        body = helper.group(1)
        if "FilesIdentical" not in body:
            failures.append(
                "#118: MatchesAnyTierFontSource does not compare CONTENT. The "
                "three tier fonts are all the same byte length, so a size-only "
                "test cannot distinguish them - or distinguish ours from a "
                "same-sized user file.")
            print("  [#118 font guard] *** NOT A CONTENT COMPARE ***")
        else:
            print("  [#118 font guard] present, on the snapshot path, "
                  "content-compared")

    print()
    if failures:
        print("FAIL: %d problem(s):" % len(failures))
        for f in failures:
            print("  - %s" % f)
        return 1

    print("ALL PASS (%d dependency rows all gated on their own name; #118 font "
          "guard live)" % len(dep_names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
