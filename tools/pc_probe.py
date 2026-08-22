import struct
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IB = 0x400000
data = open(EXE,'rb').read()
pe = struct.unpack_from("<I",data,0x3C)[0]
nsec = struct.unpack_from("<H",data,pe+6)[0]
opt = struct.unpack_from("<H",data,pe+20)[0]
secs=[]; off=pe+24+opt
for i in range(nsec):
    n=data[off:off+8].rstrip(b"\0").decode('latin1')
    vs,va,rs,ro=struct.unpack_from("<IIII",data,off+8); secs.append((n,va,vs,ro,rs)); off+=40
print("sections:", [(n,hex(IB+va),hex(vs)) for n,va,vs,ro,rs in secs])
def refs(v):
    nd=struct.pack("<I",v); out=[]
    for n,sva,vs,ro,rs in secs:
        bl=data[ro:ro+rs]; s=0
        while True:
            k=bl.find(nd,s)
            if k<0: break
            out.append((n,IB+sva+k)); s=k+1
    return out
# POSITIVE CONTROL for the dword/vtable-ref scan:
for name,v in (("MINIMAP DRAW 0x007A79B0 (known vtable slot 0x160)",0x007A79B0),
               ("recompute 0x007A7840",0x007A7840),
               ("bake 0x007A7FF0",0x007A7FF0),
               ("TOP 0x007A2740",0x007A2740),
               ("MID 0x007A2380",0x007A2380),
               ("ROWFILL 0x0079ED90",0x0079ED90),
               ("switch 0x007A2F60",0x007A2F60)):
    r=refs(v)
    print(f"{name}: {len(r)} dword refs -> {[ (n,hex(a)) for n,a in r[:6] ]}")
# POSITIVE CONTROL for the "which vtable is 0x7A79B0 in" question
r=refs(0x007A79B0)
for n,a in r:
    print("   vtable slot", hex(a), "-> slot index", hex(a-0x00ADF6A0) if 0<=a-0x00ADF6A0<0x400 else "")
