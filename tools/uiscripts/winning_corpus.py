#!/usr/bin/env python3
r"""WINNING-CORPUS RESOLVER — which .UI script does the game ACTUALLY load?

THE PROBLEM THIS EXISTS FOR (task #79c, then twice more)
--------------------------------------------------------
Both dat builders analyse `tools\uiscripts\extracted\` — 330 scripts pulled
from the GAME ARCHIVES ONLY. A plugin that replaces a stock .UI script is
therefore invisible to them, and by the LOAD-ORDER LAW (root Plugins files load
BEFORE subfolders) a plugin in a subfolder BEATS our root package.

Consequences already measured:
  * the cyclone-boom save-warning mod owned both in-city quit/exit confirms for
    five days while our notes blamed the game (fixed v2.38.0);
  * CAM replaces NINE .UI scripts, two of which are in dialog-static's TARGETS
    (`ca8cbf0f`, `8aa9aa14`) — so we ship doubled copies of the WRONG SOURCE
    and those dialogs render CAM's 1x script today.

Every "exclusive to the N target scripts => safe to double 2x in place"
judgement is computed over a corpus that cannot see a plugin referrer.

WHAT THIS DOES
--------------
Resolves the winner per TGI in true load order, extracts every third-party
winner into `extracted-plugins\`, and REPORTS what changes. It is REPORT-ONLY:
it never edits a builder, never rebuilds a dat, and never touches a game or
plugin file. Writing the report is the whole job; acting on it is a separate,
reviewed step (the entry counts in Test-DatIntegrity.ps1 move when it is).

    python winning_corpus.py              # report to stdout + WINNING-CORPUS.md
    python winning_corpus.py --no-extract # report only, skip extraction

Read-only with respect to the game and to Plugins.
"""

import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
PROJ = os.path.dirname(TOOLS)
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
import sys as _sys
_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS not in _sys.path:
    _sys.path.insert(0, _TOOLS)
from sc4paths import plugins_dir     # noqa: E402
# Resolved, not hard-coded: $SC4_PLUGINS, else the shell's Documents,
# else the OneDrive-redirected or plain %USERPROFILE% variant. See
# tools/sc4paths.py for why a literal path here was a bug, not a shortcut.
PLUG = plugins_dir(require=True)
EXTRACTOR = os.path.join(TOOLS, "dbpf", "DbpfExtract.exe")
OUT_DIR = os.path.join(HERE, "extracted-plugins")
STOCK_DIR = os.path.join(HERE, "extracted")
REPORT = os.path.join(HERE, "WINNING-CORPUS.md")

ARCHIVES = ["SimCity_1.dat", "SimCity_2.dat", "SimCity_3.dat", "SimCity_4.dat",
            "SimCity_5.dat", "EP1.dat", "SimCityLocale.DAT"]
PLUGIN_EXTS = (".dat", ".sc4lot", ".sc4desc", ".sc4model")

# The two groups both dat builders scan (build_dialog_static.py UI_GROUPS).
# The other two .UI groups in the corpus are reported but not owned by them.
BUILDER_GROUPS = {0x96A006B0, 0x08000600}
ALL_UI_GROUPS = {0x96A006B0, 0x08000600, 0x8A5971C5, 0x4A87BFE8}
UI_TYPE = 0x00000000


def entries(path):
    """(type, group, instance, offset, size) from a DBPF 1.0 index."""
    with open(path, "rb") as f:
        hdr = f.read(96)
        if hdr[:4] != b"DBPF":
            return
        count, idx_off, idx_size = struct.unpack_from("<III", hdr, 0x24)
        if not count:
            return
        stride = idx_size // count
        f.seek(idx_off)
        blob = f.read(idx_size)
    for k in range(count):
        yield struct.unpack_from("<IIIII", blob, k * stride)


def load_order():
    """Every archive the game reads, in the order it reads them.

    THE LAW (proven, README.md / SCENARIOS.md / REGRESSION.md): game archives
    first, then Plugins ROOT files, then Plugins SUBFOLDERS alphabetically.
    Later wins. Getting this order wrong makes the whole report wrong, so it
    is expressed once, here.
    """
    order = []
    for name in ARCHIVES:
        p = os.path.join(GAME, name)
        if os.path.exists(p):
            order.append((p, name, "game"))
    roots, subs = [], []
    for entry in os.listdir(PLUG):
        p = os.path.join(PLUG, entry)
        if os.path.isfile(p) and entry.lower().endswith(PLUGIN_EXTS):
            roots.append((p, entry))
    for root, _dirs, files in os.walk(PLUG):
        if os.path.normcase(root) == os.path.normcase(PLUG):
            continue
        for fn in files:
            if fn.lower().endswith(PLUGIN_EXTS):
                p = os.path.join(root, fn)
                subs.append((p, os.path.relpath(p, PLUG)))
    for p, label in sorted(roots, key=lambda t: t[1].lower()):
        order.append((p, label, "plugin-root"))
    for p, label in sorted(subs, key=lambda t: t[1].lower()):
        order.append((p, label, "plugin-sub"))
    return order


def is_ours(label):
    return "SC4UIScale" in label


def main():
    do_extract = "--no-extract" not in sys.argv
    order = load_order()
    print("Archives in load order: %d" % len(order))

    holders = {}          # (group, inst) -> [(label, kind, path), ...] in order
    for path, label, kind in order:
        try:
            for t, g, i, _off, _sz in entries(path):
                if t == UI_TYPE and g in ALL_UI_GROUPS:
                    holders.setdefault((g, i), []).append((label, kind, path))
        except Exception as exc:
            print("  !! %s: %s" % (label, exc))

    # ---- classify winners ----
    third_party = {}      # (g,i) -> (label, path)
    ours_wins = 0
    stock_wins = 0
    for key, chain in holders.items():
        label, kind, path = chain[-1]
        if kind == "game":
            stock_wins += 1
        elif is_ours(label):
            ours_wins += 1
        else:
            third_party[key] = (label, path)

    print("\n.UI TGIs seen: %d" % len(holders))
    print("  won by the game archives : %d" % stock_wins)
    print("  won by OUR packages      : %d" % ours_wins)
    print("  won by a THIRD PARTY     : %d   <-- invisible to both builders"
          % len(third_party))

    # ---- which of those are TARGETS we build a doubled copy of? ----
    # IMPORT the builder's real TARGETS rather than regexing its source.
    # ⚠ A static scan UNDER-COUNTS: discover_query_family() auto-enrols ~117
    # query panels at import time, and four of those are CAM-owned. The first
    # version of this report regexed the file, said "2 conflicts", and the
    # builder's own assert then found 6. Two instruments disagreeing about the
    # same fact is the failure mode this whole exercise exists to remove - so
    # the report and the assert now read the SAME list from the SAME place.
    sys.path.insert(0, os.path.join(TOOLS, "dialog-static"))
    import build_dialog_static as BDS
    targets = {int(i, 16) for (i, _n) in BDS.TARGETS}
    print("Builder TARGETS (incl. auto-discovered query family): %d"
          % len(targets))

    conflicts = []
    for (g, i), (label, path) in sorted(third_party.items()):
        if g in BUILDER_GROUPS and i in targets:
            conflicts.append((g, i, label))

    print("\n*** %d TARGET script(s) are owned by a third party ***"
          % len(conflicts))
    for g, i, label in conflicts:
        print("    {%08x,%08x}  <- %s" % (g, i, label))

    # ---- extract the third-party winners so the builders can read them ----
    n_extracted = 0
    if do_extract and third_party:
        if not os.path.isdir(OUT_DIR):
            os.makedirs(OUT_DIR)
        for fn in os.listdir(OUT_DIR):
            if fn.endswith((".ui", ".csv")):
                os.remove(os.path.join(OUT_DIR, fn))
        by_dat = {}
        for key, (label, path) in third_party.items():
            by_dat.setdefault(path, []).append(key)
        tmp = os.path.join(OUT_DIR, "_tmp")
        for path, keys in by_dat.items():
            if os.path.isdir(tmp):
                for fn in os.listdir(tmp):
                    os.remove(os.path.join(tmp, fn))
            else:
                os.makedirs(tmp)
            r = subprocess.run([EXTRACTOR, path, tmp, "00000000"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                print("  !! extract failed: %s\n%s" % (path, r.stderr))
                continue
            for g, i in keys:
                src = os.path.join(tmp, "T-00000000_G-%08x_I-%08x.png" % (g, i))
                if not os.path.isfile(src):
                    continue
                dst = os.path.join(
                    OUT_DIR, "T-00000000_G-%08x_I-%08x.ui" % (g, i))
                with open(src, "rb") as a, open(dst, "wb") as b:
                    b.write(a.read())
                n_extracted += 1
        for fn in os.listdir(tmp):
            os.remove(os.path.join(tmp, fn))
        os.rmdir(tmp)
        print("\nExtracted %d third-party winner(s) -> %s"
              % (n_extracted, os.path.relpath(OUT_DIR, PROJ)))

    # ---- compare each conflicting TARGET against the stock copy we build from
    shape = []
    area_re = re.compile(rb"area=\((\d+),(\d+),(\d+),(\d+)\)")
    for g, i, label in conflicts:
        won = os.path.join(OUT_DIR, "T-00000000_G-%08x_I-%08x.ui" % (g, i))
        stock = os.path.join(STOCK_DIR,
                             "T-%08x_G-%08x_I-%08x.ui" % (UI_TYPE, g, i))
        if not (os.path.isfile(won) and os.path.isfile(stock)):
            continue
        mw = area_re.search(open(won, "rb").read())
        ms = area_re.search(open(stock, "rb").read())
        if not (mw and ms):
            continue
        w = tuple(int(x) for x in mw.groups())
        s = tuple(int(x) for x in ms.groups())
        shape.append((g, i, label, s, (s[2] - s[0], s[3] - s[1]),
                      w, (w[2] - w[0], w[3] - w[1])))

    lines = ["# WINNING CORPUS — who actually supplies each `.UI` script", "",
             "*Generated by `tools\\uiscripts\\winning_corpus.py`. REPORT ONLY:"
             " nothing here has been acted on.*", "",
             "The builders read `extracted\\` (game archives only). This"
             " resolves the real load-order winner per TGI.", "",
             "| bucket | count |", "|---|---|",
             "| `.UI` TGIs seen | %d |" % len(holders),
             "| won by the game archives | %d |" % stock_wins,
             "| won by OUR packages | %d |" % ours_wins,
             "| **won by a THIRD PARTY** | **%d** |" % len(third_party), "",
             "## Third-party winners", "",
             "| TGI | winner |", "|---|---|"]
    for (g, i), (label, _p) in sorted(third_party.items()):
        mark = "  ⚠ **IN TARGETS**" if (g in BUILDER_GROUPS and i in targets) else ""
        lines.append("| `{%08x,%08x}` | %s%s |" % (g, i, label, mark))
    lines += ["", "## TARGETS we build from the WRONG SOURCE", ""]
    if shape:
        lines += ["| TGI | stock `area=` (what we double) | winner `area=` |"
                  " stock w×h | winner w×h |", "|---|---|---|---|---|"]
        for g, i, label, s, sd, w, wd in shape:
            lines.append("| `{%08x,%08x}` | `%s` | `%s` | %dx%d | **%dx%d** |"
                         % (g, i, s, w, sd[0], sd[1], wd[0], wd[1]))
    else:
        lines.append("*(none, or shapes unreadable)*")
    lines += ["", "## What to do", "",
              "1. Build the affected dialogs from the **winner**, into",
              "   `zzz-SC4UIScale\\`, gated on their mod"
              " (`ScaleTier::kThirdPartyDeps`) exactly like `SaveWarningUI`.",
              "2. Add a build-time assert: **a TARGET's winning script must be"
              " the one the builder read.** That single check would have caught",
              "   task #79c and both CAM dialogs.",
              "3. Re-derive art referrers from winners, not from stock —"
              " exclusivity verdicts computed from a stock-only corpus are"
              " computed from fiction.", ""]
    with open(REPORT, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines) + "\n")
    print("\nWrote %s" % os.path.relpath(REPORT, PROJ))

    # ---- machine-readable artifact for the builders' assert ----
    # The builders read THIS rather than re-scanning 147 archives on every
    # build: fast, deterministic, and reviewable in the repo. Regenerate it
    # whenever the plugin set changes (adding/removing a mod).
    import json
    # ⚠ TWO DIFFERENT LISTS, AND USING THE WRONG ONE IS A REAL BUG.
    #
    #   third_party_HOLDERS - a non-ours plugin carries this TGI ANYWHERE in the
    #     load chain. This is the durable fact and what the builders must key
    #     on: "a mod we do not control supplies this script, so build from it".
    #   third_party_WINNERS - a non-ours plugin is currently LAST. Informational
    #     only, because the moment our override ships WE become the winner.
    #
    # Keying the builders on WINNERS was wrong and self-erasing: after shipping
    # SaveWarningUI its two scripts dropped out of `winners`, and the staleness
    # check duly advised retiring the entries that were doing the fixing.
    tp_holders = {}
    for key, chain in holders.items():
        tp = [lbl for (lbl, kind, _p) in chain
              if kind != "game" and not is_ours(lbl)]
        if tp:
            tp_holders[key] = tp[-1]
    art = {
        "_comment": "Generated by tools/uiscripts/winning_corpus.py. "
                    "third_party_holders = a mod we do not control supplies "
                    "this .UI TGI (use THIS in builders). third_party_winners "
                    "= it is also currently last (informational; ours winning "
                    "is the goal). REGENERATE after any plugin change.",
        "third_party_holders": [
            {"group": "0x%08x" % g, "instance": "0x%08x" % i, "supplier": lbl}
            for (g, i), lbl in sorted(tp_holders.items())],
        "third_party_winners": [
            {"group": "0x%08x" % g, "instance": "0x%08x" % i, "winner": label}
            for (g, i), (label, _p) in sorted(third_party.items())],
    }
    jpath = os.path.join(HERE, "winning-corpus.json")
    with open(jpath, "w", encoding="utf-8", newline="") as f:
        json.dump(art, f, indent=2)
        f.write("\n")
    print("Wrote %s" % os.path.relpath(jpath, PROJ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
