import struct,sys,os
from capstone import *
from capstone.x86 import *
EXE=r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
data=open(EXE,'rb').read()
pe=struct.unpack_from("<I",data,0x3C)[0]
n=struct.unpack_from("<H",data,pe+6)[0];opt=struct.unpack_from("<H",data,pe+20)[0]
base=struct.unpack_from("<I",data,pe+24+28)[0]
secs=[]
for i in range(n):
    o=pe+24+opt+i*40
    nm=data[o:o+8].rstrip(b"\0").decode('latin1')
    vs,va,rs,ra=struct.unpack_from("<IIII",data,o+8);secs.append((nm,va,vs,ra,rs))
nm,sva,vs,ra,rs=[s for s in secs if s[0]=='.text'][0]
start=base+sva
lo=int(os.environ.get('LO','0x460000'),0); hi=int(os.environ.get('HI','0x480000'),0)
o0=ra+(lo-base-sva); o1=ra+(hi-base-sva)
buf=data[o0:o1]
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
targets=[int(x,0) for x in sys.argv[1:]] or [0xd0,0xd4]
seen={}
for anchor in range(0,8):
    off=anchor
    while off < len(buf):
        got=False
        for ins in md.disasm(buf[off:], lo+off):
            got=True
            off = ins.address - lo + ins.size
            for op in ins.operands:
                if op.type==X86_OP_MEM and op.mem.disp in targets and op.mem.base not in (X86_REG_ESP,X86_REG_EBP,0) and op.mem.index==0:
                    seen[ins.address]="%08x  %-7s %s"%(ins.address,ins.mnemonic,ins.op_str)
        if not got: off+=1
for a in sorted(seen): print(seen[a])
