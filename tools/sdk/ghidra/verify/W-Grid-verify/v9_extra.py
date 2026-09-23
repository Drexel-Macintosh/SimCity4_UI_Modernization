# W-Grid-verify step 9: reproducible evidence for the verifier's refutations / new findings.
from vpe import PE
from cfg import walk
pe = PE()

def around(c, before=0x30, after=6):
    for s in range(c - before, c):
        ins = pe.dis(s, 60, False)
        if c in [i.address for i in ins]:
            break
    return '\n'.join('   %08X: %-20s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str)
                     for i in ins if i.address <= c + after)

print('== A. SetCellGutters (grid vt+0x68) callers the finder missed ==')
for c in (0x79C8F2, 0x79CD7C, 0x99572C):
    print('-- call at %X' % c); print(around(c, 0x28))
print('-- grid member creation: base Init 0x994554 contains ctor call 0x9947B7 -> [this+0x14C] (0x9947C0)')
r = walk(pe, 0x994554, span=0x800, maxins=4000)
print('   0x9947B7 reachable from 0x994554:', 0x9947B7 in [i.address for i in r['insns']])
print('   base vtable 0xADBA40 slot4 =', hex(pe.u32(0xADBA40 + 16)), ' slot17 =', hex(pe.u32(0xADBA40 + 68)))
print('   derived vtable 0xAB78A0 slot4 =', hex(pe.u32(0xAB78A0 + 16)), ' slot17 =', hex(pe.u32(0xAB78A0 + 68)))
print('   0x79C800 calls base Init:', [hex(x) for x in pe.call_targets_to(0x994554)])

print('\n== B. GetRowHeaderArea (slot 73, 0x9A68E2): whole-area path uses +0x110 ==')
print(around(0x9A6936, 0x20, 0x16))

print('\n== C. cIGZWin fill-colour block on Windows (base vtable 0xADC8D8), MSVC overload grouping ==')
for s in range(102, 109):
    va = pe.u32(0xADC8D8 + 4 * s)
    rr = walk(pe, va, span=0x80)
    print('   slot %d vt+0x%X -> %X ret %s ; %s' % (s, s * 4, va, rr['rets'],
          '; '.join('%s %s' % (i.mnemonic, i.op_str) for i in rr['insns'][:4])))

print('\n== D. push-imm32 census of the grid IID ==')
import struct
sites = pe.find_bytes(b'\x68' + struct.pack('<I', 0xDAA6B9BE), '.text')
raw = pe.find_bytes(struct.pack('<I', 0xDAA6B9BE), '.text')
print('   push imm32 sites:', len(sites), ' raw dword refs in .text:', len(raw))

print('\n== E. callers of popup helper 0x5F9F10 ==')
print('  ', [hex(x) for x in pe.call_targets_to(0x5F9F10)])

print('\n== F. size-cache invalidation helper 0x9ADE44 callers (cell setters) ==')
print('  ', [hex(x) for x in pe.call_targets_to(0x9ADE44)])
