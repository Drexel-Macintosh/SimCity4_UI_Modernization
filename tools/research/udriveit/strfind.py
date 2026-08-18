#!/usr/bin/env python3
r"""Find ASCII/UTF-16 strings in SimCity 4.exe matching a regex; print VA. READ-ONLY.
    python strfind.py "udrive|mission" [-i]
"""
import re, struct, sys
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    n = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    secs = []
    for i in range(n):
        o = pe + 24 + opt + i * 40
        name = data[o:o+8].rstrip(b"\0").decode("latin1")
        vs, va, rs, ra = struct.unpack_from("<IIII", data, o + 8)
        secs.append((name, va, vs, ra, rs))
    return data, base, secs

def off_to_va(off, base, secs):
    for name, sva, vs, ra, rs in secs:
        if ra <= off < ra + rs:
            return base + sva + (off - ra), name
    return 0, "?"

def main():
    pat = re.compile(sys.argv[1].encode("latin1"), re.I)
    data, base, secs = load()
    seen = set()
    # ascii runs
    for m in re.finditer(rb"[\x20-\x7e]{4,200}", data):
        if pat.search(m.group()):
            va, sec = off_to_va(m.start(), base, secs)
            key = (va, m.group())
            if key in seen: continue
            seen.add(key)
            print("A VA 0x%08X [%-7s] %s" % (va, sec, m.group().decode("latin1")))
    # utf16
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){4,200}", data):
        s = m.group().decode("utf-16-le")
        if pat.search(s.encode("latin1", "ignore")):
            va, sec = off_to_va(m.start(), base, secs)
            print("W VA 0x%08X [%-7s] %s" % (va, sec, s))

main()
