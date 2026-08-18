#!/usr/bin/env python3
"""Scratch scanner for #188 static hunt. Read-only on the exe.
Modes:
  calls <target_va>     - list E8 rel32 call sites in .text targeting target_va
  dword <value>         - list VAs of a little-endian dword anywhere in the image
  dump <va> <n>         - hex-dump n dwords at va (for vtables in .rdata)
"""
import struct, sys

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

def off_to_va(off, base, secs):
    for name, sva, vs, ra, rs in secs:
        if ra <= off < ra + rs:
            return base + sva + (off - ra)
    return None

def main():
    data, base, secs = load(GAME_EXE)
    mode = sys.argv[1]
    if mode == "calls":
        target = int(sys.argv[2], 0)
        # scan .text only
        for name, sva, vs, ra, rs in secs:
            if name != ".text":
                continue
            end = ra + rs
            i = ra
            while True:
                i = data.find(b"\xE8", i, end)
                if i == -1:
                    break
                va = base + sva + (i - ra)
                rel = struct.unpack_from("<i", data, i + 1)[0]
                if (va + 5 + rel) & 0xFFFFFFFF == target:
                    print("call site 0x%08X (ret 0x%08X)" % (va, va + 5))
                i += 1
    elif mode == "dword":
        val = int(sys.argv[2], 0)
        pat = struct.pack("<I", val)
        i = 0
        while True:
            i = data.find(pat, i)
            if i == -1:
                break
            va = off_to_va(i, base, secs)
            print("0x%08X (file off 0x%X)" % (va if va else 0, i))
            i += 1
    elif mode == "dump":
        va = int(sys.argv[2], 0)
        n = int(sys.argv[3], 0)
        off = va_to_off(va, base, secs)
        for k in range(n):
            v = struct.unpack_from("<I", data, off + 4 * k)[0]
            print("0x%08X: 0x%08X" % (va + 4 * k, v))

if __name__ == "__main__":
    main()
