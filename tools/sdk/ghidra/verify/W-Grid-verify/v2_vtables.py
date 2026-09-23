# W-Grid-verify step 2: ctor, factory, vtable extents, overrides vs base cGZWin vtable.
import struct
from vpe import PE
pe = PE()

def show(va, n=40, stop=True):
    print(pe.dis_text(va, n, stop))

print('=== factory 0x998B10 ===')
show(0x998B10, 30)

print('\n=== ctor 0x9ABC95 (first 260 insns, no stop) ===')
ins = pe.dis(0x9ABC95, 400, stop_at_ret=True)
for i in ins:
    print('%08X: %s %s' % (i.address, i.mnemonic, i.op_str))

print('\n=== imm32 references in .text to each address in 0xADD300..0xADDA40 (vtable-start candidates) ===')
text = pe.text()
blob = pe.data[text[3]:text[3]+text[4]]
cands = {}
for va in range(0xADD300, 0xADDA40, 4):
    pat = struct.pack('<I', va)
    i = blob.find(pat)
    hits = []
    while i >= 0:
        hits.append(text[1] + i)
        i = blob.find(pat, i+1)
    if hits:
        cands[va] = hits
for va, hits in sorted(cands.items()):
    print(hex(va), [hex(h) for h in hits][:12], '(%d)' % len(hits))
# data refs too
print('--- refs from .rdata/.data ---')
for sec in ('.rdata', '.data'):
    s = [x for x in pe.secs if x[0] == sec][0]
    b = pe.data[s[3]:s[3]+s[4]]
    for va in range(0xADD300, 0xADDA40, 4):
        pat = struct.pack('<I', va)
        i = b.find(pat)
        while i >= 0:
            if i % 4 == 0:
                print(sec, 'ref to', hex(va), 'at', hex(s[1]+i))
            i = b.find(pat, i+1)

print('\n=== 0xADD348: purecall count ===')
vals = [pe.u32(0xADD348 + 4*i) for i in range((0xADD578-0xADD348)//4)]
print('entries between 0xADD348 and 0xADD578:', len(vals), 'distinct:', set(hex(v) for v in vals))
print('dword before 0xADD348:', hex(pe.u32(0xADD344)), ' dword at 0xADD578:', hex(pe.u32(0xADD578)))
print('_purecall 0x5D4A10 code:')
show(0x5D4A10, 8)

print('\n=== 0xADD578 walk ===')
w = pe.vtable_walk(0xADD578, 400)
print('code entries walking from 0xADD578:', len(w), '(stops at non-code)')
print('entries up to 0xADD7B0:', (0xADD7B0-0xADD578)//4)
print('slot140', hex(pe.u32(0xADD578+140*4)), 'slot141', hex(pe.u32(0xADD578+141*4)))

print('\n=== 0xADD7B0 walk ===')
w2 = pe.vtable_walk(0xADD7B0, 400)
print('code entries walking from 0xADD7B0:', len(w2), ' end VA', hex(0xADD7B0+4*len(w2)), 'string there:', repr(pe.cstr(0xADD7B0+4*len(w2), 32)))

print('\n=== base cGZWin vtable 0xADC8D8 walk ===')
wb = pe.vtable_walk(0xADC8D8, 400)
print('code entries from 0xADC8D8:', len(wb), ' end VA', hex(0xADC8D8+4*len(wb)), 'next dwords', [hex(pe.u32(0xADC8D8+4*len(wb)+4*k)) for k in range(4)])
print('refs to 0xADC8D8 in .text:', [hex(x) for x in pe.xrefs_imm32(0xADC8D8)][:10])

print('\n=== overrides: grid cIGZWin vtable 0xADD7B0 vs base 0xADC8D8 ===')
n = min(len(w2), len(wb))
for i in range(max(len(w2), len(wb))):
    g = w2[i] if i < len(w2) else None
    b = wb[i] if i < len(wb) else None
    if g != b:
        first = pe.dis(g, 2, False) if g else []
        desc = '; '.join('%s %s' % (x.mnemonic, x.op_str) for x in first)
        print('slot %3d vt+0x%03X grid=%s base=%s   | %s' % (i, i*4, hex(g) if g else None, hex(b) if b else None, desc))
