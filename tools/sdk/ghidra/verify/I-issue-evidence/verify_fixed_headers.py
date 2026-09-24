r"""Verify a fixed gzcom-dll checkout against the game, method by method.

    python tools\sdk\ghidra\verify\I-issue-evidence\verify_fixed_headers.py [fork-root]

Default fork root: C:\dev\gzcom-dll-fork (branch fix-vtable-order).

cIGZWin: every virtual declared in the fork's cIGZWin.h is compiled through a
call-site probe (MSVC, x86, /O2). Each slot is read from the call displacement
and must equal the game's slot for that method. The game's table is
cigzwin_consolidated.json (all 147 positions identified), plus the fix's
renamed or added methods. Each method's argument bytes must also equal the
game function's own `ret N`, wherever the census could read it
(A-full-probe\exe_argc.txt).

cIGZApp and the director classes: every method must compile to the slot
app_director.py measured in the game.

Finally, every .cpp in the fork's src\ must still compile.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.dirname(HERE)
FORK = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\gzcom-dll-fork"
INC = os.path.join(FORK, "gzcom-dll", "include")
SRC = os.path.join(FORK, "gzcom-dll", "src")
VCVARS = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat"
WORK = os.path.join(HERE, "_cache", "fixed-probe")
os.makedirs(WORK, exist_ok=True)
FAIL = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok:
        FAIL.append(msg)


def strip(s):
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return re.sub(r"//[^\n]*", " ", s)


def params_of(p):
    p = p.strip()
    return [] if p in ("", "void") else [x.strip() for x in p.split(",")]


def canon(param):
    param = re.sub(r"\b\w+::", "", param)       # cIGZWin::tWinFlag == tWinFlag
    toks = re.findall(r"[A-Za-z_]\w*|[*&]", param.split("=")[0])
    idents = [t for t in toks if t not in ("*", "&", "const")]
    if len(idents) >= 2:           # drop the parameter name
        toks.remove(idents[-1])
    return " ".join(sorted(toks))


def virtuals(path, cls):
    text = strip(open(path, encoding="latin-1").read())
    body = text[text.index("class " + cls):]
    out = []
    for m in re.finditer(r"virtual\s+([^;{(]*?)\b(~?\w+)\s*\(([^()]*)\)\s*(const)?\s*=\s*0", body):
        out.append(dict(ret=m.group(1).strip(), name=m.group(2), params=params_of(m.group(3)),
                        const=bool(m.group(4))))
    return out


NESTED = {"tWinFlag", "EnumChildrenCallback", "SortChildrenCallback", "EnumParamsCallback",
          "ClassObjectEnumerationCallback"}


def synth(param, cls):
    t = re.sub(r"\b\w+\s*$", "", param.split("=")[0]).strip() if re.search(r"[\w*&]\s+\w+\s*$", param) else param
    base = t.replace("&", "").replace("const", "").strip()
    for n in NESTED:
        base = re.sub(r"\b%s\b" % n, "%s::%s" % (cls, n), base)
    if "&" in t:
        return "*(%s*)0" % base
    if base == "cRZColor":
        return "cRZColor()"
    return "(%s)0" % base


def compile_probes(lines, name):
    cpp = os.path.join(WORK, name + ".cpp")
    with open(cpp, "w", encoding="latin-1") as f:
        f.write("\n".join(lines) + "\n")
    cmd = os.path.join(WORK, name + ".cmd")
    with open(cmd, "w", newline="\r\n") as f:
        f.write('@echo off\ncall "%s" >nul\ncd /d "%s"\ncl /nologo /c /O2 /FAs /EHsc /std:c++17 /I"%s" %s.cpp\n'
                % (VCVARS, WORK, INC, name))
    out = subprocess.run(["cmd", "/c", cmd], capture_output=True, text=True).stdout
    asm = os.path.join(WORK, name + ".asm")
    if "error" in out.lower() and not os.path.exists(asm):
        sys.exit("probe %s did not compile:\n%s" % (name, out[-2000:]))
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


# ------------------------------------------------------------------ cIGZWin
print("cIGZWin.h (%s)" % INC)
C = json.load(open(os.path.join(HERE, "cigzwin_consolidated.json")))
expected = {}
for x in C["wrong"] + C["right"]:
    m = re.match(r"\s*(.*?)\b(\w+)\s*\((.*)\)", x["sig"])
    expected[(m.group(2), tuple(canon(p) for p in params_of(m.group(3))))] = x["exe"]
FIXED = {  # methods the fix renames, adds or re-types -> the game's slot
    ("GZWinOffset", ("int32_t", "int32_t")): 57,
    ("SetSizeFromPoint", ("& cRZPoint const",)): 118,
    ("AccelerateKeyboardMsg", ("& cGZMessage const",)): 77,
    ("CheckKeyEquivalent", ("uint32_t", "uint32_t")): 80,
    ("SetFillColor", ("cRZColor",)): 105,
    ("SetShadeColor", ("cRZColor",)): 111,
    ("GZOnSetFocus", ("* cIGZWin",)): 132,
    ("GZOnMouseWheel", ("int32_t", "int32_t", "uint32_t", "int32_t")): 139,
    ("GZOnCaptureChanged", ("* cIGZWin", "* cIGZWin")): 140,
    ("GZOnMouseEnter", ("* cIGZWin",)): 141,
    ("GZOnCommand", ("uint32_t", "uint32_t")): 143,
}
expected.update(FIXED)
argc = {}
for line in open(os.path.join(V, "A-full-probe", "exe_argc.txt"), encoding="utf-8"):
    m = re.match(r"\s*(\d+) 0x[0-9a-f]+ exe=\s*(\d+)", line)
    if m:
        argc[int(m.group(1))] = int(m.group(2))
BYTES = {"cRZRect": 16, "cRZPoint": 8, "int64_t": 8, "uint64_t": 8, "double": 8}

decls = virtuals(os.path.join(INC, "cIGZWin.h"), "cIGZWin")
lines = ['#include "cIGZWin.h"', '#include "cRZRect.h"', '#include "cRZPoint.h"', '#include "cGZMessage.h"',
         "class cRZColor { public: unsigned char r, g, b, a; };"]
for i, d in enumerate(decls):
    lines.append('extern "C" void __cdecl probe_d%d(cIGZWin* w) { w->%s(%s); }'
                 % (i, d["name"], ", ".join(synth(p, "cIGZWin") for p in d["params"])))
got = compile_probes(lines, "cigzwin_fixed")
bad, abi_bad, unknown = [], [], []
for i, d in enumerate(decls):
    key = (d["name"], tuple(canon(p) for p in d["params"]))
    slot = got.get("d%d" % i)
    exp = expected.get(key)
    if exp is None:
        unknown.append(key)
        continue
    if slot != exp:
        bad.append("%s%s compiles to %s, game %s" % (key[0], key[1], slot, exp))
    nbytes = sum(4 if ("&" in p or "*" in p) else BYTES.get(canon(p).replace("const", "").strip(), 4)
                 for p in d["params"])
    if exp in argc and argc[exp] * 4 != nbytes:
        abi_bad.append("%s: header pushes %d bytes, game pops %d" % (key[0], nbytes, argc[exp] * 4))
check(not unknown, "every declaration maps to a known game slot (%d declarations)" % len(decls))
for u in unknown:
    print("        unmapped: %s%s" % u)
check(not bad, "every declaration compiles to the game's slot")
for b in bad:
    print("        " + b)
check(not abi_bad, "argument bytes match the game's `ret N` at every slot where the census reads one")
for b in abi_bad:
    print("        " + b)
covered = sorted(expected[(d["name"], tuple(canon(p) for p in d["params"]))] for d in decls
                 if (d["name"], tuple(canon(p) for p in d["params"])) in expected)
check(covered == list(range(3, 148)), "the declarations cover game slots 3-147 exactly once each")

# --------------------------------------------------------- cIGZApp + director
print("\ncIGZApp.h, cIGZCOMDirector.h, cRZCOMDllDirector.h")
APP = {"AsIGZSystemService": 3, "AddApplicationService": 4, "ModuleName": 5, "PreFrameWorkInit": 6,
       "PostFrameWorkInit": 7, "GZRun": 8, "PreFrameWorkShutdown": 9, "FrameWork": 10,
       "AddDynamicLibrariesHere": 11, "AddCOMDirectorsHere": 12, "AddApplicationServicesHere": 13,
       "LoadRegistry": 14}
DIR = {"InitializeCOM": 3, "OnStart": 4, "EnumClassObjects": 5, "GetClassObject": 6, "CanUnloadNow": 7,
       "OnUnload": 8, "RefCount": 9, "RemoveRef": 10, "FrameWork": 11, "GZCOM": 12, "GetDirectorID": 13,
       "GetLibraryPath": 14, "GetHeapAllocatedSize": 15}
lines = ['#include "cIGZApp.h"', '#include "cRZCOMDllDirector.h"', '#include "cIGZString.h"']
for d in virtuals(os.path.join(INC, "cIGZApp.h"), "cIGZApp"):
    lines.append('extern "C" void __cdecl probe_app_%s(cIGZApp* a) { a->%s(%s); }'
                 % (d["name"], d["name"], ", ".join(synth(p, "cIGZApp") for p in d["params"])))
for d in virtuals(os.path.join(INC, "cIGZCOMDirector.h"), "cIGZCOMDirector"):
    lines.append('extern "C" void __cdecl probe_dir_%s(cIGZCOMDirector* p) { p->%s(%s); }'
                 % (d["name"], d["name"], ", ".join(synth(p, "cIGZCOMDirector") for p in d["params"])))
lines.append('extern "C" void __cdecl probe_rz_GetDirectorID(cRZCOMDllDirector* p) { p->GetDirectorID(); }')
lines.append('extern "C" void __cdecl probe_rz_delete(cRZCOMDllDirector* p) { delete p; }')
got = compile_probes(lines, "app_dir_fixed")
check(all(got.get("app_" + n) == s for n, s in APP.items()) and len([k for k in got if k.startswith("app_")]) == 12,
      "cIGZApp: all 12 methods on the game's slots 3-14 (11-13 in the Mac symbols' order)")
for n, s in APP.items():
    if got.get("app_" + n) != s:
        print("        %s compiles to %s, game %s" % (n, got.get("app_" + n), s))
check(all(got.get("dir_" + n) == s for n, s in DIR.items()) and "dir_AddDirector" not in got,
      "cIGZCOMDirector: 13 methods on slots 3-15, GetDirectorID at 13, no AddDirector")
check(got.get("rz_GetDirectorID") == 13 and got.get("rz_delete") == 16,
      "cRZCOMDllDirector: GetDirectorID reaches 13 and the deleting destructor 16, as in the game")

# ------------------------------------------------------- the library still builds
print("\nfork src\\*.cpp still compile")
srcs = [f for f in sorted(os.listdir(SRC)) if f.endswith(".cpp")]
cmd = os.path.join(WORK, "build_src.cmd")
with open(cmd, "w", newline="\r\n") as f:
    f.write('@echo off\ncall "%s" >nul\ncd /d "%s"\n' % (VCVARS, WORK))
    for s in srcs:
        f.write('cl /nologo /c /EHsc /std:c++17 /I"%s" "%s" >> build_src.log 2>&1\n' % (INC, os.path.join(SRC, s)))
log = os.path.join(WORK, "build_src.log")
if os.path.exists(log):
    os.remove(log)
subprocess.run(["cmd", "/c", cmd], capture_output=True, text=True)
errs = [l for l in open(log, encoding="latin-1") if re.search(r"\berror\b", l)]
check(not errs, "%d source files compile with the fixed headers" % len(srcs))
for e in errs[:10]:
    print("        " + e.rstrip())

print("\n%s" % ("ALL CHECKS PASS" if not FAIL else "%d FAILED" % len(FAIL)))
sys.exit(1 if FAIL else 0)
