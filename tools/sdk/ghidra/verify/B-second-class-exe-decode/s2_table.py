"""Step 2: slot VA table across class vtables (read from the exe), shared vs overridden.
Output: slot | per-class VA ('=' when identical to the cGZWin base vt 0xADC8D8) | ret N of base impl."""
import sys, json
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from pe import *
from s1_vtables import CLASSES

SLOTS = list(range(50, 61)) + list(range(63, 71)) + list(range(86, 90)) + list(range(115, 151))

vts = {n: vtable(va) for n, va in CLASSES}
base = vts[CLASSES[0][0]]

def short(n):
    return n.split("(")[0].replace("cGZWin", "").replace("cSC4Win", "sc4.").replace("GZWin", "") or "base"

if __name__ == "__main__":
    names = [n for n, _ in CLASSES]
    hdr = "slot off   base_VA     ret | " + " ".join(f"{short(n)[:9]:>9}" for n in names[1:])
    print(hdr)
    rows = {}
    for s in SLOTS:
        b = base[s]
        r = retn_of(b)
        cells = []
        for n in names[1:]:
            v = vts[n][s] if s < len(vts[n]) else None
            cells.append("=" if v == b else (f"{v:08X}" if v else "--"))
        nov = sum(1 for c in cells if c != "=")
        print(f"{s:4d} {s*4:#05x} {b:08X} {str(r):>4} | " + " ".join(f"{c:>9}" for c in cells) + f"   overrides={nov}")
        rows[s] = {"base": hex(b), "ret": r, **{n: (hex(vts[n][s]) if s < len(vts[n]) else None) for n in names}}
    # census-wide override counts over all 111 window vtables
    w = json.load(open(r"C:\dev\SC4UIScale\tools\uimap\_work\wincensus.json"))
    allv = w["windowVtables"]
    print("\ncensus over", len(allv), "window vtables: number of vtables whose slot != base, and #distinct impls")
    for s in SLOTS:
        vals = [u32(v + 4 * s) for v in allv]
        dif = sum(1 for x in vals if x != base[s])
        print(f"  slot {s:3d}: {dif:3d} override, {len(set(vals))} distinct")
        rows[s]["census_overrides"] = dif
        rows[s]["census_distinct"] = sorted({hex(x) for x in vals})
    json.dump(rows, open(__file__.rsplit("\\", 1)[0] + "\\slot_table.json", "w"), indent=1)
