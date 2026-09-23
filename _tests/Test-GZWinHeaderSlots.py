#!/usr/bin/env python
"""Gate: every cIGZWin method src\\ calls through the vendored gzcom-dll header
must compile to the slot that method REALLY occupies in SimCity 4.exe 1.1.641.

    python _tests\\Test-GZWinHeaderSlots.py             the gate
    python _tests\\Test-GZWinHeaderSlots.py --selftest  + four planted defects,
                                                       each of which must FAIL

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
           (SetFillColor(cRZColor) is also by-reference in the header where
           the exe's slot-105 function takes the colour BY VALUE.)
  118-147  every declaration except CenterWindowInRect(const cRZRect&) lands
           one slot low (CenterWindowInRect(cRZRect*) two low): PlotPresent,
           all the GZOn* handlers, SendMsg, PostMsg.

The 47-50 and 102-107 errors were INTRODUCED upstream by 387a9751 ("Fix the
ordering of a few overloads", 2026-06-27): it wrote those groups in the exe's
slot order, and MSVC reverses overload groups, so they now compile backwards.
The parent commit 26fcb160 compiles them correctly (measured 2026-09-23).

Right slot, wrong ABI (SIGNATURE_DEFECTS below): SetShadeColor (the exe takes
the colour by value), AccelerateKeyboardMsg (the exe pops one argument, the
header passes none), CheckKeyEquivalent (the exe pops two, the header passes
one). Five input handlers ALSO declare the wrong argument count, by the exe's
own DoMessage pushes and `ret N`: GZOnSetFocus (header 2, exe 1),
GZOnMouseWheel (3 vs 4), GZOnCaptureChanged (4 vs 2), GZOnMouseEnter (2 vs 1)
and GZOnCommand (1 vs 2). They are already denied here as wrong-slot; a header
fix that only moved them would still unbalance the stack.

THE TRUTH COLUMN. Measured 2026-09-23 from the exe's own code - what each
function does with its arguments, its `ret N`, and who calls it - on the cGZWin
base vtable 0x00ADC8D8 and cSC4WinAlertBorder 0x00AB5B48. Slots 50-60, 63-70,
86-89 and 115-150 were also compared across 15 window classes, and 129-143 are
additionally pinned by the exe's DoMessage jump table (0x99CEF9 routes message
types to them). Evidence scripts: tools\\sdk\\ghidra\\verify\\ (A-full-probe,
B-second-class-exe-decode).

HOW THE GATE DECIDES. It compiles the probe, reads each COMPILED slot from
MSVC's own listing, and then scans src\\ for calls to any cIGZWin method name:
  * a name with any overload on a wrong slot           -> FAIL (unless ALLOWED)
  * a name with a known ABI defect                      -> FAIL
  * a name no truth row covers                          -> FAIL: decode its exe
    slot, add a row, and only then call it
  * GZWinMoveTo (ALLOWED, it reaches GZWinOffset) with an argument that does
    not look like a delta - not 0, no subtraction, not a d*/delta name - is
    an absolute move through a relative method -> FAIL, unless the line says
    `// relative-ok: <reason>`.

LIMITS, stated so the verdict is not over-read.
  * The scan is by NAME, not by receiver type. It errs toward requiring rows,
    so its DENIALS are conservative - but a PASS on a name can come from a
    same-named method of another interface. Today three of the names it finds
    are never called on a cIGZWin at all (NOT_CIGZWIN below), and SetCaption
    is called on both a cIGZWin and a cIGZWinText; the cIGZWinText slot is
    not verified by this gate.
  * The ABI check covers only the three names listed.
  * Nothing runs this gate automatically: it is a manual gate, like the rest
    of _tests\\. Run it before any change that adds a cIGZWin call.
PASS = exit 0. Needs MSVC (vcvars32).
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

# Names the scan finds in src\ that belong to OTHER interfaces today (measured
# 2026-09-23). Informational: they still need a row, because the scan cannot
# see receivers; they are just not counted as cIGZWin calls.
NOT_CIGZWIN = {
    "Init": "Logger::Init, cIGZBuffer::Init",
    "GetMainWindow": "cISC4App::GetMainWindow",
    "IsEnabled": "Logger::IsEnabled",
}

WAIVER = "relative-ok"


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


def read_src():
    files = []
    for f in sorted(os.listdir(SRC)):
        if f.endswith((".cpp", ".h")):
            files.append((f, open(os.path.join(SRC, f), encoding="latin-1").read()))
    return files


def split_args(s, start):
    """Top-level comma split of the call whose '(' is at s[start]."""
    depth, cur, args = 0, "", []
    for ch in s[start:]:
        if ch == "(":
            depth += 1
            if depth == 1:
                continue
        elif ch == ")":
            depth -= 1
            if depth == 0:
                args.append(cur)
                return args
        if ch == "," and depth == 1:
            args.append(cur)
            cur = ""
        else:
            cur += ch
    return None     # unbalanced within the window


def looks_like_delta(arg):
    a = arg.strip()
    return (a == "0" or "-" in a
            or re.fullmatch(r"d[xylt]", a) is not None
            or re.search(r"(?i)delta|D[xy]\b", a) is not None)


def moveto_absolute_calls(files):
    bad = []
    for fname, text in files:
        lines = text.split("\n")
        for i, raw in enumerate(lines):
            code = raw.split("//")[0]
            for m in re.finditer(r"(?:->|\.)\s*GZWinMoveTo\s*\(", code):
                window = code[m.end() - 1:] + " " + " ".join(
                    l.split("//")[0] for l in lines[i + 1:i + 4])
                args = split_args(window, 0)
                if args is None or len(args) != 2:
                    bad.append(f"{fname}:{i + 1}: GZWinMoveTo call not parsed - check it by hand")
                    continue
                if all(looks_like_delta(a) for a in args):
                    continue
                if WAIVER in raw:
                    continue
                bad.append(f"{fname}:{i + 1}: GZWinMoveTo({args[0].strip()}, {args[1].strip()}) "
                           f"- an ABSOLUTE-looking argument through a RELATIVE method "
                           f"(exe slot 57 is GZWinOffset); pass a delta, or mark the line "
                           f"'// {WAIVER}: <why>'")
    return bad


def check(files, wrong, right, quiet=False):
    text = "".join(re.sub(r"//.*", "", t) for _, t in files)
    called = {}
    for n in sorted(header_names()):
        k = len(re.findall(r"(?:->|\.)" + n + r"\s*\(", text))
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
    bad += moveto_absolute_calls(files)

    if not quiet:
        real = [n for n in called if n not in NOT_CIGZWIN]
        print(f"\nsrc calls {len(called)} cIGZWin method NAMES; {len(real)} are real "
              f"cIGZWin calls ({', '.join(sorted(NOT_CIGZWIN))} belong to other "
              f"interfaces). Wrong-slot names in the header: {sorted(wrong)}")
        for k, v in ALLOWED.items():
            print(f"allowed: {k} - {v} (x{called.get(k, 0)}, every argument delta-shaped "
                  f"or waived)")
    return bad


MUTATIONS = [
    ("wrong slot", "void mut(cIGZWin* w){ w->GetArea(); }", "GetArea"),
    ("no verified row", "void mut(cIGZWin* w){ w->PullToFront(); }", "PullToFront"),
    ("ABI defect", "void mut(cIGZWin* w, cRZColor& c){ w->SetShadeColor(c); }", "SetShadeColor"),
    ("absolute move", "void mut(cIGZWin* w){ w->GZWinMoveTo(640, 480); }", "GZWinMoveTo(640"),
]


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

    files = read_src()
    bad = check(files, wrong, right)
    if bad:
        print("\n".join("  " + b for b in bad))
        sys.exit("FAIL: src calls cIGZWin methods that do not reach the slot they name")

    if "--selftest" in sys.argv:
        print("\nselftest: each planted defect must FAIL")
        for label, code, needle in MUTATIONS:
            mbad = check(files + [("MUTATION.cpp", code)], wrong, right, quiet=True)
            hit = any(needle in b for b in mbad)
            print(f"  {label:16} {'FAILS as it must' if hit else 'NOT CAUGHT'}")
            if not hit:
                sys.exit(f"FAIL: selftest - the '{label}' mutation was not caught")
    print("ALL PASS")


main()
