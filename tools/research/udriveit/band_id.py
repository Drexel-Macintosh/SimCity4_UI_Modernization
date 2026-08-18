#!/usr/bin/env python3
r"""Identify a VA band of SimCity 4.exe: RTTI class names whose vtables point
into the band, plus every .rdata/.data string whose address is referenced from
inside the band.  READ-ONLY.

    python band_id.py 0x48C000 0x49A000
"""
import struct
import sys

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
        name = data[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, ra = struct.unpack_from("<IIII", data, o + 8)
        secs.append((name, va, vs, ra, rs))
    return data, base, secs


def main():
    lo = int(sys.argv[1], 0)
    hi = int(sys.argv[2], 0)
    data, base, secs = load()

    def off_of(va):
        for name, sva, vs, ra, rs in secs:
            if base + sva <= va < base + sva + max(vs, rs):
                return ra + (va - base - sva)
        return None

    # ---- RTTI: type descriptors -> COL -> vtable ----
    tds = {}
    for name, sva, vs, ra, rs in secs:
        blob = data[ra:ra + rs]
        for pat in (b".?AV", b".?AU"):
            i = blob.find(pat)
            while i != -1:
                end = blob.find(b"\0", i)
                if end != -1 and 0 < end - i < 200:
                    tds[base + sva + i - 8] = blob[i:end].decode("latin1")
                i = blob.find(pat, i + 1)

    cols = {}
    for name, sva, vs, ra, rs in secs:
        if name not in (".rdata", ".data"):
            continue
        blob = data[ra:ra + rs]
        for o in range(0, len(blob) - 20, 4):
            sig, offc, cd, ptd = struct.unpack_from("<IIII", blob, o)
            if sig == 0 and ptd in tds:
                cols[base + sva + o] = tds[ptd]

    # vtable VA -> class : dword at V-4 is a COL address
    vt = {}
    for name, sva, vs, ra, rs in secs:
        if name not in (".rdata", ".data"):
            continue
        blob = data[ra:ra + rs]
        for o in range(0, len(blob) - 4, 4):
            v = struct.unpack_from("<I", blob, o)[0]
            if v in cols:
                vt[base + sva + o + 4] = cols[v]

    print(f"== RTTI classes with a vtable slot pointing into "
          f"0x{lo:X}..0x{hi:X} ==")
    hits = {}
    for vva, cls in vt.items():
        o = off_of(vva)
        if o is None:
            continue
        for slot in range(0, 120):
            fn = struct.unpack_from("<I", data, o + slot * 4)[0]
            if not (base <= fn < base + 0x1000000):
                break
            if lo <= fn < hi:
                hits.setdefault(cls, []).append((vva, slot, fn))
    for cls in sorted(hits):
        sl = hits[cls]
        print(f"  {cls}")
        for vva, slot, fn in sl[:14]:
            print(f"      vtable 0x{vva:08X} slot {slot:3d} -> 0x{fn:08X}")
        if len(sl) > 14:
            print(f"      ... {len(sl) - 14} more")
    if not hits:
        print("  (none)")

    # ---- strings referenced from the band ----
    print(f"\n== strings referenced from inside 0x{lo:X}..0x{hi:X} ==")
    tn, tva, tvs, tra, trs = [s for s in secs if s[0] == ".text"][0]
    tbase = base + tva
    seen = set()
    for o in range(lo - tbase, hi - tbase - 4):
        v = struct.unpack_from("<I", data, tra + o)[0]
        so = off_of(v)
        if so is None:
            continue
        # only .rdata/.data
        ok = False
        for name, sva, vs, ra, rs in secs:
            if name in (".rdata", ".data") and \
               base + sva <= v < base + sva + max(vs, rs):
                ok = True
        if not ok:
            continue
        chunk = data[so:so + 96]
        end = chunk.find(b"\0")
        if end < 4:
            continue
        s = chunk[:end]
        if all(0x20 <= c < 0x7F for c in s) and len(s) >= 5:
            key = (v, s)
            if key in seen:
                continue
            seen.add(key)
            print(f"  ref@0x{tbase + o - 1:08X} -> 0x{v:08X}  "
                  f"{s.decode('latin1')!r}")


if __name__ == "__main__":
    main()
