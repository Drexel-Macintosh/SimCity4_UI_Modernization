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
       "GetW": 41, "GZPaint": 88}


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
        elif name not in ("GetFillColor_void", "SetFillColor_u32"):
            ok &= before == exe and all(c != exe for c in after)
    print("\n%s" % ("REPRODUCED: right before 387a9751, wrong from 387a9751 through HEAD; controls right"
                    if ok else "NOT REPRODUCED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
