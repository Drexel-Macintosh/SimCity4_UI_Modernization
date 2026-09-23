# W-Grid-verify step 1: IID / CLSID evidence, re-derived independently.
import struct, sys
from vpe import PE
pe = PE()

IID = 0xDAA6B9BE
CLSID = 0xDAA6B9BF
FLAT_IID = 0xC2AFA76F

def show(va, n=20, stop=True):
    print(pe.dis_text(va, n, stop))

print('=== A. .data table at 0xB17080 (12-byte stride) ===')
for i in range(-2, 40):
    va = 0xB17080 + 12*i
    a, b, c = struct.unpack('<III', pe.read(va, 12))
    name = pe.cstr(c) if pe.sec_of(c) else '?'
    if i < 3 or a in (CLSID, 0xC2AFA76E) or b in (IID, FLAT_IID):
        print(hex(va), hex(a), hex(b), hex(c), repr(name))
# locate table entries containing grid ids anywhere in .data/.rdata
print('--- every occurrence of CLSID/IID as a dword in data sections ---')
for sec in ('.rdata', '.data'):
    for v in (CLSID, IID):
        for va in pe.find_bytes(struct.pack('<I', v), sec):
            ctx = struct.unpack('<6I', pe.read(va-8, 24))
            print(sec, hex(v), 'at', hex(va), 'ctx', [hex(x) for x in ctx])

print()
print('=== B. first entry of the same table (positive control) ===')
# walk backwards to find start of the table
va = 0xB17080
a, b, c = struct.unpack('<III', pe.read(va, 12))
print(hex(va), hex(a), hex(b), repr(pe.cstr(c) if pe.sec_of(c) else '?'))

print()
print('=== C. QueryInterface 0x9A5CB5 ===')
show(0x9A5CB5, 40)

print()
print('=== D. push imm32 census: IID and FlatRect IID (positive control) ===')
def census(iid, label):
    pat = b'\x68' + struct.pack('<I', iid)
    sites = pe.find_bytes(pat, '.text')
    kinds = {}
    rows = []
    for s in sites:
        # scan forward up to 12 instructions for first indirect call
        ins = pe.dis(s, 14, stop_at_ret=False)
        kind = None
        for k in ins[1:]:
            if k.mnemonic == 'call':
                op = k.op_str
                if op.startswith('dword ptr ['):
                    inner = op[len('dword ptr ['):-1]
                    if '+' in inner:
                        disp = inner.split('+')[-1].strip()
                        kind = 'call [+%s]' % disp
                    else:
                        kind = 'call [%s]' % inner
                else:
                    kind = 'call %s' % op
                rows.append((s, kind, k.address))
                break
        if kind is None:
            rows.append((s, 'nocall', None))
        kinds[kind] = kinds.get(kind, 0) + 1
    print(label, hex(iid), 'push sites:', len(sites))
    for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
        print('   ', v, k)
    return rows

rows_grid = census(IID, 'GRID')
rows_flat = census(FLAT_IID, 'FLAT')
for s, k, a in rows_flat:
    print('   flat site', hex(s), k, hex(a) if a else '')
print('   positive control 0x47B993 / 0x4861D7 within any flat push window?',
      [hex(s) for s, k, a in rows_flat if a and (a in (0x47B993, 0x4861D7) or s in (0x47B993, 0x4861D7) or (s < 0x47B993 <= s+40) or (s < 0x4861D7 <= s+40))])
print('--- grid site list ---')
for s, k, a in rows_grid:
    print('   ', hex(s), k, hex(a) if a else '')

print()
print('=== E. push CLSID census ===')
for s in pe.find_bytes(b'\x68' + struct.pack('<I', CLSID), '.text'):
    print('   push clsid at', hex(s))
    print('      ' + pe.dis_text(s-8, 8, False).replace('\n', '\n      '))
