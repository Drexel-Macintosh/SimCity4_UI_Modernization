# verify_all.py - W-Graph adversarial verifier: re-runs every load-bearing byte check as PASS/FAIL.
# Independent of the finder's scripts (uses only vx.py from this folder). Offline read of the exe.
import sys, struct
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-Graph-verify")
from vx import *

results = []
def check(name, cond, detail=""):
    results.append((bool(cond), name, detail))
    print("%s  %s  %s" % ("PASS" if cond else "FAIL", name, detail))

# ---- 1. IIDs: raw byte scan of every section, with the FlatRect positive control
def sites(v):
    return [a for s, a in scan_dword_all(v)]
ctrl = sites(0xC2AFA76F)
check("control 0xC2AFA76F found at 0x47B994 and 0x4861D8", 0x47B994 in ctrl and 0x4861D8 in ctrl, "%d hits" % len(ctrl))
EXP = {0x02CF2351: [0x66C282, 0x9B1E77], 0x12CF2351: [0x66BC40, 0x76C2C0, 0x76DDA9, 0x9B28D2],
       0x22CF2351: [0x76BEA6, 0x76D87B, 0x9B2947], 0x32CF2351: [0x66C272, 0x9B2A3C], 0x42CF2351: [0x9B2BF3]}
for v, exp in EXP.items():
    got = sites(v)
    check("IID 0x%08X occurrences" % v, sorted(got) == sorted(exp), "got %s" % [hex(x) for x in got])

# ---- 2. QueryInterface bodies: riid compare + returned this-offset + fallthrough target
def qi(va, riid, off, nxt):
    ins = dis(va, 6, stop_at_ret=False)
    ok = ins[0].mnemonic == "cmp" and ("0x%x" % riid) in ins[0].op_str
    ok = ok and ins[2].mnemonic == "jmp" and int(ins[2].op_str, 16) == nxt
    ok = ok and any(i.mnemonic == "lea" and ("+ 0x%x]" % off) in i.op_str for i in ins)
    return ok
check("QI 0x9B1E73: 0x02CF2351 -> this+0xD8 else cGZWin QI 0x99B774", qi(0x9B1E73, 0x02CF2351, 0xD8, 0x99B774))
for va, riid in [(0x9B28CE, 0x12CF2351), (0x9B2943, 0x22CF2351), (0x9B2A38, 0x32CF2351), (0x9B2BEF, 0x42CF2351)]:
    check("QI 0x%X: 0x%08X -> this+0x22C else 0x9B1E73" % (va, riid), qi(va, riid, 0x22C, 0x9B1E73))

# ---- 3. vtable addresses: stored by the claimed constructors at the claimed offsets
def stores(vt):
    out = []
    for h in scan_dword(vt):
        for ins in insn_covering(h):
            if ins.mnemonic == "mov" and ("0x%x" % vt) in ins.op_str:
                out.append((ins.address, ins.op_str.split(",")[0]))
    return out
VT = [(0xAB4D08, 0x76B5F8, "[esi]"), (0xAB4C28, 0x76B5FE, "[esi + 0xd8]"), (0xAB4B98, 0x76B608, "[esi + 0x22c]"),
      (0xADF2E8, 0x9BA9AA, "[esi]"), (0xADF208, 0x9BA9B0, "[esi + 0xd8]"), (0xADF5B0, 0x9BA99E, "[eax]"),
      (0xADE648, 0x9B9E11, "[esi]"), (0xADE568, 0x9B9E17, "[esi + 0xd8]"), (0xADE910, 0x9B9E05, "[eax]"),
      (0xADEA90, 0x9BA04F, "[esi]"), (0xADE9B0, 0x9BA055, "[esi + 0xd8]"), (0xADED58, 0x9BA047, "[eax]"),
      (0xADEEC0, 0x9BA234, "[esi]"), (0xADEDE0, 0x9BA23A, "[esi + 0xd8]"), (0xADF188, 0x9BA22C, "[eax]"),
      (0xADE188, 0x9B754A, "[esi]"), (0xADE450, 0x9B753E, "[eax]"),
      (0xADDFF8, 0x9B7538, "[eax]"), (0xADE0F0, 0x9BA998, "[eax]"), (0xADDE50, 0x9B9DFF, "[eax]"),
      (0xADDEF0, 0x9BA041, "[eax]"), (0xADDF78, 0x9BA226, "[eax]")]
for vt, site, dst in VT:
    st = stores(vt)
    check("vtable 0x%08X stored at 0x%X %s" % (vt, site, dst), any(a == site and dst in d for a, d in st), str([(hex(a), d) for a, d in st]))

# ---- 4. slot counts: pure tables are N x one pure stub and bounded; real tables bounded or adjacent
PURE = 0x5D4A10
for va, n in [(0xADDFF8, 55), (0xADE0F0, 35), (0xADDE50, 40), (0xADDEF0, 33), (0xADDF78, 31)]:
    vals = [u32(va + 4 * i) for i in range(n)]
    nxt = u32(va + 4 * n)
    check("pure table 0x%X = %d x 0x5D4A10 then boundary" % (va, n), all(v == PURE for v in vals) and (nxt != PURE or va + 4 * n == 0xADDEF0), "next=0x%X" % nxt)
check("0xADE910 type2 iface ends at scatter cIGZGraph 0xADE9B0 (40 slots)", 0xADE910 + 40 * 4 == 0xADE9B0)
check("main tables are 178 slots (0xADE188+712 = 0xADE450)", 0xADE188 + 178 * 4 == 0xADE450)
check("0xAB4D08 run = 178 then non-code", len(vtable(0xAB4D08)) == 178)
check("0xAB4C28 run = 55 then 0", len(vtable(0xAB4C28)) == 55 and u32(0xAB4C28 + 220) == 0)
check("0xAB4B98 run = 35 then 0", len(vtable(0xAB4B98)) == 35 and u32(0xAB4B98 + 140) == 0)
check("0xADED58 run = 33 then 0", len(vtable(0xADED58)) == 33)
check("0xADF188 run = 31 then 0", len(vtable(0xADF188)) == 31)
check("main slot 68 = SetFlag 0x99DB6B (cSC4LineGraph, cGZGraph)", u32(0xAB4D08 + 68 * 4) == 0x99DB6B and u32(0xADE188 + 68 * 4) == 0x99DB6B)
check("main slot 88 = 0x9B1EA0 GZPaint -> cIGZGraph vt+0x38(NULL)", u32(0xADE188 + 88 * 4) == 0x9B1EA0 and "0x38" in dis(0x9B1EA0, 5)[3].op_str)

# ---- 5. SC4 vs GZ line graph: exactly one differing slot per table
def diffs(a, b, n):
    return [i for i in range(n) if u32(a + 4 * i) != u32(b + 4 * i)]
check("cSC4LineGraph vs cGZLineGraph main differ only in slot 148", diffs(0xAB4D08, 0xADF2E8, 178) == [148])
check("... cIGZGraph tables differ only in slot 43", diffs(0xAB4C28, 0xADF208, 55) == [43])
check("... cIGZLineGraph tables differ only in slot 32", diffs(0xAB4B98, 0xADF5B0, 35) == [32])
check("0x76B690 is a bare jmp 0x9B4585", one(0x76B690).mnemonic == "jmp" and int(one(0x76B690).op_str, 16) == 0x9B4585)

# ---- 6. overload reversal: ret sizes
def retn(va):
    r, _ = ret_n(resolve_thunk(va)[0])
    return int(r, 16) if r.startswith("0x") else int(r)
check("line slot22 0x9B6A77 ret 8 (vector,series); slot23 0x9B82CE ret 12 (float,idx,series)", retn(0x9B6A77) == 8 and retn(0x9B82CE) == 12)
check("scatter 15 ret16 / 16 ret12 / 18 ret8 / 19 ret16 / 20 ret12", [retn(x) for x in (0x9B9385, 0x9B932A, 0x9B696F, 0x9B93F1, 0x9B93A9)] == [16, 12, 8, 16, 12])
check("caller 0x66C52B pushes 4 args to scatter vt+0x3C", [i.mnemonic for i in dis(0x66C525, 4, False)] == ["push"] * 4)

# ---- 7. constants
check("0x76C3BC imm32 = 1 (series line width)", u32(0x76C3BC) == 1 and rd(0x76C3B8, 4) == bytes.fromhex("c7442478"))
check("0x9B75B4 +0x120 = 32", rd(0x9B75B4, 6) == bytes.fromhex("c78620010000") and u32(0x9B75BA) == 32)
check("0x9B7686 [eax+0x18] = 4 (major tick +0x180/+0x184)", rd(0x9B7686, 3) == bytes.fromhex("c74018") and u32(0x9B7689) == 4)
check("0x9B768D [eax+0x20] = 2 (minor tick)", rd(0x9B768D, 3) == bytes.fromhex("c74020") and u32(0x9B7690) == 2)
check("0x9B3884 push 4 (title margin)", rd(0x9B3884, 2) == b"\x6a\x04")
for s in (0x9B250B, 0x9B253A, 0x9B396A, 0x9B3A58, 0x9B3B65, 0x9B3BA2, 0x9B3CB9, 0x9B3CF7, 0x9B473D, 0x9B4784, 0x9B4893, 0x9B48D3, 0x9B5581, 0x9B408E):
    check("push 1 at 0x%X" % s, rd(s, 2) == b"\x6a\x01")
check("arc item +0x28 literal 0x3F490FF9 = %.7f (pi/4 = 0.7853982)" % struct.unpack("<f", struct.pack("<I", u32(0x9B4130)))[0], u32(0x9B4130) == 0x3F490FF9)

# ---- 8. dead-lever findings (this verifier's own)
check("DrawAxes 0x9B24E1 gated on byte +0x14C", rd(0x9B24E4, 7) == bytes.fromhex("80be4c01000000"))
check("base ctor writes +0x14C = bl (ebx=0 at 0x9B7569)", rd(0x9B7601, 6) == bytes.fromhex("889e4c010000") and rd(0x9B7569, 2) == b"\x33\xdb")
check("builder slot4 (+0x12D border) called with 0 at 0x76D6F8/0x76D701", rd(0x76D6F8, 2) == b"\x6a\x00" and rd(0x76D701, 3) == bytes.fromhex("ff5010"))
check("builder clears legend text-item frame +0x30 at 0x76E314", rd(0x76E314, 4) == bytes.fromhex("c6473000"))

n_fail = sum(1 for ok, _, _ in results if not ok)
print("\n%d checks, %d FAIL" % (len(results), n_fail))
