import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IB=0x400000
data=open(EXE,'rb').read()
pe=struct.unpack_from("<I",data,0x3C)[0]; nsec=struct.unpack_from("<H",data,pe+6)[0]; opt=struct.unpack_from("<H",data,pe+20)[0]
secs=[]; off=pe+24+opt
for i in range(nsec):
    n=data[off:off+8].rstrip(b"\0").decode('latin1'); vs,va,rs,ro=struct.unpack_from("<IIII",data,off+8); secs.append((n,va,vs,ro,rs)); off+=40
def v2o(va):
    r=va-IB
    for n,sva,vs,ro,rs in secs:
        if sva<=r<sva+max(vs,rs): return ro+(r-sva)
md=Cs(CS_ARCH_X86,CS_MODE_32)
# whole .text: find  sar r,1 ; shl r,1 ; cmp ; jg  back-edge  (the halving idiom)
lo,hi=0x407000+IB-IB, 0
n,sva,vs,ro,rs = secs[0]
base=IB+sva; blob=data[ro:ro+rs]
hits=[]
ins=list(md.disasm(blob, base))
for i in range(len(ins)-3):
    a,b,c,d = ins[i],ins[i+1],ins[i+2],ins[i+3]
    if a.mnemonic=='sar' and a.op_str.endswith(', 1') and b.mnemonic=='shl' and b.op_str.endswith(', 1') \
       and c.mnemonic=='cmp' and d.mnemonic in ('jg','jge','ja','jae') :
        try:
            tgt=int(d.op_str,16)
        except: continue
        if tgt==a.address:
            hits.append(a.address)
print(f"halving-idiom back-edges in .text: {len(hits)}")
for h in hits: print("   ", hex(h))
