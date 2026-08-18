#!/usr/bin/env python3
"""
PREDICTIVE DEFECT SWEEP helper (read-only analysis, writes only into pds-cache).

Question it answers: which .UI ROOTS have their GEOMETRY doubled by the runtime
sweep while their ART stays 1x?  That is failure mode C ("left 1x inside a
doubled frame") and it is the single most repeated bug class in this project
(budget backgrounds, advisor briefing, Data Views, U-Drive-It dashboard, the
four mayor flyouts, the news reader -- every one cured by adding the root to
build_selective_safe.SCALED_WINDOW_IDS).

Method: import the SHIPPING builder so the .UI parser and the SCALED_WINDOW_IDS
gate are byte-identical to what actually ships (no parser drift), then classify
every root.
"""
import os
import sys
import re
import json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools", "selective-safe"))

import build_selective_safe as B  # noqa: E402

UI_DIR = os.path.join(PROJ, "tools", "uiscripts", "extracted")


def dialog_static_instances():
    """Instance ids (hex str) that build_dialog_static.py statically doubles.

    Includes discover_query_family(): the builder ADOPTS every 96a006b0 script
    containing both id=0x10000005 and clsid=0x89e1567c. Modelling the literal
    TARGETS list alone under-counts by ~70 query scripts and produces a false
    positive on root 0x10000005.
    """
    src = open(os.path.join(PROJ, "tools", "dialog-static",
                            "build_dialog_static.py"), encoding="utf-8").read()
    body = src[src.index("TARGETS = ["):src.index("TARGETS += discover_query_family()")]
    inst = {m.lower() for m in re.findall(r'\(\s*"([0-9a-fA-F]{8})"\s*,', body)}
    for fn in os.listdir(UI_DIR):
        if not (fn.startswith("T-00000000_G-96a006b0_I-") and fn.endswith(".ui")):
            continue
        text = open(os.path.join(UI_DIR, fn), encoding="latin-1").read()
        if "id=0x10000005" in text and "clsid=0x89e1567c" in text:
            inst.add(fn[len("T-00000000_G-96a006b0_I-"):-len(".ui")].lower())
    return inst


def uispike_id_list(name):
    """Pull an id list out of UiSpike.cpp by name (comment-stripped)."""
    src = open(os.path.join(PROJ, "src", "UiSpike.cpp"), encoding="utf-8",
               errors="replace").read()
    i = src.index(name + "[] = {")
    j = src.index("};", i)
    body = re.sub(r"//[^\n]*", "", src[i:j])
    return {int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{8})", body)}


def main():
    static_inst = dialog_static_instances()
    never = uispike_id_list("kNeverScaleIds")
    godflyout = uispike_id_list("kGodToolFlyoutIds")

    ui_files = []
    for g in B.UI_GROUPS:
        ui_files += sorted(fn for fn in os.listdir(UI_DIR)
                           if fn.startswith("T-00000000_G-%s_I-" % g)
                           and fn.endswith(".ui"))

    # ---- pass 1: parse everything, build the ref map exactly like the builder
    parsed = {}
    refs = defaultdict(lambda: {"scaled": set(), "unscaled": set()})
    for fn in ui_files:
        text = open(os.path.join(UI_DIR, fn), encoding="latin-1", newline="").read()
        roots = B.parse_ui(text)
        B.mark_scaled(roots)
        parsed[fn] = roots
        for nd in B.walk(roots):
            for (gid, iid, _, _) in nd.images:
                (refs[(gid, iid)]["scaled"] if nd.scaled
                 else refs[(gid, iid)]["unscaled"]).add(fn)

    # art that ships 2x IN PLACE or as a retargeted clone == referenced by >=1
    # scaled file.  Art referenced only by unscaled files stays 1x on disk.
    ships_2x = {t for t, r in refs.items() if r["scaled"]}

    # ---- pass 2: classify each ROOT
    rows = []
    for fn in ui_files:
        inst = fn.split("_I-")[1][:-3].lower()
        for root in parsed[fn]:
            if root.wid is None:
                continue
            art = [(g, i) for nd in B.walk([root]) for (g, i, _, _) in nd.images]
            art_u = sorted(set(art))
            n_1x = sum(1 for t in art_u if t not in ships_2x)
            a = root.imagerect  # roots rarely have one; kept for completeness
            rows.append({
                "file": fn, "inst": inst, "id": root.wid,
                "area": None if a is None else a[0],
                "in_S": root.wid in B.SCALED_WINDOW_IDS,
                "static": inst in static_inst,
                "never": root.wid in never,
                "godflyout": root.wid in godflyout,
                "art_total": len(art_u), "art_1x": n_1x,
                "art_1x_list": ["%08x/%08x" % t for t in art_u if t not in ships_2x][:12],
            })

    out = os.path.join(HERE, "art-coverage.json")
    json.dump(rows, open(out, "w", encoding="utf-8"), indent=1)

    # ---- the report: roots whose art is NOT doubled and which nothing else covers
    print("roots parsed: %d   distinct art refs: %d   ships-2x: %d"
          % (len(rows), len(refs), len(ships_2x)))
    print()
    cand = [r for r in rows
            if not r["in_S"] and not r["static"] and not r["never"]
            and not r["godflyout"] and r["art_1x"] > 0]
    # collapse by root id: the same root id appears in stale/duplicate scripts
    byid = defaultdict(list)
    for r in cand:
        byid[r["id"]].append(r)
    print("ROOT IDS WITH 1x ART AND NO STATIC/NEVER/GODFLYOUT COVER: %d" % len(byid))
    print("(geometry doubled by the sweep -> 1x art inside a 2x frame, IF swept)")
    print("=" * 78)
    for wid, rs in sorted(byid.items(), key=lambda kv: -max(x["art_1x"] for x in kv[1])):
        n = max(x["art_1x"] for x in rs)
        tot = max(x["art_total"] for x in rs)
        insts = ",".join(sorted({x["inst"] for x in rs}))
        print("0x%08X  1x-art %3d/%-3d  scripts: %s" % (wid, n, tot, insts))
        print("            %s" % " ".join(rs[0]["art_1x_list"]))

    # ---- REVERSE CHECK: the Establish-City 4x trap.
    # A script that dialog-static doubles ships a 2x .UI.  If that root is ALSO
    # reachable by the runtime sweep, both act and it renders ~4x.  The standing
    # rule (UiSpike.cpp kNeverScaleIds comment): "Anything the static dat serves
    # that lives in the swept tree MUST be listed here."  So every static root
    # NOT in kNeverScaleIds is an unfired landmine -- harmless only for as long
    # as it stays main-window-parented.
    print()
    print("=" * 78)
    static_roots = defaultdict(set)
    for r in rows:
        if r["static"]:
            static_roots[r["id"]].add(r["inst"])
    unins = {w: i for w, i in static_roots.items() if w not in never}
    print("STATIC-DOUBLED ROOTS *NOT* INSURED BY kNeverScaleIds: %d of %d"
          % (len(unins), len(static_roots)))
    for wid, insts in sorted(unins.items()):
        print("  0x%08X   %s" % (wid, ",".join(sorted(insts))[:110]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
