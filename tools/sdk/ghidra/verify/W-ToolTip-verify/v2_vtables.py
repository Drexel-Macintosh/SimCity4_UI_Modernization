# V2: dump vtables claimed by the finder, count slots with independent bound checks.
import sys, struct
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-ToolTip-verify")
from vpe import PE
p = PE()

def xrefs_to(va):
    """All places in the image holding the dword va (any section)."""
    return p.scan_dword(va)

def dump(va, n, label):
    print('==== %s @ %08X' % (label, va))
    for i in range(n):
        d = p.u32(va + 4*i)
        tag = ''
        if d is not None and p.is_text(d):
            ins = p.dis(d, 16, maxins=2)
            tag = '; '.join('%s %s' % (x.mnemonic, x.op_str) for x in ins)
        else:
            tag = '(not code)'
        refs = xrefs_to(va + 4*i)
        rtag = (' <-REF ' + ','.join('%08X' % r for r, s in refs[:4])) if refs else ''
        print('  [%3d] +%03X %08X  %s%s' % (i, 4*i, d if d is not None else 0, tag, rtag))

which = sys.argv[1] if len(sys.argv) > 1 else 'gz'
if which == 'gz':
    dump(0xAE4368 - 0x10, 4, 'before abstract')
    dump(0xAE4368, 6, 'abstract cIGZWinToolTip?')
    dump(0xAE4380, 6, 'iface cIGZWinToolTip?')
    dump(0xAE4398, 156, 'class GZ tooltip')
elif which == 'callout':
    dump(0xAB6718 - 0x8, 2, 'before abstract')
    dump(0xAB6718, 22, 'abstract callout')
    dump(0xAB6770, 152, 'class callout')
    dump(0xAB69D0, 23, 'iface callout')
elif which == 'mgr':
    dump(0xAE434C - 8, 2, 'before gz mgr')
    dump(0xAE434C, 8, 'GZ mgr vt')
    dump(0xABCB60 - 8, 2, 'before sc4 mgr')
    dump(0xABCB60, 10, 'SC4 mgr vt')
elif which == 'btn':
    dump(0xADDD50, 56, 'btn iface')
elif which == 'btnclass':
    dump(0xADDAF0, 155, 'btn class')
