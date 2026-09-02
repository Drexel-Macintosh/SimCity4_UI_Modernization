r"""PARITY GATE: the C# hybrid (Upscale2x.exe --hybrid) == the Python reference.

The user judged the 1.5x hybrid on screen from packages built by the PYTHON
reference (tools\research\sharp15\x3_candidates.py thin_h, via
build_variant_tree.py) - an EARLIER state of it: two rule changes landed after
the second launch and were gate-verified, not launch-verified (REGRESSION.md
#203 records their measured scope). What ships is the C# port. The lab result
transfers to the shipped file only if the port is THE SAME FUNCTION as the
reference at the shipped commit - so this compares
every sheet of a C# output tree against the reference tree, pixel for pixel,
dimensions included. One mismatching pixel fails the gate.

    python gate_hybrid_parity.py <csharp_tree> <reference_tree>
    python gate_hybrid_parity.py --selftest            (proves it can fail)

Exit 0 = pixel parity (decoded RGBA) on every sheet; 1 = mismatch; 2 = inputs missing.
The reference tree keeps even-strips / no-smooth / thumbnails / fine-key
sheets as COPIES of the shipped tree, so on those sheets the comparison is the
tree under test against itself - it proves the DISPATCH left them to nearest /
supersample only if the reference was built from a tree the port had not yet
overwritten (review 2026-09-01: circular on a rerun; the hybrid sheets are the
evidence, the kept sheets are not).
"""
import os
import re
import sys

import numpy as np
from PIL import Image

NAME_RE = re.compile(
    r"^T-(?:0x)?([0-9a-f]{8})_G-(?:0x)?([0-9a-f]{8})_I-(?:0x)?([0-9a-f]{8})\.png$", re.I)


def canon(n):
    m = NAME_RE.match(n)
    return ("T-0x%s_G-0x%s_I-0x%s.png" % (m.group(1).lower(), m.group(2).lower(), m.group(3).lower())) if m else None


def load(p):
    return np.array(Image.open(p).convert("RGBA"))


def compare(cs_dir, ref_dir, limit=None):
    cs = {canon(n): n for n in os.listdir(cs_dir) if canon(n)}
    rf = {canon(n): n for n in os.listdir(ref_dir) if canon(n)}
    only_cs = sorted(set(cs) - set(rf))
    only_rf = sorted(set(rf) - set(cs))
    both = sorted(set(cs) & set(rf))
    if limit:
        both = both[:limit]
    bad = []
    dims = 0
    for i, k in enumerate(both):
        a = load(os.path.join(cs_dir, cs[k]))
        b = load(os.path.join(ref_dir, rf[k]))
        if a.shape != b.shape:
            dims += 1
            bad.append((k, "dims %dx%d vs %dx%d" % (a.shape[1], a.shape[0], b.shape[1], b.shape[0])))
            continue
        if not np.array_equal(a, b):
            d = np.any(a != b, axis=-1)
            ys, xs = np.nonzero(d)
            bad.append((k, "%d px differ, first (%d,%d) cs=%s ref=%s"
                        % (d.sum(), xs[0], ys[0], a[ys[0], xs[0]].tolist(), b[ys[0], xs[0]].tolist())))
    return both, only_cs, only_rf, bad, dims


def selftest():
    """Two identical arrays must pass, one flipped pixel must fail."""
    import tempfile
    d = tempfile.mkdtemp(prefix="parity-")
    a = np.zeros((8, 8, 4), np.uint8); a[..., 3] = 255
    os.makedirs(os.path.join(d, "cs")); os.makedirs(os.path.join(d, "ref"))
    n = "T-0x856ddbac_G-0x00000001_I-0x00000001.png"
    Image.fromarray(a, "RGBA").save(os.path.join(d, "cs", n))
    Image.fromarray(a, "RGBA").save(os.path.join(d, "ref", n))
    _, _, _, bad, _ = compare(os.path.join(d, "cs"), os.path.join(d, "ref"))
    ok1 = not bad
    b = a.copy(); b[3, 3, 0] = 1
    Image.fromarray(b, "RGBA").save(os.path.join(d, "cs", n))
    _, _, _, bad, _ = compare(os.path.join(d, "cs"), os.path.join(d, "ref"))
    ok2 = bool(bad)
    print("SELFTEST identical->pass %s, one-pixel->fail %s" % (ok1, ok2))
    return ok1 and ok2


def synthetic():
    """The corpus never exercises the per-STATE cell branch (every cell-strip
    sheet is refused by the even-strips rule) nor --hybrid bold. This builds a
    synthetic corpus that does - a 4-state strip and a 9-slice-shaped frame,
    both with strokes at every parity and a colour-keyed corner - runs the exe
    with --cell-strips / --nine-slice / --hybrid on it, runs the Python
    reference with the same cells, and demands pixel parity. Review 2026-09-01."""
    import subprocess, tempfile, shutil
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(here)), "tools", "research", "sharp15"))
    import x3_candidates as X
    exe = os.path.join(here, "Upscale2x.exe")
    if not os.path.exists(exe):
        print("no Upscale2x.exe")
        return False
    d = tempfile.mkdtemp(prefix="hybrid-syn-")
    src = os.path.join(d, "src"); os.makedirs(src)
    rng = np.random.RandomState(7)
    BG = np.array([40, 40, 48, 255], np.uint8); INK = np.array([230, 230, 220, 255], np.uint8)
    KEY = np.array([255, 0, 255, 0], np.uint8)          # key at alpha 0, as the 1x art has it
    # sheet 1: 4-state strip 84x21, each state a different stroke pattern
    a = np.empty((21, 84, 4), np.uint8); a[...] = BG
    for s in range(4):
        x0 = s * 21
        for k, w in enumerate((1, 2, 3, 1)):
            x = x0 + 2 + k * 5 + (s % 2)
            a[3:18, x:x + w] = INK
        a[8 + s:9 + s, x0 + 1:x0 + 20] = INK
        a[0:3, x0:x0 + 3] = KEY
    # sheet 2: 78x78 frame, 3x3 cells of 26, rounded-ish outline + key corners
    b = np.empty((78, 78, 4), np.uint8); b[...] = BG
    b[5:73, 5:7] = INK; b[5:73, 71:73] = INK; b[5:7, 5:73] = INK; b[71:73, 5:73] = INK
    for i in range(6):
        b[7 + i, 7 + (5 - i)] = INK; b[7 + (5 - i), 7 + i] = INK
    b[0:4, 0:4] = KEY; b[74:78, 74:78] = KEY
    b[30:31, 10:68] = INK; b[10:68, 40:41] = INK; b[50:52, 12:66] = INK
    n1 = "T-0x856ddbac_G-0x00000001_I-0x00000001.png"
    n2 = "T-0x856ddbac_G-0x00000001_I-0x00000002.png"
    Image.fromarray(a, "RGBA").save(os.path.join(src, n1))
    Image.fromarray(b, "RGBA").save(os.path.join(src, n2))
    cells = os.path.join(d, "cells.txt"); open(cells, "w").write("00000001 00000001 4\n")
    nine = os.path.join(d, "nine.txt"); open(nine, "w").write("00000001 00000002\n")
    ok = True
    for mode in ("thin", "bold"):
        out = os.path.join(d, "out-" + mode)
        r = subprocess.run([exe, src, out, "--factor", "1.5", "--normalize-names", "--cell-strips", cells,
                            "--nine-slice", nine, "--hybrid", mode], capture_output=True, text=True)
        if r.returncode != 0:
            print("exe failed:", r.stdout[-400:], r.stderr[-400:]); return False
        for name, arr, sx, sy in ((n1, a, 4, 0), (n2, b, 3, 3)):
            cs = load(os.path.join(out, name))
            oh, ow = cs.shape[:2]
            ref = X.CANDIDATES[mode + "_h"](arr, ow, oh, factor=1.5, states_x=sx, states_y=sy)
            eq = np.array_equal(cs, ref)
            print("  synthetic %-4s %s %dx%d -> %dx%d  parity %s" % (mode, name[-12:-4], arr.shape[1], arr.shape[0], ow, oh, eq))
            if not eq:
                dd = np.any(cs != ref, axis=-1); ys, xs = np.nonzero(dd)
                print("     %d px differ, first (%d,%d) cs=%s ref=%s" % (dd.sum(), xs[0], ys[0], cs[ys[0], xs[0]].tolist(), ref[ys[0], xs[0]].tolist()))
                ok = False
    shutil.rmtree(d, ignore_errors=True)
    print("SYNTHETIC per-cell / bold parity:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    if "--selftest" in argv:
        return 0 if selftest() else 1
    if "--synthetic" in argv:
        return 0 if synthetic() else 1
    if len(argv) < 2:
        print(__doc__)
        return 2
    cs_dir, ref_dir = argv[0], argv[1]
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    if not os.path.isdir(cs_dir) or not os.path.isdir(ref_dir):
        print("missing input dir")
        return 2
    both, only_cs, only_rf, bad, dims = compare(cs_dir, ref_dir, limit)
    print("gate_hybrid_parity: %d sheets compared, %d only in C#, %d only in reference"
          % (len(both), len(only_cs), len(only_rf)))
    for k, why in bad[:25]:
        print("  MISMATCH %s: %s" % (k, why))
    if len(bad) > 25:
        print("  ... %d more" % (len(bad) - 25))
    if bad or only_rf or (only_cs and not limit):
        print("FAIL - %d mismatching sheet(s) (%d by dimensions)" % (len(bad), dims))
        return 1
    print("PASS - pixel parity (decoded RGBA) on every sheet")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
