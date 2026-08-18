#!/usr/bin/env python3
r"""Disassemble SimCity 4.exe at a virtual address. Read-only.

    python disasm_at.py 0x7BE140 [count_bytes]
    python disasm_at.py 0x7BE140 256 --back 32

Written 2026-08-05 for the intro-video sizing hunt (the video draws 800x608
native on a 2400x1600 screen while the 512x384 EA-logo clip fills). There was
no general disassembler in tools\ - only task-specific emulators under
tools\uimap\emu\ - so this fills the gap for any future "what does the code at
VA X do" question.

⚠ The exe is LARGE_ADDRESS_AWARE-patched (2026-08-05); that flips ONE header
bit and does not move or alter any code, so addresses here still match every
note written before the patch.
"""
import argparse
import struct
import sys

import capstone

GAME_EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"


def load(path):
    data = open(path, "rb").read()
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


def va_to_off(va, base, secs):
    rva = va - base
    for name, sva, vs, ra, rs in secs:
        if sva <= rva < sva + max(vs, rs):
            return ra + (rva - sva)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("va")
    ap.add_argument("count", nargs="?", type=int, default=192)
    ap.add_argument("--back", type=int, default=0, help="start N bytes earlier")
    ap.add_argument("--exe", default=GAME_EXE)
    a = ap.parse_args()

    va = int(a.va, 0) - a.back
    data, base, secs = load(a.exe)
    off = va_to_off(va, base, secs)
    if off is None:
        sys.exit("VA 0x%X is not inside any section" % va)

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False
    blob = data[off:off + a.count]
    for ins in md.disasm(blob, va):
        print("  0x%08X  %-24s %s %s"
              % (ins.address,
                 " ".join("%02X" % b for b in ins.bytes)[:24],
                 ins.mnemonic, ins.op_str))


if __name__ == "__main__":
    main()
