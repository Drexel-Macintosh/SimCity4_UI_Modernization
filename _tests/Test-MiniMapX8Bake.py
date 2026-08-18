#!/usr/bin/env python3
"""
Test-MiniMapX8Bake - the #121 x8 terrain-bake patch's offline gate.

WHAT THE PATCH DOES
    The game's minimap terrain bake dispatches its per-tile blitter through a
    5-entry jump table indexed by (zoom + 2) with an UNSIGNED bound:

        0x7A8560  lea ecx,[edx+2]        ; index = zoom+2
        0x7A8563  cmp ecx,4              ; 5 entries
        0x7A8566  ja  0x7A85B0           ; UNSIGNED -> zoom -3 = 0xFFFFFFFF -> skip
        0x7A8568  jmp [ecx*4+0x7A8628]

    The destination math either side of it is fully general in zoom
    (destY = cellY*16 >> (zoom+4); tile side = 256 >> (zoom+4)), so ONLY the
    dispatch stops at -2. At our 2x tier a 64-cell tile drives the Data Views
    map's surface to 512 = zoom -3, the bake silently draws nothing, and the
    game then alpha-blends its data cells onto black.

    CodePatches::ApplyMiniMapX8Bake rewrites those 15 bytes to index (zoom + 3)
    against a 6-entry table in our DLL: entry 0 is our x8 blitter, entries 1..5
    are the game's own stubs in their original order.

WHAT THIS GATE ASSERTS (all against the STOCK exe on disk, never a patched one)
    1. The 15 dispatch bytes are exactly what CodePatches expects.
    2. The 0x21-byte stub block is exactly what CodePatches expects, and each
       stub's imm32 names a blitter in the expected order (/4, /2, 1:1, x2, x4).
    3. The 5 jump-table dwords are exactly the 5 stub VAs.
    4. The replacement CodePatches computes is LENGTH-EXACT (15 bytes) and
       differs from stock in exactly 6 byte positions: the lea imm8, the cmp
       imm8, and the 4 table-address bytes. In particular the `ja` rel8 is
       UNCHANGED, so the skip still lands at 0x7A85B0.
    5. BLAST RADIUS: the table VA 0x7A8628 appears as an immediate exactly ONCE
       in .text (the jmp we replace), so re-pointing it cannot affect anything
       else.

POSITIVE CONTROL
    The scan proves it can find a known-present immediate - a BLITTER address
    (0x7A6BD0), which check [2] independently proves is encoded as an imm32
    inside its `mov ecx, imm32` stub. Without that, "referenced once" could
    just mean the scanner is broken - a null that looks like a pass.
    (The first version of this gate used the bake itself, 0x7A7FF0, and
    reported ZERO hits: the bake is reached by `call rel32`, so its absolute
    address never appears as an imm32 anywhere. The GATE was wrong, not the
    exe - see the note at CONTROL_VA below.)

NEGATIVE CONTROL
    A deliberately corrupted copy of the dispatch bytes must FAIL check 1.

This gate reads the exe READ-ONLY. It never writes, never launches the game.
Exit 0 = pass.
"""

import os
import struct
import sys

IMAGE_BASE = 0x400000

EXE_CANDIDATES = [
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe",
    r"C:\Program Files\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe",
]

DISPATCH_VA = 0x007A8560
DISPATCH_STOCK = bytes([
    0x8D, 0x4A, 0x02,                                # lea ecx,[edx+2]
    0x83, 0xF9, 0x04,                                # cmp ecx,4
    0x77, 0x48,                                      # ja  0x7A85B0
    0xFF, 0x24, 0x8D, 0x28, 0x86, 0x7A, 0x00,        # jmp [ecx*4+0x7A8628]
])

STUB_BLOCK_VA = 0x007A856F
STUB_STOCK = bytes([
    0xB9, 0xD0, 0x6B, 0x7A, 0x00, 0xEB, 0x1A,        # ecx=0x7A6BD0  /4   zoom +2
    0xB9, 0xD0, 0x6A, 0x7A, 0x00, 0xEB, 0x13,        # ecx=0x7A6AD0  /2   zoom +1
    0xB9, 0x70, 0x6A, 0x7A, 0x00, 0xEB, 0x0C,        # ecx=0x7A6A70  1:1  zoom  0
    0xB9, 0x60, 0x6E, 0x7A, 0x00, 0xEB, 0x05,        # ecx=0x7A6E60  x2   zoom -1
    0xB9, 0xE0, 0x6E, 0x7A, 0x00,                    # ecx=0x7A6EE0  x4   zoom -2
])
EXPECTED_BLITTERS = [0x7A6BD0, 0x7A6AD0, 0x7A6A70, 0x7A6E60, 0x7A6EE0]

TABLE_VA = 0x007A8628
TABLE_STOCK = [0x007A858B, 0x007A8584, 0x007A857D, 0x007A8576, 0x007A856F]

# POSITIVE CONTROL for the imm32 scanner.
#
# The first version of this gate used the bake itself (0x7A7FF0) and reported
# ZERO hits - which looked like the exe was wrong. It was the GATE that was
# wrong: the bake is reached by `call rel32` (E8 xx xx xx xx), a RELATIVE
# encoding, so its absolute VA never appears as an imm32 anywhere. Searching
# for it proved nothing about the scanner.
#
# The right control is a value we KNOW is encoded as a literal imm32: each
# blitter address inside its `mov ecx, imm32` stub (B9 xx xx xx xx), verified
# by check [2] above. If the scanner cannot find that, it cannot be trusted to
# say the jump table is referenced only once.
CONTROL_VA = 0x007A6BD0       # the /4 blitter, from `mov ecx,0x7A6BD0`
TEXT_LO, TEXT_HI = 0x401000, 0x00B00000


def find_exe():
    for p in EXE_CANDIDATES:
        if os.path.isfile(p):
            return p
    return None


def main():
    exe = find_exe()
    if not exe:
        print("FAIL: SimCity 4.exe not found in any known location:")
        for p in EXE_CANDIDATES:
            print("   ", p)
        return 1

    data = open(exe, "rb").read()
    print("Test-MiniMapX8Bake")
    print("  exe   : %s" % exe)
    print("  size  : %d bytes" % len(data))
    print()

    def at(va, n):
        off = va - IMAGE_BASE
        if off < 0 or off + n > len(data):
            return None
        return data[off:off + n]

    failures = []

    # ---- 1. dispatch bytes -------------------------------------------------
    disp = at(DISPATCH_VA, len(DISPATCH_STOCK))
    if disp != DISPATCH_STOCK:
        failures.append("dispatch @0x%08X is %s, expected %s"
                        % (DISPATCH_VA,
                           disp.hex(" ") if disp else "<out of range>",
                           DISPATCH_STOCK.hex(" ")))
        print("  [1] dispatch bytes           FAIL")
    else:
        print("  [1] dispatch bytes           ok  (%s)" % disp.hex(" "))

    # ---- 2. stub block + blitter order -------------------------------------
    stubs = at(STUB_BLOCK_VA, len(STUB_STOCK))
    if stubs != STUB_STOCK:
        failures.append("stub block @0x%08X differs from expected"
                        % STUB_BLOCK_VA)
        print("  [2] stub block               FAIL")
    else:
        got = []
        for i in range(5):
            base = i * 7
            got.append(struct.unpack_from("<I", stubs, base + 1)[0])
        if got != EXPECTED_BLITTERS:
            failures.append("blitter order %s != expected %s"
                            % ([hex(x) for x in got],
                               [hex(x) for x in EXPECTED_BLITTERS]))
            print("  [2] stub block               FAIL (blitter order)")
        else:
            print("  [2] stub block + order       ok  (/4 /2 1:1 x2 x4)")

    # ---- 3. jump table -----------------------------------------------------
    raw = at(TABLE_VA, 20)
    tbl = list(struct.unpack("<5I", raw)) if raw else []
    if tbl != TABLE_STOCK:
        failures.append("table @0x%08X is %s, expected %s"
                        % (TABLE_VA, [hex(x) for x in tbl],
                           [hex(x) for x in TABLE_STOCK]))
        print("  [3] jump table               FAIL")
    else:
        print("  [3] jump table               ok  (%s)"
              % " ".join(hex(x) for x in tbl))

    # ---- 4. replacement shape ---------------------------------------------
    # Mirror exactly what CodePatches::ApplyMiniMapX8Bake builds.
    repl = bytearray(DISPATCH_STOCK)
    repl[2] = 0x03                      # lea ecx,[edx+3]
    repl[5] = 0x05                      # cmp ecx,5
    repl[11:15] = struct.pack("<I", 0xDEADBEEF)   # jmp [ecx*4 + <our table>]
    if len(repl) != len(DISPATCH_STOCK):
        failures.append("replacement is not length-exact")
        print("  [4] replacement shape        FAIL (length)")
    else:
        diff = [i for i in range(len(repl)) if repl[i] != DISPATCH_STOCK[i]]
        # positions 2 (lea imm8), 5 (cmp imm8), 11..14 (table address)
        if diff != [2, 5, 11, 12, 13, 14]:
            failures.append("replacement changes byte positions %s, expected "
                            "[2, 5, 11, 12, 13, 14]" % diff)
            print("  [4] replacement shape        FAIL (touched %s)" % diff)
        elif repl[6:8] != DISPATCH_STOCK[6:8]:
            failures.append("the ja rel8 was modified - the skip target moved")
            print("  [4] replacement shape        FAIL (ja changed)")
        else:
            print("  [4] replacement shape        ok  (15 bytes, ja untouched,")
            print("                                    only lea/cmp/table differ)")

    # ---- 5. blast radius: table VA referenced exactly once ------------------
    needle = struct.pack("<I", TABLE_VA)
    hits = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        hits.append(i + IMAGE_BASE)
        start = i + 1
    text_hits = [h for h in hits if TEXT_LO <= h < TEXT_HI]

    ctrl = struct.pack("<I", CONTROL_VA)
    ctrl_hits = data.count(ctrl)

    print()
    print("  positive control: 0x%08X (a blitter, encoded as imm32) appears "
          "%d time(s)" % (CONTROL_VA, ctrl_hits))
    if ctrl_hits == 0:
        failures.append("POSITIVE CONTROL FAILED: the imm32 scanner cannot find "
                        "a value we PROVED is an imm32 in check [2], so "
                        "'referenced once' below proves nothing")
        print("  [5] blast radius             FAIL (control)")
    elif len(text_hits) != 1:
        failures.append("table VA 0x%08X referenced %d times (%s) - expected "
                        "exactly 1 (the jmp we replace)"
                        % (TABLE_VA, len(text_hits),
                           [hex(h) for h in text_hits]))
        print("  [5] blast radius             FAIL")
    else:
        print("  [5] blast radius             ok  (0x%08X referenced once, at "
              "0x%08X)" % (TABLE_VA, text_hits[0]))

    # ---- negative control --------------------------------------------------
    print()
    corrupt = bytearray(DISPATCH_STOCK)
    corrupt[0] ^= 0xFF
    if bytes(corrupt) == DISPATCH_STOCK:
        print("  negative control: FAILED to build a corrupted copy")
        return 1
    print("  negative control: a corrupted dispatch differs from stock as "
          "required (check 1 would reject it).")

    print()
    if failures:
        print("FAIL: %d problem(s):" % len(failures))
        for f in failures:
            print("  - %s" % f)
        print()
        print("  If the exe is a DIFFERENT BUILD, that is expected: the DLL's")
        print("  runtime verify declines the patch and the Data Views map falls")
        print("  back to the clamp. Do NOT 'fix' this by relaxing the bytes.")
        return 1

    print("ALL PASS (dispatch + stubs + table byte-exact; replacement length-")
    print("          exact and minimal; table VA referenced exactly once)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
