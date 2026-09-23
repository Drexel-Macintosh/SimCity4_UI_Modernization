# Rebuild the window-vtable population independently and count per-slot
# overrides against the cGZWin base vtable 0xADC8D8.
import struct, json
from v_pe import PE
p = PE()
BASE = 0xADC8D8
rd = [s for s in p.secs if s[0] == '.rdata'][0]
raw = p.data[rd[3]:rd[3]+rd[2]]

# 1) bare marker: slot 87 == 0x99BE4C
marker = []
for i in range(0, len(raw) - 3, 4):
    if struct.unpack_from('<I', raw, i)[0] == 0x99BE4C:
        marker.append(rd[1] + i - 87*4)
# 2) + [vt] and [vt+88*4] in code
m2 = [vt for vt in marker if p.is_code(p.u32(vt)) and p.is_code(p.u32(vt + 88*4))]
# 3) >=3 of 8 base markers (the wincensus.py detector's list)
MARK = {0xA0: 0x0099DFA9, 0xA4: 0x0099C81B, 0xA8: 0x0099C82A, 0xAC: 0x0099BC53,
        0xB0: 0x00994EE4, 0xC0: 0x0099BCE1, 0xF8: 0x0099C97C, 0x15C: 0x0099BE4C}
m3 = [vt for vt in m2 if sum(1 for o, v in MARK.items() if p.u32(vt + o) == v) >= 3]
print('bare marker', len(marker), ' +endpoints', len(m2), ' +>=3of8', len(m3))

wc = json.load(open(r'C:\dev\SC4UIScale\tools\uimap\_work\wincensus.json'))['windowVtables']
print('wincensus.json windowVtables', len(wc), ' same set as mine:', set(wc) == set(m3))
print('in mine not wc:', ['%08X' % v for v in sorted(set(m3) - set(wc))], ' in wc not mine:', ['%08X' % v for v in sorted(set(wc) - set(m3))])

pop = m3
def ovr(slot):
    b = p.u32(BASE + 4*slot)
    return sum(1 for vt in pop if vt != BASE and p.u32(vt + 4*slot) != b), sum(1 for vt in pop if vt == BASE)

CLAIM = {55: 50, 63: 1, 68: 12, 69: 3, 70: 1, 88: 93, 89: 1, 121: 17, 122: 1, 129: 10, 130: 57, 131: 48,
         132: 5, 133: 5, 134: 60, 135: 16, 136: 51, 137: 7, 138: 55, 139: 11, 140: 3, 141: 3, 142: 7,
         143: 33, 145: 2, 148: 108, 50: 0, 51: 0, 52: 0, 53: 0, 54: 0, 56: 0, 57: 0, 58: 0, 59: 0, 60: 0,
         118: 0, 119: 0, 120: 0, 123: 0, 124: 0, 125: 0, 126: 0, 127: 0, 128: 0, 144: 0, 146: 0, 147: 0,
         149: 0, 150: 0}
print('base vtable in population:', BASE in pop)
for s in sorted(CLAIM):
    n, bin_ = ovr(s)
    print('slot %3d overrides %3d / %d  claim %3d  %s' % (s, n, len(pop) - bin_, CLAIM[s], 'OK' if n == CLAIM[s] else 'DIFF'))
# which ones don't override 148?
b148 = p.u32(BASE + 148*4)
print('vtables NOT overriding 148:', ['%08X' % vt for vt in pop if p.u32(vt + 148*4) == b148])
# lengths: is every population vtable >= 151 slots?  (slot 148..150 present as code)
short = [('%08X' % vt) for vt in pop if not all(p.is_code(p.u32(vt + 4*k)) for k in range(151))]
print('population vtables with a non-code dword before slot 151:', short)
