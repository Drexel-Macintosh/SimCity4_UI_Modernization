#!/usr/bin/env python
"""Gate: zero hedging or work-in-progress language in the public tree.

WHY THIS EXISTS
---------------
User instruction: "Make sure there's nothing. Not a cross out, not a
'think', 'need to validate' nothing." A production repository states facts;
it does not think out loud, flag things for later, or leave a strikeout
standing next to its own correction. This gate is the literal enforcement
of that instruction, run against the STAGED PUBLIC TREE
(_packaging\public-repo), never the private working tree, which is allowed
to hedge because that is where the work actually happens.

PASS = exit 0, zero hits.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "public-repo"

# Each pattern is (name, compiled regex). Word-boundary aware where it
# matters, case-insensitive throughout - a hedge word capitalized at the
# start of a sentence is still a hedge word.
PATTERNS = [
    ("strikeout", re.compile(r"~~[^~\n]+~~")),
    ("first-person hedge",
     re.compile(r"\bI think\b|\bwe think\b|\bI believe\b|\bnot sure\b|"
                r"\bI'm not certain\b|\bmight be\b|\bmaybe\b|\bperhaps\b",
                re.I)),
    ("needs-validation",
     re.compile(r"need(?:s|ed)? to validate|needs? verif(?:y|ication)|"
                r"unverified|needs? confirmation|to be confirmed|"
                r"TBD|TBC\b", re.I)),
    ("todo marker",
     re.compile(r"\bTODO\b|\bFIXME\b|\bXXX\b|\bHACK\b(?!:.*hack the)", re.I)),
    ("wip marker",
     re.compile(r"\bwork.?in.?progress\b|\bWIP\b|\bin flight\b|"
                r"\bnot yet (?:done|finished|implemented|complete)\b|"
                r"\bstill (?:working on|need|needs|open|pending)\b|"
                r"\bcoming soon\b|\bplaceholder\b", re.I)),
    ("uncertainty qualifier",
     re.compile(r"\bunclear\b|\bunsure\b|\bunknown whether\b|"
                r"\bshould probably\b|\bprobably (?:need|needs|should)\b|"
                r"\bI guess\b|\bappears? to\b(?! be [a-z]+ table)", re.I)),
    ("session/diary marker",
     re.compile(r"\bUSER (?:ORDER|REQUEST|DIRECTIVE|DIRECTION)\b|"
                r"\bthe user (?:said|reported|confirmed|asked)\b|"
                r"\bsession\b.{0,20}\bended\b|originSessionId", re.I)),
    ("open-status marker",
     re.compile(r"\bOPEN\b(?=\s*[-|:])|\bSTATUS:\s*(?:OPEN|IN PROGRESS)\b|"
                r"\bSUPERSEDED\b|\bCORRECTED\b(?=\s*\d{4}-\d{2}-\d{2})",
                re.I)),
]

# A handful of legitimate technical uses that would otherwise false-positive.
ALLOW = [
    re.compile(r"appears? to be [a-z0-9 ]+ table", re.I),   # "appears to be a lookup table"
]


def scan_file(path):
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return hits
    lines = text.split("\n")
    for lineno, line in enumerate(lines, 1):
        for name, rx in PATTERNS:
            for m in rx.finditer(line):
                if any(a.search(line) for a in ALLOW):
                    continue
                hits.append((name, lineno, line.strip()[:100]))
    return hits


def main():
    if not ROOT.exists():
        print("SKIP: %s does not exist - run Build-PublicRepo.ps1 first" % ROOT)
        return 0

    exts = {".md", ".txt", ".cpp", ".h", ".py", ".ps1"}
    files = [p for p in ROOT.rglob("*")
             if p.is_file() and p.suffix.lower() in exts]

    print("Test-NoHedging")
    print("  scanning %d file(s) under %s" % (len(files), ROOT))
    print()

    total = 0
    for path in sorted(files):
        hits = scan_file(path)
        if hits:
            rel = path.relative_to(ROOT)
            for name, lineno, snippet in hits:
                total += 1
                print("  FAIL %s:%d [%s] %s" % (rel, lineno, name, snippet))

    print()
    if total:
        print("FAIL: %d hedging/WIP hit(s) - the public tree is not clean." % total)
        return 1
    print("ALL PASS (%d files, zero hedging/WIP/diary markers)" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
