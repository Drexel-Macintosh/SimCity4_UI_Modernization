#!/usr/bin/env python3
"""ENUMERATE EVERY CONSUMER OF THE DATA VIEWS MAP WINDOW.

Anyone who wants that window must name it. Two ways exist:
  * by window id 0x00004203 (GetChildWindowFromID / GetChildAs* / ChildExists)
  * by the class iid 0xCA318385 / clsid 0xCA318388
Both appear as imm32 operands, so a raw imm32 scan of .text finds ALL of them.

POSITIVE CONTROL: the scan must find 0x007A2FF4, the already-measured
`push 0x4203` inside the DV renderer sub_7A2F60. If it does not, the probe is
blind and its null means nothing.
Read-only."""
import struct, bisect
from pe109_probe import *

data, secs = load()
S = sorted(function_starts(data, secs))
def encl(va):
    i = bisect.bisect_right(S, va) - 1
    return S[i] if i >= 0 else None

NEEDLES = {
    0x00004203: "DV map window id 0x4203",
    0xCA318385: "cISC4WinMiniMap iid",
    0xCA318388: "cSC4WinMiniMap clsid",
    0x0BC3B559: "dock/UDI minimap window id",
    0x8A2871C3: "Data Views page id",
}

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
found = {k: [] for k in NEEDLES}

for n, sva, vsize, roff, rsize in secs:
    if not n.startswith(".text"):
        continue
    base = IMAGE_BASE + sva
    blob = data[roff:roff + rsize]
    for val, label in NEEDLES.items():
        needle = struct.pack("<I", val)
        i = blob.find(needle)
        while i != -1:
            # decode a window backwards to confirm it is an operand, not data
            found[val].append(base + i)
            i = blob.find(needle, i + 1)

print("RAW imm32/byte-pattern hits in .text")
for val, label in NEEDLES.items():
    hits = found[val]
    print(f"\n  0x{val:08X}  {label}: {len(hits)} hit(s)")
    for h in hits:
        # the imm starts 1 byte after the opcode for `push imm32` (0x68)
        # and 1 byte after for `cmp r/m32, imm32` variants; just decode from -1..-8
        ctx = None
        for back in range(1, 9):
            for ins in md.disasm(data[va2off(secs, h - back): va2off(secs, h - back) + 16], h - back):
                if ins.address == h - back and ins.address + ins.size > h:
                    ctx = ins
                break
            if ctx: break
        fn = encl(h)
        print(f"      {hex(h)}  in fn {hex(fn) if fn else '?'}   "
              f"{(ctx.mnemonic + ' ' + ctx.op_str) if ctx else '(not an instruction operand -> DATA)'}")

print()
print("POSITIVE CONTROL: 0x007A2FF4 (measured `push 0x4203` in sub_7A2F60) present in "
      f"the 0x4203 hit list? -> {0x007A2FF4 + 1 in found[0x00004203] or 0x007A2FF4 in found[0x00004203] or any(abs(h-0x007A2FF4)<=2 for h in found[0x00004203])}")
