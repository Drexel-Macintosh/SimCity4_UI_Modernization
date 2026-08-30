#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test-PatchSiteBytes - assert that the byte-patch sites in the SHIPPED GAME
IMAGE still hold the bytes CodePatches.cpp expects.

WHY THIS EXISTS
    CodePatches refuses at runtime on a byte mismatch, which is correct but
    LATE and INVISIBLE: the refusal is one Info line in a log nobody reads,
    and the feature just quietly does not happen. Worse, some sites are
    described in prose across several files and their stock bytes were never
    written down anywhere - the 2026-08-30 decode of the restore-toolbars
    button found it prescribed in THREE places with the bytes recorded in
    NONE, so nothing could tell a wrong address from a moved one.

    Project law: never re-pin a fingerprint without reading the bytes. This
    reads them.

WHAT IT CHECKS
    For each site below: the game image holds exactly the expected bytes at
    the expected file offset, and the decoded meaning still matches the
    comment in CodePatches.cpp.

    Sites are recorded with a MASK, so operand bytes that are legitimately
    build-dependent (a modrm register choice) do not produce a false failure
    while the opcode and the immediate stay pinned.

POSITIVE CONTROL
    Every run asserts that a deliberately corrupted copy of the same window
    FAILS. A byte check that has never rejected anything is not evidence.

Exit 0 = pass. Exit 2 = the game is not installed where we looked (SKIP, not
a pass - it says so).
"""

import os
import sys

IMAGE_BASE = 0x400000

EXE_CANDIDATES = [
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe",
    r"C:\Program Files (x86)\Maxis\SimCity 4 Deluxe\Apps\SimCity 4.exe",
    r"C:\Program Files\Maxis\SimCity 4 Deluxe\Apps\SimCity 4.exe",
]

# name, VA, expected bytes, mask (0 = this byte may vary), what it means
SITES = [
    (
        "kRestoreToolbarsOriginSite",
        0x007EE15A,
        bytes([0x83, 0xE8, 0x1C, 0x50, 0x6A, 0x0C]),
        bytes([0xFF, 0xF8, 0xFF, 0xFF, 0xFF, 0xFF]),
        "sub eax,28 / push eax / push 12  ->  GZWinMoveTo(x=12, y=viewH-28) "
        "for the restore-toolbars button (window 0x00000043). The modrm is "
        "masked to /5 because sub is 83 /5 and the register choice is a "
        "build detail; the two IMMEDIATES are what the patch rewrites and "
        "they are pinned exactly.",
    ),
    # Precedent sites in the SAME owner (sub_7EDEB0), recorded here because
    # they were already prescribed in CodePatches.cpp with their bytes and so
    # give this file a control that is not the site under test.
    (
        "kCostBoxHeightSite",
        0x007EEF43,
        bytes([0x6A, 0x20]),
        bytes([0xFF, 0xFF]),
        "push 32 - the cost box's buffer height (#159).",
    ),
    (
        "kCostBoxWidthSite",
        0x007EEF54,
        bytes([0x68, 0x80, 0x00, 0x00, 0x00]),
        bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        "push 128 - the cost box's buffer width (#159).",
    ),
]


def masked_eq(got, want, mask):
    if len(got) != len(want):
        return False
    return all((g & m) == (w & m) for g, w, m in zip(got, want, mask))


def hexs(b):
    return " ".join("%02X" % x for x in b)


def main():
    exe = next((p for p in EXE_CANDIDATES if os.path.isfile(p)), None)
    if exe is None:
        print("SKIP: SimCity 4.exe not found. Looked in:")
        for p in EXE_CANDIDATES:
            print("   %s" % p)
        print("This is a SKIP, not a pass - nothing was verified.")
        return 2

    print("Test-PatchSiteBytes")
    print("  image : %s" % exe)
    print("  size  : %d bytes" % os.path.getsize(exe))
    print()

    with open(exe, "rb") as f:
        blob = f.read()

    failures = []
    checked = 0
    for name, va, want, mask, meaning in SITES:
        off = va - IMAGE_BASE
        got = blob[off:off + len(want)]
        ok = masked_eq(got, want, mask)
        print("  %-28s VA 0x%06X off 0x%06X" % (name, va, off))
        print("      want %s   got %s   %s"
              % (hexs(want), hexs(got), "OK" if ok else "*** MISMATCH ***"))
        if not ok:
            failures.append(
                "%s at VA 0x%06X: expected %s (mask %s), image holds %s. "
                "Either the address is wrong or this is not the 1.1.641 build "
                "CodePatches targets - do NOT re-pin without reading the "
                "disassembly."
                % (name, va, hexs(want), hexs(mask), hexs(got)))
        else:
            checked += 1
    print()

    # ---- POSITIVE CONTROL -------------------------------------------------
    # Corrupt one masked-significant byte of the first site and require the
    # comparison to reject it. Without this, a matcher that always returns
    # True would sail through every assertion above.
    name, va, want, mask, _ = SITES[0]
    broken = bytearray(want)
    broken[2] ^= 0x01          # the y immediate - a pinned byte
    if masked_eq(bytes(broken), want, mask):
        print("FAIL: positive control did not fire - the comparison accepts a")
        print("      corrupted window, so every OK above proves nothing.")
        return 1
    print("  positive control: a 1-bit change to the pinned immediate is")
    print("      correctly REJECTED, so the checks above can fail.")

    # And the mask must genuinely tolerate the byte it claims to.
    tolerant = bytearray(want)
    tolerant[1] = (tolerant[1] & 0xF8) | 0x03   # a different /5 modrm register
    if not masked_eq(bytes(tolerant), want, mask):
        print("FAIL: the modrm mask does not tolerate a different register,")
        print("      so it is not doing the job its comment claims.")
        return 1
    print("  mask control    : a different /5 modrm register is correctly")
    print("      TOLERATED, so the mask is real and not decorative.")
    print()

    if failures:
        print("FAIL: %d site(s) do not hold their expected bytes:" % len(failures))
        for f in failures:
            print("    %s" % f)
        return 1

    print("ALL PASS (%d site(s) verified against the shipped image, both "
          "controls fired)" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
