#!/usr/bin/env python3
r"""Property-id census over every exemplar/cohort: which ids appear on which
exemplar types.  Answers "what does a queryable thing carry that the
ConnectArrow prop does not", without guessing what any id MEANS."""
import collections
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbpfcore as D                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    by_pid = collections.defaultdict(collections.Counter)     # pid -> extype ct
    total = collections.Counter()
    for p in D.discover_archives():
        a = D.Archive(p)
        for tid in (D.T_EXEMPLAR, D.T_COHORT):
            for e in a.by_type(tid):
                buf, _q, _l = a.payload(e)
                _par, pr = D.decode_exemplar(buf)
                et = pr.get(0x10, ("", [""]))[1][0]
                total[et] += 1
                for pid in pr:
                    by_pid[pid][et] += 1
        a.close()
    out = os.path.join(HERE, "property-census.csv")
    extypes = [k for k, _ in total.most_common()]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["prop_id", "total"] + ["extype_%s" % e for e in extypes])
        for pid in sorted(by_pid):
            c = by_pid[pid]
            w.writerow(["0x%08X" % pid, sum(c.values())] +
                       [c.get(e, 0) for e in extypes])
    print("%d distinct property ids -> %s" % (len(by_pid), out))
    print("exemplars per extype:", total.most_common())


if __name__ == "__main__":
    main()
