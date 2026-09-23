"""Minimal offline reader for SimCity 4.exe (1.1.641 Steam). READ ONLY.
Shared helpers for the B-second-class-exe-decode unit."""
import struct, pefile, capstone

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

_pe = pefile.PE(EXE, fast_load=True)
BASE = _pe.OPTIONAL_HEADER.ImageBase
IMG = _pe.get_memory_mapped_image()
SECTIONS = []
for s in _pe.sections:
    name = s.Name.rstrip(b"\0").decode()
    SECTIONS.append((name, BASE + s.VirtualAddress, BASE + s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData)))
TEXT = [x for x in SECTIONS if x[0] == ".text"][0]

def sec_of(va):
    for n, a, b in SECTIONS:
        if a <= va < b:
            return n
    return None

def is_code(va):
    return TEXT[1] <= va < TEXT[2]

def rd(va, n):
    o = va - BASE
    return IMG[o:o + n]

def u32(va):
    return struct.unpack("<I", rd(va, 4))[0]

def vtable(va, maxn=400):
    """Entries until the first non-.text pointer."""
    out = []
    for i in range(maxn):
        p = u32(va + 4 * i)
        if not is_code(p):
            break
        out.append(p)
    return out

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = False

def dis(va, maxins=80, stop_at_ret=True, maxbytes=0x600):
    code = rd(va, maxbytes)
    lines = []
    for ins in md.disasm(code, va):
        lines.append(ins)
        if len(lines) >= maxins:
            break
        if stop_at_ret and ins.mnemonic in ("ret", "retn"):
            break
        if stop_at_ret and ins.mnemonic == "jmp" and ins.op_str.startswith(("dword ptr [e", "0x")) and False:
            break
    return lines

def fmt(lines):
    return "\n".join(f"  {i.address:08X}: {i.mnemonic} {i.op_str}" for i in lines)

def dis_fn(va, maxins=300, maxbytes=0x1200):
    """Linear sweep that follows forward branches: stop when we hit a ret and
    no pending forward branch target lies beyond it."""
    code = rd(va, maxbytes)
    out = []
    far = va
    for ins in md.disasm(code, va):
        out.append(ins)
        if len(out) >= maxins:
            break
        m = ins.mnemonic
        if (m.startswith("j") or m == "call") and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16)
            if m != "call" and va <= t < va + maxbytes and t > far:
                far = t
        if m in ("ret", "retn") or (m == "jmp" and not ins.op_str.startswith("0x")) or (m == "jmp" and ins.op_str.startswith("0x") and (int(ins.op_str,16) < va or int(ins.op_str,16) >= va+maxbytes)):
            if ins.address + ins.size > far:
                break
    return out

def retn_of(va):
    """The 'ret N' arg-byte count of a function (first ret found by forward-follow)."""
    for i in dis_fn(va):
        if i.mnemonic in ("ret", "retn"):
            return int(i.op_str, 16) if i.op_str else 0
    return None
