import os,sys,struct
_HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(_HERE))
import common as C
d=C.exe_bytes(); B=0x400000
def rd(va,n): return d[va-B:va-B+n]
idxtbl=0x78BC28; jmptbl=0x78BC08
idx=rd(idxtbl,0x69)
print("index table 0x78BC28 (0x69 bytes), id base 0x67:")
jt=[struct.unpack_from("<I",rd(jmptbl+4*i,4))[0] for i in range(max(idx)+1)]
print("jump table entries (%d):"%len(jt), ["0x%X"%x for x in jt])
for i,b in enumerate(idx):
    iid=0x67+i
    print("  id 0x%03X -> slot %2d -> 0x%08X" % (iid,b,jt[b]))
