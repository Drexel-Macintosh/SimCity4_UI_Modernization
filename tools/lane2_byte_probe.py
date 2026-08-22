#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LANE 2 adversarial verify - step 2: the BYTES, independently.

Written from scratch against the shipped exe. Does NOT import or trust
gate_ordinance_namex.py or ordinance_namex_verify_probe.py.

POSITIVE CONTROLS (stated up front; every null below is void without them):
  C1  read path      - the byte at 0x0077CC23 must be 0x6A and at +1 0x44,
                       which is the value v2.73.3 already ships a patch for.
  C2  branch scanner - the raw-byte branch scan must re-find every branch
                       target that a LINEAR capstone disassembly of the
                       enclosing function actually produces. If the scan
                       cannot see known branches it cannot prove "none".
  C3  emulator       - a DELIBERATELY WRONG replacement (disp 0x3C instead of
                       0x38 on the final push) must FAIL the arg comparison.
                       If a known-bad build passes, the comparison is blind.
Read-only. Writes nothing.
"""
import io, os, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

# ---- the spec's numbers, transcribed by hand from the patch text ----------
SITE_INCOME, SITE_EXPENSE = 0x0077CBFC, 0x0077D0B9
LEN = 43
IMMOFF = 34
PER_SITE_INCOME, PER_SITE_EXPENSE = 0x77CC23, 0x77D0E0   # v2.73.3 imm8 sites

STOCK_INCOME = bytes([
    0x8B,0x56,0x10, 0x6A,0x66, 0x6A,0x55, 0x6A,0x44,
    0x68,0x05,0xD3,0x85,0xEA, 0x89,0x54,0x24,0x24, 0x8B,0x10,
    0x6A,0x00, 0x8B,0xC8, 0xFF,0x52,0x1C, 0x8B,0x4C,0x24,0x28,
    0x50, 0x8B,0x86,0x98,0x00,0x00,0x00, 0x50, 0x6A,0x44, 0x55, 0x51])
STOCK_EXPENSE = bytes([
    0x8B,0x4E,0x10, 0x8B,0x10, 0x6A,0x66, 0x6A,0x55, 0x6A,0x44,
    0x68,0x05,0xD3,0x85,0xEA, 0x89,0x4C,0x24,0x24,
    0x6A,0x00, 0x8B,0xC8, 0xFF,0x52,0x1C, 0x8B,0x4C,0x24,0x28,
    0x50, 0x8B,0x86,0x9C,0x00,0x00,0x00, 0x50, 0x6A,0x44, 0x55, 0x51])

def repl_income(imm, lastdisp=0x38):
    return bytes([
        0x8B,0x56,0x10,
        0x6A,0x66, 0x6A,0x55, 0x6A,0x44,
        0x68,0x05,0xD3,0x85,0xEA,
        0x89,0x54,0x24,0x24,
        0x8B,0x10,
        0x6A,0x00,
        0x91,
        0xFF,0x52,0x1C,
        0x50,
        0xFF,0xB6,0x98,0x00,0x00,0x00,
        0x68]) + struct.pack("<I", imm) + bytes([
        0x55,
        0xFF,0x74,0x24,lastdisp])

def repl_expense(imm, lastdisp=0x38):
    return bytes([
        0x8B,0x4E,0x10,
        0x8B,0x10,
        0x6A,0x66, 0x6A,0x55, 0x6A,0x44,
        0x68,0x05,0xD3,0x85,0xEA,
        0x89,0x4C,0x24,0x24,
        0x6A,0x00,
        0x91,
        0xFF,0x52,0x1C,
        0x50,
        0xFF,0xB6,0x9C,0x00,0x00,0x00,
        0x68]) + struct.pack("<I", imm) + bytes([
        0x55,
        0xFF,0x74,0x24,lastdisp])

FAIL = []
def bad(msg):
    FAIL.append(msg)
    print("  *** BLOCKER: " + msg)

# --------------------------------------------------------------- PE load
def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs, off = [], pe + 24 + opt
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
print("exe %d bytes, %d sections" % (len(data), len(secs)))
if len(data) != 7876608:
    bad("exe size %d != 7876608" % len(data))

md = Cs(CS_ARCH_X86, CS_MODE_32)

# ================================================== C1 read-path control
b = data[va2off(secs, PER_SITE_INCOME):va2off(secs, PER_SITE_INCOME)+3]
c1 = (b[0] == 0x6A and b[1] == 0x44)
print("\nC1 read-path control: bytes at 0x%08X = %s -> %s"
      % (PER_SITE_INCOME, b.hex(" "), "PASS" if c1 else "FAIL"))
if not c1:
    bad("read path control failed - every byte finding below is void")

# ================================================== 1. stock bytes
print("\n" + "=" * 74)
print("1. STOCK BYTES AT THE TWO WINDOWS (read from the shipped exe)")
print("=" * 74)
windows = [("income",  SITE_INCOME,  STOCK_INCOME,  PER_SITE_INCOME,  repl_income),
           ("expense", SITE_EXPENSE, STOCK_EXPENSE, PER_SITE_EXPENSE, repl_expense)]
live = {}
for name, site, claimed, persite, mk in windows:
    o = va2off(secs, site)
    got = data[o:o+LEN]
    live[name] = got
    ok = (got == claimed)
    print("%-8s VA 0x%08X  file off 0x%06X" % (name, site, o))
    print("   live  : " + got.hex(" "))
    print("   spec  : " + claimed.hex(" "))
    print("   match : %s   (%d bytes claimed, %d read)" % ("YES" if ok else "NO", len(claimed), len(got)))
    if not ok:
        bad("%s stock bytes do not match the spec's quoted array" % name)
    # the per-site VA must be window+39 and hold 6a 44
    if persite - site != 39:
        bad("%s per-site VA is window+%d, spec says +39" % (name, persite - site))
    if got[39:41] != bytes([0x6A, 0x44]):
        bad("%s window+39 is %s not 6a 44" % (name, got[39:41].hex(" ")))

# ================================================== 2. lengths + imm slot
print("\n" + "=" * 74)
print("2. REPLACEMENT LENGTH / IMM PLACEMENT")
print("=" * 74)
for f in (2.5, 3.0):
    x = int(round(68 * f))
    for name, site, claimed, persite, mk in windows:
        r = mk(x)
        okl = len(r) == LEN
        oki = (r[IMMOFF-1] == 0x68) and (struct.unpack_from("<I", r, IMMOFF)[0] == x)
        print("f=%.2f x=%3d  %-8s len=%d(%s)  repl[%d]=0x%02X imm=%d (%s)"
              % (f, x, name, len(r), "OK" if okl else "BAD", IMMOFF-1, r[IMMOFF-1],
                 struct.unpack_from("<I", r, IMMOFF)[0], "OK" if oki else "BAD"))
        if not okl: bad("%s replacement is %d bytes, stock is %d" % (name, len(r), LEN))
        if not oki: bad("%s imm32 is not immediately after its 0x68 opcode" % name)
print("lround(68*3.0)=%d  -> imm32 bytes %s  (spec quoted 68 CC 00 00 00)"
      % (204, struct.pack("<I", 204).hex(" ")))

# ================================================== 3. decode coverage
print("\n" + "=" * 74)
print("3. DECODE COVERAGE - every byte consumed, no straddle")
print("=" * 74)
def decode(blob, va, label):
    tot, insns = 0, []
    for i in md.disasm(blob, va):
        insns.append(i); tot += i.size
    print("  %-26s %d insns, %d/%d bytes" % (label, len(insns), tot, len(blob)))
    if tot != len(blob):
        bad("%s decode covers %d of %d bytes" % (label, tot, len(blob)))
    return insns

for name, site, claimed, persite, mk in windows:
    print("-- %s stock --" % name)
    si = decode(live[name], site, "%s stock" % name)
    for i in si: print("     0x%08X  %-6s %s" % (i.address, i.mnemonic, i.op_str))
    print("-- %s replacement f=3.0 --" % name)
    ri = decode(mk(204), site, "%s repl" % name)
    for i in ri: print("     0x%08X  %-6s %s" % (i.address, i.mnemonic, i.op_str))

# ================================================== 4. what follows
print("\n" + "=" * 74)
print("4. THE INSTRUCTIONS IMMEDIATELY AFTER EACH WINDOW (liveness of eax/ecx/edx)")
print("=" * 74)
for name, site, claimed, persite, mk in windows:
    o = va2off(secs, site + LEN)
    print("-- after %s (0x%08X) --" % (name, site + LEN))
    for i in list(md.disasm(data[o:o+80], site + LEN))[:12]:
        print("     0x%08X  %-6s %s" % (i.address, i.mnemonic, i.op_str))

# ================================================== 5. branch scan
print("\n" + "=" * 74)
print("5. BRANCH TARGETS LANDING INSIDE EITHER WINDOW")
print("=" * 74)
def scan_branch_targets():
    """Raw byte scan of .text for every rel8/rel32 control transfer.
    Over-approximates (decodes at non-instruction offsets too) - the SAFE
    direction when looking for 'does anything land inside'."""
    out = []
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"): continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff+rsize]
        L = len(blob)
        for i in range(L - 6):
            op = blob[i]
            if op in (0xE8, 0xE9):
                rel = struct.unpack_from("<i", blob, i+1)[0]
                out.append((base+i, base+i+5+rel))
            elif op == 0x0F and 0x80 <= blob[i+1] <= 0x8F:
                rel = struct.unpack_from("<i", blob, i+2)[0]
                out.append((base+i, base+i+6+rel))
            elif 0x70 <= op <= 0x7F or op in (0xEB, 0xE3, 0xE0, 0xE1, 0xE2):
                rel = struct.unpack_from("<b", blob, i+1)[0]
                out.append((base+i, base+i+2+rel))
    return out

targets = scan_branch_targets()
print("  raw scan produced %d candidate branch edges in .text" % len(targets))

# ---- C2 control: linear disassembly of the enclosing function must be a
# ---- subset of the raw scan.
FN = 0x0077C660
ofn = va2off(secs, FN)
lin = []
for i in md.disasm(data[ofn:ofn+0x1200], FN):
    if i.mnemonic.startswith("j") or i.mnemonic == "call" or i.mnemonic.startswith("loop"):
        s = i.op_str
        if s.startswith("0x"):
            try: lin.append((i.address, int(s, 16)))
            except ValueError: pass
tset = set(targets)
missing = [e for e in lin if e not in tset]
print("  C2 branch-scanner control: linear disasm of sub_%06X produced %d "
      "branch edges; raw scan is missing %d of them -> %s"
      % (FN, len(lin), len(missing), "PASS" if not missing and lin else "FAIL"))
if not lin or missing:
    bad("branch scanner control failed (%d linear edges, %d unseen) - "
        "'no branch inside' would be a blind null" % (len(lin), len(missing)))

for name, site, claimed, persite, mk in windows:
    inside = sorted(set(t for (s, t) in targets if site < t < site + LEN))
    print("  %-8s window [0x%08X,0x%08X): %d branch target(s) strictly inside%s"
          % (name, site, site + LEN, len(inside),
             (" -> " + ", ".join(hex(t) for t in inside)) if inside else ""))
    if inside:
        bad("%s window has %d branch target(s) inside" % (name, len(inside)))
    # also: a branch target EXACTLY at window start is fine (boundary preserved)
    at_start = [s for (s, t) in targets if t == site]
    print("           (%d edge(s) target the window START - harmless, boundary kept)"
          % len(at_start))

# ================================================== 6. absolute refs
print("\n" + "=" * 74)
print("6. ABSOLUTE DWORDS ANYWHERE IN THE IMAGE POINTING INSIDE A WINDOW")
print("=" * 74)
for name, site, claimed, persite, mk in windows:
    hits = []
    for v in range(site + 1, site + LEN):
        pat = struct.pack("<I", v)
        st = 0
        while True:
            k = data.find(pat, st)
            if k < 0: break
            hits.append((k, v)); st = k + 1
            if len(hits) > 40: break
        if len(hits) > 40: break
    print("  %-8s: %d absolute dword(s) equal to an address inside the window"
          % (name, len(hits)))
    for k, v in hits[:10]:
        print("       file off 0x%06X -> 0x%08X" % (k, v))
    if hits:
        print("       (NOTE: whole-image byte scan; most will be coincidental data)")

# ================================================== 7. UNICORN equivalence
print("\n" + "=" * 74)
print("7. UNICORN: stock vs replacement - the ten pushed dwords and net ESP")
print("=" * 74)
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL
from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_ECX,
                               UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EBP,
                               UC_X86_REG_EBX, UC_X86_REG_EDI)

CODE = 0x00700000
STACK = 0x10000000
OBJ   = 0x20000000   # esi (the dialog/builder object)
TXT   = 0x21000000   # eax (the string/text object) -> [eax] = VTBL
VTBL  = 0x22000000
STUB  = 0x23000000

PARENT   = 0xA1A1A1A1
YINCOME  = 0xB1B1B1B1
YEXPENSE = 0xB2B2B2B2
IDVAL    = 0xC1C1C1C1
ECX_IN   = 0xD1D1D1D1
RETVAL   = 0xCAFEBABE

def run(blob, va):
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    for b_, sz in ((CODE, 0x10000), (STACK, 0x200000), (OBJ, 0x10000),
                   (TXT, 0x10000), (VTBL, 0x10000), (STUB, 0x10000)):
        mu.mem_map(b_, sz, UC_PROT_ALL)
    page = va & ~0xFFF
    mu.mem_map(page, 0x10000, UC_PROT_ALL)
    mu.mem_write(va, bytes(blob))
    # poison the whole stack with per-dword unique values so a wrong
    # displacement CANNOT accidentally read the right value
    top = STACK + 0x100000
    poison = b"".join(struct.pack("<I", 0x5A000000 | ((top - 0x20000 + 4*i) & 0xFFFFF))
                      for i in range(0x10000))
    mu.mem_write(STACK + 0x80000, poison[:0x40000])
    esp = STACK + 0x100000
    mu.mem_write(OBJ + 0x10, struct.pack("<I", PARENT))
    mu.mem_write(OBJ + 0x98, struct.pack("<I", YINCOME))
    mu.mem_write(OBJ + 0x9C, struct.pack("<I", YEXPENSE))
    mu.mem_write(TXT, struct.pack("<I", VTBL))
    mu.mem_write(VTBL + 0x1C, struct.pack("<I", STUB))
    # stub: mov eax, RETVAL ; ret   (thiscall, 0 args, pops nothing)
    mu.mem_write(STUB, b"\xB8" + struct.pack("<I", RETVAL) + b"\xC3")
    mu.reg_write(UC_X86_REG_ESP, esp)
    mu.reg_write(UC_X86_REG_ESI, OBJ)
    mu.reg_write(UC_X86_REG_EAX, TXT)
    mu.reg_write(UC_X86_REG_ECX, ECX_IN)
    mu.reg_write(UC_X86_REG_EDX, 0xDEADDEAD)
    mu.reg_write(UC_X86_REG_EBP, IDVAL)
    mu.emu_start(va, va + len(blob))
    end = mu.reg_read(UC_X86_REG_ESP)
    n = (esp - end) // 4
    args = [struct.unpack("<I", mu.mem_read(end + 4*k, 4))[0] for k in range(n)]
    return args, esp - end

for name, site, claimed, persite, mk in windows:
    a_s, d_s = run(live[name], site)
    a_r, d_r = run(mk(204), site)
    print("-- %s --" % name)
    print("   stock : net ESP -%d, %d dwords" % (d_s, len(a_s)))
    print("           " + " ".join("%08X" % v for v in a_s))
    print("   repl  : net ESP -%d, %d dwords" % (d_r, len(a_r)))
    print("           " + " ".join("%08X" % v for v in a_r))
    diffs = [k for k in range(min(len(a_s), len(a_r))) if a_s[k] != a_r[k]]
    print("   differing slots (0=arg1 ... 9=arg10): %s" % diffs)
    if d_s != 40 or d_r != 40:
        bad("%s net ESP is %d/%d, expected 40 both" % (name, d_s, d_r))
    if len(a_s) != 10 or len(a_r) != 10:
        bad("%s pushed %d/%d dwords, expected 10" % (name, len(a_s), len(a_r)))
    # arg3 is the 3rd pushed-LAST i.e. index 2 from the top of the stack
    if diffs != [2]:
        bad("%s: replacement differs from stock in slots %s, expected ONLY [2] (arg3)"
            % (name, diffs))
    else:
        print("   arg3: stock %d -> repl %d   (all other nine identical)" % (a_s[2], a_r[2]))
    if a_s[0] != PARENT or a_r[0] != PARENT:
        bad("%s arg1 (parent, the spill/reload slot) is %08X/%08X not %08X"
            % (name, a_s[0], a_r[0], PARENT))

# ---- C3 emulator control: a KNOWN-BAD replacement must be caught ---------
print("\n  C3 emulator control: same block with the final push disp 0x3C "
      "instead of 0x38 (the post-decrement reading of PUSH r/m32)")
ctl_ok = True
for name, site, claimed, persite, mk in windows:
    a_s, _ = run(live[name], site)
    a_b, _ = run(mk(204, lastdisp=0x3C), site)
    d = [k for k in range(10) if a_s[k] != a_b[k]]
    print("     %-8s bad-build differing slots = %s  (arg1 = %08X vs stock %08X)"
          % (name, d, a_b[0], a_s[0]))
    if d == [2]:
        ctl_ok = False
print("     -> %s" % ("PASS (the known-bad build IS caught)" if ctl_ok
                      else "FAIL - a known-bad build passes; the check is blind"))
if not ctl_ok:
    bad("emulator control failed: a wrong displacement is not detected")

print("\n" + "=" * 74)
if FAIL:
    print("RESULT: %d BLOCKER(S)" % len(FAIL))
    for m in FAIL: print("  - " + m)
    sys.exit(1)
print("RESULT: byte-level checks GREEN")
sys.exit(0)
