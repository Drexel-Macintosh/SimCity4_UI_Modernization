#!/usr/bin/env python3
r"""Find every `SetMarkerModel(&key, a, b, scaleFloat)` call site: the pattern

    push <imm32 float>      68 xx xx xx xx
    push <imm8 or imm32>    6A xx  /  68 ...
    push <imm8 or imm32>    6A xx  /  68 ...
    push <imm32 dataAddr>   68 xx xx xx xx     <- &{T,G,I} in .data/.rdata
    ...                     (mov ecx, reg)
    call dword ptr [reg+0x58]                  FF 5x 58

and print the resource key it points at plus the float.  READ-ONLY.

POSITIVE CONTROL: 0x00524461 must be reported with key
{0x5AD0E817, 0xBADB57F1, 0x112A0000} and scale 5.0.

    python marker_setmodel.py
"""
import struct

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

    def off(va):
        for name, sva, vs, ra, rs in secs:
            if base + sva <= va < base + sva + max(vs, rs):
                return ra + (va - base - sva)
        return None

    def keyat(va):
        o = off(va)
        if o is None:
            return None
        t, g, i = struct.unpack_from("<III", data, o)
        return t, g, i

    hits = []
    i = 0
    while i < len(blob) - 24:
        if blob[i] != 0x68:
            i += 1
            continue
        fl = struct.unpack_from("<I", blob, i + 1)[0]
        fv = struct.unpack_from("<f", blob, i + 1)[0]
        # plausible positive scale float
        if not (0x38000000 <= fl <= 0x43000000):
            i += 1
            continue
        j = i + 5
        args = []
        for _ in range(2):
            if j < len(blob) and blob[j] == 0x6A:
                args.append(blob[j + 1])
                j += 2
            elif j < len(blob) and blob[j] == 0x68:
                args.append(struct.unpack_from("<I", blob, j + 1)[0])
                j += 5
            else:
                break
        if len(args) != 2 or j >= len(blob) or blob[j] != 0x68:
            i += 1
            continue
        addr = struct.unpack_from("<I", blob, j + 1)[0]
        k = keyat(addr)
        if not k or k[0] not in (0x5AD0E817, 0x29A5D1EC, 0x7AB50E44):
            i += 1
            continue
        # look ahead <=16 bytes for FF /2 disp8 == 0x58  (call [reg+0x58])
        tail = blob[j + 5:j + 5 + 20]
        slot = None
        for p in range(len(tail) - 2):
            if tail[p] == 0xFF and (tail[p + 1] & 0xF8) == 0x50:
                slot = tail[p + 2]
                break
        hits.append((tbase + j, tbase + i, k, fv, args, slot))
        i = j + 5

    for pushva, fva, k, fv, args, slot in hits:
        t, g, ins = k
        s = f"vt+0x{slot:02X}" if slot is not None else "vt+?"
        print(f"  push key @0x{pushva:08X}  {{T=0x{t:08X}, G=0x{g:08X}, "
              f"I=0x{ins:08X}}}  args={args}  scale={fv:g} (@0x{fva:08X})  "
              f"call {s}")
    print(f"total {len(hits)}")


if __name__ == "__main__":
    main()
