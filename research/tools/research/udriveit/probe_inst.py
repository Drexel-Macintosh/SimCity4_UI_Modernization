#!/usr/bin/env python3
r"""Dump one or more exemplars by INSTANCE id, from every DBPF that carries
them, in load order.  Verbatim property dump.

    python probe_inst.py 1E680000 29F10000
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from census_markers import (dbpf_index, read_entry, maybe_decompress,   # noqa: E402
                            parse_exemplar, discover_dbpf)
from sc4paths import plugins_dir, game_dir                              # noqa: E402
from run_census import PROP_NAMES, fmt_vals                             # noqa: E402


def main(argv):
    want = {int(a, 16) & 0xFFFFFFFF for a in argv}
    game = game_dir()
    plug = plugins_dir(require=False)
    roots = [("GAME", game)]
    if plug:
        roots.append(("PLUGINS", plug))
    nfiles = 0
    hits = 0
    for label, root in roots:
        for p in discover_dbpf(root):
            idx = dbpf_index(p)
            if not idx:
                continue
            nfiles += 1
            for (t, g, i, off, sz) in idx:
                if i not in want:
                    continue
                hits += 1
                print("=" * 92)
                print("{T=0x%08X, G=0x%08X, I=0x%08X}" % (t, g, i))
                print("  file : %s" % p)
                print("  entry: off=%d size=%d" % (off, sz))
                raw = read_entry(p, off, sz)
                payload, comp = maybe_decompress(raw)
                print("  sig  : %r  compressed=%s  payload=%d bytes"
                      % (payload[:8], comp, len(payload)))
                try:
                    parent, props, order = parse_exemplar(payload)
                except Exception as e:
                    print("  PARSE FAILED: %s" % e)
                    print("  head: %s" % payload[:64].hex())
                    continue
                print("  parent cohort: {0x%08X, 0x%08X, 0x%08X}" % parent)
                print("  %d properties:" % len(props))
                for pid in order:
                    tname, vals = props[pid]
                    print("    0x%08X %-28s %-8s %s"
                          % (pid, PROP_NAMES.get(pid, ""), tname,
                             fmt_vals(tname, vals)))
    print()
    print("scanned %d DBPF files; %d matching entries" % (nfiles, hits))


if __name__ == "__main__":
    main(sys.argv[1:])
