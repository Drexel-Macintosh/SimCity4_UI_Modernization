#!/usr/bin/env python3
"""LANE 4 part 2 - WHO writes the cached arrow base [obj+0x378]/[obj+0x37C]?

The decline arrow is positioned by
    GZWinMoveTo( [obj+0x378] + (3-mag)*7 , [obj+0x37C] )
at 0x007E89EC..0x007E8A0A. If that base is snapshotted from a STOCK (unscaled)
rect, the arrow lands at a stock origin while everything around it is scaled.

POSITIVE CONTROL for the scan: the two READS we already saw disassembled
(0x007E8829 `mov ecx,[ebp+0x37C]` = 8B 8D 7C 03 00 00, and 0x007E89F2
`mov edi,[ebp+0x378]` = 8B BD 78 03 00 00) MUST appear in the scan output as
reads. If the scan cannot even find those, it cannot find a store either and
its "no store" answer would be a structural null.
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
TARGETS = (0x378, 0x37C, 0x36C)


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


def main():
    data, secs = load()
    text = [s for s in secs if s[0] == ".text"][0]
    _, sva, vsize, roff, rsize = text
    start_va = IMAGE_BASE + sva
    blob = data[roff:roff + rsize]

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    hits = []
    # linear sweep from many alignments is unnecessary: sweep once from the
    # section start, then again from every +1..+15 offset would explode.
    # Instead: byte-pattern prefilter on the 32-bit displacement, then decode
    # a window around each candidate to get a real instruction boundary.
    for disp in TARGETS:
        pat = struct.pack("<I", disp)
        i = 0
        while True:
            i = blob.find(pat, i + 1)
            if i < 0:
                break
            # try decoding starting up to 8 bytes before the displacement
            for back in range(2, 12):
                s = i - back
                if s < 0:
                    continue
                for ins in md.disasm(blob[s:s + 16], start_va + s, 1):
                    if ins.size != back + 4:
                        continue
                    txt = f"0x{ins.address:08X}  {ins.bytes.hex(' ').upper():<26} {ins.mnemonic} {ins.op_str}"
                    if f"0x{disp:x}" in ins.op_str:
                        kind = "STORE" if (ins.mnemonic.startswith("mov") and
                                           ins.op_str.startswith("dword ptr [")) else "read/other"
                        hits.append((disp, ins.address, kind, txt))
                    break

    seen = set()
    for disp, addr, kind, txt in sorted(hits, key=lambda h: (h[0], h[1])):
        k = (disp, addr)
        if k in seen:
            continue
        seen.add(k)
        print(f"[+0x{disp:03X}] {kind:<10} {txt}")

    print()
    print("### POSITIVE CONTROL ###")
    ctrl = {0x007E8829, 0x007E89F2, 0x007E885E}
    found = {a for _, a, _, _ in hits}
    for c in sorted(ctrl):
        print(f"  known access 0x{c:08X} present: {c in found}")


if __name__ == "__main__":
    main()
