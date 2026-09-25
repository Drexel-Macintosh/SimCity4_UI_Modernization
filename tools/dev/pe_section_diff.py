"""pe_section_diff.py - are two PE builds the same code? Compares each
section's raw bytes and reports which differ, ignoring the header timestamp.

    python tools/dev/pe_section_diff.py OLD.dll NEW.dll

A dead-code removal that the linker had already discarded (/OPT:REF) leaves
.text identical. MSVC still stamps a build GUID into the debug directory
(inside .rdata), so a handful of .rdata bytes differ on every rebuild; the
report lists the differing offsets so that can be told apart from real change.
"""
import struct
import sys


def sections(path):
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    table = pe + 24 + opt
    out = {}
    for i in range(nsec):
        o = table + i * 40
        name = data[o:o + 8].rstrip(b"\0").decode("ascii", "replace")
        size, ptr = struct.unpack_from("<II", data, o + 16)
        out[name] = data[ptr:ptr + size]
    return out


def main(a, b):
    sa, sb = sections(a), sections(b)
    same = True
    for name in sorted(set(sa) | set(sb)):
        x, y = sa.get(name, b""), sb.get(name, b"")
        if x == y:
            print("%-8s identical (%d bytes)" % (name, len(x)))
            continue
        same = False
        diffs = [i for i in range(min(len(x), len(y))) if x[i] != y[i]]
        print("%-8s DIFFERS: sizes %d vs %d, %d differing bytes, first offsets %s"
              % (name, len(x), len(y), len(diffs), diffs[:8]))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
