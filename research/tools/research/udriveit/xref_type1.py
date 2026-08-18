#!/usr/bin/env python3
r"""Cross-reference: type-1 decal entry index -> the parent effect(s) whose
type=1 children carry that effectIndex, from effdir-dump.txt.
Writes type1-xref.txt and prints the entries asked about on the command line.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = os.path.join(HERE, "effdir-dump.txt")

PAR = re.compile(r"^\[\s*(\d+) @file:0x([0-9a-f]+)\] (\S+)\s+\(")
CHI = re.compile(r"^    child '([^']*)'\s+type=(\d+).*effectIndex=0x[0-9a-f]+\((\d+)\)")


def build():
    xref = {}
    cur = None
    for line in open(DUMP, encoding="utf-8"):
        m = PAR.match(line)
        if m:
            cur = (int(m.group(1)), m.group(3))
            continue
        m = CHI.match(line)
        if m and int(m.group(2)) == 1 and cur:
            xref.setdefault(int(m.group(3)), []).append((cur[0], cur[1], m.group(1)))
    return xref


def main():
    x = build()
    with open(os.path.join(HERE, "type1-xref.txt"), "w", encoding="utf-8") as fh:
        fh.write("type-1 decal entry -> parent effect(s) referencing it "
                 "(type=1 children only)\n\n")
        for k in sorted(x):
            fh.write("entry %3d  <- %s\n" % (k, "; ".join(
                "[%d]%s/'%s'" % (p, n, c) for p, n, c in x[k])))
    print("total distinct referenced entries: %d" % len(x))
    for a in sys.argv[1:]:
        k = int(a)
        print("entry %3d <- %s" % (k, "; ".join(
            "[%d]%s/'%s'" % (p, n, c) for p, n, c in x.get(k, [])) or "(UNREFERENCED)"))


if __name__ == "__main__":
    main()
