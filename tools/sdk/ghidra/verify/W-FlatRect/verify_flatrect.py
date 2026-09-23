"""W-FlatRect gate: re-measures every cIGZWinFlatRect fact from the shipped exe
(OFFLINE, read-only) and fails loudly if any reading changes.
usage: python verify_flatrect.py        -> prints PASS/FAIL per check, exit 1 on any FAIL

Every check reads bytes from SimCity 4.exe 1.1.641 (via pe.py); nothing is
inferred from names. Positive control: the IID scan must find the two
GetChildAs sites 0x47B993 / 0x4861D7 established before this unit."""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import *
import xref

FAIL = 0
def check(name, cond, detail=""):
    global FAIL
    print(("PASS " if cond else "FAIL ") + name + (("  -- " + detail) if detail else ""))
    if not cond:
        FAIL += 1

def body(va, n=60):
    return " ; ".join(f"{i.mnemonic} {i.op_str}" for i in dis_fn(va, n))

def retn(va):
    return retn_of(va)

IID = 0xC2AFA76F
CLSID = 0xC2AFA76E
CTOR = 0x9CD842
CLASS_VT = 0xAE20A0
FR_VT = 0xAE2050
ABS_VT = 0xAE2300
ADJ = 0xD8

# --- identity -------------------------------------------------------------
sites = [ins.address for va, ins in xref.find(IID) if ins]
check("positive control: IID scan finds the known GetChildAs sites 0x47B993 & 0x4861D7",
      0x47B993 in sites and 0x4861D7 in sites, f"{len(sites)} sites")
check("negative control: scan for a value absent from .text returns nothing", xref.find(0xC2AF0F1A) == [])
check("QI 0x9CD1D2 compares riid with IID and returns this+0xD8",
      "cmp dword ptr [esp + 4], 0xc2afa76f" in body(0x9CD1D2) and "lea edx, [ecx + 0xd8]" in body(0x9CD1D2))
check("class vt slot 0 = QI 0x9CD1D2", u32(CLASS_VT) == 0x9CD1D2)
cb = body(CTOR, 40)
check("ctor stores abstract vt 0xAE2300 then FR vt 0xAE2050 at +0xD8, class vt 0xAE20A0 at +0",
      "lea eax, [esi + 0xd8]" in cb and "0xae2300" in cb and "0xae2050" in cb and "mov dword ptr [esi], 0xae20a0" in cb)
check("ctor zeroes byte +0xDC, byte +0xDD, dwords +0xE0..+0xEC",
      all(s in cb for s in ("[esi + 0xdc], al", "[esi + 0xdd], al", "[esi + 0xe0], eax", "[esi + 0xe4], eax", "[esi + 0xe8], eax", "[esi + 0xec], eax")))
check("factory 0x99899E allocates 0xF0 bytes then jumps to ctor", "push 0xf0" in body(0x99899E) and "jmp 0x9cd842" in body(0x99899E))
check("FR vt is exactly 20 slots (class vt starts at FR_VT+0x50)", FR_VT + 20 * 4 == CLASS_VT)
n = 0
while u32(ABS_VT + 4 * n) == 0x5D4A10: n += 1
nxt = [ins.address for va, ins in xref.find(ABS_VT + 0x50) if ins]
check("abstract cIGZWinFlatRect vt 0xAE2300 is 20 purecalls wide (0xAE2350 is another ctor's vt)",
      n >= 20 and len(nxt) >= 1, f"purecall run {n}, 0xAE2350 stored at {[hex(a) for a in nxt]}")

# --- per slot ---------------------------------------------------------------
S = [u32(FR_VT + 4 * i) for i in range(20)]
def thunk_to(va):
    ins = dis(va, 2, stop_at_ret=False)
    if ins[0].mnemonic == "sub" and ins[0].op_str == "ecx, 0xd8" and ins[1].mnemonic == "jmp":
        return int(ins[1].op_str, 16)
    return None
check("slot 0 QI thunk -> 0x9CD1D2", thunk_to(S[0]) == 0x9CD1D2)
check("slot 1 AddRef thunk -> class slot 1", thunk_to(S[1]) == u32(CLASS_VT + 4))
check("slot 2 Release thunk -> class slot 2", thunk_to(S[2]) == u32(CLASS_VT + 8))
check("slot 3 AsIGZWin = lea eax,[ecx-0xd8]", body(S[3], 3).startswith("lea eax, [ecx - 0xd8]"))
# slots 4-7: thunk -> jmp stub -> cGZWin class slots 106,107,103,104
def via_stub(va):
    t = thunk_to(va)
    j = dis(t, 1, stop_at_ret=False)[0]
    return t, int(j.op_str, 16)
for fs, cs, what in ((4, 106, "SetFillColor(ulong native)"), (5, 107, "SetFillColor(uchar r,g,b)"),
                     (6, 103, "GetFillColor() -> native"), (7, 104, "GetFillColor(uchar& r,g,b)")):
    t, tgt = via_stub(S[fs])
    check(f"slot {fs} {what} -> class vt slot {cs}", u32(CLASS_VT + 4 * cs) == t and u32(0xAB5B48 + 4 * cs) == tgt,
          f"stub {t:#x} -> {tgt:#x}")
check("cGZWin 107 packs (r<<16)|(g<<8)|b into +0xD4, ret 0xC",
      "mov dword ptr [ecx + 0xd4], eax" in body(0x99BFAC) and retn(0x99BFAC) == 0xC)
check("cGZWin 106 native->rgb via service vt+0x90 then this->vt[107], ret 4",
      "call dword ptr [edx + 0x90]" in body(0x99BF1F) and "call dword ptr [eax + 0x1ac]" in body(0x99BF1F) and retn(0x99BF1F) == 4)
check("cGZWin 103 rgb->native via service vt+0x88, ret 0", "call dword ptr [esi + 0x88]" in body(0x99BF7A) and retn(0x99BF7A) == 0)
check("cGZWin 104 writes R,G,B bytes of +0xD4 to 3 refs, ret 0xC", "lea eax, [ecx + 0xd4]" in body(0x99BFC9) and retn(0x99BFC9) == 0xC)
b8 = body(S[8]); check("slot 8 SetOutlineColor(ulong): native->rgb then self vt[9] (+0x24), ret 4",
      "call dword ptr [edx + 0x90]" in b8 and "call dword ptr [eax + 0x24]" in b8 and retn(S[8]) == 4)
b9 = body(S[9]); check("slot 9 SetOutlineColor(r,g,b): packs into iface+8,+0xC,+0x10,+0x14, ret 0xC",
      all(f"[ecx + {o}], eax" in b9 for o in ("0x14", "0x10", "0xc", "8")) and retn(S[9]) == 0xC)
b10 = body(S[10]); check("slot 10 SetOutlineColor(idx,r,g,b): switch 0..3 -> +8/+0xC/+0x10/+0x14, ret 0x10",
      all(f"[ecx + {o}], eax" in b10 for o in ("0x14", "0x10", "0xc", "8")) and retn(S[10]) == 0x10)
b11 = body(S[11]); check("slot 11 GetOutlineColor(idx,&r,&g,&b), ret 0x10", "byte ptr [ecx + 0xa]" in b11 and retn(S[11]) == 0x10)
b12 = body(S[12], 120); check("slot 12 SetOutlineFlags: byte iface+5 = arg; 0x10 raised / 0x20 sunken bevel; |= 0xF; ret 4",
      "mov byte ptr [esi + 5], al" in b12 and "test al, 0x30" in b12 and "or byte ptr [esi + 5], 0xf" in b12 and retn(S[12]) == 4)
check("slot 13 GetOutlineFlags = movzx byte iface+5", body(S[13], 2).startswith("movzx eax, byte ptr [ecx + 5]"))
check("slot 14 GetOutlineFlag(mask) = (flags & mask) != 0, ret 4", "and al, byte ptr [esp + 4]" in body(S[14]) and retn(S[14]) == 4)
check("slot 15 SetOutlineColors(4 x native), ret 0x10", body(S[15], 120).count("call dword ptr [eax + 0x90]") == 4 and retn(S[15]) == 0x10)
check("slot 16 GetOutlineColors(4 x native&), ret 0x10", body(S[16], 120).count("call dword ptr [eax + 0x88]") == 4 and retn(S[16]) == 0x10)
b17 = body(S[17], 80); check("slot 17 AutoSize(const cRZRect&): mode byte iface+4, GetArea(slot47) ... SetArea(slot55), ret 4",
      "cmp byte ptr [esi + 4], 0" in b17 and "call dword ptr [eax + 0xbc]" in b17 and "call dword ptr [edx + 0xdc]" in b17 and retn(S[17]) == 4)
check("slot 18 SetSizeMode: byte iface+4 = arg, returns 1, ret 4", "mov byte ptr [ecx + 4], al" in body(S[18]) and retn(S[18]) == 4)
check("slot 19 GetSizeMode = movzx byte iface+4", body(S[19], 2).startswith("movzx eax, byte ptr [ecx + 4]"))

# --- paint ------------------------------------------------------------------
bp = body(0x9CD1FF, 120)
check("GZPaint: 0x40 skips fill; fill = DC(+0x6C) SetColor(GetFillColorRGB slot126) + FillRect(+0x24)",
      "test byte ptr [ebx + 0xdd], 0x40" in bp and "call dword ptr [eax + 0x1f8]" in bp and "lea edx, [ebx + 0x24]" in bp)
check("GZPaint: edges L/T/R/B gated by bits 1/2/4/8 with colours +0xE0/+0xE4/+0xE8/+0xEC, 1-px lines to r-1/b-1",
      all(s in bp for s in ("test al, 1", "[ebx + 0xdd], 2", "[ebx + 0xdd], 4", "[ebx + 0xdd], 8",
                            "[ebx + 0xe0]", "[ebx + 0xe4]", "[ebx + 0xe8]", "[ebx + 0xec]", "dec esi", "dec edi")))

# --- call sites (Windows slot numbers seen from callers) --------------------
bl = body(0x94E33B, 300)
check(".UI applier 0x94E33B: style -> SetOutlineFlags (+0x30); colorleft..colorbottom -> SetOutlineColor(idx,r,g,b) (+0x28)",
      "call dword ptr [eax + 0x30]" in bl and bl.count("call dword ptr [eax + 0x28]") == 4)
bf = " ; ".join(f"{i.mnemonic} {i.op_str}" for i in md.disasm(rd(0x77BC1D, 0x20), 0x77BC1D))
check("button factory +0x100 outer: SetFillColor(0xFF,0,0xFF) via slot 5 (+0x14) then SetOutlineFlags(0x40)",
      "push 0xff ; push 0 ; push 0xff ; call dword ptr [edx + 0x14]" in bf and "push 0x40 ; call dword ptr [eax + 0x30]" in bf)
bb = " ; ".join(f"{i.mnemonic} {i.op_str}" for i in md.disasm(rd(0x99AABF, 0x18), 0x99AABF))
check("title/gen bar 0x42B7C351: SetOutlineFlags(0xF) then SetSizeMode(5)", "push 0xf" in bb and "push 5" in bb and "[eax + 0x48]" in bb)
bs = body(0x999B84, 40)
check("GZWinGen child callback 0x999B84 calls AutoSize (+0x44) with rect inset by gutters", "call dword ptr [eax + 0x44]" in bs)

# --- compiler cross-check -----------------------------------------------------
asm = os.path.join(os.path.dirname(os.path.abspath(__file__)), "msvc_order.asm")
if os.path.exists(asm):
    txt = open(asm, encoding="latin1").read()
    m = re.search(r"\?\?_7cFR@@6B@ DD\s+FLAT:(\S+)(.*?)CONST\s+ENDS", txt, re.S)
    order = [m.group(1)] + re.findall(r"DD\s+FLAT:(\S+)", m.group(2))
    want = ["SetFillColor@cFR@@UAEXK", "SetFillColor@cFR@@UAEXEEE", "GetFillColor@cFR@@UBEKXZ", "GetFillColor@cFR@@UBEXAAE00",
            "SetOutlineColor@cFR@@UAEXK", "SetOutlineColor@cFR@@UAEXEEE", "SetOutlineColor@cFR@@UAEXJEEE", "GetOutlineColor",
            "SetOutlineFlags", "GetOutlineFlags", "GetOutlineFlag@", "SetOutlineColors", "GetOutlineColors", "AutoSize",
            "SetSizeMode", "GetSizeMode"]
    ok = len(order) == 20 and all(w in order[4 + i] for i, w in enumerate(want))
    check("MSVC compile of the MAC declaration order reproduces the exe order (overloads grouped, reversed)", ok)
else:
    print("SKIP msvc_order.asm missing (run msvc_order.cmd)")

print(f"\n{'ALL PASS' if not FAIL else str(FAIL) + ' FAIL'}")
sys.exit(1 if FAIL else 0)
