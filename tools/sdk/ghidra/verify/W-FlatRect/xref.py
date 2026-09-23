"""Find every occurrence of a 32-bit little-endian value inside .text and
report the instruction that contains it (READ ONLY, offline).
usage: python xref.py <hex> [<hex> ...]
Positive control: `python xref.py C2AFA76F` must list 0x47B993 and 0x4861D7
(the two GetChildAs(id, IID_cIGZWinFlatRect, &p) sites) plus the QI compare
at 0x9CD1D2."""
import sys, struct
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from pe import *

TXT_LO, TXT_HI = TEXT[1], TEXT[2]
_text = bytes(rd(TXT_LO, TXT_HI - TXT_LO))


def containing_insn(hit_va):
    """Try start offsets 1..10 bytes back; accept an instruction that spans hit_va..hit_va+4."""
    best = None
    for back in range(1, 11):
        st = hit_va - back
        code = rd(st, 16)
        ins = next(md.disasm(code, st), None)
        if ins and ins.address + ins.size >= hit_va + 4 and ins.address < hit_va:
            best = ins
            break
    return best


def find(val):
    pat = struct.pack("<I", val)
    out = []
    i = _text.find(pat)
    while i >= 0:
        va = TXT_LO + i
        ins = containing_insn(va)
        out.append((va, ins))
        i = _text.find(pat, i + 1)
    return out


if __name__ == "__main__":
    for a in sys.argv[1:]:
        v = int(a, 16)
        hits = find(v)
        print(f"== {v:#010x}: {len(hits)} hit(s) in .text")
        for va, ins in hits:
            if ins:
                print(f"   {ins.address:08X}: {ins.mnemonic} {ins.op_str}")
            else:
                print(f"   {va:08X}: (no decodable containing insn)")
