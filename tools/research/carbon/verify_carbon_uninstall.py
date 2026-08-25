#!/usr/bin/env python3
r"""OFFLINE PROOF: SC4UIScale still works when the Scoty Carbon Skin is UNINSTALLED.

THE QUESTION. We ship eight carbon-sourced override packages
(zzz-SC4UIScale\z_SC4UIScale_ZCarbon*), each gated in src\ScaleTier.cpp on the
skin's own dats by exact filename + byte size. If the player uninstalls the
skin, ScaleTier::SyncStaticLayers must disarm all eight at the next boot and
the tree must fall back EXACTLY to what it looked like before the skin ever
existed. This script proves that offline - the game is never launched and the
live Plugins tree is never touched.

SIMULATED ABSENCE LIVES IN THE INSTRUMENT, NOT ON DISK. Nothing here renames,
moves or deletes a single file. The "post-uninstall" tree is a VIRTUAL file
list built in memory:
  * every path under the skin folder (zz-scoty-mods) is filtered out, and
  * the ZCarbon packages' armed/disarmed state is DERIVED by re-implementing
    ScaleTier's own gate logic (kThirdPartyDeps + FindPluginFile + SyncDat)
    against that filtered tree - it is NOT hardcoded. If the disarm did not
    cover a package, this script would arm it and the ORPHAN check would go
    red, which is the whole point of check 3.

TIER. The live machine currently sits at ScaleFactor=1 (stock), where every
package is stashed. The pre-carbon baseline capture was taken at 1.5x with
the packages ARMED, so both simulated states here are computed at the -15x
tier: SyncDat/SyncDatStable are emulated to produce the file names the game
would actually see after a 1.5x boot.

CHECKS
  1. REVERSION - each of the 494 formerly-colliding TGIs has a winner in the
     post-uninstall tree, and that winner is one of OUR packages or a game
     archive. Never None, never a carbon dat.
  2. BASELINE EQUALITY - every TGI in the pre-carbon capture resolves to the
     same winner FILENAME as it did before the skin existed. Basenames, not
     paths (v4.2.0 moved packages into 010-SC4UIScale\).
  3. NO ORPHANS - zero ZCarbon packages armed in the post-uninstall state,
     and every ZCarbon package on disk maps to a kThirdPartyDeps row AND a
     gated SyncDat call site (a row with no call site is inert - the #119
     WarriorUI shape).
  POSITIVE CONTROL - the WITH-carbon winners are computed too. If the two
  states are identical the absence filter is broken and every green above is
  a false green; the run FAILS LOUDLY instead of reporting a null.

Usage:  python tools\research\carbon\verify_carbon_uninstall.py
"""
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
CAP = os.path.join(PROJ, "_tests", "captures", "2026-08-25-carbon")
INTER = os.path.join(CAP, "carbon-vs-ours-intersection.txt")
BASELINE = os.path.join(PROJ, "_tests", "captures",
                        "2026-08-24-tgi-winners-FINAL.txt")
OUT = os.path.join(CAP, "uninstall-reversion.txt")
# Speed cache only (~30MB of TGI listings), keyed by size+mtime and rebuilt
# from scratch whenever it is missing - so it lives in TEMP, never in the
# captures directory that gets committed.
CACHE = os.path.join(os.environ.get("TEMP", "."),
                     "sc4uiscale-carbon-tgi-cache.json")
DBPF = os.path.join(PROJ, "tools", "dbpf", "DbpfPack.exe")
SRC = os.path.join(PROJ, "src", "ScaleTier.cpp")
PLUG = os.path.join(os.environ["USERPROFILE"], "OneDrive", "Documents",
                    "SimCity 4", "Plugins")

# The skin folder, as installed. Simulated absence = every path under here.
SKIN_DIR_NAME = "zz-scoty-mods"

# ScaleTier.cpp:42 IsDbpfName - .SC4Lot/.SC4Desc/.SC4Model are DBPF too.
DBPF_EXTS = (".dat", ".sc4lot", ".sc4desc", ".sc4model", ".sc4")
DISABLED = ".x1-disabled"

# The tier we simulate. ScaleTier.cpp:45 kPackages.
ALL_TAGS = ("-4x", "-3x", "-2x", "-15x")
ACTIVE_TAG = "-15x"

# ScaleTier.cpp:467 - dirs FindPluginFile refuses to descend into, so a
# package can never satisfy its own dependency.
FIND_SKIP_DIRS = {"zzz-sc4uiscale", "010-sc4uiscale", "_dllstash"}
FIND_DEPTH = 4

# The one deliberate skip in the collision set: the WebText caption LTEXT,
# where carbon is SUPPOSED to win (carbon_final_census.py:36).
SKIP_CARBON_OK = {(0x2026960B, 0x6A231EAA, 0x0A5128F3)}

ROW = re.compile(r"^0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8})")
BASEROW = re.compile(r"^0x([0-9A-Fa-f]{8}) 0x([0-9A-Fa-f]{8}) "
                     r"0x([0-9A-Fa-f]{8}) -> (.+)$")

LOG = []


def say(s=""):
    print(s)
    LOG.append(s)


# ---------------------------------------------------------------- gate table
def parse_dep_rows(text):
    """kThirdPartyDeps from ScaleTier.cpp - the single source of truth."""
    start = text.index("kThirdPartyDeps[] = {")
    end = text.index("\n\t};", start)
    body = text[start:end]
    rows = []
    pat = re.compile(
        r'\{\s*L"([^"]+)",\s*'          # package
        r'L"([^"]+)",\s*'               # modFile
        r'(true|false),\s*'             # prefixMatch
        r'(\d+),\s*'                    # modSize
        r'(?:L"([^"]+)"|nullptr),\s*'   # modFile2
        r'(\d+)\s*\}', re.S)
    for m in pat.finditer(body):
        rows.append({
            "package": m.group(1).replace("\\\\", "\\"),
            "file": m.group(2),
            "prefix": m.group(3) == "true",
            "size": int(m.group(4)),
            "file2": m.group(5),
            "size2": int(m.group(6)),
        })
    return rows


def parse_sync_calls(text):
    """Every SyncDat() call site, with the condition that arms it.

    Parsed rather than hardcoded so a package added to the source without a
    matching call here cannot silently drop out of the model.
    """
    pat = re.compile(
        r'\bSyncDat\(\s*(\w+),\s*L"([^"]+)",\s*(pkg\.tag|L"[^"]*")\s*,\s*'
        r'(.*?)\);', re.S)
    calls = []
    for m in pat.finditer(text):
        cond = " ".join(m.group(4).split())
        tagexpr = m.group(3)
        tags = list(ALL_TAGS) if tagexpr == "pkg.tag" else [tagexpr[2:-1]]
        calls.append({
            "dirvar": m.group(1),
            "base": m.group(2).replace("\\\\", "\\"),
            "tags": tags,
            "per_tier": tagexpr == "pkg.tag",
            "cond": cond,
            "line": text[:m.start()].count("\n") + 1,
        })
    return calls


def parse_stable_calls(text):
    pat = re.compile(r'\bSyncDatStable\(\s*(\w+),\s*L"([^"]+)",\s*(\w+)\);')
    return [{"dirvar": m.group(1), "base": m.group(2),
             "line": text[:m.start()].count("\n") + 1}
            for m in pat.finditer(text)]


# ------------------------------------------------------------- the live tree
def scan_tree(root):
    """Every real file: relpath -> size. Read-only; nothing is mutated."""
    out = {}
    for d, dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            try:
                out[os.path.relpath(p, root)] = os.path.getsize(p)
            except OSError:
                pass
    return out


def tree_stamp(root):
    """(path, size, mtime) fingerprint of the whole tree.

    TREE-STABILITY GUARD. This repo has several agents deploying into the
    same live Plugins tree; a rebuild landing mid-run mixes two builds'
    bytes into one winner table and every number above becomes fiction.
    Measured 2026-08-25: a concurrent deploy rewrote SelectiveArt,
    ThirdPartyUI, WarriorUI and six ZCarbon packages between 10:43 and
    10:46 while this script was reading them. Snapshot before, verify
    after, and refuse to call the run valid if anything moved.

    SCOPED to CONTENT IDENTITY, not to the path. This model reads a package
    through EITHER extension (resolve_source), and arms it from the gate
    logic rather than from what happens to be bare on disk - so a tier flip
    renaming `<x>.dat` <-> `<x>.dat.x1-disabled` changes nothing this script
    concluded, and failing the run on it would be a false alarm. A REWRITE
    (new size or new mtime) is the thing that invalidates a run, and that is
    what this catches.
    """
    out = {}
    for d, _dirs, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            rel = os.path.relpath(p, root)
            if rel.endswith(DISABLED):
                rel = rel[:-len(DISABLED)]
            out[rel] = (st.st_size, int(st.st_mtime))
    return out


def under_skin(rel):
    return rel.lower().split(os.sep)[0] == SKIN_DIR_NAME


# ---------------------------------------------- FindPluginFile (ScaleTier:434)
def find_plugin_file(files, name, prefix, present):
    """Emulate FindPluginFile(pluginsRoot, name, prefix, depth=4).

    `present(rel)` decides whether a real file exists in this simulated
    state. Returns (found, size, relpath, matches).
    """
    needle = name.lower()
    found = None
    matches = 0
    for rel, size in files.items():
        if not present(rel):
            continue
        parts = rel.split(os.sep)
        # depth: Plugins\ = 1 ... Plugins\a\b\c\ = 4. depth<=0 returns false.
        if len(parts) > FIND_DEPTH:
            continue
        if any(p.lower() in FIND_SKIP_DIRS for p in parts[:-1]):
            continue
        fn = parts[-1].lower()
        hit = fn.startswith(needle) if prefix else fn == needle
        if hit:
            matches += 1
            if found is None:
                found = (rel, size)
    if found is None:
        return False, 0, None, 0
    return True, found[1], found[0], matches


def resolve_deps(rows, files, present):
    """depOk[] exactly as SyncStaticLayers computes it (ScaleTier:2762)."""
    dep_ok = {}
    detail = {}
    for r in rows:
        ok1, sz1, hit1, _ = find_plugin_file(files, r["file"], r["prefix"],
                                             present)
        size_ok = (r["size"] == 0) or (sz1 == r["size"])
        why = None
        if not ok1:
            why = "ABSENT %s" % r["file"]
        elif not size_ok:
            why = "SIZE %s is %d, built from %d" % (r["file"], sz1, r["size"])
        if ok1 and size_ok and r["file2"]:
            ok2, sz2, _h2, _ = find_plugin_file(files, r["file2"],
                                                r["prefix"], present)
            s2 = (r["size2"] == 0) or (sz2 == r["size2"])
            if not ok2:
                why = "ABSENT %s" % r["file2"]
            elif not s2:
                why = "SIZE %s is %d, built from %d" % (r["file2"], sz2,
                                                        r["size2"])
            ok1, size_ok = ok2, s2
        dep_ok[r["package"]] = bool(ok1 and size_ok)
        detail[r["package"]] = why or ("ok (%s)" % hit1)
    return dep_ok, detail


# ------------------------------------------------- the virtual (armed) tree
def managed_index(calls, stables):
    """Every filename ScaleTier owns, so the raw tree never leaks a stale one.

    Returns (owned_lower_names_by_dir, armed_plan_inputs).
    """
    owned = {}   # dirkey -> set of lowercase filenames ScaleTier controls
    for c in calls:
        d, b = os.path.split(c["base"])
        key = (c["dirvar"], d)
        s = owned.setdefault(key, set())
        for t in ALL_TAGS + tuple(c["tags"]):
            s.add(("%s%s.dat" % (b, t)).lower())
            s.add(("%s%s.dat%s" % (b, t, DISABLED)).lower())
    for st in stables:
        d, b = os.path.split(st["base"])
        s = owned.setdefault((st["dirvar"], d), set())
        s.add(("%s.dat" % b).lower())
        s.add(("%s.dat%s" % (b, DISABLED)).lower())
        for t in ALL_TAGS:
            s.add(("%s%s.dat" % (b, t)).lower())
            s.add(("%s%s.dat%s" % (b, t, DISABLED)).lower())
    return owned


DIRVAR_REL = {"docPlugins": "010-SC4UIScale", "pluginsRoot": ""}


def arm_plan(calls, stables, dep_ok, web_btn_present):
    """Which virtual files exist after a 1.5x boot. (reldir, name) -> src tag.

    Emulates SyncDat's rename and SyncDatStable's content-swap.
    """
    plan = {}          # relpath(virtual) -> relpath(content source, tagged)
    armed_pkgs = {}
    unmodelled = []
    for c in calls:
        reldir = DIRVAR_REL[c["dirvar"]]
        subdir, b = os.path.split(c["base"])
        d = os.path.join(reldir, subdir) if subdir else reldir
        for t in c["tags"]:
            if c["cond"] == "match":
                armed = c["per_tier"] and t == ACTIVE_TAG
            elif "DepOkByName(" in c["cond"]:
                pkg = re.search(r'DepOkByName\(\s*L"([^"]+)"',
                                c["cond"]).group(1).replace("\\\\", "\\")
                armed = (t == ACTIVE_TAG) and dep_ok.get(pkg, True)
            elif c["cond"] == "!webBtnPresent":
                armed = not web_btn_present          # inverse gate, tierless
            elif c["cond"] == "stockTier":
                armed = False                        # SelectorUI-1x: 1x only
            else:
                unmodelled.append((c["base"], c["cond"], c["line"]))
                armed = False
            key = c["base"] if not c["per_tier"] else c["base"]
            armed_pkgs.setdefault(key, False)
            if armed:
                armed_pkgs[key] = True
                name = "%s%s.dat" % (b, t)
                plan[os.path.join(d, name)] = os.path.join(d, name)
    for st in stables:
        reldir = DIRVAR_REL[st["dirvar"]]
        subdir, b = os.path.split(st["base"])
        d = os.path.join(reldir, subdir) if subdir else reldir
        # stable NAME, active tier's CONTENT (ScaleTier:586)
        plan[os.path.join(d, "%s.dat" % b)] = os.path.join(
            d, "%s%s.dat" % (b, ACTIVE_TAG))
        armed_pkgs[st["base"]] = True
    return plan, armed_pkgs, unmodelled


def resolve_source(files, rel):
    """A planned file's real bytes: bare .dat or the .x1-disabled twin."""
    if rel in files:
        return rel
    if rel + DISABLED in files:
        return rel + DISABLED
    return None


def build_virtual_tree(files, owned, plan, present):
    """relpath -> content relpath, for every archive the game would load."""
    tree = {}
    for rel in files:
        if not present(rel):
            continue
        low = os.path.basename(rel).lower()
        if low.endswith(DISABLED):
            continue                       # extension gate: never loaded
        if not low.endswith(DBPF_EXTS):
            continue
        d = os.path.dirname(rel)
        if any(low in s for (dv, sub), s in owned.items()
               if os.path.normpath(os.path.join(DIRVAR_REL[dv], sub) or ".")
               == os.path.normpath(d or ".")):
            continue                       # ScaleTier owns this name
        tree[rel] = rel
    missing = []
    for virt, src in plan.items():
        real = resolve_source(files, src)
        if real is None:
            missing.append(virt)
            continue
        tree[virt] = real
    return tree, missing


def load_order(tree, fold):
    """Game load order: a directory's FILES, then its subdirs, both sorted."""
    kids = {}
    for rel in tree:
        d = os.path.dirname(rel)
        parts = d.split(os.sep) if d else []
        for i in range(len(parts)):
            kids.setdefault(os.sep.join(parts[:i]),
                            set()).add(os.sep.join(parts[:i + 1]))
        kids.setdefault(d, set())
    byd = {}
    for rel in tree:
        byd.setdefault(os.path.dirname(rel), []).append(rel)
    out = []

    def walk(d):
        for f in sorted(byd.get(d, []), key=lambda p: fold(os.path.basename(p))):
            out.append(f)
        for sub in sorted(kids.get(d, ()),
                          key=lambda p: fold(os.path.basename(p))):
            walk(sub)

    walk("")
    return out


# ------------------------------------------------------------- DBPF contents
def list_tgis(cache, abspath):
    key = abspath.lower()
    try:
        st = os.stat(abspath)
        stamp = [st.st_size, int(st.st_mtime)]
    except OSError:
        return []
    hit = cache.get(key)
    if hit and hit[0] == stamp:
        return [tuple(t) for t in hit[1]]
    r = subprocess.run([DBPF, "--list", abspath], capture_output=True,
                       text=True, errors="replace")
    rows = []
    for line in r.stdout.splitlines():
        m = ROW.match(line.strip())
        if m:
            rows.append((int(m.group(1), 16), int(m.group(2), 16),
                         int(m.group(3), 16)))
    cache[key] = [stamp, rows]
    return rows


def winners(order, contents, fold_name):
    w = {}
    for rel in order:
        for tgi in contents.get(rel, ()):
            w[tgi] = rel
    return w


def compute_state(label, files, owned, calls, stables, rows, present, contents,
                  cache):
    dep_ok, detail = resolve_deps(rows, files, present)
    web = find_plugin_file(files, "z_Full Screen - Web Button Improvement Mod",
                           True, present)[0]
    plan, armed, unmodelled = arm_plan(calls, stables, dep_ok, web)
    tree, missing = build_virtual_tree(files, owned, plan, present)
    for rel, src in tree.items():
        ab = os.path.join(PLUG, src)
        if rel not in contents:
            contents[rel] = list_tgis(cache, ab)
    res = {}
    for name, fold in (("lower", str.lower), ("upper", str.upper)):
        res[name] = winners(load_order(tree, fold), contents, name)
    amb = [t for t in res["lower"] if res["lower"][t] != res["upper"].get(t)]
    say("[%s] archives loaded: %-4d  deps ok: %d/%d  planned-but-missing: %d  "
        "comparator-ambiguous: %d"
        % (label, len(tree), sum(1 for v in dep_ok.values() if v), len(dep_ok),
           len(missing), len(amb)))
    if unmodelled:
        say("  UNMODELLED SyncDat conditions (the model is incomplete):")
        for b, c, ln in unmodelled:
            say("    ScaleTier.cpp:%d  %s  cond=%s" % (ln, b, c))
    if missing:
        say("  planned files with no bytes on disk: %s"
            % ", ".join(sorted(os.path.basename(m) for m in missing)[:8]))
    return res["lower"], dep_ok, detail, armed, tree


def main():
    text = open(SRC, encoding="utf-8", errors="replace").read()
    rows = parse_dep_rows(text)
    calls = parse_sync_calls(text)
    stables = parse_stable_calls(text)
    owned = managed_index(calls, stables)
    say("ScaleTier.cpp: %d dep rows, %d SyncDat call sites, %d stable packages"
        % (len(rows), len(calls), len(stables)))

    stamp0 = tree_stamp(PLUG)
    files = scan_tree(PLUG)
    skin_files = [r for r in files if under_skin(r)]
    say("live tree: %d files, %d under %s\\ (simulated absent)"
        % (len(files), len(skin_files), SKIN_DIR_NAME))
    if not skin_files:
        say("POSITIVE CONTROL FAILED: the skin folder is not in the live tree, "
            "so 'simulated absence' removes nothing and every check below "
            "would be vacuously green.")
        sys.exit(2)

    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE))
        except Exception:
            cache = {}
    contents = {}

    say()
    say("=== STATE A: skin INSTALLED (positive control) ===")
    win_with, dep_with, det_with, armed_with, tree_with = compute_state(
        "with-carbon", files, owned, calls, stables, rows,
        lambda r: True, contents, cache)

    say()
    say("=== STATE B: skin UNINSTALLED (simulated absence) ===")
    win_wo, dep_wo, det_wo, armed_wo, tree_wo = compute_state(
        "post-uninstall", files, owned, calls, stables, rows,
        lambda r: not under_skin(r), contents, cache)

    json.dump(cache, open(CACHE, "w"))

    # ---------------- POSITIVE CONTROL: the two states must differ ----------
    say()
    say("=== POSITIVE CONTROL ===")
    moved = [t for t in win_with if win_with[t] != win_wo.get(t)]
    lost = [t for t in win_with if t not in win_wo]
    say("TGIs whose winner CHANGED between the two states: %d "
        "(of which disappear entirely: %d)" % (len(moved), len(lost)))
    carbon_owned = sum(1 for t, p in win_with.items()
                       if "scoty" in os.path.basename(p).lower())
    zc_owned_with = sum(1 for t, p in win_with.items()
                        if os.path.basename(p).startswith(
                            "z_SC4UIScale_ZCarbon"))
    say("with-carbon: %d TGIs won by a scoty_* dat, %d by a ZCarbon package"
        % (carbon_owned, zc_owned_with))
    if not moved:
        say("POSITIVE CONTROL FAILED: the two states are identical, so the "
            "absence filter never removed anything - every check below is a "
            "FALSE GREEN.")
        sys.exit(2)
    say("positive control PASSES: the filter demonstrably changes the tree.")

    # ---------------- CHECK 1: reversion on the 494 colliding TGIs ----------
    say()
    say("=== CHECK 1: REVERSION (formerly-colliding TGIs) ===")
    coll = []
    for line in open(INTER, encoding="utf-8"):
        m = ROW.match(line.strip())
        if m and not line.startswith("#"):
            coll.append((int(m.group(1), 16), int(m.group(2), 16),
                         int(m.group(3), 16)))
    coll_set = set(coll)
    fail1 = []
    by_owner = {}
    for tgi in coll:
        p = win_wo.get(tgi)
        b = os.path.basename(p) if p else "(NO WINNER)"
        by_owner[b] = by_owner.get(b, 0) + 1
        if p is None:
            fail1.append((tgi, b, "no winner - the TGI vanished"))
        elif "scoty" in b.lower():
            fail1.append((tgi, b, "still owned by a carbon dat"))
        elif b.startswith("z_SC4UIScale_ZCarbon"):
            fail1.append((tgi, b, "owned by a ZCarbon package that should be "
                                  "disarmed"))
    say("colliding TGIs checked: %d   reversion failures: %d"
        % (len(coll), len(fail1)))
    for b, n in sorted(by_owner.items(), key=lambda kv: -kv[1]):
        say("    %5d  %s" % (n, b))
    for tgi, b, why in fail1[:40]:
        say("  FAIL %08x/%08x/%08x -> %s (%s)" % (tgi + (b, why)))

    # ---------------- CHECK 2: baseline equality ---------------------------
    say()
    say("=== CHECK 2: BASELINE EQUALITY (the real proof) ===")
    diffs = []
    normalised = []
    nbase = 0
    for line in open(BASELINE, encoding="utf-8"):
        m = BASEROW.match(line.strip())
        if not m:
            continue
        tgi = (int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16))
        nbase += 1
        old = os.path.basename(m.group(4).strip())
        p = win_wo.get(tgi)
        new = os.path.basename(p) if p else "(NO WINNER)"
        if old == new:
            continue
        # DECLARED NORMALISATION, never silent: SelectiveArt is the
        # stable-filename pilot (ScaleTier.cpp:586). The baseline captured it
        # under its bare name; the model plans the same bare name carrying the
        # active tier's bytes. Any OTHER family/suffix difference is a diff.
        oldfam = re.sub(r"-(15x|2x|3x|4x)\.dat$", ".dat", old)
        newfam = re.sub(r"-(15x|2x|3x|4x)\.dat$", ".dat", new)
        if oldfam == newfam:
            normalised.append((tgi, old, new))
            continue
        diffs.append((tgi, old, new))
    say("baseline TGIs checked: %d   baseline diffs: %d   suffix-only "
        "(declared, see below): %d" % (nbase, len(diffs), len(normalised)))
    # SENSITIVITY CONTROL for the number above. A near-zero diff count only
    # means something if this comparison CAN produce a large one. Run the
    # identical comparison against the WITH-carbon state, where the answer is
    # known to be large by construction (carbon + ZCarbon own ~500 baseline
    # TGIs). If this control is also ~0, the comparison itself is broken.
    ctrl = 0
    for line in open(BASELINE, encoding="utf-8"):
        m = BASEROW.match(line.strip())
        if not m:
            continue
        tgi = (int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16))
        p = win_with.get(tgi)
        if os.path.basename(m.group(4).strip()) != (
                os.path.basename(p) if p else "(NO WINNER)"):
            ctrl += 1
    say("SENSITIVITY CONTROL: the same comparison against the WITH-carbon "
        "state yields %d diffs. The %d above is a measured near-zero, not a "
        "comparison that cannot fire." % (ctrl, len(diffs)))
    if ctrl < 50:
        say("CONTROL FAILED: the baseline comparison cannot detect the "
            "difference it is supposed to detect.")
        sys.exit(2)
    if normalised:
        seen = {}
        for tgi, o, n in normalised:
            seen[(o, n)] = seen.get((o, n), 0) + 1
        say("  DECLARED NORMALISATION - same package family, tier-suffix "
            "difference only. Nothing else was normalised:")
        for (o, n), c in sorted(seen.items(), key=lambda kv: -kv[1]):
            say("    %5d  %s  ->  %s" % (c, o, n))
    for tgi, o, n in diffs[:60]:
        wc = win_with.get(tgi)
        say("  DIFF %08x/%08x/%08x  %s  ->  %s   (with-carbon: %s)"
            % (tgi + (o, n, os.path.basename(wc) if wc else "(none)")))

    # ------------- CHECK 2b: ATTRIBUTION - is the diff even carbon's? ------
    # A baseline diff is only OUR uninstall bug if the carbon uninstall caused
    # it. The baseline is a snapshot of a MACHINE, and third-party mods come
    # and go on that machine independently of the skin. So for every diff
    # whose new winner is a DEP-GATED package, re-run the whole computation
    # with that package's dependency ALSO filtered out - i.e. simulate the
    # third-party mod being absent, as it was when the baseline was taken. If
    # the baseline winner comes back, the diff is attributable to that mod
    # arriving, not to the carbon uninstall. If it does NOT come back, the
    # diff is real and carbon-caused.
    if diffs:
        say()
        say("=== CHECK 2b: DIFF ATTRIBUTION ===")
        suspects = {}
        for _t, _o, n in diffs:
            fam = re.sub(r"-(15x|2x|3x|4x)\.dat$", "", n)
            for c in calls:
                if os.path.basename(c["base"]) != fam:
                    continue
                mm = re.search(r'DepOkByName\(\s*L"([^"]+)"', c["cond"])
                if mm:
                    suspects[fam] = mm.group(1).replace("\\\\", "\\")
        if not suspects:
            say("  no diff maps to a dep-gated package - nothing to attribute; "
                "these diffs stand as carbon-caused.")
        else:
            names = []
            for fam, pkg in sorted(suspects.items()):
                for r in rows:
                    if r["package"] == pkg:
                        names.append((r["file"], r["prefix"]))
                        if r["file2"]:
                            names.append((r["file2"], r["prefix"]))
                say("  suspect: %s is gated on %s - simulating that mod ABSENT "
                    "too (it post-dates the baseline capture)"
                    % (fam, ", ".join(n for n, _ in names)))

            def present_c(rel):
                if under_skin(rel):
                    return False
                b = os.path.basename(rel).lower()
                for n, pre in names:
                    if (b.startswith(n.lower()) if pre else b == n.lower()):
                        return False
                return True

            win_c = compute_state("skin+suspect-mod absent", files, owned,
                                  calls, stables, rows, present_c, contents,
                                  cache)[0]
            resolved, unresolved = [], []
            for tgi, o, n in diffs:
                p = win_c.get(tgi)
                nb = os.path.basename(p) if p else "(NO WINNER)"
                (resolved if nb == o else unresolved).append((tgi, o, n, nb))
            say("  diffs explained by the post-baseline mod arrival: %d/%d"
                % (len(resolved), len(diffs)))
            for tgi, o, n, nb in resolved[:20]:
                say("    EXPLAINED %08x/%08x/%08x  baseline %s restored "
                    "when the mod is absent" % (tgi + (o,)))
            for tgi, o, n, nb in unresolved[:20]:
                say("    CARBON-CAUSED %08x/%08x/%08x  %s -> %s (still %s "
                    "with the mod removed)" % (tgi + (o, n, nb)))
            diffs = [d[:3] for d in unresolved]
            say("  baseline diffs attributable to the CARBON UNINSTALL: %d"
                % len(diffs))

    # ---------------- CHECK 3: no orphans, every package gated -------------
    say()
    say("=== CHECK 3: NO ORPHANS / EVERY ZCARBON PACKAGE IS GATED ===")
    zc_armed = sorted(k for k, v in armed_wo.items()
                      if v and "ZCarbon" in k)
    zc_armed_with = sorted(k for k, v in armed_with.items()
                           if v and "ZCarbon" in k)
    say("ZCarbon packages armed WITH the skin:  %d  %s"
        % (len(zc_armed_with),
           ", ".join(os.path.basename(p) for p in zc_armed_with)))
    say("ZCarbon packages armed AFTER uninstall: %d  %s"
        % (len(zc_armed), ", ".join(os.path.basename(p) for p in zc_armed)
           or "(none - correct)"))
    zc_tgis = [t for t, p in win_wo.items()
               if os.path.basename(p).startswith("z_SC4UIScale_ZCarbon")]
    say("TGIs owned by a ZCarbon package after uninstall: %d" % len(zc_tgis))

    # every ZCarbon package ON DISK has a dep row AND a gated call site
    disk = set()
    for rel in files:
        b = os.path.basename(rel)
        if b.startswith("z_SC4UIScale_ZCarbon"):
            disk.add(re.sub(r"-(15x|2x|3x|4x)\.dat(\.x1-disabled)?$", "", b))
    gated_rows = {os.path.basename(r["package"]) for r in rows}
    call_dep = {}
    for c in calls:
        mm = re.search(r'DepOkByName\(\s*L"([^"]+)"', c["cond"])
        if mm:
            call_dep[os.path.basename(c["base"])] = \
                mm.group(1).replace("\\\\", "\\")
    ungated = sorted(d for d in disk if d not in gated_rows)
    nocall = sorted(d for d in disk if d not in call_dep)
    say("ZCarbon package families on disk: %d   without a kThirdPartyDeps "
        "row: %d   without a gated SyncDat call: %d"
        % (len(disk), len(ungated), len(nocall)))
    for d in ungated:
        say("  UNGATED (no dep row - would stay armed forever): %s" % d)
    for d in nocall:
        say("  NO CALL SITE (dep row computed then discarded - the #119 "
            "WarriorUI shape): %s" % d)
    # and the reverse: a dep row whose package has no SyncDat call is inert
    inert = sorted(os.path.basename(r["package"]) for r in rows
                   if os.path.basename(r["package"]) not in call_dep)
    if inert:
        say("  INERT DEP ROWS (row exists, no gated call site): %s"
            % ", ".join(inert))

    say()
    say("=== DEP RESOLUTION AFTER UNINSTALL (what the DLL would log) ===")
    for r in rows:
        p = os.path.basename(r["package"])
        say("  %-34s %-8s %s" % (p, "ARMED" if dep_wo[r["package"]]
                                 else "disarmed", det_wo[r["package"]]))

    # ---------------- CHECK 4: PARTIAL UNINSTALL MATRIX --------------------
    # A full uninstall is the EASY case: nothing of carbon's is left to beat
    # our stock layer. The dangerous case is PARTIAL - some skin dats deleted,
    # others still installed - because a ZCarbon package that DISARMS while
    # the carbon dat it was overriding is STILL LOADING hands those TGIs back
    # to carbon's own 1x art inside a scaled cell. ScaleTier.cpp:2790 already
    # says this in words ("THE SKIN IS STILL INSTALLED, so nothing of ours
    # takes over"); this measures exactly how many TGIs each partial state
    # costs, and which of them.
    say()
    say("=== CHECK 4: PARTIAL-UNINSTALL MATRIX ===")
    carbon_dats = {}          # basename -> set of TGIs
    for rel in files:
        b = os.path.basename(rel)
        if not under_skin(rel) or not b.lower().endswith(DBPF_EXTS):
            continue
        carbon_dats[b] = set(list_tgis(cache, os.path.join(PLUG, rel)))
    zc_cov = {}               # ZCarbon package base -> set of TGIs
    for rel in files:
        b = os.path.basename(rel)
        if not b.startswith("z_SC4UIScale_ZCarbon"):
            continue
        if ACTIVE_TAG + ".dat" not in b:
            continue
        fam = re.sub(r"-(15x|2x|3x|4x)\.dat(\.x1-disabled)?$", "", b)
        zc_cov[fam] = set(list_tgis(cache, os.path.join(PLUG, rel)))
    json.dump(cache, open(CACHE, "w"))

    pinned = {}               # ZCarbon base -> set of dat names its gate pins
    for r in rows:
        p = os.path.basename(r["package"])
        if "ZCarbon" not in p:
            continue
        s = {r["file"].lower()}
        if r["file2"]:
            s.add(r["file2"].lower())
        pinned[p] = s
    gate_dats = sorted({d for s in pinned.values() for d in s})
    say("skin dats installed: %d   gate-relevant: %d   %s"
        % (len(carbon_dats), len(gate_dats), ", ".join(gate_dats)))

    # 4a. UNPINNED SOURCES: a carbon dat that supplies TGIs our package
    # overrides but that NO gate row pins. Deleting only that dat leaves our
    # package ARMED over content whose original is gone - the reverse hazard.
    say()
    say("-- 4a. contributing skin dats vs what each gate actually pins --")
    # The number that matters is COVERAGE: how many of a package's TGIs are
    # supplied by a skin dat its own gate row PINS. A TGI supplied only by an
    # UNPINNED skin dat is the reverse hazard - delete that dat and our copy
    # stays armed over content whose original is gone. A TGI supplied by NO
    # skin dat at all is stock-derived and carries no such risk.
    unpinned_only = []
    for pkg in sorted(zc_cov):
        pin = pinned.get(pkg, set())
        pinned_tgis, unpinned_tgis = set(), set()
        contrib = []
        for d, t in sorted(carbon_dats.items()):
            hit = zc_cov[pkg] & t
            if not hit:
                continue
            contrib.append((d, len(hit), d.lower() in pin))
            (pinned_tgis if d.lower() in pin else unpinned_tgis).update(hit)
        only = unpinned_tgis - pinned_tgis
        nostock = zc_cov[pkg] - pinned_tgis - unpinned_tgis
        say("  %-32s %4d TGIs | %4d from a PINNED skin dat | %d from an "
            "UNPINNED one only | %d from no skin dat (stock-derived)"
            % (pkg, len(zc_cov[pkg]), len(pinned_tgis), len(only),
               len(nostock)))
        for d, n, isp in sorted(contrib, key=lambda kv: -kv[1]):
            say("        %-46s %4d%s" % (d, n, "" if isp else "   (unpinned)"))
        if only:
            unpinned_only.append((pkg, sorted(only)))
    say("  packages with TGIs sourced ONLY from an unpinned skin dat: %d"
        % len(unpinned_only))
    for pkg, t in unpinned_only:
        say("    %s: %d" % (pkg, len(t)))

    # 4b. THE MATRIX: every subset of the gate-relevant dats. All other skin
    # dats are held PRESENT (the worst case for "carbon still loads").
    say()
    say("-- 4b. armed set + cost, over every subset of the %d gate dats --"
        % len(gate_dats))
    say("   (skin dats outside the gate set are held INSTALLED: worst case)")
    # LOAD-ORDER CORRECTION, or the number is an upper bound. "zz-scoty-mods"
    # sorts BEFORE "zzz-SC4UIScale" under BOTH case-foldings ('-' 0x2D beats
    # both 'z' 0x7A and 'Z' 0x5A), so our OTHER zzz packages still out-sort a
    # remaining carbon dat and keep covering their TGIs. Only 010-SC4UIScale
    # loses to the skin. So a TGI is really left at carbon 1x only if NO armed
    # zzz package of ours covers it.
    zzz_cover = set()
    for rel, src in tree_wo.items():
        if rel.lower().startswith("zzz-sc4uiscale"):
            zzz_cover |= set(contents.get(rel, ()))
    say("  armed non-ZCarbon zzz-SC4UIScale packages still cover %d TGIs "
        "(they out-sort the skin folder under both case-foldings)"
        % len(zzz_cover))
    outcomes = {}
    for mask in range(1 << len(gate_dats)):
        gone = {gate_dats[i] for i in range(len(gate_dats))
                if mask & (1 << i)}
        remain_tgis = set()
        for d, t in carbon_dats.items():
            if d.lower() not in gone:
                remain_tgis |= t
        armed = [p for p in sorted(zc_cov)
                 if not (pinned.get(p, set()) & gone)]
        covered = set(zzz_cover)
        for p in armed:
            covered |= zc_cov[p]
        lost = set()
        for pkg in sorted(zc_cov):
            if pkg not in armed:
                lost |= (zc_cov[pkg] & remain_tgis) - covered
        cost = len(lost)
        key = (tuple(armed), cost)
        outcomes.setdefault(key, []).append(gone)
    say("  distinct outcomes: %d over %d subsets"
        % (len(outcomes), 1 << len(gate_dats)))
    rank = sorted(outcomes.items(), key=lambda kv: -kv[0][1])
    say("  -- the %d SINGLE-FILE deletions, worst first --" % len(gate_dats))
    singles = []
    for (armed, cost), examples in rank:
        for g in examples:
            if len(g) == 1:
                singles.append((cost, next(iter(g)), armed))
    for cost, g, armed in sorted(singles, reverse=True):
        say("    delete %-46s -> %d/8 armed, %4d TGIs left to carbon 1x"
            % (g, len(armed), cost))
        if cost:
            say("        disarmed: %s" % ", ".join(
                p.replace("z_SC4UIScale_", "") for p in sorted(zc_cov)
                if p not in armed))
    say("  -- the 3 worst outcomes of any size --")
    for (armed, cost), examples in rank[:3]:
        smallest = min(examples, key=len)
        say("    cost %4d | armed %d/8 | smallest trigger: delete %s"
            % (cost, len(armed), ", ".join(sorted(smallest)) or "(nothing)"))
    worst = rank[0][0][1] if rank else 0
    say("  WORST partial state costs %d TGIs; a FULL uninstall costs 0 "
        "(nothing of carbon's is left to win) - measured by CHECK 1 above."
        % worst)

    # ---------------- TREE-STABILITY GUARD ---------------------------------
    say()
    say("=== TREE STABILITY ===")
    stamp1 = tree_stamp(PLUG)
    moved_files = sorted(set(stamp0) ^ set(stamp1)) + sorted(
        k for k in set(stamp0) & set(stamp1) if stamp0[k] != stamp1[k])
    say("files whose size/mtime changed DURING this run: %d"
        % len(moved_files))
    for m in moved_files[:20]:
        say("  MOVED %s" % m)
    if moved_files:
        say("RUN INVALID: the live tree was rewritten while it was being "
            "read (a concurrent deploy). Re-run on a settled tree.")

    ok = not fail1 and not diffs and not zc_armed and not zc_tgis \
        and not ungated and not nocall and not moved_files
    say()
    say("UNINSTALL PROOF: %s" % ("GREEN" if ok else "RED"))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LOG))
        f.write("\n\n=== POST-UNINSTALL WINNERS, colliding set (%d) ===\n"
                % len(coll))
        for tgi in sorted(coll_set):
            p = win_wo.get(tgi)
            f.write("0x%08X 0x%08X 0x%08X -> %s\n"
                    % (tgi + (os.path.basename(p) if p else "(NO WINNER)",)))
    print("wrote %s" % OUT)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
