#!/usr/bin/env python
"""Read (OFFLINE) the cIGZWin vtable of cSC4WinAlertBorder at 0x00AB5B48 in
SimCity 4.exe 1.1.641 and disassemble the slots of every OVERLOAD GROUP in the
vendored cIGZWin.h, so each overload's real Windows slot can be told apart by
its own code (callee stack cleanup 'ret N' = 4 * arg count for __thiscall, and
what it does with the args).

Positive controls (established 2026-09-23): slot 48 GetArea() returns a
pointer (no args, ret 0); 53 SetSize(w,h) ret 8; 54 SetArea(rect) ret 4;
55 SetArea(l,t,r,b) ret 0x10; 118 SetSize(pt) ret 4; 120 null-tests its arg.
"""
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
VT = 0x00AB5B48
SLOTS = [19, 20, 25, 26, 47, 48, 49, 50, 53, 54, 55, 102, 103, 104, 105, 106, 107,
         118, 119, 120, 144, 145, 146, 147]

data = open(EXE, "rb").read()
pe = struct.unpack_from("<I", data, 0x3C)[0]
nsec = struct.unpack_from("<H", data, pe + 6)[0]
optsz = struct.unpack_from("<H", data, pe + 20)[0]
base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + optsz + 40 * i
    va, vs, raw, rs = struct.unpack_from("<IIII", data, o + 8)[0:4] if False else (
        struct.unpack_from("<I", data, o + 12)[0], struct.unpack_from("<I", data, o + 8)[0],
        struct.unpack_from("<I", data, o + 20)[0], struct.unpack_from("<I", data, o + 16)[0])
    secs.append((base + va, max(vs, rs), raw))


def off(va):
    for sva, sz, raw in secs:
        if sva <= va < sva + sz:
            return raw + (va - sva)
    raise ValueError(hex(va))


md = Cs(CS_ARCH_X86, CS_MODE_32)
print(f"size {len(data)} imagebase {base:#x}")


def dis(va, n=40, depth=0):
    out = []
    code = data[off(va):off(va) + 0x200]
    for ins in md.disasm(code, va):
        out.append(f"      {ins.address:08x}  {ins.mnemonic} {ins.op_str}")
        if ins.mnemonic in ("ret", "retn") or (ins.mnemonic == "jmp" and depth >= 1):
            break
        if ins.mnemonic == "jmp" and ins.op_str.startswith("0x") and len(out) == 1:
            # a bare thunk: follow it once
            out.append("      -> follow")
            out += dis(int(ins.op_str, 16), n, depth + 1)
            break
        if len(out) >= n:
            out.append("      ...")
            break
    return out


for s in SLOTS:
    fn = struct.unpack_from("<I", data, off(VT + 4 * s))[0]
    print(f"slot {s:3} vt+{4*s:#05x} -> {fn:#010x}")
    print("\n".join(dis(fn)))
