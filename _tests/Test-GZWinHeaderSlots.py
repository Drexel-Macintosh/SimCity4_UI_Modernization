#!/usr/bin/env python
"""Gate: every cIGZWin method src\\ calls through the vendored gzcom-dll header
must compile to the slot that method REALLY occupies in SimCity 4.exe 1.1.641.

WHY THIS EXISTS
---------------
The pinned gzcom-dll cIGZWin.h (submodule 08c529bc = upstream HEAD 779b669b,
unchanged) compiles, under MSVC, to a vtable that disagrees with the exe for 40
of its 147 declarations:

  53-57    GZWinOffset is missing, and SetSize(cRZPoint) - declared late - is
           pulled up next to SetSize(w,h) because MSVC groups every overload of
           a name at the first one's slot, in REVERSE declaration order.
           GZWinMoveTo therefore compiles to the exe's GZWinOffset (slot 57):
           that is the real reason every one of our move calls passes a DELTA
           (the "GZWinMoveTo moves BY, not TO" law in research\\laws).
           SetSize(w,h) compiles to exe SetArea(const cRZRect&).
  47-50    GetArea / GetAreaAbsolute: each pair compiles swapped. GetArea()
           reaches exe GetArea(cRZRect&), which writes 16 bytes through
           whatever is on the stack.
  102-107  GetFillColor / SetFillColor: the r,g,b and cRZColor overloads swap.
  118-147  every declaration except CenterWindowInRect(const cRZRect&) lands
           one slot low (CenterWindowInRect(cRZRect*) two low): PlotPresent,
           all the GZOn* handlers, SendMsg, PostMsg.

The 47-50 and 102-107 errors were INTRODUCED upstream by 387a9751 ("Fix the
ordering of a few overloads", 2026-06-27): it wrote those groups in the exe's
slot order, and MSVC reverses overload groups, so they now compile backwards.
The parent commit 26fcb160 compiles all eight correctly (measured 2026-09-23).

Some declarations sit on the right slot with the wrong ABI (SIGNATURE_DEFECTS
below): the exe takes colours BY VALUE, and two keyboard methods pop more
arguments than the header passes. Those are denied too.

THE TRUTH COLUMN. Measured 2026-09-23, each row from the exe's own code (what
the function does with its arguments, its `ret N`, and who calls it), on the
cGZWin base vtable 0x00ADC8D8 and cSC4WinAlertBorder 0x00AB5B48; slots
115-147 additionally from the exe's own DoMessage jump table (0x99CEF9 routes
message types to 129-143). The Mac debug-symbol vtable agrees except where
MSVC groups overloads (102-107). Evidence scripts:
tools\\sdk\\ghidra\\verify\\ (A-full-probe, B-second-class-exe-decode).

HOW THE GATE DECIDES. It compiles the probe, reads each COMPILED slot from
MSVC's own listing, and then scans src\\ for calls to any cIGZWin method name:
  * a name with any overload on a wrong slot           -> FAIL (unless ALLOWED)
  * a name with a known ABI defect                      -> FAIL
  * a name no truth row covers                          -> FAIL: decode its exe
    slot, add a row, and only then call it.
The scan is by NAME, so it is conservative: a same-named method on another
interface also has to be covered. PASS = exit 0. Needs MSVC (vcvars32).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROBE = os.path.join(ROOT, "tools", "sdk", "ghidra", "probe")
SRC = os.path.join(ROOT, "src")
HDR = os.path.join(ROOT, "vendor", "gzcom-dll", "gzcom-dll", "include", "cIGZWin.h")

# probe name -> the slot that method occupies in SimCity 4.exe 1.1.641.
EXE_SLOT = {
    # called by src\ - each decoded from its body, not its name
    "QueryInterface": 0,             # cmp riid 1 / 0x22BA0121 / 0xE98B2F57; ret 8
    "Release": 2,                    # dec [ecx+0xC]
    "Init": 4,
    "GetMainWindow": 10,             # asks the window manager [ecx+4]
    "GetParentWin": 11,              # mov eax,[ecx+0x48]
    "GetChildCount": 13,             # counts the child list [ecx+0x44]
    "EnumChildren": 32,              # walks [ecx+0x44], 3 args
    "GetChildWindowFromID": 34,      # walks children comparing child->slot63
    "GetChildWindowFromIDRecursive": 35,
    "GetW": 41, "GetH": 42,
    "GetL": 43, "GetT": 44, "GetR": 45, "GetB": 46,   # [ecx+0xA8/AC/B0/B4]
    "SetW": 51, "SetH": 52,
    "GetID": 63,                     # mov eax,[ecx+0x10]
    "GetFlag": 67, "SetFlag": 68,    # SetFlag = 0x0099DB6B
    "ShowWindow": 69, "HideWindow": 70,
    "IsVisible": 71, "IsEnabled": 72,        # GetFlag(1) / GetFlag(2)
    "GetCaption": 73, "SetCaption": 74,      # string object at [ecx+0x50]
    "GZPaint": 88,
    "InvalidateSelf": 91,            # mov byte [ecx+0x70],1
    "InvalidateSelfAndParents": 92,  # calls slot 91, then walks parents
    "AddMessageFilter": 116, "RemoveMessageFilter": 117,
    "GZWinMoveTo": 56,               # absolute; slot 57 is GZWinOffset
    # known to compile wrong (controls + the deny list)
    "GetArea_rect": 47,              # copies [ecx+0xA8..] into the arg
    "GetArea_ptr": 48,               # lea eax,[ecx+0xA8]; ret
    "GetAreaAbsolute_rect": 49, "GetAreaAbsolute_ptr": 50,
    "SetSize_wh": 53,                # SetArea(l,t,l+w,t+h)
    "SetArea_rect": 54,              # unpacks a rect into slot 55
    "SetArea_ltrb": 55,
    "FitRectToWindow": 58,
    "GetFillColor_color": 102, "GetFillColor_void": 103, "GetFillColor_rgb": 104,
    "SetFillColor_color": 105, "SetFillColor_u32": 106, "SetFillColor_rgb": 107,
    "SetSize_pt": 118,               # unpacks a point into slot 53
    "CenterWindowInRect_ref": 119,   # no null test
    "CenterWindowInRect_ptr": 120,   # null-tests its argument
    "IsPointInWindowWindowCoordinates": 121,
    "PlotPresent": 124,              # 0x0099C498 = our PlotPresentDetour VA
    "GZOnMouseWheel": 139,           # DoMessage type 14
    "GZOnCommand": 143,              # DoMessage type 3
    "SendMsg_5": 144, "SendMsg_msg": 145,
    "PostMsg_5": 146, "PostMsg_msg": 147,
}

# Right slot, wrong ABI - calling these through the header corrupts state or
# the stack even though the slot matches.
SIGNATURE_DEFECTS = {
    "SetShadeColor": "exe slot 111 stores its argument BY VALUE; the header passes a pointer",
    "AccelerateKeyboardMsg": "exe slot 77 pops one argument; the header passes none",
    "CheckKeyEquivalent": "exe slot 80 pops two arguments; the header passes one",
}

# A mislabel we call on purpose, with the semantics of the slot it reaches.
ALLOWED = {"GZWinMoveTo": "reaches exe GZWinOffset (slot 57): every call must pass a delta"}


def compile_probe():
    asm = os.path.join(PROBE, "vtprobe.asm")
    if os.path.exists(asm):
        os.remove(asm)
    r = subprocess.run(["cmd", "/c", os.path.join(PROBE, "build.cmd")], cwd=PROBE,
                       capture_output=True, text=True)
    if not os.path.exists(asm):
        sys.exit("FAIL: probe did not compile:\n" + r.stdout[-1500:])
    slots, cur = {}, None
    for line in open(asm, encoding="latin-1"):
        m = re.match(r"_probe_(\w+)\s+PROC", line)
        if m:
            cur = m.group(1)
            continue
        m = re.search(r"(?:call|jmp)\s+DWORD PTR \[e\w\w(?:\+(\d+))?\]", line)
        if cur and m:
            slots[cur] = int(m.group(1) or 0) // 4
            cur = None
    return slots


def header_names():
    text = re.sub(r"//.*", "", open(HDR, encoding="latin-1").read())
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return set(re.findall(r"virtual\s+[^;{(]*?\b(\w+)\s*\(", text)) | {
        "QueryInterface", "AddRef", "Release"}


def main():
    compiled = compile_probe()
    missing = sorted(set(EXE_SLOT) - set(compiled))
    if missing:
        sys.exit(f"FAIL: probe emitted no call for {missing} - instrument blind")

    wrong, right = {}, set()
    print(f"{'probe':34} compiled  exe")
    for name, exe in EXE_SLOT.items():
        c = compiled[name]
        base = name.split("_")[0]
        print(f"{name:34} {c:8}  {exe:3}{'' if c == exe else '  <-- WRONG SLOT'}")
        if c == exe:
            right.add(base)
        else:
            wrong.setdefault(base, []).append(name)

    # Positive controls: the instrument must see both an agreement and the
    # known disagreements, or a clean result means nothing.
    if compiled["GetID"] != 63 or compiled["GZPaint"] != 88:
        sys.exit("FAIL: control - GetID/GZPaint no longer compile to 63/88")
    for must in ("GZWinMoveTo", "GetArea", "SetSize", "PlotPresent"):
        if must not in wrong:
            sys.exit(f"FAIL: control - {must} now compiles correctly; the header "
                     "changed. Re-derive this gate (and the RELATIVE call sites).")

    src = ""
    for f in os.listdir(SRC):
        if f.endswith((".cpp", ".h")):
            src += re.sub(r"//.*", "", open(os.path.join(SRC, f), encoding="latin-1").read())
    called = {}
    for n in sorted(header_names()):
        k = len(re.findall(r"(?:->|\.)" + n + r"\s*\(", src))
        if k:
            called[n] = k
    if called.get("GetW", 0) == 0:
        sys.exit("FAIL: control - the src scan found no GetW calls; the scanner is blind")

    bad = []
    for n, k in called.items():
        if n in ALLOWED:
            continue
        if n in wrong:
            bad.append(f"{n} x{k}: compiles to the wrong exe slot ({', '.join(wrong[n])})")
        elif n in SIGNATURE_DEFECTS:
            bad.append(f"{n} x{k}: {SIGNATURE_DEFECTS[n]}")
        elif n not in right:
            bad.append(f"{n} x{k}: no exe-verified row - decode its slot before calling it")

    print(f"\nsrc calls {len(called)} cIGZWin method names; wrong-slot names in the "
          f"header: {sorted(wrong)}")
    for k, v in ALLOWED.items():
        print(f"allowed: {k} - {v} (x{called.get(k, 0)})")
    if bad:
        print("\n".join("  " + b for b in bad))
        sys.exit("FAIL: src calls cIGZWin methods that do not reach the slot they name")
    print("ALL PASS")


main()
