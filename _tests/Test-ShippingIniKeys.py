#!/usr/bin/env python3
"""
Test-ShippingIniKeys - the shipped user ini may not document a key the DLL
does not read.

WHY THIS EXISTS
    A key printed in the user's ini with a comment explaining what it does is a
    PROMISE. Three keys in the old 24 KB ini (Scaling/AutoConfig, PresentWidth,
    PresentHeight) were parsed into Settings and then read by nothing at all -
    a player could set them, watch nothing happen, and have no way to tell the
    difference between "wrong value" and "dead key". That is the same failure
    class as a silent truncation: the instrument (the ini) says something the
    code does not do.

WHAT IT CHECKS
    Every key=value line in _packaging/SC4UIScale.ini resolves to a real read in
    src/Settings.cpp or src/UiSpike.cpp, under the SAME section name.

    Covers five read paths - the two Win32 wide entry points, the ANSI one
    UiSpike's live-tune poll uses, Settings.cpp's own float helper
    (GetPrivateProfileFloat, which has NO trailing W and was the reason the
    first version of this check produced a false failure on ScaleFactor), and
    since v4.0.7 the vendored IniReader helpers in Settings.cpp, where sections
    come from get_section_optional("Name") and every key read goes through the
    gi/gu/gf lambdas as (sectionVar, "Key", ...).

POSITIVE CONTROL
    The run asserts that an invented key is NOT reported as read. Without that,
    a regex that silently matched everything would pass this gate while proving
    nothing (project law: state the positive control - a probe that finds
    nothing is not evidence until you show it could have found something).

Exit 0 = pass. Run from the repo root.
"""

import os
import io
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INI = os.path.join(REPO, "_packaging", "SC4UIScale.ini")
SOURCES = ("Settings.cpp", "UiSpike.cpp")

# Settings.cpp names its sections with local constants; map them to the literal
# section names that actually appear in the ini file.
CONST_TO_SECTION = {
    "Spike": "UiSpike",
    "Logging": "Logging",
    "Scaling": "Scaling",
    "Touch": "TouchControls",
    "Gestures": "Gestures",
}

# Since the v4.0.7 IniReader migration, Settings.cpp holds each section in an
# optional named after it and reads keys through the gi/gu/gf lambdas.
VAR_TO_SECTION = {
    "scaling": "Scaling",
    "spike": "UiSpike",
    "logging": "Logging",
}


def keys_read_by_the_dll():
    src = ""
    for name in SOURCES:
        with open(os.path.join(REPO, "src", name), encoding="utf-8", errors="replace") as fh:
            src += fh.read()

    found = set()

    # GetPrivateProfileIntW / StringW / the local GetPrivateProfileFloat helper,
    # all called as (kSection, L"Key", ...). Note the optional trailing W: the
    # float helper does not have one.
    for m in re.finditer(r'GetPrivateProfile\w*?W?\(\s*k(\w+)\s*,\s*L"(\w+)"', src):
        found.add((CONST_TO_SECTION.get(m.group(1), m.group(1)), m.group(2)))

    # UiSpike's live-tune poll uses the ANSI form with literal section names.
    for m in re.finditer(r'GetPrivateProfile\w*?A\(\s*"(\w+)"\s*,\s*"(\w+)"', src):
        found.add((m.group(1), m.group(2)))

    # Settings.cpp's IniReader path: gi/gu/gf(sectionVar, "Key", ...).
    for m in re.finditer(r'\b(?:gi|gu|gf)\(\s*(\w+)\s*,\s*"(\w+)"', src):
        found.add((VAR_TO_SECTION.get(m.group(1), m.group(1)), m.group(2)))

    return found


def keys_declared_in_text(text):
    declared = []
    section = None
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif line and not line.startswith(";") and "=" in line:
            declared.append((section, line.split("=", 1)[0].strip()))
    return declared


def keys_declared_in_the_ini():
    with open(INI, encoding="utf-8") as fh:
        return keys_declared_in_text(fh.read())


def starter_ini_text():
    """kStarterIni is THE ini every v4.5.x user actually gets: no install
    path ships _packaging/SC4UIScale.ini any more - the DLL seeds this C
    string at the Plugins root on first launch. Extracted from the source,
    concatenated string literals decoded, so this gate validates the file
    that ships rather than the reference copy that ships to nobody."""
    with open(os.path.join(REPO, "src", "ScaleTier.cpp"), encoding="utf-8",
              errors="replace") as fh:
        src = fh.read()
    # The terminator is the semicolon AFTER the last string literal - the ini
    # text itself is full of `;` comment markers, so "first semicolon" is
    # wrong. Match the whole run of adjacent literals instead.
    m = re.search(r'kStarterIni\s*=\s*((?:\s*"(?:[^"\\]|\\.)*")+)\s*;', src)
    if not m:
        return None
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
    if not parts:
        return None
    text = "".join(parts)
    return (text.replace("\\r\\n", "\n")
                .replace('\\"', '"')
                .replace("\\\\", "\\"))


# ---------------------------------------------------------------------------
# THE OTHER DIRECTION. Everything above checks that every key IN the ini is
# read by the DLL. That is only half the contract, and the missing half was a
# real ship blocker: _packaging\SC4UIScale.ini shipped for weeks WITHOUT
# ScaleAll or ScaleRegion. Both default to FALSE in Settings.h and nothing
# else ever sets them true, so a fresh install off that file loaded the mod
# completely inert - no scaling, no error, no log complaint. A forward-only
# gate cannot see that, because an absent key is not a wrong key.
#
# So: any setting that gates a whole feature AND whose built-in default is
# off MUST be present in the shipped ini. The default is re-read from
# Settings.h each run, so if someone later flips a default to true this gate
# stops demanding the key instead of going stale.
# ---------------------------------------------------------------------------
REQUIRED = {
    "ScaleAll": ("spikeScaleAll",
                 "the city-view scaler - the whole mod"),
    "ScaleRegion": ("spikeScaleRegion",
                    "the region screen half, including the region map"),
}


def gate_required_keys(declared, settings_src):
    problems = []
    for key, (member, what) in REQUIRED.items():
        m = re.search(r"bool\s+%s\s*=\s*(true|false)\s*;" % re.escape(member),
                      settings_src)
        if not m:
            problems.append("could not find `bool %s = ...` in Settings.h - this"
                            " gate has gone stale and is no longer checking"
                            " anything" % member)
            continue
        default_off = (m.group(1) == "false")
        present = any(k == key for (_sect, k) in declared)
        if default_off and not present:
            problems.append("[UiSpike] %s is MISSING from the shipped ini and"
                            " defaults to false -> %s never runs. Silent,"
                            " total, and indistinguishable from 'the mod does"
                            " not work'." % (key, what))
        elif default_off:
            print("  [UiSpike] %-15s present (default false - load-bearing: %s)"
                  % (key, what))
        else:
            print("  [UiSpike] %-15s default is now true; presence optional"
                  % key)
    return problems


def main():
    if not os.path.isfile(INI):
        print("FAIL: %s is missing" % INI)
        return 1

    # BOM check: a BOM makes the DLL abandon the file and boot windowed.
    with open(INI, "rb") as fh:
        if fh.read(3) == b"\xef\xbb\xbf":
            print("FAIL: %s starts with a UTF-8 BOM - the DLL will ignore it" % INI)
            return 1

    read = keys_read_by_the_dll()
    declared = keys_declared_in_the_ini()

    print("Test-ShippingIniKeys")
    print("  ini      : %s" % os.path.relpath(INI, REPO))
    print("  declared : %d keys" % len(declared))
    print("  DLL reads: %d distinct section/key pairs" % len(read))
    print()

    failures = []
    for section, key in declared:
        ok = (section, key) in read
        print("  [%s] %-14s %s" % (section, key, "read by the DLL" if ok else "*** NOT READ ***"))
        if not ok:
            failures.append("[%s] %s" % (section, key))

    print()
    if ("UiSpike", "ThisKeyDoesNotExist") in read:
        print("FAIL: positive control tripped - the matcher reports invented keys as read,")
        print("      so a pass here would prove nothing.")
        return 1
    print("  positive control: an invented key is correctly NOT matched.")

    if failures:
        print()
        print("FAIL: the shipped ini documents %d key(s) the DLL never reads:" % len(failures))
        for f in failures:
            print("    %s" % f)
        print("  Either wire the key up or delete it. Do not ship a promise the code")
        print("  does not keep.")
        return 1

    print()
    print("  required load-bearing keys:")
    with io.open(os.path.join(REPO, "src", "Settings.h"), encoding="utf-8",
                 errors="replace") as f:
        settings_src = f.read()
    missing = gate_required_keys(declared, settings_src)
    if missing:
        print()
        print("FAIL: the shipped ini omits %d load-bearing key(s):" % len(missing))
        for m in missing:
            print("    %s" % m)
        return 1

    # ------------------------------------------------------------------
    # THE STARTER INI - the ini v4.5.x users ACTUALLY get. Since v4.5.0 no
    # install path ships _packaging/SC4UIScale.ini; the DLL seeds
    # kStarterIni at the Plugins root on first launch. v4.5.1 seeded five
    # of its eight keys under [Scaling] while Settings.cpp reads all five
    # from [UiSpike] - five dead keys this gate structurally could not see,
    # because it only validated the reference file that ships to nobody.
    # ------------------------------------------------------------------
    starter = starter_ini_text()
    if starter is None:
        print()
        print("FAIL: could not extract kStarterIni from src/ScaleTier.cpp -")
        print("      the seeded ini would go unvalidated, which is how the")
        print("      v4.5.1 dead-section defect shipped.")
        return 1
    sdecl = keys_declared_in_text(starter)
    print()
    print("  kStarterIni (seeded by the DLL, src/ScaleTier.cpp): %d keys" % len(sdecl))
    if len(sdecl) < 5:
        print("FAIL: only %d key(s) parsed out of kStarterIni - the extraction"
              " is broken, not the ini." % len(sdecl))
        return 1
    sfail = []
    for section, key in sdecl:
        ok = (section, key) in read
        print("  [%s] %-14s %s" % (section, key,
              "read by the DLL" if ok else "*** NOT READ ***"))
        if not ok:
            sfail.append("[%s] %s" % (section, key))
    # MUTATION CONTROL: the exact v4.5.1 defect (AutoScale seeded under
    # [Scaling]) must be reportable, or a pass above proves nothing about
    # this gate's ability to fail.
    if ("Scaling", "AutoScale") in read:
        print("FAIL: mutation control is vacuous - the matcher claims the DLL")
        print("      reads AutoScale from [Scaling], so the dead-section")
        print("      defect could never be caught.")
        return 1
    print("  mutation control: [Scaling] AutoScale would read as NOT READ -")
    print("      the v4.5.1 dead-section defect is catchable by this gate.")
    if sfail:
        print()
        print("FAIL: kStarterIni seeds %d key(s) in a section the DLL never"
              " reads them from:" % len(sfail))
        for f in sfail:
            print("    %s" % f)
        print("  This is the v4.5.1 dead-section class. Fix the SECTION in")
        print("  kStarterIni - the compiled defaults masking it today will not")
        print("  mask a user's edit.")
        return 1
    smissing = gate_required_keys(sdecl, settings_src)
    if smissing:
        print()
        print("FAIL: kStarterIni omits %d load-bearing key(s):" % len(smissing))
        for m2 in smissing:
            print("    %s" % m2)
        return 1

    print()
    print("ALL PASS (%d reference keys + %d seeded keys, all reachable;"
          " load-bearing keys present in both; no BOM)"
          % (len(declared), len(sdecl)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
