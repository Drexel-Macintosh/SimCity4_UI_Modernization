import sys, collections
from save_records import scan
from clsid_table import TABLE
cities = sys.argv[1:]
tab={}; 
for c in cities:
    s,rows = scan(c)
    tab[c]={t:(len(r) if r is not None else -1) for t,g,i,r,ul,rl,dd in rows}
allt = sorted(set().union(*[set(v) for v in tab.values()]))
names=[c.split('/')[-1].replace('.sc4','')[:12] for c in cities]
print("%-10s %-40s %s"%("CLSID","CLASS NAME"," ".join("%-9s"%n for n in names)))
for t in allt:
    nm = TABLE.get(t,"<UNNAMED>")
    row=[tab[c].get(t) for c in cities]
    f=[("-" if v is None else ("opaque" if v==-1 else str(v))) for v in row]
    print("0x%08X %-40s %s"%(t,nm," ".join("%-9s"%x for x in f)))
