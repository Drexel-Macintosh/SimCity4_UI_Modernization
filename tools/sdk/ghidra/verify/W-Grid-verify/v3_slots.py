# W-Grid-verify step 3: every cIGZWinGrid slot VA from vtable 0xADD578 vs the finder's list; ret N per slot
# via recursive-descent walk (cfg.py), plus first instructions, written to v3_slots.txt
import json, re
from vpe import PE
from cfg import walk, fmt
pe = PE()

FINDER_VA = {0:0x9A5CB5,1:0x94D34F,2:0x9A7650,3:0x9AF121,4:0x9ABED4,5:0x9CFA36,6:0x9AFCCB,7:0x9A619F,8:0x9A76DA,9:0x9A7734,
10:0x9A6284,11:0x9A81BE,12:0x9A629F,13:0x9A62BC,14:0x9683E0,15:0x9A62F0,16:0x9A6333,17:0x9A633A,18:0x9A6357,19:0x9AC269,
20:0x9AC2E9,21:0x9A6376,22:0x9A63B4,23:0x9A63BF,24:0x9A63F4,25:0x9A642D,26:0x9A6462,27:0x9A648F,28:0x76B620,29:0x9A64B3,
30:0x9AA3E1,31:0x9AE48F,32:0x9AD817,33:0x9A64CB,34:0x9A64DB,35:0x9A64EE,36:0x9A6563,37:0x9A65D8,38:0x9A65FB,39:0x9A6618,
40:0x9A96FD,41:0x9A9711,42:0x9A87DC,43:0x9A9765,44:0x9AA477,45:0x9A8809,46:0x9A8869,47:0x9A6639,48:0x9A667E,49:0x9A6697,
50:0x9A97CE,51:0x9A66B4,52:0x9A66FC,53:0x9A6722,54:0x9A6748,55:0x9A6778,56:0x9A679D,57:0x9A67B1,58:0x9A67DE,59:0x5F8AC0,
60:0x9A6814,61:0x9AC369,62:0x9AC3D2,63:0x423850,64:0x9A6823,65:0x9AC43B,66:0x9A6830,67:0x9AC4AA,68:0x459870,69:0x472E70,
70:0x9AE35C,71:0x9AF0F6,72:0x9A683D,73:0x9A68E2,74:0x9A6986,75:0x9A69B7,76:0x9A69D4,77:0x9A69F9,78:0x9AD986,79:0x9AD9B3,
80:0x9AD931,81:0x9AD95E,82:0x9AB87B,83:0x9AB889,84:0x9AA5CE,85:0x9AC519,86:0x9AB8FE,87:0x9AA7E3,88:0x9AA7FB,89:0x9A6C14,
90:0x9AC741,91:0x9AC866,92:0x9AC960,93:0x9ACA52,94:0x9ACB56,95:0x9AA59C,96:0x9AB897,97:0x9A6A39,98:0x9A6AF1,99:0x938789,
100:0x9AE5AC,101:0x9AE6DF,102:0x9AD9DB,103:0x9ADB72,104:0x9A6B50,105:0x9AFC65,106:0x9AE813,107:0x9A6BA5,108:0x9A6BC2,109:0x9A6BF7,
110:0x9A7C69,111:0x9AA813,112:0x9AE8CB,113:0x9AA8AA,114:0x9AEB66,115:0x9AA8E2,116:0x9AECB7,117:0x9A8F16,118:0x9ADD09,119:0x9ACE2F,
120:0x9AAAD1,121:0x9AB198,122:0x9AB1DC,123:0x9AB1FA,124:0x9AB23E,125:0x9A6D2D,126:0x9A6D43,127:0x9A6D4A,128:0x9A6D87,129:0x9A6E0F,
130:0x9A6E22,131:0x9ACED6,132:0x9AD1E8,133:0x9A9892,134:0x9A6E90,135:0x9A6EBD,136:0x9A6EF7,137:0x9A6F67,138:0x9A6EDA,139:0x9A5F70,
140:0x9A5F99,141:0x9A824E}

FINDER_RET = {0:8,1:0,2:0,3:0,5:0,6:0,7:0x10,8:4,9:4,10:4,11:4,12:4,13:4,14:0,15:4,16:0,17:8,18:8,19:16,20:16,21:4,22:0,23:16,24:16,
25:16,26:16,27:8,28:0,29:4,30:12,31:4,32:4,33:4,34:4,35:4,36:4,37:8,38:8,39:8,40:0,41:8,42:8,43:8,44:12,45:8,46:0,47:8,48:8,49:8,
50:4,51:4,52:4,53:4,54:8,55:8,56:4,57:4,58:8,59:8,60:4,61:12,62:12,63:0,64:4,65:12,66:4,67:12,68:0,69:0,70:8,71:8,72:8,73:8,74:8,
75:8,76:8,77:4,78:8,79:8,80:8,81:8,82:0,83:0,84:12,85:12,86:8,87:8,88:8,89:12,90:12,91:16,92:12,93:16,94:16,95:12,96:8,97:16,98:0,
99:16,100:12,101:12,102:16,103:16,104:8,105:8,106:12,107:8,108:8,109:8,110:16,111:12,112:24,113:12,114:16,115:12,116:24,117:16,
118:8,119:12,120:8,121:8,122:4,123:8,124:4,125:4,126:0,127:16,128:12,129:8,130:4,131:16,132:16,133:0x24,134:4,135:8,136:8,137:8,
138:8,139:0,140:4,141:4}

MAC = {}
d = json.load(open(r'C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json', encoding='utf-8'))
for t in d['types']:
    if t['name'] == 'vftable_cIGZWinGrid':
        for f in t['fields']:
            MAC[f['off']//4] = f['name']

VT = 0xADD578
mism_va = []
mism_ret = []
lines = []
for s in range(142):
    va = pe.u32(VT + 4*s)
    r = walk(pe, va)
    rets = r['rets']
    fv = FINDER_VA.get(s)
    fr = FINDER_RET.get(s)
    if fv != va:
        mism_va.append((s, hex(va), hex(fv) if fv else None))
    ok_ret = (fr is None) or (rets == [fr])
    if not ok_ret:
        mism_ret.append((s, rets, fr, [hex(t) for t in r['tails']], r['indirect']))
    lines.append('#### slot %d (vt+0x%X) mac=%s  VA=%s  finderVA=%s  rets=%s finderRet=%s tails=%s ind=%s' % (
        s, s*4, MAC.get(s), hex(va), hex(fv) if fv else None, rets, fr, [hex(t) for t in r['tails']], r['indirect']))
    lines.append(fmt(r, 70))
open('v3_slots.txt', 'w').write('\n'.join(lines))
print('VA mismatches:', mism_va)
print('ret mismatches (slot, measured rets, finder ret, tails, indirect):')
for m in mism_ret:
    print('  ', m)
