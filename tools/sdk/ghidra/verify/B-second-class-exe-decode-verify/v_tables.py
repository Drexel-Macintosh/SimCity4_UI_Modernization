# Re-derive: (1) base DoMessage 0x99CCF0 jump table 0x99CEF9 (type -> slot),
# (2) GZ type -> Win32 WM_ table at 0x9DA71A / 0x9DA775, (3) ret-N arity of the
# base stubs used in slots 129-143, (4) exe slots 102-107 getter/setter grouping
# versus the Mac's interleaved order (MSVC overload-grouping check).
import re, json
from v_pe import PE
p = PE()
BASE = 0xADC8D8

print('== (1) DoMessage 0x99CCF0: msg type -> vtable slot')
for t in range(1, 21):
    tgt = p.u32(0x99CEF9 + 4*(t-1))
    call = None
    for i in p.dis(tgt, 0x40):
        if i.address == 0x99CEF0: break
        if i.mnemonic == 'call' and 'ptr [e' in i.op_str:
            m = re.search(r'\+ (0x[0-9a-f]+)\]', i.op_str); call = int(m.group(1), 16) if m else 0; break
    print('  type %2d -> %s' % (t, ('slot %d (vt+0x%X)' % (call//4, call)) if call is not None else 'returns false'))

print('== (2) 0x9DA71A: GZ type -> Win32 message')
names = {0x100: 'WM_KEYDOWN', 0x101: 'WM_KEYUP', 0x200: 'WM_MOUSEMOVE', 0x201: 'WM_LBUTTONDOWN', 0x202: 'WM_LBUTTONUP',
         0x204: 'WM_RBUTTONDOWN', 0x205: 'WM_RBUTTONUP', 0x20A: 'WM_MOUSEWHEEL', 0x700: '0x700 (private)'}
for k in range(11):
    t = p.u32(0x9DA775 + 4*k)
    ins = p.dis(t, 8, maxins=1)[0]
    v = None
    m = re.match(r'eax, (0x[0-9a-f]+)', ins.op_str)
    if ins.mnemonic == 'mov' and m: v = int(m.group(1), 16)
    print('  type %2d -> %s' % (k+5, names.get(v, 'none') if v else 'none (xor eax,eax)'))

print('== (3) arity of base slots 129-147 (ret N / 4)')
for s in range(118, 151):
    va = p.u32(BASE + 4*s)
    rets = [i for i in p.dis(va, 0x400) if i.mnemonic == 'ret']
    r = rets[0] if rets else None
    n = (int(r.op_str, 16) // 4) if (r and r.op_str) else 0
    print('  slot %3d %08X first ret: %s -> %d stack args' % (s, va, r.op_str if r and r.op_str else '(none)', n))

print('== (4) exe slots 102-107 vs Mac names')
mac = {t['name']: t for t in json.load(open(r'C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json'))['types'] if t['name'] == 'vftable_cIGZWin'}['vftable_cIGZWin']
macnames = {f['off']//4: f['name'] for f in mac['fields']}
for s in range(102, 108):
    va = p.u32(BASE + 4*s)
    body = p.dis_until_ret(va, 0x100)
    writes_d4 = any(i.mnemonic == 'mov' and i.op_str.startswith('dword ptr [ecx + 0xd4]') for i in body)
    calls107 = any('0x1ac]' in i.op_str for i in body)
    kind = 'SETTER' if (writes_d4 or calls107) else 'GETTER'
    print('  slot %d %08X exe=%s  mac=%s' % (s, va, kind, macnames[s]))
