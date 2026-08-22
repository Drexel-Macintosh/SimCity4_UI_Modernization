#!/usr/bin/env python3
r"""Census of every `call [reg+0xC4]` (cISC4City::GetCitySituationManager) in
.text, with the vtable slot invoked on the result within the next 48 bytes.
READ-ONLY.

Slot map (cISC4CitySituationManager, gzcom-dll header, cIGZUnknown = 3 slots):
 0x0C Init            0x10 Shutdown        0x14 GetMissionSuccessCount
 0x18 GetActiveSituation 0x1C GetCurrentStatus 0x20 GetActiveAuto
 0x24 GetCurrentTarget   0x28 GetCurrentTargetIndex 0x2C GetNumTargets
 0x30 GetNumTargetsRemaining 0x34 GetCurrentTimeLimitSeconds
 0x38 GetCurrentSituationTime 0x3C GetCurrentTimeRemainingSeconds
 0x40 GetCurrentTargetName 0x44 GetSituationAura 0x48 GetSituationMoney
 0x4C IsSituationAvailable(cISC4Occupant*) 0x50 IsSituationAvailable(guid)
 0x54 InitiateSituationByGuid 0x58 InitiateSituationForOccupant
 0x5C InitiateSituationByAutomataGroup 0x60 StartJoyride
 0x64 TreatAutomatonAsGroup 0x68 SetMaxCSI 0x6C GetMaxCSI
 0x70 GetTrackedAutomataCount 0x74 SetCSIVisible 0x78 GetCSIVisible
 0x7C HandleTuningParametersChanged 0x80 CountdownIsInProgress
 0x84 ResetTutorials
POSITIVE CONTROL: 0x007EF6F4 (the U-Drive-It panel) must appear with slot 0x78.
"""
import struct,re
import capstone
from capstone import x86
EXE=r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
NAMES={0x0C:"Init",0x10:"Shutdown",0x14:"GetMissionSuccessCount",0x18:"GetActiveSituation",
 0x1C:"GetCurrentStatus",0x20:"GetActiveAuto",0x24:"GetCurrentTarget",0x28:"GetCurrentTargetIndex",
 0x2C:"GetNumTargets",0x30:"GetNumTargetsRemaining",0x34:"GetCurrentTimeLimitSeconds",
 0x38:"GetCurrentSituationTime",0x3C:"GetCurrentTimeRemainingSeconds",0x40:"GetCurrentTargetName",
 0x44:"GetSituationAura",0x48:"GetSituationMoney",0x4C:"IsSituationAvailable(occupant)",
 0x50:"IsSituationAvailable(guid)",0x54:"InitiateSituationByGuid",0x58:"InitiateSituationForOccupant",
 0x5C:"InitiateSituationByAutomataGroup",0x60:"StartJoyride",0x64:"TreatAutomatonAsGroup",
 0x68:"SetMaxCSI",0x6C:"GetMaxCSI",0x70:"GetTrackedAutomataCount",0x74:"SetCSIVisible",
 0x78:"GetCSIVisible",0x7C:"HandleTuningParametersChanged",0x80:"CountdownIsInProgress",
 0x84:"ResetTutorials"}
d=open(EXE,'rb').read()
pe=struct.unpack_from("<I",d,0x3C)[0]; n=struct.unpack_from("<H",d,pe+6)[0]; opt=struct.unpack_from("<H",d,pe+20)[0]
base=struct.unpack_from("<I",d,pe+24+28)[0]
secs=[]
for i in range(n):
    o=pe+24+opt+i*40
    nm=d[o:o+8].rstrip(b"\0").decode('latin1'); vs,va,rs,ra=struct.unpack_from("<IIII",d,o+8); secs.append((nm,va,vs,ra,rs))
_,sva,vs,ra,rs=[s for s in secs if s[0]=='.text'][0]
tbase=base+sva; seg=d[ra:ra+rs]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32); md.detail=True
hits=0
for m in re.finditer(rb"\xff[\x90\x91\x92\x93\x95\x96\x97]\xc4\x00\x00\x00",seg):
    va=tbase+m.start(); hits+=1
    slots=[]
    for ins in md.disasm(seg[m.start()+6:m.start()+6+56], va+6):
        if ins.mnemonic=="call" and ins.operands[0].type==x86.X86_OP_MEM and ins.operands[0].mem.base!=0:
            dsp=ins.operands[0].mem.disp
            if 0<=dsp<=0x90:
                slots.append((ins.address,dsp))
    print("call GetCitySituationManager @0x%08X -> %s"%(va,
      ", ".join("+0x%02X %s @0x%08X"%(s,NAMES.get(s,"?"),a) for a,s in slots) or "(no vcall within 56B)"))
print("\n%d call sites"%hits)
