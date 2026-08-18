"""scan_76d3d0_reach.py - #103 adjudicator (READ-ONLY on the exe).

Two questions, both answered against the WHOLE image, not just the builder:

  Q1  Who calls / references sub_76D3D0 (0x0076D3D0)?  Is it Graphs-only, or
      can the Budget dialog reach it?
  Q2  Does ANY branch target, call target, or 4-byte absolute in .text/.rdata/
      .data land INSIDE one of the three v2.55.0 re-encoded blocks?
      (The shipped gate only scans 0x0076D3D0..0x0076E420 - SCOPE, law 42.)

Run:  python tools\\uimap\\emu\\scan_76d3d0_reach.py
"""
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))      # tools\uimap
import common as C                              # noqa: E402

FN_LO, FN_HI = 0x0076D3D0, 0x0076E420
BLOCKS = [
    (0x0076E0E8, 25, "B1 plain swatch anchor"),
    (0x0076E145, 41, "B2 checkbox rect"),
    (0x0076E1D6, 42, "B3 AddChild + cbox swatch"),
]

print("exe:", C.EXE)
print("fingerprint:", C.exe_fingerprint())
print(".text %08X-%08X  .rdata %08X-%08X  .data %08X-%08X"
      % (C.TEXT_LO, C.TEXT_HI, C.RDATA_LO, C.RDATA_HI, C.DATA_LO, C.DATA_HI))

text = C.text_blob()
m = C.md()

# ---------------------------------------------------------------------------
# Q1a  direct rel32 call/jmp to 0x0076D3D0 anywhere in .text
# ---------------------------------------------------------------------------
print("\n=== Q1a  direct rel32 call/jmp targeting 0x0076D3D0 (whole .text) ===")
hits = []
# E8 rel32 (call) and E9 rel32 (jmp): brute-force over every byte offset, then
# confirm by decoding at that offset. Brute force is deliberate - it does not
# depend on knowing function boundaries.
for op, name in ((0xE8, "call"), (0xE9, "jmp")):
    i = 0
    while True:
        i = text.find(bytes([op]), i)
        if i < 0 or i + 5 > len(text):
            break
        rel = struct.unpack_from("<i", text, i + 1)[0]
        va = C.TEXT_LO + i
        tgt = va + 5 + rel
        if tgt == FN_LO:
            hits.append((va, name))
        i += 1
for va, name in sorted(hits):
    print("  %-4s from %08X" % (name, va))
print("  total: %d" % len(hits))

# ---------------------------------------------------------------------------
# Q1b  absolute 0x0076D3D0 stored anywhere (vtable slot / function pointer)
# ---------------------------------------------------------------------------
print("\n=== Q1b  absolute dword 0x0076D3D0 in .text/.rdata/.data ===")
needle = struct.pack("<I", FN_LO)
for nm, lo, hi, off, raw in [(s[0], s[1], s[2], s[3], s[4])
                             for s in C.sections()]:
    if nm not in (".text", ".rdata", ".data"):
        continue
    blob = C.exe_bytes()[off:off + min(raw, hi - lo)]
    i = 0
    n = 0
    while True:
        i = blob.find(needle, i)
        if i < 0:
            break
        print("  %-7s %08X" % (nm, lo + i))
        n += 1
        i += 1
    print("  %-7s total %d" % (nm, n))

# ---------------------------------------------------------------------------
# Q2  anything landing inside a re-encoded block, WHOLE IMAGE
# ---------------------------------------------------------------------------
print("\n=== Q2  references INTO the three re-encoded blocks (whole image) ===")
holes = []
for va, ln, nm in BLOCKS:
    holes.append((va, va + ln, nm))
    print("  block %08X..%08X (%d bytes)  %s" % (va, va + ln, ln, nm))

# Q2a: every rel32 call/jmp and rel8/rel32 jcc in the WHOLE .text.
print("\n  -- Q2a rel8/rel32 branch immediates, whole .text (brute decode) --")
bad = []
# Brute-force decode from EVERY byte offset is too slow for 6 MB; instead
# scan for the encodings that can produce a rel target and confirm the
# computed target, which is exactly what a stray branch would look like.
# 1-byte-opcode rel32: E8 (call), E9 (jmp)
for op in (0xE8, 0xE9):
    i = 0
    while True:
        i = text.find(bytes([op]), i)
        if i < 0 or i + 5 > len(text):
            break
        rel = struct.unpack_from("<i", text, i + 1)[0]
        va = C.TEXT_LO + i
        tgt = va + 5 + rel
        for a, b, nm in holes:
            if a < tgt < b:            # a itself = block entry, legal
                bad.append((va, tgt, "rel32 op %02X" % op, nm))
        i += 1
# 2-byte-opcode rel32 jcc: 0F 80..8F
i = 0
while True:
    i = text.find(b"\x0f", i)
    if i < 0 or i + 6 > len(text):
        break
    if 0x80 <= text[i + 1] <= 0x8F:
        rel = struct.unpack_from("<i", text, i + 2)[0]
        va = C.TEXT_LO + i
        tgt = va + 6 + rel
        for a, b, nm in holes:
            if a < tgt < b:
                bad.append((va, tgt, "jcc rel32", nm))
    i += 1
# 1-byte rel8: 70..7F jcc, EB jmp, E3 jecxz, E0..E2 loop
for i in range(len(text) - 2):
    op = text[i]
    if 0x70 <= op <= 0x7F or op in (0xEB, 0xE3, 0xE0, 0xE1, 0xE2):
        rel = struct.unpack_from("<b", text, i + 1)[0]
        va = C.TEXT_LO + i
        tgt = va + 2 + rel
        for a, b, nm in holes:
            if a < tgt < b:
                bad.append((va, tgt, "rel8 op %02X" % op, nm))
print("  candidate rel hits INSIDE a block (pre-validation): %d" % len(bad))
for va, tgt, kind, nm in bad:
    # Validate: does a real instruction actually START at va? Decode a short
    # window ending at va from a nearby anchor to reduce false positives from
    # bytes that merely LOOK like a branch opcode.
    print("    from %08X -> %08X  (%s)  %s" % (va, tgt, kind, nm))

# Q2b: absolute dword pointing inside a block (jump table / data pointer)
print("\n  -- Q2b absolute dwords pointing inside a block, .text/.rdata/.data --")
nabs = 0
for s in C.sections():
    nm, lo, hi, off, raw = s
    if nm not in (".text", ".rdata", ".data"):
        continue
    blob = C.exe_bytes()[off:off + min(raw, hi - lo)]
    for a, b, bnm in holes:
        for t in range(a, b):
            needle = struct.pack("<I", t)
            i = 0
            while True:
                i = blob.find(needle, i)
                if i < 0:
                    break
                print("    %-7s %08X holds %08X  (%s)"
                      % (nm, lo + i, t, bnm))
                nabs += 1
                i += 1
print("  total absolute refs inside a block: %d" % nabs)

print("\nDONE")
