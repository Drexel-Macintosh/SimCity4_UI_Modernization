# Disassemble around every code reference to each claimed vtable and report
# the store instruction (which register/offset receives the vtable).
import sys
from v_refs import load

p, refs = load()

def window(site, before=0x60, after=0x18):
    # try several start points; pick the one whose decode lands exactly on site-2..site-1
    best = None
    for back in range(before, before - 16, -1):
        ins = p.dis(site - back, back + after)
        addrs = [i.address for i in ins]
        hit = [i for i in ins if i.address < site <= i.address + i.size - 4 + 0 or (i.address < site < i.address + i.size)]
        if hit:
            best = ins; break
    return best

VT = {
 'cGZWin base': 0xADC8D8, 'AlertBorder': 0xAB5B48, 'Text': 0xADFEB8, 'BMP': 0xADF6A0,
 'Btn(+4?)': 0xADDAF0, 'Btn(+0?)': 0xADDD50, 'RCI(+4?)': 0xAB8628, 'RCI +0 a': 0xAB889C, 'RCI +0 b': 0xAB8884,
 'Grid(+4?)': 0xADD7B0, 'Grid(+0?)': 0xADD348, 'TextEdit': 0xADFBD0, 'LineInput': 0xAE0FB0,
 'FlatRect': 0xAE20A0, 'MiniMap': 0xAB83B8, 'Custom': 0xAD6AA0, 'Slider': 0xAE04D8,
 'Scrollbar': 0xAE0810, 'ListBox': 0xAE1780, 'Gen': 0xADC678,
}
for name, vt in VT.items():
    for site in refs.get(vt, []):
        ins = window(site)
        print('==== %s vt %08X ref@%08X' % (name, vt, site))
        if not ins:
            print('   (no sync)'); continue
        # show from 8 instructions before the holding instruction to 3 after
        k = [j for j, i in enumerate(ins) if i.address < site < i.address + i.size][0]
        for i in ins[max(0, k-8):k+3]:
            print('  %s %08X  %-6s %s' % ('>>' if i is ins[k] else '  ', i.address, i.mnemonic, i.op_str))
