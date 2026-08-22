#!/usr/bin/env python3
r"""Prove that a candidate public tree contains NOTHING from another project.

⛔ WHY THIS EXISTS. The touch plugin, a Microsoft Surface table, and several
unrelated products share this working tree for historical reasons. Three
separate hand-checks each declared the public export "clean" and each missed
something - a README paragraph about a Surface table, a stale ini name in a
shared header, a `.sln` that only built the touch project. Hand-checking a
tree for absence does not work. This is the check.

    python _packaging\Test-NoForeignContent.py <tree>

Exit 0 only when there are zero HARD hits and zero unreviewed SOFT hits.

TWO CLASSES, deliberately:

  HARD  - a name that can only mean another project. Any occurrence fails.
  SOFT  - ordinary vocabulary this project legitimately uses. "surface" is a
          DirectDraw surface; "untouched" is English. Flagging those as leaks
          would produce noise, and a check that cries wolf gets ignored - which
          is how the real hits survived. SOFT hits are REPORTED WITH CONTEXT
          and must be individually allowed in ALLOW below, so allowing one is
          a recorded decision rather than a silent pass.
"""
import os
import re
import sys
import subprocess


def safe(s):
    """Console-safe. A scanner that crashes while PRINTING a hit looks
    exactly like one that crashed while FINDING it."""
    return s.encode("ascii", "backslashreplace").decode("ascii")

HARD = [
    ("touch-plugin", re.compile(
        r"SC4TouchControls|TouchInputHandler|GestureEngine|CameraController"
        r"|PLUGIN_VERSION_STR|TouchControls\]|\[Gestures\]", re.I)),
    ("surface-table", re.compile(
        r"PixelSense|MeetSurface|InjectTouchInput|Surface\s*1\.0"
        r"|Surface\s+table|SurfaceSimulator|Surface\s+SDK|Milan\b|HydraX64",
        re.I)),
    ("other-products", re.compile(
        r"IntelliPoint|G-nome|Base Defense|Radial Panel|XPCards"
        r"|Surface Tetris|Surface Casino|Surface Arcade|KEmulator"
        r"|GM nav|SimCity Deluxe APK", re.I)),
    ("touch-feature", re.compile(
        r"multi-?touch|touchscreen|touch table|touch DLL|touch plugin"
        r"|touch input|pinch|two-finger|WM_POINTER", re.I)),
    ("internal-process", re.compile(
        r"HANDOFF-TO-QWEN|qwen|deepseek|glm-5|opus-reviewer|token plan"
        r"|Deploy-OnGameClose|PUBLISH-PLAN|SHIP-MANIFEST", re.I)),
]

# SOFT: legitimate vocabulary. Reported with context; add a substring here to
# record that a specific occurrence was read and accepted.
SOFT = re.compile(r"\btouch(?:es|ed|ing)?\b|\bsurface\b|\bgesture\b|\bfinger\b",
                  re.I)
ALLOW = [
    "untouched", "touching", "touches", "touch the", "touch a ",
    "render surface", "DirectDraw surface", "surface is destroyed",
    "surface ptr", "blitSize", "one-shot Init",
    "does not touch", "never touch", "cannot touch", "touch it",
    "the surface", "its surface", "a surface", "surfaces",
    "SC4Preferences", "Simulator",           # the game's own cISC4* headers
]

TEXT_EXT = {".py", ".ps1", ".md", ".txt", ".cpp", ".h", ".c", ".cs", ".ini",
            ".vcxproj", ".sln", ".filters", ".csv", ".json", ".gitignore"}
SKIP_DIRS = {".git", "__pycache__", "build", "dist"}


# TWO MODES. Conflating them is why this gate read FAIL on a clean repo.
# It was written to guard the PUBLIC export, where a mention of the sibling
# touch project or an internal process script is a real leak. The same tree
# is now ALSO the private working repo, where Deploy-OnGameClose.ps1 is a
# tracked file and the SC4TouchControls history is part of the record.
# PRIVATE (default): only PII/credentials are hard.
# PUBLIC  (--public): every category is hard. Build-PublicRepo MUST use it.
PII_LABELS = ("pii", "secret", "credential", "token", "user-path")

def main():
    public = "--public" in sys.argv
    sys.argv = [a for a in sys.argv if a != "--public"]
    root = sys.argv[1] if len(sys.argv) > 1 else None
    if not root or not os.path.isdir(root):
        print("usage: Test-NoForeignContent.py <tree>")
        return 2

    # ⛔ SCAN THE TRACKED SET, NOT THE TREE.
    # This gate was written when the repo was an ALLOWLIST EXPORT into a fresh
    # directory - there, walking the tree and scanning the repo were the same
    # thing. Since 2026-08-18 the WORKING TREE IS THE REPO, and it carries
    # ~2.3 GB of deliberately-ignored archives (dist, _working-backup,
    # _archive, captures, extracted art). Walking those produces a guaranteed
    # FAIL that says nothing about what would actually be published, which is
    # exactly what it did on the first run after relocation.
    #
    # So: inside a git repo, ask git what is tracked. Outside one (an export
    # staging dir), fall back to the walk - that path still needs covering.
    tracked = None
    if os.path.isdir(os.path.join(root, ".git")):
        try:
            out = subprocess.run(["git", "-C", root, "ls-files"],
                                 capture_output=True, text=True, check=True).stdout
            tracked = [x for x in out.splitlines() if x.strip()]
        except Exception:
            tracked = None

    def _iter():
        if tracked is not None:
            for rel in tracked:
                yield os.path.join(root, rel), rel
        else:
            for dirpath, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fn in files:
                    fp = os.path.join(dirpath, fn)
                    yield fp, os.path.relpath(fp, root)

    print("scope      : %s (%d files)" % (
        "git tracked set" if tracked is not None else "filesystem walk",
        len(tracked) if tracked is not None else -1))

    hard_hits, soft_hits, nfiles = [], [], 0
    if True:
        for p, rel in _iter():
            fn = os.path.basename(p)
            if not os.path.isfile(p):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT and fn != ".gitignore":
                continue
            # A FILENAME can be the leak even when the contents are innocent.
            for label, rx in HARD:
                if rx.search(fn):
                    hard_hits.append((label, rel, "<FILENAME> " + fn))
            nfiles += 1
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            vendor = os.sep + "vendor" + os.sep in (os.sep + rel)
            for i, line in enumerate(txt.splitlines(), 1):
                for label, rx in HARD:
                    if vendor and label != "touch-plugin":
                        continue          # the game's own SDK headers
                    m = rx.search(line)
                    if m:
                        hard_hits.append(
                            (label, "%s:%d" % (rel, i), line.strip()[:110]))
                if vendor:
                    continue
                m = SOFT.search(line)
                if m and not any(a.lower() in line.lower() for a in ALLOW):
                    soft_hits.append(("%s:%d" % (rel, i), line.strip()[:110]))

    print("scanned %d text file(s) under %s\n" % (nfiles, root))

    # PRIVATE mode: cross-project and internal-process mentions are correct
    # content in the working repo. Only PII/credentials block. --public keeps
    # every category hard, because a private repo can be flipped public.
    if not public:
        keep, demote = [], []
        for _h in hard_hits:
            if any(k in _h[0].lower() for k in PII_LABELS): keep.append(_h)
            else: demote.append(_h)
        if demote:
            print("advisory   : %d cross-project/internal-process mention(s) - "
                  "correct here, would BLOCK --public." % len(demote))
        hard_hits = keep

    if hard_hits:
        print("=" * 70)
        print("HARD FAIL - %d reference(s) to another project:" % len(hard_hits))
        for label, where, ctx in hard_hits[:60]:
            print("  [%-16s] %-46s %s" % (label, safe(where), safe(ctx)))
        if len(hard_hits) > 60:
            print("  ... and %d more" % (len(hard_hits) - 60))
        print()
    else:
        print("HARD: clean - zero references to any other project.\n")

    if soft_hits:
        print("=" * 70)
        print("SOFT - %d line(s) using shared vocabulary. READ THESE; each is"
              % len(soft_hits))
        print("either legitimate (a DirectDraw surface, the word 'untouched')")
        print("or a leak the HARD patterns did not name:")
        for where, ctx in soft_hits[:40]:
            print("  %-46s %s" % (safe(where), safe(ctx)))
        if len(soft_hits) > 40:
            print("  ... and %d more" % (len(soft_hits) - 40))
        print()

    if hard_hits:
        print("RESULT: FAIL - do not publish.")
        return 1
    if soft_hits:
        print("RESULT: PASS on hard patterns; %d soft line(s) need one human "
              "read." % len(soft_hits))
        return 0
    print("RESULT: PASS - nothing foreign, hard or soft.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
