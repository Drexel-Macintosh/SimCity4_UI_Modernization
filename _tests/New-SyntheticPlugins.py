#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
New-SyntheticPlugins.py - a synthetic SimCity 4 Plugins tree with KNOWN ANSWERS.

    python _tests\New-SyntheticPlugins.py --files 1000
    python _tests\New-SyntheticPlugins.py --files 50000 --big-index --long-paths 20

The boot-walk harness (_tests\Test-BootWalk.ps1) drives this. The tree is a
CONSUMER-SHAPED input for the DLL's boot walks - sc4pac layout, the four DBPF
extensions the game scans, our own release bundle copied in as "ours", every
third-party dependency filename from src\ScaleTier.cpp's kThirdPartyDeps table
planted (or deliberately not), a 200,000-entry index, paths past 260
characters - and manifest.json is the answer key: every count the walks are
supposed to produce, MEASURED from the tree after it is written, never
inferred from the plan.

DANGER - READ BEFORE RUNNING
----------------------------
* IT WRITES N FILES (--files; default 1000; the harness runs it at 50,000)
  plus the directories to hold them, a ~160 MB copy of our own bundle, a 4 MB
  200,000-entry DBPF with --big-index, directories whose full paths exceed 260
  characters with --long-paths, an OFFLINE-attributed file with --offline-file
  and a Plugins-into-Plugins junction loop with --junction.
* IT DELETES AND REBUILDS its own --out directory when the recorded parameters
  differ from the ones asked for (or with --force). It only ever deletes a
  directory that carries its own manifest.json marker; anything else is
  refused and left alone.
* IT REFUSES any --out under OneDrive, under Documents\SimCity 4 (the live
  Plugins tree), under the game install, or with a "SimCity 4" component
  anywhere in the path. Default: C:\dev\_scale\Plugins-<N>.
* It never launches, attaches to, or reads the game.

IDEMPOTENT PER SEED: the same arguments produce the same bytes (DBPF header
timestamps are derived from the seed). A rerun with identical parameters
finds its own manifest and REUSES the tree in a fraction of a second.

PLANTED FIXTURES (all counted inside --files)
  NetworkAddonMod_Controller.dat        3 dirs below root (--nam-depth 3) or 4
                                        (--nam-depth 4): FindPluginFile's
                                        depth-4 budget reaches 3, not 4.
  z_Full Screen - Web Button Improvement Mod v1.dat
                                        3 dirs below root but inside a folder
                                        chain of 3 x 120-char segments, so its
                                        path is ~390 chars: visible only to a
                                        \\?\ walk with kLongPath buffers.
  scoty_Carbon_Files.dat                present at the WRONG size (pinned+1).
  SaveWarning_Disable_Exit_Quit.dat     duplicated in two folders, both at the
                                        pinned size (a DUPLICATE dep source).
  CAM / CoriBoom / warrior / null-45    present at their pinned sizes.
  every other kThirdPartyDeps filename  ABSENT.
  zzz_after-us\a.dat, ~tilde\b.dat      top-level folders that sort AFTER ours
                                        (must trigger the load-order warning).
  900-overrides\c.dat                   sorts before zzz-SC4UIScale (must not).
  big-index.dat (--big-index)           200,000 index entries, 8 of them icons:
                                        the DLL's `count < 200000` guard skips
                                        the whole file.
  <long-path j>\deep-item-j.dat         (--long-paths L) L-1 more DBPFs that
                                        only a long-path walk can reach.
"""
import argparse
import ctypes
import hashlib
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time

ICON_T, ICON_G = 0x856DDBAC, 0x6A386D26
FILLER_T, FILLER_G = 0x6534284A, 0x2026960B      # exemplar-ish, never an icon
EXTS = [".dat", ".SC4Lot", ".SC4Desc", ".SC4Model"]
DBPF_EXTS = {".dat", ".sc4lot", ".sc4desc", ".sc4model"}
GENERATOR = "New-SyntheticPlugins.py"
GEN_VERSION = 1
MAX_PATH = 260
INST_BASE = 0x40000000
FILE_ATTRIBUTE_OFFLINE = 0x1000
BIG_INDEX_ENTRIES = 200000

CATEGORIES = [
    "050-load-first", "100-props-textures", "150-mods", "170-terrain",
    "200-residential", "300-commercial", "360-landmark", "400-industrial",
    "500-utilities", "600-civics", "610-safety", "700-transit",
    "710-automata", "770-network-addon-mod", "777-network-addon-mod",
    "900-overrides",
]
GROUPS = ["mattb325", "simmer2", "kingofsimcity", "diego-del-llano", "sm2",
          "memo", "t-wrecks", "pegasus", "jasoncw", "nofunk", "girafe", "orange"]
WORDS = ["residential-pack", "commercial-w2w", "industrial-props", "trees",
         "seaport", "landmark", "textures", "civic-buildings", "fillers",
         "streetside", "hd-vehicles", "terrain-mod"]

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
def lp(p):
    r"""Long-path form: \\?\ prefix + absolute path. Required for anything that
    might exceed 260 characters; harmless on everything else."""
    p = os.path.abspath(p)
    if p.startswith("\\\\?\\"):
        return p
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p[2:]
    return "\\\\?\\" + p


def unlp(p):
    if p.startswith("\\\\?\\UNC\\"):
        return "\\\\" + p[8:]
    if p.startswith("\\\\?\\"):
        return p[4:]
    return p


def my_documents():
    buf = ctypes.create_unicode_buffer(MAX_PATH)
    try:
        # CSIDL_PERSONAL = 5: honours a OneDrive-redirected Documents.
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Documents")


def refuse_if_unsafe(out):
    """The refusal list. Every entry here is a place the game, OneDrive, or the
    player owns; a synthetic tree written there is a disaster, not a test."""
    norm = os.path.normcase(os.path.abspath(out)).rstrip("\\")
    parts = norm.split("\\")
    reasons = []
    if len(parts) < 3:
        reasons.append("a drive root or a first-level folder is not an acceptable --out")
    for comp in parts:
        c = comp.lower()
        if c == "onedrive" or c.startswith("onedrive -") or c.startswith("onedrive-"):
            reasons.append("the path has a OneDrive component (%s)" % comp)
        if c in ("simcity 4", "simcity 4 deluxe", "simcity 4 deluxe edition"):
            reasons.append("the path has a game folder component (%s)" % comp)
    for env in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial", "SC4_GAME_DIR"):
        v = os.environ.get(env)
        if v:
            base = os.path.normcase(os.path.abspath(v)).rstrip("\\")
            if norm == base or norm.startswith(base + "\\"):
                reasons.append("the path is under %%%s%% (%s)" % (env, v))
    docs = [my_documents(), os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Documents")]
    for d in docs:
        base = os.path.normcase(os.path.abspath(os.path.join(d, "SimCity 4"))).rstrip("\\")
        if norm == base or norm.startswith(base + "\\"):
            reasons.append("the path is under Documents\\SimCity 4 (%s)" % d)
    steam = os.path.normcase(r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe")
    if norm.startswith(steam):
        reasons.append("the path is under the Steam install")
    if reasons:
        sys.stderr.write("REFUSED: --out %s\n" % out)
        for r in reasons:
            sys.stderr.write("  - %s\n" % r)
        sys.stderr.write("This script writes thousands of files and deletes its own output; "
                         "point it at C:\\dev\\_scale\\... or another scratch location.\n")
        sys.exit(2)


# ---------------------------------------------------------------------------
# kThirdPartyDeps - parsed the way _tests\Test-ThirdPartyGates.ps1 parses it
# ---------------------------------------------------------------------------
def parse_third_party_deps(src):
    text = open(src, encoding="utf-8").read()
    m = re.search(r"kThirdPartyDeps\[\]\s*=\s*\{(?P<body>.*?)\n\t\};", text, re.S)
    if not m:
        raise SystemExit("could not parse kThirdPartyDeps out of %s" % src)
    row = re.compile(
        r'\{\s*L"(?P<pkg>[^"]+)",\s*L"(?P<f1>(?:[^"\\]|\\.)*)",\s*(?P<pre>true|false),'
        r'\s*(?P<s1>\d+),\s*(?:L"(?P<f2>(?:[^"\\]|\\.)*)"|nullptr),\s*(?P<s2>\d+)\s*\}')

    def unesc(s):
        return None if s is None else s.replace("\\\\", "\\")

    rows = []
    for mm in row.finditer(m.group("body")):
        rows.append(dict(
            package=unesc(mm.group("pkg")),
            modFile=unesc(mm.group("f1")),
            prefix=(mm.group("pre") == "true"),
            modSize=int(mm.group("s1")),
            modFile2=unesc(mm.group("f2")),
            modSize2=int(mm.group("s2")),
        ))
    if not rows:
        raise SystemExit("kThirdPartyDeps parsed as empty")
    return rows


def distinct_needles(rows):
    """One entry per DISTINCT (name, prefix) pair - the DLL memoises its walks
    on exactly that key (ScaleTier.cpp: findCached)."""
    seen = {}
    for r in rows:
        for name, size in ((r["modFile"], r["modSize"]), (r["modFile2"], r["modSize2"])):
            if not name:
                continue
            key = (name.lower(), r["prefix"])
            if key not in seen:
                seen[key] = dict(name=name, prefix=r["prefix"], expectedSize=size, packages=[])
            seen[key]["packages"].append(r["package"])
            if seen[key]["expectedSize"] == 0 and size:
                seen[key]["expectedSize"] = size
    return list(seen.values())


# ---------------------------------------------------------------------------
# DBPF writer - dbpf_pack lifted from tools\dbpf\row15-probe\build_row15_probe.py
# (index major 7 / minor 0, 20-byte entries T,G,I,offset,size; header: count at
# 0x24, index offset 0x28, index size 0x2C, index minor 0x3C; NOTES-PACK.md)
# ---------------------------------------------------------------------------
def dbpf_pack(records, out_path, now=None):
    now = int(time.time()) if now is None else now
    rows = sorted(records, key=lambda r: r["tgi"])
    body, offsets = bytearray(), []
    off = 96
    for r in rows:
        offsets.append((r["tgi"], off, len(r["data"])))
        body += r["data"]
        off += len(r["data"])
    idx_off, idx_size = off, len(rows) * 20
    hdr = bytearray(96)
    hdr[0:4] = b"DBPF"
    struct.pack_into("<II", hdr, 4, 1, 0)                 # 1.0
    struct.pack_into("<II", hdr, 0x18, now, now)
    struct.pack_into("<I", hdr, 0x20, 7)                  # index major
    struct.pack_into("<III", hdr, 0x24, len(rows), idx_off, idx_size)
    struct.pack_into("<III", hdr, 0x30, 0, 0, 0)          # no holes
    struct.pack_into("<I", hdr, 0x3C, 0)                  # index minor -> 7.0
    idx = bytearray()
    for (t, g, i), o, n in offsets:
        idx += struct.pack("<IIIII", t, g, i, o, n)
    with open(out_path, "wb") as f:
        f.write(bytes(hdr) + bytes(body) + bytes(idx))
    return rows, idx_off, idx_size


def dbpf_bytes_size(records):
    return 96 + sum(len(r["data"]) for r in records) + 20 * len(records)


def read_icon_instances(path):
    """The index reader the manifest's truth comes from. Same header offsets
    and stride rule as ScaleTier.cpp ReadIconTgis, WITHOUT its
    `count < 200000` guard - the manifest records what is in the file."""
    with open(path, "rb") as f:
        hdr = f.read(0x68)
        if len(hdr) < 0x60 or hdr[:4] != b"DBPF":
            return None
        count, offset, size = struct.unpack_from("<III", hdr, 0x24)
        idx_min = struct.unpack_from("<I", hdr, 0x3C)[0]
        stride = 24 if idx_min == 1 else 20
        if count == 0 or offset == 0:
            return set()
        f.seek(offset)
        idx = f.read(count * stride)
    out = set()
    if len(idx) < count * stride:
        return None
    for i in range(count):
        t, g, inst = struct.unpack_from("<III", idx, i * stride)
        if t == ICON_T and g == ICON_G:
            out.add(inst)
    return out


def make_png_strip(seed_val):
    """A real 176x44 RGBA 4-cell strip: what an ItemIcon payload looks like."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (176, 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for cell in range(4):
        r = (seed_val * 37 + cell * 61) & 0xFF
        g = (seed_val * 91 + cell * 17) & 0xFF
        b = (seed_val * 53 + cell * 101) & 0xFF
        x0 = cell * 44
        d.rectangle([x0 + 2, 2, x0 + 41, 41], fill=(r, g, b, 255), outline=(255, 255, 255, 255))
        d.line([x0 + 4, 4, x0 + 39, 39], fill=(255 - r, 255 - g, 255 - b, 255), width=2)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def build_records(icons, png0, target_size, filler_entries, item_index):
    recs = []
    for k, inst in enumerate(icons):
        data = png0 if (k == 0 and png0 is not None) else b"\x00"
        recs.append(dict(tgi=(ICON_T, ICON_G, inst), data=data))
    for j in range(filler_entries):
        recs.append(dict(tgi=(FILLER_T, FILLER_G, (item_index << 20) | j), data=b"\x00"))
    if target_size is not None:
        cur = dbpf_bytes_size(recs) + 20      # + the pad entry's own index row
        pad = target_size - cur
        if pad < 0:
            raise SystemExit("target size %d too small for %d entries" % (target_size, len(recs)))
        recs.append(dict(tgi=(FILLER_T, FILLER_G, 0xFFFF0000 | (item_index & 0xFFFF)), data=bytes(pad)))
    return recs


# ---------------------------------------------------------------------------
# the plan
# ---------------------------------------------------------------------------
def long_segment(prefix, j, n=120):
    s = "%s-%02d-" % (prefix, j)
    s += "".join("abcdefghijklmnopqrstuvwxyz"[(i * 7 + j) % 26] for i in range(n))
    return s[:n]


def build_plan(a, needles, ours_sorted):
    """Returns (items, facts). Each item: rel (path below root), icons list,
    png (bool), targetSize, filler, role. Fixture rows come first so their
    icon instances are stable across --files values."""
    K = a.icons_per_file
    items = []
    facts = dict(needlePlan={}, orderingWarnFolders=["zzz_after-us", "~tilde"],
                 orderingOkFolders=["900-overrides"])

    by_lower = {n["name"].lower(): n for n in needles}

    def needle(sub):
        hits = [n for n in needles if sub.lower() in n["name"].lower()]
        if len(hits) != 1:
            raise SystemExit("fixture contract broken: expected exactly one kThirdPartyDeps "
                             "needle containing %r, found %d" % (sub, len(hits)))
        return hits[0]

    nam = needle("NetworkAddonMod")
    web = needle("Web Button Improvement Mod")
    carbon_core = needle("scoty_Carbon_Files")
    dup = needle("SaveWarning_Disable_Exit_Quit")
    facts["namNeedle"] = nam["name"]
    facts["webButtonNeedle"] = web["name"]
    facts["wrongSizeNeedle"] = carbon_core["name"]
    facts["duplicateNeedle"] = dup["name"]

    def size_for(n, delta=0):
        return (n["expectedSize"] if n["expectedSize"] else 4096 + len(items)) + delta

    def plant(n, rel_dir, filename=None, delta=0, covered=False, role="needle"):
        fn = filename or n["name"]
        rel = rel_dir + "\\" + fn if rel_dir else fn
        items.append(dict(rel=rel, targetSize=size_for(n, delta), filler=0,
                          covered=covered, role=role, needle=n["name"]))
        facts["needlePlan"].setdefault(n["name"], []).append(rel)

    # --- NAM at depth 3 or 4 ------------------------------------------------
    nam_dir = "770-network-addon-mod\\9-patches\\nam.controller.left-hand-drive.4.9.sc4pac"
    if a.nam_depth == 4:
        nam_dir += "\\Controller"
    plant(nam, nam_dir, covered=True, role="nam")
    facts["namRel"] = items[-1]["rel"]
    facts["namDepth"] = a.nam_depth

    # --- the web button, past MAX_PATH ---------------------------------------
    long_dirs = []
    for j in range(a.long_paths):
        long_dirs.append("\\".join([long_segment("long-path", j),
                                    long_segment("second-segment", j),
                                    long_segment("third-segment", j)]))
    if a.long_paths >= 1:
        plant(web, long_dirs[0], filename=web["name"] + " v1.dat", role="webbutton")
        facts["webButtonRel"] = items[-1]["rel"]
        facts["webButtonPresent"] = True
    else:
        facts["webButtonRel"] = None
        facts["webButtonPresent"] = False

    # --- wrong size, duplicate, present-ok -----------------------------------
    plant(carbon_core, "150-mods\\scoty.carbon-skin.1.5.sc4pac", delta=1, role="wrongsize")
    plant(dup, "150-mods\\cyclone-boom.save-warning.1.0.sc4pac", covered=True, role="dup1")
    plant(dup, "150-mods\\zz_old-manual-install", role="dup2")
    present_ok = {
        "cam_extended_essentials.dat": "050-load-first\\cam.colossus-addon-mod.4.0.1.sc4pac",
        "cam_intro.dat": "050-load-first\\cam.colossus-addon-mod.4.0.1.sc4pac",
        "ui_compact.dat": "150-mods\\warrior.god-terraforming-in-mayor-mode.1.0.sc4pac",
        "mayor_sign_menu.dat": "150-mods\\warrior.god-terraforming-in-mayor-mode.1.0.sc4pac",
        "raise the ui mod.dat": "150-mods\\warrior.raise-the-ui-mod.1.0.sc4pac",
        "regioncensusui.dat": "150-mods\\null-45.region-view-census-ui.1.0.1.sc4pac",
    }
    for key, rel_dir in present_ok.items():
        if key in by_lower:
            plant(by_lower[key], rel_dir)
    for n in needles:
        if n["prefix"] and "coriboom" in n["name"].lower():
            plant(n, "150-mods\\coriboom.36-slot-building-styles-ui.2.0.sc4pac",
                  filename=n["name"] + " v2.dat")

    # --- load-order fixtures ------------------------------------------------
    for rel in ("zzz_after-us\\a.dat", "~tilde\\b.dat", "900-overrides\\c.dat"):
        items.append(dict(rel=rel, targetSize=None, filler=0, covered=False, role="ordering", needle=None))

    # --- the big index ------------------------------------------------------
    if a.big_index:
        items.append(dict(rel="150-mods\\big.index-stress.1.0.sc4pac\\big-index.dat", targetSize=None,
                          filler=BIG_INDEX_ENTRIES - K, covered=False, role="bigindex", needle=None))
        facts["bigIndexRel"] = items[-1]["rel"]
    else:
        facts["bigIndexRel"] = None

    # --- long-path fillers --------------------------------------------------
    for j in range(1, a.long_paths):
        items.append(dict(rel=long_dirs[j] + "\\deep-item-%02d.dat" % j, targetSize=None, filler=0,
                          covered=False, role="longpath", needle=None))

    # --- bulk ---------------------------------------------------------------
    n_fixture = len(items)
    if a.files < n_fixture:
        raise SystemExit("--files %d is below the %d planted fixtures" % (a.files, n_fixture))
    D = a.dirs
    pkg_dirs = []
    for i in range(D):
        cat = CATEGORIES[i % len(CATEGORIES)]
        name = "%s.%s-%d.%d.%d.0.sc4pac" % (GROUPS[i % len(GROUPS)], WORDS[(i * 7) % len(WORDS)],
                                             i, 1 + i % 3, i % 7)
        sub = ["", "\\lots", "\\lots\\growables"][i % 3]
        pkg_dirs.append(cat + "\\" + name + sub)
    for f in range(a.files - n_fixture):
        d = pkg_dirs[f % D]
        items.append(dict(rel=d + "\\item-%06d%s" % (f, EXTS[f % 4]), targetSize=None, filler=0,
                          covered=(f == 0), role="bulk", needle=None))

    # --- icons ---------------------------------------------------------------
    covered_slot = 0
    for idx, it in enumerate(items):
        if it["covered"] and len(ours_sorted) >= (covered_slot + 1) * K:
            it["icons"] = ours_sorted[covered_slot * K:(covered_slot + 1) * K]
            covered_slot += 1
        else:
            it["covered"] = False
            it["icons"] = [INST_BASE + idx * K + k for k in range(K)]
        it["png"] = idx < a.png_subset
    facts["coveredFiles"] = covered_slot
    facts["fixtureFiles"] = n_fixture
    facts["longPathDirs"] = long_dirs
    return items, facts


# ---------------------------------------------------------------------------
# survey - THE TRUTH IS MEASURED FROM DISK, not copied from the plan
# ---------------------------------------------------------------------------
def survey(root, needles):
    root_l = lp(root)
    st = dict(dirs=0, files=0, bytes=0, longPrefixed=0, longPlain=0, thirdPartyDbpf=0, oursDbpf=0,
              maxPathLen=0, deepest=0)
    ours, theirs = set(), set()
    per_file_icons = {}
    all_files = []       # (rel, name, size, depth, pathlen)
    unreadable = []
    to_read = []         # (rel, full, isOurs) - read AFTER the walk, in parallel:
                         # the first open of a freshly written file costs ~10 ms
                         # on a machine with a real-time scanner (measured:
                         # 19.5 s of a 21 s run at N=2000), and those waits
                         # overlap perfectly across threads.

    def walk(d, rel, depth):
        with os.scandir(d) as it:
            entries = sorted(it, key=lambda e: e.name.lower())
        for e in entries:
            full = e.path
            plain = unlp(full)
            n = len(plain)
            st["maxPathLen"] = max(st["maxPathLen"], n)
            if n + 4 > MAX_PATH:
                st["longPrefixed"] += 1
            if n > MAX_PATH:
                st["longPlain"] += 1
            r = (rel + "\\" + e.name) if rel else e.name
            if e.is_dir(follow_symlinks=False):
                if e.is_junction() or e.is_symlink():
                    continue
                st["dirs"] += 1
                st["deepest"] = max(st["deepest"], depth + 1)
                walk(full, r, depth + 1)
                continue
            if depth == 0 and e.name.lower() == "manifest.json":
                # The answer key is not part of the tree it describes: the
                # harness's walk WILL see it, and adds it back knowingly.
                continue
            sz = e.stat(follow_symlinks=False).st_size
            st["files"] += 1
            st["bytes"] += sz
            all_files.append((r, e.name, sz, depth, n))
            ext = os.path.splitext(e.name)[1].lower()
            if ext in DBPF_EXTS:
                is_ours = e.name.lower().startswith("z_sc4uiscale_")
                if is_ours:
                    st["oursDbpf"] += 1
                else:
                    st["thirdPartyDbpf"] += 1
                to_read.append((r, full, is_ours))

    walk(root_l, "", 0)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=32) as pool:
        results = list(pool.map(lambda t: read_icon_instances(t[1]), to_read))
    for (r, full, is_ours), inst in zip(to_read, results):
        if inst is None:
            unreadable.append(r)
            inst = set()
        per_file_icons[r] = inst
        if is_ours:
            ours.update(inst)
        else:
            theirs.update(inst)

    needle_facts = {}
    for nd in needles:
        name_l = nd["name"].lower()
        hits = []
        for r, nm, sz, depth, n in all_files:
            ok = nm.lower().startswith(name_l) if nd["prefix"] else (nm.lower() == name_l)
            if ok:
                hits.append(dict(rel=r, size=sz, depth=depth, pathLen=n))
        hits.sort(key=lambda h: [c.lower() for c in h["rel"].split("\\")])
        first = hits[0] if hits else None
        if not hits:
            verdict = "absent"
        elif nd["expectedSize"] and first["size"] != nd["expectedSize"]:
            verdict = "changed"
        else:
            verdict = "ok"
        needle_facts[nd["name"]] = dict(
            name=nd["name"], prefix=nd["prefix"], expectedSize=nd["expectedSize"],
            packages=nd["packages"],
            present=bool(hits), matches=len(hits),
            firstRel=first["rel"] if first else None,
            size=first["size"] if first else 0,
            firstDepth=first["depth"] if first else None,
            firstPathLen=first["pathLen"] if first else None,
            deepestDepth=max(h["depth"] for h in hits) if hits else None,
            shallowestDepth=min(h["depth"] for h in hits) if hits else None,
            withinDepth4=bool(hits) and min(h["depth"] for h in hits) <= 3,
            withinMaxPath=bool(hits) and all(h["pathLen"] < MAX_PATH for h in hits),
            paths=[h["rel"] for h in hits],
            verdictCorrectWalk=verdict,
        )
    return st, ours, theirs, per_file_icons, needle_facts, unreadable


def sha1_list(insts):
    return hashlib.sha1(("".join("%08X\n" % i for i in sorted(insts))).encode("ascii")).hexdigest()


# ---------------------------------------------------------------------------
def newest_bundle():
    dist = os.path.join(REPO, "dist")
    cands = [d for d in os.listdir(dist) if d.startswith("SC4UIScale-v") and not d.endswith("-dev")
             and os.path.isdir(os.path.join(dist, d, "Plugins"))]
    if not cands:
        raise SystemExit("no built bundle under dist\\; pass --bundle")
    cands.sort(key=lambda d: [int(x) if x.isdigit() else x for x in re.split(r"[.\-]", d[len("SC4UIScale-v"):])])
    return os.path.join(dist, cands[-1], "Plugins")


def copy_bundle(bundle, out):
    n = 0
    for name in ("010-SC4UIScale", "zzz-SC4UIScale"):
        src = os.path.join(bundle, name)
        if not os.path.isdir(src):
            raise SystemExit("bundle lacks %s: %s" % (name, bundle))
        dst = lp(os.path.join(out, name))
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            sp = os.path.join(src, f)
            if os.path.isfile(sp):
                shutil.copyfile(sp, dst + "\\" + f)
                n += 1
    dll = os.path.join(bundle, "SC4UIScale.dll")
    if not os.path.isfile(dll):
        raise SystemExit("bundle lacks SC4UIScale.dll: %s" % bundle)
    shutil.copyfile(dll, lp(os.path.join(out, "SC4UIScale.dll")))
    return n + 1


def params_fingerprint(a, bundle):
    keys = dict(files=a.files, icons_per_file=a.icons_per_file, png_subset=a.png_subset, dirs=a.dirs,
                long_paths=a.long_paths, big_index=a.big_index, nam_depth=a.nam_depth,
                offline_file=a.offline_file, junction=a.junction, seed=a.seed,
                bundle=os.path.basename(os.path.dirname(bundle)), gen=GEN_VERSION)
    return hashlib.sha1(json.dumps(keys, sort_keys=True).encode()).hexdigest(), keys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None, help=r"tree root (default C:\dev\_scale\Plugins-<N>)")
    ap.add_argument("--files", type=int, default=1000, help="third-party DBPF count, fixtures included")
    ap.add_argument("--icons-per-file", type=int, default=8)
    ap.add_argument("--png-subset", type=int, default=200,
                    help="how many DBPFs get a real 176x44 RGBA strip PNG as icon 0 (the rest are 1-byte payloads)")
    ap.add_argument("--dirs", type=int, default=None, help="package directories for the bulk files (default files//40, min 8)")
    ap.add_argument("--long-paths", type=int, default=20, help="folder chains of 3 x 120-char segments (>260-char paths)")
    ap.add_argument("--big-index", action="store_true", help="one big-index.dat with %d index entries" % BIG_INDEX_ENTRIES)
    ap.add_argument("--bundle", default=None, help=r"dist\SC4UIScale-vX.Y.Z\Plugins (default: newest non-dev)")
    ap.add_argument("--nam-depth", type=int, choices=(3, 4), default=3)
    ap.add_argument("--offline-file", action="store_true", help="set FILE_ATTRIBUTE_OFFLINE on one dat")
    ap.add_argument("--junction", action="store_true", help="mklink /J <out>\\Plugins -> <out> (a loop)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--force", action="store_true", help="rebuild even when the manifest says the tree is current")
    ap.add_argument("--src", default=os.path.join(REPO, "src", "ScaleTier.cpp"))
    a = ap.parse_args()

    if a.dirs is None:
        a.dirs = max(8, a.files // 40)
    if a.png_subset > a.files:
        a.png_subset = a.files
    out = a.out or os.path.join(r"C:\dev\_scale", "Plugins-%d" % a.files)
    out = os.path.abspath(out)
    refuse_if_unsafe(out)
    bundle = os.path.abspath(a.bundle) if a.bundle else newest_bundle()
    if not os.path.isdir(os.path.join(bundle, "010-SC4UIScale")):
        raise SystemExit("--bundle must be the Plugins folder of a built bundle: %s" % bundle)
    fp, params = params_fingerprint(a, bundle)
    manifest_path = os.path.join(out, "manifest.json")

    # ---- reuse or rebuild ---------------------------------------------------
    if os.path.isdir(out):
        marker = None
        if os.path.isfile(manifest_path):
            try:
                marker = json.load(open(manifest_path, encoding="utf-8"))
            except Exception:
                marker = None
        if not (marker and marker.get("generator") == GENERATOR):
            sys.stderr.write("REFUSED: %s exists and does not carry this script's manifest.json marker; "
                             "delete it yourself if it is really disposable.\n" % out)
            sys.exit(2)
        if marker.get("paramsFingerprint") == fp and not a.force:
            c = marker["counts"]
            print("REUSED %s (same parameters, seed %d): %d third-party DBPFs, %d dirs, ours=%d theirs=%d uncovered=%d"
                  % (out, a.seed, c["thirdPartyDbpf"], c["dirs"], marker["icons"]["ours"],
                     marker["icons"]["theirs"], marker["icons"]["uncovered"]))
            return 0
        t = time.time()
        shutil.rmtree(lp(out))
        print("removed the previous tree (%.1fs)" % (time.time() - t))

    t0 = time.time()
    rows = parse_third_party_deps(a.src)
    needles = distinct_needles(rows)

    # ours: the bundle's own live dats, read with the same index reader
    ours_inst = set()
    for name in ("010-SC4UIScale", "zzz-SC4UIScale"):
        d = os.path.join(bundle, name)
        for f in os.listdir(d):
            if os.path.splitext(f)[1].lower() in DBPF_EXTS:
                s = read_icon_instances(os.path.join(d, f))
                if s:
                    ours_inst |= s
    ours_sorted = sorted(ours_inst)

    items, facts = build_plan(a, needles, ours_sorted)

    # ---- write --------------------------------------------------------------
    os.makedirs(lp(out), exist_ok=True)
    # The marker goes down FIRST: a run that dies half-way must leave a tree
    # this script is allowed to delete on the next attempt.
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(dict(generator=GENERATOR, incomplete=True, paramsFingerprint=None), f)
    made_dirs = set()
    now = 1_000_000_000 + a.seed          # deterministic DBPF header stamps
    png_cache = {}
    written = 0
    for idx, it in enumerate(items):
        full = lp(os.path.join(out, it["rel"]))
        d = os.path.dirname(full)
        if d not in made_dirs:
            os.makedirs(d, exist_ok=True)
            made_dirs.add(d)
        png0 = None
        if it["png"]:
            key = (a.seed * 7919 + idx) & 0xFFFF
            png0 = png_cache.get(key)
            if png0 is None:
                png0 = make_png_strip(key)
                png_cache[key] = png0
        recs = build_records(it["icons"], png0, it["targetSize"], it["filler"], idx)
        dbpf_pack(recs, full, now=now)
        written += 1
    bundle_files = copy_bundle(bundle, out)

    offline_rel = None
    if a.offline_file:
        offline_rel = next(it["rel"] for it in items if it["role"] == "bulk")
        p = lp(os.path.join(out, offline_rel))
        attrs = ctypes.windll.kernel32.GetFileAttributesW(p)
        if attrs == 0xFFFFFFFF or not ctypes.windll.kernel32.SetFileAttributesW(p, attrs | FILE_ATTRIBUTE_OFFLINE):
            raise SystemExit("SetFileAttributesW(OFFLINE) failed on %s" % offline_rel)

    junction_rel = None
    if a.junction:
        junction_rel = "Plugins"
        link = os.path.join(out, junction_rel)
        if not os.path.lexists(link):
            r = subprocess.run(["cmd", "/c", "mklink", "/J", link, out], capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit("mklink /J failed: %s %s" % (r.stdout, r.stderr))

    # ---- measure ------------------------------------------------------------
    st, ours, theirs, per_file, needle_facts, unreadable = survey(out, needles)
    if unreadable:
        raise SystemExit("unreadable DBPF(s) in the tree just written: %s" % unreadable[:5])
    if st["thirdPartyDbpf"] != a.files:
        raise SystemExit("plan/disk disagree: planned %d third-party DBPFs, measured %d"
                         % (a.files, st["thirdPartyDbpf"]))
    if ours != ours_inst:
        raise SystemExit("ours read back from the copied bundle differs from the bundle itself")
    uncovered = theirs - ours
    big_icons = set()
    if facts["bigIndexRel"]:
        big_icons = per_file[facts["bigIndexRel"]]
    long_only = set()
    for it in items:
        if it["role"] in ("longpath", "webbutton"):
            long_only |= per_file[it["rel"]]
    unc_sorted = sorted(uncovered)
    unc_ex_big = sorted(uncovered - big_icons)

    manifest = dict(
        generator=GENERATOR, generatorVersion=GEN_VERSION, seed=a.seed,
        params=params, paramsFingerprint=fp, root=out,
        bundle=bundle, bundleName=os.path.basename(os.path.dirname(bundle)),
        counts=dict(thirdPartyDbpf=st["thirdPartyDbpf"], oursDbpf=st["oursDbpf"],
                    bundleFilesCopied=bundle_files, totalFiles=st["files"], totalBytes=st["bytes"],
                    totalsExclude="manifest.json at the root (a walk of the tree sees one more file)",
                    dirs=st["dirs"], deepestDirDepth=st["deepest"], maxPathLen=st["maxPathLen"],
                    longPaths=dict(
                        prefixed260=st["longPrefixed"],
                        plain260=st["longPlain"],
                        note="prefixed260 = entries whose \\\\?\\-prefixed path exceeds 260 chars, which is "
                             "what IconSynth::Walk counts in gLongPathsSeen; plain260 = entries whose plain "
                             "path exceeds 260"),
                    longPathDirs=a.long_paths, fixtureFiles=facts["fixtureFiles"],
                    coveredFiles=facts["coveredFiles"]),
        icons=dict(ours=len(ours), theirs=len(theirs), covered=len(theirs & ours), uncovered=len(uncovered),
                   uncoveredSha1=sha1_list(unc_sorted),
                   uncoveredList=[("%08X" % i) for i in unc_sorted] if len(unc_sorted) <= 2000 else None,
                   uncoveredExBigIndex=len(unc_ex_big), uncoveredExBigIndexSha1=sha1_list(unc_ex_big),
                   bigIndex=(dict(rel=facts["bigIndexRel"], entries=BIG_INDEX_ENTRIES, icons=len(big_icons),
                                  iconsSha1=sha1_list(big_icons)) if facts["bigIndexRel"] else None),
                   longPathOnly=dict(files=len([1 for it in items if it["role"] in ("longpath", "webbutton")]),
                                     icons=len(long_only)),
                   listFormat="sorted, one %08X per line, LF, ASCII; sha1 over those bytes"),
        needles=needle_facts,
        thirdPartyDeps=rows,
        namNeedle=facts["namNeedle"], namRel=facts["namRel"], namDepth=a.nam_depth,
        webButtonNeedle=facts["webButtonNeedle"], webButtonPresent=facts["webButtonPresent"],
        webButtonRel=facts["webButtonRel"],
        webButtonPathLen=(len(os.path.join(out, facts["webButtonRel"])) if facts["webButtonRel"] else None),
        wrongSizeNeedle=facts["wrongSizeNeedle"], duplicateNeedle=facts["duplicateNeedle"],
        offlineFile=offline_rel, junction=junction_rel,
        orderingWarnFolders=facts["orderingWarnFolders"], orderingOkFolders=facts["orderingOkFolders"],
        seconds=round(time.time() - t0, 1),
    )
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)

    nf = needle_facts.values()
    print("synthetic Plugins %s: %d third-party DBPFs (+%d ours) in %d dirs, %d entries past MAX_PATH, "
          "ours=%d theirs=%d uncovered=%d, needles ok=%d changed=%d absent=%d, bigIndex=%s, %.1fs"
          % (out, st["thirdPartyDbpf"], st["oursDbpf"], st["dirs"], st["longPlain"], len(ours), len(theirs),
             len(uncovered), sum(1 for n in nf if n["verdictCorrectWalk"] == "ok"),
             sum(1 for n in nf if n["verdictCorrectWalk"] == "changed"),
             sum(1 for n in nf if n["verdictCorrectWalk"] == "absent"),
             "yes" if facts["bigIndexRel"] else "no", time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
