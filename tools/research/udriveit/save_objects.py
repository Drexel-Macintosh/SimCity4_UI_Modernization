#!/usr/bin/env python3
r"""Every persisted object in a city save, resolved to its EXEMPLAR NAME.

Each occupant record embeds its source exemplar key as the byte triple
    u32 group | u32 type(0x6534284A) | u32 instance
(measured, not assumed - see the cSC4PropOccupant hexdump: group 0xC977C536 at
+0x38, type at +0x3C, instance 0x1E680000 at +0x40).  Joining that instance
against the 11,118-exemplar index in idx-section1.txt turns the save into a
by-name inventory of the city.
"""
import sys, struct, collections, re
from save_records import scan
from clsid_table import TABLE

EXTYPE = 0x6534284A

def load_names():
    names = {}
    for fn in ("idx-section1.txt",):
        for line in open(fn, encoding="utf-8", errors="replace"):
            m = re.match(r"^([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s+(\S+)\s+\{[^}]*\}\s+(.*)$", line.strip())
            if m:
                names[int(m.group(2), 16)] = (m.group(4).strip(), m.group(1))
    return names

NAMES = load_names()
PAT = struct.pack("<I", EXTYPE)

def keys_in(rec):
    out = []
    p = 0
    while True:
        k = rec.find(PAT, p)
        if k < 0 or k < 4 or k + 8 > len(rec):
            break
        p = k + 1
        g = struct.unpack_from("<I", rec, k - 4)[0]
        i = struct.unpack_from("<I", rec, k + 4)[0]
        out.append((g, i))
    return out

def main(path):
    s, rows = scan(path)
    print("%d exemplar names loaded from idx-section1.txt" % len(NAMES))
    total = collections.Counter()
    percls = collections.defaultdict(collections.Counter)
    unnamed = collections.Counter()
    for t, g, i, recs, ul, rl, d in rows:
        if not recs:
            continue
        for (ro, rs, crc, mem, vmaj, vmin) in recs:
            rec = d[ro:ro + rs]
            ks = keys_in(rec)
            if not ks:
                continue
            gg, ii = ks[0]
            nm = NAMES.get(ii, (None, None))[0]
            key = nm if nm else "<unnamed I=0x%08X G=0x%08X>" % (ii, gg)
            total[key] += 1
            percls[t][key] += 1
            if not nm:
                unnamed[(gg, ii)] += 1
    print("\n==== objects whose exemplar instance appears EXACTLY TWICE ====")
    for k, c in sorted(total.items()):
        if c == 2:
            owners = [TABLE.get(t, "0x%08X" % t) for t in percls if k in percls[t]]
            print("  %-60s x2   owner=%s" % (k, ",".join(owners)))
    print("\n==== all U-Drive-It / marker family objects present ====")
    for k, c in sorted(total.items()):
        if re.search(r"Tag1x1x3|UDI|Drive|Mission|Marker", k, re.I):
            owners = [TABLE.get(t, "0x%08X" % t) for t in percls if k in percls[t]]
            print("  %-60s x%-5d owner=%s" % (k, c, ",".join(owners)))
    print("\n==== per-class object totals with resolved keys ====")
    for t in sorted(percls, key=lambda x: -sum(percls[x].values())):
        print("  0x%08X %-38s %d keyed records, %d distinct exemplars"
              % (t, TABLE.get(t, "<UNNAMED>"), sum(percls[t].values()), len(percls[t])))
    print("\nunresolved exemplar instances: %d distinct, %d records"
          % (len(unnamed), sum(unnamed.values())))
    for (gg, ii), c in unnamed.most_common(25):
        print("   G=0x%08X I=0x%08X  x%d" % (gg, ii, c))

main(sys.argv[1])
