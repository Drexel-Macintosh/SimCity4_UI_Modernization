#!/usr/bin/env python3
"""Root-ladder at ALL depths (register #14 / coverage-matrix.md 0.6).

coverage_rederive.py's enumerate_roots() only records depth-0 <LEGACY>
elements as "roots" (that IS the census denominator, by construction).
0x00004200 (Data Views Map-View page, I-2bc9060f) is a MEASURED
counterexample: the code passes it as a loader winId at 0x007EEAE6 even
though it is a depth-1 child (coverage-matrix.md 0.6, SDK-GAPS.md,
FINAL-3-PERCENT.md 4.0(b)). The open question: how many OTHER depth>=1
nodes exist in the corpus that a loader call could equally address as a
top-level handle? That count was flagged "unmeasured" - this is that
measurement.

Reuses coverage_rederive.py's own tag regexes and quote-blanking so the
depth accounting matches the shipped census exactly (same corpus, same
tag grammar, same latin-1 decode). Does NOT reuse enumerate_roots() itself
because that function only *keeps* depth-0 records; this walks the same
state machine but keeps every <LEGACY> line regardless of depth.

This is an OFFLINE, CORPUS-SIDE instrument: it tells you every id that
EXISTS at each depth, i.e. every node a code call site COULD reference
as a non-root winId. It does not (and cannot, without a disassembler
enumerating loader call sites / winId push arguments across .text) tell
you how many such nodes the CODE actually addresses - only 7 script-
winId pairs are documented as measured from disassembly, of which 1
(0x00004200) is depth-1. That numerator stays open; see the printed
NOTE at the end of this script's output.
"""
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPTS_GAME = os.path.join(REPO, "tools", "uiscripts", "extracted")
SCRIPTS_PLUGINS = os.path.join(REPO, "tools", "uiscripts", "extracted-plugins")

BOMS = ("\xff\xfe\x00\x00", "\x00\x00\xfe\xff",
        "\xef\xbb\xbf",
        "\xff\xfe", "\xfe\xff",
        "﻿")

RE_ID = re.compile(r"\bid=0x([0-9a-fA-F]{1,8})")
RE_AREA = re.compile(r"\barea=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")
RE_LEGACY_LINE = re.compile(r"^\s*<LEGACY\b")
RE_CHILDREN_OPEN = re.compile(r"^\s*<CHILDREN\s*>")
RE_CHILDREN_END = re.compile(r"^\s*</CHILDREN\s*>")

# The 7 script->winId pairs documented in FINAL-3-PERCENT.md 4.0(b) / SDK-GAPS.md
# as MEASURED from disassembly (call-site address in comment). This is the
# entire known universe of code-driven loader targets in the repo's notes -
# it is NOT a claim that these are the only ones that exist in the compiled
# code, only the only ones anyone has pulled out of .text so far.
KNOWN_CODE_WINID_PAIRS = [
    ("0a2dd355", "4a35b0f2", "0x00443EA5 (tutorial page)"),
    ("0a41be3e", "0a41c7b2", "0x00444057 (tutorial pointer 1)"),
    ("0a41be3f", "0a41c7b3", "0x00444083 (tutorial pointer 2)"),
    ("4bc906b5", "6a64e3c0", "documented positive control"),
    ("6a9455c9", "27df05be", "0x00438465/0x00438935/0x0043A812"),
    ("6bc9065a", "0a4a8176", "documented positive control (3rd depth-0 root)"),
    ("2bc9060f", "00004200", "0x007EEAE6 (Data Views Map-View page)"),
]


def strip_bom(text):
    t = text
    while True:
        for b in BOMS:
            if t.startswith(b):
                t = t[len(b):]
                break
        else:
            return t


def _blank_quoted(text):
    out = []
    inq = False
    for ch in text:
        if ch == '"':
            inq = not inq
            out.append(' ')
        elif ch == '\n':
            out.append(ch)
        else:
            out.append(' ' if inq else ch)
    return ''.join(out)


def script_files(d):
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith(".ui")]


def enumerate_all_depths(text):
    """Every <LEGACY> element in the file, at ITS OWN depth (0 = top-level).
    Same state machine as coverage_rederive.enumerate_roots(), except every
    node is kept, not just depth-0 ones. Returns (nodes, final_depth, min_depth)
    where nodes = [(depth, id_or_None, area_or_None), ...] in document order."""
    scan_lines = _blank_quoted(text).splitlines()
    raw_lines = text.splitlines()
    nodes = []
    depth = 0
    min_depth = 0
    for i, sline in enumerate(scan_lines):
        rline = raw_lines[i] if i < len(raw_lines) else ""
        if RE_LEGACY_LINE.search(sline):
            m = RE_ID.search(rline)
            a = RE_AREA.search(rline)
            nodes.append((depth,
                          int(m.group(1), 16) if m else None,
                          tuple(int(x) for x in a.groups()) if a else None))
        if RE_CHILDREN_END.search(sline):
            depth -= 1
        elif RE_CHILDREN_OPEN.search(sline):
            depth += 1
        min_depth = min(min_depth, depth)
    return nodes, depth, min_depth


def main():
    files = [(p, "game") for p in script_files(SCRIPTS_GAME)] + \
            [(p, "plugin") for p in script_files(SCRIPTS_PLUGINS)]

    by_depth_id_count = Counter()          # depth -> count of id-bearing nodes
    by_depth_total_count = Counter()       # depth -> count of ALL nodes (incl. id-less)
    depth1plus_ids = defaultdict(list)     # id -> [(script_stem, depth, area), ...]
    unbalanced = []
    stem_of_00004200 = []

    total_files = 0
    for path, kind in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        # corpus filenames are T-..._G-..._I-<instance>.ui
        m = re.search(r"_I-([0-9a-fA-F]{8})\.ui$", os.path.basename(path), re.I)
        inst = m.group(1) if m else stem
        try:
            with open(path, "r", encoding="latin-1") as f:
                text = strip_bom(f.read())
        except OSError as e:
            print("UNREADABLE:", path, e)
            continue
        total_files += 1
        nodes, final_depth, min_depth = enumerate_all_depths(text)
        if final_depth != 0 or min_depth < 0:
            unbalanced.append((stem, final_depth, min_depth))
        for depth, id_, area in nodes:
            by_depth_total_count[depth] += 1
            if id_ is not None:
                by_depth_id_count[depth] += 1
                if depth >= 1:
                    depth1plus_ids[id_].append((inst, depth, area))
                if id_ == 0x00004200:
                    stem_of_00004200.append((inst, depth, area))

    print("== ROOT LADDER AT ALL DEPTHS ==")
    print("files scanned: %d (game=%d, plugin=%d)" %
          (total_files, len(script_files(SCRIPTS_GAME)), len(script_files(SCRIPTS_PLUGINS))))
    if unbalanced:
        print("UNBALANCED FILES (final_depth!=0 or min_depth<0) -- integrity check FAILED for:")
        for stem, fd, md in unbalanced:
            print("   %s final_depth=%d min_depth=%d" % (stem, fd, md))
    else:
        print("depth accounting balanced on every file (final_depth==0, min_depth==0 for all).")

    print()
    print("nodes with a nonzero id=, by depth:")
    max_depth = max(by_depth_id_count.keys()) if by_depth_id_count else 0
    for d in range(0, max_depth + 1):
        print("  depth %d: %6d id-bearing nodes  (%6d nodes total, incl. id-less)"
              % (d, by_depth_id_count.get(d, 0), by_depth_total_count.get(d, 0)))

    depth0_id_nodes = by_depth_id_count.get(0, 0)
    depth1plus_id_nodes = sum(v for d, v in by_depth_id_count.items() if d >= 1)
    distinct_depth1plus_ids = len(depth1plus_ids)

    print()
    print("== HEADLINE ==")
    print("depth-0 id-bearing nodes (the existing census denominator): %d" % depth0_id_nodes)
    print("depth>=1 id-bearing nodes (occurrences, corpus-wide):       %d" % depth1plus_id_nodes)
    print("distinct depth>=1 ids (corpus-wide):                       %d" % distinct_depth1plus_ids)

    print()
    print("0x00004200 occurrences (positive control -- must show depth>=1 at least once):")
    for inst, depth, area in stem_of_00004200:
        print("   I-%s depth=%d area=%s" % (inst, depth, area))

    print()
    print("== WHAT THIS DOES AND DOES NOT ANSWER ==")
    print("This is the corpus-side count: %d distinct ids exist at depth>=1 anywhere"
          % distinct_depth1plus_ids)
    print("in the 339-file corpus, i.e. %d CANDIDATE nodes a loader call could address"
          % distinct_depth1plus_ids)
    print("directly as a non-root winId, the way 0x00004200 is documented to be.")
    print()
    print("It does NOT tell you how many the CODE actually does this to. That requires")
    print("enumerating every loader call site in .text (the sub_5F9480-style thunk family)")
    print("and reading its pushed winId argument -- a live/interactive disassembler task,")
    print("not something derivable from the .UI corpus alone. The repo's entire measured")
    print("universe of such call sites is %d pairs (FINAL-3-PERCENT.md 4.0(b)):"
          % len(KNOWN_CODE_WINID_PAIRS))
    depth_by_pair = {}
    # cross-reference the known pairs against this run's per-script node list
    # (re-scan just those files to get exact depth, not just "in depth1plus_ids")
    script_to_path = {}
    for path, kind in files:
        m = re.search(r"_I-([0-9a-fA-F]{8})\.ui$", os.path.basename(path), re.I)
        if m:
            script_to_path[m.group(1).lower()] = path
    for script_inst, win_id, site in KNOWN_CODE_WINID_PAIRS:
        p = script_to_path.get(script_inst.lower())
        depth = "FILE NOT FOUND"
        if p:
            with open(p, "r", encoding="latin-1") as f:
                text = strip_bom(f.read())
            nodes, _, _ = enumerate_all_depths(text)
            want = int(win_id, 16)
            hits = [d for d, i, a in nodes if i == want]
            depth = hits[0] if hits else "ID NOT FOUND IN SCRIPT"
        print("   I-%s -> id=0x%s  depth=%s   (%s)" % (script_inst, win_id, depth, site))
    depth1_known = sum(1 for s, w, _ in KNOWN_CODE_WINID_PAIRS
                        if script_to_path.get(s.lower()) and
                        int(w, 16) in [i for d, i, a in enumerate_all_depths(
                            strip_bom(open(script_to_path[s.lower()], "r", encoding="latin-1").read()))[0]
                            if d >= 1])
    print()
    print("Of those %d KNOWN code call sites, %d are depth-1+ (0x00004200)."
          % (len(KNOWN_CODE_WINID_PAIRS), depth1_known))
    print("This 7-pair set is a sample the notes happened to check, not an exhaustive")
    print("disassembly sweep -- so 1/7 is not a rate that generalises to the full binary.")


if __name__ == "__main__":
    sys.exit(main())
