#!/usr/bin/env python3
r"""Enumerate every cheat code SimCity 4.exe registers.

MECHANISM (measured, VA 0x006930FE-0x00693117):
    mov eax,[<char** in .data>]     ; the cheat name
    push eax
    lea ecx,[esp+N] ; call 0x408480 ; cRZString ctor from char*
    push eax                        ; -> cIGZString&
    push <cheatID imm32>
    mov ecx,[0x00B43CAC]            ; cIGZCheatCodeManager
    call [ebx+0x0C]                 ; AddCheatCode(id, name)

So: walk .text, track the last `mov eax,[imm32]`/`push imm32` that resolves to
an ASCII string, and pair it with the imm32 pushed just before a
`call [reg+0x0C]` that follows a load of 0x00B43CAC.  READ-ONLY.

POSITIVE CONTROL: the output MUST contain WeaknessPays / HowDryIAm /
FightThePower.  If it does not, the scan is broken and any absence below
(e.g. "no mission-indicator cheat") is meaningless.
"""
import struct, sys
import capstone
from capstone import x86
EXE=r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
CHEATMGR=0x00B43CAC
d=open(EXE,'rb').read()
pe=struct.unpack_from("<I",d,0x3C)[0]; n=struct.unpack_from("<H",d,pe+6)[0]; opt=struct.unpack_from("<H",d,pe+20)[0]
base=struct.unpack_from("<I",d,pe+24+28)[0]
secs=[]
for i in range(n):
    o=pe+24+opt+i*40
    nm=d[o:o+8].rstrip(b"\0").decode('latin1'); vs,va,rs,ra=struct.unpack_from("<IIII",d,o+8); secs.append((nm,va,vs,ra,rs))
def v2o(va):
    r=va-base
    for nm,sva,vs,ra,rs in secs:
        if sva<=r<sva+max(vs,rs):
            o=ra+(r-sva)
            if o<ra+rs: return o
def cstr(va,ml=64):
    o=v2o(va)
    if o is None: return None
    b=d[o:o+ml]; e=b.find(b"\0")
    if 2<e<ml and all(32<=c<127 for c in b[:e]): return b[:e].decode('latin1')
def dw(va):
    o=v2o(va)
    return struct.unpack_from("<I",d,o)[0] if o is not None else None

_,sva,vs,ra,rs=[s for s in secs if s[0]=='.text'][0]
tbase=base+sva
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32); md.detail=True

# find all .text sites referencing the cheat manager global
sites=[]
pat=struct.pack("<I",CHEATMGR)
k=ra
while True:
    j=d.find(pat,k,ra+rs)
    if j<0: break
    sites.append(tbase+(j-ra)); k=j+1
print("# %d .text references to cheat-manager global 0x%08X"%(len(sites),CHEATMGR))
out={}
for s in sites:
    start=max(tbase, s-0x40); end=min(tbase+rs, s+0x600)
    o=v2o(start)
    names=[]; lastname=None
    for ins in md.disasm(d[o:o+(end-start)], start):
        if ins.mnemonic=="mov" and len(ins.operands)==2 and ins.operands[1].type==x86.X86_OP_MEM \
           and ins.operands[1].mem.base==0 and ins.operands[1].mem.index==0:
            t=dw(ins.operands[1].mem.disp & 0xFFFFFFFF)
            if t:
                sv=cstr(t)
                if sv: lastname=sv
        if ins.mnemonic=="push" and ins.operands[0].type==x86.X86_OP_IMM:
            sv=cstr(ins.operands[0].imm & 0xFFFFFFFF)
            if sv: lastname=sv
        if ins.mnemonic=="push" and ins.operands[0].type==x86.X86_OP_IMM and lastname:
            v=ins.operands[0].imm & 0xFFFFFFFF
            if 0x1000 < v < 0xFFFFFFFF and cstr(v) is None:
                names.append((ins.address,v,lastname))
        if ins.mnemonic=="call" and ins.operands[0].type==x86.X86_OP_MEM and ins.operands[0].mem.disp==0x0C:
            if names:
                a,v,nm=names[-1]
                out.setdefault((v,nm),ins.address)
                names=[]; lastname=None
for (v,nm),site in sorted(out.items(), key=lambda x:x[0][1].lower()):
    print("cheat 0x%08X  %-28s  registered @0x%08X"%(v,nm,site))
print("\n%d distinct (id,name) pairs"%len(out))
