r"""Which upstream commit broke cIGZWin slots 47-50 and 102-107?

    python tools\sdk\ghidra\verify\I-issue-evidence\regression_387a9751.py

Fetches cIGZWin.h at three nsgomez/gzcom-dll commits with `gh api` into
`_cache\` (gitignored):
  4669fa92  the last version before 387a9751
  387a9751  "Fix the ordering of a few overloads in cIGZWin"
  779b669b  upstream HEAD, identical to our pin
It then compiles the gate's probe (tools\sdk\ghidra\probe\vtprobe.cpp)
against each version and compares every probe with the exe slot. Every other
header stays the pinned one. Probes for methods a version does not declare
are dropped and listed. GetW (41) and GZPaint (88) are the controls, and
must be right in all three versions.
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
CACHE = os.path.join(HERE, "_cache")
INC = os.path.join(REPO, "vendor", "gzcom-dll", "gzcom-dll", "include")
PROBE = os.path.join(REPO, "tools", "sdk", "ghidra", "probe", "vtprobe.cpp")
VCVARS = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat"
VERSIONS = ["4669fa92", "387a9751", "779b669b"]
EXE = {"GetArea_rect": 47, "GetArea_ptr": 48, "GetAreaAbsolute_rect": 49, "GetAreaAbsolute_ptr": 50,
       "GetFillColor_color": 102, "GetFillColor_void": 103, "GetFillColor_rgb": 104,
       "SetFillColor_color": 105, "SetFillColor_u32": 106, "SetFillColor_rgb": 107,
       "SetArea_rect": 54, "SetArea_ltrb": 55,
       "CenterWindowInRect_ref": 119, "CenterWindowInRect_ptr": 120,
       "GetW": 41, "GZPaint": 88}
# What the game has at the slots these probes can reach, for the change report.
GAME = {47: "GetArea(cRZRect&)", 48: "GetArea()", 49: "GetAreaAbsolute(cRZRect&)", 50: "GetAreaAbsolute()",
        54: "SetArea(const cRZRect&)", 55: "SetArea(l,t,r,b)", 56: "GZWinMoveTo", 102: "GetFillColor(cRZColor&)",
        103: "GetFillColor()", 104: "GetFillColor(r&,g&,b&)", 105: "SetFillColor(cRZColor)",
        106: "SetFillColor(uint32_t)", 107: "SetFillColor(r,g,b)", 118: "SetSize(const cRZPoint&)",
        119: "CenterWindowInRect(const cRZRect&)", 120: "CenterWindowInRect(cRZRect*)"}


def fetch(short):
    dst = os.path.join(CACHE, short, "hdr", "cIGZWin.h")
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        body = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.raw",
                               "repos/nsgomez/gzcom-dll/contents/gzcom-dll/include/cIGZWin.h?ref=" + short],
                              capture_output=True, check=True).stdout
        open(dst, "wb").write(body)
    return os.path.dirname(dst)


def compile_version(short):
    hdr = fetch(short)
    d = os.path.dirname(hdr)
    cpp = os.path.join(d, "vtprobe.cpp")
    shutil.copy(PROBE, cpp)
    cmd = os.path.join(d, "build.cmd")
    with open(cmd, "w", newline="\r\n") as f:
        f.write('@echo off\ncall "%s" >nul\ncd /d "%s"\ncl /nologo /c /O2 /FAs /I"%s" /I"%s" vtprobe.cpp\n'
                % (VCVARS, d, hdr, INC))
    asm = os.path.join(d, "vtprobe.asm")
    dropped = []
    for _ in range(8):
        if os.path.exists(asm):
            os.remove(asm)
        out = subprocess.run(["cmd", "/c", cmd], capture_output=True, text=True).stdout
        if os.path.exists(asm):
            break
        bad = sorted({int(n) for n in re.findall(r"vtprobe\.cpp\((\d+)\): error", out)})
        if not bad:
            sys.exit("%s did not compile:\n%s" % (short, out[-1500:]))
        lines = open(cpp, encoding="latin-1").read().splitlines()
        for n in bad:
            dropped.append(lines[n - 1].strip())
            lines[n - 1] = "// dropped: " + lines[n - 1]
        open(cpp, "w", encoding="latin-1").write(chr(10).join(lines) + chr(10))
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
    return slots, dropped


def main():
    res = {}
    for v in VERSIONS:
        res[v], dropped = compile_version(v)
        if dropped:
            print("%s does not declare: %s" % (v, "; ".join(dropped)))
    print("\n%-22s %4s  %s" % ("probe", "exe", "  ".join("%-10s" % v for v in VERSIONS)))
    ok = True
    for name, exe in EXE.items():
        cells = [res[v].get(name) for v in VERSIONS]
        print("%-22s %4d  %s" % (name, exe, "  ".join("%-10s" % ("%s%s" % (c, "" if c == exe else " WRONG"))
                                                        for c in cells)))
        before, *after = cells
        if name in ("GetW", "GZPaint"):
            ok &= all(c == exe for c in cells)
        elif name.startswith(("GetArea", "GetFillColor_c", "GetFillColor_r", "SetFillColor_c", "SetFillColor_r")):
            ok &= before == exe and all(c != exe for c in after)
    print("\nWhat 387a9751 changed (4669fa92 -> 387a9751):")
    for name, exe in EXE.items():
        b, a = res["4669fa92"].get(name), res["387a9751"].get(name)
        if b == a:
            continue
        verdict = ("ADDED" if b is None else "FIXED" if a == exe else "BROKE" if b == exe else "wrong before and after")
        if name == "CenterWindowInRect_ptr":
            verdict = "BROKE in effect: it used to reach the reference overload, whose ABI is the same pointer"
        print("  %-22s %s -> %s  (reached %s, now reaches %s)  %s"
              % (name, b, a, GAME.get(b, b), GAME.get(a, a), verdict))
    # The three extra changes the review found must still show.
    ok &= res["4669fa92"].get("SetArea_ltrb") == 56 and res["387a9751"].get("SetArea_ltrb") == 55
    ok &= res["4669fa92"].get("SetArea_rect") == 55 and res["387a9751"].get("SetArea_rect") == 56
    ok &= res["4669fa92"].get("CenterWindowInRect_ptr") == 119 and res["387a9751"].get("CenterWindowInRect_ptr") == 118
    # Every probe the gate knows, not just the ones above: which were already
    # wrong before 387a9751, and which did it change?
    import ast
    src = open(os.path.join(REPO, "_tests", "Test-GZWinHeaderSlots.py"), encoding="utf-8").read()
    gate = next(ast.literal_eval(n.value) for n in ast.parse(src).body
                if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "EXE_SLOT")
    wrong_now = sorted(n for n in gate if res["779b669b"].get(n) is not None and res["779b669b"][n] != gate[n])
    changed = [n for n in wrong_now if res["4669fa92"].get(n) != res["779b669b"].get(n)]
    same_before = [n for n in wrong_now if n not in changed]
    print("\nOf the %d gate probes wrong at HEAD: %d changed with 387a9751 (%s); %d compiled to the same "
          "wrong slot before it: %s" % (len(wrong_now), len(changed), ", ".join(changed), len(same_before),
                                       ", ".join(same_before)))
    print("\n%s" % ("REPRODUCED" if ok else "NOT REPRODUCED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
