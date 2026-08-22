#!/usr/bin/env python3
"""LENS: every consumer that sizes itself off the Data Views map.

Scans 0x00790000-0x007B0000 for
  (a) direct field reads/writes at cIGZWin rect offsets +0x34..+0x40 on a
      register base (NOT esp/ebp - those are stack locals),
  (b) virtual calls at the cIGZWin geometry slots (GetW 0xA4 ... GetAreaAbsolute
      0xC8), and
  (c) cSC4WinMiniMap-private field touches (+0xE4 blitSize, +0xF0 surface,
      +0x104 zoom, +0x114/+0x118/+0x11C raster, +0x120 dirty).
Groups by enclosing function so a function that mixes (a|b) with (c) is flagged
as an EXTENT/STRIDE MIXING candidate - the confirmed #109 shape.

cIGZWin slot map is derived from vendor/gzcom-dll .../cIGZWin.h declaration
order. POSITIVE CONTROL: that map must independently place `Plot` at +0x160,
which is the already-measured cSC4WinMiniMap draw override 0x007A79B0.
Read-only.
"""
import sys, struct, bisect, collections
from pe109_probe import *

data, secs = load()
starts = function_starts(data, secs)
S = sorted(starts)

def encl(va):
    i = bisect.bisect_right(S, va) - 1
    return S[i] if i >= 0 else None

# ---- cIGZWin vtable slot map from the header's declaration order ----------
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
SLOT = {i * 4: n for i, n in enumerate(IGZWIN)}
print("POSITIVE CONTROL for the slot map:")
print(f"  slot +0x160 = {SLOT.get(0x160)!r}  (must be 'Plot' == the measured "
      f"cSC4WinMiniMap draw override 0x007A79B0)")
assert SLOT.get(0x160) == "Plot", "slot map is wrong - refusing to report"
GEOM_SLOTS = {0xA4, 0xA8, 0xAC, 0xB0, 0xB4, 0xB8, 0xBC, 0xC0, 0xC4, 0xC8}
SET_SLOTS = {0xCC, 0xD0, 0xD4, 0xD8, 0xDC, 0xE0}
HIT_SLOTS = {0x98, 0x9C, 0xA0, 0xF4, 0xE8, 0xEC, 0xF0}

RECT_F = {0x34: "rect.L", 0x38: "rect.T", 0x3C: "rect.R", 0x40: "rect.B"}
MM_F = {0xE0: "mmFlags", 0xE4: "blitSize", 0xF0: "surface", 0xF4: "lockObj",
        0xFC: "initLatch", 0x104: "zoom", 0x114: "rasterBase",
        0x118: "rasterW", 0x11C: "rasterH", 0x120: "dirtyMask"}

LO, HI = 0x00790000, 0x007B0000

# capstone reg ids for esp/ebp
from capstone.x86 import X86_REG_ESP, X86_REG_EBP

buckets = collections.defaultdict(lambda: {"rect": [], "geom": [], "set": [],
                                           "hit": [], "mm": [], "abs": []})

off = va2off(secs, LO)
blob = data[off: off + (HI - LO)]
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

# Linear sweep from each known function start inside the window, so decode is
# aligned. Fall back to a raw linear sweep for gaps.
covered = set()
fn_in_range = [s for s in S if LO <= s < HI]
print(f"\n{len(fn_in_range)} known function starts in [{hex(LO)},{hex(HI)})")

def sweep(start, end):
    o = va2off(secs, start)
    for ins in md.disasm(data[o:o + (end - start)], start):
        if ins.address in covered:
            continue
        covered.add(ins.address)
        fn = encl(ins.address)
        b = buckets[fn]
        if ins.mnemonic == "call" and ins.operands and \
           ins.operands[0].type == X86_OP_MEM and ins.operands[0].mem.base and \
           ins.operands[0].mem.base not in (X86_REG_ESP, X86_REG_EBP):
            d = ins.operands[0].mem.disp
            if d in GEOM_SLOTS:
                b["geom"].append((ins.address, SLOT[d], d))
            elif d in SET_SLOTS:
                b["set"].append((ins.address, SLOT[d], d))
            elif d in HIT_SLOTS:
                b["hit"].append((ins.address, SLOT[d], d))
        else:
            for op in ins.operands:
                if op.type != X86_OP_MEM:
                    continue
                if op.mem.base in (0, X86_REG_ESP, X86_REG_EBP):
                    continue
                d = op.mem.disp
                if d in RECT_F:
                    b["rect"].append((ins.address, RECT_F[d], ins.mnemonic, ins.op_str))
                elif d in MM_F:
                    b["mm"].append((ins.address, MM_F[d], ins.mnemonic, ins.op_str))

for i, s in enumerate(fn_in_range):
    e = fn_in_range[i + 1] if i + 1 < len(fn_in_range) else HI
    sweep(s, min(e, HI))

print("\n" + "=" * 78)
print("FUNCTIONS IN 0x790000-0x7B0000 TOUCHING cIGZWin RECT *AND/OR* MINIMAP FIELDS")
print("=" * 78)
rows = []
for fn, b in sorted(buckets.items(), key=lambda kv: (kv[0] or 0)):
    if not (b["rect"] or b["geom"] or b["mm"] or b["set"]):
        continue
    rows.append((fn, b))
print(f"{len(rows)} functions\n")
for fn, b in rows:
    mmset = sorted({x[1] for x in b["mm"]})
    geoms = sorted({x[1] for x in b["geom"]})
    sets = sorted({x[1] for x in b["set"]})
    rects = sorted({x[1] for x in b["rect"]})
    flag = ""
    extent = bool(geoms) or bool(rects)
    stride = any(k in mmset for k in ("blitSize", "rasterW", "rasterBase", "surface"))
    if extent and stride:
        flag = "   <<<<<< EXTENT+STRIDE IN THE SAME FUNCTION"
    print(f"{hex(fn)}  geom={geoms} rectFields={rects} set={sets} mm={mmset}{flag}")
