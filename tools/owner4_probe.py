#!/usr/bin/env python3
"""Owner probe #4: identify the vtables, and read the crashing signature.
Read-only."""
import struct, bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IB = 0x400000
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.detail = False


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []; off = pe + 24 + opt
    for i in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize)); off += 40
    return data, secs


DATA, SECS = load()


def va2off(va):
    rva = va - IB
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


def sec_of(va):
    rva = va - IB
    for n, sva, vsize, roff, rsize in SECS:
        if sva <= rva < sva + max(vsize, rsize):
            return n
    return None


def dw(va):
    o = va2off(va)
    return struct.unpack_from("<I", DATA, o)[0] if o is not None else None


def cstr(va, n=96):
    o = va2off(va)
    if o is None: return None
    b = DATA[o:o+n]
    z = b.find(b"\0")
    s = b[:z if z >= 0 else n]
    try:
        t = s.decode("ascii")
    except Exception:
        return None
    return t if all(32 <= c < 127 for c in s) and len(s) > 2 else None


def rtti_name(vt_base):
    """MSVC: [vt-4] = COL ptr; COL+0x0C = TypeDescriptor ptr; TD+8 = name."""
    col = dw(vt_base - 4)
    if col is None or sec_of(col) != ".rdata":
        return None
    td = dw(col + 0x0C)
    if td is None:
        return None
    nm = cstr(td + 8, 160)
    return nm


def find_vt_base(slot_va, maxback=0x400):
    """Walk back from a slot until the dword stops pointing into .text."""
    va = slot_va
    while va - 4 >= IB and slot_va - va < maxback:
        d = dw(va - 4)
        if d is None or sec_of(d) != ".text":
            break
        va -= 4
    return va


def dis(va, n, stop=None):
    o = va2off(va)
    out = []
    for ins in MD.disasm(DATA[o:o+n*10], va, n):
        out.append(ins)
        if stop and ins.address >= stop:
            break
    return out


ANN = {0x34: "rect.L", 0x38: "rect.T", 0x3c: "rect.R", 0x40: "rect.B",
       0xe4: "blitSize", 0xf0: "surface", 0x104: "zoom",
       0x114: "rasterBase", 0x118: "rasterW", 0x11c: "rasterH", 0x120: "dirty"}


def show(va, n, title, stop=None):
    print(f"\n--- {title} @ 0x{va:08X} ---")
    for ins in dis(va, n, stop):
        t = ""
        for off, what in ANN.items():
            if f"+ 0x{off:x}]" in ins.op_str:
                t = f"   <<< {what}?"
        print(f"  0x{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}{t}")


print("=" * 74)
print("A. IDENTIFY THE VTABLES WE LANDED IN")
print("=" * 74)
slots = {
    0x00AB814C: "fn 0x7a54d0",
    0x00AB7EEC: "fn 0x7a56e0",
    0x00AB8160: "fn 0x7a61e0",
    0x00AB8164: "fn 0x7a6220",
    0x00AB815C: "fn 0x7a6270",
    0x00AB7FF4: "fn 0x7a6290",
    0x00AD10B8: "fn 0x7a6544",
    0x00AB8518: "fn 0x7a79b0 (MINIMAP DRAW, control)",
}
bases = {}
for s, who in sorted(slots.items()):
    b = find_vt_base(s)
    bases.setdefault(b, []).append((s, who))
    print(f"  slot {s:08X} ({who:<38}) -> vtable base {b:08X}  index +0x{s-b:X} (#{(s-b)//4})")

print("\n  RTTI names:")
for b in sorted(bases):
    print(f"    vtable {b:08X}: COL={dw(b-4):08X}  name={rtti_name(b)!r}")

print("\n" + "=" * 74)
print("B. FULL DUMP OF EACH DISTINCT VTABLE (first 120 slots)")
print("=" * 74)
for b in sorted(bases):
    print(f"\n  ==== vtable {b:08X}  name={rtti_name(b)!r} ====")
    i = 0
    while i < 140:
        v = dw(b + i*4)
        if v is None or sec_of(v) != ".text":
            print(f"    (ends at +0x{i*4:X}, next dword {v:08X} in {sec_of(v)})")
            break
        mk = ""
        for s, who in slots.items():
            if s == b + i*4:
                mk = f"   <<<<<< {who}"
        print(f"    +0x{i*4:03X} (#{i:3}) = {v:08X}{mk}")
        i += 1

print("\n" + "=" * 74)
print("C. 0x007A2740 FULL DISASSEMBLY (signature / args / [ebx+0x94c])")
print("=" * 74)
show(0x007A2740, 140, "TOP 0x007A2740")
