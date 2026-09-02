r"""PARITY GATE: the C# hybrid (Upscale2x.exe --hybrid) == the Python reference.

The user judged the 1.5x hybrid on screen from packages built by the PYTHON
reference (tools\research\sharp15\x3_candidates.py thin_h, via
build_variant_tree.py). What ships is the C# port. The lab result transfers
to the shipped file only if the port is THE SAME FUNCTION - so this compares
every sheet of a C# output tree against the reference tree, pixel for pixel,
dimensions included. One mismatching pixel fails the gate.

    python gate_hybrid_parity.py <csharp_tree> <reference_tree>
    python gate_hybrid_parity.py --selftest            (proves it can fail)

Exit 0 = byte parity on every sheet; 1 = mismatch; 2 = inputs missing.
The reference tree keeps even-strips / no-smooth / thumbnails / fine-key
sheets as the SHIPPED bytes, so on those the comparison is C# nearest (or
supersample) against itself - a free regression control for the dispatch.
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


def main(argv):
    if "--selftest" in argv:
        return 0 if selftest() else 1
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
    print("PASS - byte parity on every sheet")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
