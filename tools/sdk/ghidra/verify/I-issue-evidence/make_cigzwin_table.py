r"""Emit the cIGZWin issue's slot table from the evidence, never by hand.

    python tools\sdk\ghidra\verify\I-issue-evidence\make_cigzwin_table.py [exe]

Reads cigzwin_consolidated.json (written by consolidate_cigzwin.py) and the
exe's base cGZWin vtable 0x00ADC8D8. For each wrong declaration it prints:
  - the slot MSVC compiles it to,
  - the slot the game has it at,
  - which game method a call through the header actually reaches.
"""
import json
import os
import sys

import pefile

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.dirname(HERE)
EXE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps", "SimCity 4.exe")
VT = 0x00ADC8D8
pe = pefile.PE(EXE, fast_load=True)
BASE = pe.OPTIONAL_HEADER.ImageBase
C = json.load(open(os.path.join(HERE, "cigzwin_consolidated.json")))
B = {}
with open(os.path.join(V, "B-second-class-exe-decode", "slot_table.tsv"), encoding="utf-8") as f:
    f.readline()
    for line in f:
        c = line.rstrip("\n").split("\t")
        if c and c[0].isdigit():
            B[int(c[0])] = c[2]

# game slot -> header declaration that belongs there (decoded rows only)
at = {x["exe"]: x["sig"] for x in C["wrong"] + C["right"]}
at.setdefault(57, "GZWinOffset(int32_t, int32_t) - not declared in the header")


def short(sig):
    ret, rest = sig.split(" ", 1) if sig.startswith(("bool", "void", "uint", "int", "cIGZ")) else ("", sig)
    return rest.replace("const&", "const &")


print("| declaration | compiles to | game slot | a call reaches (game slot = method) |")
print("|---|---:|---:|---|")
for x in sorted(C["wrong"], key=lambda r: r["hidx"]):
    comp = x["compiled"]
    reach = at.get(comp) or (B.get(comp, "?") + " (name from the Mac symbols)")
    fn = pe.get_dword_at_rva(VT + 4 * comp - BASE)
    print("| `%s` | %d | %d | %d = `%s` (`0x%08X`) |" % (short(x["sig"]), comp, x["exe"], comp, short(reach), fn))
