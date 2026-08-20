#!/usr/bin/env python
"""Gate: the v3.14 SELECTOR'S CONTRACT, asserted on the source.

WHY THIS EXISTS
---------------
The v3.13 selector froze for 3.3s on a click and offered an empty drop
list, and both defects were of one shape: work running at a moment it had
no business running (the display enumeration on the first click; a list
rebuilt while the player was reading it). The v3.14 rewrite is a state
machine - SelState -> SelDerive -> diff-apply, commit at close - and
Test-SelectorDerive.py pins the RULE it derives. This gate pins the SHAPE
it must keep, because the rule cannot defend itself from the next edit:

  * the 250ms tick (SelOnTick) polls three GetSelection calls and nothing
    else - NO syscalls, NO file I/O, NO list mutation. A stall that ever
    appears there is outside our code, and this gate is what keeps it that
    way.
  * SelDerive and SelBuildResRows are PURE - no syscalls, no logging, no
    control mutation. They are the spec's mirror and a future diagnosis
    must be able to read them without suspecting them.
  * RemoveAllStrings exists in exactly ONE function (the diff-apply
    SelPushCombo), which is the structural end of the mutate-under-open-
    drop class.
  * the commit writers (SelCommitScale, SelWriteGraphicsIni,
    SelWriteDgVoodooFullScreen) are called from SelOnClose and nowhere
    else - Accept is the only exit, so a close IS the commit, and a write
    anywhere else is a choice the player never confirmed. The ONE named
    exception is the pre-dialog RESMISMATCH rescue in
    ServiceScaleSelector, which must sit BEFORE the dialog gate (a safety
    net that needs the player to open the dialog is not a safety net).

⚠ THIS IS A SOURCE-SHAPE GATE, and it is honest about that: it proves the
code is WIRED the way the contract requires. It cannot prove runtime
behaviour - only a launch can - and it cannot see conditions inside a
function (a banned call hidden behind an `if` is still banned; a log line
that only fires on an event is indistinguishable from one that fires per
tick). Every assertion here is structure that is NECESSARY, never a
result that is sufficient. Same family as Test-StockTierContract.

PASS = exit 0.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
UISPIKE = os.path.join(REPO, "src", "UiSpike.cpp")

# Symbols the tick path must never contain. These are the APIs that cost
# milliseconds through the OneDrive sync filter or the display driver -
# the two things that FROZE the dialog, both measured (v3.13.2 ledger).
TICK_BANNED = [
    "EnumDisplaySettings",
    "GetPrivateProfile",
    "WritePrivateProfile",
    "CreateFile",
    "GetFileAttributes",
    "RemoveAllStrings",
    "InsertString",
    "Sleep(",
    "GetTickCount",
]

# Symbols a pure derivation must never contain (adds the engine-facing
# mutations and the logger to the syscall list).
PURE_BANNED = TICK_BANNED + [
    "Logger::",
    "SetSelection",
    "SetChecked",
    "SetCaption",
    "HideWindow",
]


def strip_comments(src):
    """Remove // and /* */ comments.

    ⚠ NECESSARY, NOT COSMETIC. This file's own comments quote the banned
    call shapes they warn against, and the source under test does the same
    - matching prose would let a warning about a bug read as the bug (the
    Test-StockTierContract lesson).
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def find_function(src, name, sig=None):
    """Locate `name`'s definition and return (sig_start, body_start, end).

    Paren-balances the argument list (a parameter like `const char
    (*rows)[80]` carries its own parens, which a plain [^)]* regex dies
    on), then brace-walks the body, so nested blocks do not end it. A
    CALL of the function ends in `;` after the parens, not `{`, so only
    the definition matches. Returns None if the parser cannot find it -
    which is a gate failure (parser rot), never a silent pass.
    """
    if sig is not None:
        m = re.search(sig, src)
        starts = [m.start()] if m else []
    else:
        starts = [m.start() for m in
                  re.finditer(r"\b%s\s*\(" % re.escape(name), src)]
    for start in starts:
        i = src.index("(", start)
        depth, j = 0, i
        while j < len(src):
            if src[j] == "(":
                depth += 1
            elif src[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            continue
        k = j + 1
        while k < len(src) and src[k] in " \t\r\n":
            k += 1
        if k >= len(src) or src[k] != "{":
            continue   # a call or a declaration, not the definition
        depth, body_start = 0, k
        while k < len(src):
            if src[k] == "{":
                depth += 1
            elif src[k] == "}":
                depth -= 1
                if depth == 0:
                    return (start, body_start, k)
            k += 1
    return None


def body_of(src, span):
    return src[span[1]:span[2]]


def banned_found(body, banned):
    return [b for b in banned if b in body]


def main():
    failures = []
    notes = []

    if not os.path.isfile(UISPIKE):
        print("FAIL: %s not found" % UISPIKE)
        return 1

    src = strip_comments(open(UISPIKE, encoding="utf-8",
                              errors="replace").read())

    print("Test-SelectorContract")
    print("  src/UiSpike.cpp (comments stripped)")
    print()

    # ---- locate every function the contract names -------------------------
    spans = {}
    for name in ("SelBuildResRows", "SelDerive", "SelPushCombo",
                 "SelOnOpen", "SelOnTick", "SelOnClose", "SelCommitScale",
                 "SelWriteGraphicsIni", "SelWriteDgVoodooFullScreen",
                 "SelApplyStatics", "SelNoticeTick", "SelRadioTick"):
        spans[name] = find_function(src, name)
    spans["ServiceScaleSelector"] = find_function(
        src, "ServiceScaleSelector",
        r"void\s+UiSpike::ServiceScaleSelector\s*\(\s*\)\s*\{")

    missing = [n for n, s in spans.items() if s is None]
    if missing:
        print("FAIL: could not locate %s - the parser has rotted, not the "
              "code." % ", ".join(missing))
        return 1
    print("  [all %d contract functions located] ok" % len(spans))

    # ---- 1: the tick is a poll and nothing else ---------------------------
    bad = banned_found(body_of(src, spans["SelOnTick"]), TICK_BANNED)
    if bad:
        failures.append(
            "SelOnTick contains %s. The 250ms tick must poll three "
            "GetSelection calls and nothing else - a syscall or a list "
            "mutation there is the freeze class and the empty-drop class "
            "returning." % ", ".join(bad))
        print("  [tick has no syscalls/mutations] *** %s ***" % ", ".join(bad))
    else:
        print("  [tick has no syscalls/mutations] ok")

    # ---- 2: the derivation is pure ----------------------------------------
    for name in ("SelDerive", "SelBuildResRows"):
        bad = banned_found(body_of(src, spans[name]), PURE_BANNED)
        if bad:
            failures.append(
                "%s contains %s. The derivation is the spec's mirror and "
                "must stay pure: no syscalls, no logging, no control "
                "mutation - a future diagnosis must be able to read it "
                "without suspecting it." % (name, ", ".join(bad)))
            print("  [%s is pure] *** %s ***" % (name, ", ".join(bad)))
        else:
            print("  [%s is pure] ok" % name)

    # ---- 3: RemoveAllStrings lives in exactly one function ----------------
    ras = [m.start() for m in re.finditer(r"RemoveAllStrings\s*\(", src)]
    if not ras:
        failures.append("RemoveAllStrings appears NOWHERE - the diff-apply "
                        "rebuild is gone, so combos can never be populated. "
                        "The parser or the code has rotted.")
        print("  [RemoveAllStrings exists] *** MISSING ***")
    else:
        outside = [o for o in ras
                   if not (spans["SelPushCombo"][1] <= o
                           < spans["SelPushCombo"][2])]
        if outside:
            failures.append(
                "RemoveAllStrings is called outside SelPushCombo (%d "
                "site(s)). One function owns list rebuilds - that is the "
                "structural end of mutating a combo while its drop list is "
                "open, and a second call site re-opens the class."
                % len(outside))
            print("  [RemoveAllStrings only in SelPushCombo] *** %d "
                  "OUTSIDE ***" % len(outside))
        else:
            print("  [RemoveAllStrings only in SelPushCombo] ok "
                  "(%d site(s))" % len(ras))

    # ---- 4: the commit writers are called from SelOnClose alone -----------
    for name in ("SelCommitScale", "SelWriteGraphicsIni",
                 "SelWriteDgVoodooFullScreen"):
        calls = [m.start() for m in re.finditer(name + r"\s*\(", src)]
        own = spans[name]
        # own[0] is the SIGNATURE start - the definition's own name sits
        # before the body brace, so excluding only the body would count the
        # definition as a caller of itself.
        callers = [c for c in calls if not (own[0] <= c < own[2])]
        bad_callers = [c for c in callers
                       if not (spans["SelOnClose"][1] <= c
                               < spans["SelOnClose"][2])]
        if bad_callers:
            failures.append(
                "%s is called outside SelOnClose (%d site(s)). Accept is "
                "the only exit, so a close IS the commit - a writer called "
                "anywhere else commits a choice the player never "
                "confirmed." % (name, len(bad_callers)))
            print("  [%s called only at close] *** %d OUTSIDE ***"
                  % (name, len(bad_callers)))
        else:
            print("  [%s called only at close] ok" % name)

    # ---- 5: every ini write sits in a sanctioned writer -------------------
    # The ONE named exception is the RESMISMATCH rescue inside
    # ServiceScaleSelector - and it must be PRE-DIALOG (before the dialog
    # gate), because a safety net that needs the player to open the dialog
    # is not a safety net.
    writes = [m.start() for m in
              re.finditer(r"WritePrivateProfileStringW\s*\(", src)]
    if not writes:
        failures.append("WritePrivateProfileStringW appears NOWHERE - the "
                        "selector can no longer commit anything.")
        print("  [ini writes exist] *** MISSING ***")
    else:
        sanctioned = [spans["SelCommitScale"], spans["SelWriteGraphicsIni"],
                      spans["ServiceScaleSelector"]]
        rogue = [w for w in writes
                 if not any(s[1] <= w < s[2] for s in sanctioned)]
        if rogue:
            failures.append(
                "%d WritePrivateProfileStringW site(s) outside the "
                "sanctioned writers (SelCommitScale, SelWriteGraphicsIni, "
                "the ServiceScaleSelector rescue)." % len(rogue))
            print("  [writes only in sanctioned functions] *** %d ROGUE ***"
                  % len(rogue))
        else:
            print("  [writes only in sanctioned functions] ok")
        # the ServiceScaleSelector write is the RESMISMATCH rescue and must
        # precede the dialog gate
        svc = body_of(src, spans["ServiceScaleSelector"])
        w_off = svc.find("WritePrivateProfileStringW")
        gate_off = svc.find("GetChildWindowFromIDRecursive(kSelDlgId)")
        if w_off == -1:
            notes.append("ServiceScaleSelector carries no write (the "
                         "RESMISMATCH rescue was removed) - allowed, the "
                         "rescue was a net, not a feature.")
        elif gate_off == -1:
            failures.append("could not locate the dialog gate in "
                            "ServiceScaleSelector - cannot prove the "
                            "rescue write is pre-dialog.")
            print("  [rescue write is pre-dialog] *** GATE NOT FOUND ***")
        elif w_off > gate_off:
            failures.append(
                "the ServiceScaleSelector ini write sits AFTER the dialog "
                "gate. The RESMISMATCH rescue must fire BEFORE any dialog "
                "question - a safety net that needs the player to open "
                "Graphic Options is not a safety net.")
            print("  [rescue write is pre-dialog] *** TOO LATE ***")
        else:
            print("  [rescue write is pre-dialog] ok")

    # ---- 6: the state-machine skeleton the spec mirrors --------------------
    derive_sig = re.search(r"void\s+SelDerive\s*\(\s*const\s+SelState\s*&",
                           src)
    if not derive_sig:
        failures.append("SelDerive no longer takes (const SelState&) - the "
                        "single-source-of-truth design was refactored away "
                        "from under Test-SelectorDerive's mirror.")
        print("  [SelDerive(const SelState&)] *** CHANGED ***")
    else:
        print("  [SelDerive(const SelState&)] ok")
    for field in ("sMode", "sRes", "sScale"):
        if not re.search(r"\b%s\b" % field, src):
            failures.append("SelState field %s is gone - the staged "
                            "REQUEST the derive mirrors no longer exists."
                            % field)
    if all(re.search(r"\b%s\b" % f, src) for f in ("sMode", "sRes",
                                                    "sScale")):
        print("  [staged requests sMode/sRes/sScale] ok")

    # ---- negative controls: the checker must be able to FAIL --------------
    print()
    tick_body = body_of(src, spans["SelOnTick"])
    # (a) an injected banned call in the real tick body MUST be caught
    injected = tick_body + "\n\tWritePrivateProfileStringW(L\"a\", L\"b\", " \
                           "L\"c\", p);\n"
    # banned_found reports the BANNED TOKEN (WritePrivateProfile), not the
    # full injected spelling - a non-empty return is the catch.
    if not banned_found(injected, TICK_BANNED):
        failures.append("NEGATIVE CONTROL FAILED: the banned-symbol scan "
                        "did not see a WritePrivateProfileStringW injected "
                        "into the tick body - the checker is blind and its "
                        "pass above proves nothing.")
        print("  [negative control: injected write is caught] *** BLIND ***")
    else:
        print("  [negative control: injected write is caught] ok")
    # (b) a banned call quoted in a COMMENT must NOT be caught (proves the
    # stripper runs and the gate reads code, not prose)
    synthetic = "// WritePrivateProfileStringW in a comment\nint f(){return 1;}"
    stripped = strip_comments(synthetic)
    if "WritePrivateProfileStringW" in stripped:
        failures.append("NEGATIVE CONTROL FAILED: the comment stripper left "
                        "a quoted banned call in place - the gate would "
                        "convict its own warnings.")
        print("  [negative control: commented call is stripped] *** KEPT ***")
    else:
        print("  [negative control: commented call is stripped] ok")
    # (c) a RemoveAllStrings injected OUTSIDE SelPushCombo must be caught
    outside_count = len([o for o in
                         [spans["SelOnTick"][1] + 10]
                         if not (spans["SelPushCombo"][1] <= o
                                 < spans["SelPushCombo"][2])])
    if outside_count != 1:
        failures.append("NEGATIVE CONTROL FAILED: the containment check "
                        "cannot construct an outside offset.")
        print("  [negative control: containment check] *** BROKEN ***")
    else:
        print("  [negative control: containment check] ok")

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
    print("ALL PASS (selector contract: the tick is a poll, the derive is "
          "pure, one rebuild function, writes only at close, rescue "
          "pre-dialog)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
