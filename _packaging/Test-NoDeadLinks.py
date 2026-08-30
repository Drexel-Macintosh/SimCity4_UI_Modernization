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

IN-REPO MODE (2026-08-30). The export path is no longer the only way this
tree reaches the public: the working tree now pushes straight to the public
remote, so a dead link in a tracked document is published the moment it is
committed. `--repo` runs the same check over the TRACKED SET of this
repository (git ls-files), which is exactly what a reader on GitHub sees -
an untracked file on disk resolves locally and 404s for them, so the tracked
set, not the working tree, is the right universe.

Usage:  Test-NoDeadLinks.py [staged-tree]      PASS = exit 0.
        Test-NoDeadLinks.py --repo             check this repo's tracked set.
"""
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_MODE = "--repo" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
if REPO_MODE:
    ROOT = Path(__file__).resolve().parent.parent
elif _args:
    ROOT = Path(_args[0])
else:
    ROOT = Path(__file__).resolve().parent / "public-repo"

# [text](path) - markdown links
RX_MD = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
# `path\to\file.ext` or `path/to/file.ext` - backticked repo paths
RX_TICK = re.compile(r"`([A-Za-z_][\w./\\-]*\.(?:md|py|ps1|cpp|h|cs|txt|csv|sln|vcxproj))`")

# Paths that name things outside the repository on purpose.
EXTERNAL = re.compile(
    r"^(?:https?:|mailto:|#)|"
    r"SimCity 4\.exe|FontStyle\.ini|SC4GraphicsOptions\.ini|dgVoodoo|"
    r"SC4UIScale\.(?:ini|log)|Plugins\\|Documents\\", re.I)

# --repo mode only. Three kinds of reference that are correct precisely
# BECAUSE the file is absent from the tracked set - flagging them would train
# a reader to ignore this gate, which is how the real hits survived three hand
# checks last time.
#   1. Things that exist only at RUN time or in a built bundle (deploy state,
#      release manifests, generated site tables, logs, capture output).
#   2. Contents of a git SUBMODULE. `vendor/gzcom-dll` is one tracked entry;
#      the SDK headers inside it are real files a clone gets, but git does not
#      list them, so a header citation is live, not dead.
#   3. Trees the .gitignore deliberately excludes and the prose names AS
#      excluded: derived _work/diff output, the volatile scratchpad, and the
#      game-derived extraction trees a cold clone regenerates.
GENERATED = re.compile(
    r"(?:^|[\\/])(?:z_SC4UIScale_STATE\.txt|SHA256SUMS\.txt)$|"
    r"(?:^|[\\/])(?:vendor|scratchpad|_work|diff|extracted[\w-]*)[\\/]|"
    r"^(?:vendor|scratchpad)[\\/]|"
    r"[\\/]generated[\w.-]*sites[\w.-]*\.txt$|^generated[\w.-]*\.txt$|"
    r"extracted-png-tgi\.csv$|item_icons\.csv$|"
    r"\.(?:log|dat|uipay|png|jpg)$", re.I)

# SDK headers cited by bare filename. They live inside the `vendor/gzcom-dll`
# SUBMODULE, so a clone has them and `git ls-files` does not - the same
# reason as GENERATED rule 2, but the citation style (bare `cIGZWin.h`)
# carries no path to match on.
#
# This is a LOOKUP, not a name pattern, deliberately: a prefix rule would
# also wave through `cIGZTypoed.h`, and a citation of a header the SDK does
# not have is exactly the dead reference this gate is for. If the submodule
# is not checked out the set is empty and every such citation is reported -
# a refusal, not a silent pass.
def _sdk_headers():
    inc = ROOT / "vendor" / "gzcom-dll" / "gzcom-dll" / "include"
    if not inc.is_dir():
        return set()
    return {p.name.lower() for p in inc.rglob("*.h")}

# Files that belong to the UPSTREAM sc4pac channel repo, named in our
# submission notes because the contributor runs them inside a clone of THAT
# repo. Ours to cite, never ours to ship.
UPSTREAM_SC4PAC = re.compile(r"^(?:src/)?lint\.py$|^docs/metadata\.md$")

# NOTE (2026-08-30): there is deliberately NO allowlist of "names a document
# mentions because they do not exist". One was written and then deleted the
# same hour, because the right fix turned out to be in the prose, not the
# gate: a document that says "Rebuild-Previews.ps1 was never written" should
# not format that name as a live path in the first place. Dropping the
# backticks says the same thing to the reader AND to this scan. Every such
# reference in the tree was repaired that way, so the exclusion had nothing
# left to exclude - and an exclusion nobody can check is how a gate stops
# meaning anything.

# A markdown link target that is not a path at all: table cells, prose
# fragments and captured values ("8", "arg", "p,53,25,80,53"). A repository
# path has a separator or an extension; these have neither.
def _looks_like_path(raw):
    return "/" in raw or "\\" in raw or re.search(r"\.\w{1,6}$", raw)


def _tracked():
    """Paths git actually tracks, relative to ROOT, forward-slashed.

    In --repo mode the universe is the tracked set: that is what a reader on
    GitHub can click. Falling back to the working tree here would let an
    untracked local file vouch for a link that 404s for everyone else.
    """
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                         capture_output=True, text=True, check=True)
    return [ln for ln in out.stdout.splitlines() if ln]


def repo_files():
    out = set()
    if REPO_MODE:
        for rel in _tracked():
            out.add(rel.lower())
            out.add(Path(rel).name.lower())
        return out
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
    sdk = _sdk_headers() if REPO_MODE else set()
    if REPO_MODE:
        print("  vendor SDK headers visible: %d%s" % (
            len(sdk), "" if sdk else "  (submodule not checked out - every "
                                     "header citation will be reported)"))
        # Same exclusions as the export mode, plus the two trees the repo's
        # own tools refuse to quote as current knowledge: vendored source and
        # the raw agent drafts (their README says nothing there is
        # authoritative, so their links are leads, not claims).
        docs = [ROOT / p for p in _tracked()
                if p.endswith(".md")
                and "vendor" not in Path(p).parts
                and "submenus-dll-src" not in Path(p).parts
                and "_incoming" not in Path(p).parts]
    else:
        docs = [p for p in ROOT.rglob("*.md")
                if "vendor" not in p.relative_to(ROOT).parts]

    print("Test-NoDeadLinks%s" % (" (--repo: tracked set)" if REPO_MODE else ""))
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
            if REPO_MODE and (not _looks_like_path(raw)
                              or GENERATED.search(raw)
                              or Path(raw).name.lower() in sdk
                              or UPSTREAM_SC4PAC.match(raw)):
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
