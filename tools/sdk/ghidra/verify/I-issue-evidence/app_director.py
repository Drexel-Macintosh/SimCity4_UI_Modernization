r"""Evidence tables for the cIGZApp and cIGZCOMDirector issues.

    python tools\sdk\ghidra\verify\I-issue-evidence\app_director.py [exe]

cIGZApp: the live app object is found from the exe's own boot code, not from
an address list. The framework stores the app pointer at 0xB540B4. The only
caller of the setter passes (new cSC4App) + 0x2C, and the constructor puts
the vtable there. Each of the 15 slots is then identified by what its code
does and by who calls it. The framework's own default class (cGZApp) is
decoded too: its bodies give each slot's return type.

cIGZCOMDirector: every director vtable in the exe that shares the base
class's slots 9-12 and 14-15 is listed with its slot 13.

Exits non-zero if any row stops holding.
"""
import os
import re
import struct
import sys

import capstone
import pefile

EXE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps", "SimCity 4.exe")
pe = pefile.PE(EXE, fast_load=True)
BASE = pe.OPTIONAL_HEADER.ImageBase
SECS = {s.Name.rstrip(b"\0").decode(): s for s in pe.sections}
T = SECS[".text"]
TLO = BASE + T.VirtualAddress
TC = T.get_data()
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
FAIL = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok:
        FAIL.append(msg)


def dword(va):
    return pe.get_dword_at_rva(va - BASE)


def body(va, n=0x40):
    out = []
    for i in MD.disasm(TC[va - TLO:va - TLO + n], va):
        out.append(("%s %s" % (i.mnemonic, i.op_str)).strip())
        if i.mnemonic in ("ret", "jmp"):
            break
    return "; ".join(out)


def calls_to(target):
    hits = []
    for o in range(len(TC) - 5):
        if TC[o] == 0xE8 and TLO + o + 5 + struct.unpack_from("<i", TC, o + 1)[0] == target:
            hits.append(TLO + o)
    return hits


# ------------------------------------------------------------------ cIGZApp
print("cIGZApp - the live object")
setter = 0x8793DD   # mov ecx,[esp+4]; mov [0xB540B4],ecx; mov eax,[ecx]; jmp [eax+4]
check(body(setter).startswith("mov ecx, dword ptr [esp + 4]; mov dword ptr [0xb540b4], ecx"),
      "%08X stores its argument in the app global 0xB540B4 (then AddRef)" % setter)
callers = calls_to(setter)
check(len(callers) == 1, "one caller: %s" % ", ".join("%08X" % c for c in callers))
pre = list(MD.disasm(TC[callers[0] - 0x40 - TLO:callers[0] - TLO], callers[0] - 0x40))
txt = "; ".join("%s %s" % (i.mnemonic, i.op_str) for i in pre)
check("push 0x670" in txt and "lea eax, [edi + 0x2c]" in txt and "call 0x44acd0" in txt,
      "it passes (new 0x670-byte object built by 0x44ACD0) + 0x2C")
ctor = list(MD.disasm(TC[0x44ACD0 - TLO:0x44ACD0 - TLO + 0x80], 0x44ACD0))
vt = next(int(i.op_str.split(", ")[1], 16) for i in ctor if i.op_str.startswith("dword ptr [esi + 0x2c], 0x"))
check(vt == 0xA86A68, "the constructor puts vtable %08X at +0x2C" % vt)
check(any("0xb07ec4" in i.op_str for i in MD.disasm(TC[callers[0] - 0x40 - TLO:callers[0] - TLO], callers[0] - 0x40))
      and pe.get_data(dword(0xB07EC4) - BASE, 10) == b"SimCity 4\x00",
      "its constructor argument is the module name \"SimCity 4\" (global 0xB07EC4)")
base_ctor = 0x87B144
bc = body(base_ctor, 0x40)
check("push 0x66" in bc and "lea ecx, [esi + 0x20]" in bc and "0xac3190" in bc,
      "the base class cGZApp (0x87B144) registers as service 0x66 (GZIID_cIGZApp), stores the name at "
      "+0x20 and has its own cIGZApp vtable 0xAC3190")

GZ = ["QueryInterface", "AddRef", "Release", "AsIGZSystemService", "ModuleName", "FrameWork",
      "AddApplicationService", "PreFrameWorkInit", "PostFrameWorkInit", "PreFrameWorkShutdown", "GZRun",
      "LoadRegistry", "AddDynamicLibrariesHere", "AddCOMDirectorsHere", "AddApplicationServicesHere"]
EXE_ROWS = [  # slot, name the exe proves, how
    (3, "AsIGZSystemService", "lea eax,[ecx-0x1C] in both classes"),
    (4, "AddApplicationService", "gets FrameWork() from its own slot 10, then tail-jumps to cIGZFrameWork::AddSystemService (+0xC) with the caller's one argument"),
    (5, "ModuleName", "returns [this+8], the module-name string the base constructor stored (\"SimCity 4\")"),
    (6, "PreFrameWorkInit", "framework boot 0x87AFDD calls it with no argument and tests the bool; on false it calls com->RealShutdown"),
    (7, "PostFrameWorkInit", "framework boot 0x87B09C calls it after AppInit and PostAppInit"),
    (8, "GZRun", "0x87959C calls it on Application(); both classes return false, and the framework then runs its own loop"),
    (9, "PreFrameWorkShutdown", "framework shutdown 0x87AB54 calls it"),
    (10, "FrameWork", "jmp 0x8793EC = mov eax,[0xB540AC] (the framework global); ret"),
    (11, "(void hook)", "the same empty `ret` in cGZApp and cSC4App; boot calls it third"),
    (12, "(void hook)", "the same empty `ret` in cGZApp and cSC4App; boot calls it second"),
    (13, "(void hook)", "the same empty `ret` in cGZApp and cSC4App; boot calls it first"),
    (14, "LoadRegistry", "returns bool: `mov al,1; ret` in cGZApp, and cSC4App's version reads Resources.ini, sets up the DB segments, and returns al=1. It is the only bool among 11-14"),
]
checks = {
    3: lambda a, b: body(a).startswith("lea eax, [ecx - 0x1c]") and a == b,
    4: lambda a, b: body(a, 0x20).startswith("mov eax, dword ptr [ecx]; call dword ptr [eax + 0x28]") and "jmp dword ptr [edx + 0xc]" in body(a, 0x20) and a == b,
    5: lambda a, b: body(a) == "mov eax, dword ptr [ecx + 8]; ret" and a == b,
    6: lambda a, b: insn_disp(0x87AFDD) == 0x18,
    7: lambda a, b: insn_disp(0x87B09C) == 0x1C,
    8: lambda a, b: body(a) == "xor al, al; ret" and body(b) == "xor al, al; ret" and insn_disp(0x87959C) == 0x20,
    9: lambda a, b: insn_disp(0x87AB54) == 0x24,
    10: lambda a, b: body(a).startswith("jmp 0x8793ec") and body(0x8793EC) == "mov eax, dword ptr [0xb540ac]; ret",
    11: lambda a, b: body(a) == "ret" and body(b) == "ret",
    12: lambda a, b: body(a) == "ret" and body(b) == "ret",
    13: lambda a, b: body(a) == "ret" and body(b) == "ret",
    14: lambda a, b: body(b) == "mov al, 1; ret" and "mov al, 1; add esp, 0xa0; ret" in "; ".join(
        "%s %s" % (i.mnemonic, i.op_str) for i in MD.disasm(TC[a - TLO:a - TLO + 0x320], a)),
}


def insn_disp(site):
    i = next(MD.disasm(TC[site - TLO:site - TLO + 8], site))
    m = re.search(r"\+ (0x[0-9a-f]+)\]", i.op_str)
    return int(m.group(1), 16) if (i.mnemonic == "call" and m) else None


print("\ncIGZApp slots: SC4 %08X / base cGZApp %08X" % (vt, 0xAC3190))
print("  %-4s %-23s %-27s %s" % ("slot", "exe", "gzcom-dll declares", "evidence"))
wrong = 0
for slot, name, how in EXE_ROWS:
    a, b = dword(vt + 4 * slot), dword(0xAC3190 + 4 * slot)
    ok = checks[slot](a, b)
    gz = GZ[slot]
    agree = gz == name or (name == "(void hook)" and gz.endswith("Here"))
    wrong += not agree
    print("  %s %2d  %-23s %-27s %s" % ("ok  " if ok else "FAIL", slot, name, gz + ("" if agree else "  <-- WRONG"), how))
    if not ok:
        FAIL.append("cIGZApp slot %d" % slot)
check(wrong == 8, "gzcom-dll's cIGZApp.h puts 8 of its 12 methods on the wrong slot (4, 5, 6, 7, 8, 10, 11, 14); "
      "3 and 9 are right, and 12 and 13 hold void hooks in both")

# ----------------------------------------------------------- cIGZCOMDirector
print("\ncIGZCOMDirector")
rd = SECS[".rdata"]
r0 = BASE + rd.VirtualAddress
vals = struct.unpack_from("<%dI" % (rd.SizeOfRawData // 4), rd.get_data())
anchor = 0xAD8BA0
sig = {k: dword(anchor + 4 * k) for k in (9, 10, 11, 12, 14, 15)}
dirs = [r0 + 4 * (k - 13) for k in range(13, len(vals) - 3)
        if all(vals[k - 13 + s] == v for s, v in sig.items())]
ids = {}
for d in dirs:
    f = dword(d + 13 * 4)
    b = TC[f - TLO:f - TLO + 6]
    if b[0] == 0xB8 and b[5] == 0xC3:
        ids[d] = struct.unpack_from("<I", b, 1)[0]
check(len(dirs) == 27 and len(ids) == 26 and len(set(ids.values())) == 26,
      "%d director vtables; slot 13 is `mov eax,imm32; ret` with a distinct constant in %d, and the last "
      "one is abstract" % (len(dirs), len(ids)))
check(ids.get(anchor) == 0xC3CAEC3B, "vtable %08X (GZResourceD's director) returns 0xC3CAEC3B, Scion's "
      "kGZResManCOMDirectorID" % anchor)
d16 = body(dword(anchor + 16 * 4), 0x30)
nxt = dword(anchor + 17 * 4)
check("test byte ptr [esp + 8], 1" in d16 and not (TLO <= nxt < TLO + T.Misc_VirtualSize),
      "slot 16 is the scalar deleting destructor and the vtable ends there: there is no AddDirector slot")
print("  slot 13 constants: %s" % ", ".join("%08X" % v for v in sorted(ids.values())))

print("\n%s" % ("ALL ROWS HOLD" if not FAIL else "%d FAILED: %s" % (len(FAIL), FAIL)))
sys.exit(1 if FAIL else 0)
