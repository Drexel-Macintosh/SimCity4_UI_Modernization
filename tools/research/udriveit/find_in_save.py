#!/usr/bin/env python3
"""Search every DECOMPRESSED subfile of a save for 32-bit values."""
import sys, struct, collections
from save_records import scan, walk
from clsid_table import TABLE

def main():
    path = sys.argv[1]
    vals = [int(a,0) for a in sys.argv[2:]]
    s, rows = scan(path)
    tot = collections.Counter()
    for t,g,i,recs,ul,rl,d in rows:
        for v in vals:
            pat = struct.pack("<I", v)
            n = d.count(pat)
            if n:
                # which records?
                where=[]
                if recs:
                    off=0
                    while True:
                        k=d.find(pat,off)
                        if k<0: break
                        off=k+1
                        for ri,(ro,rs,crc,mem,vmaj,vmin) in enumerate(recs):
                            if ro<=k<ro+rs:
                                where.append((ri, k-ro)); break
                print("0x%08X %-36s  value 0x%08X x%d  %s" % (
                    t, TABLE.get(t,"<UNNAMED>"), v, n,
                    "recs:"+ ",".join("#%d+0x%X"%w for w in where[:8]) if where else "(opaque)"))
                tot[v]+=n
    print("--- totals ---")
    for v in vals:
        print("0x%08X : %d" % (v, tot[v]))

main()
