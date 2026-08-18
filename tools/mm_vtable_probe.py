#!/usr/bin/env python3
"""Recover the cSC4WinMiniMap window vtable and its OVERRIDE set, by anchoring
on the already-measured fact `Plot` (slot +0x160) == 0x007A79B0.
Then diff against the plain cGZWin vtable to separate overrides from inherited.
Read-only."""
import struct, bisect
from pe109_probe import *

data, secs = load()

IGZWIN = [
 "QueryInterface","AddRef","Release","DoMessage","Init","Shutdown",
 "GetWindowManager","SetWindowManager","GetKeyboard","SetKeyboard",
 "GetMainWindow","GetParentWin","SetParentWin","GetChildCount","ChildAdd",
 "ChildRemove","ChildDelete","ChildDeleteAbsolute","ChildDeleteAll",
 "ChildExists(win)","ChildExists(id)","IsWinInParentChain","IsWinInChildChain",
 "PullToFront","SendToBack","ChildToFront(win)","ChildToFront(id)",
 "ChildToBack","ChildStepFront","ChildStepBack","MoveRelativeTo",
 "ChildMoveRelative","EnumChildren","SortChildren","GetChildWindowFromID",
 "GetChildWindowFromIDRecursive","GetChildAs","GetChildAsRecursive",
 "GetWindowFromPoint","GetChildWindowFromPoint","GetChildWindowFromCursorPoint",
 "GetW","GetH","GetL","GetT","GetR","GetB","GetArea(rect&)","GetArea()",
 "GetAreaAbsolute(rect&)","GetAreaAbsolute()","SetW","SetH","SetSize",
 "SetArea(rect)","SetArea(l,t,r,b)","GZWinMoveTo","FitRectToWindow",
 "ScreenToWindowCoordinates","WindowToScreenCoordinates",
 "WindowToWindowCoordinates","IsPointInWindowScreenCoordinates","GetID",
 "SetID","GetInstanceID","SetInstanceID","GetFlag","SetFlag","ShowWindow",
 "HideWindow","IsVisible","IsEnabled","GetCaption","SetCaption",
 "GetKeyboardAccelerator","SetKeyboardAccelerator","AccelerateKeyboardMsg",
 "GetKeyEquivalent","SetKeyEquivalent","CheckKeyEquivalent","MakeKeyEquivalent",
 "IsChildKeyEquivalent","ProcessCursorMessage","UpdateCursor","SetCursor",
 "SetNotificationTarget","GetNotificationTarget","GZPaint","Plot",
 "CalcAbsoluteArea","InvalidateSelf","InvalidateSelfAndParents",
 "GetDrawContext","GetBufferToDrawTo","SetBufferToDrawTo",
 "SetBufferToDrawToRecursive","SetAreaToDrawTo","SetAreaToDrawToRecursive",
 "GetAreaToDrawTo","PrivateBuffer","GetPrivateBuffer","GetFillColor(c&)",
 "GetFillColor()",
]

PLOT = 0x007A79B0
hits = [v for n, v in find_dword_refs(data, secs, PLOT) if n in (".rdata", ".data")]
print(f"Plot 0x{PLOT:X} appears as a dword at: {[hex(h) for h in hits]}")
for h in hits:
    base = h - 0x160
    print(f"\n=== candidate cSC4WinMiniMap vtable base {hex(base)} "
          f"(anchor: slot +0x160 == Plot) ===")
    o = va2off(secs, base)
    slots = []
    for i in range(len(IGZWIN) + 12):
        d = struct.unpack_from("<I", data, o + i * 4)[0]
        slots.append(d)
    for i, d in enumerate(slots):
        nm = IGZWIN[i] if i < len(IGZWIN) else f"(slot {i})"
        mark = ""
        if 0x790000 <= d < 0x7B0000:
            mark = "  <== in the minimap code block 0x79-0x7A"
        print(f"  +0x{i*4:03X} {nm:<32} 0x{d:08X}{mark}")

# The base cGZWin vtable: find the vtable that supplies most of the same
# entries. Search .rdata for a table whose +0x160 differs but +0xA4..+0xB8 match.
print("\n=== base cGZWin vtable (for the OVERRIDE diff) ===")
if hits:
    base = hits[0] - 0x160
    o = va2off(secs, base)
    mm = [struct.unpack_from("<I", data, o + i * 4)[0] for i in range(len(IGZWIN))]
    # SetFlag base impl is documented as 0x0099DB6B in project notes -> slot 0x10C
    print(f"  minimap slot +0x10C (SetFlag) = 0x{mm[0x10C//4]:08X}  "
          f"(project notes: cGZWin::SetFlag base impl 0x0099DB6B)")
    # count how many candidate vtables share >=60 entries
    best = []
    for n, sva, vsize, roff, rsize in secs:
        if n != ".rdata":
            continue
        blob = data[roff:roff + rsize]
        for off in range(0, len(blob) - len(IGZWIN) * 4, 4):
            same = 0
            for i in (0x0C//4, 0xA4//4, 0xA8//4, 0xAC//4, 0xB0//4, 0xB4//4,
                      0xB8//4, 0xBC//4, 0xF8//4, 0x108//4, 0x10C//4):
                d = struct.unpack_from("<I", blob, off + i * 4)[0]
                if d == mm[i]:
                    same += 1
            if same >= 9:
                best.append((IMAGE_BASE + sva + off, same))
    print(f"  vtables sharing >=9 of 11 probe slots with the minimap vtable: "
          f"{[(hex(a), s) for a, s in best[:20]]}")
