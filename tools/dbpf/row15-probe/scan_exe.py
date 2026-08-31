#!/usr/bin/env python3
r"""Byte-scan the shipped game executable for 32-bit constants.

Every id is scanned as a little-endian dword AND as an ASCII hex string, at
every byte offset (not dword-aligned).  Each run prints NEGATIVE CONTROLS
alongside the targets: ids adjacent to the target and a nonsense id.  A hit on
a negative control means the scan is noise and the run must be discarded.

    python scan_exe.py 8A416A99 2A499F85 ...

Read-only.  Never writes to the game install.
"""
import os
import struct
import sys

GAME = os.environ.get(
    "SC4_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe")
EXE = os.path.join(GAME, "Apps", "SimCity 4.exe")

# ids whose presence is NOT in question -- if these miss, the scan is broken
POSITIVE = [0x27812810, 0x27812821, 0x00000010]
# ids that must MISS -- if these hit, a hit means nothing
# 0xDEADBEEF is NOT usable here: it occurs 40 times as a fill/guard pattern in
# this binary.  A negative control has to be a value with no reason to exist.
NEGATIVE = [0x1234ABCD, 0x5A5AF00D, 0x7E7E1357]


def count(blob, needle):
    n = 0
    k = blob.find(needle)
    offs = []
    while k >= 0:
        n += 1
        if len(offs) < 8:
            offs.append(k)
        k = blob.find(needle, k + 1)
    return n, offs


def scan(blob, val, label=""):
    le = struct.pack("<I", val)
    n_le, offs = count(blob, le)
    n_asc = count(blob, ("%08x" % val).encode())[0] + \
        count(blob, ("%08X" % val).encode())[0]
    print("  0x%08X %-10s dword-LE hits=%-4d ascii-hex hits=%-3d  first offs=%s"
          % (val, label, n_le, n_asc, ["0x%X" % o for o in offs]))
    return n_le


def main(argv):
    with open(EXE, "rb") as f:
        blob = f.read()
    print("EXE %s  (%d bytes)" % (EXE, len(blob)))
    print("POSITIVE CONTROLS (must hit):")
    ok = all(scan(blob, v, "ctl+") > 0 for v in POSITIVE)
    print("NEGATIVE CONTROLS (must miss):")
    bad = sum(scan(blob, v, "ctl-") for v in NEGATIVE) > 0
    print("controls: positive %s, negative %s"
          % ("PASS" if ok else "FAIL", "PASS" if not bad else "FAIL"))
    print("TARGETS:")
    for a in argv:
        v = int(a, 16)
        n = scan(blob, v, "TARGET")
        # ADJACENCY CONTROL: the two ids either side of the target.  They have
        # no meaning, so their hit count is this scan's local noise floor.
        n_lo = scan(blob, (v - 1) & 0xFFFFFFFF, " adj-1")
        n_hi = scan(blob, (v + 1) & 0xFFFFFFFF, " adj+1")
        print("    -> target %d hits vs local noise floor %d/%d : %s"
              % (n, n_lo, n_hi,
                 "SIGNAL" if n > max(n_lo, n_hi) else "NOT DISTINGUISHABLE"))
    return 0 if (ok and not bad) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
