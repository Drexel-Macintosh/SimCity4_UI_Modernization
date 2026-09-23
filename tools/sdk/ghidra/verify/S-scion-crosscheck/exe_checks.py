r"""Scion cross-check, part 2: settle each disagreement against the exe.

    python tools\sdk\ghidra\verify\S-scion-crosscheck\exe_checks.py [exe]

Scion (github.com/nsgomez/scion, LGPL-2.1+) reimplements the framework layer
of the same exe. Where its interface headers disagree with the gzcom-dll pin
we compile against (header_diff.py), this script reads the exe's own code to
say which one is right. Nothing from Scion is copied here; the one Scion
fact used is its resource director's ID, 0xC3CAEC3B, as an anchor.

Every check prints MEASURED lines and exits non-zero if the exe stops matching
what README.md records.
"""
import os
import re
import struct
import sys

import capstone
import pefile

EXE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps", "SimCity 4.exe")
LOG = os.path.join(os.path.expanduser("~"), "OneDrive", "Documents", "SimCity 4", "Plugins",
                   "010-SC4UIScale", "SC4UIScale.log")

pe = pefile.PE(EXE, fast_load=True)
BASE = pe.OPTIONAL_HEADER.ImageBase
SECS = {s.Name.rstrip(b"\0").decode(): s for s in pe.sections}
TEXT = SECS[".text"]
TLO = BASE + TEXT.VirtualAddress
THI = TLO + TEXT.Misc_VirtualSize
TCODE = TEXT.get_data()
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
FAIL = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok:
        FAIL.append(msg)


def dword(va):
    return pe.get_dword_at_rva(va - BASE)


def insn(va):
    off = va - TLO
    return next(MD.disasm(TCODE[off:off + 16], va))


def is_code(v):
    return TLO <= v < THI


# ---------------------------------------------------------------- toolchain
print("1. Toolchain (Scion's README says VS .NET 2003 + STLport)")
opt = pe.DOS_HEADER.e_lfanew + 24
raw = open(EXE, "rb").read()
check((raw[opt + 2], raw[opt + 3]) == (7, 10), "optional-header linker version %d.%d (7.10 = VS .NET 2003)"
      % (raw[opt + 2], raw[opt + 3]))
stl, std = raw.count(b"@_STL@@"), raw.count(b"@std@@")
check(stl > 0 and std == 0, "RTTI names in STLport 4.x's _STL namespace: %d; in std: %d "
      "(each count is the other's control)" % (stl, std))
print("        no Rich header in this build, so the compiler's own build number is not readable")

# ------------------------------------------------------------------ cIGZApp
print("\n2. cIGZApp order: gzcom-dll vs Mac symbols + Scion")
# The exe's framework boot (cGZFramework::sInit 0x87AF13, sRun 0x87957A).
# The app pointer lives at 0xB540B4 and the framework at 0xB540AC.
# Rows: (call site, object global, displacement, what it is, gz slot, Mac/Scion slot)
APP, FW = 0xB540B4, 0xB540AC
rows = [
    (0x87AFDD, APP, 0x18, "PreFrameworkInit (result tested; failure path calls com->RealShutdown)", 7, 6),
    (0x87B09C, APP, 0x1C, "PostFrameworkInit (after AppInit/PostAppInit)", 8, 7),
    (0x87959C, None, 0x20, "GZRun (on framework->Application(), result tested)", 10, 8),
]
for site, glob, disp, what, gz, mac in rows:
    i = insn(site)
    m = re.search(r"\[(\w+) \+ (0x[0-9a-f]+)\]", i.op_str)
    got = int(m.group(2), 16) if (i.mnemonic == "call" and m) else None
    check(got == disp, "%08X %s [%s]: slot %d. Mac/Scion predicts %d, gzcom-dll %d"
          % (site, i.mnemonic, i.op_str, disp // 4, mac, gz))
# Ruler: the same function's framework/COM calls, which both headers agree on.
for site, disp, what in [(0x87AF5D, 0x5C, "cIGZFrameWork::GetCOMObject (slot 23)"),
                         (0x87AF66, 0x24, "cIGZCOM::RealInit (slot 9)"),
                         (0x87AF73, 0x2C, "cIGZCOM::SetServiceRunning (slot 11)"),
                         (0x87AF97, 0x0C, "cIGZFrameWork::AddSystemService (slot 3)"),
                         (0x879582, 0x94, "cIGZFrameWork::Application (slot 37)")]:
    i = insn(site)
    check(("+ 0x%x]" % disp) in i.op_str, "ruler %08X %s [%s] = %s" % (site, i.mnemonic, i.op_str, what))
check("0xb540b4" in insn(0x87AFD5).op_str and "0xb540b4" in insn(0x87B094).op_str,
      "the PreFrameworkInit and PostFrameworkInit calls are made on the app global 0xB540B4")

# ----------------------------------------------------------- cIGZCOMDirector
print("\n3. cIGZCOMDirector slot 13: AddDirector (gzcom-dll, Mac) or GetDirectorID (Scion)")
anchor_fn = TCODE.find(b"\xB8" + struct.pack("<I", 0xC3CAEC3B) + b"\xC3")
check(anchor_fn >= 0, "Scion's resource-director ID 0xC3CAEC3B is returned by `mov eax,imm; ret` at %08X"
      % (TLO + anchor_fn))
anchor_fn += TLO
rdata = SECS[".rdata"]
rva0 = BASE + rdata.VirtualAddress
rd = rdata.get_data()
vals = struct.unpack_from("<%dI" % (len(rd) // 4), rd)
refs = [rva0 + 4 * k for k, v in enumerate(vals) if v == anchor_fn]
check(len(refs) == 1, "exactly one vtable points at it (%s)" % ", ".join("%08X" % r for r in refs))
avt = refs[0] - 13 * 4
check(dword(avt + 12 * 4) and insn(dword(avt + 12 * 4)).op_str == "eax, dword ptr [ecx + 0x24]"
      and "[esi + 0x24], ebx" in "".join("%s %s;" % (x.mnemonic, x.op_str) for x in
                                         MD.disasm(TCODE[dword(avt + 3 * 4) - TLO:][:0x20], dword(avt + 3 * 4))),
      "anchor vtable %08X: slot 3 stores the cIGZCOM* at +0x24 and slot 12 (GZCOM) returns it" % avt)
base_sig = {k: dword(avt + 4 * k) for k in (9, 10, 11, 12, 14, 15)}
directors = []
for k in range(13, len(vals) - 3):
    if all(vals[k - 13 + s] == v for s, v in base_sig.items()):
        directors.append(rva0 + 4 * (k - 13))
ids, other = [], []
for vt in directors:
    f = dword(vt + 13 * 4)
    b = TCODE[f - TLO:f - TLO + 6]
    if b[0] == 0xB8 and b[5] == 0xC3:
        ids.append(struct.unpack_from("<I", b, 1)[0])
    else:
        other.append((vt, f))
print("        director vtables sharing the base's slots 9-12 and 14-15: %d" % len(directors))
check(len(ids) >= 10 and len(set(ids)) == len(ids),
      "slot 13 is a per-class constant getter in %d of them, all different (GetDirectorID)" % len(ids))
check(all(insn(f).mnemonic == "push" for _, f in other),
      "the rest (%d) are abstract: slot 13 is the pure-virtual stub" % len(other))
check(0xC3CAEC3B in ids, "Scion's own ID is one of them")
# The exe's slot 16 is the scalar deleting destructor, which gzcom-dll's
# cRZCOMDllDirector also puts at 16 (destructor declared before GetDirectorID).
d16 = dword(avt + 16 * 4)
body = "".join("%s %s;" % (x.mnemonic, x.op_str) for x in MD.disasm(TCODE[d16 - TLO:][:0x30], d16))
check("test byte ptr [esp + 8], 1" in body and "ret 4" in body,
      "slot 16 is the scalar deleting destructor, where gzcom-dll also puts its destructor")

# -------------------------------------------------------- cIGZFrameWorkW32
print("\n4. cIGZFrameWorkW32: gzcom-dll/Mac (no Run) vs Scion (Run at slot 4)")
print("        our DLL calls GetMainHWND at gzcom-dll slot 5 (Scion's slot 5 is GetWindowsInstance)")
print("        and subclasses the window it returns. SetWindowSubclass succeeds only on a real")
print("        window of this process, so the log line proves slot 5 returned one.")
if os.path.exists(LOG):
    text = open(LOG, encoding="utf-8", errors="replace").read()
    check("Tick subclass installed" in text and "SetWindowSubclass failed" not in text,
          "live log: 'Tick subclass installed', no 'SetWindowSubclass failed' (%s)" % LOG)
else:
    print("        (no live log at %s; skipped, not a pass)" % LOG)

print("\n%s" % ("ALL MATCH README.md" if not FAIL else "%d FAILED" % len(FAIL)))
sys.exit(1 if FAIL else 0)
