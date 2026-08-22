#!/usr/bin/env python
"""Gate: no hedging, work-in-progress or private-session language ships.

WHY THIS EXISTS
---------------
A production repository states facts. It does not think out loud, flag work
for later, leave a strikeout standing beside its own correction, or address
a reader who was in the room. This gate enforces that on the STAGED EXPORT,
never on the private working tree, which is allowed to hedge because that is
where the work happens.

WHY THE PATTERNS ARE NARROW
---------------------------
The first version banned the words outright and produced 651 hits, almost
all of them ordinary technical English: a file "held open" by the game,
"placeholder art" as a real DBPF concept, a dial that "appears to wrap" on
screen. A gate that cries wolf on correct prose gets ignored, which is worse
than no gate at all. Each pattern below therefore matches the SENTENCE SHAPE
that carries a hedge, not a word that can appear inside one.

Third-party code under vendor is excluded: it ships verbatim for licence
compliance and is not ours to rewrite.

Usage:  Test-NoHedging.py [staged-tree]      PASS = exit 0.
"""
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = (Path(sys.argv[1]) if len(sys.argv) > 1
        else Path(__file__).resolve().parent / "public-repo")

PATTERNS = [
    # A crossed-out claim beside its replacement.
    ("strikeout", re.compile(r"~~[^~\n]+~~")),

    # Epistemic hedging ABOUT A FACT - not description of what a screen shows.
    ("hedge",
     re.compile(r"\bI think\b|\bwe think\b|\bI believe\b|\bI guess\b|"
                r"\bnot (?:yet )?sure\b|\bunsure\b|\bit is unclear\b|"
                r"\b(?:probably|might|maybe|perhaps) (?:need|needs|should|"
                r"want|be worth)\b", re.I)),

    # Work deferred rather than done.
    ("deferred work",
     re.compile(r"\bTODO\b|\bFIXME\b|"
                r"needs? (?:to be )?(?:validat|verif|confirm)|"
                r"\bunverified\b|\bto be (?:confirmed|determined|decided)\b|"
                r"\bTBD\b|\bcoming soon\b|\bnot yet (?:done|finished|"
                r"implemented|complete|written|shipped)\b|"
                r"\bstill (?:to do|todo|outstanding|pending|open)\b|"
                r"\bwork.in.progress\b|\bnext (?:target|step)s?\s*:", re.I)),

    # An open-defect list or status board.
    ("open status",
     re.compile(r"\bSTATUS\s*:\s*(?:OPEN|IN.PROGRESS|WIP|PENDING)\b|"
                # "first-open defect" is a defect ON first open, not an open
                # one - the hyphenated forms are ordinary technical English.
                r"(?<!-)\bopen (?:defect|issue|item|bug|question)s?\b|"
                r"\bremains? open\b|\bnot closed\b", re.I)),

    # A retraction left standing instead of the corrected fact alone.
    ("revision layering",
     re.compile(r"\bSUPERSEDED\b|\bSUPERSEDES\b|"
                r"\bCORRECTED\s+\d{4}-\d{2}-\d{2}|"
                r"\b(?:this|the (?:above|earlier|previous|old))\s+"
                r"(?:claim|note|line|entry|statement)\s+(?:was|is)\s+wrong\b|"
                r"\ban earlier (?:revision|version|build) (?:of this|had|did)",
                re.I)),

    # The private session showing through.
    ("session residue",
     re.compile(r"\bUSER (?:ORDER|REQUEST|DIRECTIVE|DIRECTION)\b|"
                r"\bthe user (?:said|reported|confirmed|asked|wants|raised)\b|"
                r"\boriginSessionId\b|\bnode_type:\s*memory\b|"
                r"\[\[[a-z0-9-]+\]\]", re.I)),

    # The private priority code: star / no-entry / warning glyphs. Table
    # notation (check, cross, arrow) is ordinary technical writing and stays.
    ("attention glyph", re.compile("[⛔⚠⭐✅❌❗"
                                   "‼\U0001f6d1]")),
]


def scan_file(path):
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return hits
    for lineno, line in enumerate(text.split("\n"), 1):
        for name, rx in PATTERNS:
            if rx.search(line):
                hits.append((name, lineno, line.strip()[:110]))
    return hits


def main():
    if not ROOT.exists():
        print("SKIP: %s does not exist - build the export first" % ROOT)
        return 0

    exts = {".md", ".txt", ".cpp", ".h", ".py", ".ps1", ".cs"}
    files = [p for p in ROOT.rglob("*")
             if p.is_file() and p.suffix.lower() in exts
             and "vendor" not in p.relative_to(ROOT).parts]

    print("Test-NoHedging")
    print("  scanning %d file(s) under %s (vendor excluded)" % (len(files), ROOT))
    print()

    total = 0
    for path in sorted(files):
        for name, lineno, snippet in scan_file(path):
            total += 1
            print("  FAIL %s:%d [%s] %s"
                  % (path.relative_to(ROOT), lineno, name, snippet))

    print()
    if total:
        print("FAIL: %d hit(s) - the export is not production-clean." % total)
        return 1
    print("ALL PASS (%d files, no hedging/WIP/session residue)" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
