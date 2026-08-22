#!/usr/bin/env python3
r"""Disassemble a VA range in SimCity 4.exe and annotate any immediate that
points at a printable C string (ASCII or UTF-16LE) in a data section.
READ-ONLY.

    python annot.py 0x53A410 2110
    python annot.py 0x53A410 --end 0x53AC4E
"""
import argparse, struct, sys
import capstone

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


def va_to_off(va, base, secs):
    rva = va - base
    for name, sva, vs, ra, rs in secs:
        if sva <= rva < sva + max(vs, rs):
            o = ra + (rva - sva)
            if o < ra + rs:
                return o, name
    return None, None


def cstr(data, base, secs, va, maxlen=96):
    off, sec = va_to_off(va, base, secs)
    if off is None:
        return None
    b = data[off:off + maxlen]
    # ascii
    end = b.find(b"\0")
    if end > 2:
        s = b[:end]
        if all(32 <= c < 127 for c in s):
            return '"%s"' % s.decode("latin1")
    # utf16
    if len(b) > 6 and b[1] == 0 and b[3] == 0 and 32 <= b[0] < 127:
        try:
            u = b.decode("utf-16-le", errors="ignore")
            u = u.split("\0")[0]
            if len(u) > 2 and all(32 <= ord(c) < 127 for c in u):
                return 'L"%s"' % u
        except Exception:
            pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("va")
    ap.add_argument("count", nargs="?", type=int, default=256)
    ap.add_argument("--end")
    a = ap.parse_args()
    data, base, secs = load()
    va = int(a.va, 0)
    n = (int(a.end, 0) - va) if a.end else a.count
    off, _ = va_to_off(va, base, secs)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    for ins in md.disasm(data[off:off + n], va):
        note = ""
        for op in ins.operands:
            if op.type == capstone.x86.X86_OP_IMM:
                s = cstr(data, base, secs, op.imm)
                if s:
                    note = "   ; " + s
            elif op.type == capstone.x86.X86_OP_MEM and op.mem.base == 0 and op.mem.disp:
                s = cstr(data, base, secs, op.mem.disp)
                if s:
                    note = "   ; " + s
        print("  0x%08X  %-22s %s %s%s"
              % (ins.address, " ".join("%02X" % b for b in ins.bytes)[:22],
                 ins.mnemonic, ins.op_str, note))


if __name__ == "__main__":
    main()
