#!/usr/bin/env python3
r"""Find (uint32 id, char* name) pair tables in .data / .rdata of SimCity 4.exe
and print contiguous runs.  READ-ONLY.
    python idname_tables.py [minrun]
POSITIVE CONTROL: the run containing 0x0BB14381 -> "cSC4CitySituationManager"
MUST appear.  If it does not, the scan is broken.
"""
import struct,sys
EXE=r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
d=open(EXE,'rb').read()
pe=struct.unpack_from("<I",d,0x3C)[0]; n=struct.unpack_from("<H",d,pe+6)[0]; opt=struct.unpack_from("<H",d,pe+20)[0]
base=struct.unpack_from("<I",d,pe+24+28)[0]
secs=[]
for i in range(n):
    o=pe+24+opt+i*40
    nm=d[o:o+8].rstrip(b"\0").decode('latin1'); vs,va,rs,ra=struct.unpack_from("<IIII",d,o+8); secs.append((nm,va,vs,ra,rs))
def v2o(va):
    r=va-base
    for nm,sva,vs,ra,rs in secs:
        if sva<=r<sva+max(vs,rs):
            o=ra+(r-sva)
            if o<ra+rs: return o
def cstr(va,ml=64):
    o=v2o(va)
    if o is None: return None
    b=d[o:o+ml]; e=b.find(b"\0")
    if 2<e<ml and all(32<=c<127 for c in b[:e]): return b[:e].decode('latin1')
minrun=int(sys.argv[1]) if len(sys.argv)>1 else 4
for nm,sva,vs,ra,rs in secs:
    if nm not in (".data",".rdata"): continue
    va0=base+sva
    k=0; run=[]
    while k+8<=rs:
        a,b=struct.unpack_from("<II",d,ra+k)
        s=cstr(b)
        if s is not None and a!=0:
            run.append((va0+k,a,s)); k+=8
        else:
            if len(run)>=minrun:
                print("--- table at 0x%08X [%s] %d entries ---"%(run[0][0],nm,len(run)))
                for va,i,s in run: print("   0x%08X  0x%08X  %s"%(va,i,s))
            run=[]; k+=4
    if len(run)>=minrun:
        print("--- table at 0x%08X [%s] %d entries ---"%(run[0][0],nm,len(run)))
        for va,i,s in run: print("   0x%08X  0x%08X  %s"%(va,i,s))
