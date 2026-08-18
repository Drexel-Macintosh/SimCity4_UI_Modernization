#!/usr/bin/env python3
r"""Harvest every `csi_image = "0x........"` from the LUA resources and report
the owning automata_group, then locate the bitmap TGI in the archives.

The game's own schema (LUA {T=0xCA63E2A3,G=0x4A5E8F3F,I=0xFF1D4800}) says:
    -- bitmap image id to use for city-mission indicators
    csi_image = "string",
READ-ONLY.
"""
import os,re,sys,struct
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(HERE,"..",".."))
import index_all
from census_markers import qfs_decompress
TEXT_TYPES={0x00000000,0xCA63E2A3}
G=index_all.index()
rows=[]
for (t,g,i),(path,off,sz) in sorted(G['by_tgi'].items()):
    if t not in TEXT_TYPES: continue
    with open(path,'rb') as f:
        f.seek(off); raw=f.read(sz)
    if len(raw)>9 and (raw[4:6]==b"\x10\xfb" or raw[0:2]==b"\x10\xfb"):
        try: raw=qfs_decompress(raw)
        except Exception: pass
    txt=raw.decode('latin1','replace')
    for m in re.finditer(r'csi_image\s*=\s*"(0x[0-9a-fA-F]+)"',txt):
        # nearest preceding automata_group.<name>
        pre=txt[:m.start()]
        gm=None
        for gg in re.finditer(r'automata_group\.(\w+)\s*=',pre): gm=gg
        rows.append((int(m.group(1),16), gm.group(1) if gm else "?", os.path.basename(path),
                     "{T=0x%08X,G=0x%08X,I=0x%08X}"%(t,g,i)))
by={}
for v,grp,f,tgi in rows: by.setdefault(v,[]).append(grp)
print("%d csi_image assignments, %d distinct bitmap ids\n"%(len(rows),len(by)))
for v in sorted(by):
    print("csi_image 0x%08X  <- %d group(s): %s"%(v,len(by[v]),", ".join(sorted(set(by[v])))))
print("\n--- where each bitmap id lives in the archives ---")
for v in sorted(by):
    hits=[(t,g,i,p) for (t,g,i),(p,o,s) in G['by_tgi'].items() if i==v]
    if not hits:
        print("0x%08X : NOT FOUND as an instance id in any indexed DBPF"%v)
    for (t,g,i,p) in hits:
        print("0x%08X : {T=0x%08X,G=0x%08X,I=0x%08X}  %s"%(v,t,g,i,os.path.basename(p)))
