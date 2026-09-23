#!/usr/bin/env python
"""Gate: calls through the vendored gzcom-dll cIGZWin.h must land on the
slot they NAME in SimCity 4.exe 1.1.641.

WHY THIS EXISTS
---------------
The pinned gzcom-dll cIGZWin.h (submodule, 08c529bc) omits GZWinOffset and
declares SetSize(cRZPoint) next to CenterWindowInRect. MSVC pulls every
overload of a name up to the first one's slot, so the header COMPILES to a
vtable that disagrees with the exe's in two bands:

  slots 53-57   SetSize(w,h)   compiles to 54 = exe SetArea(const cRZRect&)
                SetArea(rect)  compiles to 56 = exe GZWinMoveTo
                GZWinMoveTo    compiles to 57 = exe GZWinOffset (RELATIVE)
                SetSize(pt)    compiles to 53 = exe SetSize(w,h)
  slots 118+    every declaration but CenterWindowInRect(ref) compiles one
                slot LOW (PlotPresent, the GZOn* handlers, SendMsg, PostMsg,
                IsPointInWindow*Coordinates, CenterWindowInRect(ptr)) -
                four probed below, the rest follow from the shift

GZWinMoveTo is the one we call, 21 times, and every call already passes a
DELTA - the "GZWinMoveTo moves BY, not TO" law in research\\laws was this
mislabel, learned from the screen before its cause was known. Calling any
other name in the table below would reach a different function with the
wrong arguments; SetSize(w,h) would dereference w as a cRZRect*.

THE TRUTH COLUMN. Measured 2026-09-23 three independent ways, which agree:
  1. the exe's own code at cSC4WinAlertBorder's vtable 0x00AB5B48 (slot 53
     calls slot 55 with l,t,l+w,t+h; 54 unpacks a rect into 55; 56 adds
     w,h to x,y; 57 adds dx,dy to all four edges; 118 unpacks a point into
     53; 119/120 are the two CenterWindowInRect, 120 null-tests its arg);
  2. the Mac debug-symbol vtable in 0xC0000054/sc4-ghidra-symbols
     (tools\\sdk\\ghidra\\out\\SimCity4.gdt.json), which matches (1) at
     every slot checked and puts PlotPresent at 124 = 0x0099C498, the VA
     our PlotPresentDetour found independently;
  3. this gate's compile of the header (the COMPILED column, read live).

PASS = exit 0. Needs MSVC (vcvars32) - the build machine has it.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROBE = os.path.join(ROOT, "tools", "sdk", "ghidra", "probe")
SRC = os.path.join(ROOT, "src")

# probe name -> slot the method occupies in SimCity 4.exe 1.1.641
EXE_SLOT = {
    "SetW": 51, "SetH": 52, "SetSize_wh": 53, "SetArea_rect": 54,
    "SetArea_ltrb": 55, "GZWinMoveTo": 56, "FitRectToWindow": 58,
    "GetID": 63, "SetFlag": 68, "ShowWindow": 69, "GZPaint": 88,
    "SetSize_pt": 118, "CenterWindowInRect_ref": 119,
    "CenterWindowInRect_ptr": 120, "IsPointInWindowWindowCoordinates": 121,
    "PlotPresent": 124, "GZOnCommand": 143,
}
# A mislabel we call on purpose, with the semantics of the slot it reaches.
ALLOWED = {"GZWinMoveTo": "reaches GZWinOffset: every call must pass a delta"}


def compile_probe():
    asm = os.path.join(PROBE, "vtprobe.asm")
    if os.path.exists(asm):
        os.remove(asm)
    subprocess.run(["cmd", "/c", os.path.join(PROBE, "build.cmd")], cwd=PROBE,
                   capture_output=True, text=True)
    if not os.path.exists(asm):
        sys.exit("FAIL: probe did not compile (run tools\\sdk\\ghidra\\probe\\build.cmd)")
    slots, cur = {}, None
    for line in open(asm, encoding="latin-1"):
        m = re.match(r"_probe_(\w+)\s+PROC", line)
        if m:
            cur = m.group(1)
            continue
        m = re.search(r"(?:call|jmp)\s+DWORD PTR \[e\w\w\+(\d+)\]", line)
        if cur and m:
            slots[cur] = int(m.group(1)) // 4
            cur = None
    return slots


def main():
    compiled = compile_probe()
    missing = sorted(set(EXE_SLOT) - set(compiled))
    if missing:
        sys.exit(f"FAIL: probe emitted no call for {missing} - instrument blind")

    wrong = {}
    print(f"{'method':34} compiled  exe")
    for name, exe in EXE_SLOT.items():
        c = compiled[name]
        flag = "" if c == exe else "  <-- MISLABEL"
        print(f"{name:34} {c:8}  {exe:3}{flag}")
        if c != exe:
            wrong[name.split("_")[0]] = wrong.get(name.split("_")[0], []) + [name]

    # Positive controls: the instrument must see both an agreement and the
    # known disagreement, or a clean result means nothing.
    if compiled["GetID"] != 63 or compiled["GZPaint"] != 88:
        sys.exit("FAIL: control - GetID/GZPaint no longer compile to 63/88")
    if "GZWinMoveTo" not in wrong:
        sys.exit("FAIL: control - GZWinMoveTo now compiles correctly; the header "
                 "changed, re-derive this gate and the RELATIVE call sites")

    src = ""
    for f in os.listdir(SRC):
        if f.endswith((".cpp", ".h")):
            src += re.sub(r"//.*", "", open(os.path.join(SRC, f), encoding="latin-1").read())
    bad = []
    for base in wrong:
        if base in ALLOWED:
            continue
        n = len(re.findall(r"(?:->|\.)" + base + r"\s*\(", src))
        if n:
            bad.append(f"{base} x{n}")
    print(f"\nmislabelled names: {sorted(wrong)}")
    for k, v in ALLOWED.items():
        print(f"allowed: {k} - {v}")
    if bad:
        sys.exit(f"FAIL: src calls a mislabelled cIGZWin method: {bad}")
    print("ALL PASS")


main()
