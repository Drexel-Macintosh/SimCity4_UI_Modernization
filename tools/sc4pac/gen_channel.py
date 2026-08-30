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
sha256.  That is ~80 entries whose hashes change on every build (the exact
count is printed by every run): not a hand-maintained list.

Two outputs
-----------
The default output is the ANNOTATED INTERNAL file (the measurement record,
211+ comment lines).  `--publish` additionally writes a LEAN file for the
upstream channel PR - same model, same hashes, corpus-normal comment volume.
v4.5.1's PR #199 shipped the internal file verbatim, engineering commentary
and a "Do not publish" line included; the lean emitter exists so that can
never happen again.  `--publish` refuses to run without `--last-modified`
(the release publish time from the GitHub API).

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
# The corpus convention is a display name, not a handle (cf. "Null 45",
# "CasperVg", "memo, Panda").
AUTHOR_DISPLAY = "Drexel Macintosh"
OUT_RELPATH = os.path.join("_packaging", "sc4pac", "drexel-sc4-ui-scale.yaml")
PUBLISH_RELPATH = os.path.join("_packaging", "sc4pac", "publish", "sc4-ui-scale.yaml")

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
        conflicts="Only compatible with game version 1.1.641, the Windows digital edition.",
        warning=None,
        # "Below <WxH>" is gated against kTierMinimums in src/ScaleTier.cpp on
        # every run - v4.5.1 published "below 1320x900" (the pre-audit
        # 880*f/600*f formula) against a measured 1440x1080 floor.
        description="""
    Enlarges the game's own UI - toolbars, dialogs, menus, icons and fonts -
    so the interface stays usable at modern resolutions, instead of scaling
    the whole frame and blurring the city.

    - The scale factor (1.5x / 2x / 3x) is chosen automatically from the
      resolution the game actually renders at, and can be changed in-game
      under *Options > Graphic Options*.
    - Below 1440x1080 the mod stays completely inert and the game is
      exactly stock.
    - On first launch the mod writes its settings file `SC4UIScale.ini` at
      the Plugins root (a file kept in the package folder would be deleted
      by every update). Settings survive updates; the file stays behind on
      uninstall and can be deleted by hand.""",
    ),
    dict(
        name="sc4-ui-scale-mod-overrides",
        subfolder="900-overrides",
        dependencies=[f"{GROUP}:sc4-ui-scale"],
        file_roots=[],
        dir_roots=["zzz-SC4UIScale"],
        summary="Scaled UI artwork for CAM, NAM and other mods, for SC4UIScale",
        conflicts=None,
        warning=(
            "Letter-named top-level override folders from a hand install "
            "(e.g. zzz-...) sort after 900-overrides and can beat this "
            "package's artwork. If you migrated from a hand install, move "
            "them into 895-my-overrides as the sc4pac docs recommend."
        ),
        description="""
    Enlarged copies of other mods' own interface artwork, so a scaled UI
    stays consistent when those mods are installed. Inert without them.

    Covers the Colossus Addon Mod, the Network Addon Mod, Save Warning,
    36 Slot Building Styles, God Terraforming in Mayor Mode, and Scoty's
    Carbon Skin. The artwork belongs to those authors - see
    THIRD-PARTY-NOTICES.md, installed in this package's folder.""",
    ),
]

# --------------------------------------------------------------------------
# INI POLICY.  Per-file, explicit, with the reason carried into the YAML.
#
# Default: the user CONFIG ini never ships; the two read-only ASSET inis
# ship by default (as `withChecksum` entries, NEVER `isIni: true`) because
# excluding them has a measured functional cost - unscaled text at every
# tier. `--no-asset-inis` excludes them; nothing ever ships the config ini.
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
        "⚠ COST OF EXCLUDING IT (grep src/ScaleTier.cpp for the string): with the\n"
        "source absent the DLL logs \"font source FontStyle<tag>.ini missing - text\n"
        "stays 1x\" and continues. An sc4pac install therefore gets a scaled UI with\n"
        "UNSCALED TEXT at every tier. It is read-only and never user-edited, so the\n"
        "UPDATE hazard above does not apply to it - an update re-extracts it.\n"
        "Shipped by default since v4.5.2; excluded only by --no-asset-inis.",
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
        "solve comes back. Shipped by default since v4.5.2 (--no-asset-inis excludes).",
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
PRESERVED_HEADER = r"""# sc4pac channel metadata for SC4UIScale - THE ANNOTATED INTERNAL RECORD.
#
# STATUS: SHIPPED (v4.5.1+). Every one-time blocker recorded below is CLOSED
# (see the closure record at the bottom); the measurement record itself is
# kept verbatim. THE FILE THAT GOES UPSTREAM IS NOT THIS ONE - it is the lean
# file emitted by `gen_channel.py --publish`, same model and hashes, without
# the engineering commentary. PR #199 shipped this internal file verbatim,
# which is why that distinction now exists.
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
#    after the user edited it. So NO SETTINGS INI SHIPS; the DLL creates
#    SC4UIScale.ini at the Plugins root on first run - the only copy that
#    survives updates AND uninstall. (The read-only FontStyle asset inis are
#    a separate case with their own rules - see INI_RULES in the generator.)
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
# ============ PROBE #202 - WAS THE ONE BLOCKER, NOW CLOSED =================
#
# PROBE #202 (`python _tests/Probe-ScanPredicate.py --stage | --read`) asked:
# is SC4's plugin scan gated on EXTENSION or on DBPF MAGIC? If magic, `.uipay`
# payloads would be live plugins - three tiers of every package permanently in
# the index - and this file's payload lists would be void. `.dat.x1-disabled`
# being skipped proves one string is skipped; it is not proof about another.
# MEASURED 2026-08-30, one game launch: the scan is EXTENSION-gated. The
# payload lists in this file are sound, and the publish embargo that stood
# here is lifted."""

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
# FORMERLY OUTSTANDING - ALL CLOSED (the list is kept so the closures have
# their questions next to them; nothing here is open):
#   - probe #202: CLOSED, extension-gated - measured 2026-08-30, see above.
#   - The real sha256 of the DLL and every payload: CLOSED - computed from
#     the bundle on every run and re-verified off the emitted YAML.
#   - `lastModified`: CLOSED - the release publish time from the GitHub API,
#     passed with --last-modified (which `--publish` REQUIRES; without it the
#     internal file carries the bundle mtime as a marked placeholder).
#   - The `group-to-github` mapping for `a-drexel`: submitted with the
#     package in one PR (upstream precedent: PR #164). Lint verified locally
#     against the full corpus, positive control fired.
#   - THE INI DECISION: CLOSED, executed per-file in the generator's
#     INI_RULES. The DLL creates SC4UIScale.ini at the Plugins ROOT and no
#     settings ini ships - the only shape that survives both updates and
#     uninstall. When an excluded ini is present in a bundle the YAML carries
#     an `exclude:` block stating the reason; the v4.5.1+ bundle ships no
#     settings ini at all, so no exclude block appears - earlier notes
#     pointing at "the exclude blocks above" described a bundle shape that no
#     longer exists.
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
         asset_id, sums, ship_asset_inis, group=GROUP,
         real_last_modified=False):
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
            return (0 if b.endswith(".dll") else 1 if b.endswith(".ini")
                    else 2 if b.endswith(".md") else 3, rel)

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
                elif base.lower().endswith(".md"):
                    L.append("  # Third-party artwork attribution, installed beside the art it covers.")
                    L.append("  # It lives INSIDE the dir root on purpose: a bundle-root extra file")
                    L.append("  # would change this package's longest-common-prefix and re-root the")
                    L.append("  # whole install one level deeper (the v4.5.0 discovery trap, again).")
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
        if pkg.get("warning"):
            L.append(f"  warning: {q(pkg['warning'])}")
        if pkg["conflicts"]:
            L.append(f"  conflicts: {q(pkg['conflicts'])}")
        L.append("  description: |2")
        L += pkg["description"].split("\n")
        L.append(f"  author: {q(AUTHOR_DISPLAY)}")
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
    if not real_last_modified:
        L += [
            "# ⚠ `lastModified` is the newest file mtime in the bundle, used as a",
            "#   placeholder. Re-stamp it from the published release asset before the",
            "#   channel goes live.",
        ]
    L.append(f"assetId: {q(asset_id)}")
    L.append(f"version: {q(version)}")
    if real_last_modified:
        # Emitted, not hand-added afterwards. The v4.5.0 entry carried these two
        # comments because someone typed them into a GENERATED file, and the
        # comment-preservation check then blocked the next run rather than lose
        # them - which is exactly what it is for. The generator owns them now.
        L += [
            "# The RELEASE publish time from the GitHub API, not a file mtime. sc4pac uses",
            "# this to decide whether a cached asset is stale, so it has to move when the",
            "# asset does.",
        ]
    L.append(f"lastModified: {q(last_modified)}")
    L.append(
        "url: "
        + q(
            f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/"
            f"v{version}/{product}-v{version}.zip"
        )
    )
    L += [
        "# No `nonPersistentUrl`: docs/metadata.md scopes that field to a SECOND",
        "# host's page (e.g. url on GitHub, nonPersistentUrl on Simtropolis) and the",
        "# update checkers only consume STEX/SC4E links. GitHub is our only host, so",
        "# the field would be noise - v4.5.1 carried a same-host HTML page here under",
        "# an invented rationale, corrected on the corpus survey of 2026-08-30.",
    ]
    L.append("")
    L += PRESERVED_TRAILER.split("\n")
    return "\n".join(L) + "\n"


def emit_lean(bundle_dir, product, version, last_modified, claims, asset_id,
              sums, group=GROUP):
    """The file that goes UPSTREAM. Same model and hashes as the internal
    file, corpus-normal comment volume (the 693-file survey put the median at
    0 comment lines and the busiest DLL package at 44; the internal file's
    211 made PR #199 read as a leaked engineering document). Only the load-
    bearing facts a channel maintainer needs survive as comments."""
    L = [
        f"# Generated by tools/sc4pac/gen_channel.py --publish from "
        f"{os.path.basename(os.path.normpath(bundle_dir))}; do not hand-edit.",
    ]
    for i, pkg in enumerate(PACKAGES):
        if i:
            L += ["", "---", ""]
        L.append(f"group: {q(group)}")
        L.append(f"name: {q(pkg['name'])}")
        L.append(f"version: {q(version)}")
        if i == 0:
            L.append("# 050-load-first and the group id are load-bearing: `a-drexel.*` sorts")
            L.append("# before `cam.*`, so this package loads BEFORE (and per-TGI loses to) CAM.")
            L.append("# Losing is the compatibility gate - the art is stock-derived and a real")
            L.append("# mod's own files must win. The override half ships separately below.")
        else:
            L.append("# Built FROM other mods' own artwork, so it must WIN - hence the last")
            L.append("# canonical subfolder. Gated at RUNTIME on each mod's files (also works")
            L.append("# for hand-installed mods; a hard dependency would drag this package")
            L.append("# along when e.g. CAM is uninstalled).")
        L.append(f"subfolder: {q(pkg['subfolder'])}")
        if pkg["dependencies"]:
            L.append("dependencies:")
            for d in pkg["dependencies"]:
                L.append(f"- {q(d)}")
        L.append("assets:")
        L.append(f"- assetId: {q(asset_id)}")

        mine = {r: v for r, v in claims.items() if v[0] == pkg["name"]}

        def wc_key(rel):
            b = os.path.basename(rel).lower()
            return (0 if b.endswith(".dll") else 1 if b.endswith(".ini")
                    else 2 if b.endswith(".md") else 3, rel)

        wc = sorted((r for r, v in mine.items() if v[1] == "withChecksum"), key=wc_key)
        if wc:
            L.append("  withChecksum:")
            payload_note_done = False
            for rel in wc:
                base = os.path.basename(rel)
                if base.lower().endswith(".dll"):
                    L.append("  # The DLL must land at the Plugins root (SC4 loads DLLs from the top")
                    L.append("  # level only); .dll is root-placed by extension, and the checksum is")
                    L.append("  # required for a code mod.")
                elif base.lower().endswith(".uipay") and not payload_note_done:
                    payload_note_done = True
                    L.append("  # Inert per-tier payloads (non-canonical extension, so each needs its")
                    L.append("  # own checksummed entry). The DLL copies the matching one over the")
                    L.append("  # package's stable .dat at boot; filenames never change, so uninstall")
                    L.append("  # removes exactly what was installed.")
                L.append(f"  - include: {q('/Plugins/' + rel)}")
                L.append(f"    sha256: {q(sums[rel])}")

        L.append("  include:")
        for d in pkg["dir_roots"]:
            L.append(f"  - {q('/Plugins/' + d + '/')}")

        L.append("info:")
        L.append(f"  summary: {q(pkg['summary'])}")
        if pkg.get("warning"):
            L.append(f"  warning: {q(pkg['warning'])}")
        if pkg["conflicts"]:
            L.append(f"  conflicts: {q(pkg['conflicts'])}")
        L.append("  description: |2")
        L += pkg["description"].split("\n")
        L.append(f"  author: {q(AUTHOR_DISPLAY)}")
        L.append(f"  website: {q(f'https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}')}")

    L += ["", "---", ""]
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
    # DEFAULT ON since v4.5.2. The v4.5.1 channel shipped WITH the asset inis
    # (85 checksums = 81 + the 4 FontStyle files) - they are what scales the
    # text - but the flag defaulted OFF, so one forgotten flag on a future
    # regeneration would have silently shipped a channel with unscaled text
    # at every tier, and every count floor would still have passed. The
    # hazardous direction is now the one that needs the explicit flag.
    ap.add_argument("--ship-asset-inis", dest="ship_asset_inis",
                    action="store_true", default=True,
                    help="(default) ship the read-only FontStyle sources and the empty placeholder (never the user config ini)")
    ap.add_argument("--no-asset-inis", dest="ship_asset_inis",
                    action="store_false",
                    help="exclude the asset inis - COSTS UNSCALED TEXT at every tier; measured, not hypothetical")
    ap.add_argument("--allow-comment-loss", action="store_true",
                    help="permit the new output to drop comment lines the old one had")
    ap.add_argument("--publish", action="store_true",
                    help=f"ALSO write the lean upstream file ({PUBLISH_RELPATH}); requires --last-modified")
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

        if args.publish and not args.last_modified:
            raise Fail(
                "--publish requires --last-modified (the release publish time "
                "from the GitHub API: gh api repos/OWNER/REPO/releases/tags/vX "
                "--jq .published_at). The upstream file must never carry a "
                "bundle-mtime placeholder."
            )

        # ---- DESCRIPTION-VS-SOURCE GATE ---------------------------------
        # The published description states the minimum resolution; the
        # authority is kTierMinimums in src/ScaleTier.cpp. v4.5.1 published
        # "below 1320x900" (the pre-audit 880*f/600*f formula) against a
        # measured floor of 1440x1080 - a threshold nobody re-checked after
        # the thresholds were re-measured. THRESHOLDS COME FROM CONTROLS.
        tier_src_path = os.path.join(repo, "src", "ScaleTier.cpp")
        tier_src = open(tier_src_path, encoding="utf-8").read()
        mrow = re.search(r"\{\s*1\.5f\s*,\s*(\d+)\s*,\s*(\d+)\s*\}", tier_src)
        if not mrow:
            raise Fail("could not read the 1.5x row of kTierMinimums from src/ScaleTier.cpp")
        floor = f"{mrow.group(1)}x{mrow.group(2)}"
        for pkg in PACKAGES:
            for stated in re.findall(r"[Bb]elow (\d+x\d+)", pkg["description"]):
                if stated != floor:
                    raise Fail(
                        f"{pkg['name']}: description says 'below {stated}' but "
                        f"kTierMinimums' 1.5x row is {floor} - fix the "
                        "description in PACKAGES, never the source."
                    )
        print(f"MIN-RES GATE    : description floor {floor} matches kTierMinimums")

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
                    claims, asset_id, sums, args.ship_asset_inis, group=args.group,
                    real_last_modified=bool(args.last_modified))

        lean_text = None
        if args.publish:
            lean_text = emit_lean(bundle, product, version, last_modified,
                                  claims, asset_id, sums, group=args.group)

        # ---- CHECKSUM RE-VERIFY, off the emitted text --------------------
        # Both outputs, not just the internal one: the lean file is the one
        # that ships upstream, so it is the one that most needs measuring.
        for label, doc in (("internal", text), ("lean", lean_text)):
            if doc is None:
                continue
            n_pairs, problems = verify_emitted_checksums(doc, plugins)
            if n_pairs != len(sums):
                raise Fail(f"{label} YAML carries {n_pairs} checksum entries, expected {len(sums)}")
            if problems:
                for p in problems:
                    print(f"   {p}")
                raise Fail(f"{len(problems)} {label} sha256 entries failed re-verification")
            print(f"RE-VERIFIED     : {n_pairs}/{n_pairs} {label} sha256 entries re-hashed and matched")

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
        if lean_text is not None:
            lean_out = os.path.join(repo, PUBLISH_RELPATH)
            os.makedirs(os.path.dirname(lean_out), exist_ok=True)
            with open(lean_out, "w", encoding="utf-8", newline="\n") as f:
                f.write(lean_text)
            n_comments = sum(1 for ln in lean_text.split("\n")
                             if ln.lstrip().startswith("#"))
            print(f"WROTE           : {lean_out} "
                  f"({len(lean_text.splitlines())} lines, {n_comments} comment lines)")
        return 0

    except Fail as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # A cp1252 console cannot print the U+26A0 in the preserved prose; the
    # 2026-08-30 run CRASHED mid-report while echoing dropped comment lines
    # and wrote nothing. The report must never be the thing that fails.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    sys.exit(main(sys.argv[1:]))
