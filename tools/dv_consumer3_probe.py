#!/usr/bin/env python3
"""LENS pass 3 - the disciplined scan, with CORRECTED offsets.

Window rect  = +0xA8 L / +0xAC T / +0xB0 R / +0xB4 B   (measured, see slotcheck)
Absolute rect= +0x14 .. +0x20                          (measured, GetAreaAbsolute)
Minimap state= +0xE4 blitSize, +0xF0 surface, +0xF4 lockObj, +0x104 zoom,
               +0x114/+0x118/+0x11C raster, +0x120 dirty

For every function in the DV/minimap code block, report:
  EXTENT sources touched : window-rect fields, geometry vcalls (GetW..GetArea*)
  STRIDE sources touched : blitSize / rasterW / surface
  HIT-TEST slots called  : GetWindowFromPoint / GetChildWindowFromPoint /
                           ScreenToWindowCoordinates / IsPointInWindowScreenCoords
Anything with EXTENT and STRIDE from different owners is an overrun candidate.

POSITIVE CONTROLS (must all pass or the scan is reported as blind):
  1. sub_7A2F60 must show a GetArea(rect&) geometry vcall  (measured 0x7A301E).
  2. the bake 0x7A7FF0 must show blitSize AND rasterW      (measured 0x7A8596/0x7A8547).
  3. cSC4WinMiniMap::Plot 0x7A79B0 must show surface       (measured 0x7A7A09).
Read-only."""
import struct, bisect, collections
from pe109_probe import *
from capstone.x86 import X86_REG_ESP, X86_REG_EBP

data, secs = load()
S = sorted(function_starts(data, secs))
def encl(va):
    i = bisect.bisect_right(S, va) - 1
    return S[i] if i >= 0 else None

WINRECT = {0xA8: "L", 0xAC: "T", 0xB0: "R", 0xB4: "B"}
ABSRECT = {0x14: "aL", 0x18: "aT", 0x1C: "aR", 0x20: "aB"}
STRIDE = {0xE4: "blitSize", 0xF0: "surface", 0x118: "rasterW", 0x114: "rasterBase"}
OTHERMM = {0x104: "zoom", 0x11C: "rasterH", 0x120: "dirty", 0xF4: "lockObj"}
GEOM = {0xA4: "GetW", 0xA8: "GetH", 0xAC: "GetL", 0xB0: "GetT", 0xB4: "GetR",
        0xB8: "GetB", 0xBC: "GetArea(r&)", 0xC0: "GetArea()",
        0xC4: "GetAreaAbs(r&)", 0xC8: "GetAreaAbs()"}
HIT = {0x98: "GetWindowFromPoint", 0x9C: "GetChildWindowFromPoint",
       0xA0: "GetChildWinFromCursorPoint", 0xE8: "ScreenToWindowCoords",
       0xEC: "WindowToScreenCoords", 0xF0: "WindowToWindowCoords",
       0xF4: "IsPointInWindowScreenCoords"}
SETG = {0xCC: "SetW", 0xD0: "SetH", 0xD4: "SetSize", 0xD8: "SetArea(rect)",
        0xDC: "SetArea(ltrb)", 0xE0: "GZWinMoveTo"}

LO, HI = 0x0079D000, 0x007A9000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
B = collections.defaultdict(lambda: collections.defaultdict(set))

fns = [s for s in S if LO <= s < HI]
for i, s in enumerate(fns):
    e = fns[i + 1] if i + 1 < len(fns) else HI
    o = va2off(secs, s)
    for ins in md.disasm(data[o:o + (e - s)], s):
        b = B[s]
        if ins.mnemonic == "call" and ins.operands and \
           ins.operands[0].type == X86_OP_MEM and \
           ins.operands[0].mem.base not in (0, X86_REG_ESP, X86_REG_EBP):
            d = ins.operands[0].mem.disp
            if d in GEOM: b["geomcall"].add(GEOM[d])
            if d in HIT: b["hitcall"].add(HIT[d])
            if d in SETG: b["setcall"].add(SETG[d])
            continue
        for op in ins.operands:
            if op.type != X86_OP_MEM or op.mem.base in (0, X86_REG_ESP):
                continue
            d = op.mem.disp
            if d in WINRECT: b["winrect"].add(WINRECT[d])
            elif d in ABSRECT: b["absrect"].add(ABSRECT[d])
            elif d in STRIDE: b["stride"].add(STRIDE[d])
            elif d in OTHERMM: b["mm"].add(OTHERMM[d])

ctl = []
ctl.append(("sub_7A2F60 GetArea(r&)", "GetArea(r&)" in B[0x7A2F60]["geomcall"]))
ctl.append(("bake 0x7A7FF0 blitSize+rasterW",
            {"blitSize", "rasterW"} <= B[0x7A7FF0]["stride"]))
ctl.append(("Plot 0x7A79B0 surface", "surface" in B[0x7A79B0]["stride"]))
print("POSITIVE CONTROLS")
for n, ok in ctl:
    print(f"   {'PASS' if ok else '*** FAIL ***'}  {n}")
if not all(ok for _, ok in ctl):
    print("PROBE IS BLIND - refusing to report a null."); raise SystemExit(3)

print(f"\nfunctions scanned in [{hex(LO)},{hex(HI)}): {len(fns)}\n")
print("=" * 100)
print(f"{'fn':<10} {'winrect':<14} {'absrect':<10} {'geom vcalls':<28} "
      f"{'STRIDE':<26} {'hit-test':<24} {'set'}")
print("=" * 100)
for s in fns:
    b = B[s]
    if not any(b.values()):
        continue
    print(f"{hex(s):<10} {','.join(sorted(b['winrect'])) or '-':<14} "
          f"{','.join(sorted(b['absrect'])) or '-':<10} "
          f"{','.join(sorted(b['geomcall'])) or '-':<28} "
          f"{','.join(sorted(b['stride'])) or '-':<26} "
          f"{','.join(sorted(b['hitcall'])) or '-':<24} "
          f"{','.join(sorted(b['setcall'])) or '-'}")

print("\n### MIXING CANDIDATES (an EXTENT source AND a STRIDE source together)")
for s in fns:
    b = B[s]
    ext = b["winrect"] | b["absrect"] | b["geomcall"]
    if ext and b["stride"]:
        print(f"  {hex(s)}  extent={sorted(ext)}  stride={sorted(b['stride'])}")
print("\n### ANY HIT-TEST / COORD-CONVERSION IN THE BLOCK")
for s in fns:
    if B[s]["hitcall"]:
        print(f"  {hex(s)}  {sorted(B[s]['hitcall'])}  "
              f"stride={sorted(B[s]['stride'])} mm={sorted(B[s]['mm'])}")
