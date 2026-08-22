"""fn.py - disassemble one function using the derived function map.

Unlike tools\\flyout-sim\\disasm_fn.py (which stops at the first `ret`),
this uses funcs.json boundaries, so a builder with early-out rets is shown
whole - which is exactly what the constant map needs.

Usage:
    python fn.py 0x788300                 # the function OWNING that VA
    python fn.py 0x788300 --grep=push
    python fn.py 0x788300 --range=0x788300:0x788400
    python fn.py --callers 0x779660       # who calls it
    python fn.py --callees 0x7876b0       # what it calls
"""
import os
import sys

import common as C


def disasm(lo, hi):
    m = C.md()
    blob = C.rd(lo, hi - lo)
    return list(m.disasm(blob, lo))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = [a for a in sys.argv[1:] if a.startswith("--")]
    grep = None
    rng = None
    for o in opts:
        if o.startswith("--grep="):
            grep = o.split("=", 1)[1].lower()
        if o.startswith("--range="):
            a, b = o.split("=", 1)[1].split(":")
            rng = (int(a, 0), int(b, 0))

    if "--callers" in opts or "--callees" in opts:
        edges = C.jload(os.path.join(C.WORK, "edges.json"))
        fm = C.FuncMap()
        va = int(args[0], 0)
        if "--callers" in opts:
            seen = []
            for s, t, k in edges:
                if t == va and k == "call":
                    seen.append((s, fm.owner(s)))
            print("%d caller sites of sub_%X:" % (len(seen), va))
            for s, o in seen:
                print("  site 0x%08X   in sub_%X" % (s, o))
        else:
            o = fm.owner(va)
            e = fm.end(o)
            import collections
            h = collections.Counter()
            for s, t, k in edges:
                if o <= s < e and k == "call":
                    h[t] += 1
            print("callees of sub_%X (0x%X..0x%X):" % (o, o, e))
            for t, c in h.most_common():
                print("  sub_%-8X x%d" % (t, c))
        return

    va = int(args[0], 0)
    fm = C.FuncMap()
    if rng:
        lo, hi = rng
    else:
        lo = fm.owner(va)
        hi = fm.end(lo)
    print("; sub_%X  0x%X..0x%X  (%d bytes)" % (lo, lo, hi, hi - lo))
    for ins in disasm(lo, hi):
        line = "0x%08X:  %-22s %s %s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        if grep and grep not in line.lower():
            continue
        print(line)


if __name__ == "__main__":
    main()
