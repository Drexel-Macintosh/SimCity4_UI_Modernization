#!/usr/bin/env python3
"""Dump the (uint32 id, char* name) pair table in .data. Read-only."""
import struct, sys
GAME_EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
def load(path):
    data = open(path,"rb").read()
    pe = struct.unpack_from("<I",data,0x3C)[0]
    n = struct.unpack_from("<H",data,pe+6)[0]
    opt = struct.unpack_from("<H",data,pe+20)[0]
    base = struct.unpack_from("<I",data,pe+24+28)[0]
    secs=[]
    for i in range(n):
        o=pe+24+opt+i*40
        name=data[o:o+8].rstrip(b"\0").decode("latin1")
        vs,va,rs,ra=struct.unpack_from("<IIII",data,o+8)
        secs.append((name,va,vs,ra,rs))
    return data,base,secs
def va_to_off(va,base,secs):
    rva=va-base
    for name,sva,vs,ra,rs in secs:
        if sva<=rva<sva+max(vs,rs): return ra+(rva-sva)
    return None
def cstr(data,base,secs,va):
    off=va_to_off(va,base,secs)
    if off is None: return None
    end=data.find(b"\0",off)
    s=data[off:end]
    try: return s.decode("latin1")
    except: return None
def main():
    data,base,secs=load(GAME_EXE)
    start=int(sys.argv[1],0); count=int(sys.argv[2],0)
    off=va_to_off(start,base,secs)
    for k in range(count):
        i,p=struct.unpack_from("<II",data,off+8*k)
        s=cstr(data,base,secs,p) if 0x400000<p<0x1000000 else None
        print("0x%08X  id=0x%08X  ptr=0x%08X  %r" % (start+8*k,i,p,s))
main()
