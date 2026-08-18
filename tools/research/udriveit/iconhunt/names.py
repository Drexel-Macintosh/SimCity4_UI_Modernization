#!/usr/bin/env python3
r"""names.py - NAME-FIRST sweep, independent of pixels.

(a) SimCity 4.exe: ASCII + UTF-16LE strings, reported with their VA via the
    PE section table (file offset -> RVA -> VA).
(b) every archive: exemplar names (property 0x00000020), LTEXT bodies, and a
    raw keyword byte-scan of EVERY decompressed payload -- text scanners are
    blind to binaries, so this scans raw AND NUL-stripped.
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "..", "..", "uimap", "emu"))

KEYS = ["udi", "udrive", "u-drive", "drive", "offer", "avail", "mission", "advice",
        "opportun", "reward", "dispatch", "hail", "taxi", "cab", "chopper", "heli",
        "bubble", "balloon", "callout", "call-out", "pin", "pip", "tag", "indicator",
        "alert", "notify", "notification", "marker", "beacon", "waypoint", "prize"]
RX = re.compile("|".join(re.escape(k) for k in KEYS), re.I)
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"


def pe_sections(data):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    t = pe + 24 + optsz
    secs = []
    for k in range(nsec):
        o = t + 40 * k
        nm = data[o:o+8].rstrip(b"\0").decode("ascii", "replace")
        vs, va, rs, ra = struct.unpack_from("<4I", data, o + 8)
        secs.append((nm, va, vs, ra, rs))
    return base, secs


def off2va(off, base, secs):
    for nm, va, vs, ra, rs in secs:
        if ra <= off < ra + rs:
            return base + va + (off - ra), nm
    return None, "?"


def exe_scan():
    data = open(EXE, "rb").read()
    base, secs = pe_sections(data)
    hits = []
    for m in re.finditer(rb"[\x20-\x7e]{4,200}", data):
        s = m.group().decode("ascii")
        if RX.search(s):
            va, sec = off2va(m.start(), base, secs)
            hits.append(("A", va, sec, s))
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){4,200}", data):
        s = m.group().decode("utf-16-le", "replace")
        if RX.search(s):
            va, sec = off2va(m.start(), base, secs)
            hits.append(("W", va, sec, s))
    return hits, len(data), base, secs


def archive_scan():
    import index_all
    from qfs_ab import qfs
    g = index_all.index()
    files = sorted(set(g["files"]))
    byfile = {}
    for (t, gg, i), (p, o, s) in g["by_tgi"].items():
        byfile.setdefault(p, []).append((t, gg, i, o, s))
    hits = []
    stat = dict(entries=0, scanned=0, fail=0)
    for p in files:
        try:
            fh = open(p, "rb")
        except Exception:
            continue
        with fh:
            for (t, gg, i, o, s) in byfile.get(p, []):
                stat["entries"] += 1
                if s > 4_000_000:
                    continue
                try:
                    fh.seek(o); raw = fh.read(s)
                    d = qfs(raw) or raw
                except Exception:
                    stat["fail"] += 1
                    continue
                stat["scanned"] += 1
                for variant in (d, d.replace(b"\x00", b"")):
                    for m in re.finditer(rb"[\x20-\x7e]{4,120}", variant):
                        ss = m.group().decode("ascii")
                        if RX.search(ss):
                            hits.append((os.path.basename(p), t, gg, i, ss))
                    break_after = True
                    if break_after:
                        # second variant only if first found nothing textual
                        if any(h[3] == i for h in hits[-40:]):
                            break
    return hits, stat


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "exe"
    if which == "exe":
        hits, n, base, secs = exe_scan()
        print("exe bytes: %d  imagebase %#x  sections: %s" % (n, base, [s[0] for s in secs]))
        print("keyword string hits: %d" % len(hits))
        seen = set()
        for enc, va, sec, s in hits:
            k = (enc, s)
            if k in seen: continue
            seen.add(k)
            print("%s VA=%s %-8s %s" % (enc, ("0x%08X" % va) if va else "  ?  ", sec, s.strip()))
    else:
        hits, stat = archive_scan()
        print("STAT", stat, "hits", len(hits))
        import collections
        c = collections.Counter()
        for (a, t, gg, i, s) in hits:
            c[(a, "%08X" % t, "%08X" % gg, "%08X" % i, s.strip()[:90])] += 1
        for k, v in c.most_common():
            print("%s T=%s G=%s I=%s | %s" % k)
