#!/usr/bin/env python3
r"""Cross-reference finder for SimCity 4.exe.  READ-ONLY.

    python xrefs.py 0x4902E0            # who CALLs / JMPs here
    python xrefs.py 0x4902E0 --data     # also: who stores this dword (vtables etc.)
    python xrefs.py --imm 0x29F10000    # who pushes/moves this immediate

POSITIVE CONTROL (--imm): 0x29F10000 must be reported at 0x6D4A66
(the neighbour-connection arrow marker, per exe_instance_sweep.py).
"""
import argparse
import struct
import sys

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"


def load(path=EXE):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?")
    ap.add_argument("--imm")
    ap.add_argument("--data", action="store_true")
    a = ap.parse_args()

    data, base, secs = load()
    text = [s for s in secs if s[0] == ".text"][0]
    tname, tva, tvs, tra, trs = text
    blob = data[tra:tra + trs]
    tbase = base + tva

    if a.imm:
        want = int(a.imm, 0)
        pat = struct.pack("<I", want)
        i = blob.find(pat)
        hits = []
        while i != -1:
            op = blob[i - 1]
            va = tbase + i - 1
            kind = {0x68: "push imm32", 0xB8: "mov eax", 0xB9: "mov ecx",
                    0xBA: "mov edx", 0xBB: "mov ebx", 0xBD: "mov ebp",
                    0xBE: "mov esi", 0xBF: "mov edi", 0x3D: "cmp eax",
                    0x05: "add eax", 0x2D: "sub eax", 0xA1: "mov eax,[m]",
                    0xA3: "mov [m],eax"}.get(op)
            hits.append((va, kind, blob[max(0, i - 8):i + 4].hex()))
            i = blob.find(pat, i + 1)
        for va, kind, ctx in hits:
            print(f"  0x{va:08X}  {kind or '(mid-instr / modrm)':<16} ctx={ctx}")
        print(f"total {len(hits)}")
        # also non-.text sections
        for name, sva, vs, ra, rs in secs:
            if name == ".text":
                continue
            b2 = data[ra:ra + rs]
            j = b2.find(pat)
            c = 0
            while j != -1:
                print(f"  {name} 0x{base + sva + j:08X}  (data dword)")
                c += 1
                j = b2.find(pat, j + 1)
        return

    want = int(a.target, 0)
    print(f"== direct CALL/JMP rel32 to 0x{want:08X} ==")
    n = 0
    for i in range(len(blob) - 5):
        op = blob[i]
        if op in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            if tbase + i + 5 + rel == want:
                print(f"  0x{tbase + i:08X}  {'call' if op == 0xE8 else 'jmp'}")
                n += 1
    print(f"  total {n}")

    if a.data:
        pat = struct.pack("<I", want)
        print(f"== dword 0x{want:08X} stored in data sections ==")
        for name, sva, vs, ra, rs in secs:
            b2 = data[ra:ra + rs]
            j = b2.find(pat)
            while j != -1:
                print(f"  {name} 0x{base + sva + j:08X}")
                j = b2.find(pat, j + 1)


if __name__ == "__main__":
    main()
