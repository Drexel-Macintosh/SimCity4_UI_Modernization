"""Step 1: verify candidate class vtables and find where each one ends.
Evidence per vtable:
  - vt[-1] (MSVC RTTI COL pointer, if any)
  - run length of consecutive .text pointers
  - every address inside that run that the CODE references as an imm32
    (a ctor 'mov [reg+x], imm32' / 'mov [reg], imm32' marks a vtable start)
  - slot 87 == 0x0099BE4C (the census fingerprint for 'is a window vtable')
"""
import sys, struct, re
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from pe import *

CLASSES = [
    ("cGZWin(base,clsid E2BA00EE)", 0xADC8D8),
    ("cSC4WinAlertBorder", 0xAB5B48),
    ("cGZWinText", 0xADFEB8),
    ("cGZWinBMP", 0xADF6A0),
    ("cGZWinBtn", 0xADDAF0),
    ("cGZWinTextEdit", 0xADFBD0),
    ("cGZWinLineInput", 0xAE0FB0),
    ("cSC4WinRCI", 0xAB8628),
    ("GZWinFlatRect", 0xAE20A0),
    ("cGZWinScrollbar", 0xAE0810),
    ("cGZWinSlider", 0xAE04D8),
    ("cGZWinListBox", 0xAE1780),
    ("cGZWinGen", 0xADC678),
    ("cSC4WinMiniMap", 0xAB83B8),
    ("cGZWinGrid", 0xADD7B0),
    ("cGZWinCustom", 0xAD6AA0),
]

text = rd(TEXT[1], TEXT[2] - TEXT[1])

def code_refs(target):
    pat = struct.pack("<I", target)
    hits = []
    i = text.find(pat)
    while i >= 0:
        hits.append(TEXT[1] + i)
        i = text.find(pat, i + 1)
    return hits

if __name__ == "__main__":
    for name, va in CLASSES:
        vt = vtable(va)
        col = u32(va - 4)
        print(f"== {name} vt {va:#010x}: run of {len(vt)} code ptrs; vt[-1]={col:#010x} ({sec_of(col)}); slot87={vt[87]:#x}")
        # starts of other vtables inside the run (referenced by code)
        starts = []
        for i in range(1, len(vt) + 1):
            a = va + 4 * i
            r = code_refs(a)
            if r:
                starts.append((i, a, r[:3]))
        for i, a, r in starts[:4]:
            print(f"    code-referenced address inside/at-end of run: slot {i} = {a:#x}  refs {[hex(x) for x in r]}")
        refs = code_refs(va)
        print(f"    refs to vt itself: {[hex(x) for x in refs[:6]]}")
