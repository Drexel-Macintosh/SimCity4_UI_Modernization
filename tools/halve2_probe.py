import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IB=0x400000
data=open(EXE,'rb').read()
pe=struct.unpack_from("<I",data,0x3C)[0]; nsec=struct.unpack_from("<H",data,pe+6)[0]; opt=struct.unpack_from("<H",data,pe+20)[0]
secs=[]; off=pe+24+opt
for i in range(nsec):
    n=data[off:off+8].rstrip(b"\0").decode('latin1'); vs,va,rs,ro=struct.unpack_from("<IIII",data,off+8); secs.append((n,va,vs,ro,rs)); off+=40
n,sva,vs,ro,rs=secs[0]; base=IB+sva; blob=data[ro:ro+rs]
md=Cs(CS_ARCH_X86,CS_MODE_32)
hits=[]
for i in range(len(blob)-8):
    # sar r32,1  (D1 F8..FF)   shl r32,1 (D1 E0..E7)
    if blob[i]!=0xD1 or not (0xF8<=blob[i+1]<=0xFF): continue
    if blob[i+2]!=0xD1 or not (0xE0<=blob[i+3]<=0xE7): continue
    # then a cmp (2 or 3 bytes) then jg/jge/ja/jae rel8 pointing back to i
    for clen in (2,3,6):
        j=i+4+clen
        if j+1>=len(blob): continue
        if blob[j] in (0x7F,0x7D,0x77,0x73):
            rel=struct.unpack_from("<b",blob,j+1)[0]
            if (j+2+rel)==i:
                hits.append(base+i); break
print(f"POSITIVE CONTROL: does it find the two KNOWN loops 0x79edb2 / 0x79edd0? ",
      hex(0x79EDB2) in [hex(h) for h in hits], hex(0x79EDD0) in [hex(h) for h in hits])
print(f"halving-idiom back-edges in .text: {len(hits)}")
for h in hits:
    print("   ", hex(h))
