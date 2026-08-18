"""idscan_ab.py - locate 32-bit id literals anywhere in the exe, per section.

READ ONLY. Prints VA, section, owning function (from funcs.json when the hit
is in .text) for every occurrence of each id given on the command line.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as C


def sections():
    d = C.exe_bytes()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    base = pe + 24 + opt
    out = []
    for i in range(nsec):
        o = base + 40 * i
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vsize = struct.unpack_from("<I", d, o + 8)[0]
        va = struct.unpack_from("<I", d, o + 12)[0]
        rsize = struct.unpack_from("<I", d, o + 16)[0]
        roff = struct.unpack_from("<I", d, o + 20)[0]
        out.append((name, va + C.IMAGE_BASE, vsize, roff, rsize))
    return out


def sec_of(off, secs):
    for name, va, vsize, roff, rsize in secs:
        if roff <= off < roff + rsize:
            return name, va + (off - roff)
    return "?", off + C.IMAGE_BASE


def main():
    ids = [int(a, 16) for a in sys.argv[1:]]
    d = C.exe_bytes()
    secs = sections()
    try:
        fm = C.FuncMap()
    except Exception:
        fm = None
    for v in ids:
        pat = struct.pack("<I", v)
        print("=" * 70)
        print("0x%08X" % v)
        pos = 0
        n = 0
        while True:
            i = d.find(pat, pos)
            if i < 0:
                break
            pos = i + 1
            n += 1
            name, va = sec_of(i, secs)
            extra = ""
            if name == ".text" and fm is not None:
                try:
                    f = fm.owner(va)
                    if f:
                        extra = "  fn 0x%06X" % f
                except Exception:
                    pass
            print("  off 0x%06X  VA 0x%08X  %-8s%s   ctx %s" % (
                i, va, name, extra, d[max(0, i - 10):i + 14].hex()))
        if n == 0:
            print("  (no occurrence anywhere in the file)")


main()
