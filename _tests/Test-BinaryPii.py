#!/usr/bin/env python3
r"""Byte-scan a release bundle for personal data - ASCII **and UTF-16**.

⛔ WHY THIS EXISTS. Every other privacy check in this repo reads files as TEXT,
so all of them are blind to a compiled binary. On 2026-08-05 the v2.93.0 bundle
was declared clean by two independent TEXT scanners and still carried this, in
`.rdata`, as a UTF-16LE string:

    C:\Users\<user>\...\vendor\gzcom-dll\...\cRZCOMDllDirector.cpp

Source: plain `assert()` in the vendored SDK. Without NDEBUG, MSVC's assert
expands to `_wassert(..., _CRT_WIDE(__FILE__), __LINE__)`, and `_CRT_WIDE`
puts the compiler's ABSOLUTE source path into the binary as wide characters.
`/PDBALTPATH:%_PDB%` had already removed the ASCII PDB path, and everyone
(including the #108 plan) treated that as the whole problem.

**A text scanner cannot see a wide string, and it cannot see a binary at all.**
That is the entire reason for this file. It reads bytes, and it reads them
twice: raw, and with NUL bytes removed - the second pass is what turns UTF-16
back into something a byte search can find.

CURE, already applied: `/d1trimfile:"<repo root>\\"` in both vcxproj files.
Verified: the rebuilt DLL contains ZERO occurrences, ASCII or wide.

    python _tests\Test-BinaryPii.py [bundle-dir]
    set SC4_PII_TOKENS=surname,handle    (optional extra literals)

Exit 0 = clean. Exit 1 = DO NOT UPLOAD.
"""
import os
import re
import sys

def safe(s):
    """Console-safe. A scanner reading raw BYTES will inevitably surface a
    character the Windows console codepage cannot encode - and a crash while
    PRINTING a hit reads exactly like a crash while finding one. The negative
    control tripped over this on its first run against a known-bad binary."""
    return s.encode("ascii", "backslashreplace").decode("ascii")


HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

# Any absolute per-user path is a leak regardless of whose name is in it.
PATH_RX = re.compile(rb"(?i)[A-Za-z]:\\Users\\[^\x00\s\"'<>|]{1,120}")

# ⚠ NOT "OneDrive" on its own. The installer legitimately EXPLAINS that
# Documents may be OneDrive-redirected, and flagging that word produced a false
# positive that would have trained the operator to skip real hits. Flag paths
# and identity literals; never flag a word that belongs in the product.
DEFAULT_TOKENS = []


def tokens():
    out = list(DEFAULT_TOKENS)
    out += [t.strip() for t in os.environ.get("SC4_PII_TOKENS", "").split(",")]
    local = os.path.join(PROJ, "tools", ".pii-tokens")
    if os.path.isfile(local):
        with open(local, encoding="utf-8") as fh:
            out += [ln.strip() for ln in fh]
    return [t for t in out if t]


def scan(blob, label, toks):
    found = []
    for m in PATH_RX.finditer(blob):
        found.append(("USERPATH/" + label, m.group(0).decode("latin-1")))
    for t in toks:
        i = blob.find(t.encode("latin-1", "ignore"))
        if i >= 0:
            lo = max(0, i - 40)
            found.append(("TOKEN/" + label,
                          blob[lo:i + len(t) + 40].decode("latin-1", "replace")))
    return found


def scan_zip(path, toks):
    """A zip is the thing actually uploaded, so scan THAT, not only its source.

    Two surfaces, and both have leaked in real projects: the compressed member
    contents, and the CENTRAL DIRECTORY, which stores every entry NAME in the
    clear. A build path that ended up in a FILENAME is invisible to a scan of
    the extracted files' bytes.
    """
    import zipfile
    n = 0
    bad = 0
    with zipfile.ZipFile(path) as z:
        names = "\n".join(z.namelist()).encode("utf-8")
        for kind, val in scan(names, "zip-entry-name", toks):
            print("!! ENTRY NAME  %-16s %s" % (kind, safe(val[:130])))
            bad += 1
        for info in z.infolist():
            if info.is_dir():
                continue
            n += 1
            blob = z.read(info)
            hits = scan(blob, "ascii", toks) + scan(blob.replace(b"\x00", b""),
                                                    "wide", toks)
            if hits:
                bad += 1
                print("\n!! %s" % info.filename)
                for kind, val in hits[:6]:
                    print("     %-16s %s" % (kind, safe(val[:130])))
    print("\nscanned %d member(s) inside %s" % (n, os.path.basename(path)))
    if n == 0:
        print("RESULT: REFUSING TO PASS - the archive is empty or unreadable.")
        return 1
    if bad:
        print("RESULT: %d LEAK(S) - DO NOT UPLOAD" % bad)
        return 1
    print("RESULT: CLEAN - members and entry names both.")
    return 0


def main():
    bundle = sys.argv[1] if len(sys.argv) > 1 else None
    if not bundle:
        dist = os.path.join(PROJ, "dist")
        # ⚠ DIRECTORIES ONLY. The first version of this picker took the last
        # matching NAME, which sorted "SC4UIScale-v2.93.1.zip" above the folder
        # of the same name. os.walk() on a file yields nothing, so it scanned
        # ZERO files and printed "CLEAN" - a confident pass from an instrument
        # that had looked at nothing. Caught within a minute of writing it,
        # which is the only reason it is a footnote and not a shipped leak.
        cands = sorted(d for d in os.listdir(dist)
                       if d.startswith("SC4UIScale-v")
                       and os.path.isdir(os.path.join(dist, d)))
        if not cands:
            print("no dist\\SC4UIScale-v* BUNDLE DIRECTORY found"); return 2
        bundle = os.path.join(dist, cands[-1])
    if os.path.isfile(bundle) and bundle.lower().endswith(".zip"):
        return scan_zip(bundle, tokens())
    if not os.path.isdir(bundle):
        print("not a bundle directory: %s" % bundle); return 2
    toks = tokens()
    if not toks:
        print("NOTE: no identity tokens configured (SC4_PII_TOKENS or "
              "tools\\.pii-tokens). The by-NAME rule is NOT running; the "
              "absolute-path rule - which caught the real defect - is.")

    nfiles = bad = 0
    for root, _d, files in os.walk(bundle):
        for fn in files:
            p = os.path.join(root, fn)
            nfiles += 1
            blob = open(p, "rb").read()
            hits = scan(blob, "ascii", toks) + scan(blob.replace(b"\x00", b""),
                                                    "wide", toks)
            if hits:
                bad += 1
                print("\n!! %s" % os.path.relpath(p, bundle))
                seen = set()
                for kind, val in hits:
                    if val in seen:
                        continue
                    seen.add(val)
                    print("     %-16s %s" % (kind, safe(val[:130])))

    print("\nscanned %d file(s) in %s" % (nfiles, os.path.basename(bundle)))
    # ⛔ ZERO FILES IS NOT A PASS. An instrument that looked at nothing must say
    # so, not report the absence of hits as evidence of absence.
    if nfiles == 0:
        print("RESULT: REFUSING TO PASS - scanned nothing. Wrong path?")
        return 1
    if bad:
        print("RESULT: %d FILE(S) CARRY PERSONAL DATA - DO NOT UPLOAD" % bad)
        return 1
    print("RESULT: CLEAN - no absolute user path or identity literal in any "
          "byte, ASCII or UTF-16.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
