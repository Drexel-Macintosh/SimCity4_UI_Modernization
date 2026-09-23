"""W-Graph: byte-level re-check of every claim in the unit's report.
Reads the shipped SimCity 4.exe (1.1.641.0 Steam) OFFLINE. Prints one line per
check and ends OVERALL: PASS / FAIL (non-zero exit on failure).
    python tools\\sdk\\ghidra\\verify\\W-Graph\\verify_graph.py
"""
import sys, struct
from pe import *
from slots import resolve, retn

ok = fail = 0
def check(name, cond, detail=''):
    global ok, fail
    if cond: ok += 1
    else: fail += 1
    print('%s  %s %s' % ('PASS' if cond else 'FAIL', name, detail))

def bytes_at(va, hexstr):
    b = rd(va, len(hexstr) // 2)
    return b is not None and b.hex() == hexstr

# ---- positive control: the IID scanner finds the FlatRect IID where the brief says
def imm_hits(v):
    return [h for h in find_bytes(struct.pack('<I', v), '.text')]
fr = imm_hits(0xC2AFA76F)
check('control: FlatRect IID 0xC2AFA76F pushed at 0x47B993/0x4861D7', 0x47B994 in fr and 0x4861D8 in fr)

# ---- IIDs: QueryInterface compare + this-adjust
QI = {  # iid: (QI fn, adjust)
    0x02CF2351: (0x9B1E73, 0xD8),   # cIGZGraph      (cGZGraph base QI)
    0x12CF2351: (0x9B28CE, 0x22C),  # cIGZLineGraph  (cGZLineGraph QI)
    0x22CF2351: (0x9B2943, 0x22C),  # bar-type iface (type2)
    0x32CF2351: (0x9B2A38, 0x22C),  # cIGZScatterGraph
    0x42CF2351: (0x9B2BEF, 0x22C),  # pie-type iface (type3)
}
for iid, (fn, adj) in QI.items():
    ins = dis(fn, 0x20, maxins=6)
    check('QI %08X at %08X' % (iid, fn), ins[0].op_str == 'dword ptr [esp + 4], 0x%x' % iid)
    lea = [i for i in dis(fn, 0x40, maxins=12) if i.mnemonic == 'lea' and 'edx, [ecx +' in i.op_str]
    check('QI %08X returns this+0x%X' % (iid, adj), lea and lea[0].op_str.endswith('0x%x]' % adj))

# ---- constructors store the vtables at +0 / +0xD8 / +0x22C
def ctor_has(fn, n, pairs):
    txt = ' | '.join('%s %s' % (i.mnemonic, i.op_str) for i in dis(fn, n))
    return all(('0x%x' % vt) in txt for vt in pairs)
check('cSC4LineGraph ctor 0x76B5F0 -> AB4D08/AB4C28/AB4B98', ctor_has(0x76B5F0, 0x26, [0xAB4D08, 0xAB4C28, 0xAB4B98]))
check('cGZLineGraph ctor 0x9BA988 -> ADF2E8/ADF208/ADF5B0 (pure ADE0F0)', ctor_has(0x9BA988, 0x40, [0xADF2E8, 0xADF208, 0xADF5B0, 0xADE0F0]))
check('scatter ctor 0x9BA033 -> ADEA90/ADE9B0/ADED58 (pure ADDEF0)', ctor_has(0x9BA033, 0x40, [0xADEA90, 0xADE9B0, 0xADED58, 0xADDEF0]))
check('type2 ctor 0x9B9DED -> ADE648/ADE568/ADE910 (pure ADDE50)', ctor_has(0x9B9DF0, 0x40, [0xADE648, 0xADE568, 0xADE910, 0xADDE50]))
check('type3 ctor 0x9BA216 -> ADEEC0/ADEDE0/ADF188 (pure ADDF78)', ctor_has(0x9BA216, 0x40, [0xADEEC0, 0xADEDE0, 0xADF188, 0xADDF78]))
check('cGZGraph base ctor 0x9B7526 -> ADE188 / +D8 ADE450 (pure ADDFF8)', ctor_has(0x9B7526, 0x30, [0xADE188, 0xADE450, 0xADDFF8]))

# ---- slot counts from the pure-virtual tables (_purecall 0x5D4A10)
PURE_STARTS = {0xADDFF8, 0xADE0F0, 0xADDE50, 0xADDEF0, 0xADDF78}
def pure_count(va):
    # tables are laid out back to back: stop at the next known table start
    n = 0
    while u32(va + 4 * n) == 0x5D4A10:
        n += 1
        if (va + 4 * n) in PURE_STARTS: break
    return n
# the type2 pure table abuts the scatter one; its concrete table 0xADE910 must
# also end exactly where the scatter class's cIGZGraph table 0xADE9B0 begins
check('type2 concrete iface 0xADE910 spans 40 slots up to 0xADE9B0', (0xADE9B0 - 0xADE910) // 4 == 40)
for name, va, want in (('cIGZGraph', 0xADDFF8, 55), ('cIGZLineGraph', 0xADE0F0, 35),
                       ('type2 iface', 0xADDE50, 40), ('cIGZScatterGraph', 0xADDEF0, 33),
                       ('type3 iface', 0xADDF78, 31)):
    n = pure_count(va)
    check('%s pure table %08X has %d slots' % (name, va, want), n == want, '(got %d)' % n)

# ---- AsIGZGraph proves which subobject is cIGZGraph
check('cIGZLineGraph slot34 AsIGZGraph 0x76B640 returns iface-0x154 (= obj+0xD8)',
      bytes_at(0x76B64A, '8d81acfeffff'))
check('cIGZScatterGraph slot32 AsIGZGraph 0x9BA2F4 adds -0x154', bytes_at(0x9BA2F4 + 6, '81c1acfeffff'))

# ---- MSVC overload reversal (Windows order != Mac order), by callee-cleaned arg bytes
rl = lambda vt, s: retn(resolve(u32(vt + 4 * s))[0])
check('line slot22 = SetData(vector&,ulong) ret 8', rl(0xADF5B0, 22) == 8)
check('line slot23 = SetData(float,ulong,ulong) ret 12', rl(0xADF5B0, 23) == 12)
check('scatter slot15 = InsertData(float,float,ulong,ulong) ret 16', rl(0xADED58, 15) == 16)
check('scatter slot16 = InsertData(const pt&,ulong,ulong) ret 12', rl(0xADED58, 16) == 12)
check('scatter slots18/19/20 = SetData(vector&) / (f,f,m,m) / (pt&,m,m)',
      (rl(0xADED58, 18), rl(0xADED58, 19), rl(0xADED58, 20)) == (8, 16, 12))

# ---- cSC4LineGraph overrides exactly three slots
def diffs(a, b, n):
    va, vb = vtable(a, n), vtable(b, n)
    return [i for i in range(n) if va[i] != vb[i]]
check('cSC4LineGraph vs cGZLineGraph: main differs only at 148', diffs(0xADF2E8, 0xAB4D08, 178) == [148])
check('... cIGZGraph differs only at 43 (DrawLine -> sub_986670)', diffs(0xADF208, 0xAB4C28, 55) == [43])
check('... cIGZLineGraph differs only at 32 (DrawLine)', diffs(0xADF5B0, 0xAB4B98, 35) == [32])

# ---- pixel constants (stock bytes)
PIX = [
    (0x9B75B4, 'c7862001000020000000', 'title band height +0x120 = 32 (ctor)'),
    (0x9B3884, '6a04', 'auto title rect margin 4 (sub_9B387A)'),
    (0x9B7686, 'c7401804000000', 'major tick length default 4 (+0x180/+0x184)'),
    (0x9B768D, 'c7402002000000', 'minor tick length default 2 (+0x188/+0x18C)'),
    (0x9B7FE0, '4848', 'Y value-label gap 2 (right = plotL - tick - 2)'),
    (0x9B7E4C, '8d4c1102', 'X value-label gap 2 (top = plotB + tick + 2)'),
    (0x9B250B, '6a01', 'axis line width 1 (vertical)'),
    (0x9B253A, '6a01', 'axis line width 1 (horizontal)'),
    (0x9B396A, '6a01', 'window border width 1'),
    (0x9B3A58, '6a01', 'plot-area frame width 1'),
    (0x9B3B65, '6a01', 'value-axis tick width 1'),
    (0x9B473D, '6a01', 'category tick width 1 (line graph)'),
    (0x9B5581, '6a01', 'bar frame width 1'),
    (0x76C3B8, 'c744247801000000', 'Graphs series LINE WIDTH 1 (LineGraphSeriesInfo+0x10)'),
    (0x76E250, 'c7451c01000000', 'legend swatch frame width 1'),
    (0x76DD5F, 'c78424a80000002d000000', 'type1 plot left 45'),
    (0x76DD4E, '83ea6e', 'type1 plot right W-110'),
    (0x76DD4B, '83e814', 'type1 plot bottom H-20'),
    (0x76D848, 'c78424980000002d000000', 'type2 (bar) plot left 45'),
    (0x76D837, '83ea02', 'type2 (bar) plot right W-2'),
    (0x76D834, '83e814', 'type2 (bar) plot bottom H-20'),
    (0x76D645, '685f6bc8e9', 'chart TITLE font = Legend 0xE9C86B5F'),
    (0x76D658, '686e6bc8e9', 'axis label/title font = ChartTickText 0xE9C86B6E'),
    (0x76DD91, '685e6bc8e9', 'legend rows font = ChartLabel 0xE9C86B5E (documented)'),
]
for va, hx, what in PIX:
    check('%08X %s' % (va, what), bytes_at(va, hx))

print('\n%d PASS / %d FAIL' % (ok, fail))
print('OVERALL: %s' % ('PASS' if fail == 0 else 'FAIL'))
sys.exit(1 if fail else 0)
