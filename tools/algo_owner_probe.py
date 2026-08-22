#!/usr/bin/env python3
"""Who owns 0x007A2740 / 0x0079ED90, and what args reach ROWFILL.

Read-only.
"""
import sys, struct, os, re
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
MD.detail = False


def dis(data, secs, va, count=200):
    o = va2off(secs, va)
    if o is None:
        return []
    return list(MD.disasm(data[o:o+count*10], va, count))


def func_start(data, secs, va, back=0x600):
    """Scan backwards for a plausible prologue right after a ret/int3 pad."""
    o = va2off(secs, va)
    blob = data[o-back:o+1]
    # find last 0xCC 0xCC pad or ret followed by alignment
    best = None
    for i in range(len(blob) - 4):
        # sub esp, imm8/32  (83 EC xx / 81 EC xx xx xx xx) or push ebp;mov ebp,esp
        if blob[i] == 0x83 and blob[i+1] == 0xEC:
            best = va - back + i
        elif blob[i] == 0x81 and blob[i+1] == 0xEC:
            best = va - back + i
        elif blob[i] == 0x55 and blob[i+1] == 0x8B and blob[i+2] == 0xEC:
            best = va - back + i
    return best


def callers_of(data, secs, target):
    hits = []
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff+rsize]
        for i in range(len(blob) - 5):
            if blob[i] != 0xE8:
                continue
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            site = base + i
            if site + 5 + rel == target:
                hits.append(site)
    return hits


def dword_refs(data, secs, value):
    needle = struct.pack("<I", value & 0xFFFFFFFF)
    out = []
    for n, sva, vsize, roff, rsize in secs:
        blob = data[roff:roff+rsize]
        s = 0
        while True:
            i = blob.find(needle, s)
            if i < 0:
                break
            out.append((n, IMAGE_BASE + sva + i))
            s = i + 1
    return out


def show(data, secs, va, n, title):
    print("=" * 78)
    print(title)
    print("=" * 78)
    for ins in dis(data, secs, va, n):
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
    print()


def main():
    data, secs = load()

    # 1. The function containing the ROWFILL call site 0x7a2628
    print("### function-start guess for the site 0x7a2628:",
          hex(func_start(data, secs, 0x7A2628) or 0))
    show(data, secs, 0x7A2560, 130, "0x007A2560.. (contains the ROWFILL call at 0x7a2628)")

    # 2. Who calls the function that contains 0x7a2628?
    #    Find its entry by scanning for a ret before it.
    # 3. vtable slots holding these VAs
    print("=" * 78)
    print("DWORD REFERENCES (vtable slots / data) to the chain functions")
    print("=" * 78)
    for nm, va in (("ROWFILL 0x0079ED90", 0x0079ED90),
                   ("MID     0x007A2380", 0x007A2380),
                   ("TOP     0x007A2740", 0x007A2740),
                   ("callee  0x0079F230", 0x0079F230),
                   ("resize  0x007A1310", 0x007A1310),
                   ("0x007A00B0", 0x007A00B0),
                   ("0x0079EFD0", 0x0079EFD0),
                   ("0x0079EB40", 0x0079EB40)):
        refs = dword_refs(data, secs, va)
        print(f"{nm}: {len(refs)} -> " + ", ".join(f"{s}:{hex(v)}" for s, v in refs[:10]))
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
