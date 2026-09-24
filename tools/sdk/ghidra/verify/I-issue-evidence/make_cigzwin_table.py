r"""Emit the cIGZWin issue's slot table from the evidence, never by hand.

    python tools\sdk\ghidra\verify\I-issue-evidence\make_cigzwin_table.py [exe]

Reads cigzwin_consolidated.json (written by consolidate_cigzwin.py) and the
exe's base cGZWin vtable 0x00ADC8D8. For each wrong declaration it prints the
slot MSVC compiles it to, the slot the game has it at, and which game method a
call through the header actually runs.

The last column names the game's method by name only, adding the argument
list just where a name has overloads. It never borrows a header signature the
issue says is wrong for the game (the input handlers, and the by-value colour
at 105).
"""
import json
import os
import re
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
ALL = C["wrong"] + C["right"] + C["undecoded"]


def name_of(sig):
    return re.match(r".*?\b(\w+)\s*\(", sig).group(1)


def params(sig):
    return sig[sig.index("("):sig.rindex(")") + 1].replace("const&", "const &")


OVERLOADED = {n for n in (name_of(x["sig"]) for x in ALL) if sum(1 for y in ALL if name_of(y["sig"]) == n) > 1}
GAME_FORM = {"bool SetFillColor(cRZColor const&)": "SetFillColor(cRZColor), colour passed by value"}

# game slot -> the game's method there (decoded rows only)
at = {}
for x in C["wrong"] + C["right"]:
    n = name_of(x["sig"])
    at[x["exe"]] = GAME_FORM.get(x["sig"]) or (n + params(x["sig"]) if n in OVERLOADED else n)
at[57] = "GZWinOffset"
NOT_DECLARED = {57}

print("| The header's method | The header calls slot | The game has it at slot | What the game actually runs there |")
print("|---|---:|---:|---|")
for x in sorted(C["wrong"], key=lambda r: r["hidx"]):
    comp = x["compiled"]
    fn = pe.get_dword_at_rva(VT + 4 * comp - BASE)
    n = name_of(x["sig"])
    mine = n + params(x["sig"]) if n in OVERLOADED else n
    note = " (not declared in the header)" if comp in NOT_DECLARED else ""
    print("| `%s` | %d | %d | `%s`%s (`0x%08X`) |" % (mine, comp, x["exe"], at.get(comp, "?"), note, fn))
