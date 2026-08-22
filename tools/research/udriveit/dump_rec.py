#!/usr/bin/env python3
"""Dump records of one CLSID from a save: hex + u32/float decode."""
import sys, struct
from save_records import scan
from clsid_table import TABLE

path, cid = sys.argv[1], int(sys.argv[2], 0)
lim = int(sys.argv[3]) if len(sys.argv) > 3 else 4
s, rows = scan(path)
for t, g, i, recs, ul, rl, d in rows:
    if t != cid:
        continue
    print("CLSID 0x%08X %s  group=%08x inst=%08x  %d bytes uncompressed, %s records"
          % (t, TABLE.get(t, "<UNNAMED>"), g, i, ul, len(recs) if recs else "n/a"))
    if recs is None:
        print(d[:512].hex())
        break
    for ri, (ro, rs, crc, mem, vmaj, vmin) in enumerate(recs[:lim]):
        b = d[ro:ro + rs]
        print("\n--- record #%d  off 0x%X  size %d  crc %08X  mem %08X  ver %d.%d ---"
              % (ri, ro, rs, crc, mem, vmaj, vmin))
        for k in range(0, len(b), 16):
            chunk = b[k:k + 16]
            hexs = " ".join("%02x" % c for c in chunk)
            asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
            ws = ""
            if k + 16 <= len(b):
                u = struct.unpack_from("<4I", b, k)
                f = struct.unpack_from("<4f", b, k)
                ws = " | " + " ".join("%10d" % x if x < 1 << 31 else "%#010x" % x for x in u)
                ws += " | " + " ".join(("%9.3f" % x if -1e9 < x < 1e9 else "  ------") for x in f)
            print("  %04X  %-47s |%s|%s" % (k, hexs, asc, ws))
    break
