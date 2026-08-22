#!/usr/bin/env python3
"""AUDIT THE INSTRUMENT: verify the cIGZWin slot map by disassembling the base
implementations the minimap vtable inherits. GetW/GetH/GetL/GetT/GetR/GetB must
provably read +0x34..+0x40. Also settles the project note that calls
0x0099DB6B 'cGZWin::SetFlag'. Read-only."""
from pe109_probe import *

data, secs = load()

CHECK = [
    (0x0099C81B, "slot+0xA4 claimed GetW  -> expect [+0x3C]-[+0x34]"),
    (0x0099C82A, "slot+0xA8 claimed GetH  -> expect [+0x40]-[+0x38]"),
    (0x0099BC53, "slot+0xAC claimed GetL  -> expect [+0x34]"),
    (0x00994EE4, "slot+0xB0 claimed GetT  -> expect [+0x38]"),
    (0x0099BC5A, "slot+0xB4 claimed GetR  -> expect [+0x3C]"),
    (0x0099BC61, "slot+0xB8 claimed GetB  -> expect [+0x40]"),
    (0x0099BCE1, "slot+0xC0 claimed GetArea() -> expect lea eax,[ecx+0x34]"),
    (0x0099BC68, "slot+0xCC claimed SetW"),
    (0x0099BDBB, "slot+0x10C claimed SetFlag"),
    (0x0099DB6B, "slot+0x110 claimed ShowWindow (project notes call this SetFlag)"),
    (0x009D7D97, "slot+0xD8 claimed SetArea(rect) - does it thunk to +0xDC?"),
    (0x007A8E30, "slot+0xDC cSC4WinMiniMap::SetArea(l,t,r,b) OVERRIDE"),
]
for va, label in CHECK:
    print("=" * 74)
    print(f"{hex(va)}  {label}")
    for ins in disasm(data, secs, va, 0x60)[:22]:
        print(f"   0x{ins.address:08X}  {ins.bytes.hex():<14} {ins.mnemonic:<7} {ins.op_str}")
        if ins.mnemonic in ("ret", "jmp"):
            break
