#!/usr/bin/env python3
"""What happens to the freshly-created cIGZBuffer after the painters run
(the common exit 0x7a45f6), and the 77-case painter table.

Read-only.
"""
import sys, struct
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
    for i in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


def va2off(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


MD = Cs(CS_ARCH_X86, CS_MODE_32)


def show(data, secs, lo, nbytes, title):
    print("=" * 78)
    print(title)
    print("=" * 78)
    o = va2off(secs, lo)
    for ins in MD.disasm(data[o:o + nbytes], lo):
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
    print()


def main():
    data, secs = load()
    show(data, secs, 0x007A45F6, 0x140, "common exit 0x007A45F6 (what happens to the buffer)")
    show(data, secs, 0x007A484B, 0x60, "0x007A484B / 0x7A4864 / 0x7A487C early-outs")

    # painter jump table at 0x7a4884, byte index table at 0x7a48d0
    o = va2off(secs, 0x007A4884)
    tbl = [struct.unpack_from("<I", data, o + 4*i)[0] for i in range(20)]
    print("### painter jump table 0x7a4884 (first 20)")
    for i, v in enumerate(tbl):
        print(f"   [{i:2}] {hex(v)}")
    o2 = va2off(secs, 0x007A48D0)
    idx = list(data[o2:o2+0x4D])
    print("\n### byte index table 0x7a48d0 (dataview type 0..0x4C -> case)")
    print("   ", idx)
    print()

    # buffer-size arithmetic check
    for W in (256, 384, 512, 768, 1024):
        for dim in (64, 128, 256):
            m, e = 1, W
            while e > dim:
                e >>= 1
                m <<= 1
            painted = dim * m
            print(f"  W={W:5} dim={dim:4} -> reduced={e:4} MULT={m:3} painted={painted:5} "
                  f"{'OK  ' if painted <= W else 'OVER'} (exact={painted == W})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
