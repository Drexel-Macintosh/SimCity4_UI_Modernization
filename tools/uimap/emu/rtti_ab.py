"""rtti_ab.py - MSVC RTTI name for a vtable VA (and reverse: name -> vtables).

READ ONLY.
    python emu/rtti_ab.py 0xA85800          # vtable VA -> class name
    python emu/rtti_ab.py --find cSC4Win    # substring over all .?AV names
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C


def rd32(va):
    d = C.exe_bytes()
    off = va - C.IMAGE_BASE
    if off < 0 or off + 4 > len(d):
        return None
    return struct.unpack_from("<I", d, off)[0]


def cstr(va, n=200):
    d = C.exe_bytes()
    off = va - C.IMAGE_BASE
    e = d.find(b"\0", off, off + n)
    if e < 0:
        return ""
    return d[off:e].decode("latin1")


def name_for_vtable(vt):
    col = rd32(vt - 4)
    if not col:
        return None
    td = rd32(col + 12)
    if not td:
        return None
    return cstr(td + 8)


def main():
    if sys.argv[1] == "--find":
        pat = sys.argv[2].encode("latin1")
        d = C.exe_bytes()
        pos = 0
        seen = set()
        while True:
            i = d.find(b".?AV", pos)
            if i < 0:
                break
            pos = i + 1
            e = d.find(b"\0", i, i + 200)
            if e < 0:
                continue
            nm = d[i:e]
            if pat in nm and nm not in seen:
                seen.add(nm)
                td = i - 8 + C.IMAGE_BASE
                print("  typedesc 0x%08X  %s" % (td, nm.decode("latin1")))
        return
    for a in sys.argv[1:]:
        vt = int(a, 16)
        print("0x%08X -> %s" % (vt, name_for_vtable(vt)))


main()
