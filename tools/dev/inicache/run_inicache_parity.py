"""run_inicache_parity.py - IniCache against the real profile API (audit B8).

    python tools/dev/inicache/run_inicache_parity.py

Builds inicache_parity.cpp with src/IniCache.cpp and runs it over the
built-in edge cases plus the two inis that ship: _packaging/SC4UIScale.ini
and the starter ini the DLL seeds (kStarterIni, extracted from ScaleTier.cpp
the same way Test-ShippingIniKeys reads it). Every lookup is asked of both
IniCache and GetPrivateProfileStringW/StringA/IntW; any difference fails.

Exit 0 = PASS on Windows. 1 = FAIL. 2 = parity not proven here: off Windows
the model check runs, and with MinGW-w64 + Wine installed the parity check
runs under Wine, which is a model of Windows and not Windows.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.dirname(HERE))
import find_cxx  # noqa: E402


def starter_ini(tmp):
    spec = importlib.util.spec_from_file_location(
        "sik", os.path.join(REPO, "_tests", "Test-ShippingIniKeys.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    text = mod.starter_ini_text()
    if not text:
        return None
    path = os.path.join(tmp, "starter.ini")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", "\r\n"))
    return path


def main():
    tmp = tempfile.mkdtemp(prefix="inicache-")
    try:
        src = os.path.join(REPO, "src")
        test = os.path.join(HERE, "inicache_parity.cpp")
        corpus = [os.path.join(REPO, "_packaging", "SC4UIScale.ini")]
        st = starter_ini(tmp)
        if st:
            corpus.append(st)
        else:
            print("note: kStarterIni not found in ScaleTier.cpp - corpus is short one file")

        # 1. the model check, wherever a compiler exists
        model = os.path.join(tmp, "model.exe")
        cmd, how = find_cxx.build([test], model, [src], want_win32=False)
        verdict = 2
        if os.name != "nt":
            if not cmd:
                print("NOT RUN: %s." % how)
                return 2
            r = find_cxx.run_build(cmd)
            if r.returncode != 0:
                print("BUILD FAILED (%s):\n%s%s" % (how, r.stdout, r.stderr))
                return 1
            rc = subprocess.run([model]).returncode
            if rc == 1:
                return 1

        # 2. parity with the real API: Windows, or Wine as a model of it
        exe = os.path.join(tmp, "parity.exe")
        cmd, how = find_cxx.build([test, os.path.join(src, "IniCache.cpp")], exe, [src],
                                  want_win32=True)
        if not cmd:
            print("parity NOT RUN: %s." % how)
            return 2
        if os.name != "nt" and not shutil.which("wine"):
            print("parity NOT RUN: no Wine to run the Win32 build here.")
            return 2
        r = find_cxx.run_build(cmd)
        if r.returncode != 0:
            print("BUILD FAILED (%s):\n%s%s" % (how, r.stdout, r.stderr))
            return 1
        run = [exe] + corpus if os.name == "nt" else ["wine", exe] + corpus
        env = dict(os.environ, WINEDEBUG="-all")
        rc = subprocess.run(run, env=env).returncode
        if rc != 0:
            return 1
        verdict = 0 if os.name == "nt" else 2
        if verdict == 2:
            print("(exit 2: parity held under Wine; the Windows run is the one that counts)")
        return verdict
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
