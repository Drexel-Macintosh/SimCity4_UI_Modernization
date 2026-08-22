#!/usr/bin/env python3
r"""Grep the TEXT resource types (.UI = 0x00000000, LUA = 0xCA63E2A3,
INI/lua-ish 0x00000000) across every DBPF, case-insensitive. READ-ONLY.
    python textres_grep.py "0c16b317"
"""
import os, re, sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(HERE,"..",".."))
import index_all
from census_markers import qfs_decompress

TEXT_TYPES = {0x00000000, 0xCA63E2A3, 0x0A5BCF4B, 0xAA5C3144}

def payload(path,off,sz):
    with open(path,'rb') as f:
        f.seek(off); raw=f.read(sz)
    if len(raw)>9 and (raw[4:6]==b"\x10\xfb" or raw[0:2]==b"\x10\xfb"):
        try: raw=qfs_decompress(raw)
        except Exception: pass
    return raw

def main():
    pat=re.compile(sys.argv[1].encode('latin1'),re.I)
    g=index_all.index()
    n=0; scanned=0
    for (t,grp,i),(path,off,sz) in sorted(g['by_tgi'].items()):
        if t not in TEXT_TYPES: continue
        raw=payload(path,off,sz)
        scanned+=1
        for m in pat.finditer(raw):
            n+=1
            s=max(0,m.start()-120); e=min(len(raw),m.end()+120)
            ctx=raw[s:e].decode('latin1','replace').replace('\r',' ').replace('\n',' | ')
            print("{T=0x%08X,G=0x%08X,I=0x%08X} %s @+0x%X\n    ...%s..."
                  %(t,grp,i,os.path.basename(path),m.start(),ctx))
            if n>60: return
    print("\nscanned %d text resources, %d hits"%(scanned,n))
main()
