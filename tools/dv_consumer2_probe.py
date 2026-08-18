#!/usr/bin/env python3
"""LENS pass 2, with the CORRECTED window-rect offsets.

⚠ INSTRUMENT CORRECTION: the task brief says cIGZWin rect = +0x34/0x38/0x3C/0x40.
That is WRONG for this build. Measured from the base implementations the
cSC4WinMiniMap vtable inherits:
    GetL 0x0099BC53 -> mov eax,[ecx+0xA8]
    GetT 0x00994EE4 -> mov eax,[ecx+0xAC]
    GetR 0x0099BC5A -> mov eax,[ecx+0xB0]
    GetB 0x0099BC61 -> mov eax,[ecx+0xB4]
    GetW 0x0099C81B -> [ecx+0xB0] - [ecx+0xA8]
    GetH 0x0099C82A -> [ecx+0xB4] - [ecx+0xAC]
and the project's own src\\UiSpike.cpp agrees ("window rect [0xa8..0xb4]",
:6624, :9230). Scanning +0x34 would have been a BLIND probe.

Dumps the four functions that matter with per-instruction field tags.
Read-only."""
import sys
from pe109_probe import *

data, secs = load()

RECT = {0xA8: "win.L", 0xAC: "win.T", 0xB0: "win.R", 0xB4: "win.B",
        0xC8: "win.flags"}
MM = {0xE0: "mm.flags", 0xE4: "mm.BLITSIZE", 0xF0: "mm.surface",
      0xF4: "mm.lockObj", 0xFC: "mm.initLatch", 0xFD: "mm.rebakeGate",
      0xFE: "mm.bodyGate", 0x104: "mm.ZOOM", 0x114: "mm.rasterBase",
      0x118: "mm.RASTERW", 0x11C: "mm.rasterH", 0x120: "mm.dirty"}
SLOTNAME = {0xA4: "GetW", 0xA8: "GetH", 0xAC: "GetL", 0xB0: "GetT",
            0xB4: "GetR", 0xB8: "GetB", 0xBC: "GetArea(r&)", 0xC0: "GetArea()",
            0xC4: "GetAreaAbs(r&)", 0xC8: "GetAreaAbs()", 0xCC: "SetW",
            0xD0: "SetH", 0xD4: "SetSize", 0xD8: "SetArea(rect)",
            0xDC: "SetArea(l,t,r,b)", 0xE0: "GZWinMoveTo",
            0x98: "GetWindowFromPoint", 0x9C: "GetChildWindowFromPoint",
            0xA0: "GetChildWindowFromCursorPoint",
            0xF4: "IsPointInWindowScreenCoords",
            0xE8: "ScreenToWindowCoords", 0xEC: "WindowToScreenCoords",
            0x160: "Plot", 0x15C: "GZPaint", 0x164: "CalcAbsoluteArea",
            0x174: "GetBufferToDrawTo", 0x188: "GetAreaToDrawTo",
            0x0C: "DoMessage", 0x88: "GetChildWindowFromID",
            0x8C: "GetChildWindowFromIDRecursive"}
from capstone.x86 import X86_REG_ESP, X86_REG_EBP

def dump(va, n, label, base_bias=0):
    print("=" * 78)
    print(f"{label}  {hex(va)}   (field offsets shown +{hex(base_bias)} biased)")
    print("=" * 78)
    for ins in disasm(data, secs, va, n):
        tag = ""
        if ins.mnemonic == "call" and ins.operands and \
           ins.operands[0].type == X86_OP_MEM and ins.operands[0].mem.base not in (0, X86_REG_ESP, X86_REG_EBP):
            d = ins.operands[0].mem.disp
            if d in SLOTNAME:
                tag = f"   <<VCALL {SLOTNAME[d]}>>"
            else:
                tag = f"   <<vcall +0x{d:x}>>"
        else:
            for op in ins.operands:
                if op.type == X86_OP_MEM and op.mem.base not in (0, X86_REG_ESP):
                    d = op.mem.disp + base_bias
                    if d in RECT: tag = f"   <<< {RECT[d]}"
                    elif d in MM: tag = f"   <<< {MM[d]}"
        print(f"  0x{ins.address:08X} {ins.bytes.hex():<16} {ins.mnemonic:<7} {ins.op_str}{tag}")

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "plot"
    if which == "plot":
        dump(0x007A79B0, 0x300, "cSC4WinMiniMap::Plot (vt+0x160)")
    elif which == "setarea":
        dump(0x007A8E30, 0x200, "cSC4WinMiniMap::SetArea(l,t,r,b) (vt+0xDC)")
    elif which == "handler":
        dump(0x007A8640, 0x500, "minimap message handler (thiscall on this+0xD8)", 0xD8)
    elif which == "cells":
        dump(0x007A8800, 0x200, "data-CELL overlay region", 0xD8)
    elif which == "renderer":
        dump(0x007A2F60, 0x180, "DV renderer sub_7A2F60 head")
    elif which == "init":
        dump(0x007A8BD0, 0x200, "cSC4WinMiniMap::Init (vt+0x10)")
    elif which == "recompute":
        dump(0x007A7840, 0x120, "recompute 0x7A7840")
    else:
        dump(int(which, 16), int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x200,
             "custom", int(sys.argv[3], 16) if len(sys.argv) > 3 else 0)
