# W-Grid-verify step 8: re-read the finder's listed call sites; print the call and the pushes feeding it.
import json
from vpe import PE
pe = PE()
MAC = {}; MACW = {}
d = json.load(open(r'C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json', encoding='utf-8'))
for t in d['types']:
    if t['name'] == 'vftable_cIGZWinGrid':
        for f in t['fields']: MAC[f['off']//4] = f['name']
    if t['name'] == 'vftable_cIGZWin':
        for f in t['fields']: MACW[f['off']//4] = f['name']

SITES = [0x9A2091, 0x9A2312, 0x9A484C, 0x9A4946, 0x9A495D, 0x9A4AA1, 0x9A2111,
         0x4BF0B1, 0x4BF0C4, 0x4BF4B1, 0x4BF4C4,
         0x8B0EAF, 0x8B0EC5, 0x8B0ECC, 0x8B0F78, 0x8B2F86, 0x8B2FAB,
         0x5FA094, 0x5FA240, 0x5FA273,
         0x68A01E, 0x68A031, 0x6875A4, 0x684EC3, 0x47AD20]

def insn_at_or_after(va):
    for s in range(va - 0x30, va + 1):
        ins = pe.dis(s, 40, False)
        addrs = [i.address for i in ins]
        if va in addrs:
            return ins, addrs.index(va)
    return None, None

for site in SITES:
    ins, k = insn_at_or_after(site)
    if ins is None:
        # site might be the push of a call; search forward for the next call
        print('==== %X : no sync' % site); continue
    # find the call at or after site
    j = k
    while j < len(ins) and ins[j].mnemonic != 'call':
        j += 1
    if j >= len(ins):
        print('==== %X : no call after' % site); continue
    call = ins[j]
    lo = max(0, j - 9)
    print('==== site %X -> call at %X' % (site, call.address))
    for i in ins[lo:j+1]:
        note = ''
        if i.mnemonic == 'call' and i.op_str.startswith('dword ptr [') and '+' in i.op_str:
            disp = int(i.op_str.split('+')[-1].strip(' ]'), 0)
            note = '   ; grid %d %s | win %d %s' % (disp//4, MAC.get(disp//4), disp//4, MACW.get(disp//4))
        print('   %08X: %s %s%s' % (i.address, i.mnemonic, i.op_str, note))

print('==== static rects')
for va in (0xB17B2C, 0xB17B4C):
    print(hex(va), [pe.i32(va + 4*i) for i in range(4)])
