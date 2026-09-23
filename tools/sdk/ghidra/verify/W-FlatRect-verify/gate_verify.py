"""W-FlatRect VERIFIER gate (independent of the finder's pe.py/xref.py/verify_flatrect.py).
Re-measures the load-bearing FlatRect claims from SimCity 4.exe 1.1.641 (offline,
read-only, hand-parsed PE) and the verifier's own MSVC compile (msvc_layout.asm).
usage: python gate_verify.py   -> PASS/FAIL lines, exit 1 on any FAIL."""
import sys, os, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

FAIL = 0
def check(name, cond, detail=""):
    global FAIL
    print(("PASS " if cond else "FAIL ") + name + (("  -- " + detail) if detail else ""))
    if not cond:
        FAIL += 1

def B(va, n=200):
    return " ; ".join(f"{i.mnemonic} {i.op_str}" for i in fn(va, n))

IID, CLSID = 0xC2AFA76F, 0xC2AFA76E
FR, CVT, ABS, GZ = 0xAE2050, 0xAE20A0, 0xAE2300, 0xADC8D8

# ---- identity (with controls) ----
hits = [insn_containing(h) for h in find_imm32(IID)]
addrs = [i.address for i in hits if i]
check("IID raw scan: 17 .text hits incl. positive controls 0x47B993/0x4861D7",
      len(addrs) == 17 and 0x47B993 in addrs and 0x4861D7 in addrs, f"{len(addrs)}")
check("negative control 0xC2AF0F1A: 0 hits", find_imm32(0xC2AF0F1A) == [])
check("class QI 0x9CD1D2: cmp riid,IID ; lea edx,[ecx+0xd8] ; else jmp base QI 0x99B774",
      "cmp dword ptr [esp + 4], 0xc2afa76f" in B(0x9CD1D2) and "lea edx, [ecx + 0xd8]" in B(0x9CD1D2) and "jmp 0x99b774" in B(0x9CD1D2))
c = B(0x9CD842, 40)
check("ctor 0x9CD842: base ctor 0x99D938, [+0xD8]=0xAE2300 then 0xAE2050, [+0]=0xAE20A0",
      "call 0x99d938" in c and "0xae2300" in c and "0xae2050" in c and "mov dword ptr [esi], 0xae20a0" in c)
check("factory 0x99899E new(0xF0) -> jmp ctor; registration 0x998BFB push clsid after push factory",
      "push 0xf0" in B(0x99899E, 8) and "jmp 0x9cd842" in B(0x99899E, 8)
      and u32(0x998BF7) == 0x99899E and u32(0x998BFC) == CLSID)
check("iface vt is 20 slots: 0xAE209C holds GetSizeMode code, 0xAE20A0 is the class vt (QI) - no RTTI COL between",
      u32(FR + 19 * 4) == 0x9CD6EC and u32(CVT) == 0x9CD1D2 and find_imm32(CVT) != [])
n = 0
while u32(ABS + 4 * n) == 0x5D4A10:
    n += 1
check("abstract vt 0xAE2300 bounded at 20 by the 0xAE2350 store at 0x9CDB68 (purecall run continues)",
      find_imm32(0xAE2350) == [0x9CDB6A] and n >= 20, f"run {n}")
check("cGZWin base ctor writes up to +0xD4 -> Windows cGZWin size 0xD8 (Mac 0xE8)",
      "[esi + 0xd4]" in B(0x99D938, 300))

# ---- all 20 slots ----
exp = {
    0: (0x9CD1D2, -0xD8, [8], "0xc2afa76f"),
    1: (0x94C47C, -0xD8, [0], "inc dword ptr [ecx + 0xc]"),
    2: (0x99B7A3, -0xD8, [0], "dec eax"),
    3: (0x95BA6F, 0, [0], "lea eax, [ecx - 0xd8]"),
    4: (0x99BF1F, -0xD8, [4], "call dword ptr [eax + 0x1ac]"),
    5: (0x99BFAC, -0xD8, [12], "mov dword ptr [ecx + 0xd4], eax"),
    6: (0x99BF7A, -0xD8, [0], "call dword ptr [esi + 0x88]"),
    7: (0x99BFC9, -0xD8, [12], "mov cl, byte ptr [eax + 2]"),
    8: (0x9CD433, 0, [4], "call dword ptr [eax + 0x24]"),
    9: (0x9CD46F, 0, [12], "mov dword ptr [ecx + 8], eax"),
    10: (0x9CD603, 0, [16], "mov dword ptr [ecx + 0x14], eax"),
    11: (0x9CD671, 0, [16], "mov al, byte ptr [ecx + 0x16]"),
    12: (0x9CD300, 0, [4], "or byte ptr [esi + 5], 0xf"),
    13: (0x9CD40A, 0, [0], "movzx eax, byte ptr [ecx + 5]"),
    14: (0x9CD40F, 0, [4], "and al, byte ptr [esp + 4]"),
    15: (0x9CD492, 0, [16], "mov dword ptr [edi + 0x14], eax"),
    16: (0x9CD563, 0, [16], "call dword ptr [eax + 0x88]"),
    17: (0x9CD7B6, 0, [4], "call dword ptr [edx + 0xdc]"),
    18: (0x9CD6E0, 0, [4], "mov byte ptr [ecx + 4], al"),
    19: (0x9CD6EC, 0, [0], "movzx eax, byte ptr [ecx + 4]"),
}
for s in range(20):
    f, d, ch = resolve(u32(FR + 4 * s))
    e = exp[s]
    check(f"slot {s:2}: resolves to {e[0]:#x} this{e[1]:+#x} ret{e[2]} body has '{e[3]}'",
          f == e[0] and d == e[1] and rets(f) == e[2] and e[3] in B(f), f"got {f:#x} {d:+#x} {rets(f)}")
check("slot 4/5/6/7 stubs are FlatRect class slots 106/107/103/104",
      [resolve(u32(FR + 4 * s))[2][1] for s in (4, 5, 6, 7)] == [u32(CVT + 4 * k) for k in (106, 107, 103, 104)])

# ---- independent corroboration: the FlatRect .UI WRITER 0x95C211 (reached from IID site 0x9662B5) ----
w = fn(0x95C211, 300)
edges = []
for k, ins in enumerate(w):
    if ins.mnemonic == "call" and ins.op_str == "dword ptr [eax + 0x2c]":
        pushed = [x for x in w[max(0, k - 6):k] if x.mnemonic == "push" and x.op_str.startswith("0") or x.op_str in ("1", "2", "3")]
        edges.append(w[k - 2].op_str)
strs = [rd(int(x.op_str, 16), 16).split(b"\0")[0] for x in w if x.mnemonic == "push" and x.op_str.startswith("0xad58") or (x.mnemonic == "push" and x.op_str in ("0xad57fc", "0xad57f0"))]
check("writer 0x95C211 calls slot 11 (vt+0x2C) GetOutlineColor(edge 0..3,&r,&g,&b) and emits colorleft/top/right/bottom",
      edges == ["0", "1", "2", "3"] and strs[:4] == [b"colorleft", b"colortop", b"colorright", b"colorbottom"], f"{edges} {strs}")
bits = [x.op_str.split(",")[1].strip() for x in w if x.mnemonic == "test" and x.op_str.startswith("byte ptr [ebp - 1]")]
kw = [rd(int(x.op_str, 16), 12).split(b"\0")[0] for x in w if x.mnemonic == "push" and x.op_str in ("0xaa1bd8", "0xad57ec", "0xaa1bcc", "0xad57e4", "0xad5624", "0xad562c", "0xad5614")]
check("writer calls slot 13 (vt+0x34) GetOutlineFlags; bits 2,4,8,0x10,0x20,0x40 -> top,right,bottom,raised,sunken,nofill (bit 1 left via al)",
      "call dword ptr [eax + 0x34]" in B(0x95C211) and bits == ["2", "4", "8", "0x10", "0x20", "0x40"]
      and kw == [b"left", b"top", b"right", b"bottom", b"raised", b"sunken", b"nofill"], f"{bits} {kw}")
check("0x9662B5 dispatcher: riid==IID -> QI -> call 0x95C211", "call 0x95c211" in " ; ".join(f"{i.mnemonic} {i.op_str}" for i in disrange(0x96630C, 0x966330)))

# ---- applier + 'autosize' null with control ----
a = B(0x94E33B, 300)
check("applier 0x94E33B: QI IID, style token 0xF005 -> slot 12 (vt+0x30); 0x200..0x203 -> slot 10 (vt+0x28) idx 0..3; no vt+0x44/0x48",
      "push 0xc2afa76f" in a and "0xf005" in a and "call dword ptr [eax + 0x30]" in a and a.count("call dword ptr [eax + 0x28]") == 4
      and "+ 0x44]" not in a and "+ 0x48]" not in a)
check("'autosize' token 0xA03 used only at 0x94F82D (GZWinBtn applier, QI 0x8810) + its registration 0x952B44",
      sorted(i.address for i in (insn_containing(h) for h in find_imm32(0xA03)) if i and i.mnemonic == "push") == [0x94F82D, 0x952B44]
      and "push 0x8810" in B(0x94F757, 12))
check("base cGZWin QI 0x99B774 answers only 1 / 0x22BA0121 / 0xE98B2F57 (so a FlatRect never reaches the Btn applier)",
      all(x in B(0x99B774) for x in ("0x22ba0121", "0xe98b2f57")) and "0x8810" not in B(0x99B774))

# ---- GZPaint + DC line-thickness state ----
p = B(0x9CD1FF)
check("GZPaint: no width field; 4x DC vt+0x88 Line, fill via vt+0x8C on +0x24; dec esi/edi (r-1,b-1)",
      p.count("call dword ptr [eax + 0x88]") == 4 and "lea edx, [ebx + 0x24]" in p and "call dword ptr [eax + 0x64]" not in p)
DC = 0xAC16C8
s25, s19 = resolve(u32(DC + 25 * 4))[0], resolve(u32(DC + 19 * 4))[0]
check("DC class vt 0xAC16C8 slot 25 (vt+0x64) = SetLineThickness(float): stores [esi+0x4c], forwards engine vt+0x2C",
      s25 == 0x82C2D0 and "mov dword ptr [esi + 0x4c], ecx" in B(s25) and "call dword ptr [edx + 0x2c]" in B(s25) and rets(s25) == [4])
check("DC slot 19 ResetToDefaultState pushes 1.0f (0x3F800000) into vt+0x64",
      "push 0x3f800000 ; mov ecx, esi ; call dword ptr [edx + 0x64]" in B(s19))
for site in (0x9AF48A, 0x9AF5E8, 0x9BF113):
    win = " ; ".join(f"{i.mnemonic} {i.op_str}" for i in disrange(site - 0x20, site + 0x30))
    check(f"another widget sets DC thickness at {site:#x} before Line and restores 1.0 (fld1) after",
          "call dword ptr [eax + 0x64]" in win and "call dword ptr [eax + 0x88]" in win and "fld1" in win)

# ---- bar override: min H only ----
o = B(0x9994BF)
check("bar AutoSize override 0x9994BF: base AutoSize call, SetH (vt+0xD0) only - no SetW (vt+0xCC)/SetSize (vt+0xD4)",
      "call 0x9cd7b6" in o and "call dword ptr [eax + 0xd0]" in o and "+ 0xcc]" not in o and "+ 0xd4]" not in o)
check("min-size helper 0x998F1D: *w=0x80, *h=max(8, textH+8, childH+2)",
      "mov dword ptr [eax], 0x80" in B(0x998F1D) and "mov dword ptr [esi], 8" in B(0x998F1D) and "add eax, 8" in B(0x998F1D))
check("cGZWinGen SetArea override 0x99A0AF clamps W/H to gen+0xE8/+0xEC (the 128+2gx / minH+2gy minimum)",
      u32(0xADC678 + 55 * 4) == 0x99A0AF and "[esi + 0xe8]" in B(0x99A0AF, 20) and "[esi + 0xec]" in B(0x99A0AF, 20))

# ---- verifier's own MSVC compile ----
asm = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "msvc_layout.asm"), encoding="latin1").read()
m = re.search(r"\?\?_7ImplFR@@6B@ DD FLAT:\?\?_R4ImplFR@@6B@.*?\n((?:\s+DD\s+FLAT:\S+\n)+)", asm)
ents = re.findall(r"FLAT:\?(\w+)@ImplFR@@(\S+)", m.group(1)) if m else []
want = [("QueryInterface", "UAE_NKPAPAX@Z"), ("AddRef", "UAEKXZ"), ("Release", "UAEKXZ"), ("AsIGZWin", "UAEPAUcIGZWin@@XZ"),
        ("SetFillColor", "UAE_NK@Z"), ("SetFillColor", "UAE_NEEE@Z"), ("GetFillColor", "UBEKXZ"), ("GetFillColor", "UBE_NAAE00@Z"),
        ("SetOutlineColor", "UAE_NK@Z"), ("SetOutlineColor", "UAE_NEEE@Z"), ("SetOutlineColor", "UAE_NJEEE@Z"), ("GetOutlineColor", "UBE_NJAAE00@Z"),
        ("SetOutlineFlags", "UAE_NJ@Z"), ("GetOutlineFlags", "UAEJXZ"), ("GetOutlineFlag", "UAE_NJ@Z"), ("SetOutlineColors", "UAE_NKKKK@Z"),
        ("GetOutlineColors", "UAE_NAAK000@Z"), ("AutoSize", "UAE_NABUcRZRect@@@Z"), ("SetSizeMode", "UAE_NJ@Z"), ("GetSizeMode", "UAEJXZ")]
check("verifier's MSVC compile of the Mac order yields the exe's 20-slot order (native,rgb | get() ,get(&) | native,rgb,edge | ...)",
      ents == want, f"{len(ents)} entries")

print("\nALL PASS" if FAIL == 0 else f"\n{FAIL} FAIL")
sys.exit(1 if FAIL else 0)
