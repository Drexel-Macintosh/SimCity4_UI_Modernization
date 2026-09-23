# V4: independently check every PIXEL lever the finder names: decode the instruction AT the
# claimed VA with capstone and report its mnemonic/operands and the immediate value.
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-ToolTip-verify")
from vpe import PE
p = PE()

# (claimed VA, expected immediate (signed), label)
claims = [
    (0x7EFCCD, 8, 'expanded padX push 8'), (0x7EFCCB, 8, 'expanded padY push 8'),
    (0x7EFD42, 5, 'simple padX push 5'), (0x7EFD40, 3, 'simple padY push 3'),
    (0x79834C, 8, 'SetBackgroundImage default padX'), (0x79835F, 3, 'default padY'),
    (0x438002, 12, 'query padX'), (0x438000, 10, 'query padY'),
    (0x43A397, 12, 'query2 padX'), (0x43A395, 10, 'query2 padY'),
    (0x439200, 12, 'query3 padX'), (0x4391FE, 10, 'query3 padY'),
    (0x7EFCD6, -28, 'expanded avoid -28'), (0x7EFCE3, 28, 'expanded avoid +28'),
    (0x7EFD4B, -4, 'simple avoid -4'), (0x7EFD58, 20, 'simple avoid +20'),
    (0x799E94, -28, 'ctor avoid -28'), (0x799EA5, 28, 'ctor avoid +28'),
    (0x4C58BF, -40, 'traffic avoid -40'), (0x4C58CC, 40, 'traffic avoid +40'),
    (0x438039, -1000, 'query avoid -1000'), (0x43804B, 28, 'query avoid 28'),
    (0x43A3CE, -1000, 'query2 avoid -1000'), (0x43A3E0, 28, 'query2 avoid 28'),
    (0x4391A3, -1000, 'query3 avoid -1000'), (0x4391AB, 28, 'query3 avoid 28'),
    (0x798781, 4, 'icon->text +4'), (0x79885A, 4, 'title width +4'),
    (0x79887B, 3, 'title band +3 (lea)'), (0x79890B, 4, 'title/body gap +4'),
    (0x798994, 4, 'meter gap +4'), (0x798A02, 2, 'content h +2'),
    (0x798CB2, 4, 'body y +4 (title)'), (0x798CE1, 4, 'body y +4 (meter)'),
    (0x7981EA, 16, 'inset l'), (0x7981EF, 16, 'inset t'), (0x7981F3, 16, 'inset r'), (0x7981F9, 16, 'inset b'),
    (0x79880A, 250, 'wrap title'), (0x7988A9, 250, 'wrap body'),
    (0x79871C, 16, 'fallback cell'), (0x798747, 0xCCCCCCCD, 'div5 w'), (0x798760, 0xCCCCCCCD, 'div5 h'),
    (0x9D9D3F, 256, 'GZ buf w'), (0x9D9D3D, 64, 'GZ buf h'), (0x9DA07F, 256, 'GZ ellipsis'),
    (0x44CB3E, 3, 'app Init pad 3'), (0x44CB3C, 1, 'app Init pad 1'),
    (0x7E7E3E, 0x2EE, 'timer 750 a'), (0x7E7E4A, 0x2EE, 'timer 750 b'),
    (0x9DA386, None, 'GZ gap dec'), (0x9DA39E, None, 'GZ gap dec'), (0x9DA3C6, None, 'GZ gap dec'),
    (0x9DA3E3, None, 'GZ gap inc'), (0x9DA3F9, None, 'GZ gap inc (claimed)'), (0x9DA411, None, 'GZ gap inc'),
    (0x9DA42B, None, 'GZ gap dec'), (0x9DA4B0, None, 'GZ gap inc (claimed)'),
    (0x9DA4B3, 2, 'GZ margin cmp'), (0x9DA4B8, 2, 'GZ margin push'), (0x9DA4EA, -2, 'GZ margin push -2'),
]

def s32(v):
    return v - (1 << 32) if v & 0x80000000 else v

ok = bad = 0
for va, exp, label in claims:
    ins = p.dis(va, 16, maxins=1)
    if not ins:
        print('%08X  NO DECODE  %s' % (va, label)); bad += 1; continue
    i = ins[0]
    # is va an instruction start? verify by decoding from a few bytes before and seeing alignment
    starts = set()
    for back in range(1, 16):
        for x in p.dis(va - back, back + 16, maxins=8):
            starts.add(x.address)
    imms = []
    for op in i.operands:
        if op.type == 2:  # X86_OP_IMM
            imms.append(s32(op.imm & 0xFFFFFFFF) if exp is None or exp >= 0 or True else op.imm)
        if op.type == 3 and op.mem.disp:  # MEM displacement (lea)
            imms.append(op.mem.disp)
    val_ok = exp is None or any((m == exp) or ((m & 0xFFFFFFFF) == (exp & 0xFFFFFFFF)) for m in imms)
    flag = 'OK ' if val_ok else 'BAD'
    if val_ok: ok += 1
    else: bad += 1
    print('%s %08X  %-22s %-30s imms=%s  [%s]' % (flag, va, i.bytes.hex(), i.mnemonic + ' ' + i.op_str, imms, label))
print('ok', ok, 'bad', bad)
