#!/usr/bin/env python3
"""READ-ONLY byte-pattern scan for modrm disp32 == 0xd0/0xd4 with base reg (no index).
Covers 8-bit/32-bit forms of mov/fld/fst/fstp/fadd/lea/cmp/push/call etc. by
brute-force: find every occurrence of the 4-byte LE disp and disassemble backwards."""
import struct, sys
from capstone import *
EXE=r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
d=open(EXE,'rb').read()
pe=struct.unpack_from("<I",d,0x3C)[0]
n=struct.unpack_from("<H",d,pe+6)[0]; opt=struct.unpack_from("<H",d,pe+20)[0]
base=struct.unpack_from("<I",d,pe+24+28)[0]
for i in range(n):
    o=pe+24+opt+i*40
    nm=d[o:o+8].rstrip(b"\0").decode('latin1')
    vs,va,rs,ra=struct.unpack_from("<IIII",d,o+8)
    if nm=='.text': sva,ssz,sra,srs=va,vs,ra,rs
start=base+sva
blob=d[sra:sra+srs]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
targets=[int(x,0) for x in (sys.argv[1:] or ['0xd0','0xd4'])]
found={}
for t in targets:
    pat=struct.pack("<I",t)
    p=0
    while True:
        p=blob.find(pat,p)
        if p<0: break
        # try instruction starts from p-10 .. p-2
        for back in range(2,12):
            s=p-back
            if s<0: continue
            for ins in md.disasm(blob[s:s+16], start+s):
                if ins.size==back+4:
                    for op in ins.operands:
                        if op.type==CS_OP_MEM and op.mem.disp==t and op.mem.base!=0 and op.mem.index==0:
                            reg=ins.reg_name(op.mem.base)
                            if reg not in ('esp','ebp'):
                                found[ins.address]=(ins.mnemonic,ins.op_str,ins.bytes.hex(),reg)
                break
        p+=1
for a in sorted(found):
    m,o,b,r=found[a]
    print("%08x  %-7s %-42s [%s]  %s"%(a,m,o,r,b))
print("total",len(found))
