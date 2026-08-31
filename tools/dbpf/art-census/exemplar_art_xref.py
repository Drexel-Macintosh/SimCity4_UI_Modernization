#!/usr/bin/env python3
"""Which exemplars BIND FSH art by instance id?

The Zone Manager exemplar {6534284A,E7E2C2DB,E9482490} proved the mechanism:
a Uint32 array property whose values are FSH instance ids in group 0x1ABE787D,
read at runtime by 0x004DC460 into a 16-slot table.  This sweep finds EVERY
exemplar/cohort that does the same, so an art table cannot hide in data.

Positive control (asserted): the Zone Manager's property 0xE94825B6 must come
back in the results.
"""
import sys, collections
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\dbpf\row15-probe")
import dbpfcore as D

G_ART = 0x1ABE787D
T_FSH = 0x7AB50E44
T_PNG = 0x856DDBAC

arch = [D.Archive(p) for p in D.discover_archives()]
art = set()
for A in arch:
    for e in A.index:
        if e[1] == G_ART and e[0] in (T_FSH, T_PNG):
            art.add(e[2])
sys.stderr.write("art instance ids in group %08X: %d\n" % (G_ART, len(art)))

rows = []
scanned = failed = 0
for A in arch:
    for e in A.index:
        if e[0] not in (0x6534284A, 0x05342861):
            continue
        scanned += 1
        try:
            buf, q, l = A.payload(e)
            par, props = D.decode_exemplar(buf)
        except Exception:
            failed += 1
            continue
        nm = props.get(0x20, (None, [""]))[1][0] if 0x20 in props else ""
        for pid, (tname, vals) in props.items():
            if tname not in ("Uint32", "Sint32"):
                continue
            iv = [v for v in vals if isinstance(v, int)]
            if len(iv) < 2:
                continue
            hit = [v for v in iv if v in art]
            if len(hit) == len(iv) and len({v for v in iv if v}) >= 2:
                rows.append((A.name, "%08X" % e[2], nm, "%08X" % pid,
                             len(iv), " ".join("%08X" % v for v in iv)))
    A.close()

sys.stderr.write("exemplars/cohorts scanned %d, undecodable %d\n" % (scanned, failed))
print("archive,instance,name,prop,n,ids")
for r in rows:
    print("%s,%s,\"%s\",%s,%d,%s" % r)
