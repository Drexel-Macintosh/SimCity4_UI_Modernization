#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate the sc4pac channel metadata for SC4UIScale from a BUILT BUNDLE.

    python tools/sc4pac/gen_channel.py --bundle dist/SC4UIScale-v4.5.0-dev

Why this is generated rather than hand-written
----------------------------------------------
The v4.5.0 payload layout ships one live `z_SC4UIScale_<Pkg>.dat` per package
plus inert `z_SC4UIScale_<Pkg>.<tag>.uipay` files (tags 15x / 2x / 3x / on /
off).  Measured against sc4pac 0.10.0: a file with a NON-CANONICAL EXTENSION
installs ONLY through a `withChecksum` entry - listed under `include:` it is
silently dropped.  So every `.uipay` needs its own entry carrying a real
sha256.  That is ~78 entries whose hashes change on every build: not a
hand-maintained list.

What it does NOT do
-------------------
It does not invent policy.  Every design decision, and the whole measured
record of sc4pac's behaviour, lives in the PRESERVED_* constants below, copied
verbatim from the hand-written file this generator replaces.  The generator
refuses to write output that drops any of those comment lines (see
--allow-comment-loss).

Self-checks that run on every invocation (all can fail, and say so loudly):
  * COVERAGE   - every file under <bundle>/Plugins is claimed by exactly one
                 package through exactly one mechanism, or the run aborts.
  * CHECKSUM   - every sha256 written into the YAML is re-verified by re-
                 hashing the file it came from, reading the paths back OUT of
                 the emitted YAML rather than out of memory.
  * COMMENTS   - every `#` line present in the previous version of the output
                 file must still be present in the new one.

Exit codes: 0 ok, 1 a self-check failed (nothing written), 2 bad arguments.
"""

import argparse
import datetime as _dt
import hashlib
import os
import re
import sys

# --------------------------------------------------------------------------
# Identity.  NOT the version - that is discovered from the bundle directory.
# --------------------------------------------------------------------------
GROUP = "a-drexel"
GITHUB_OWNER = "Drexel-Macintosh"
GITHUB_REPO = "SimCity4_UI_Modernization"
OUT_RELPATH = os.path.join("_packaging", "sc4pac", "drexel-sc4-ui-scale.yaml")

# sc4pac's own root-placement / canonical-extension constant, quoted from the
# measurement record in PRESERVED_HEADER below.  A file matching this installs
# through a plain `include:` pattern; anything else needs `withChecksum`.
CANONICAL_EXT_RE = re.compile(r"(?:\.dat|\.sc4model|\.sc4lot|\.sc4desc|\.sc4|\.dll)$", re.I)

# A pre-release marker on the bundle directory name.  Stripped for the release
# version and the release URL, and reported when it is.
PRERELEASE_RE = re.compile(r"-(?:dev|alpha|beta|rc)(?:[.\-]?\d+)?$", re.I)
BUNDLE_DIR_RE = re.compile(r"^(?P<product>[A-Za-z0-9_]+)-v(?P<version>.+)$")

# --------------------------------------------------------------------------
# The package model.  Two packages, one shared asset.
#
# `roots` are entries directly under <bundle>/Plugins.  A file is a top-level
# root; a directory root claims its whole subtree.  Anything under Plugins
# that is not claimed here is an ORPHAN and aborts the run - that is the
# check that catches a new folder appearing in a future build.
# --------------------------------------------------------------------------
PACKAGES = [
    dict(
        name="sc4-ui-scale",
        subfolder="050-load-first",
        dependencies=["config:sc4-edition-windows-digital"],
        file_roots=["SC4UIScale.dll"],
        dir_roots=["010-SC4UIScale"],
        summary="Scales the SimCity 4 interface to 1.5x, 2x or 3x for high-resolution displays",
        conflicts="Requires game version 1.1.641. Refuses to patch any other build.",
        description="""
    Enlarges the game's own UI - toolbars, dialogs, menus, icons and fonts -
    so the interface stays usable at modern resolutions, instead of scaling
    the whole frame and blurring the city.

    The scale factor is chosen automatically from the resolution the game
    actually renders at, and can be changed in-game under
    Options -> Graphic Options. Below 1320x900 the mod stays completely
    inert and the game is exactly stock.""",
    ),
    dict(
        name="sc4-ui-scale-mod-overrides",
        subfolder="900-overrides",
        dependencies=[f"{GROUP}:sc4-ui-scale"],
        file_roots=[],
        dir_roots=["zzz-SC4UIScale"],
        summary="Scaled UI artwork for CAM, NAM and other mods, for SC4UIScale",
        conflicts=None,
        description="""
    Enlarged copies of other mods' own interface artwork, so a scaled UI
    stays consistent when those mods are installed. Inert without them.

    Covers CAM, the Network Addon Mod, Save Warning, 36 Slot Building
    Styles, God Terraforming in Mayor Mode, and Scoty's Carbon Skin.
    Artwork belongs to those authors - see THIRD-PARTY-NOTICES.md.""",
    ),
]

# --------------------------------------------------------------------------
# INI POLICY.  Per-file, explicit, with the reason carried into the YAML.
#
# Default: SHIP NO INI AT ALL.  The reasons differ per file and two of them
# have a functional cost, so they are spelled out one by one rather than
# collapsed into "no inis".  `--ship-asset-inis` flips the two read-only
# asset inis back on (as `withChecksum` entries, NEVER `isIni: true`).
# --------------------------------------------------------------------------
INI_RULES = [
    (
        re.compile(r"^SC4UIScale\.ini$", re.I),
        "config",
        "the user-edited settings file. It must NOT ship under any\n"
        "mechanism: in the package folder every package UPDATE destroys it (the\n"
        "versioned folder is deleted wholesale), and `isIni: true` lands it at the\n"
        "Plugins root RENAMED to SC4UIScale_sc4pacnew.ini, never activated, and\n"
        "deleted on uninstall even after the user has edited it. The DLL creates\n"
        "SC4UIScale.ini at the Plugins root itself on first run - the only copy that\n"
        "survives both. This exclusion is unconditional.",
    ),
    (
        re.compile(r"^FontStyle-.+\.ini$", re.I),
        "asset",
        "a per-tier FontStyle SOURCE, read by the DLL out of this folder\n"
        "and copied over the live Plugins/FontStyle.ini at boot.\n"
        "⚠ COST OF EXCLUDING IT, measured in src/ScaleTier.cpp:1594-1611: with the\n"
        "source absent the DLL logs \"font source FontStyle<tag>.ini missing - text\n"
        "stays 1x\" and continues. An sc4pac install therefore gets a scaled UI with\n"
        "UNSCALED TEXT at every tier. It is read-only and never user-edited, so the\n"
        "UPDATE hazard above does not apply to it - an update re-extracts it.\n"
        "Re-enable with `gen_channel.py --ship-asset-inis`.",
    ),
    (
        re.compile(r"^z_SC4UIScale_FontStyle\.ini$", re.I),
        "asset",
        "the ZERO-BYTE placeholder whose only purpose (see\n"
        "_packaging/Build-Dist.ps1:207-252) is to give a package manager a file of\n"
        "ours to own, so uninstalling can remove the FontStyle.ini the DLL\n"
        "generates. It is deliberately NOT named FontStyle.ini - #182 proved a\n"
        "live-named empty font file crashes a vanilla game after a hand removal.\n"
        "⚠ COST OF EXCLUDING IT: the orphaned-FontStyle.ini problem it was added to\n"
        "solve comes back. Re-enable with `gen_channel.py --ship-asset-inis`.",
    ),
]


def ini_rule(basename):
    for pat, kind, reason in INI_RULES:
        if pat.match(basename):
            return kind, reason
    return None, None


# --------------------------------------------------------------------------
# PRESERVED PROSE - verbatim from the hand-written drexel-sc4-ui-scale.yaml.
# This is the record of what was MEASURED rather than assumed. Do not edit to
# "tidy"; the comment-preservation check exists to make a drop impossible to
# do silently.
# --------------------------------------------------------------------------
PRESERVED_HEADER = r"""# sc4pac channel metadata for SC4UIScale.
#
# STATUS: shape settled, blocked on ONE engine fact (probe #202, below).
# Everything sc4pac-side in this file was MEASURED against sc4pac 0.10.0 on
# 2026-08-29 by installing a throwaway local channel into a scratch plugins
# root - not read out of the docs and not inferred. Where a measurement
# contradicted the documentation, the measurement is what is encoded here.
#
# ============ WHAT WAS MEASURED, AND WHAT IT CHANGED ========================
#
# 1. ROOT PLACEMENT IS BY EXTENSION, NOT BY `withChecksum`.
#    sc4pac's own constant: (?:\.dat|\.sc4model|\.sc4lot|\.sc4desc|\.sc4|\.dll)$
#    A `.dll` lands at the Plugins ROOT with or without `isIni`. Everything
#    else stays in the package folder. That is exactly what SC4 requires of us
#    (dat scan recursive, DLL loader top-level only), so the DLL needs no
#    special handling - but it DOES need a `withChecksum` entry, because a file
#    listed only under `include:` was NOT INSTALLED AT ALL.
#
# 2. `isIni: true` IS A TRAP FOR US. It puts the ini at the root, but renamed
#    to `<stem>_sc4pacnew.ini`, and sc4pac never activates it - the user has to
#    rename it by hand. Worse, an uninstall deletes `*_sc4pacnew.ini` even
#    after the user edited it. So THIS PACKAGE SHIPS NO INI AT ALL; the DLL
#    creates SC4UIScale.ini at the Plugins root on first run. See the ini note
#    at the bottom - it reverses part of v4.4.0 and needs a decision.
#
# 3. A NON-CANONICAL EXTENSION INSTALLS ONLY VIA `withChecksum`. A `.uipay`
#    listed under `include:` was silently dropped; listed under `withChecksum`
#    it installed into the package folder. Every payload therefore needs its
#    own checksummed entry - there is no wildcard shortcut.
#
# 4. sc4pac PARSES EVERY SHIPPED `.dat` AS DBPF and aborts the install on a
#    bad one ("seems to contain a corrupted DBPF file"). Our `.off` payloads
#    must be real one-entry archives, which they are by construction.
#
# 5. AN UPDATE WIPES THE VERSIONED FOLDER. v1.0.0 -> v2.0.0 deletes
#    `<group>.<name>.1.0.0.sc4pac` wholesale and creates a 2.0.0 folder. Two
#    consequences, both already handled:
#      - The DLL's write target MOVES on every package update, because the
#        version is in the folder name. Our folder discovery finds our folders
#        BY CONTENT rather than by name (v4.5.0), so this costs nothing.
#      - Anything the DLL wrote into that folder is discarded. The arming pass
#        re-runs at every boot off a fingerprint, so it self-heals on the next
#        launch. This is WHY arming must be idempotent and fingerprint-driven.
#
# 6. NOTHING IN sc4pac VERIFIES INSTALLED BYTES. `update` says "Everything is
#    up-to-date" and `repair` says "Looking good" after the installed files
#    have been rewritten, and after an extra file is added to the package
#    folder. This is the fact the whole content-swap design rested on.
#    POSITIVE CONTROLS, because a silent tool proves nothing on its own:
#    `repair` DOES report a deleted package folder as [missing] and a stray
#    folder as [orphan], and checksum enforcement IS live - corrupting a file
#    inside the source archive aborts the install. Verification happens in the
#    staging directory, before the move into Plugins. So the null is real:
#    sc4pac looks, and deliberately does not look at content.
#
# 7. `group: a-drexel` PASSES LINT. The rule is
#    `[a-z0-9]+(?:-[a-z0-9]+)*`; the control (`A_Drexel`) fails it, exit 1.
#    ⚠ A DLL package additionally requires a group->GitHub-owner mapping
#    contributed to `lint-config.yaml` upstream, or lint refuses:
#    "GitHub account ... is not known to belong to group a-drexel".
#
# ============ WHY THE GROUP ID IS `a-drexel`, AND DO NOT "TIDY" IT ==========
#
# LOAD-BEARING. sc4pac sorts by `<group>.<name>` inside a subfolder, and the
# lowest canonical subfolder is `050-load-first`, where CAM lives. Our early
# package must load BEFORE CAM so it LOSES to CAM per-TGI - losing is the
# compatibility gate, not an accident. `a-drexel` sorts before `cam.*`;
# `drexel` does not, and renaming it inverts CAM precedence with no error
# anywhere. VERIFIED by per-TGI winner diff, not by argument:
# `python tools/uimap/winner_table.py --diff <live> <proposed> --ignore-moves`
# 1888 keys examined, 3/3 controls fired, and ZERO CAM keys changed hands.
#
# ============ THE ONE REMAINING BLOCKER ====================================
#
# PROBE #202, staged, needs one game launch:
#   `python _tests/Probe-ScanPredicate.py --stage | --read`
# Is SC4's plugin scan gated on EXTENSION or on DBPF MAGIC? If magic, `.uipay`
# payloads are live plugins - three tiers of every package permanently in the
# index - and this file's payload lists are void. `.dat.x1-disabled` being
# skipped proves one string is skipped; it is not proof about a different one.
# Do not publish this channel entry until #202 comes back extension-gated."""

PRESERVED_DLL_NOTE = r"""# Lands at the Plugins ROOT because it is a .dll. Required by SC4: the dat
# scan is recursive, the DLL loader is top-level only."""

PRESERVED_EARLY_INCLUDE_NOTE = r"""# Stock-derived art and scripts - DESIGNED TO LOSE to a real mod's own
# files. See the group-id note above for how that survives sc4pac."""

PRESERVED_OVERRIDE_INCLUDE_NOTE = r"""# Built FROM other mods' own artwork, so these must WIN - hence the last
# canonical subfolder. Gated AT RUNTIME on each mod's files by exact name
# and byte size, deliberately NOT as sc4pac dependencies: the gates must
# also work for hand-installed copies of those mods, a mod UPDATE must
# disable us (our copies hard-code its exact rects), and a hard dependency
# would mean uninstalling CAM drags this package with it."""

PRESERVED_TRAILER = r"""# ===========================================================================
# THE 900-overrides QUESTION, MEASURED AND CLOSED
#
# `900-overrides` is the last canonical subfolder, and sc4pac's own CLI README
# tells users to move their `zzz-` folders into `895-my-overrides` - i.e.
# BELOW it. So on a canonically migrated install our override package wins
# everything, exactly as `zzz-SC4UIScale\` does today.
#
# The residual exposure is a HYBRID install: digits sort before letters, so an
# un-migrated letter-named top-level folder out-sorts `900-overrides`.
# MEASURED on this machine, which has three of them (BSC, CSX, ~Documents):
#   proposed layout, tree as-is      : 9 keys lost, ALL UncoveredIcons, to
#                                      BSC prop packs
#   proposed layout, tree migrated   : 0 keys changed, 3/3 controls fired
# So the regression belongs to an incomplete sc4pac migration, not to this
# design, and the cure is documentation plus a boot-time census that names the
# offending folder instead of rendering wrong art silently.
#
# STILL OUTSTANDING
#   - probe #202 (above) - the only hard blocker.
#   - The real sha256 of the extracted DLL, and a real `lastModified`.
#   - A `group-to-github` mapping for `a-drexel` contributed upstream, which a
#     DLL package cannot pass lint without.
#   - THE INI DECISION. Shipping it in the package folder loses the user's
#     tier choice on every update (the folder is wiped); shipping it with
#     `isIni: true` lands it inert as `_sc4pacnew.ini` and deletes it on
#     uninstall even if edited. The measured-correct answer is that the DLL
#     creates SC4UIScale.ini at the Plugins ROOT and we ship no ini - which
#     partly reverses v4.4.0's "the root holds only the DLL", and is the one
#     thing here that is a judgement call rather than a measurement.
# ==========================================================================="""


# --------------------------------------------------------------------------
# Bundle scan
# --------------------------------------------------------------------------
class Fail(Exception):
    pass


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_version(bundle_dir):
    base = os.path.basename(os.path.normpath(bundle_dir))
    m = BUNDLE_DIR_RE.match(base)
    if not m:
        raise Fail(
            f"bundle directory name {base!r} is not <Product>-v<version>; "
            "pass --version and --product explicitly"
        )
    raw = m.group("version")
    release = PRERELEASE_RE.sub("", raw)
    return m.group("product"), raw, release


def scan(bundle_dir):
    """Walk <bundle>/Plugins and hand every file to exactly one package."""
    plugins = os.path.join(bundle_dir, "Plugins")
    if not os.path.isdir(plugins):
        raise Fail(f"no Plugins/ directory under {bundle_dir}")

    owner = {}          # top-level entry name -> package name
    for pkg in PACKAGES:
        for n in pkg["file_roots"] + pkg["dir_roots"]:
            if n in owner:
                raise Fail(f"root {n!r} claimed by two packages")
            owner[n] = pkg["name"]

    claims = {}         # rel posix path -> (pkg name, mechanism, abs path)
    orphans = []
    all_files = []

    for parent, dirs, files in os.walk(plugins):
        dirs.sort()
        for fn in sorted(files):
            abspath = os.path.join(parent, fn)
            rel = os.path.relpath(abspath, plugins).replace("\\", "/")
            all_files.append(rel)
            top = rel.split("/", 1)[0]
            pkg_name = owner.get(top)
            if pkg_name is None:
                orphans.append(rel)
                continue
            if "/" not in rel and top not in [
                n for p in PACKAGES for n in p["file_roots"]
            ]:
                orphans.append(rel)
                continue
            claims[rel] = (pkg_name, None, abspath)

    return plugins, all_files, claims, orphans


def classify(claims, ship_asset_inis):
    """Decide the INSTALL MECHANISM for each claimed file.

    Exactly one of:
      withChecksum   - the only thing that installs a non-canonical extension,
                       and the only thing that installs a .dll at all.
      include-dir    - a canonical extension covered by the folder pattern.
      excluded-ini   - deliberately not installed, with a stated reason.
    """
    for rel, (pkg_name, _, abspath) in list(claims.items()):
        base = os.path.basename(rel)
        if base.lower().endswith(".ini"):
            kind, reason = ini_rule(base)
            if kind is None:
                raise Fail(
                    f"{rel}: an .ini with no rule in INI_RULES. Add one (with its "
                    "reason) rather than letting it fall through - the ini policy "
                    "is per-file on purpose."
                )
            if kind == "asset" and ship_asset_inis:
                claims[rel] = (pkg_name, "withChecksum", abspath)
            else:
                claims[rel] = (pkg_name, "excluded-ini", abspath)
        elif base.lower().endswith(".dll"):
            claims[rel] = (pkg_name, "withChecksum", abspath)
        elif CANONICAL_EXT_RE.search(base):
            claims[rel] = (pkg_name, "include-dir", abspath)
        else:
            claims[rel] = (pkg_name, "withChecksum", abspath)
    return claims


# --------------------------------------------------------------------------
# Emission
# --------------------------------------------------------------------------
def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def group_line_note():
    return [
        "# GROUP ID: LOAD-BEARING, DO NOT \"TIDY\". sc4pac sorts by `<group>.<name>`",
        "# inside a subfolder, so `a-drexel` sorts before `cam.*` and this package",
        "# loads BEFORE CAM - which means it LOSES to CAM per-TGI. That losing IS the",
        "# compatibility gate. Renaming the group to `drexel` inverts CAM precedence",
        "# with no error anywhere. Verified by per-TGI winner-table diff: 1888 keys",
        "# examined, 3/3 controls fired, ZERO CAM keys changed hands.",
    ]


def emit(bundle_dir, product, raw_version, version, last_modified, claims,
         asset_id, sums, ship_asset_inis, group=GROUP):
    L = []
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L += [
        "# ###########################################################################",
        "# GENERATED FILE - do not hand-edit; your edit is lost on the next build.",
        f"#   generator : tools/sc4pac/gen_channel.py",
        f"#   bundle    : {os.path.basename(os.path.normpath(bundle_dir))}",
        f"#   generated : {stamp}",
        "# The prose below is carried verbatim from the hand-written version of this",
        "# file. The generator refuses to write output that drops any of it.",
        "# ###########################################################################",
        "#",
    ]
    L += PRESERVED_HEADER.split("\n")
    L += [
        "#",
        "# ============ WHAT THE GENERATOR ADDS ======================================",
        "#",
        "# The payload lists below are MACHINE-GENERATED from the built bundle named",
        "# at the top of this file. Every sha256 was computed from a file that exists",
        "# in that bundle, and re-verified by re-hashing after the YAML was written.",
        "# The bundle's own SHA256SUMS.txt is NOT used as a source - in the v4.5.0-dev",
        "# bundle it still describes the pre-payload layout and is stale.",
        "#",
        "# Regenerate with:",
        "#   python tools/sc4pac/gen_channel.py --bundle dist/<Product>-v<version>",
        "#",
    ]
    L.append("")
    L += group_line_note()

    for i, pkg in enumerate(PACKAGES):
        if i:
            L += ["", "---", ""]
            L += group_line_note()
        L.append(f"group: {q(group)}")
        L.append(f"name: {q(pkg['name'])}")
        L.append(f"version: {q(version)}")
        L.append(f"subfolder: {q(pkg['subfolder'])}")
        if pkg["dependencies"]:
            L.append("dependencies:")
            for d in pkg["dependencies"]:
                L.append(f"- {q(d)}")
        L.append("assets:")
        L.append(f"- assetId: {q(asset_id)}")

        mine = {r: v for r, v in claims.items() if v[0] == pkg["name"]}

        # DLL first, then any shipped asset ini, then the payloads: the two
        # special cases carry their own explanation and belong at the top.
        def wc_key(rel):
            b = os.path.basename(rel).lower()
            return (0 if b.endswith(".dll") else 1 if b.endswith(".ini") else 2, rel)

        wc = sorted((r for r, v in mine.items() if v[1] == "withChecksum"), key=wc_key)
        ex = sorted(r for r, v in mine.items() if v[1] == "excluded-ini")

        if wc:
            L.append("  withChecksum:")
            first_payload_note_done = False
            for rel in wc:
                base = os.path.basename(rel)
                if base.lower().endswith(".dll"):
                    L += ["  " + c for c in PRESERVED_DLL_NOTE.split("\n")]
                    L.append("  # It ALSO needs the checksum for a second, measured reason: a file")
                    L.append("  # listed only under `include:` was NOT INSTALLED AT ALL.")
                elif base.lower().endswith(".ini"):
                    L.append("  # Shipped by --ship-asset-inis. NOTE: no `isIni: true` - that lands the")
                    L.append("  # file at the Plugins root renamed `_sc4pacnew.ini` and never activates")
                    L.append("  # it. This keeps it in the package folder, where the DLL reads it.")
                elif not first_payload_note_done:
                    first_payload_note_done = True
                    L.append("  # PAYLOADS. `.uipay` is a NON-CANONICAL extension: measured against")
                    L.append("  # sc4pac 0.10.0, such a file is silently DROPPED when listed under")
                    L.append("  # `include:` and installs only through a `withChecksum` entry. There is")
                    L.append("  # no wildcard shortcut, so each one is listed individually. Inert by")
                    L.append("  # construction - the DLL arms one per package at boot.")
                L.append(f"  - include: {q('/Plugins/' + rel)}")
                L.append(f"    sha256: {q(sums[rel])}")

        L.append("  include:")
        if pkg["name"] == PACKAGES[0]["name"]:
            L += ["  " + c for c in PRESERVED_EARLY_INCLUDE_NOTE.split("\n")]
        else:
            L += ["  " + c for c in PRESERVED_OVERRIDE_INCLUDE_NOTE.split("\n")]
        L.append("  # The live `.dat` of each package installs through this folder pattern;")
        L.append("  # `.dat` is one of sc4pac's canonical extensions, so it needs no checksum.")
        for d in pkg["dir_roots"]:
            L.append(f"  - {q('/Plugins/' + d + '/')}")

        if ex:
            L.append("  exclude:")
            L.append("  # NO INI SHIPS. Each exclusion below states what the file was for and")
            L.append("  # what excluding it costs, because two of them have a functional cost.")
            for rel in ex:
                base = os.path.basename(rel)
                _, reason = ini_rule(base)
                for cl in (f"{base} is {reason}").split("\n"):
                    L.append(("  # " + cl).rstrip())
                L.append(f"  - {q('/Plugins/' + rel)}")

        L.append("info:")
        L.append(f"  summary: {q(pkg['summary'])}")
        if pkg["conflicts"]:
            L.append(f"  conflicts: {q(pkg['conflicts'])}")
        L.append("  description: |2")
        L += pkg["description"].split("\n")
        L.append(f"  author: {q(GITHUB_OWNER)}")
        L.append(f"  website: {q(f'https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}')}")

    L += ["", "---", ""]
    L += [
        "# THE ASSET. One zip serves both packages.",
    ]
    if raw_version != version:
        L += [
            f"# ⚠ The source bundle is a PRE-RELEASE build ({raw_version}). The release",
            f"#   marker was stripped for the tag and the URL, so this points at tag",
            f"#   v{version}, which does not exist until that release is published.",
        ]
    L += [
        "# ⚠ `lastModified` is the newest file mtime in the bundle, used as a",
        "#   placeholder. Re-stamp it from the published release asset before the",
        "#   channel goes live.",
    ]
    L.append(f"assetId: {q(asset_id)}")
    L.append(f"version: {q(version)}")
    L.append(f"lastModified: {q(last_modified)}")
    L.append(
        "url: "
        + q(
            f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/"
            f"v{version}/{product}-v{version}.zip"
        )
    )
    L.append("")
    L += PRESERVED_TRAILER.split("\n")
    L += [
        "",
        "# ===========================================================================",
        "# GENERATOR ADDENDUM to STILL OUTSTANDING, above. Nothing there was deleted;",
        "# this records which of those items the generated file has since closed.",
        "#   CLOSED  - the real sha256 of the DLL, and of every payload, is now",
        "#             computed from the bundle on every run.",
        "#   OPEN    - `lastModified` is still a placeholder (bundle mtime).",
        "#   OPEN    - probe #202. Unchanged, and still the only hard blocker.",
        "#   OPEN    - the `group-to-github` mapping for `a-drexel`. Lint still",
        "#             refuses without it; the fix is upstream, NOT a group rename.",
        "#   CHANGED - THE INI DECISION is now executed, per-file, in the `exclude:`",
        "#             blocks above. SC4UIScale.ini is excluded unconditionally and",
        "#             that is measured-correct. The other two inis are excluded by",
        "#             the same blanket rule but are NOT the same case: they are",
        "#             read-only assets an update simply re-extracts, and excluding",
        "#             them costs unscaled text (FontStyle-*.ini) and the orphaned",
        "#             FontStyle.ini that the empty placeholder was added to solve.",
        "#             `gen_channel.py --ship-asset-inis` ships those two and only",
        "#             those two. This one needs a human decision.",
        "# ===========================================================================",
    ]
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------
# Self-checks
# --------------------------------------------------------------------------
# The two banner fields that legitimately change on every run. Excluded from
# the preservation comparison, or the check would fail on its own timestamp on
# the second run - which would train everyone to pass --allow-comment-loss and
# would destroy the check. Nothing else is exempt.
VOLATILE_COMMENT_RE = re.compile(r"^#\s+(?:generated|bundle)\s*:")


def comment_lines(text):
    return [
        ln.rstrip()
        for ln in text.split("\n")
        if ln.lstrip().startswith("#") and not VOLATILE_COMMENT_RE.match(ln.strip())
    ]


def tree_fingerprint(plugins_dir):
    """(relpath -> size, mtime) for every file under Plugins.

    Taken before hashing and again after the YAML is built. If it moved, the
    bundle was being rebuilt underneath the run and the manifest would be
    TORN - some hashes from before the rebuild, some from after. Observed for
    real on 2026-08-29, when a rebuild landed mid-run and the payloads briefly
    vanished. A torn manifest passes every other check in this file, so this
    is the only thing that can catch it.
    """
    out = {}
    for parent, _dirs, files in os.walk(plugins_dir):
        for f in files:
            fp = os.path.join(parent, f)
            try:
                st = os.stat(fp)
                out[os.path.relpath(fp, plugins_dir)] = (st.st_size, st.st_mtime_ns)
            except OSError:
                out[os.path.relpath(fp, plugins_dir)] = None
    return out


def verify_emitted_checksums(text, plugins_dir):
    """Read the sha256 entries back OUT of the emitted YAML and re-hash.

    Deliberately parses the OUTPUT rather than trusting the in-memory model:
    the thing that ships is the file, so the file is what gets measured.
    """
    pairs = re.findall(
        r'^\s*- include: "(/Plugins/[^"]+)"\n\s*sha256: "([0-9a-f]{64})"$',
        text,
        re.M,
    )
    problems = []
    for inc, digest in pairs:
        rel = inc[len("/Plugins/"):]
        p = os.path.join(plugins_dir, rel.replace("/", os.sep))
        if not os.path.isfile(p):
            problems.append(f"{inc}: NO SUCH FILE in the bundle")
            continue
        again = sha256_of(p)
        if again != digest:
            problems.append(f"{inc}: sha256 mismatch on re-hash ({digest} != {again})")
    return len(pairs), problems


def main(argv):
    ap = argparse.ArgumentParser(description="Generate sc4pac channel metadata for SC4UIScale.")
    ap.add_argument("--bundle", required=True, help="built bundle directory, e.g. dist/SC4UIScale-v4.5.0-dev")
    ap.add_argument("--out", default=None, help=f"output yaml (default <repo>/{OUT_RELPATH})")
    ap.add_argument("--version", default=None, help="override the release version discovered from the bundle name")
    ap.add_argument("--last-modified", default=None, help="override the asset lastModified stamp")
    ap.add_argument("--group", default=GROUP, help="override the group id (used ONLY for the deliberately-broken lint control)")
    ap.add_argument("--ship-asset-inis", action="store_true",
                    help="also ship the read-only FontStyle sources and the empty placeholder (never the user config ini)")
    ap.add_argument("--allow-comment-loss", action="store_true",
                    help="permit the new output to drop comment lines the old one had")
    ap.add_argument("--check-only", action="store_true", help="run every check, print the report, write nothing")
    args = ap.parse_args(argv)

    try:
        bundle = os.path.abspath(args.bundle)
        if not os.path.isdir(bundle):
            raise Fail(f"no such bundle directory: {bundle}")
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        out = os.path.abspath(args.out) if args.out else os.path.join(repo, OUT_RELPATH)

        product, raw_version, release_version = discover_version(bundle)
        version = args.version or release_version

        plugins, all_files, claims, orphans = scan(bundle)

        print(f"bundle          : {bundle}")
        print(f"product/version : {product} / raw={raw_version} release={version}")
        print(f"files under Plugins/: {len(all_files)}")

        # ---- COVERAGE ----------------------------------------------------
        if orphans:
            print(f"ORPHANS ({len(orphans)}) - claimed by no package:")
            for o in orphans:
                print(f"   {o}")
            raise Fail(
                f"{len(orphans)} file(s) under Plugins/ are claimed by no package. "
                "Add the root to PACKAGES or the run cannot be trusted."
            )
        missing = set(all_files) - set(claims)
        if missing:
            raise Fail(f"internal: {len(missing)} files neither claimed nor orphaned: {sorted(missing)[:5]}")
        print(f"COVERAGE        : {len(claims)}/{len(all_files)} files claimed, 0 orphans")

        claims = classify(claims, args.ship_asset_inis)

        by_mech = {}
        for rel, (pkg_name, mech, _) in claims.items():
            by_mech.setdefault(mech, []).append(rel)
        for mech in sorted(by_mech):
            print(f"   {mech:<14}: {len(by_mech[mech])}")
        for pkg in PACKAGES:
            n = sum(1 for v in claims.values() if v[0] == pkg["name"])
            print(f"   {pkg['name']:<28}: {n} files")

        # ---- HASH --------------------------------------------------------
        fp_before = tree_fingerprint(plugins)
        sums = {}
        for rel, (_, mech, abspath) in sorted(claims.items()):
            if mech == "withChecksum":
                if not os.path.isfile(abspath):
                    raise Fail(f"{rel}: vanished between scan and hash")
                sums[rel] = sha256_of(abspath)
        print(f"CHECKSUMS       : {len(sums)} computed")

        # ---- lastModified ------------------------------------------------
        if args.last_modified:
            last_modified = args.last_modified
        else:
            newest = max(os.path.getmtime(v[2]) for v in claims.values())
            last_modified = _dt.datetime.fromtimestamp(
                newest, _dt.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

        asset_id = f"{args.group}-{PACKAGES[0]['name']}"
        text = emit(bundle, product, raw_version, version, last_modified,
                    claims, asset_id, sums, args.ship_asset_inis, group=args.group)

        # ---- CHECKSUM RE-VERIFY, off the emitted text --------------------
        n_pairs, problems = verify_emitted_checksums(text, plugins)
        if n_pairs != len(sums):
            raise Fail(f"emitted YAML carries {n_pairs} checksum entries, expected {len(sums)}")
        if problems:
            for p in problems:
                print(f"   {p}")
            raise Fail(f"{len(problems)} emitted sha256 entries failed re-verification")
        print(f"RE-VERIFIED     : {n_pairs}/{n_pairs} emitted sha256 entries re-hashed and matched")

        # ---- TORN-READ GUARD ---------------------------------------------
        fp_after = tree_fingerprint(plugins)
        if fp_after != fp_before:
            moved = sorted(set(fp_before) ^ set(fp_after)) + sorted(
                k for k in set(fp_before) & set(fp_after) if fp_before[k] != fp_after[k]
            )
            for k in moved[:20]:
                print(f"   moved: {k}")
            raise Fail(
                f"the bundle changed under the run ({len(moved)} file(s) added, removed "
                "or rewritten while hashing). The manifest would be TORN. Wait for the "
                "build to finish and re-run."
            )
        print(f"STABLE          : bundle unchanged across the run ({len(fp_after)} files)")

        # ---- COMMENT PRESERVATION ----------------------------------------
        if os.path.isfile(out):
            old = comment_lines(open(out, encoding="utf-8").read())
            new = set(comment_lines(text))
            dropped = [c for c in old if c not in new]
            if dropped:
                print(f"COMMENTS DROPPED ({len(dropped)}) vs {out}:")
                for c in dropped:
                    print(f"   {c}")
                if not args.allow_comment_loss:
                    raise Fail(
                        f"{len(dropped)} comment line(s) from the existing output would be "
                        "lost. Those comments are the measurement record. Carry them into "
                        "the generator, or pass --allow-comment-loss deliberately."
                    )
            else:
                print(f"COMMENTS        : all {len(old)} comment lines of the previous output preserved")
        else:
            print("COMMENTS        : no previous output to compare against (first run)")

        # ---- WRITE -------------------------------------------------------
        if args.check_only:
            print("check-only: nothing written")
            return 0
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"WROTE           : {out} ({len(text.splitlines())} lines)")
        return 0

    except Fail as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
