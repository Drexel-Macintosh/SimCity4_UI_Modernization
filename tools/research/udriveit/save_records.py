#!/usr/bin/env python3
r"""Walk every subfile of an SC4 city save as a stream of persisted records.

Record header measured from the file (not assumed):
    u32 size      bytes of THIS record INCLUDING the size field
    u32 crc
    u32 memAddr   heap pointer the object had at save time
    u16 verMajor
    u16 verMinor
    ... class payload ...
The subfile's DBPF TYPE id IS the persisted class's GZCLSID; the record itself
carries no class id, which is why the subfile type is the class census key.
A subfile is accepted as a record array only if the record sizes TILE the
decompressed buffer exactly with no slack.
"""
import sys, struct, collections
from sc4save import Save

DIR_TYPE = 0xE86B1EEF


def walk(buf):
    recs, p, n = [], 0, len(buf)
    while p + 12 <= n:
        size, crc, mem = struct.unpack_from("<III", buf, p)
        if size < 12 or p + size > n:
            return recs, False
        vmaj, vmin = struct.unpack_from("<HH", buf, p + 12) if size >= 16 else (0, 0)
        recs.append((p, size, crc, mem, vmaj, vmin))
        p += size
    return recs, (p == n and len(recs) > 0)


def scan(path):
    s = Save(path)
    out = []
    for e in sorted(s.entries):
        t, g, i, off, sz = e
        if t == DIR_TYPE:
            continue
        d = s.data(e)
        recs, ok = walk(d)
        out.append((t, g, i, recs if ok else None, len(d), sz, d))
    return s, out


def main(path):
    s, rows = scan(path)
    ra = [r for r in rows if r[3] is not None]
    op = [r for r in rows if r[3] is None]
    print("== %s ==  %d subfiles, %d record-arrays, %d opaque" % (path, len(rows), len(ra), len(op)))
    print()
    print("---- RECORD-ARRAY subfiles sorted by OBJECT COUNT ----")
    print("%-10s %-9s %8s %10s  %s" % ("CLSID", "GROUP", "OBJECTS", "UNCOMP", "versions / rec-size histogram"))
    for t, g, i, recs, ul, rl, d in sorted(ra, key=lambda r: (len(r[3]), r[0])):
        vers = collections.Counter("%d.%d" % (r[4], r[5]) for r in recs)
        sizes = collections.Counter(r[1] for r in recs)
        vs = ",".join("v%s x%d" % (k, v) for k, v in vers.most_common(3))
        ss = ",".join("%dB x%d" % (k, v) for k, v in sizes.most_common(3))
        print("0x%08X %08x %8d %10d  %s | %s" % (t, g, len(recs), ul, vs, ss))
    print()
    print("---- OPAQUE subfiles (not a record stream) ----")
    for t, g, i, recs, ul, rl, d in sorted(op):
        print("0x%08X/%08x/%08x  %8d B  first16=%s" % (t, g, i, ul, d[:16].hex()))


if __name__ == "__main__":
    main(sys.argv[1])
