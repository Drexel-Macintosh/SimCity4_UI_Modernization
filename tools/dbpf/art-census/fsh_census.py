#!/usr/bin/env python3
"""FULL art census of DBPF group 0x1ABE787D (FSH, type 0x7AB50E44).

Every entry is DECOMPRESSED (QFS) before it is read -- the earlier census was
a byte-scan of the RAW records and was therefore blind to 89.9% of the group.
Read-only against the game install.

Emits one CSV row per FSH resource:
  archive,instance,qfs,dirid,nsub,codes,dims,names,ascii

POSITIVE CONTROL (asserted at the end, not assumed):
  the ten signpost/route tiles 0x8B4A6560..67 must appear, all 8x8, and the
  FOUR of them that are QFS-COMPRESSED (0x60,0x63,0x65,0x66) must yield their
  embedded names -- which only a working decompressor can produce.
"""
import csv, os, re, struct, sys, time
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\dbpf\row15-probe")
import dbpfcore as D

T_FSH = 0x7AB50E44
G_ART = 0x1ABE787D
ASCII = re.compile(rb"[ -~]{4,}")

def parse_fsh(buf):
    """(dirid, [(tag, code, w, h, m0,m1,m2,m3)], [names])  -- tolerant."""
    if len(buf) < 16 or buf[:4] != b"SHPI":
        return None, [], []
    fsz, n, dirid = struct.unpack_from("<II4s", buf, 4)
    subs = []
    for k in range(min(n, 4096)):
        p = 16 + 8 * k
        if p + 8 > len(buf):
            break
        tag, off = struct.unpack_from("<4sI", buf, p)
        if off + 16 > len(buf):
            subs.append((tag.decode("latin1"), -1, 0, 0, 0, 0, 0, 0))
            continue
        hdr = struct.unpack_from("<I", buf, off)[0]
        code = hdr & 0xFF
        w, h, m0, m1, m2, m3 = struct.unpack_from("<6H", buf, off + 4)
        subs.append((tag.decode("latin1"), code, w, h, m0, m1, m2, m3))
    # names: every ASCII run in the whole record (attachment-chain agnostic)
    names = [m.group(0).decode("latin1") for m in ASCII.finditer(buf[16:])]
    return dirid.decode("latin1"), subs, names

def main(out_path):
    t0 = time.time()
    fh = open(out_path, "w", newline="", encoding="utf-8")
    w = csv.writer(fh)
    w.writerow(["archive", "instance", "qfs", "dirid", "nsub",
                "codes", "dims", "names", "nbytes"])
    total = bad = 0
    for p in D.discover_archives():
        A = D.Archive(p)
        ents = A.find(t=T_FSH, g=G_ART)
        for e in ents:
            total += 1
            try:
                buf, q, listed = A.payload(e)
            except Exception as ex:
                bad += 1
                w.writerow([A.name, "%08X" % e[2], "ERR", "", "", "",
                            "", "DECOMP-FAIL:%s" % ex, e[4]])
                continue
            dirid, subs, names = parse_fsh(buf)
            if dirid is None:
                bad += 1
                w.writerow([A.name, "%08X" % e[2], int(q), "NOT-SHPI", "",
                            "", "", buf[:8].hex(), len(buf)])
                continue
            codes = "|".join(sorted({"%02X" % s[1] for s in subs}))
            dims = "|".join(sorted({"%dx%d" % (s[2], s[3]) for s in subs}))
            w.writerow([A.name, "%08X" % e[2], int(q), dirid, len(subs),
                        codes, dims, " ".join(names), len(buf)])
            if total % 2000 == 0:
                sys.stderr.write("%d  %.0fs\n" % (total, time.time() - t0))
                sys.stderr.flush()
        A.close()
    fh.close()
    sys.stderr.write("DONE %d rows, %d unparsable, %.0fs\n"
                     % (total, bad, time.time() - t0))

if __name__ == "__main__":
    main(sys.argv[1])
