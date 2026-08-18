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
def refs(v):
    nd=struct.pack("<I",v); out=[]
    for n,sva,vs,ro,rs in secs:
        bl=data[ro:ro+rs]; s=0
        while True:
            k=bl.find(nd,s)
            if k<0: break
            out.append((n,IB+sva+k)); s=k+1
    return out
md=Cs(CS_ARCH_X86,CS_MODE_32)
# function boundaries by int3 runs across 0x7a4900..0x7a6200
lo,hi=0x7a4900,0x7a6200
o=v2o(lo); blob=data[o:o+(hi-lo)]
bounds=[]; i=0
while i<len(blob):
    if blob[i]==0xCC:
        j=i
        while j<len(blob) and blob[j]==0xCC: j+=1
        if j-i>=2 and j<len(blob): bounds.append(lo+j)
        i=j
    else: i+=1
print("boundaries:", [hex(b) for b in bounds])
for site in (0x7a4b19,0x7a53d7,0x7a55d1,0x7a5f1b):
    cand=[b for b in bounds if b<=site]
    st=cand[-1] if cand else None
    r=refs(st) if st else []
    print(f"site {hex(site)} -> fn {hex(st) if st else '?'} vtable-refs={[(n,hex(a)) for n,a in r]}")
# the minimap window vtable base implied by the known draw slot
print("minimap window vtable base (0xAB8518 - 0x160) =", hex(0xAB8518-0x160))
o=v2o(0xAB83B8)
print("first 8 slots:", [hex(struct.unpack_from('<I',data,o+4*i)[0]) for i in range(8)])
