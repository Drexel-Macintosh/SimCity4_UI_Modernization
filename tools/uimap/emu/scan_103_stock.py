"""#103 STOCK LENS - read-only exe scans."""
import os, sys, struct
_HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(_HERE))
import common as C

text=C.text_blob(); LO=C.TEXT_LO; HI=C.TEXT_HI
print("exe fp",C.exe_fingerprint())

def rel32_targets():
    """yield (site, target, kind) for E8/E9"""
    for i in range(len(text)-5):
        op=text[i]
        if op in (0xE8,0xE9):
            rel=struct.unpack_from("<i",text,i+1)[0]
            tgt=LO+i+5+rel
            if LO<=tgt<HI:
                yield LO+i, tgt, ("call" if op==0xE8 else "jmp")

TG=list(rel32_targets())
calltgts=sorted(set(t for _,t,k in TG if k=="call"))
import bisect
def fn_start(va):
    i=bisect.bisect_right(calltgts,va)-1
    return calltgts[i] if i>=0 else None

def callers(target):
    return [(s,k) for s,t,k in TG if t==target]

for fn in (0x77BEC0,0x78B120,0x779850,0x779660):
    print("\n== callers of 0x%X ==" % fn)
    for s,k in callers(fn):
        print("   %s from 0x%08X  (in fn 0x%08X)"%(k,s,fn_start(s) or 0))

print("\nfn containing 0x78826D ->","0x%08X"%fn_start(0x78826D))
print("fn containing 0x77C7E6 ->","0x%08X"%fn_start(0x77C7E6))
print("fn containing 0x77F51A ->","0x%08X"%fn_start(0x77F51A))
print("fn containing 0x786BA2 ->","0x%08X"%fn_start(0x786BA2))

print("\n=== callers of the four builders + the WinProc head ===")
for fn in (0x77C660,0x77E600,0x786690,0x7876B0,0x77AB40,0x77C5E0):
    cs=callers(fn)
    print("0x%08X <- "%fn, ["0x%08X"%s for s,_ in cs])
# find function start containing 0x78C19D by scanning back for 'sub esp,0xb0' (81 EC B0 00 00 00)
import re
pat=bytes.fromhex("81ECB0000000")
i=text.rfind(pat,0,0x78C19D-LO)
print("WinProc start candidate: 0x%08X"%(LO+i))
print("callers of that:", ["0x%08X"%s for s,_ in callers(LO+i)])
