#!/usr/bin/env python3
r"""Dump EVERY LTEXT (type 0x2026960B) in every DBPF the install ships, plus
Plugins, with TGI + decoded text.  READ-ONLY.

POSITIVE CONTROL: the dump MUST contain a known mayor-mode string.  If the
control is missing the scan is broken and every "no match" below is meaningless.

    python ltext_dump.py                 # write ltext-all.tsv + control
    python ltext_dump.py "drive|mission" # also grep
"""
import os, re, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from census_markers import dbpf_index, read_entry, qfs_decompress, discover_dbpf  # noqa
from sc4paths import plugins_dir, game_dir  # noqa

T_LTEXT = 0x2026960B

def decode_ltext(b):
    if len(b) < 4:
        return None
    # SC4 LTEXT: u16 charcount, u16 0x1000, UTF-16LE payload
    n, ctl = struct.unpack_from("<HH", b, 0)
    if ctl == 0x1000:
        s = b[4:4 + n * 2]
        try:
            return s.decode("utf-16-le", "replace")
        except Exception:
            pass
    # fallback: whole blob as utf-16
    try:
        return b.decode("utf-16-le", "replace")
    except Exception:
        return None

def main():
    roots = [game_dir()]
    p = plugins_dir(require=False)
    if p and os.path.isdir(p):
        roots.append(p)
    rows = []
    files = 0
    for root in roots:
        for path in discover_dbpf(root):
            idx = dbpf_index(path)
            if not idx:
                continue
            files += 1
            for (t, g, i, off, sz) in idx:
                if t != T_LTEXT:
                    continue
                raw = read_entry(path, off, sz)
                if len(raw) > 9 and (raw[4:6] == b"\x10\xfb" or raw[0:2] == b"\x10\xfb"):
                    try:
                        raw = qfs_decompress(raw)
                    except Exception:
                        pass
                s = decode_ltext(raw)
                if s is None:
                    continue
                rows.append((t, g, i, os.path.basename(path), s))
    out = os.path.join(HERE, "ltext-all.tsv")
    with open(out, "w", encoding="utf-8") as fh:
        for (t, g, i, f, s) in rows:
            fh.write("0x%08X\t0x%08X\t0x%08X\t%s\t%s\n"
                     % (t, g, i, f, s.replace("\t", " ").replace("\r", " ").replace("\n", "\n")))
    print("scanned %d DBPF files; %d LTEXT entries -> %s" % (files, len(rows), out))
    ctl = [r for r in rows if "Residential" in r[4] or "Mayor" in r[4]]
    print("POSITIVE CONTROL (LTEXT containing 'Residential' or 'Mayor'): %d hits" % len(ctl))
    for r in ctl[:3]:
        print("   {0x%08X,0x%08X,0x%08X} %s | %s" % (r[0], r[1], r[2], r[3], r[4][:70]))
    if len(sys.argv) > 1:
        pat = re.compile(sys.argv[1], re.I)
        print("\n--- grep %r ---" % sys.argv[1])
        n = 0
        for (t, g, i, f, s) in rows:
            if pat.search(s):
                n += 1
                print("{0x%08X,0x%08X,0x%08X} %-20s %s"
                      % (t, g, i, f, s.replace("\n", "\n")[:200]))
        print("%d matches" % n)

main()
