r"""#159 — find the code that sizes the PLACEMENT COST readout 128x32.

MEASURED FIRST (2026-08-15, VisTrace at 2x, log SC4UIScale.log):
  the readout is VWKID 7 of the 3D view - class GZWinBMP vt 0x00ADF6A0,
  id 0x00000000, kids=0, and it is the ONLY view child that MOVES and toggles
  visibility while placing:
      (434,716) -> (483,713) -> (1072,1014), always 128x32
  Our sweep scaled it to 256x64 four times; the game reset it each frame and
  ScaleRecord tombstoned it ("game-managed geometry"). Scaling it also FLASHED
  (FLASHSET candidate #9), so fighting it per frame is the wrong cure - the box
  has to be born right, like the tooltip's 250px wrap byte patch.

So: find where the exe writes a 128-wide / 32-tall rect into a SetArea call.

  cIGZWin slots (SC4-UI-ENGINE.md): SetW +0xCC, SetSize +0xD4, SetArea4 +0xDC
  A cursor-tracking box computes l,t from the mouse and r=l+128, b=t+32, so the
  128 and 32 should appear as ADD/LEA immediates near the call, not as literal
  absolute coordinates.

⚠ THIS PROBE PROVES NOTHING ON ITS OWN. It NARROWS. A hit is a candidate to be
confirmed against the live window, never a patch site to be trusted (law: a
static defect is a hypothesis).

    python costbox_probe.py [--w 128] [--h 32] [--window 40]

Read-only: opens the exe, writes nothing.
"""
import os
import struct
import sys

import capstone

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000


def arg(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


WANT_W = arg("--w", 128)
WANT_H = arg("--h", 32)
BACK = arg("--window", 40)          # instructions to look back from the call

# cIGZWin geometry setters, by vtable byte offset.
SETTERS = {0xDC: "SetArea4", 0xD4: "SetSize", 0xCC: "SetW"}


def text_section(data):
    pe = data.find(b"PE\0\0")
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    off = pe + 24 + opt
    for i in range(nsec):
        s = data[off + i * 40: off + (i + 1) * 40]
        name = s[:8].rstrip(b"\0").decode("latin-1")
        vsize, va, rsize, raw = struct.unpack_from("<IIII", s, 8)
        if name == ".text":
            return raw, rsize, va + IMAGE_BASE
    raise SystemExit("no .text section")


def main():
    if not os.path.exists(EXE):
        raise SystemExit("exe not found: %s" % EXE)
    data = open(EXE, "rb").read()
    raw, size, base = text_section(data)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    code = data[raw: raw + size]
    print("exe %.1f MB   .text VA 0x%08X  %d bytes" % (
        len(data) / 1e6, base, size))
    print("hunting SetArea/SetSize sites carrying BOTH %d and %d within %d "
          "instructions\n" % (WANT_W, WANT_H, BACK))

    # ⛔ DO NOT LINEAR-SWEEP .text WITH ONE md.disasm() CALL. It is a generator
    # that STOPS DEAD at the first undecodable byte, and .text is full of data
    # and alignment padding. The first version of this probe did exactly that,
    # got 37,426 instructions out of 6,787,072 bytes (~181 bytes per
    # instruction - impossible), and reported "0 candidates" over ~2% coverage.
    # A null from a scan that never reached the code is not a null.
    #
    # Instead: find the CALL SITES BY BYTE PATTERN first, then disassemble a
    # short window backwards from each. `call dword ptr [reg+0xDC]` must use
    # the disp32 form (0xDC as a signed disp8 would be -36), so the encoding is
    # FF /2 mod=10 -> FF (90..97) DC 00 00 00.
    sites = []
    for off, nm in SETTERS.items():
        for reg in range(8):
            if reg == 4:
                continue                      # ESP needs a SIB byte; skip
            pat = bytes([0xFF, 0x90 + reg, off, 0x00, 0x00, 0x00])
            p = 0
            while True:
                k = code.find(pat, p)
                if k < 0:
                    break
                sites.append((base + k, nm))
                p = k + 1
    sites.sort()
    print("call sites found by byte pattern: %d" % len(sites))
    if not sites:
        raise SystemExit("POSITIVE CONTROL FAILED: zero SetArea-shaped call "
                         "sites in .text. The encoding assumption is wrong; "
                         "fix the probe before reading anything into a null.")

    def back_disasm(site_va, nbytes=320):
        """Instructions ending exactly at site_va, or [] if no clean alignment."""
        start = site_va - nbytes
        if start < base:
            start = base
        for s in range(start, site_va):
            got = list(md.disasm(code[s - base: site_va - base], s))
            if got and got[-1].address + got[-1].size == site_va:
                return got
        return []

    hits = 0
    for site_va, slot in sites:
        got = back_disasm(site_va)
        if not got:
            continue
        tail = got[-BACK:]
        found = set()
        for p in tail:
            for o in p.operands:
                if o.type == capstone.x86.X86_OP_IMM:
                    v = o.imm & 0xFFFFFFFF
                    if v in (WANT_W, WANT_H):
                        found.add(v)
        if WANT_W in found and WANT_H in found:
            hits += 1
            print("\n=== CANDIDATE %d: %s call at VA 0x%08X" % (
                hits, slot, site_va))
            for p in tail:
                mark = ""
                for o in p.operands:
                    if (o.type == capstone.x86.X86_OP_IMM
                            and (o.imm & 0xFFFFFFFF) in (WANT_W, WANT_H)):
                        mark = "   <== %d" % (o.imm & 0xFFFFFFFF)
                print("   0x%08X  %-8s %s%s" % (p.address, p.mnemonic,
                                                p.op_str, mark))
    print("\n%d candidate site(s) of %d call site(s) examined."
          % (hits, len(sites)))
    if hits == 0:
        # A silent zero here reads exactly like "the constant is not in the
        # exe", which is NOT what a null from this probe means.
        print("NULL IS NOT EVIDENCE: the box may be sized from a struct field, "
              "from art dimensions, or by a helper that takes w/h as ARGS. "
              "Widen --window, or try --w/--h of the 1x design, before "
              "concluding anything.")
    return 0


sys.exit(main())
