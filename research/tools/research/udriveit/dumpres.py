#!/usr/bin/env python3
r"""Dump one DBPF resource payload as text (or hex). READ-ONLY.
    python dumpres.py <type> <group> <inst> [--hex]
"""
import os,sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(HERE,"..",".."))
import index_all
from census_markers import qfs_decompress
t,g,i=[int(a,16) for a in sys.argv[1:4]]
G=index_all.index()
hit=G['by_tgi'].get((t,g,i))
if not hit:
    print("not found"); raise SystemExit(1)
path,off,sz=hit
with open(path,'rb') as f:
    f.seek(off); raw=f.read(sz)
if len(raw)>9 and (raw[4:6]==b"\x10\xfb" or raw[0:2]==b"\x10\xfb"):
    raw=qfs_decompress(raw)
print("# %s  %d bytes"%(path,len(raw)))
if "--hex" in sys.argv:
    for k in range(0,min(len(raw),4096),16):
        print("%06X  %-48s %s"%(k," ".join("%02X"%b for b in raw[k:k+16]),
            "".join(chr(b) if 32<=b<127 else "." for b in raw[k:k+16])))
else:
    sys.stdout.write(raw.decode('latin1','replace'))
