#!/usr/bin/env python3
r"""iconhunt stage 1 - EXHAUSTIVE index of every image resource.

Archives are DISCOVERED by sniffing the DBPF magic on EVERY file under both
trees (game install root + user Plugins).  Extension lists rot: this install
ships nine .dat plus SimCityLocale.DAT plus Intro.dat, and the Plugins tree
holds .sc4model/.sc4desc/.sc4lot and 22 ".x1-disabled" files whose extension
no list would have carried.  Magic-sniffing cannot miss one.

Indexes T=0x7AB50E44 (FSH) and T=0x856DDBAC (PNG) in ALL groups, no exclusions.
Read-only on the game and on Documents.
"""
import os
import pickle
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
UD = os.path.dirname(HERE)
TOOLS = os.path.dirname(os.path.dirname(UD))
sys.path.insert(0, UD)
sys.path.insert(0, TOOLS)
from sc4paths import game_dir, plugins_dir            # noqa: E402
from census_markers import dbpf_index                 # noqa: E402

T_FSH = 0x7AB50E44
T_PNG = 0x856DDBAC
CACHE = os.path.join(HERE, "image-index.pkl")


def discover(root):
    """Every DBPF under root, found by MAGIC not by extension."""
    hits = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            p = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(p) < 96:
                    continue
                with open(p, "rb") as fh:
                    if fh.read(4) != b"DBPF":
                        continue
            except Exception:
                continue
            hits.append(p)
    return sorted(hits)


def build():
    roots = []
    g = game_dir()
    if g:
        roots.append(("GAME", g))
    p = plugins_dir(require=False)
    if p and os.path.isdir(p):
        roots.append(("PLUGINS", p))
    per_file = []
    entries = []          # (T,G,I,path,off,size)
    typecount = Counter()
    for label, root in roots:
        print("== root %s: %s" % (label, root))
        for path in discover(root):
            idx = dbpf_index(path)
            if not idx:
                print("   !! DBPF magic but unreadable index: %s" % path)
                per_file.append((label, path, 0, 0, 0))
                continue
            nf = np = 0
            for (t, gg, i, off, sz) in idx:
                typecount[t] += 1
                if t == T_FSH:
                    nf += 1
                    entries.append((t, gg, i, path, off, sz))
                elif t == T_PNG:
                    np += 1
                    entries.append((t, gg, i, path, off, sz))
            per_file.append((label, path, len(idx), nf, np))
    return {"entries": entries, "per_file": per_file, "types": typecount}


def main():
    d = build()
    with open(CACHE, "wb") as fh:
        pickle.dump(d, fh, 2)
    print()
    print("%-8s %6s %6s %6s  %s" % ("ROOT", "TOTAL", "FSH", "PNG", "ARCHIVE"))
    tf = tp = tt = 0
    for (label, path, n, nf, np) in sorted(d["per_file"], key=lambda r: -r[3] - r[4]):
        if nf or np:
            print("%-8s %6d %6d %6d  %s" % (label, n, nf, np, path))
        tf += nf
        tp += np
        tt += n
    silent = [r for r in d["per_file"] if not r[3] and not r[4]]
    print()
    print("archives with ZERO image resources: %d" % len(silent))
    print("archives discovered              : %d" % len(d["per_file"]))
    print("total DBPF entries               : %d" % tt)
    print("FSH resources (0x7AB50E44)       : %d" % tf)
    print("PNG resources (0x856DDBAC)       : %d" % tp)
    print("GRAND TOTAL image resources      : %d" % (tf + tp))
    print()
    print("top 12 resource types in the corpus (sanity - FSH/PNG must appear):")
    for t, c in d["types"].most_common(12):
        print("   0x%08X  %8d %s" % (t, c, "<-- FSH" if t == T_FSH else
                                     ("<-- PNG" if t == T_PNG else "")))


if __name__ == "__main__":
    main()
