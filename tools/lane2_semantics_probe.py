#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LANE 2 adversarial verify - step 3: does arg3 actually mean X, and is
anything ELSE in that arg list a 1x-baked size that this fix leaves behind?

POSITIVE CONTROL: the disassembly must show sub_779660 ending in `ret 0x28`
(10 dword args) - a figure the caller side independently proves by pushing
exactly 10 dwords. Two INDEPENDENT failure modes, so their agreement counts.
Read-only.
"""
import struct, sys, re, io, os, glob
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
ROOT = r"<HOME>\OneDrive\Projects\Surface 1 Project\1 Completed Projects\SC4TouchControls"
IMAGE_BASE = 0x400000
FN = 0x00779660

def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs, off = [], pe + 24 + opt
    for _ in range(nsec):
        n = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize)); off += 40
    return data, secs

def va2off(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            return roff + (rva - sva)
    return None

data, secs = load()
md = Cs(CS_ARCH_X86, CS_MODE_32)

print("=" * 74)
print("A. sub_779660 - the callee. thiscall: arg1=[esp+4] .. arg10=[esp+0x28]")
print("   (prologue-relative; watch for a `sub esp,N` shifting the frame)")
print("=" * 74)
o = va2off(secs, FN)
blob = data[o:o+0x600]
insns = list(md.disasm(blob, FN))
esp_adj = 0
saved = 0
ARGNAME = {}
ret_found = None
for i in insns[:170]:
    note = ""
    m = re.search(r"\[esp \+ 0x([0-9a-f]+)\]", i.op_str)
    if m:
        d = int(m.group(1), 16)
        eff = d - (esp_adj + saved)
        if eff >= 4 and eff % 4 == 0 and eff <= 0x28:
            note = "   <<< ARG%d" % (eff // 4)
    if i.mnemonic == "push":
        saved += 4
    elif i.mnemonic == "pop":
        saved -= 4
    elif i.mnemonic == "sub" and i.op_str.startswith("esp,"):
        esp_adj += int(i.op_str.split(",")[1].strip(), 16)
    elif i.mnemonic == "add" and i.op_str.startswith("esp,"):
        esp_adj -= int(i.op_str.split(",")[1].strip(), 16)
    print("  0x%08X  %-7s %s%s" % (i.address, i.mnemonic, i.op_str, note))
    if i.mnemonic == "ret":
        ret_found = i.op_str
        break

print("\n  ret operand: %r  -> %s dwords popped" %
      (ret_found, int(ret_found, 16)//4 if ret_found else "?"))
ctl = (ret_found == "0x28")
print("  POSITIVE CONTROL (callee ret 0x28 == 10 args, matching the 10 caller "
      "pushes measured independently): %s" % ("PASS" if ctl else "FAIL"))

print("\n" + "=" * 74)
print("B. OTHER CALLERS of sub_779660 - what x values do they pass as arg3?")
print("   (if arg3 is X, siblings should pass a spread of plausible x's;")
print("    if it is a constant everywhere it is probably NOT x)")
print("=" * 74)
callers = []
for n, sva, vsize, roff, rsize in secs:
    if not n.startswith(".text"): continue
    base = IMAGE_BASE + sva
    b = data[roff:roff+rsize]
    for i in range(len(b)-5):
        if b[i] != 0xE8: continue
        rel = struct.unpack_from("<i", b, i+1)[0]
        if base + i + 5 + rel == FN:
            callers.append(base + i)
print("  %d call sites" % len(callers))
for c in callers:
    # walk back 60 bytes and decode forward to find the last 10 pushes
    start = c - 70
    oo = va2off(secs, start)
    seq = [x for x in md.disasm(data[oo:oo+80], start) if x.address < c]
    pushes = [x for x in seq if x.mnemonic in ("push",)]
    pv = [x.op_str for x in pushes][-10:]
    arg3 = pv[-3] if len(pv) >= 3 else "?"
    print("  call @0x%08X   arg3=%-22s | args(1..10 rev)=%s"
          % (c, arg3, ",".join(reversed(pv))))

print("\n" + "=" * 74)
print("C. SOURCE-WIDE SCAN: does anything in src/ address a byte inside either")
print("   43-byte window other than the two sites being moved?")
print("=" * 74)
W = [(0x0077CBFC, 43, "income"), (0x0077D0B9, 43, "expense")]
pat = re.compile(r"0[xX]([0-9a-fA-F]{5,8})\b")
hits, scanned, control_hits = [], 0, []
for p in sorted(glob.glob(os.path.join(ROOT, "src", "*.cpp")) +
                glob.glob(os.path.join(ROOT, "src", "*.h"))):
    txt = io.open(p, "r", encoding="utf-8", errors="replace").read()
    scanned += 1
    for m in pat.finditer(txt):
        v = int(m.group(1), 16)
        ln = txt[:m.start()].count("\n") + 1
        for s, l, nm in W:
            if s <= v < s + l:
                hits.append((os.path.basename(p), ln, hex(v), nm,
                             txt.split("\n")[ln-1].strip()[:100]))
        if v in (0x77CC23, 0x77D0E0):
            control_hits.append((os.path.basename(p), ln, hex(v)))
print("  scanned %d files" % scanned)
for h in hits:
    print("   %-26s line %-5d %-10s in %-8s | %s" % h)
print("  POSITIVE CONTROL (the same regex must locate the two KNOWN literals "
      "0x77CC23 / 0x77D0E0): %d hit(s) -> %s"
      % (len(control_hits), "PASS" if len(control_hits) >= 2 else "FAIL"))
for h in control_hits:
    print("     %-26s line %-5d %s" % h)
inside_other = [h for h in hits if h[2].lower() not in ("0x77cc23", "0x77d0e0")]
print("  literals inside a window OTHER than the two being moved: %d" % len(inside_other))
sys.exit(0 if (ctl and len(control_hits) >= 2) else 1)
