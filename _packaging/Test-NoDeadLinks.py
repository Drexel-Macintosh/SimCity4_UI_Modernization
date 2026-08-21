#!/usr/bin/env python
"""Gate: every path a shipped document names actually ships.

WHY THIS EXISTS
---------------
The private tree is a densely cross-linked wiki. Publishing a curated subset
of it silently breaks every reference that pointed at a file left behind, and
the reader cannot tell a typo from a file they were never given. An
adversarial read of the corpus found this to be the single largest class of
defect - references to a regression diary, one-off probe scripts, and sibling
documents that the manifest does not carry.

A dead link is not cosmetic: it is the document claiming evidence the reader
cannot check.

Checks both markdown links and bare backticked paths, since the corpus uses
both. Only paths that look like repository files are considered - URLs,
anchors and game-side paths are ignored.

Usage:  Test-NoDeadLinks.py [staged-tree]      PASS = exit 0.
"""
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = (Path(sys.argv[1]) if len(sys.argv) > 1
        else Path(__file__).resolve().parent / "public-repo")

# [text](path) - markdown links
RX_MD = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
# `path\to\file.ext` or `path/to/file.ext` - backticked repo paths
RX_TICK = re.compile(r"`([A-Za-z_][\w./\\-]*\.(?:md|py|ps1|cpp|h|cs|txt|csv|sln|vcxproj))`")

# Paths that name things outside the repository on purpose.
EXTERNAL = re.compile(
    r"^(?:https?:|mailto:|#)|"
    r"SimCity 4\.exe|FontStyle\.ini|SC4GraphicsOptions\.ini|dgVoodoo|"
    r"SC4UIScale\.(?:ini|log)|Plugins\\|Documents\\", re.I)


def repo_files():
    out = set()
    for p in ROOT.rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT)
            out.add(str(rel).replace("\\", "/").lower())
            out.add(p.name.lower())
    return out


def candidates(text):
    for m in RX_MD.finditer(text):
        yield m.group(1)
    for m in RX_TICK.finditer(text):
        yield m.group(1)


def main():
    if not ROOT.exists():
        print("SKIP: %s does not exist - build the export first" % ROOT)
        return 0

    known = repo_files()
    docs = [p for p in ROOT.rglob("*.md")
            if "vendor" not in p.relative_to(ROOT).parts]

    print("Test-NoDeadLinks")
    print("  %d document(s), %d shipped path(s)" % (len(docs), len(known)))
    print()

    dead = 0
    for doc in sorted(docs):
        rel = doc.relative_to(ROOT)
        try:
            text = doc.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        seen = set()
        for raw in candidates(text):
            if raw in seen:
                continue
            seen.add(raw)
            if EXTERNAL.search(raw):
                continue
            # A link to a directory resolves on GitHub, as does a repo-
            # relative one like ../../releases. Neither is a dead file.
            if raw.endswith("/") or raw.endswith("\\") or "releases" in raw:
                continue
            norm = raw.replace("\\", "/").lstrip("./").lower()
            if norm in known or Path(norm).name in known:
                continue
            # Relative to the document's own folder.
            sibling = (rel.parent / raw.replace("\\", "/"))
            if str(sibling).replace("\\", "/").lower() in known:
                continue
            dead += 1
            print("  DEAD %s -> %s" % (rel, raw))

    print()
    if dead:
        print("FAIL: %d reference(s) point at files the export does not "
              "contain." % dead)
        return 1
    print("ALL PASS (every referenced repository path ships)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
