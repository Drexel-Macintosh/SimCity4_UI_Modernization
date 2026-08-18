#!/usr/bin/env python3
r"""Find the enclosing function start for a VA in SimCity 4.exe (READ-ONLY).

A function start = the first byte after a run of >=2 0xCC padding bytes at or
before the VA.  Also reports the next 0xCC run (the function end).

    python fnstart.py 0x490E59 [0x495521 ...]
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
    data, base, secs = load()
    tn, tva, tvs, tra, trs = [s for s in secs if s[0] == ".text"][0]
    blob = data[tra:tra + trs]
    tbase = base + tva
    for arg in sys.argv[1:]:
        va = int(arg, 0)
        off = va - tbase
        i = off
        while i > 1:
            if blob[i - 1] == 0xCC and blob[i - 2] == 0xCC:
                break
            i -= 1
        start = tbase + i
        j = off
        while j < len(blob) - 2:
            if blob[j] == 0xCC and blob[j + 1] == 0xCC:
                break
            j += 1
        print(f"0x{va:08X}  ->  fn start 0x{start:08X}  end ~0x{tbase + j:08X}"
              f"  (size {j - i} bytes)")


if __name__ == "__main__":
    main()
