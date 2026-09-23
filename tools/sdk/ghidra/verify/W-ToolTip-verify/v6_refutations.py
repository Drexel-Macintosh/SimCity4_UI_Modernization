# V6: re-runnable evidence for the verifier's refutations / corrections of the W-ToolTip finder.
import sys, struct
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-ToolTip-verify")
from vpe import PE
p = PE()
fails = 0
def check(cond, msg):
    global fails
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails += 1

def ins_at(va):
    return p.dis(va, 16, maxins=1)[0]

# R1. GZPaint 0x798710 is reached ONLY through class vt slot 88 (cGZWin vptr at obj+4) => ecx = obj+4.
check(p.u32(0xAB6770 + 88 * 4) == 0x798710, 'class vt 0xAB6770 slot 88 = 0x798710')
check(p.callers_rel32(0x798710) == [], 'no direct rel32 caller of 0x798710')
check([a for a, s in p.scan_dword(0x798710)] == [0xAB68D0], 'only dword ref of 0x798710 is the vtable slot')
check(p.u32(0xAB6770) == 0x799F30 and ins_at(0x799F30).op_str == 'ecx, 4' and ins_at(0x799F30).mnemonic == 'sub',
      'class slot 0 is a sub ecx,4 thunk => class vt lives at obj+4')
# R2. constraint rect = obj+0xDC..0xE8 LTRB (SetConstraintRect interface slot 19 writes [ecx+0xDC..0xE8])
s19 = p.u32(0xAB69D0 + 19 * 4)
txt19 = ' '.join('%s %s' % (i.mnemonic, i.op_str) for i in p.dis(s19, 0x68, maxins=30))
check('[ecx + 0xdc], edx' in txt19 and '[ecx + 0xe8], eax' in txt19, 'slot 19 writes obj+0xDC..0xE8')
# R3. GZPaint: ebx = -2*[esi+0x148] - [esi+0xDC] + [esi+0xE4]  (esi = obj+4) => obj+0xE8 - obj+0xE0 - 2*obj+0x14C
seq = [(0x79879E, 'mov', 'ebx, dword ptr [esi + 0x148]'), (0x7987A4, 'mov', 'ecx, dword ptr [esi + 0xdc]'),
       (0x7987AA, 'mov', 'edx, dword ptr [esi + 0xe4]'), (0x7987B2, 'neg', 'ebx'), (0x7987B4, 'shl', 'ebx, 1'),
       (0x7987B6, 'sub', 'ebx, ecx'), (0x7987B8, 'add', 'ebx, edx'), (0x798809, 'push', 'ebx'),
       (0x79880A, 'push', '0xfa'), (0x79883E, 'call', 'dword ptr [eax + 0xb4]')]
for va, mn, ops in seq:
    i = ins_at(va)
    check(i.mnemonic == mn and i.op_str == ops, '%08X %s %s' % (va, mn, ops))
print('  => with esi = obj+4: ebx = [obj+0xE8] (constraint.bottom) - [obj+0xE0] (constraint.top) - 2*[obj+0x14C] (padX)')
print('     pushed as the LAST (6th) arg of font vt+0xB4 after 250; i.e. CalculateTextArea(buf,len,rect,0,250,ebx)')
# R4. font vt+0xB4 (slot 45) implementation: 6-arg (ret 0x18); p6 clamped to >= GetLineHeight and divided by it
FVT = 0xAC55D8
f45 = p.u32(FVT + 45 * 4)
body = p.dis(f45, 0x160, maxins=120)
t = ['%s %s' % (i.mnemonic, i.op_str) for i in body]
check(any(x == 'call dword ptr [eax + 0x8c]' for x in t), 'slot45 calls vt+0x8C (GetLineHeight, Mac slot 35)')
check('cmp dword ptr [ebp + 0x1c], ebx' in t and 'mov dword ptr [ebp + 0x1c], ebx' in t,
      'p6 ([ebp+0x1C]) = max(p6, lineHeight)  -> p6 is a HEIGHT')
check('idiv ebx' in t, 'p6 / lineHeight -> max line count')
check('cmp eax, dword ptr [ebp + 0x18]' in t, 'CalculateWidthOfLines result compared with p5 ([ebp+0x18]) -> p5 is the max WIDTH (=250)')
check(any(i.mnemonic == 'ret' and i.op_str == '0x18' for i in p.dis(f45, 0x200, maxins=200)), 'slot45 ret 0x18 (6 args)')
check(p.u32(FVT + 46 * 4) != f45, 'slot46 is a different overload (5-arg)')
# R5. GZ tooltip class vt also overrides 62/121/122 with 'xor al,al; ret 8' (hit-test transparent)
for s in (62, 121, 122):
    g = p.u32(0xAE4398 + 4 * s); a = p.u32(0xAB5B48 + 4 * s)
    i2 = p.dis(g, 8, maxins=2)
    check(g == 0x93877E and a != g and i2[0].mnemonic == 'xor' and i2[1].op_str == '8',
          'GZ tip class slot %d = %08X (xor al,al; ret 8) vs AlertBorder %08X' % (s, g, a))
# R6. GZ layout 2px gap sites: 0x9DA3F9 / 0x9DA4B0 are not instruction starts; the inc pairs are at +1
layout_starts = set(i.address for i in p.dis(0x9DA106, 0x470, maxins=400))  # linear sweep from the fn entry
for claimed, real, reg in ((0x9DA3F9, 0x9DA3FA, 'edi'), (0x9DA4B0, 0x9DA4B1, 'esi')):
    starts = layout_starts
    check(claimed not in starts and real in starts and ins_at(real).mnemonic == 'inc' and ins_at(real).op_str == reg
          and ins_at(real + 1).mnemonic == 'inc', 'claimed %08X is mid-instruction; inc/inc %s at %08X' % (claimed, reg, real))
# R7. SC4 tip-mgr Init registers ids through msg-server vt+0x14 = slot 5 AddNotification (Mac/SDK: slot 4 = MessagePost)
check(ins_at(0x7E7CB8).op_str == 'dword ptr [eax + 0x14]', '0x7E7CB8 call [eax+0x14] (slot 5)')
check(ins_at(0x7E60A7).op_str == 'dword ptr [edx + 0x10]', 'tick poster 0x7E60A7 uses vt+0x10 (slot 4 MessagePost)')
# R8. extra Windows cIGZWinBtn slots sit at 51/52: 47/48/50 are thunks to cGZWin SetID/GetID/GetCaption
for s, tgt in ((47, 0x99BE5C), (48, 0x99BE66), (50, 0x99BE50)):
    f = p.u32(0xADDD50 + 4 * s); ii = p.dis(f, 12, maxins=2)
    check(ii[0].op_str == 'ecx, 4' and int(ii[1].op_str, 16) == tgt, 'btn iface slot %d thunk -> %08X' % (s, tgt))
check(p.u32(0xADDD50 + 53 * 4) == 0xFF7FFFFF, 'btn iface ends after slot 52')
# R9. cGZWin base QI 0x99B774 accepts 0xE98B2F57 next to GZIID_cIGZWin 0x22BA0121
q = ' '.join('%s %s' % (i.mnemonic, i.op_str) for i in p.dis(0x99B774, 0x20, maxins=8))
check('0x22ba0121' in q and '0xe98b2f57' in q, 'cGZWin QI accepts 0x22BA0121 and 0xE98B2F57')
print('fails', fails)
