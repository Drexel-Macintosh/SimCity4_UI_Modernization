r"""Dump every cIGZWin slot not yet identified, for a person to read.

    python tools\sdk\ghidra\verify\I-issue-evidence\dump_undecoded.py > undecoded_dump.txt

For each undecoded header row it prints the slot the header compiles to, the
game's base cGZWin function there (0x00ADC8D8), the function's `ret N`, and
its body. Calls through the object's own vtable are labelled with the slot's
identity where one is decoded (a trailing "?" means only the header's name).
Fields are labelled from rows already decoded. It also shows how many of the
15 other window classes override the slot, and the first override's body.
"""
import json
import os
import re
import sys

import capstone
import pefile

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps", "SimCity 4.exe")
pe = pefile.PE(EXE, fast_load=True)
BASE = pe.OPTIONAL_HEADER.ImageBase
T = next(s for s in pe.sections if s.Name.rstrip(b"\0") == b".text")
TLO = BASE + T.VirtualAddress
TC = T.get_data()
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
CLASSES = [("cGZWin", 0xADC8D8), ("cSC4WinAlertBorder", 0xAB5B48), ("cGZWinText", 0xADFEB8),
           ("cGZWinBMP", 0xADF6A0), ("cGZWinBtn", 0xADDAF0), ("cGZWinTextEdit", 0xADFBD0),
           ("cGZWinLineInput", 0xAE0FB0), ("cSC4WinRCI", 0xAB8628), ("GZWinFlatRect", 0xAE20A0),
           ("cGZWinScrollbar", 0xAE0810), ("cGZWinSlider", 0xAE04D8), ("cGZWinListBox", 0xAE1780),
           ("cGZWinGen", 0xADC678), ("cSC4WinMiniMap", 0xAB83B8), ("cGZWinGrid", 0xADD7B0),
           ("cGZWinCustom", 0xAD6AA0)]
FIELDS = {0x04: "winmgr", 0x08: "refcount", 0x10: "ID", 0x14: "absRect.l", 0x18: "absRect.t", 0x1C: "absRect.r",
          0x20: "absRect.b", 0x44: "children", 0x48: "parent", 0x4C: "notifyTarget", 0x50: "caption",
          0x64: "privBuf", 0x70: "invalid", 0x78: "keyAccel", 0x7C: "params", 0x88: "filters",
          0xA8: "rect.l", 0xAC: "rect.t", 0xB0: "rect.r", 0xB4: "rect.b", 0xC8: "flags", 0xCC: "instanceID",
          0xD0: "shadeColor", 0xD4: "fillColor"}
C = json.load(open(os.path.join(HERE, "cigzwin_consolidated.json")))
known = {x["exe"]: re.match(r".*?\b(\w+)\s*\(", x["sig"]).group(1) for x in C["wrong"] + C["right"]}
known[57] = "GZWinOffset"
header_at = {x["compiled"]: re.match(r".*?\b(\w+)\s*\(", x["sig"]).group(1) + "?" for x in C["undecoded"]}


def dword(va):
    return pe.get_dword_at_rva(va - BASE)


def body(va, limit=40):
    out = []
    for i in MD.disasm(TC[va - TLO:va - TLO + 0x200], va):
        s = ("%s %s" % (i.mnemonic, i.op_str)).strip()
        m = re.search(r"call dword ptr \[e\w\w \+ (0x[0-9a-f]+)\]", s)
        if m:
            k = int(m.group(1), 16) // 4
            s += "   ; slot %d %s" % (k, known.get(k) or header_at.get(k, ""))
        for f in re.finditer(r"\[e(?:cx|si|di|bx) \+ (0x[0-9a-f]+)\]", s):
            v = int(f.group(1), 16)
            if v in FIELDS and "slot" not in s:
                s += "   ; " + FIELDS[v]
        out.append("      %08X  %s" % (i.address, s))
        if i.mnemonic == "ret" or len(out) >= limit:
            break
    return out


argc = {}
for line in open(os.path.join(os.path.dirname(HERE), "A-full-probe", "exe_argc.txt"), encoding="utf-8"):
    m = re.match(r"\s*(\d+) (0x[0-9a-f]+) exe=\s*(\S+)", line)
    if m:
        argc[int(m.group(1))] = m.group(3)

for x in sorted(C["undecoded"], key=lambda r: r["compiled"]):
    slot = x["compiled"]
    fns = [dword(vt + 4 * slot) for _, vt in CLASSES]
    base = fns[0]
    ov = [(CLASSES[i][0], f) for i, f in enumerate(fns) if f != base]
    print("\n=== hidx %d  %s  -> slot %d   base %08X  exe argc %s   overridden in %d/15"
          % (x["hidx"], x["sig"], slot, base, argc.get(slot), len(ov)))
    print("\n".join(body(base)))
    if ov:
        print("    first override (%s %08X):" % ov[0])
        print("\n".join(body(ov[0][1], 18)))
