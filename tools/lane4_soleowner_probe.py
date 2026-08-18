#!/usr/bin/env python3
"""LANE 4 part 5 - is sub_7E8510 the SOLE mover of the decline arrow, and is
its prologue safe for a 5-byte trampoline?

Two questions, two positive controls.

(1) SOLE OWNER. Scan .text for every 32-bit immediate 0xCA5A415E (the decline
    arrow window id) and 0x6A5A4156 (the increase arrow). Only code that can
    NAME the window can fetch and move it.
    POSITIVE CONTROL: the scan must report the four sites we have already
    disassembled by hand - 0x007E87FA, 0x007E88F4, 0x007E89B9 (inside the
    updater) and 0x007ED2DB (the builder's snapshot). If it misses any of
    those it is blind and "no other owner" would be a structural null.

(2) TRAMPOLINE. Print the first 8 bytes at 0x007E8510 and the instruction
    boundaries, so the 5-byte JMP a detour needs can be shown NOT to straddle
    an instruction.
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000
IDS = {0xCA5A415E: "decline arrow", 0x6A5A4156: "increase arrow",
       0x8A517556: "rating groove", 0xE9889775: "composite HUD root"}
CONTROL = {0x007E87FA, 0x007E88F4, 0x007E89B9, 0x007ED2DB}


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    off = pe + 24 + opt
    for _ in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


def va2off(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None


data, secs = load()
sva = roff = rsize = None
for n, s, v, r, rs in secs:
    if n == ".text":
        sva, roff, rsize = IMAGE_BASE + s, r, rs
blob = data[roff:roff + rsize]

print("### (1) EVERY .text reference to the arrow / groove ids ###")
found_push = set()
for wid, label in IDS.items():
    pat = struct.pack("<I", wid)
    i = -1
    print(f"\n  0x{wid:08X}  {label}")
    while True:
        i = blob.find(pat, i + 1)
        if i < 0:
            break
        # a `push imm32` is 68 <imm32>
        site = sva + i - 1 if i > 0 and blob[i-1] == 0x68 else sva + i
        kind = "push imm32" if (i > 0 and blob[i-1] == 0x68) else "raw dword"
        print(f"    0x{site:08X}  {kind}")
        found_push.add(site)

print("\n  POSITIVE CONTROL - the four hand-disassembled sites:")
for c in sorted(CONTROL):
    print(f"    0x{c:08X} present: {c in found_push}")

print("\n### (2) trampoline safety at 0x007E8510 ###")
o = va2off(secs, 0x007E8510)
raw = data[o:o + 12]
print("  STOCK BYTES 0x007E8510: " + " ".join(f"{b:02X}" for b in raw))
md = Cs(CS_ARCH_X86, CS_MODE_32)
acc = 0
for ins in md.disasm(raw, 0x007E8510):
    acc += ins.size
    print(f"    0x{ins.address:08X} (+{acc - ins.size}) size={ins.size}  "
          f"{ins.mnemonic} {ins.op_str}")
    if acc >= 8:
        break
print("  -> a 5-byte JMP lands on a boundary iff some prefix sums to exactly 5")
