#!/usr/bin/env python3
r"""Read raw dwords (vtable slots) from SimCity 4.exe at a VA. Read-only.

    python vt_read.py 0xAA4868 34

Written 2026-08-17 for #188: the marker's occupant interface table
(vt1 = 0xAA4868) matched cISC4Occupant's 34 declared virtuals exactly, so
slot N of this table IS the header's method N. Printing the slots lets the
header name every hot slot the live VTCAP counted.
"""
import struct
import sys

GAME_EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

# cISC4Occupant declared order (cIGZUnknown 3 first), from
# vendor\gzcom-dll\...\include\cISC4Occupant.h - used only as a LABEL for
# the printout; a mismatch in count is reported, never silently assumed.
OCCUPANT = [
    "QueryInterface", "AddRef", "Release",
    "GetType", "GetPosition", "SetPosition", "GetBoundingBox",
    "SetBoundingBox", "GetHighlight", "SetHighlight", "GetOccupantGroups",
    "IsOccupantGroup", "GetSize", "SetSize", "GetOccupantManagerBBox",
]


def load(path):
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    n = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    secs = []
    for i in range(n):
        o = pe + 24 + opt + i * 40
        name = data[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, ra = struct.unpack_from("<IIII", data, o + 8)
        secs.append((name, va, vs, ra, rs))
    return data, base, secs


def va_to_off(va, base, secs):
    rva = va - base
    for name, sva, vs, ra, rs in secs:
        if sva <= rva < sva + max(vs, rs):
            return ra + (rva - sva)
    return None


def main():
    va = int(sys.argv[1], 0)
    count = int(sys.argv[2], 0) if len(sys.argv) > 2 else 24
    data, base, secs = load(GAME_EXE)
    for i in range(count):
        slot_va = va + i * 4
        off = va_to_off(slot_va, base, secs)
        if off is None:
            print("slot %2d (+0x%02X): <unmapped>" % (i, i * 4))
            continue
        val = struct.unpack_from("<I", data, off)[0]
        print("slot %2d (+0x%02X): 0x%08X" % (i, i * 4, val))


if __name__ == "__main__":
    main()
