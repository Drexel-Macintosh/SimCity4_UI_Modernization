#!/usr/bin/env python3
r"""Search EVERY DBPF entry (decompressed) in the install + Plugins for a 32-bit
little-endian value.  Prints owning TGI + byte offset.  READ-ONLY.

    python find_ref.py 0xEC07FCBE [more...] [--types 0x6534284A]

POSITIVE CONTROL built in: also searches for 0x29F10000, the neighbour-connect
arrow exemplar instance, which MUST be found inside at least one exemplar
(its own) -- if the control is silent the scan is broken.
"""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
from census_markers import dbpf_index, qfs_decompress, discover_dbpf  # noqa
from sc4paths import plugins_dir, game_dir  # noqa

def entries(roots):
    for root in roots:
        for path in discover_dbpf(root):
            idx = dbpf_index(path)
            if not idx:
                continue
            try:
                blob = open(path, "rb").read()
            except Exception:
                continue
            for (t, g, i, off, sz) in idx:
                raw = blob[off:off + sz]
                if len(raw) > 9 and (raw[4:6] == b"\x10\xfb" or raw[0:2] == b"\x10\xfb"):
                    try:
                        raw = qfs_decompress(raw)
                    except Exception:
                        pass
                yield (path, t, g, i, raw)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    vals = [int(a, 0) & 0xFFFFFFFF for a in args] or []
    vals.append(0x29F10000)          # positive control
    pats = {v: struct.pack("<I", v) for v in vals}
    roots = [game_dir()]
    p = plugins_dir(require=False)
    if p and os.path.isdir(p):
        roots.append(p)
    counts = {v: 0 for v in vals}
    for (path, t, g, i, raw) in entries(roots):
        for v, pat in pats.items():
            k = raw.find(pat)
            while k >= 0:
                # skip self-reference in the index/own instance
                counts[v] += 1
                if counts[v] <= 40:
                    print("0x%08X in {T=0x%08X,G=0x%08X,I=0x%08X} @+0x%X  %s"
                          % (v, t, g, i, k, os.path.basename(path)))
                k = raw.find(pat, k + 1)
    print()
    for v in vals:
        tag = "  <-- POSITIVE CONTROL" if v == 0x29F10000 else ""
        print("0x%08X: %d hit(s)%s" % (v, counts[v], tag))

main()
