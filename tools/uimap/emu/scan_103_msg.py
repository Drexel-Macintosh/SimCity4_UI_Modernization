import os,sys,struct
_HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(_HERE))
import common as C
d=C.exe_bytes(); B=0x400000
# find all occurrences of imm 0x42B7C353 and 0xA2BF8AD1 in .text
for val,name in ((0x42B7C353,"msg 0x42B7C353"),):
    pat=struct.pack("<I",val)
    print("==",name)
    off=0
    while True:
        i=d.find(pat,off)
        if i<0: break
        va=i+B
        if C.TEXT_LO<=va<C.TEXT_HI:
            print("  .text 0x%08X  ctx: %s"%(va, d[i-6:i+6].hex()))
        elif C.RDATA_LO<=va<C.RDATA_HI:
            print("  .rdata 0x%08X"%va)
        elif C.DATA_LO<=va<C.DATA_HI:
            print("  .data 0x%08X"%va)
        off=i+1
