r"""pe.py - offline helpers for the W-ToolTip unit (SimCity 4 Deluxe 1.1.641.0 Steam exe).

Read-only. Loads the exe once, exposes:
  EXE, IMG (bytes), BASE, sections, va2off(va), rd(va,n), u32(va), dis(va, n_ins or end), in_text(va)
  find_bytes(pattern) -> list of VAs
  xrefs_imm32(value) -> VAs of every occurrence of the dword in .text (raw byte scan)
"""
import struct, capstone, pefile

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
_pe = pefile.PE(EXE, fast_load=True)
BASE = _pe.OPTIONAL_HEADER.ImageBase
IMG = open(EXE, "rb").read()
SECS = []
for s in _pe.sections:
    SECS.append((s.Name.rstrip(b"\0").decode(), BASE + s.VirtualAddress, s.Misc_VirtualSize,
                 s.PointerToRawData, s.SizeOfRawData))

def sec_of(va):
    for n, v, vs, ro, rs in SECS:
        if v <= va < v + max(vs, rs):
            return n
    return None

def va2off(va):
    for n, v, vs, ro, rs in SECS:
        if v <= va < v + rs:
            return ro + (va - v)
    return None

def off2va(off):
    for n, v, vs, ro, rs in SECS:
        if ro <= off < ro + rs:
            return v + (off - ro)
    return None

def rd(va, n):
    o = va2off(va)
    return IMG[o:o + n] if o is not None else None

def u32(va):
    b = rd(va, 4)
    return struct.unpack("<I", b)[0] if b and len(b) == 4 else None

TEXT = [s for s in SECS if s[0] == ".text"][0]
def in_text(va):
    return TEXT[1] <= va < TEXT[1] + TEXT[2]

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = False

def dis(va, count=40, end=None, stop_ret=False):
    """list of (addr, mnemonic, op_str, bytes)"""
    out = []
    code = rd(va, 0x2000 if end is None else end - va)
    for i in MD.disasm(code, va):
        out.append((i.address, i.mnemonic, i.op_str, bytes(i.bytes)))
        if end is None and len(out) >= count:
            break
        if stop_ret and i.mnemonic == "ret":
            break
    return out

def pdis(va, count=40, end=None, stop_ret=False, file=None):
    for a, m, o, b in dis(va, count, end, stop_ret):
        print("  %08X  %-24s %s %s" % (a, b.hex(), m, o), file=file)

def find_bytes(pat, sec=None):
    res = []
    i = IMG.find(pat)
    while i >= 0:
        va = off2va(i)
        if va is not None and (sec is None or sec_of(va) == sec):
            res.append(va)
        i = IMG.find(pat, i + 1)
    return res

def xrefs_imm32(value, sec=".text"):
    return find_bytes(struct.pack("<I", value), sec)

def vtable(va, maxn=400):
    """read consecutive in-.text pointers starting at va"""
    out = []
    for k in range(maxn):
        p = u32(va + 4 * k)
        if p is None or not in_text(p):
            break
        out.append(p)
    return out
