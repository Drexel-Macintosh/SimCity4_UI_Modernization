#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ADVERSARIAL verify of LANE 4 (#130 rating decline arrow).

Everything here is read from the SHIPPED exe. Positive controls are printed
for every negative claim.
"""
import sys, struct
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


DATA, SECS = load()
MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True


def va2off(va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def rd(va, n):
    o = va2off(va)
    return DATA[o:o+n] if o is not None else None


def dis(va, count=60):
    o = va2off(va)
    out = []
    for ins in MD.disasm(DATA[o:o+count*16], va):
        out.append(ins)
        if len(out) >= count:
            break
    return out


def show(va, count=60, tag=""):
    print("--- %s @ 0x%08X ---" % (tag, va))
    for ins in dis(va, count):
        print("  0x%08X  %-24s %s %s" % (ins.address,
              ins.bytes.hex(), ins.mnemonic, ins.op_str))


print("=" * 78)
print("SECTIONS:", [(n, hex(IMAGE_BASE+va), hex(max(vs, rs))) for n, va, vs, ro, rs in SECS])

# ---------------------------------------------------------------- CLAIM A
print("\n=== A. stock prologue bytes at 0x007E8510 ===")
b = rd(0x7E8510, 16)
print("   bytes:", " ".join("%02X" % c for c in b))
print("   spec claims 83 EC 64 53 55 ->",
      "MATCH" if b[:5] == bytes([0x83, 0xEC, 0x64, 0x53, 0x55]) else "*** MISMATCH ***")
show(0x7E8510, 8, "sub_7E8510 prologue")

# ---------------------------------------------------------------- CLAIM B
print("\n=== B. function extent, ret form, and branch targets in [0x7E8510,0x7E8515) ===")
# walk linearly to the end of the function: stop at the last ret before the
# next function prologue / int3 padding run.
va = 0x7E8510
end = None
targets = []
seen_rets = []
o = va2off(va)
buf = DATA[o:o + 0x1400]
insns = list(MD.disasm(buf, va))
for i, ins in enumerate(insns):
    if ins.mnemonic == "ret" or ins.mnemonic == "retn":
        seen_rets.append((ins.address, ins.op_str, ins.bytes.hex()))
    if ins.mnemonic.startswith("j") or ins.mnemonic == "call":
        # direct targets only
        for op in ins.operands:
            if op.type == 2:  # IMM
                targets.append((ins.address, ins.mnemonic, op.imm))
    if ins.mnemonic == "int3":
        end = ins.address
        break
print("   int3 padding starts at 0x%08X (function end)" % (end or 0))
print("   RET sites:")
for a, s, h in seen_rets:
    if end is None or a < end:
        print("      0x%08X  ret %s   (%s)" % (a, s, h))
inwin = [t for t in targets if 0x7E8510 < t[2] < 0x7E8515]
print("   POSITIVE CONTROL: total direct jmp/call targets scanned in the "
      "function = %d; targets equal to 0x7E8510 exactly = %d"
      % (len(targets), len([t for t in targets if t[2] == 0x7E8510])))
print("   branch targets landing INSIDE the 5-byte hook window "
      "(0x7E8511..0x7E8514): %d %s" % (len(inwin), inwin))

# also: anything ANYWHERE in .text jumping into that window?
print("\n   whole-.text scan for a rel32 jmp/call into 0x7E8511..0x7E8514:")
hits = []
for n, sva, vsize, roff, rsize in SECS:
    if n != ".text":
        continue
    tsz = max(vsize, rsize)
    for k in range(tsz - 5):
        c = DATA[roff + k]
        if c in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", DATA, roff + k + 1)[0]
            tgt = IMAGE_BASE + sva + k + 5 + rel
            if 0x7E8510 <= tgt <= 0x7E8514:
                hits.append((IMAGE_BASE + sva + k, hex(tgt)))
print("      hits:", hits[:20], "count=%d" % len(hits))
print("      POSITIVE CONTROL: same scan for target==0x007E8510 finds the "
      "real callers listed below.")
