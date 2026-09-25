"""run_idwalk_test.py - build and run idwalk_test.cpp against the CURRENT
BATCHED ID LOOKUPS block of src/UiSpike.cpp (audit A1, 2026-09-25).

    python tools/dev/idwalk/run_idwalk_test.py

The block (IdCollectCtx through the "end BATCHED ID LOOKUPS" marker) is copied
verbatim into a temp dir, so the test always runs the code that ships. Needs a
C++20 compiler, found by tools/dev/find_cxx.py: cl or clang-cl on PATH, Visual
Studio through vswhere (a plain PowerShell is enough), or g++ / clang++.
Exit 0 = PASS; 1 = FAIL; 2 = could not run (no compiler, or the markers moved).
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import find_cxx  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(REPO, "src", "UiSpike.cpp")
START = "// Collect EVERY window with the given id under root (bounded walk)."
END = "// ---- end BATCHED ID LOOKUPS"


def extract():
    lines = open(SRC, encoding="utf-8", errors="replace").read().splitlines(True)
    a = [i for i, l in enumerate(lines) if START in l]
    b = [i for i, l in enumerate(lines) if END in l]
    if len(a) != 1 or len(b) != 1 or b[0] <= a[0]:
        print("REFUSED: the block markers in src/UiSpike.cpp moved "
              "(start %d hit(s), end %d hit(s)) - fix START/END here." % (len(a), len(b)))
        sys.exit(2)
    return "".join(lines[a[0]:b[0] + 1])


def main():
    tmp = tempfile.mkdtemp(prefix="idwalk-")
    try:
        with open(os.path.join(tmp, "idwalk_block.inc"), "w", encoding="utf-8") as f:
            f.write(extract())
        test = os.path.join(HERE, "idwalk_test.cpp")
        exe = os.path.join(tmp, "idwalk_test.exe")
        cmd, how = find_cxx.build([test], exe, [tmp], want_win32=False)
        if not cmd:
            print("NOT RUN: %s." % how)
            return 2
        r = find_cxx.run_build(cmd)
        if r.returncode != 0:
            print("BUILD FAILED (%s):\n%s%s" % (how, r.stdout, r.stderr))
            return 1
        return subprocess.run([exe]).returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
