"""privacy_audit.py - what would leak if this repo went public.

Written before the GitHub move. The user's stated gate is PRIVACY, so this
exists to answer one question with numbers rather than confidence:
    "what personally identifying or machine specific content is in here?"

It does NOT change anything. It reports. Remediation is a separate, reviewed
step - a script that rewrites source in bulk is exactly how a subtle breakage
ships (and #98 is the standing reminder that a change made on static reasoning
alone can break a working UI).

CATEGORIES, roughly in order of how badly they leak:
  IDENTITY   a real name, account name, e-mail address
  USERPATH   C:\\Users\\<name>\\... - leaks the account name in every hit
  CLOUDPATH  OneDrive / Dropbox / personal cloud roots
  MACHINE    hostnames, serial numbers, licence keys, product IDs
  ABSPATH    any other absolute local path (portability, mild leak)
  BINARY     images and other non-text that cannot be reviewed by grep

Usage:  python tools/privacy_audit.py [--full]
        --full lists every hit instead of the top files per category.
"""
import os
import re
import sys
import collections

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FULL = "--full" in sys.argv

# Directories that are vendored, generated, or otherwise not ours to clean.
SKIP_DIRS = {
    ".git", "vendor", "build", "__pycache__", "node_modules",
    "extracted", "out",  # generated art dumps + captures
}
TEXT_EXT = {
    ".py", ".ps1", ".cpp", ".h", ".hpp", ".c", ".md", ".txt", ".json", ".ini",
    ".xml", ".vcxproj", ".sln", ".bat", ".cmd", ".yml", ".yaml", ".cfg", ".js",
}
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga", ".dds", ".dat", ".dll",
    ".exe", ".lib", ".exp", ".pdb", ".obj", ".log", ".zip", ".msi",
}

def _identity_pattern():
    r"""A regex for the operator's own name tokens, supplied LOCALLY.

    ⚠ THIS FILE USED TO HARD-CODE THE NAME IT WAS HUNTING FOR. A privacy
    auditor that embeds the identity string publishes it: the tool became the
    leak it exists to find, and it would have shipped in the first public
    commit. Supply the tokens out-of-band instead:

        set SC4_PII_TOKENS=surname,handle          (comma separated)
        - or - one token per line in tools/.pii-tokens   (gitignored)

    With no tokens configured the IDENTITY-by-name rule is simply absent, and
    the run SAYS SO rather than quietly passing - a scan that cannot see the
    thing is not evidence that the thing is gone.
    """
    toks = [t.strip() for t in os.environ.get("SC4_PII_TOKENS", "").split(",")]
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pii-tokens")
    if os.path.isfile(local):
        with open(local, encoding="utf-8") as fh:
            toks += [ln.strip() for ln in fh]
    toks = [re.escape(t) for t in toks if t]
    if not toks:
        print("NOTE: no identity tokens configured (SC4_PII_TOKENS or "
              "tools/.pii-tokens) - the by-NAME rule is NOT running. "
              "Path and email rules still are.")
        return r"(?!x)x"                     # matches nothing, and says so
    return r"\b(?:%s)\w*\b" % "|".join(toks)


PATTERNS = [
    ("IDENTITY",  re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("IDENTITY",  re.compile(_identity_pattern(), re.I)),
    ("USERPATH",  re.compile(r"[A-Za-z]:\\+Users\\+[^\\\s\"'<>|]+", re.I)),
    ("CLOUDPATH", re.compile(r"\bOneDrive\b|\bDropbox\b|\bGoogle Drive\b", re.I)),
    ("MACHINE",   re.compile(r"\b[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}(?:-[A-Z0-9]{5})?\b")),
    ("ABSPATH",   re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:\\+(?!Users)[^\\\s\"'<>|]+\\+")),
]


def walk():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def main():
    hits = collections.defaultdict(list)          # cat -> [(relpath, line, text)]
    per_file = collections.Counter()              # relpath -> hits
    binaries = []
    scanned = 0
    for path in walk():
        rel = os.path.relpath(path, ROOT)
        ext = os.path.splitext(path)[1].lower()
        if ext in BINARY_EXT:
            binaries.append((rel, os.path.getsize(path)))
            continue
        if ext not in TEXT_EXT:
            continue
        scanned += 1
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for n, line in enumerate(f, 1):
                    if len(line) > 4000:
                        line = line[:4000]
                    for cat, rx in PATTERNS:
                        m = rx.search(line)
                        if m:
                            hits[cat].append((rel, n, m.group(0)[:90]))
                            per_file[rel] += 1
        except Exception as e:
            print("  ! unreadable %s (%s)" % (rel, e))

    print("PRIVACY AUDIT - %s" % ROOT)
    print("scanned %d text files\n" % scanned)

    total = 0
    for cat in ("IDENTITY", "USERPATH", "CLOUDPATH", "MACHINE", "ABSPATH"):
        rows = hits.get(cat, [])
        total += len(rows)
        print("%-10s %5d hits in %d files" % (cat, len(rows), len({r[0] for r in rows})))
        if not rows:
            continue
        if FULL:
            for rel, n, txt in rows:
                print("    %s:%d  %s" % (rel, n, txt))
        else:
            byfile = collections.Counter(r[0] for r in rows)
            for rel, c in byfile.most_common(8):
                sample = next(r[2] for r in rows if r[0] == rel)
                print("    %-58s %4d   e.g. %s" % (rel, c, sample))
            if len(byfile) > 8:
                print("    ... and %d more files" % (len(byfile) - 8))
        print()

    print("BINARY/UNREVIEWABLE: %d files (%.1f MB) - grep cannot vet these."
          % (len(binaries), sum(b[1] for b in binaries) / 1048576.0))
    bybucket = collections.Counter(os.path.splitext(b[0])[1].lower() for b in binaries)
    for ext, c in bybucket.most_common(12):
        mb = sum(b[1] for b in binaries if b[0].lower().endswith(ext)) / 1048576.0
        print("    %-8s %5d files  %8.1f MB" % (ext, c, mb))

    print("\nTOTAL text hits: %d" % total)
    print("\nHOW TO READ THIS")
    print("  USERPATH is the big one: every hit spells out the account name.")
    print("  Most will be in comments, docs and helper scripts, which are safe to")
    print("  rewrite - but the .ps1/.py tools NEED working paths to run, so those")
    print("  want a parameter or an env var, not a blind find-and-replace.")
    print("  BINARY files cannot be reviewed by text search at all; the images were")
    print("  audited by eye separately, and 2 leaking captures were deleted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
