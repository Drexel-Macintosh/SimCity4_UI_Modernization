#!/usr/bin/env python3
r"""Enumerate every `push imm8 ; push <familyInstance>` marker-spawn site in
SimCity 4.exe, plus every bare `push <familyInstance>`.  READ-ONLY.

A family instance = low 16 bits zero (the marker/prop exemplar convention,
e.g. Zot_NoPower 0x0FD10000, ConnectArrow 0x29F10000).

POSITIVE CONTROLS that MUST appear:
    0x0FD10000 (Zot_NoPower)  at 0x6CADAA with kind 4
    0x107A0000 (Zot_NoCar)    at 0x6CB195 with kind 6
    0x1C430000 (Zot_NoWater)  at 0x6CAF3E with kind 5
    0x1C440000 (Zot_NoWork)   at 0x6CB1C6 with kind 7
    0x29F10000 (ConnectArrow) at 0x6D4A66 (bare push)
"""
import os
import struct
import sys

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
HERE = os.path.dirname(os.path.abspath(__file__))


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


def load_names():
    """instance -> exemplar name, from the prior census artifact."""
    names = {}
    p = os.path.join(HERE, "marker-exemplars.txt")
    if not os.path.exists(p):
        return names
    for line in open(p, encoding="utf-8", errors="replace"):
        parts = line.split()
        if len(parts) >= 4 and len(parts[0]) == 8 and len(parts[1]) == 8:
            try:
                g = int(parts[0], 16)
                i = int(parts[1], 16)
            except ValueError:
                continue
            names.setdefault(i, (g, parts[-1]))
    return names


def main():
    data, base, secs = load()
    tn, tva, tvs, tra, trs = [s for s in secs if s[0] == ".text"][0]
    blob = data[tra:tra + trs]
    tbase = base + tva
    names = load_names()

    def fam(v):
        return (v & 0xFFFF) == 0 and 0x00010000 <= v <= 0xFFFF0000

    kinded = []
    bare = []
    i = 0
    while i < len(blob) - 8:
        if blob[i] == 0x6A and blob[i + 2] == 0x68:
            v = struct.unpack_from("<I", blob, i + 3)[0]
            if fam(v):
                kinded.append((tbase + i, blob[i + 1], v))
                i += 7
                continue
        if blob[i] == 0x68:
            v = struct.unpack_from("<I", blob, i + 1)[0]
            if fam(v):
                bare.append((tbase + i, v))
                i += 5
                continue
        i += 1

    print("== push <kind:imm8> ; push <familyInstance> ==")
    for va, kind, v in kinded:
        g, nm = names.get(v, (None, "?"))
        gs = f"G=0x{g:08X} " if g else ""
        print(f"  0x{va:08X}  kind={kind:<3} inst=0x{v:08X}  {gs}{nm}")
    print(f"  total {len(kinded)}")

    print("\n== bare push <familyInstance> ==")
    for va, v in bare:
        g, nm = names.get(v, (None, "?"))
        gs = f"G=0x{g:08X} " if g else ""
        print(f"  0x{va:08X}  inst=0x{v:08X}  {gs}{nm}")
    print(f"  total {len(bare)}")


if __name__ == "__main__":
    main()
