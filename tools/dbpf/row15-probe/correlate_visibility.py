#!/usr/bin/env python3
r"""Does an exemplar that carries 0x8A416A99 also carry the properties that
give it a place on screen?

MENU family : 0x8A2602B8, 0x8A2602B9, 0x8A2602BB, 0xCA416AB5  (item icon /
              order / button id / button class -- the things that put an
              exemplar in a tool menu with a name and a tip)
QUERY       : 0x2A499F85  (query exemplar GUID -- the thing that opens a
              query dialog for an occupant)

The point of the table is NOT that these ids "mean" those names; it is that
the exemplar kinds whose UVNK strings can be NAMED on screen carry them and
the ConnectArrow's kind carries neither.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbpfcore as D                                          # noqa: E402

MENU = {0x8A2602B8, 0x8A2602B9, 0x8A2602BB, 0xCA416AB5}
QUERY = {0x2A499F85}
UVNK = 0x8A416A99


def main():
    tab = collections.defaultdict(lambda: [0, 0, 0, 0])   # ex, uvnk, menu, query
    for p in D.discover_archives():
        a = D.Archive(p)
        for tid in (D.T_EXEMPLAR, D.T_COHORT):
            for e in a.by_type(tid):
                buf, _q, _l = a.payload(e)
                _par, pr = D.decode_exemplar(buf)
                et = pr.get(0x10, ("", ["(none)"]))[1][0]
                row = tab[et]
                row[0] += 1
                if UVNK in pr:
                    row[1] += 1
                    if MENU & set(pr):
                        row[2] += 1
                    if QUERY & set(pr):
                        row[3] += 1
        a.close()
    print("%-10s %8s %8s %10s %10s" % ("extype", "n", "hasUVNK",
                                       "UVNK+menu", "UVNK+query"))
    for et, row in sorted(tab.items(), key=lambda kv: -kv[1][1]):
        if not row[1]:
            continue
        print("%-10s %8d %8d %10d %10d" % (et, row[0], row[1], row[2], row[3]))
    print()
    print("extype 30 is the ConnectArrow's kind (its 0x00000010 reads 30).")


if __name__ == "__main__":
    main()
