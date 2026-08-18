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
o=v2o(0x007A4734)
for ins in md.disasm(data[o:o+0x120],0x007A4734):
    print(f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
