# V1: IID literal scans + FlatRect positive control, independent of the finder.
import sys
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-ToolTip-verify")
from vpe import PE
p = PE()

def ctx(va, back=12, fwd=24):
    # disassemble around a literal: find an instruction start that contains va
    for start in range(va - back, va + 1):
        ins = p.dis(start, back + fwd, maxins=12)
        for i in ins:
            if i.address <= va < i.address + i.size:
                return ins
    return []

for name, v in [('FlatRect IID (control)', 0xC2AFA76F),
                ('cIGZWinToolTip IID?', 0x22C010CF),
                ('CalloutBox IID?', 0xC9B432CF),
                ('TipMgr IID? (folded)', 0x22C010CD),
                ('GZ tipmgr clsid', 0x22C010CE),
                ('kSC4CLSID_cSC4WinToolTipMgr', 0xCA56C8C4),
                ('unknown IID', 0xE98B2F57),
                ('tip window id', 0x82F0121D),
                ('tip layer id', 0x2AAB8CC1),
                ('tick', 0xCA56DD76),
                ('tick table', 0x0CA56DD7),
                ('GZ tick', 0x533CCA1E),
                ]:
    hits = p.scan_dword(v)
    print('%-30s 0x%08X  %d hits' % (name, v, len(hits)))
    for h, s in hits[:40]:
        print('     %08X %s' % (h, s))
