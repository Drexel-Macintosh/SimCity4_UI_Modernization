#!/usr/bin/env python3
"""
Test-MutationCountInvariant - the O(n^2) crash-killer gate rests on ONE
invariant, and until now that invariant was enforced only by a human reading
the code once.

THE INVARIANT
    In UiSpike::ScalePanelRoot and UiSpike::ScaleSubtree, EVERY call that
    mutates a game window (SetW / SetH / SetArea / GZWinMoveTo / ChildAdd /
    ChildDelete) must be paired with an increment of the scale counter.

WHY IT MATTERS - this is not a style rule
    v2.69.0 (task #117) made the per-child liveness re-verification in five
    loops CONDITIONAL. Those loops re-enumerate the whole child list because OUR
    OWN WRITES can make the game destroy a later sibling; skipping the verify
    when nothing was mutated is what removes an O(n^2) cost from a 16 ms tick.

    The "was anything mutated?" signal is the scale COUNT. It was chosen over a
    new hand-maintained flag precisely because it is load-bearing elsewhere -
    it is the same number the per-panel "%d windows scaled" log lines print.

    If someone later adds a SetW/SetH/GZWinMoveTo WITHOUT incrementing the
    count, the loop will skip a liveness verify it needed, and the crash that
    comment calls a "CRASH KILLER" comes back - under rapid menu switching, on
    someone else's machine, with nothing in the log to explain it. That is a
    silent, delayed, hard-to-attribute failure: exactly the class this project
    keeps getting bitten by.

WHAT THIS CHECKS
    Every mutation call in those two functions has a count increment within
    MAX_DISTANCE lines. The increment may appear BEFORE or AFTER the mutation -
    in ScaleSubtree's third cluster it is 5 lines BEFORE the writes, and an
    earlier hand-audit that searched only forwards nearly concluded that path
    was uncounted.

NEGATIVE CONTROL
    A gate that cannot fail proves nothing (project law: null is not evidence).
    This one runs a MUTATION TEST on itself: it deletes a count increment from
    an in-memory copy of the source and asserts the check REJECTS that copy. If
    the negative control does not trip, the run fails even when the real source
    is clean.

Exit 0 = pass. Run from anywhere.
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "UiSpike.cpp")

FUNCTIONS = ("ScalePanelRoot", "ScaleSubtree")

# Calls that change a GAME WINDOW. Deliberately excludes our own bookkeeping
# (scaleMap writes, StoreScaleRecord) - those cannot destroy a sibling window.
MUTATION = re.compile(r"->\s*(SetW|SetH|SetArea|GZWinMoveTo|ChildAdd|ChildDelete)\s*\(")
INCREMENT = re.compile(r"(\(\s*\*\s*count\s*\)|\bcount\b)\s*\+\+")

# Max lines between a mutation and its counter increment. The real spread today
# is 9 (ScalePanelRoot's GZWinMoveTo at the top of its cluster). 12 leaves a
# little headroom while still catching a genuinely orphaned mutation.
MAX_DISTANCE = 12


def function_body(lines, name):
    """Return (start, end) 1-based inclusive line numbers for UiSpike::<name>."""
    pattern = re.compile(r"^\w[\w:<>\*&\s]*\bUiSpike::" + name + r"\s*\(")
    for i, line in enumerate(lines):
        if pattern.match(line):
            depth = 0
            started = False
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if not started and "{" in lines[j]:
                    started = True
                if started and depth <= 0:
                    return i + 1, j + 1
    return None, None


def check(lines, verbose=True):
    """Return a list of violation strings. Empty list = invariant holds."""
    violations = []
    for name in FUNCTIONS:
        start, end = function_body(lines, name)
        if start is None:
            violations.append(
                "FUNCTION NOT FOUND: UiSpike::%s - it was renamed or removed, so "
                "this gate is no longer checking what it claims." % name)
            continue

        increments = [k + 1 for k in range(start - 1, end) if INCREMENT.search(lines[k])]
        mutations = [k + 1 for k in range(start - 1, end) if MUTATION.search(lines[k])]

        if verbose:
            print("  UiSpike::%-16s lines %5d..%-5d  %d mutation(s), %d increment(s)"
                  % (name, start, end, len(mutations), len(increments)))

        if not mutations:
            violations.append(
                "NO MUTATIONS FOUND in UiSpike::%s - the matcher is broken or the "
                "function changed shape; a pass here would be meaningless." % name)
            continue

        for line_no in mutations:
            if not increments:
                violations.append(
                    "%s:%d has NO counter increment anywhere in UiSpike::%s"
                    % (os.path.basename(SRC), line_no, name))
                continue
            distance = min(abs(inc - line_no) for inc in increments)
            nearest = min(increments, key=lambda inc: abs(inc - line_no))
            if distance > MAX_DISTANCE:
                violations.append(
                    "%s:%d mutates a window (%s) but the nearest counter increment "
                    "is at line %d, %d lines away (max %d). If this mutation is "
                    "genuinely uncounted, the #117 verify gate will skip a liveness "
                    "check it needs and the rapid-menu-switch crash returns."
                    % (os.path.basename(SRC), line_no,
                       lines[line_no - 1].strip()[:48], nearest, distance, MAX_DISTANCE))
            elif verbose:
                print("      line %-6d -> increment at %-6d (distance %d)"
                      % (line_no, nearest, distance))
    return violations


def negative_control(lines):
    """Delete a counter increment and confirm the check REJECTS the result.

    Without this, a matcher that silently matched nothing would 'pass'.
    """
    start, end = function_body(lines, "ScaleSubtree")
    if start is None:
        return False, "could not locate ScaleSubtree to build the control"

    # Find an increment that is the ONLY one near some mutation, and remove it.
    mutations = [k + 1 for k in range(start - 1, end) if MUTATION.search(lines[k])]
    if not mutations:
        return False, "no mutations to build a control from"

    target = mutations[0]
    increments = [k + 1 for k in range(start - 1, end) if INCREMENT.search(lines[k])]
    near = [i for i in increments if abs(i - target) <= MAX_DISTANCE]
    if not near:
        return False, "no increment near the chosen mutation"

    broken = list(lines)
    for i in near:
        broken[i - 1] = "// [negative control] increment removed"

    residual = check(broken, verbose=False)
    tripped = any(str(target) in v for v in residual)
    return tripped, ("removed %d increment(s) near line %d -> %d violation(s)"
                     % (len(near), target, len(residual)))


def main():
    if not os.path.isfile(SRC):
        print("FAIL: %s not found" % SRC)
        return 1

    with open(SRC, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().split("\n")

    print("Test-MutationCountInvariant")
    print("  source: src/UiSpike.cpp (%d lines)" % len(lines))
    print("  rule  : every window mutation in ScalePanelRoot / ScaleSubtree must")
    print("          have a scale-counter increment within %d lines (either side)" % MAX_DISTANCE)
    print()

    violations = check(lines)

    print()
    ok, detail = negative_control(lines)
    print("  negative control: %s" % detail)
    if not ok:
        print()
        print("FAIL: the NEGATIVE CONTROL did not trip. Deleting a counter increment")
        print("      did not produce a violation, so this gate cannot detect the")
        print("      thing it exists to detect. Fix the gate before trusting a pass.")
        return 1
    print("  negative control: correctly REJECTED the damaged copy.")

    if violations:
        print()
        print("FAIL: %d violation(s) of the mutation/count invariant:" % len(violations))
        for v in violations:
            print("    - %s" % v)
        print()
        print("  Why this matters: src/UiSpike.cpp's five 'CRASH KILLER' liveness")
        print("  verifies are skipped when the scale count did not move (task #117).")
        print("  An uncounted mutation makes that gate skip a verify it needs.")
        print("  Either increment the counter, or - if the mutation genuinely must")
        print("  not count as a scaled window - re-open #117 and pick a different")
        print("  mutation signal. Do NOT just raise MAX_DISTANCE.")
        return 1

    print()
    print("ALL PASS (mutation/count invariant holds; negative control tripped as required)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
