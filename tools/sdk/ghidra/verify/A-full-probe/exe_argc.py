#!/usr/bin/env python
"""Structural cross-check of ALL 148 cIGZWin slots against the exe (OFFLINE).

For every slot of cSC4WinAlertBorder's cIGZWin vtable 0x00AB5B48 in
SimCity 4.exe 1.1.641, read the callee stack cleanup of the implementation
('ret N' -> N/4 dword args, __thiscall; a bare 'ret' = 0 args) and compare it
with the dword-arg count of the header declaration that COMPILES to that slot
(slots.json from gen_probe.py). An argc disagreement PROVES a mislabel at that
slot; agreement is only consistency (same-arity neighbours cannot be told apart).

Positive controls: slot 48 GetArea() -> 0 args; 53 SetSize(w,h) -> 2;
55 SetArea(l,t,r,b) -> 4; 104 GetFillColor(r&,g&,b&) -> 3; 144 -> 5.
"""
import json
import os
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
VT = 0x00AB5B48

data = open(EXE, "rb").read()
pe = struct.unpack_from("<I", data, 0x3C)[0]
nsec = struct.unpack_from("<H", data, pe + 6)[0]
optsz = struct.unpack_from("<H", data, pe + 20)[0]
base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + optsz + 40 * i
    vs, va, rs, raw = struct.unpack_from("<IIII", data, o + 8)
    secs.append((base + va, max(vs, rs), raw))


def off(va):
    for sva, sz, raw in secs:
        if sva <= va < sva + sz:
            return raw + (va - sva)
    raise ValueError(hex(va))


md = Cs(CS_ARCH_X86, CS_MODE_32)


def retn(va, hops=0):
    """First ret reachable in a linear sweep of ONE function. Follows an entry
    'jmp imm' (adjustor thunk) up to 3 hops. An unconditional jmp with no
    pending in-function branch target beyond it ends the function (tail call):
    if no ret was seen, the arity is UNKNOWN (None) - a tail call forwards the
    caller's stack untouched, so it proves nothing about arg count."""
    first = True
    reach = va
    for ins in md.disasm(data[off(va):off(va) + 0x800], va):
        if first and ins.mnemonic == "jmp" and ins.op_str.startswith("0x") and hops < 3:
            return retn(int(ins.op_str, 16), hops + 1)
        first = False
        if ins.mnemonic in ("ret", "retn"):
            return int(ins.op_str, 16) if ins.op_str else 0
        if ins.mnemonic == "int3":
            return None
        if ins.mnemonic.startswith("j") and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16)
            if va < t < va + 0x800:
                reach = max(reach, t)
        if ins.mnemonic == "jmp" and ins.address >= reach:
            return None
    return None


def dword_args(argtoks):
    # every scalar/pointer/reference argument here is passed as one dword
    return len(argtoks)


rows = json.load(open(os.path.join(HERE, "slots.json")))["rows"]
by_compiled = {}
for r in rows:
    by_compiled.setdefault(r["compiled"], []).append(r)


def argc_of(sig):
    inner = sig[sig.index("(") + 1: sig.rindex(")")].strip()
    return 0 if not inner else inner.count(",") + 1


# intended declaration per exe slot: the exe slot where measured (established or
# decoded), else the Mac slot (non-overloaded names only; Mac has no overload sigs).
intended = {}
for r in rows:
    s = r["exe"] if r["exe"] is not None else (r["mac"] if r["overloads"] == 1 else None)
    if s is not None:
        intended[s] = r
intended.setdefault(57, {"sig": "GZWinOffset(dx,dy)  [Mac-only, not in header]", "name": "GZWinOffset"})
mac_offset_argc = {57: 2}

out = []
bad_c, bad_i = [], []
for s in range(148):
    fn = struct.unpack_from("<I", data, off(VT + 4 * s))[0]
    n = retn(fn)
    exe_argc = None if n is None else n // 4
    decl = by_compiled.get(s, [])
    csig = decl[0]["sig"] if decl else "(nothing compiles here)"
    cargc = argc_of(csig) if decl else None
    it = intended.get(s)
    isig = it["sig"] if it else "?"
    iargc = mac_offset_argc.get(s, argc_of(isig) if it and "(" in isig else None)
    f1 = f2 = ""
    if exe_argc is None:
        f1 = f2 = "tail/unk"
    else:
        if cargc is None or exe_argc != cargc:
            f1 = "C-ARGC!"
            bad_c.append(s)
        if iargc is not None and exe_argc != iargc:
            f2 = "I-ARGC!"
            bad_i.append(s)
    out.append(f"{s:3} {fn:#010x} exe={exe_argc!s:>4} | compiled-decl {cargc!s:>4} {f1:8} {csig:58} "
               f"| intended {iargc!s:>4} {f2:8} {isig}")

open(os.path.join(HERE, "exe_argc.txt"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
print(f"\nexe argc != argc of the declaration that COMPILES to the slot: {bad_c}")
print(f"exe argc != argc of the INTENDED declaration (exe/Mac name) : {bad_i}")
