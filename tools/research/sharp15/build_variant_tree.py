r"""BUILD A 1.5x PREVIEW-TREE VARIANT FROM A LAB CANDIDATE - for the in-game A/B.

The DAT builders consume PNG trees (tools\upscale\preview-15x\SimCity_1). A
variant tree with the same file names and the SAME DIMENSIONS as the shipped
tree drops straight into them via --upscale-dir, so a candidate can be judged
on the real screen without porting it to Upscale2x.cs first. The port happens
once, for the winner, with a parity gate (plan Phase 3).

Dimensions are PINNED to the shipped 1.5x sheet (law 66: art dimensions have
the scope of the whole game). Only pixel content changes.

The derived lists are honoured exactly as Rebuild-Corpus.ps1 would:
  cell-strips.txt        per-STATE processing (a cell never sees its neighbour)
  nine-slice.txt         3x3 cells (corner/edge/centre never bleed)
  tiled.txt              wrap padding (seam continuity across the wrap edge)
  even-strips.txt        KEPT AS SHIPPED (the tick-ladder even reduce; round 1)
  no-smooth.txt          KEPT AS SHIPPED (a builder measures their pixel edges)
  keyed, MinKeyRun < 3   KEPT AS SHIPPED (the fine-key refusal, Upscale2x.cs:1396)
Everything else takes the candidate. A manifest of what took what is written
beside the tree.

    python build_variant_tree.py thin_h [--out DIR] [--limit N] [--keyed]

Offline. Reads the 1x extract and the shipped preview-15x; writes only the
variant tree (gitignored: game-derived art).
"""
import json
import os
import re
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
UP = os.path.join(REPO, "tools", "upscale")
SRC = os.path.join(REPO, "tools", "dbpf", "extracted", "SimCity_1")
SHIPPED = os.path.join(UP, "preview-15x", "SimCity_1")
NAME_RE = re.compile(
    r"^T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})_I-(?:0x)?([0-9a-f]{8})\.png$", re.I)

sys.path.insert(0, HERE)
import x3_candidates as X          # noqa: E402


def load_list(fn):
    """(group, instance) pairs from a derived list under tools/upscale."""
    out = set()
    p = os.path.join(UP, fn)
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8", errors="replace"):
        s = line.strip()
        if s and not s.startswith("#"):
            parts = s.replace(",", " ").split()
            if len(parts) >= 2:
                try:
                    out.add((int(parts[0], 16), int(parts[1], 16)))
                except ValueError:
                    pass
    return out


def load_states(fn):
    out = {}
    p = os.path.join(UP, fn)
    for line in open(p, encoding="utf-8", errors="replace"):
        s = line.strip()
        if s and not s.startswith("#"):
            parts = s.replace(",", " ").split()
            if len(parts) >= 3:
                try:
                    out[(int(parts[0], 16), int(parts[1], 16))] = int(parts[2])
                except ValueError:
                    pass
    return out


def min_key_run(a):
    key = (a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255)
    if not key.any():
        return None
    best = 10 ** 9
    for row in key:
        idx = np.flatnonzero(np.diff(np.concatenate([[0], row.astype(np.int8), [0]])))
        for s, e in zip(idx[::2], idx[1::2]):
            best = min(best, int(e - s))
    return best


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cand = argv[0]
    fn = X.CANDIDATES[cand]
    out_dir = os.path.join(UP, "preview-15x-" + cand, "SimCity_1")
    limit = None
    keyed_ok = "--keyed" in argv
    if "--out" in argv:
        out_dir = argv[argv.index("--out") + 1]
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    os.makedirs(out_dir, exist_ok=True)
    strips = load_states("cell-strips.txt")
    nine = load_list("nine-slice.txt")
    tiled = load_list("tiled.txt")
    even = load_list("even-strips.txt")
    nosmooth = load_list("no-smooth.txt")
    names = sorted(n for n in os.listdir(SHIPPED) if NAME_RE.match(n))
    manifest = {"candidate": cand, "date": time.strftime("%Y-%m-%d %H:%M"),
                "kept_shipped": {}, "took": {}, "counts": {}}
    counts = {"cand": 0, "even": 0, "nosmooth": 0, "finekey": 0, "keyed_skipped": 0,
              "missing_src": 0, "cells": 0, "nine": 0, "tiled": 0}
    t0 = time.time()
    for i, n in enumerate(names):
        if limit and i >= limit:
            break
        m = NAME_RE.match(n)
        tgi = (int(m.group(2), 16), int(m.group(3), 16))
        sp = os.path.join(SRC, n.replace("0x", ""))
        if not os.path.exists(sp):
            sp = os.path.join(SRC, n)
        shipped = Image.open(os.path.join(SHIPPED, n))
        ow, oh = shipped.size
        dst = os.path.join(out_dir, n)

        def keep(reason):
            shipped.save(dst)
            manifest["kept_shipped"][n] = reason
            counts[reason] += 1
        if not os.path.exists(sp):
            keep("missing_src")
            continue
        if tgi in even:
            keep("even")
            continue
        if tgi in nosmooth:
            keep("nosmooth")
            continue
        a = np.array(Image.open(sp).convert("RGBA"))
        mkr = min_key_run(a)
        if mkr is not None:
            if mkr < 3:
                keep("finekey")
                continue
            if not keyed_ok:
                keep("keyed_skipped")
                continue
        states_x = strips.get(tgi, 0)
        states_y = 0
        wrap = tgi in tiled
        if tgi in nine:
            states_x, states_y = 3, 3
            counts["nine"] += 1
        elif states_x > 1:
            counts["cells"] += 1
        if wrap:
            counts["tiled"] += 1
        o = fn(a, ow, oh, factor=1.5, states_x=states_x, states_y=states_y, wrap=wrap)
        assert o.shape[1] == ow and o.shape[0] == oh
        Image.fromarray(o, "RGBA").save(dst)
        manifest["took"][n] = {"states_x": states_x, "states_y": states_y, "wrap": wrap}
        counts["cand"] += 1
        if (i + 1) % 200 == 0:
            print("  %d/%d  %.0fs" % (i + 1, len(names), time.time() - t0), flush=True)
    manifest["counts"] = counts
    with open(os.path.join(os.path.dirname(out_dir), "VARIANT-MANIFEST.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print("variant %s -> %s" % (cand, out_dir))
    print("counts:", counts, " %.0fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
