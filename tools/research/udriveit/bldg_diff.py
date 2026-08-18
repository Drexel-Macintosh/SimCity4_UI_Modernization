import sys, struct, collections, re
from save_records import scan
from save_objects import NAMES, keys_in
cities=sys.argv[1:]
tab={}
for c in cities:
    s,rows=scan(c)
    cnt=collections.Counter()
    for t,g,i,recs,ul,rl,d in rows:
        if t!=0xA9BD882D or not recs: continue
        for (ro,rs,crc,mem,vmaj,vmin) in recs:
            ks=keys_in(d[ro:ro+rs])
            if ks:
                nm=NAMES.get(ks[0][1],(None,))[0] or "I=0x%08X"%ks[0][1]
                cnt[nm]+=1
    tab[c]=cnt
allk=sorted(set().union(*[set(v) for v in tab.values()]))
names=[c.split('/')[-1].replace('.sc4','')[:10] for c in cities]
print("%-52s %s"%("BUILDING EXEMPLAR"," ".join("%-9s"%n for n in names)))
for k in allk:
    row=[tab[c].get(k,0) for c in cities]
    # highlight the 2/8/7 signature
    print("%-52s %s"%(k," ".join("%-9d"%v for v in row)))
