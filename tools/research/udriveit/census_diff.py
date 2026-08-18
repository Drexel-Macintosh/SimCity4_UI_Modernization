import sys, collections
from save_records import scan
cities = sys.argv[1:]
tab = {}
for c in cities:
    s, rows = scan(c)
    d = {}
    for t,g,i,recs,ul,rl,data in rows:
        d[t] = len(recs) if recs is not None else -1   # -1 = opaque
    tab[c] = d
allt = sorted(set().union(*[set(v) for v in tab.values()]))
names = [c.split('/')[-1].replace('.sc4','') for c in cities]
print("%-10s %s" % ("CLSID", "  ".join("%-14s" % n for n in names)))
for t in allt:
    row = [tab[c].get(t, None) for c in cities]
    fmt = []
    for v in row:
        fmt.append("%-14s" % ("absent" if v is None else ("opaque" if v==-1 else str(v))))
    print("0x%08X %s" % (t, "  ".join(fmt)))
