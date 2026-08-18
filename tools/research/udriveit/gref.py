#!/usr/bin/env python3
r"""Find every .text reference to a global VA and print the nearby pushed
string literals (window +-N bytes). READ-ONLY.
    python gref.py 0x00B43D1C [window]
"""
import struct, sys, re
import capstone
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

def load():
    data=open(EXE,'rb').read()
    pe=struct.unpack_from("<I",data,0x3C)[0]
    n=struct.unpack_from("<H",data,pe+6)[0]; opt=struct.unpack_from("<H",data,pe+20)[0]
    base=struct.unpack_from("<I",data,pe+24+28)[0]
    secs=[]
    for i in range(n):
        o=pe+24+opt+i*40
        nm=data[o:o+8].rstrip(b"\0").decode('latin1')
        vs,va,rs,ra=struct.unpack_from("<IIII",data,o+8); secs.append((nm,va,vs,ra,rs))
    return data,base,secs

data,base,secs=load()
def v2o(va):
    r=va-base
    for nm,sva,vs,ra,rs in secs:
        if sva<=r<sva+max(vs,rs):
            o=ra+(r-sva)
            if o<ra+rs: return o
def cstr(va,ml=80):
    o=v2o(va)
    if o is None: return None
    b=data[o:o+ml]; e=b.find(b"\0")
    if 2<e<ml and all(32<=c<127 for c in b[:e]): return b[:e].decode('latin1')

target=int(sys.argv[1],0)
win=int(sys.argv[2],0) if len(sys.argv)>2 else 40
text=next(s for s in secs if s[0]==".text")
_,sva,vs,ra,rs=text
tbase=base+sva
pat=struct.pack("<I",target)
hits=[]
off=ra
while True:
    k=data.find(pat,off,ra+rs)
    if k<0: break
    hits.append(k); off=k+1
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32); md.detail=True
print("%d refs to 0x%08X in .text"%(len(hits),target))
for k in hits:
    va=tbase+(k-ra)
    lo=max(ra,k-win)
    strs=[]
    for ins in md.disasm(data[lo:k+win],tbase+(lo-ra)):
        if ins.mnemonic=="push" and ins.operands and ins.operands[0].type==capstone.x86.X86_OP_IMM:
            s=cstr(ins.operands[0].imm)
            if s: strs.append((ins.address,s))
    print("  ref@~0x%08X  %s"%(va, "; ".join("0x%X:%s"%(a,s) for a,s in strs)))
