#!/usr/bin/env python3
"""READ-ONLY: enumerate every instruction touching [reg+0xd0] / [reg+0xd4] in .text."""
import struct, sys
from capstone import *
EXE=r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
d=open(EXE,'rb').read()
pe=struct.unpack_from("<I",d,0x3C)[0]
n=struct.unpack_from("<H",d,pe+6)[0]; opt=struct.unpack_from("<H",d,pe+20)[0]
base=struct.unpack_from("<I",d,pe+24+28)[0]
secs=[]
for i in range(n):
    o=pe+24+opt+i*40
    nm=d[o:o+8].rstrip(b"\0").decode('latin1')
    vs,va,rs,ra=struct.unpack_from("<IIII",d,o+8); secs.append((nm,va,vs,ra,rs))
tx=[s for s in secs if s[0]=='.text'][0]
nm,sva,vs,ra,rs=tx
start=base+sva
blob=d[ra:ra+rs]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
targets=set(int(x,0) for x in (sys.argv[1:] or ['0xd0','0xd4']))
# linear sweep from many starts to reduce misalignment: just do one linear pass, plus a pass offset by func starts
hits={}
def sweep(off0):
    for ins in md.disasm(blob[off0:], start+off0):
        for op in ins.operands:
            if op.type==CS_OP_MEM and op.mem.base!=0 and op.mem.index==0 and op.mem.disp in targets:
                hits[ins.address]=(ins.mnemonic,ins.op_str,ins.bytes.hex())
sweep(0)
for a in sorted(hits):
    m,o,b=hits[a]
    print("%08x  %-7s %-40s %s"%(a,m,o,b))
print("total",len(hits))
