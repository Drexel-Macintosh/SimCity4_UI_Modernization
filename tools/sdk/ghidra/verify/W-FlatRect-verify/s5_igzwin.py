"""Step 5: Mac vftable_cIGZWin names for the slots the finder uses, and the
Windows base bodies (cGZWin class vt 0xADC8D8)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfn import *

GZ = 0xADC8D8
d = json.load(open(r"C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json"))
vt = [t for t in d["types"] if t["name"] == "vftable_cIGZWin"]
print("Mac vftable_cIGZWin count:", len(vt), [ (t["path"], t["size"]) for t in vt])
mac = {}
for t in vt:
    for f in t["fields"]:
        mac[f["off"] // 4] = f["name"]
for s in (3, 11, 32, 35, 36, 43, 44, 47, 48, 53, 54, 55, 56, 64, 68, 93, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 118, 124, 125, 126, 127, 130, 131, 145, 146, 147):
    va = u32(GZ + 4 * s)
    print(f"\n--- cIGZWin slot {s} (vt+{4*s:#x}) Mac='{mac.get(s)}' base={va:08X} rets={rets(va)}")
    print(fmt(fn(va, 40), "     "))
print("\nMac cIGZWin slot count:", max(mac) + 1)
