#!/usr/bin/env python3
"""W-Grid unit helper: read-only PE access + capstone disasm for SimCity 4.exe.

Written 2026-09-23 for the cIGZWinGrid mapping unit. Read-only; never writes the exe.
"""
import struct
import sys
import re

import capstone

GAME_EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

_data = open(GAME_EXE, "rb").read()
_pe = struct.unpack_from("<I", _data, 0x3C)[0]
_n = struct.unpack_from("<H", _data, _pe + 6)[0]
_opt = struct.unpack_from("<H", _data, _pe + 20)[0]
BASE = struct.unpack_from("<I", _data, _pe + 24 + 28)[0]
SECS = []
for i in range(_n):
    o = _pe + 24 + _opt + i * 40
    name = _data[o:o + 8].rstrip(b"\0").decode("latin1")
    vs, va, rs, ra = struct.unpack_from("<IIII", _data, o + 8)
    SECS.append((name, va, vs, ra, rs))
DATA = _data


def sec(name):
    for s in SECS:
        if s[0] == name:
            return s
    return None


def off(va):
    rva = va - BASE
    for name, sva, vs, ra, rs in SECS:
        if sva <= rva < sva + max(vs, rs):
            if rva - sva >= rs:
                return None
            return ra + (rva - sva)
    return None


def va_of_off(o):
    for name, sva, vs, ra, rs in SECS:
        if ra <= o < ra + rs:
            return BASE + sva + (o - ra)
    return None


def secname(va):
    rva = va - BASE
    for name, sva, vs, ra, rs in SECS:
        if sva <= rva < sva + max(vs, rs):
            return name
    return None


def is_text(va):
    return secname(va) == ".text"


def u32(va):
    o = off(va)
    return struct.unpack_from("<I", DATA, o)[0]


def u16(va):
    return struct.unpack_from("<H", DATA, off(va))[0]


def u8(va):
    return DATA[off(va)]


def rd(va, n):
    o = off(va)
    return DATA[o:o + n]


def cstr(va, maxlen=256):
    o = off(va)
    if o is None:
        return None
    e = DATA.find(b"\0", o, o + maxlen)
    if e < 0:
        return None
    return DATA[o:e].decode("latin1")


MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True


def dis(va, n=0x100):
    return list(MD.disasm(rd(va, n), va))


def func(va, maxbytes=0x4000, stop_at_ret=True):
    """Linear disasm from va until a ret followed by int3/nop padding or maxbytes."""
    out = []
    code = rd(va, maxbytes)
    for ins in MD.disasm(code, va):
        out.append(ins)
        if stop_at_ret and ins.mnemonic in ("ret", "retn"):
            # stop if next byte is padding (0xCC / 0x90) or we're clearly done
            nxt = ins.address + ins.size
            b = u8(nxt)
            if b in (0xCC, 0x90):
                break
            # otherwise heuristic: stop if no jump targets beyond here
            tgt_beyond = False
            for j in out:
                if j.mnemonic.startswith("j") and j.op_str.startswith("0x"):
                    try:
                        t = int(j.op_str, 16)
                    except ValueError:
                        continue
                    if t > ins.address:
                        tgt_beyond = True
                        break
            if not tgt_beyond:
                break
    return out


def pf(ins_list, file=sys.stdout):
    for i in ins_list:
        print("  %08X  %-24s %s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str), file=file)


def ret_n(va, maxbytes=0x4000):
    """Return the stack-pop count of the first ret reached linearly (-1 unknown)."""
    for ins in func(va, maxbytes):
        if ins.mnemonic in ("ret", "retn"):
            if ins.op_str:
                return int(ins.op_str, 0)
            return 0
    return -1


def find_bytes(pat, secname_=None):
    res = []
    for name, sva, vs, ra, rs in SECS:
        if secname_ and name != secname_:
            continue
        blob = DATA[ra:ra + rs]
        start = 0
        while True:
            i = blob.find(pat, start)
            if i < 0:
                break
            res.append(BASE + sva + i)
            start = i + 1
    return res


def find_u32(v, secname_=None):
    return find_bytes(struct.pack("<I", v), secname_)


def find_push_imm(v):
    """'push imm32' = 68 xx xx xx xx"""
    return find_bytes(b"\x68" + struct.pack("<I", v), ".text")


def xref_calls(target):
    """E8 rel32 direct calls to target."""
    s = sec(".text")
    name, sva, vs, ra, rs = s
    blob = DATA[ra:ra + rs]
    res = []
    for m in re.finditer(b"\xE8", blob):
        i = m.start()
        if i + 5 > len(blob):
            break
        rel = struct.unpack_from("<i", blob, i + 1)[0]
        src = BASE + sva + i
        if src + 5 + rel == target:
            res.append(src)
    return res


def xref_jmps(target):
    s = sec(".text")
    name, sva, vs, ra, rs = s
    blob = DATA[ra:ra + rs]
    res = []
    for m in re.finditer(b"\xE9", blob):
        i = m.start()
        if i + 5 > len(blob):
            break
        rel = struct.unpack_from("<i", blob, i + 1)[0]
        src = BASE + sva + i
        if src + 5 + rel == target:
            res.append(src)
    return res


def vtable(va, maxslots=400):
    """Read consecutive .text pointers starting at va."""
    out = []
    for k in range(maxslots):
        try:
            p = u32(va + 4 * k)
        except Exception:
            break
        if not is_text(p):
            break
        if k > 0 and find_u32_is_ref(va + 4 * k) and False:
            break
        out.append(p)
    return out


def find_u32_is_ref(va):
    return False


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("va")
    ap.add_argument("n", nargs="?", type=lambda x: int(x, 0), default=0x80)
    a = ap.parse_args()
    pf(dis(int(a.va, 0), a.n))
