#!/usr/bin/env python3
r"""Read-only DBPF reader specialised for SimCity 4 .sc4 CITY SAVES.

A .sc4 is a DBPF 1.0 archive.  Unlike the shipped .dat archives the save's
index can use minor version 1 (20-byte entries) or 2 (24-byte entries, an
extra u32 wedged after the instance = the "instance high" word), and almost
every subfile is QFS/RefPack compressed with its uncompressed length recorded
in the DIR subfile (type 0xE86B1EEF).

Nothing here writes.  Callers pass a COPY of the save.
"""
import struct, sys, collections

DIR_TYPE = 0xE86B1EEF


def qfs_decompress(data):
    """RefPack/QFS.  `data` starts at the 4-byte compressed length."""
    # SC4 layout: u32 compressed-size, 0x10 0xFB, u24 BE uncompressed size
    if len(data) >= 6 and data[4] == 0x10 and data[5] == 0xFB:
        p = 6
    elif len(data) >= 2 and data[0] == 0x10 and data[1] == 0xFB:
        p = 2
    else:
        raise ValueError("not QFS (sig %s)" % data[:6].hex())
    ulen = (data[p] << 16) | (data[p + 1] << 8) | data[p + 2]
    p += 3
    out = bytearray()
    n = len(data)
    while p < n:
        b0 = data[p]
        if b0 < 0x80:
            b1 = data[p + 1]; p += 2
            plain = b0 & 0x03
            copy = ((b0 & 0x1C) >> 2) + 3
            off = ((b0 & 0x60) << 3) + b1 + 1
        elif b0 < 0xC0:
            b1 = data[p + 1]; b2 = data[p + 2]; p += 3
            plain = (b1 >> 6) & 0x03
            copy = (b0 & 0x3F) + 4
            off = ((b1 & 0x3F) << 8) + b2 + 1
        elif b0 < 0xE0:
            b1 = data[p + 1]; b2 = data[p + 2]; b3 = data[p + 3]; p += 4
            plain = b0 & 0x03
            copy = ((b0 & 0x0C) << 6) + b3 + 5
            off = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1
        elif b0 < 0xFC:
            p += 1
            plain = ((b0 & 0x1F) << 2) + 4
            copy = 0; off = 0
        else:
            p += 1
            plain = b0 & 0x03
            copy = 0; off = 0
            out += data[p:p + plain]
            p += plain
            break
        out += data[p:p + plain]
        p += plain
        if copy:
            src = len(out) - off
            for i in range(copy):
                out.append(out[src + i])
    return bytes(out), ulen


class Save:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.raw = f.read()
        h = self.raw
        if h[:4] != b"DBPF":
            raise SystemExit("not DBPF: %s" % path)
        (self.vmaj, self.vmin) = struct.unpack_from("<II", h, 4)
        (self.imaj,) = struct.unpack_from("<I", h, 0x20)
        (self.count, self.idx_off, self.idx_size) = struct.unpack_from("<III", h, 0x24)
        (self.hole_count, self.hole_off, self.hole_size) = struct.unpack_from("<III", h, 0x30)
        (self.imin,) = struct.unpack_from("<I", h, 0x3C)
        stride = self.idx_size // self.count if self.count else 20
        self.stride = stride
        self.entries = []          # (T,G,I, off, size)
        blob = h[self.idx_off:self.idx_off + self.idx_size]
        for k in range(self.count):
            f = struct.unpack_from("<%dI" % (stride // 4), blob, k * stride)
            if stride == 20:
                t, g, i, off, sz = f
            elif stride == 24:
                t, g, i, _hi, off, sz = f
            else:
                raise SystemExit("odd index stride %d" % stride)
            self.entries.append((t, g, i, off, sz))
        # DIR: uncompressed sizes for compressed entries
        self.dir = {}
        for (t, g, i, off, sz) in self.entries:
            if t == DIR_TYPE:
                d = h[off:off + sz]
                rec = 16 if stride == 20 else 20
                for k in range(len(d) // rec):
                    f = struct.unpack_from("<%dI" % (rec // 4), d, k * rec)
                    if rec == 16:
                        self.dir[(f[0], f[1], f[2])] = f[3]
                    else:
                        self.dir[(f[0], f[1], f[2])] = f[4]

    def data(self, e):
        t, g, i, off, sz = e
        raw = self.raw[off:off + sz]
        if (t, g, i) in self.dir:
            try:
                out, ul = qfs_decompress(raw)
                return out
            except Exception as ex:
                return raw
        if len(raw) >= 6 and raw[4] == 0x10 and raw[5] == 0xFB:
            try:
                return qfs_decompress(raw)[0]
            except Exception:
                pass
        return raw

    def is_comp(self, e):
        return (e[0], e[1], e[2]) in self.dir


if __name__ == "__main__":
    s = Save(sys.argv[1])
    print("file      : %s" % s.path)
    print("dbpf ver  : %d.%d   index %d.%d  stride %d" % (s.vmaj, s.vmin, s.imaj, s.imin, s.stride))
    print("entries   : %d   index@0x%X size %d" % (s.count, s.idx_off, s.idx_size))
    print("DIR recs  : %d" % len(s.dir))
    by = collections.Counter()
    bysz = collections.Counter()
    for e in s.entries:
        by[e[0]] += 1
        bysz[e[0]] += e[4]
    print()
    print("%-12s %6s %12s   %s" % ("TYPE", "COUNT", "RAWBYTES", "sample G/I"))
    for t, c in sorted(by.items(), key=lambda kv: -kv[1]):
        samp = [e for e in s.entries if e[0] == t][:2]
        ss = " ".join("%08x/%08x" % (e[1], e[2]) for e in samp)
        print("0x%08X %6d %12d   %s" % (t, c, bysz[t], ss))
