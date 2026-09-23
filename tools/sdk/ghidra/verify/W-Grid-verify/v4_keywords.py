# W-Grid-verify step 4: keyword registration (0x95B021..ret) -> token/name table; then annotate the
# IGZWinGrid deserializer 0x95A250 with token names and grid-vtable slot names (Mac names; call [reg+disp]).
import json
from vpe import PE
pe = PE()

MAC = {}
MACW = {}
d = json.load(open(r'C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json', encoding='utf-8'))
for t in d['types']:
    if t['name'] == 'vftable_cIGZWinGrid':
        for f in t['fields']:
            MAC[f['off']//4] = f['name']
    if t['name'] == 'vftable_cIGZWin':
        for f in t['fields']:
            MACW[f['off']//4] = f['name']

# --- registration walk
ins = pe.dis(0x95B021, 5000, stop_at_ret=True)
print('registration fn 0x95B021 .. 0x%X (%d insns)' % (ins[-1].address, len(ins)))
pairs = []
prev = None
names = {}
for i in ins:
    if i.mnemonic == 'push' and prev is not None and prev.mnemonic in ('push',) :
        try:
            a = int(prev.op_str, 0); b = int(i.op_str, 0)
        except ValueError:
            a = b = None
        if b is not None and pe.sec_of(b) and pe.sec_of(b)[0] == '.rdata':
            nm = pe.cstr(b, 64)
            pairs.append((prev.address, a, nm))
    if i.mnemonic == 'push' and prev is not None and prev.mnemonic == 'mov' and prev.op_str.startswith('edi, 0x'):
        pass
    prev = i
for a, tok, nm in pairs:
    names[tok] = nm
    print('  %08X token=%s name=%r' % (a, hex(tok), nm))
print('pairs:', len(pairs), ' tokens in 0x1601..0x16FF:', len([p for p in pairs if 0x1600 < p[1] < 0x1700]))
json.dump({hex(k): v for k, v in names.items()}, open('v4_tokens.json', 'w'), indent=1)

# --- deserializer annotate
out = []
ins = pe.dis(0x95A250, 3000, stop_at_ret=False)
for i in ins:
    if i.address >= 0x95B021: break
    note = ''
    if i.mnemonic == 'push':
        try:
            v = int(i.op_str, 0)
            if v in names: note = '   ; token ' + names[v]
            elif pe.sec_of(v) and pe.sec_of(v)[0] in ('.rdata',) and 0xA80000 <= v < 0xB07000:
                s = pe.cstr(v, 40)
                if s and all(32 <= ord(c) < 127 for c in s): note = '   ; str %r' % s
        except ValueError:
            pass
    if i.mnemonic == 'call' and i.op_str.startswith('dword ptr [') and '+' in i.op_str:
        disp = int(i.op_str.split('+')[-1].strip(' ]'), 0)
        note = '   ; grid slot %d %s | IGZWin slot %d %s' % (disp//4, MAC.get(disp//4), disp//4, MACW.get(disp//4))
    out.append('%08X: %-30s %s%s' % (i.address, i.mnemonic + ' ' + i.op_str, '', note))
open('v4_deser.txt', 'w').write('\n'.join(out))
print('wrote v4_deser.txt', len(out))
