"""find_cxx.py - find a C++20 compiler for the offline C++ tests.

Used by tools/dev/idwalk/run_idwalk_test.py and
tools/dev/inicache/run_inicache_parity.py (2026-09-25 audit), so both run
from a plain PowerShell as well as from a Visual Studio developer prompt.

    build(sources, exe, includes, want_win32) -> (cmd_or_None, why)

Search order: cl / clang-cl on PATH (a developer prompt), then Visual Studio
through vswhere + vcvars32.bat (x86, the game's architecture), then g++ /
clang++. `want_win32` means the program calls the Win32 API: on a
non-Windows host it then needs a MinGW-w64 cross compiler, and the result
runs under Wine only.
"""
import os
import shutil
import subprocess
import tempfile

VSWHERE = os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                       "Microsoft Visual Studio", "Installer", "vswhere.exe")


def _vcvars32():
    if os.name != "nt" or not os.path.isfile(VSWHERE):
        return None
    try:
        path = subprocess.run(
            [VSWHERE, "-latest", "-products", "*", "-requires",
             "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
             "-property", "installationPath"],
            capture_output=True, text=True).stdout.strip()
    except OSError:
        return None
    bat = os.path.join(path, "VC", "Auxiliary", "Build", "vcvars32.bat") if path else ""
    return bat if bat and os.path.isfile(bat) else None


def build(sources, exe, includes, want_win32):
    """A command list (or a cmd /c string on Windows) that builds `exe`."""
    inc_cl = []
    inc_gnu = []
    for i in includes:
        inc_cl += ["/I", i]
        inc_gnu += ["-I", i]
    outdir = os.path.dirname(exe)
    cl_args = ["/nologo", "/std:c++20", "/EHsc", "/O1", "/DUNICODE", "/D_UNICODE"] + inc_cl \
        + sources + ["/Fe" + exe, "/Fo" + outdir + os.sep]
    if os.name == "nt":
        for cl in ("cl", "clang-cl"):
            if shutil.which(cl):
                return [cl] + cl_args, cl
        bat = _vcvars32()
        if bat:
            quoted = " ".join('"%s"' % a if " " in a else a for a in ["cl"] + cl_args)
            return 'cmd /s /c ""%s" >nul && %s"' % (bat, quoted), "Visual Studio (vcvars32)"
        for cxx in ("g++", "clang++"):
            if shutil.which(cxx):
                return [cxx, "-std=c++20", "-O1", "-DUNICODE", "-D_UNICODE"] + inc_gnu \
                    + sources + ["-o", exe], cxx
        return None, "no cl, clang-cl, Visual Studio or g++ found"
    if want_win32:
        mingw = shutil.which("x86_64-w64-mingw32-g++")
        if not mingw:
            return None, "the Win32 build needs x86_64-w64-mingw32-g++ off Windows"
        # MinGW's header is windows.h; the sources say Windows.h, which a
        # case-sensitive file system does not find. A one-line shim does.
        shim = tempfile.mkdtemp(prefix="cxxshim-")
        with open(os.path.join(shim, "Windows.h"), "w") as f:
            f.write("#include <windows.h>\n")
        return [mingw, "-std=c++20", "-O1", "-static", "-DUNICODE", "-D_UNICODE",
                "-Wno-cast-function-type", "-I", shim] + inc_gnu + sources + ["-o", exe], \
            "MinGW-w64 (runs under Wine)"
    for cxx in ("g++", "clang++"):
        if shutil.which(cxx):
            return [cxx, "-std=c++20", "-O1"] + inc_gnu + sources + ["-o", exe], cxx
    return None, "no g++ or clang++ on PATH"


def run_build(cmd):
    if isinstance(cmd, str):
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return subprocess.run(cmd, capture_output=True, text=True)
