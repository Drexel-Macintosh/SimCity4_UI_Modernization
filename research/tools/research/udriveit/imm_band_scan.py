#!/usr/bin/env python3
r"""Scan a VA band of SimCity 4.exe for hard-coded 32-bit immediates that look
like marker-family exemplar instance ids (low 16 bits == 0) or like known
resource TYPE ids.  READ-ONLY.

    python imm_band_scan.py 0x48C000 0x49A000

POSITIVE CONTROL: run it over 0x6D4800..0x6D4C00 and 0x29F10000 must appear
(the neighbour-connection arrow marker, pushed at 0x6D4A66).
"""
import struct
import sys

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

KNOWN_TYPES = {
    0x5AD0E817: "S3D model",
    0x29A5D1EC: "type 0x29A5D1EC (2nd model-ish type accepted by 0x7FEDE0)",
    0x6534284A: "marker/prop EXEMPLAR type",
    0x7AB50E44: "FSH texture",
    0xBADB57F1: "S3D group (marker models)",
    0xC977C536: "marker/prop exemplar group",
    0x856DDBAC: "PNG type",
}


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


OPS = {0x68: "push", 0xB8: "mov eax", 0xB9: "mov ecx", 0xBA: "mov edx",
       0xBB: "mov ebx", 0xBD: "mov ebp", 0xBE: "mov esi", 0xBF: "mov edi",
       0x3D: "cmp eax", 0x05: "add eax", 0x2D: "sub eax", 0x25: "and eax",
       0x0D: "or eax", 0x35: "xor eax", 0xA9: "test eax"}


def main():
    lo = int(sys.argv[1], 0)
    hi = int(sys.argv[2], 0)
    data, base, secs = load()
    tn, tva, tvs, tra, trs = [s for s in secs if s[0] == ".text"][0]
    tbase = base + tva
    blob = data[tra:tra + trs]

    seen = []
    for off in range(lo - tbase, hi - tbase):
        op = blob[off]
        if op not in OPS:
            continue
        # C7 44 24 xx imm32  (mov dword ptr [esp+d8], imm32) handled separately
        val = struct.unpack_from("<I", blob, off + 1)[0]
        va = tbase + off
        why = None
        if val in KNOWN_TYPES:
            why = KNOWN_TYPES[val]
        elif (val & 0xFFFF) == 0 and 0x00010000 <= val <= 0xFFFF0000:
            why = "family instance? (low16 == 0)"
        if why:
            seen.append((va, OPS[op], val, why))

    # also C7 05 / C7 44 24 / C7 45 forms:  mov dword ptr [...], imm32
    for off in range(lo - tbase, hi - tbase):
        if blob[off] != 0xC7:
            continue
        modrm = blob[off + 1]
        # only the common [esp+disp8] and [ebp+disp8] and [reg] forms
        for immoff in (4, 3, 2, 7):
            if off + immoff + 4 > len(blob):
                continue
            val = struct.unpack_from("<I", blob, off + immoff)[0]
            if val in KNOWN_TYPES:
                seen.append((tbase + off, f"mov m32 (modrm {modrm:02X})",
                             val, KNOWN_TYPES[val]))
                break

    seen.sort()
    for va, kind, val, why in seen:
        print(f"  0x{va:08X}  {kind:<22} 0x{val:08X}   {why}")
    print(f"total {len(seen)} in 0x{lo:X}..0x{hi:X}")


if __name__ == "__main__":
    main()
