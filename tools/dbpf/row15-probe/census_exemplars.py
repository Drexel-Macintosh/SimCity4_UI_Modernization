#!/usr/bin/env python3
r"""Census every exemplar/cohort in the install and dump one CSV row each.

Answers, from bytes and not from lore: what KIND of object the ConnectArrow
exemplar is, who else is that kind, and which exemplars carry the
0x8A416A99 UserVisibleNameKey whose consumer we are trying to find.

Writes only into this directory.  Read-only on the game install.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbpfcore as D                                          # noqa: E402

P_TYPE = 0x00000010
P_NAME = 0x00000020
P_UVNK = 0x8A416A99
P_OCCSIZE = 0x27812810
P_RKT1 = 0x27812821

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exemplar-census.csv")


def main():
    ltext = {}                       # instance -> (archive, group, text)
    for p in D.discover_archives():
        a = D.Archive(p)
        for e in a.by_type(D.T_LTEXT):
            try:
                buf, _q, _l = a.payload(e)
                ltext.setdefault((e[1], e[2]), []).append((a.name, D.ltext_text(buf)))
            except Exception as exc:
                ltext.setdefault((e[1], e[2]), []).append((a.name, "<%s>" % exc))
        a.close()

    rows = []
    bad = 0
    for p in D.discover_archives():
        a = D.Archive(p)
        for tid in (D.T_EXEMPLAR, D.T_COHORT):
            for e in a.by_type(tid):
                try:
                    buf, _q, _l = a.payload(e)
                    parent, pr = D.decode_exemplar(buf)
                except Exception as exc:
                    bad += 1
                    rows.append(dict(archive=a.name, type="%08X" % e[0],
                                     group="%08X" % e[1], inst="%08X" % e[2],
                                     exname="<undecodable: %s>" % exc,
                                     extype="", parent="", uvnk="",
                                     uvnk_text="", occsize="", rkt=""))
                    continue
                uvnk = pr.get(P_UVNK, (None, []))[1]
                uvnk_tgi = ""
                uvnk_text = ""
                if len(uvnk) == 3:
                    uvnk_tgi = "%08X_%08X_%08X" % tuple(uvnk)
                    hits = ltext.get((uvnk[1], uvnk[2]), [])
                    uvnk_text = " | ".join("%s:%s" % h for h in hits) or "<NO LTEXT>"
                rows.append(dict(
                    archive=a.name, type="%08X" % e[0], group="%08X" % e[1],
                    inst="%08X" % e[2],
                    exname=pr.get(P_NAME, ("", [""]))[1][0],
                    extype=pr.get(P_TYPE, ("", [""]))[1][0],
                    parent="%08X_%08X_%08X" % parent,
                    uvnk=uvnk_tgi, uvnk_text=uvnk_text,
                    occsize=";".join(str(v) for v in pr.get(P_OCCSIZE, ("", []))[1]),
                    rkt=";".join("%08X" % v for v in pr.get(P_RKT1, ("", []))[1]),
                ))
        a.close()

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("%d exemplar/cohort records, %d undecodable -> %s" % (len(rows), bad, OUT))
    print("%d LTEXT (group,instance) keys" % len(ltext))


if __name__ == "__main__":
    main()
