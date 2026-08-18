#!/usr/bin/env python3
"""LANE 4 part 4 - bound the function that SNAPSHOTS the arrow base, and find
who calls it. If the snapshot runs once at HUD build (before our scale pass)
the base is a stock 1x coordinate forever. If it re-runs after every rating
change it can also RATCHET, because the previous decline left the arrow at
base+(3-mag)*7.

POSITIVE CONTROL for the caller scan: 0x007E8510 (the rating updater) is
called from 0x007ED320 by a `call rel32` we have already disassembled. The
same scan is run for 0x7E8510 and MUST report 0x007ED320 among its callers;
if it does not, the scan is blind and its answer for the snapshot function is
worthless.
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    off = pe + 24 + opt
    for _ in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


def text_span(secs):
    for n, sva, vsize, roff, rsize in secs:
        if n == ".text":
            return IMAGE_BASE + sva, roff, rsize
    raise SystemExit("no .text")


def va2off(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def callers(data, secs, target):
    """Every `E8 rel32` whose destination == target."""
    sva, roff, rsize = text_span(secs)
    blob = data[roff:roff + rsize]
    out = []
    for i in range(len(blob) - 5):
        if blob[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", blob, i + 1)[0]
        site = sva + i
        if site + 5 + rel == target:
            out.append(site)
    return out


def func_start(data, secs, inside, back=0x600):
    """Walk back to the int3 padding that precedes the function."""
    o = va2off(secs, inside)
    blob = data[o - back:o]
    # last run of >=2 0xCC before `inside`
    for j in range(len(blob) - 2, 0, -1):
        if blob[j] == 0xCC and blob[j - 1] == 0xCC:
            k = j + 1
            while k < len(blob) and blob[k] == 0xCC:
                k += 1
            return inside - back + k
    return None


def dump(data, secs, start, end, label=""):
    o = va2off(secs, start)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    print("=" * 74)
    print(f"{label}  0x{start:08X}..0x{end:08X}")
    print("=" * 74)
    for i in md.disasm(data[o:o + (end - start) + 16], start):
        if i.address >= end:
            break
        print(f"0x{i.address:08X}  {i.bytes.hex(' ').upper():<26} {i.mnemonic} {i.op_str}")


if __name__ == "__main__":
    data, secs = load()

    print("### POSITIVE CONTROL: callers of the rating updater 0x007E8510 ###")
    c = callers(data, secs, 0x007E8510)
    print("  " + ", ".join(f"0x{a:08X}" for a in c))
    print(f"  contains the known caller 0x007ED320: {0x007ED320 in c}\n")

    fs = func_start(data, secs, 0x007ED2AD)
    print(f"### snapshot function start (int3-bounded): 0x{fs:08X} ###")
    print("### its callers ###")
    for a in callers(data, secs, fs):
        print(f"  0x{a:08X}")
    print()
    dump(data, secs, fs, 0x007ED2B0, "snapshot function head")
