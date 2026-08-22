#!/usr/bin/env python3
r"""Search DBPF entries of the given TYPES for 32-bit LE values. READ-ONLY."""
import os, sys, struct, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
from census_markers import dbpf_index, qfs_decompress, discover_dbpf  # noqa
from sc4paths import plugins_dir, game_dir  # noqa

T_EXEMPLAR = 0x6534284A
T_COHORT   = 0x05342861
TYPES = {T_EXEMPLAR, T_COHORT}

def main():
    args=[a for a in sys.argv[1:] if not a.startswith("--")]
    deep = "--deep" in sys.argv
    vals=[int(a,0)&0xFFFFFFFF for a in args]
    vals.append(0x29F10000)
    pats={v:struct.pack("<I",v) for v in vals}
    roots=[game_dir()]
    if deep:
        p=plugins_dir(require=False)
        if p and os.path.isdir(p): roots.append(p)
    counts={v:0 for v in vals}
    nfiles=0; nent=0
    for root in roots:
        for path in discover_dbpf(root):
            idx=dbpf_index(path)
            if not idx: continue
            nfiles+=1
            blob=open(path,"rb").read()
            for (t,g,i,off,sz) in idx:
                if t not in TYPES: continue
                nent+=1
                raw=blob[off:off+sz]
                if len(raw)>9 and (raw[4:6]==b"\x10\xfb" or raw[0:2]==b"\x10\xfb"):
                    try: raw=qfs_decompress(raw)
                    except Exception: pass
                for v,pat in pats.items():
                    k=raw.find(pat)
                    while k>=0:
                        counts[v]+=1
                        if counts[v]<=25:
                            print("0x%08X in {T=0x%08X,G=0x%08X,I=0x%08X} @+0x%X  %s"
                                  %(v,t,g,i,k,os.path.basename(path)))
                        k=raw.find(pat,k+1)
    print("\nscanned %d files, %d exemplar/cohort entries"%(nfiles,nent))
    for v in vals:
        print("0x%08X: %d hit(s)%s"%(v,counts[v]," <-- POSITIVE CONTROL" if v==0x29F10000 else ""))
main()
