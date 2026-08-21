#!/usr/bin/env python
"""Gate: THE STOCK TIER'S CONTRACT, asserted on the source.

WHY THIS EXISTS
---------------
Two defects shipped on 2026-08-19, one build apart, and they are the same
mistake wearing different clothes: a piece of boot work was attached to a
neighbouring call whose gate did not match the condition the work depends on.

  1. z_SC4UIScale_SelectorUI-1x - the stock-tier scale selector - was armed
     from inside ScaleTier::SyncStaticLayers. That function is NOT called at
     the stock tier, so the package could never be armed in the one state it
     exists for. Measured: the dat sat as .x1-disabled on a 1x machine while
     the DLL logged that the selector "IS serviced", and Graphic Options had
     no selector in it.

  2. The static-layer sync was gated on `spikeAutoScale || tierActive`, both
     of which are FALSE for a manual stock factor - so choosing 1x in the
     in-game selector left the PREVIOUS tier's art dats armed while geometry
     ran at 1x. The user's whole UI was wrong on screen.

The project already records this shape twice (#149, #182) in comments beside
the very call site that grew both of these. A comment did not stop the third
and fourth instances; this gate is the version that can.

THIS IS A SOURCE-SHAPE GATE, and it is honest about that: it proves the
CALLS ARE WIRED the way the contract requires. It cannot prove the runtime
behaviour - only a boot can - so every assertion here is about structure that
is necessary, never about a result that is sufficient. _tests/Test-BootMatrix
covers the runtime side (and kills the game, so it is not run casually).

PASS = exit 0.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DIRECTOR = os.path.join(REPO, "src", "SC4UIScaleDllDirector.cpp")
SCALETIER = os.path.join(REPO, "src", "ScaleTier.cpp")


def strip_comments(src):
    """Remove // and /* */ comments.

    NECESSARY, NOT COSMETIC. Every invariant below is about what the CODE
    does, and this file's comments quote the very call shapes being searched
    for - including the wrong ones they warn against. Matching prose would let
    a warning about a bug read as the bug, or worse, let the fix's own
    explanation satisfy the gate that checks the fix.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def indent_of(line):
    return len(line) - len(line.lstrip())


def main():
    failures = []
    notes = []

    for p in (DIRECTOR, SCALETIER):
        if not os.path.isfile(p):
            print("FAIL: %s not found" % p)
            return 1

    director = strip_comments(open(DIRECTOR, encoding="utf-8", errors="replace").read())
    scaletier = strip_comments(open(SCALETIER, encoding="utf-8", errors="replace").read())

    print("Test-StockTierContract")
    print("  src/SC4UIScaleDllDirector.cpp, src/ScaleTier.cpp (comments stripped)")
    print()

    # ---- 1: the selector package is armed OUTSIDE SyncStaticLayers --------
    # The two functions must not be nested: SyncStaticLayers does not run at
    # the stock tier, and the selector package is FOR the stock tier.
    m = re.search(r"void\s+SyncStaticLayers\s*\([^)]*\)\s*\{", scaletier)
    if not m:
        failures.append("could not locate SyncStaticLayers in ScaleTier.cpp - "
                        "the parser has rotted, not the code.")
    else:
        # walk braces to find the function body
        i = scaletier.index("{", m.start())
        depth, j = 0, i
        while j < len(scaletier):
            if scaletier[j] == "{":
                depth += 1
            elif scaletier[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = scaletier[i:j]
        if "SelectorUI" in body or "SyncSelectorPackage" in body:
            failures.append(
                "the stock-tier selector package is armed from INSIDE "
                "SyncStaticLayers. That function is not called at the stock "
                "tier, so the package can never be armed in the only state it "
                "exists for - this is the exact defect of 2026-08-19.")
            print("  [selector arming outside SyncStaticLayers] *** NESTED ***")
        else:
            print("  [selector arming outside SyncStaticLayers] ok")

    # ---- 2: the director calls it, and calls it UNCONDITIONALLY -----------
    calls = [ln for ln in director.split("\n") if "SyncSelectorPackage(" in ln]
    if not calls:
        failures.append(
            "SC4UIScaleDllDirector.cpp never calls ScaleTier::SyncSelectorPackage - "
            "the stock-tier selector package would never be armed or stashed at all.")
        print("  [director calls SyncSelectorPackage] *** MISSING ***")
    else:
        # UNCONDITIONAL = at the same indent as the surrounding statements,
        # not nested inside an `if` that asks how the factor was chosen. We
        # test the practical version of that: the enclosing block must not be
        # an `if` whose condition mentions the gates that are false at stock.
        lines = director.split("\n")
        idx = next(i for i, ln in enumerate(lines) if "SyncSelectorPackage(" in ln)
        base = indent_of(lines[idx])
        guarded_by = None
        for k in range(idx - 1, max(0, idx - 60), -1):
            ln = lines[k]
            stripped = ln.strip()
            if not stripped:
                continue
            # SKIP BARE BRACES. The first non-blank line above a call inside
            # an `if` block is the block's own `{`, which sits at the LOWER
            # indent - so treating it as "left the block" ended the walk one
            # line before the `if` it was looking for. The gate then passed on
            # the very defect it was written for, and only the negative
            # control said so (2026-08-19). A guard walk that stops at a brace
            # can never see the condition that brace belongs to.
            if stripped in ("{", "}"):
                continue
            if indent_of(ln) < base and stripped.startswith("if"):
                guarded_by = stripped
                break
            if indent_of(ln) < base:
                break
        if guarded_by:
            bad = [t for t in ("tierActive", "spikeAutoScale", "spikeScaleAll")
                   if t in guarded_by]
            if bad:
                failures.append(
                    "SyncSelectorPackage is guarded by `%s`, which mentions %s. "
                    "Those are FALSE at the stock tier - the only state this "
                    "package is for - so the guard makes it unreachable exactly "
                    "when it is needed."
                    % (guarded_by, ", ".join(bad)))
                print("  [call is unconditional] *** GUARDED BY %s ***" % guarded_by)
            else:
                notes.append("SyncSelectorPackage sits under `%s`; no stock-tier "
                             "gate named, allowed." % guarded_by)
                print("  [call is unconditional] ok (enclosing if is unrelated)")
        else:
            print("  [call is unconditional] ok")

        # and it must be gated on the tier being STOCK, nothing else
        if not any(re.search(r"SyncSelectorPackage\(\s*!\s*tierActive\s*\)", c)
                   for c in calls):
            failures.append(
                "SyncSelectorPackage is not called as SyncSelectorPackage(!tierActive). "
                "The condition this package depends on is 'is the tier stock' - "
                "anything else is gating it on a neighbour's question.")
            print("  [armed on !tierActive] *** WRONG ARGUMENT ***")
        else:
            print("  [armed on !tierActive] ok")

    # ---- 3: a stock factor must still UNLOAD the art ----------------------
    # SyncStaticLayers(1.0) is disable-all by its own contract, so the gate in
    # front of it has to be reachable when the user deliberately picks 1x.
    # `spikeAutoScale || tierActive` is not: both are false in that case.
    m2 = re.search(r"if\s*\(([^)]*)\)\s*\n?\s*\{[^{}]*SyncStaticLayers\s*\(",
                   director, flags=re.S)
    if not m2:
        m2 = re.search(r"if\s*\(([^)]*)\)[^;]{0,600}?SyncStaticLayers\s*\(",
                       director, flags=re.S)
    if not m2:
        failures.append("could not locate the guard in front of SyncStaticLayers.")
        print("  [stock factor unloads art] *** GUARD NOT FOUND ***")
    else:
        cond = " ".join(m2.group(1).split())
        # It needs a term that is TRUE when the request is for the mod to be
        # active but the resolved factor is stock. The captured pre-force copy
        # of the ini's ScaleAll is that term.
        if "iniWantsScaling" not in cond:
            failures.append(
                "the SyncStaticLayers guard is `%s`, which has no term that is "
                "true for a MANUAL STOCK factor. spikeAutoScale and tierActive "
                "are both false there, so choosing 1x skips the sync and the "
                "PREVIOUS tier's art dats stay armed while geometry runs at 1x. "
                "That is the user-reported 'everything broken at 1x'." % cond)
            print("  [stock factor unloads art] *** GUARD IS %s ***" % cond)
        else:
            print("  [stock factor unloads art] ok (guard: %s)" % cond)

    # ---- 4: the pre-force capture must precede everything that forces it --
    # iniWantsScaling only answers "did the user ask for this mod to be
    # active" if it is taken BEFORE the two blocks that set spikeScaleAll to
    # false. Taken after, it is a copy of the wrong answer.
    cap = director.find("iniWantsScaling =")
    if cap == -1:
        if "iniWantsScaling" in director:
            failures.append("iniWantsScaling is used but never assigned.")
    else:
        forced = [m.start() for m in
                  re.finditer(r"settings\.spikeScaleAll\s*=\s*false", director)]
        early = [f for f in forced if f < cap]
        if early:
            failures.append(
                "iniWantsScaling is captured at offset %d but spikeScaleAll is "
                "forced false earlier (offset %d). The capture then records "
                "'is scaling happening', not 'did the user ask for it' - the "
                "wrong question, which is the whole bug it exists to fix."
                % (cap, early[0]))
            print("  [capture precedes the forcing] *** TOO LATE ***")
        else:
            print("  [capture precedes the forcing] ok")

    print()
    for n in notes:
        print("  note: %s" % n)
    if failures:
        print()
        print("FAIL: %d problem(s):" % len(failures))
        for f in failures:
            print("  - %s" % f)
        return 1
    print()
    print("ALL PASS (stock-tier contract: selector armed on !tierActive outside "
          "SyncStaticLayers; a stock factor still unloads the art)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
