#!/usr/bin/env python3
r"""grepdat.py - byte-scan EVERY decompressed entry of EVERY discovered archive
for the given literals.  Scans the raw payload AND a NUL-stripped copy (text
scanners are blind to binaries; UTF-16 names would otherwise be invisible).
Prints the owning TGI + archive + a context window, and a scanned-count so a
zero result can be told apart from a refusal.
"""
import os, re, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "..", "..", "uimap", "emu"))
from qfs_ab import qfs
import index_all

pats = [p.encode() for p in sys.argv[1:]]
if not pats:
    sys.exit("usage: grepdat.py <literal> [...]")
rx = re.compile(b"|".join(re.escape(p) for p in pats), re.I)

g = index_all.index()
byfile = {}
for (t, gg, i), (p, o, s) in g["by_tgi"].items():
    byfile.setdefault(p, []).append((t, gg, i, o, s))

scanned = failed = hits = 0
for p in sorted(byfile):
    try:
        fh = open(p, "rb")
    except Exception:
        continue
    with fh:
        for (t, gg, i, o, s) in byfile[p]:
            if s > 8_000_000:
                continue
            try:
                fh.seek(o); raw = fh.read(s)
                d = qfs(raw) or raw
            except Exception:
                failed += 1
                continue
            scanned += 1
            for variant, lbl in ((d, "raw"), (d.replace(b"\x00", b""), "nul-stripped")):
                for m in rx.finditer(variant):
                    hits += 1
                    a = max(0, m.start() - 60); b = min(len(variant), m.end() + 90)
                    ctx = re.sub(rb"[^\x20-\x7e]", b".", variant[a:b]).decode()
                    print("%-42s T=%08X G=%08X I=%08X [%s] %s" %
                          (os.path.basename(p), t, gg, i, lbl, ctx))
                    if hits > 4000:
                        print("... capped"); sys.exit(0)
                if lbl == "raw" and rx.search(d):
                    break
print("SCANNED %d entries, %d unreadable, %d hits" % (scanned, failed, hits), file=sys.stderr)
