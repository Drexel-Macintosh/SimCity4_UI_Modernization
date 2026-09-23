# every raw dword occurrence of the grid IID/CLSID in .text, with the instruction that holds it
import struct
from vpe import PE
pe = PE()
for val, lab in ((0xDAA6B9BE, 'IID'), (0xDAA6B9BF, 'CLSID'), (0xC2AFA76F, 'FLAT-IID')):
    hits = pe.find_bytes(struct.pack('<I', val), '.text')
    print(lab, hex(val), 'raw dword hits in .text:', len(hits))
    for h in hits:
        # find the instruction containing h: try starting 1..8 bytes before
        found = None
        for back in range(1, 9):
            st = h - back
            ins = pe.dis(st, 1, stop_at_ret=False)
            if ins and ins[0].address == st and st + ins[0].size >= h + 4:
                # accept only if the next disassembled instruction chain from a bit earlier syncs too
                found = ins[0]
                if ins[0].mnemonic in ('push', 'cmp', 'mov'):
                    break
        if found is None:
            print('   ', hex(h), '??')
            continue
        print('   ', hex(h), '%08X %s %s' % (found.address, found.mnemonic, found.op_str))
