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
  tiled.txt              wrap padding - consumed only by the Scale3x candidates;
                         a no-op for thin_h/bold_h (they never look past a block)
  even-strips.txt        KEPT AS SHIPPED (the tick-ladder even reduce; round 1)
  no-smooth.txt          KEPT AS SHIPPED (a builder measures their pixel edges)
  keyed, MinKeyRun < 3   KEPT AS SHIPPED (the fine-key refusal, Upscale2x.cs:1396)
                         - or LIFTED with --hybrid-finekey (2026-09-07, Beta 1
                         A4): those sheets take the candidate too. Counted as
                         finekey_lifted; finekey reads 0 under the option.
                         A lifted sheet's exact-key set is then held to the
                         SHIPPED NEAREST'S SHEET MAP (gate_key_integrity R2's
                         model: BuildSampleMap with cell-strips states, whole
                         sheet). The candidate's own key mask is per CELL, and
                         on a 129x129 nine-slice sheet (43 -> 65 per cell,
                         non-integral 1.5x) the per-cell factor map lands one
                         source column off the sheet map every third column of
                         the 2nd/3rd cells - 12 lifted sheets ({1abe787d,
                         46a006b0} x 1441622x) lost 61 key px each to R2 on the
                         first build. Where the two maps disagree the pixel is
                         the shipped one (nearest's, verbatim); counted per
                         sheet as key_set_px_reverted. The C# lift needs the
                         same rule or a refusal for that cell shape.
  redraw_ladder LADDERS  KEPT AS SHIPPED, always (read from redraw_ladder.py's
                         list, never restated): their shipped bytes are the
                         #180 re-lay, which Rebuild-Corpus.ps1 runs AFTER the
                         exe and which would overwrite a lifted C# output just
                         the same. Both ladders are fine-key sheets, so the
                         round-1 manifest counted them under finekey (377 =
                         375 + 2); they are counted as `ladder` now.
  thumbnails.txt         KEPT AS SHIPPED (item-icon bindings: a rendered picture
                         wants hard pixels - the user's round-1 verdict, 2026-09-01)
Everything else takes the candidate. A manifest of what took what is written
beside the tree.

    python build_variant_tree.py thin_h [--out DIR] [--limit N] [--keyed]
                                        [--hybrid-finekey]

--hybrid-finekey implies --keyed (a lifted fine key beside a skipped broad key
models no dispatch that exists) and defaults the tree to preview-15x-<cand>_fk
so build_variant_packages.ps1 -Variant <cand>_fk finds it. Kept sheets are BYTE
copies of the shipped file (the round-1 form re-encoded them through PIL: same
pixels, different container bytes - a byte diff against the shipped tree now
lists exactly the sheets that took the candidate).

Offline. Reads the 1x extract and the shipped preview-15x; writes only the
variant tree (gitignored: game-derived art).
"""
import ast
import json
import os
import re
import shutil
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


def load_ladders():
    """redraw_ladder.py's LADDERS as {(group, instance)} - PARSED from the file
    (it runs sys.exit(main()) at module level, so importing it would redraw),
    the same idiom as gate_key_integrity.load_ladders."""
    path = os.path.join(UP, "redraw_ladder.py")
    with open(path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "LADDERS":
                    return set(map(tuple, ast.literal_eval(node.value)))
    raise SystemExit("LADDERS not found in %s - refusing to guess" % path)


def key_mask(a):
    return (a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255)


def sample_map(src, out, factor, states=0):
    """Mirror of Upscale2x.cs BuildSampleMap (X axis; states=0 is the Y-axis
    rule from UpscaleNearest) - the same mirror gate_key_integrity.sample_map
    keeps (not imported: that module runs main() at import)."""
    if states > 1 and src % states == 0 and out % states == 0:
        bs, bo = src // states, out // states
        m = np.empty(out, dtype=np.int64)
        for b in range(states):
            blk = b * bs + (np.arange(bo, dtype=np.int64) * bs) // bo
            np.minimum(blk, (b + 1) * bs - 1, out=blk)
            m[b * bo:(b + 1) * bo] = blk
        return m
    o = np.arange(out, dtype=np.int64)
    if out >= int(np.floor(src * factor)):
        m = (o / factor).astype(np.int64)
    else:
        m = (o * src) // out
    return np.minimum(m, src - 1)


def min_key_run(a):
    key = key_mask(a)
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
    lift = "--hybrid-finekey" in argv
    out_dir = os.path.join(UP, "preview-15x-" + cand + ("_fk" if lift else ""), "SimCity_1")
    limit = None
    keyed_ok = ("--keyed" in argv) or lift
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
    thumbs = load_list("thumbnails.txt")
    ladders = load_ladders()
    names = sorted(n for n in os.listdir(SHIPPED) if NAME_RE.match(n))
    manifest = {"candidate": cand, "date": time.strftime("%Y-%m-%d %H:%M"),
                "options": {"keyed": keyed_ok, "hybrid_finekey": lift},
                "kept_shipped": {}, "took": {}, "counts": {}}
    counts = {"cand": 0, "even": 0, "nosmooth": 0, "thumb": 0, "ladder": 0, "finekey": 0,
              "finekey_lifted": 0, "keyed_skipped": 0, "missing_src": 0,
              "cells": 0, "nine": 0, "tiled": 0,
              "key_set_px_reverted": 0, "key_set_sheets_reverted": 0, "key_set_not_nearest": 0}
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
            shutil.copyfile(os.path.join(SHIPPED, n), dst)   # bytes, not a re-encode
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
        if tgi in thumbs:
            keep("thumb")
            continue
        if tgi in ladders:
            keep("ladder")
            continue
        a = np.array(Image.open(sp).convert("RGBA"))
        mkr = min_key_run(a)
        lifted = False
        if mkr is not None:
            if mkr < 3:
                if not lift:
                    keep("finekey")
                    continue
                lifted = True
            elif not keyed_ok:
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
        reverted, key_ok = 0, True
        if lifted:
            # the exact-key set is the SHIPPED nearest's, on the SHEET map (see
            # the docstring): where the candidate's per-cell mask disagrees the
            # pixel is the shipped one - nearest's, verbatim
            pred = key_mask(a)[sample_map(a.shape[0], oh, 1.5, 0)][:, sample_map(a.shape[1], ow, 1.5, strips.get(tgi, 0))]
            fix = pred ^ key_mask(o)
            reverted = int(fix.sum())
            if reverted:
                o = o.copy()
                o[fix] = np.array(shipped.convert("RGBA"))[fix]
            key_ok = bool(np.array_equal(key_mask(o), pred))
        Image.fromarray(o, "RGBA").save(dst)
        manifest["took"][n] = {"states_x": states_x, "states_y": states_y, "wrap": wrap,
                               "finekey_lifted": lifted, "min_key_run": mkr,
                               "key_set_px_reverted": reverted, "key_set_is_shipped_nearest": key_ok}
        counts["cand"] += 1
        if lifted:
            counts["finekey_lifted"] += 1
            counts["key_set_px_reverted"] += reverted
            counts["key_set_sheets_reverted"] += int(reverted > 0)
            counts["key_set_not_nearest"] += int(not key_ok)
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
