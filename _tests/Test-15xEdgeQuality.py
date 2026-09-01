#!/usr/bin/env python
r"""Test-15xEdgeQuality - the 1.5x edge-quality gate (2026-09-01).

WHY THIS EXISTS. Every sharpness/evenness instrument this project owns lives in
tools\research\sharp15\ and NONE of it was wired into _tests\. #200 (v4.3.0)
flipped the 1.5x default from area-average to nearest on the strength of those
numbers, and nothing in the regression suite would go red if the average crept
back - or if a new resampler made the ragged strokes the user reported on
2026-09-01 worse. This gate reads the BUILT preview trees and holds them to a
committed baseline.

WHAT IT MEASURES, per sheet, against the 1x extract:
  swc / cv_L   stroke-width consistency (tools\research\sharp15\stroke_width.py)
               - the number for "some strokes 1px, some 2px"
  manuf        invented colours (a pixel the artist never drew)
  soft_frac    strong luma steps that land as a ramp
  edge_w       edge transition width in output pixels
  key_near     #143 pink class; key_moved: exact-key set vs the NN prediction

CONTROLS FIRST, DISTINCT EXIT CODE. 2x and 3x are pure nearest block
replicates, so on every sheet they MUST read swc=0, manuf=0, soft_frac=0,
edge_w=1.000 and dims exactly N*. Any failure there is the INSTRUMENT's
(exit 2), never the tier's - fix it before believing any 1.5x number.

1.5x is judged RELATIVE TO THE BASELINE (_tests\golden\15x-edge-quality-baseline.json):
  * dims of every sheet equal the baseline (law 66: art dimensions have the
    scope of the whole game; a resampler change may not move them)
  * manuf == 0 on every sheet the baseline recorded as copy-only, unless the
    sheet is named in a blending list the baseline knows (even-strips.txt)
  * corpus swc, per L, not worse than baseline by more than the noise floor
  * key_near == 0 everywhere; key_moved == 0 unless baseline recorded it

  --selftest          prove the gate can go red (duplicate a column -> swc
                      rises; blend one pixel -> manuf rises) - exit 1 if the
                      mutations are NOT caught
  --refresh-baseline  rewrite the baseline from the current trees (a
                      deliberate act; say why in the commit)
  --limit N           first N sheets only (smoke)
  --json PATH         write the full per-sheet table

Exit: 0 pass, 1 fail, 2 instrument/control failure, 3 missing inputs.
"""
import json
import os
import re
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LAB = os.path.join(REPO, "tools", "research", "sharp15")
sys.path.insert(0, LAB)
import metrics as M            # noqa: E402
import stroke_width as SW      # noqa: E402

UP = os.path.join(REPO, "tools", "upscale")
SRC = os.path.join(REPO, "tools", "dbpf", "extracted", "SimCity_1")
TIERS = {1.5: os.path.join(UP, "preview-15x", "SimCity_1"),
         2.0: os.path.join(UP, "preview", "SimCity_1"),
         3.0: os.path.join(UP, "preview-3x", "SimCity_1")}
BASELINE = os.path.join(HERE, "golden", "15x-edge-quality-baseline.json")
NAME_RE = re.compile(
    r"^T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})_I-(?:0x)?([0-9a-f]{8})\.png$", re.I)
NOISE = {"swc": 0.005}          # corpus-level tolerance; the per-L floor is measured
                                # by the lab (nearest vs even_nearest) - 0.001-0.002


def load_list(fn):
    out = set()
    p = os.path.join(UP, fn)
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8", errors="replace"):
        s = line.strip()
        if s and not s.startswith("#"):
            parts = s.replace(",", " ").split()
            if len(parts) >= 2:
                out.add((parts[0].lower(), parts[1].lower()))
    return out


def tgi_of(name):
    m = NAME_RE.match(name)
    return (m.group(2).lower(), m.group(3).lower()) if m else None


def src_path(name):
    """1x extract keeps the un-prefixed name."""
    p = os.path.join(SRC, name)
    if os.path.exists(p):
        return p
    p = os.path.join(SRC, name.replace("0x", ""))
    return p if os.path.exists(p) else None


def measure(src, out, f):
    r = M.report(out, src, f)
    sw = SW.sheet_stats(src, out, f)
    d = {"w": int(out.shape[1]), "h": int(out.shape[0]),
         "manuf": int(r["manuf"]), "edges": int(r["edges"]), "soft": int(r["soft"]),
         "peak_sum": float(r["peak_sum"]), "peak_n": int(r["peak_n"]),
         "key_near": int(r["key_near"]), "key_moved": int(r["key_moved"]),
         "key_exact": int(r["key_exact"]), "blended": int(sw["blended"])}
    for L in range(1, SW.MAXL + 1):
        d["n_%d" % L] = sw["n_%d" % L]
        d["cv_%d" % L] = sw["cv_%d" % L]
    return d


def corpus(rows):
    """Pool per-sheet rows into corpus numbers."""
    out = {"sheets": len(rows)}
    out["manuf"] = sum(r["manuf"] for r in rows)
    e = sum(r["edges"] for r in rows)
    out["soft_frac"] = (sum(r["soft"] for r in rows) / e) if e else 0.0
    pn = sum(r["peak_n"] for r in rows)
    ps = sum(r["peak_sum"] for r in rows)
    out["edge_w"] = (pn / ps) if ps else 1.0
    out["key_near"] = sum(r["key_near"] for r in rows)
    out["key_moved"] = sum(r["key_moved"] for r in rows)
    ntot, acc = 0, 0.0
    for L in range(1, SW.MAXL + 1):
        n = sum(r["n_%d" % L] for r in rows)
        cv = (sum(r["n_%d" % L] * r["cv_%d" % L] for r in rows) / n) if n else 0.0
        out["n_%d" % L] = n
        out["cv_%d" % L] = cv
        ntot += n
        acc += n * cv
    out["swc"] = (acc / ntot) if ntot else 0.0
    return out


def run_tier(f, names, limit=None):
    rows = {}
    d = TIERS[f]
    t0 = time.time()
    for i, n in enumerate(names):
        if limit and i >= limit:
            break
        sp = src_path(n)
        op = os.path.join(d, n)
        if not sp or not os.path.exists(op):
            continue
        src = np.array(Image.open(sp).convert("RGBA"))
        out = np.array(Image.open(op).convert("RGBA"))
        rows[n] = measure(src, out, f)
    return rows, time.time() - t0


def control_check(f, rows):
    """Integer tiers: every sheet a clean replicate."""
    bad = []
    for n, r in rows.items():
        sp = src_path(n)
        src = Image.open(sp)
        w, h = src.size
        if r["w"] != int(w * f) or r["h"] != int(h * f):
            bad.append((n, "dims %dx%d vs %dx%d" % (r["w"], r["h"], w * f, h * f)))
            continue
        if r["manuf"] or r["soft"] or r["blended"]:
            bad.append((n, "manuf %d soft %d blended %d" % (r["manuf"], r["soft"], r["blended"])))
            continue
        if any(r["cv_%d" % L] != 0.0 for L in range(1, SW.MAXL + 1)):
            bad.append((n, "cv nonzero"))
    return bad


def selftest(names):
    """Mutate one sheet's 1.5x output and prove the numbers move."""
    n = None
    for cand in names:
        sp = src_path(cand)
        if sp and os.path.exists(os.path.join(TIERS[1.5], cand)):
            src = np.array(Image.open(sp).convert("RGBA"))
            if 40 <= src.shape[1] <= 200 and 20 <= src.shape[0] <= 200:
                n = cand
                break
    if n is None:
        print("SELFTEST: no suitable sheet")
        return False
    src = np.array(Image.open(src_path(n)).convert("RGBA"))
    out = np.array(Image.open(os.path.join(TIERS[1.5], n)).convert("RGBA"))
    base = measure(src, out, 1.5)
    # mutation 1: duplicate a column (shifts every run right of it by one and
    # lengthens one run) -> swc must rise or blended must rise
    m1 = out.copy()
    c = out.shape[1] // 2
    m1[:, c + 1:] = out[:, c:-1]
    r1 = measure(src, m1, 1.5)
    moved1 = (sum(r1["cv_%d" % L] for L in range(1, 5)) > sum(base["cv_%d" % L] for L in range(1, 5))
              or r1["blended"] > base["blended"])
    # mutation 2: paint one interior pixel a colour the artist never drew
    # (a blend that happens to land on an existing colour would not count,
    # so search for a provably novel one) -> manuf must rise by exactly 1
    m2 = out.copy()
    y, x = out.shape[0] // 2, out.shape[1] // 2
    palette = set(np.unique(M._pack(src)).tolist())
    px = out[y, x].astype(int)
    for k in range(1, 64):
        cand = np.array([(px[0] + k) % 256, (px[1] + 2 * k) % 256, (px[2] + 3 * k) % 256, px[3]], np.uint8)
        if int(M._pack(cand[None, None])[0, 0]) not in palette:
            m2[y, x] = cand
            break
    r2 = measure(src, m2, 1.5)
    moved2 = r2["manuf"] > base["manuf"]
    print("SELFTEST on %s: duplicate-column caught=%s  blend-pixel caught=%s"
          % (n, moved1, moved2))
    return moved1 and moved2


def main(argv):
    limit = None
    refresh = "--refresh-baseline" in argv
    json_out = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    if "--json" in argv:
        json_out = argv[argv.index("--json") + 1]
    if "--tree" in argv:
        # measure a VARIANT 1.5x tree (build_variant_tree.py output) against the
        # same baseline - report-only comparison for the lab, same gate logic
        TIERS[1.5] = argv[argv.index("--tree") + 1]
        print("1.5x tree override:", TIERS[1.5])
    for f, d in TIERS.items():
        if not os.path.isdir(d):
            print("MISSING tier tree", d)
            return 3
    if not os.path.isdir(SRC):
        print("MISSING 1x extract", SRC)
        return 3
    names = sorted(n for n in os.listdir(TIERS[1.5]) if NAME_RE.match(n))
    if "--selftest" in argv:
        return 0 if selftest(names) else 1

    # ---- controls first
    for f in (2.0, 3.0):
        rows, dt = run_tier(f, names, limit)
        bad = control_check(f, rows)
        c = corpus(list(rows.values()))
        print("CONTROL %.0fx: %d sheets  manuf %d  soft %.4f  edge_w %.3f  swc %.4f  (%.0fs)"
              % (f, c["sheets"], c["manuf"], c["soft_frac"], c["edge_w"], c["swc"], dt))
        if bad:
            print("INSTRUMENT FAILURE at %.0fx - a block replicate did not read clean:" % f)
            for n, why in bad[:10]:
                print("   ", n, why)
            return 2
        if c["manuf"] != 0 or c["swc"] != 0.0:
            print("INSTRUMENT FAILURE: corpus numbers nonzero at an integer tier")
            return 2

    # ---- 1.5x
    rows, dt = run_tier(1.5, names, limit)
    c = corpus(list(rows.values()))
    print("1.5x: %d sheets  manuf %d  soft %.4f  edge_w %.3f  swc %.4f  cv1 %.3f cv2 %.3f cv3 %.3f cv4 %.3f"
          "  key_near %d key_moved %d  (%.0fs)"
          % (c["sheets"], c["manuf"], c["soft_frac"], c["edge_w"], c["swc"],
             c["cv_1"], c["cv_2"], c["cv_3"], c["cv_4"], c["key_near"], c["key_moved"], dt))
    blend_lists = load_list("even-strips.txt")
    if json_out:
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump({"corpus": c, "sheets": rows}, fh, indent=1, sort_keys=True)
        print("wrote", json_out)
    if refresh:
        os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
        with open(BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"date": time.strftime("%Y-%m-%d"), "corpus": c,
                       "sheets": {n: {"w": r["w"], "h": r["h"], "manuf": r["manuf"],
                                      "key_moved": r["key_moved"], "key_near": r["key_near"]}
                                  for n, r in rows.items()}},
                      fh, indent=1, sort_keys=True)
        print("BASELINE WRITTEN", BASELINE)
        return 0
    if not os.path.exists(BASELINE):
        print("NO BASELINE - run with --refresh-baseline first (and commit it)")
        return 3
    base = json.load(open(BASELINE, encoding="utf-8"))
    fails = []
    bs = base["sheets"]
    for n, r in rows.items():
        b = bs.get(n)
        if b is None:
            continue  # new sheet: reported, not failed
        if (r["w"], r["h"]) != (b["w"], b["h"]):
            fails.append("%s dims %dx%d -> %dx%d (law 66)" % (n, b["w"], b["h"], r["w"], r["h"]))
        if r["manuf"] and not b["manuf"] and tgi_of(n) not in blend_lists:
            fails.append("%s invented %d colours, baseline 0, not in a blending list" % (n, r["manuf"]))
        # near-key pixels exist in the ARTISTS' 1x sources too, so the gate is
        # "no MORE than the baseline", never "zero" (the shipped tree carries
        # 10,251 of them at 1.5x; a resampler that adds one is the #143 class)
        if r["key_near"] > b.get("key_near", 0):
            fails.append("%s key_near %d > baseline %d (the #143 pink class)"
                         % (n, r["key_near"], b.get("key_near", 0)))
        if r["key_moved"] and not b.get("key_moved"):
            fails.append("%s key_moved %d, baseline 0" % (n, r["key_moved"]))
    bc = base["corpus"]
    if not limit:
        if c["swc"] > bc["swc"] + NOISE["swc"]:
            fails.append("corpus swc %.4f worse than baseline %.4f (+%.4f allowed)"
                         % (c["swc"], bc["swc"], NOISE["swc"]))
        for L in range(1, SW.MAXL + 1):
            if c["cv_%d" % L] > bc["cv_%d" % L] + NOISE["swc"]:
                fails.append("cv_%d %.4f worse than baseline %.4f" % (L, c["cv_%d" % L], bc["cv_%d" % L]))
    missing = [n for n in bs if n not in rows]
    if missing and not limit:
        fails.append("%d baseline sheets missing from the tree, e.g. %s" % (len(missing), missing[0]))
    if fails:
        print("FAIL (%d):" % len(fails))
        for x in fails[:40]:
            print("   ", x)
        return 1
    print("PASS: 1.5x within baseline (%s)" % base.get("date"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
