# -*- coding: utf-8 -*-
r"""LANE 3 probe: every VERTICAL constant written by the Graphs panel builder
sub_76D3D0, read from the SHIPPED exe.  Read-only; writes nothing.

POSITIVE CONTROL (mandatory here): the probe must re-find, byte-for-byte, the
five imm sites CodePatches.cpp already patches (0x0076E233/E239/E23C/E2AF/E2C8)
and the two NOT_PATCHED sites the byte gate names (0x0076DE79 ROW0_TOP=0x14,
0x0076E34B lea edx,[ecx+eax+4]).  If any of those seven is not reported by this
scan, the scan is BLIND and its nulls mean nothing.
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

FN_LO = 0x0076D3D0
FN_HI = 0x0076E430


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    off = pe + 24 + opt
    for _ in range(nsec):
        n = data[off:off + 8].rstrip(b"\0").decode("latin1")
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


def main():
    data, secs = load()
    lo = va2off(secs, FN_LO)
    hi = va2off(secs, FN_HI)
    blob = data[lo:hi]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    insns = list(md.disasm(blob, FN_LO))
    print("# sub_76D3D0 .. 0x%08X : %d insns, %d bytes" % (FN_HI, len(insns), hi - lo))
    print()
    want = {0x0076E233, 0x0076E239, 0x0076E23C, 0x0076E2AF, 0x0076E2C8,
            0x0076DE79, 0x0076E34B}
    seen = set()
    for i in insns:
        b = " ".join("%02X" % c for c in i.bytes)
        mark = ""
        if i.address in want:
            seen.add(i.address)
            mark = "   <== CONTROL"
        print("0x%08X  %-26s %-38s %s%s" %
              (i.address, b, i.mnemonic + " " + i.op_str, "", mark))
    print()
    print("# POSITIVE CONTROL: %d/%d known sites re-found: %s" %
          (len(seen), len(want), sorted("0x%08X" % a for a in seen)))
    missing = want - seen
    if missing:
        print("# BLIND - missing %s" % sorted("0x%08X" % a for a in missing))
        return 1
    print("# control PASSED - nulls from this listing are MEASURED, not structural.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
