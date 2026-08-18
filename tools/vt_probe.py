import struct
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
def rd(va): return struct.unpack_from("<I",data,v2o(va))[0]
TEXT_LO, TEXT_HI = 0x407000, 0xA7FA2D
def is_code(v): return TEXT_LO <= v < TEXT_HI
# scan back from a slot to the vtable start (first dword that is not code)
def vt_base(slot):
    a=slot
    while is_code(rd(a-4)): a-=4
    return a
for slot in (0xAB7EEC, 0xAB814C, 0xAB8518):
    b=vt_base(slot)
    print(f"slot {hex(slot)} -> vtable base {hex(b)}  index {hex(slot-b)}  ({(slot-b)//4})  len~", end=" ")
    n=0
    while is_code(rd(b+4*n)): n+=1
    print(n, "slots")
# compare the two window-looking vtables at the GetChildAsRecursive slot
for b in (0xAB7EEC, 0xAB814C, 0xAB8518):
    base=vt_base(b)
    print(hex(base), "slot+0x94 =", hex(rd(base+0x94)), " slot+0xBC =", hex(rd(base+0xBC)), " slot+0x0C =", hex(rd(base+0x0C)))
