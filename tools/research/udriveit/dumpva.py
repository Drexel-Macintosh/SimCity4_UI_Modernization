#!/usr/bin/env python3
r"""Hex/dword dump SimCity 4.exe at a VA. READ-ONLY.  python dumpva.py 0xB08B00 [n] [--dw]"""
import struct,sys
EXE=r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
data=open(EXE,'rb').read()
pe=struct.unpack_from("<I",data,0x3C)[0]
n=struct.unpack_from("<H",data,pe+6)[0]; opt=struct.unpack_from("<H",data,pe+20)[0]
base=struct.unpack_from("<I",data,pe+24+28)[0]
secs=[]
for i in range(n):
    o=pe+24+opt+i*40
    nm=data[o:o+8].rstrip(b"\0").decode('latin1')
    vs,va,rs,ra=struct.unpack_from("<IIII",data,o+8); secs.append((nm,va,vs,ra,rs))
def v2o(va):
    r=va-base
    for nm,sva,vs,ra,rs in secs:
        if sva<=r<sva+max(vs,rs):
            o=ra+(r-sva)
            if o<ra+rs: return o,nm
    return None,None
def cstr(va,ml=90):
    o,_=v2o(va)
    if o is None: return None
    b=data[o:o+ml]; e=b.find(b"\0")
    if 1<e<ml and all(32<=c<127 for c in b[:e]): return b[:e].decode('latin1')
va=int(sys.argv[1],0); cnt=int(sys.argv[2],0) if len(sys.argv)>2 else 128
o,sec=v2o(va)
print("VA 0x%08X [%s] off 0x%X"%(va,sec,o))
if "--dw" in sys.argv:
    for k in range(0,cnt,4):
        d=struct.unpack_from("<I",data,o+k)[0]
        s=cstr(d)
        print("  0x%08X: 0x%08X %s"%(va+k,d,("-> \"%s\""%s) if s else ""))
else:
    for k in range(0,cnt,16):
        chunk=data[o+k:o+k+16]
        print("%08X  %-48s %s"%(va+k," ".join("%02X"%b for b in chunk),
              "".join(chr(b) if 32<=b<127 else "." for b in chunk)))
