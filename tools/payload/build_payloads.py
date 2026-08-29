#!/usr/bin/env python3
"""Convert the tier-tagged dat layout into the CONTENT-SWAP payload layout.

WHY THIS EXISTS. The mod arms a scale tier by RENAMING its own dats
(`.dat` <-> `.dat.x1-disabled`). That rename is the single reason sc4pac
cannot uninstall this mod cleanly: the package manager removes files by the
exact name it recorded installing, and AutoScale rewrites those names on the
player's FIRST LAUNCH. The replacement is one live `z_SC4UIScale_<Pkg>.dat`
per package whose BYTES the DLL overwrites from an inert payload file the
game never loads. `src/ScaleTier.cpp` already pilots the stable-filename half
for SelectiveArt (`SyncDatStable`, v4.0.3); this tool builds the payload half
for every package.

TWO ENGINE FACTS THIS RESTS ON, both measured by `_tests/Probe-ScanPredicate.py`
(#202) on this machine, not assumed:

  * SC4's plugin scan is EXTENSION-GATED, not magic-gated. A real DBPF copied
    to `.uipay` did NOT appear in the game's registered-segment census while
    our live `.dat` files did - 13 of them, which was the positive control
    proving the census could have seen it. So `.uipay` is inert by extension.
  * A ONE-ENTRY DBPF loads cleanly and registers as a segment. That is what
    makes a gated-OFF package shippable as real content instead of as a
    missing or empty file.

WHAT IT EMITS, per package base `z_SC4UIScale_<Pkg>`:

    z_SC4UIScale_<Pkg>.15x.uipay   byte-for-byte copy of <Pkg>-15x.dat
    z_SC4UIScale_<Pkg>.2x.uipay    byte-for-byte copy of <Pkg>-2x.dat
    z_SC4UIScale_<Pkg>.3x.uipay    byte-for-byte copy of <Pkg>-3x.dat
    z_SC4UIScale_<Pkg>.off.uipay   a one-entry DBPF that contests nothing

`.x1-disabled` is stripped when reading, so it does not matter which tier
happened to be armed on the machine the sources came from.

THE `.off` PAYLOAD IS THE SUBTLE PART. It may not be empty or content-free:
`_packaging/Build-Dist.ps1` hard-throws on shipping such a file (#182 - an
empty FontStyle.ini got snapshotted as the user's original and the game took
an ACCESS_VIOLATION), and sc4pac aborts an install outright when a shipped
`.dat` fails to parse as DBPF. So it is a VALID one-entry DBPF whose single
TGI is unique per package and verified ABSENT from the merged index of every
archive the game can see - a live file that declares nothing anyone else owns.

MANDATORY POSITIVE CONTROL. "Absent from the index" is worthless if the index
is empty, and a false zero of exactly that shape has shipped in this project
twice. So the census is asserted large BEFORE any absence is believed, and the
numbers are printed every run. Reference figure measured 2026-08-29 on this
machine: 927,267 TGIs from 288 archives.

USAGE

    python tools/payload/build_payloads.py --src <plugins-dir> --out <dir>
    python tools/payload/build_payloads.py --verify --out <dir>

`--out` is REQUIRED and is never the live Plugins folder by default: this tool
does not touch the player's install.
"""

import argparse
import hashlib
import importlib.util
import json
import io
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DBPF_PACK = os.path.join(REPO, "tools", "dbpf", "DbpfPack.exe")
PROBE = os.path.join(REPO, "_tests", "Probe-ScanPredicate.py")

PREFIX = "z_SC4UIScale_"
DISABLED = ".x1-disabled"
PAYLOAD_EXT = ".uipay"
MANIFEST = "payload-manifest.json"

# Tier tag on disk -> payload suffix. `-1x` is NOT a tier: it marks the one
# package armed by the ABSENCE of a tier (see INVERSE GATE below), so it maps
# to `on`, never to a scale name.
TIER_TAGS = {"-15x": "15x", "-2x": "2x", "-3x": "3x"}
INVERSE_TAG = "-1x"
REQUIRED_TIERS = ("15x", "2x", "3x")

# The `.off` entry's Type/Group. NOT invented here: this is the exact T/G the
# #202 probe packed and booted, so the shape that was measured to load cleanly
# is the shape that ships. Only the instance varies, one per package.
OFF_TYPE = 0x856DDBAC
OFF_GROUP = 0x6A386D26
OFF_INST_BASE = 0x5C4B0000
OFF_INST_SPAN = 0x10000

# Census control thresholds - the same numbers Probe-ScanPredicate.py refuses
# below, so the two tools agree on what "we actually looked" means.
MIN_ARCHIVES = 50
MIN_KEYS = 50000
REF_KEYS, REF_ARCHIVES = 927267, 288   # measured 2026-08-29, this machine


# ---------------------------------------------------------------------------
# The DBPF index parse is IMPORTED, never re-implemented. A third copy of that
# loop is a third place for the parse to drift out of agreement with the
# archives it is supposed to describe.
# ---------------------------------------------------------------------------

def _load_probe():
    if not os.path.exists(PROBE):
        raise SystemExit("cannot find the index parser at %s - this tool "
                         "deliberately has no copy of its own." % PROBE)
    spec = importlib.util.spec_from_file_location("_probe_scanpredicate", PROBE)
    mod = importlib.util.module_from_spec(spec)
    # Bytecode caching OFF across this import: loading the probe must not drop
    # a __pycache__ entry into _tests/. This tool writes nowhere but --out.
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(mod)   # module body is __main__-guarded
    finally:
        sys.dont_write_bytecode = prev
    return mod


_probe = _load_probe()
read_index = _probe.read_index
merged_index = _probe.merged_index


def header_entry_count(path):
    """The index entry COUNT straight out of the 96-byte header.

    Not a second index parse - it reads one dword. `read_index` returns a SET,
    so it silently collapses duplicate TGIs; "exactly one entry" has to be
    checked against the count the file itself declares.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(96)
        if len(head) < 96 or head[:4] != b"DBPF":
            return None
        return struct.unpack_from("<I", head, 0x24)[0]
    except (OSError, struct.error):
        return None


def census(extra_trees):
    """Every TGI the game can see, with the positive control armed."""
    trees = [_probe.DOCS_PLUGINS] + _probe.game_trees() + list(extra_trees or [])
    keys, parsed, unparsed = merged_index(trees)
    print("merged index census: %d TGI(s) from %d archive(s); %d unparsable"
          % (len(keys), parsed, unparsed))
    print("  reference (measured 2026-08-29, this machine): %d TGI(s) / %d archive(s)"
          % (REF_KEYS, REF_ARCHIVES))
    for t in trees:
        print("  tree: %s%s" % (t, "" if os.path.isdir(t) else "   [ABSENT]"))
    if parsed < MIN_ARCHIVES or len(keys) < MIN_KEYS:
        raise SystemExit(
            "REFUSING: the census looks too small (%d archives, %d keys; "
            "floor is %d/%d). Every 'this TGI is absent' below would be absent "
            "because we failed to look, not because nothing owns it - the "
            "false zero this project has already shipped twice."
            % (parsed, len(keys), MIN_ARCHIVES, MIN_KEYS))
    print("CONTROL PASSED: the census demonstrably read the installed archives, "
          "so an absence in it is real evidence.")
    return keys


# ---------------------------------------------------------------------------
# Source scan
# ---------------------------------------------------------------------------

def split_name(name):
    """`z_SC4UIScale_Foo-2x.dat.x1-disabled` -> ('z_SC4UIScale_Foo', '-2x').

    Returns (base, tag) with tag '' for an untagged dat, or None if the file is
    not one of ours. The `.x1-disabled` suffix is stripped first, so whichever
    tier happened to be armed on the source machine is irrelevant.
    """
    if not name.startswith(PREFIX):
        return None
    stem = name[:-len(DISABLED)] if name.endswith(DISABLED) else name
    if not stem.lower().endswith(".dat"):
        return None
    stem = stem[:-4]
    for tag in list(TIER_TAGS) + [INVERSE_TAG]:
        if stem.endswith(tag):
            return stem[:-len(tag)], tag
    return stem, ""


def scan(src, out_abs):
    """Group every source dat under `src` by (relative dir, package base)."""
    groups = {}
    for root, dirs, files in os.walk(src):
        if os.path.abspath(root) == out_abs:      # never eat our own output
            dirs[:] = []
            continue
        rel = os.path.relpath(root, src)
        rel = "" if rel == "." else rel.replace("\\", "/")
        for name in files:
            got = split_name(name)
            if not got:
                continue
            base, tag = got
            g = groups.setdefault((rel, base), {})
            if tag in g:
                raise SystemExit(
                    "AMBIGUOUS SOURCE: two files claim %s%s in %s (%s and %s). "
                    "Refusing to guess which one's bytes ship."
                    % (base, tag or " (untagged)", root,
                       os.path.basename(g[tag]), name))
            g[tag] = os.path.join(root, name)
    return groups


def categorise(groups, armed_tags=None):
    """Split the scan into the four shapes this layout actually has.

    full     - all three tiers present; the normal case.
    inverse  - ONLY `-1x`. z_SC4UIScale_SelectorUI-1x is the one package armed
               by the ABSENCE of a tier (ScaleTier.cpp: SyncSelectorPackage);
               it ships the scale selector at stock geometry and is what keeps
               1x from being a one-way door. It gets on/off, never tiers.
    plain    - no tag at all: string-only packages (WebText, CamGraphLabels,
               MenuFix). A string has no geometry, so there is nothing to
               scale and nothing to gate - their `.dat` name is already stable
               and sc4pac can already remove it. No payload is invented.
    partial  - some but not all tiers. Reported, never emitted: half a payload
               set is a package that silently loses a tier.

    A base that has tier tags AND a bare `.dat` is NOT plain - the bare file is
    the live stable target of the pilot swap (SelectiveArt), not a source.
    """
    full, inverse, plain, partial = {}, {}, {}, {}
    for key, files in sorted(groups.items()):
        tiers = {TIER_TAGS[t]: p for t, p in files.items() if t in TIER_TAGS}
        if tiers:
            (full if len(tiers) == 3 else partial)[key] = (tiers, files)
        elif INVERSE_TAG in files:
            # tag carried per package: SelectorUI's call site passes L"-1x"
            # (-> "1x"), WebText's passes L"" (-> "on"). One hardcoded tag
            # for both is how WebText got a .1x payload the DLL never opens.
            inverse[key] = (files[INVERSE_TAG],
                            (armed_tags or {}).get(
                                key[1] if isinstance(key, tuple)
                                else str(key).replace(chr(92), '/').split('/')[-1],
                                INVERSE_TAG.lstrip('-')))
        else:
            plain[key] = files.get("")

    # A base with no tier tags is AMBIGUOUS ON DISK: genuinely never armed
    # (CamGraphLabels, MenuFix), or an INVERSE-GATED package the DLL arms with
    # on/off (WebText, gated on the Web Button mod). The filesystem cannot tell
    # those apart - only the DLL's call site can, so ask it.
    #
    # Getting this wrong is silent and total. WebText was classified
    # tier-independent, so nothing built it a payload, so ArmOne logged
    # "NO PAYLOAD AT ALL ... Leaving %ls.dat exactly as found" and its inverse
    # gate never fired. Found 2026-08-29 by Test-DatIntegrity's payload
    # coverage check, alongside the same failure in SelectorUI - two instances
    # of one class, which is why this is derived now instead of listed.
    if armed_tags:
        promoted = []
        for key in list(plain):
            base = key[1] if isinstance(key, tuple) else str(key).replace(
                "\\", "/").split("/")[-1]
            tag = armed_tags.get(base)
            if tag and plain.get(key):
                inverse[key] = (plain.pop(key), tag)
                promoted.append("%s (.%s)" % (base, tag))
        if promoted:
            print("  inverse-gated BY CALL SITE, not by filename: %s"
                  % ", ".join(sorted(promoted)))
    return full, inverse, plain, partial


# ---------------------------------------------------------------------------
# Which packages does the DLL actually ARM? Derived from its call sites.
# ---------------------------------------------------------------------------

SYNCDAT_RE = re.compile(
    r'SyncDat\s*\(\s*[A-Za-z_]\w*\s*,\s*L"([^"]+)"\s*,\s*([^,]+),')


def syncdat_call_sites(scale_tier_cpp):
    """base name -> payload tag the DLL will ask ArmOne for.

    WHY THIS IS PARSED AND NOT LISTED. A package with no tier tags on disk is
    ambiguous: it may be genuinely tier-independent and never armed
    (CamGraphLabels, MenuFix), or it may be an INVERSE-GATED package the DLL
    arms with `on`/`off` (WebText, gated on the Web Button mod). The filesystem
    cannot tell those apart - only the call site can.

    Getting it wrong is silent and total. WebText was classified
    tier-independent, so nothing built it a payload, so ArmOne logged
    "NO PAYLOAD AT ALL ... Leaving %ls.dat exactly as found" and its inverse
    gate never fired at all. Found 2026-08-29 by Test-DatIntegrity's payload
    coverage check, alongside the same failure in SelectorUI.

    The mapping mirrors PayloadTagOf() in ScaleTier.cpp: strip a leading
    hyphen; an empty tag means `on`.
    """
    out = {}
    with io.open(scale_tier_cpp, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    for m in SYNCDAT_RE.finditer(src):
        rel, tag_expr = m.group(1), m.group(2).strip()
        base = rel.split("\\")[-1]
        if tag_expr == 'L""':
            out[base] = "on"                 # inverse gate, not a tier
        elif tag_expr.startswith('L"'):
            out[base] = tag_expr[2:-1].lstrip("-")
        else:
            out[base] = None                 # pkg.tag - a real tier package
    return out


# ---------------------------------------------------------------------------
# The `.off` payload
# ---------------------------------------------------------------------------

def one_pixel_png():
    """A 1x1 fully transparent PNG, built rather than pasted so it is auditable.

    The entry's Type is 0x856DDBAC, which in SC4 means PNG, and the game stores
    that type as plain uncompressed PNG (NOTES-PACK.md). The probe proved a
    one-entry archive registers with arbitrary bytes in it, but shipping bytes
    that match their declared type costs nothing and removes the only way a
    correctly-typed reader could ever choke on this file.
    """
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)   # 1x1, 8-bit RGBA
    idat = zlib.compress(b"\x00" + b"\x00" * 4)           # filter 0 + RGBA 0000
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def pick_off_instance(key, taken, index_keys, remembered):
    """A deterministic, unique, verified-ABSENT instance for one package.

    Deterministic so a rebuild does not churn the shipped TGI: the start point
    is a stable digest of the package's own path, not a counter and not
    Python's randomised hash. A previous run's choice (payload-manifest.json)
    wins when it is still free, so the value is stable across rebuilds.
    """
    ident = "%s/%s" % key if key[0] else key[1]
    prev = remembered.get(ident)
    if prev is not None and prev not in taken \
            and (OFF_TYPE, OFF_GROUP, prev) not in index_keys:
        taken.add(prev)
        return prev, True
    digest = hashlib.sha256(ident.encode("utf-8")).digest()
    start = struct.unpack_from(">I", digest)[0] % OFF_INST_SPAN
    for step in range(OFF_INST_SPAN):
        inst = OFF_INST_BASE + ((start + step) % OFF_INST_SPAN)
        if inst in taken or (OFF_TYPE, OFF_GROUP, inst) in index_keys:
            continue
        taken.add(inst)
        return inst, False
    raise SystemExit("no free instance in the reserved .off window for %s - "
                     "widen OFF_INST_SPAN." % ident)


def pack_off(inst, dest):
    """Build the one-entry DBPF at `dest` via the project's own DBPF writer."""
    tmp = tempfile.mkdtemp(prefix="uipay-off-")
    try:
        entry = os.path.join(tmp, "T-0x%08X_G-0x%08X_I-0x%08X.png"
                             % (OFF_TYPE, OFF_GROUP, inst))
        with open(entry, "wb") as f:
            f.write(one_pixel_png())
        r = subprocess.run([DBPF_PACK, tmp, dest], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(dest):
            raise SystemExit("DbpfPack failed for %s:\n%s%s"
                             % (dest, r.stdout, r.stderr))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # Prove what was just written, do not assume the writer's exit code.
    n = header_entry_count(dest)
    idx = read_index(dest)
    if n != 1 or idx != {(OFF_TYPE, OFF_GROUP, inst)}:
        raise SystemExit("built .off is not the one entry asked for: %s "
                         "(header count %s, index %s)" % (dest, n, idx))


def copy_verbatim(src, dest):
    """Copy and PROVE the copy, by digest, not by the absence of an exception."""
    h_in = hashlib.sha256()
    with open(src, "rb") as a, open(dest, "wb") as b:
        while True:
            buf = a.read(1 << 20)
            if not buf:
                break
            h_in.update(buf)
            b.write(buf)
    h_out = hashlib.sha256()
    with open(dest, "rb") as f:
        while True:
            buf = f.read(1 << 20)
            if not buf:
                break
            h_out.update(buf)
    if h_in.digest() != h_out.digest():
        raise SystemExit("copy is NOT byte-for-byte: %s -> %s" % (src, dest))
    return os.path.getsize(dest), h_out.hexdigest()


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def build(args):
    src = os.path.abspath(args.src)
    out = os.path.abspath(args.out)
    if not os.path.isdir(src):
        raise SystemExit("source directory not found: %s" % src)
    if os.path.normcase(src) == os.path.normcase(out):
        raise SystemExit("--out must not be --src: this tool never rewrites "
                         "the layout it is reading.")
    if not os.path.exists(DBPF_PACK):
        raise SystemExit("DbpfPack.exe not found at %s" % DBPF_PACK)

    print("source : %s" % src)
    print("output : %s" % out)
    print()
    index_keys = census(args.extra_tree)
    print()

    groups = scan(src, out)
    if not groups:
        raise SystemExit(
            "no %s*.dat sources under %s. NOT a result: point --src at a "
            "Plugins-style directory (e.g. dist\\SC4UIScale-vX.Y.Z\\Plugins)."
            % (PREFIX, src))
    # Ask the DLL which packages it actually arms. A repo-relative path is
    # used so this works from any cwd; if the source is missing we say so
    # and continue with filename-only classification rather than guessing.
    _repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _cpp = os.path.join(_repo, 'src', 'ScaleTier.cpp')
    armed_tags = {}
    if os.path.isfile(_cpp):
        armed_tags = syncdat_call_sites(_cpp)
        print('  DLL call sites parsed: %d SyncDat target(s)' % len(armed_tags))
        if not armed_tags:
            raise SystemExit('REFUSING: parsed src/ScaleTier.cpp and found ZERO '
                             'SyncDat call sites. The regex has rotted, and every '
                             'inverse-gated package would be silently classified '
                             'tier-independent and shipped with no payload.')
    else:
        print('  WARNING: %s not found - inverse gates cannot be detected '
              'by call site' % _cpp)
    full, inverse, plain, partial = categorise(groups, armed_tags)

    remembered = {}
    mpath = os.path.join(out, MANIFEST)
    if os.path.exists(mpath):
        try:
            with open(mpath, "r", encoding="utf-8") as f:
                old = json.load(f)
            remembered = {k: int(v["off_instance"], 16)
                          for k, v in old.get("packages", {}).items()
                          if "off_instance" in v}
        except (OSError, ValueError, KeyError):
            remembered = {}

    os.makedirs(out, exist_ok=True)
    taken, records, reused = set(), {}, 0

    def emit(key, members):
        """members: {payload suffix -> source path}. Adds `.off` itself."""
        nonlocal reused
        rel, base = key
        dest_dir = os.path.join(out, *rel.split("/")) if rel else out
        os.makedirs(dest_dir, exist_ok=True)
        entry = {"dir": rel, "payloads": {}}
        for suffix, srcfile in sorted(members.items()):
            dest = os.path.join(dest_dir, "%s.%s%s" % (base, suffix, PAYLOAD_EXT))
            size, digest = copy_verbatim(srcfile, dest)
            entry["payloads"][suffix] = {
                "from": os.path.relpath(srcfile, src).replace("\\", "/"),
                "bytes": size, "sha256": digest}
        inst, was_reused = pick_off_instance(key, taken, index_keys, remembered)
        reused += 1 if was_reused else 0
        dest = os.path.join(dest_dir, "%s.off%s" % (base, PAYLOAD_EXT))
        pack_off(inst, dest)
        entry["off_instance"] = "0x%08X" % inst
        entry["off_tgi"] = "T-0x%08X_G-0x%08X_I-0x%08X" % (OFF_TYPE, OFF_GROUP, inst)
        entry["payloads"]["off"] = {
            "from": "(generated one-entry DBPF)",
            "bytes": os.path.getsize(dest), "sha256": None}
        records["%s/%s" % (rel, base) if rel else base] = entry

    for key, (tiers, _files) in sorted(full.items()):
        emit(key, tiers)
    for key, (path, itag) in sorted(inverse.items()):
        # ⚠ THE TAG MUST BE "1x", NOT "on". The DLL decides the payload
        # name from the tag its call site passes: SyncSelectorPackage passes
        # L"-1x", PayloadTagOf strips the hyphen, and ArmOne then opens
        # z_SC4UIScale_SelectorUI.1x.uipay. MigrateRenamesToPayloads writes
        # exactly that name too.
        #
        # Emitting "on" here shipped a bundle the DLL could not read: on a
        # FRESH install ArmOne missed, fell back to .off, and the stock-tier
        # selector - the one thing keeping 1x from being a one-way door - was
        # inert. It worked only on UPGRADED installs, where migration had
        # produced the right name. Two spellings of one tag, and only the
        # upgrade path exercised the correct one.
        #
        # "on"/"off" stays correct for a TRUE inverse gate (WebText), whose
        # call site passes L"" and whose payload tag really is "on".
        emit(key, {itag: path})

    manifest = {
        "tool": "tools/payload/build_payloads.py",
        "source": src,
        "census": {"tgis": len(index_keys), "floor_tgis": MIN_KEYS,
                   "floor_archives": MIN_ARCHIVES},
        "off_type": "0x%08X" % OFF_TYPE, "off_group": "0x%08X" % OFF_GROUP,
        "tier_independent": sorted("%s/%s" % k if k[0] else k[1] for k in plain),
        "incomplete": sorted("%s/%s" % k if k[0] else k[1] for k in partial),
        "packages": records,
    }
    with open(mpath, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")

    # ---- report ----------------------------------------------------------
    def label(key):
        return "%s/%s" % key if key[0] else key[1]

    print("FULL TIER SETS (15x / 2x / 3x / off)            : %d" % len(full))
    for key in sorted(full):
        print("    %s" % label(key))
    print()
    print("INVERSE-GATED (on / off; armed by ABSENCE of a tier): %d" % len(inverse))
    for key in sorted(inverse):
        print("    %s   [source %s]" % (label(key), INVERSE_TAG))
    print()
    print("TIER-INDEPENDENT (no tag; always on - NO payload invented): %d"
          % len(plain))
    for key in sorted(plain):
        print("    %s" % label(key))
    print()
    if partial:
        print("INCOMPLETE TIER SETS - NOT EMITTED                : %d" % len(partial))
        for key, (tiers, _f) in sorted(partial.items()):
            missing = [t for t in REQUIRED_TIERS if t not in tiers]
            print("    %s   has %s, MISSING %s"
                  % (label(key), ",".join(sorted(tiers)), ",".join(missing)))
        print()

    n_sets = len(full) + len(inverse)
    n_files = sum(len(r["payloads"]) for r in records.values())
    print("produced %d payload set(s), %d %s file(s) under %s"
          % (n_sets, n_files, PAYLOAD_EXT, out))
    print("off TGIs: %d assigned, all verified ABSENT from the %d-key census "
          "(%d reused from the previous manifest)"
          % (len(taken), len(index_keys), reused))
    print("manifest: %s" % mpath)

    if partial and not args.allow_incomplete:
        print()
        raise SystemExit(
            "FAILED: %d base(s) are missing tiers (listed above). Emitting a "
            "partial set would ship a package that silently loses a tier. Fix "
            "the source, or pass --allow-incomplete to skip them knowingly."
            % len(partial))
    return 0


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def verify(args):
    out = os.path.abspath(args.out)
    if not os.path.isdir(out):
        raise SystemExit("payload directory not found: %s" % out)
    print("verifying: %s" % out)
    print()
    index_keys = census(args.extra_tree)
    print()

    sets = {}
    for root, _dirs, files in os.walk(out):
        rel = os.path.relpath(root, out)
        rel = "" if rel == "." else rel.replace("\\", "/")
        for name in files:
            if not name.endswith(PAYLOAD_EXT) or not name.startswith(PREFIX):
                continue
            stem = name[:-len(PAYLOAD_EXT)]
            if "." not in stem:
                continue
            base, suffix = stem.rsplit(".", 1)
            sets.setdefault((rel, base), {})[suffix] = os.path.join(root, name)

    if not sets:
        raise SystemExit("FAILED [scan]: no %s files under %s. Nothing was "
                         "checked - this is a refusal, not a pass."
                         % (PAYLOAD_EXT, out))

    fails = []
    off_owner = {}
    n_payloads = 0

    for key, members in sorted(sets.items()):
        label = "%s/%s" % key if key[0] else key[1]
        got = set(members)

        # (a) complete set: a tier package or the inverse-gated one, nothing else
        if got not in (set(REQUIRED_TIERS) | {"off"},
                       {INVERSE_TAG.lstrip("-"), "off"}, {"on", "off"}):
            fails.append("(a) incomplete set  %s has {%s}; expected "
                         "{15x,2x,3x,off} or {on,off}"
                         % (label, ",".join(sorted(got))))

        for suffix, path in sorted(members.items()):
            n_payloads += 1
            idx = read_index(path)
            # (b) parseable DBPF
            if idx is None:
                fails.append("(b) not a parseable DBPF  %s.%s" % (label, suffix))
                continue
            if suffix != "off":
                continue
            # (c) exactly one entry
            n = header_entry_count(path)
            if n != 1 or len(idx) != 1:
                fails.append("(c) .off is not one entry  %s: header count %s, "
                             "%d distinct TGI(s)" % (label, n, len(idx)))
                continue
            tgi = next(iter(idx))
            # (d) no two .off payloads share a TGI
            if tgi in off_owner:
                fails.append("(d) duplicate .off TGI  %s and %s both own "
                             "T-0x%08X_G-0x%08X_I-0x%08X"
                             % (off_owner[tgi], label, *tgi))
            else:
                off_owner[tgi] = label
            # (e) absent from the merged index
            if tgi in index_keys:
                fails.append("(e) .off TGI is CONTESTED  %s owns "
                             "T-0x%08X_G-0x%08X_I-0x%08X, which already exists "
                             "in the merged index" % (label, *tgi))

    print("payload sets found : %d" % len(sets))
    print("%s files checked : %d" % (PAYLOAD_EXT, n_payloads))
    print(".off TGIs checked  : %d, against %d census key(s)"
          % (len(off_owner), len(index_keys)))
    print()
    if fails:
        print("VERIFY FAILED - %d problem(s):" % len(fails))
        for f in fails:
            print("    %s" % f)
        return 1
    print("VERIFY PASSED: (a) every set complete, (b) every payload parses as "
          "DBPF, (c) every .off has exactly one entry, (d) no two .off payloads "
          "share a TGI, (e) no .off TGI exists anywhere in the merged index.")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help="Plugins-style source directory to convert "
                                  "(walked recursively; layout preserved)")
    ap.add_argument("--out", required=True,
                    help="REQUIRED. Directory to write payloads into. Never "
                         "defaults to the live Plugins folder.")
    ap.add_argument("--verify", action="store_true",
                    help="check a produced payload set instead of building one")
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="report bases missing tiers without failing the run")
    ap.add_argument("--extra-tree", action="append", metavar="DIR",
                    help="additional archive tree to fold into the census "
                         "(repeatable)")
    args = ap.parse_args()
    if args.verify:
        return verify(args)
    if not args.src:
        ap.error("--src is required unless --verify is given")
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
