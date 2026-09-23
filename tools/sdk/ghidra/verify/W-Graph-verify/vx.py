# vx.py - independent offline reader for SimCity 4.exe (W-Graph adversarial verify).
# Written from scratch for this verification; does not import the finder's pe.py.
import struct, pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

_pe = pefile.PE(EXE, fast_load=True)
BASE = _pe.OPTIONAL_HEADER.ImageBase
_data = _pe.get_memory_mapped_image()
SECTIONS = []
for s in _pe.sections:
    name = s.Name.rstrip(b"\0").decode(errors="replace")
    va = BASE + s.VirtualAddress
    size = max(s.Misc_VirtualSize, s.SizeOfRawData)
    SECTIONS.append((name, va, va + size, s.Characteristics))

def sec_of(va):
    for n, a, b, c in SECTIONS:
        if a <= va < b:
            return n
    return None

def is_exec(va):
    for n, a, b, c in SECTIONS:
        if a <= va < b:
            return bool(c & 0x20000000)
    return False

def rd(va, n):
    o = va - BASE
    return bytes(_data[o:o + n])

def u32(va):
    return struct.unpack_from("<I", _data, va - BASE)[0]

def i32(va):
    return struct.unpack_from("<i", _data, va - BASE)[0]

def u8(va):
    return _data[va - BASE]

def f32(va):
    return struct.unpack_from("<f", _data, va - BASE)[0]

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n=40, stop_at_ret=True):
    out = []
    code = rd(va, n * 16)
    for ins in md.disasm(code, va):
        out.append(ins)
        if len(out) >= n:
            break
        if stop_at_ret and ins.mnemonic in ("ret", "retn"):
            break
        if stop_at_ret and ins.mnemonic == "jmp" and ins.op_str.startswith("0x"):
            break
    return out

def one(va):
    code = rd(va, 16)
    for ins in md.disasm(code, va):
        return ins
    return None

def fmt(ins):
    return "0x%08X  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)

def dump(va, n=40, stop_at_ret=True, file=None):
    lines = [fmt(i) for i in dis(va, n, stop_at_ret)]
    s = "\n".join(lines)
    if file:
        print(s, file=file)
    else:
        print(s)
    return lines

def text_ranges():
    return [(a, b) for n, a, b, c in SECTIONS if c & 0x20000000]

def scan_dword(val):
    """every byte offset in executable sections where the little-endian dword appears."""
    pat = struct.pack("<I", val)
    hits = []
    for a, b in text_ranges():
        blob = rd(a, b - a)
        i = blob.find(pat)
        while i >= 0:
            hits.append(a + i)
            i = blob.find(pat, i + 1)
    return hits

def scan_dword_all(val):
    pat = struct.pack("<I", val)
    hits = []
    for n, a, b, c in SECTIONS:
        blob = rd(a, b - a)
        i = blob.find(pat)
        while i >= 0:
            hits.append((n, a + i))
            i = blob.find(pat, i + 1)
    return hits

def insn_covering(va, back=12):
    """find an instruction that starts at va-k and covers va (imm/disp). Returns the one whose
    decode is consistent with the subsequent stream (try linear decode from start candidates)."""
    cands = []
    for k in range(1, back + 1):
        st = va - k
        ins = one(st)
        if ins and ins.address + ins.size > va:
            cands.append(ins)
    return cands

def resolve_thunk(va, depth=0):
    """follow simple adjustor thunks: 'sub/add ecx,N ; jmp X' or 'jmp X'. Returns (final, adj, chain)."""
    chain = []
    adj = 0
    cur = va
    for _ in range(4):
        ins = dis(cur, 3, stop_at_ret=False)
        if not ins:
            break
        i0 = ins[0]
        if i0.mnemonic == "jmp" and i0.op_str.startswith("0x"):
            chain.append((cur, "jmp"))
            cur = int(i0.op_str, 16)
            continue
        if i0.mnemonic in ("sub", "add") and i0.op_str.startswith("ecx, ") and len(ins) > 1 and ins[1].mnemonic == "jmp" and ins[1].op_str.startswith("0x"):
            n = int(i0.op_str.split(", ")[1], 16)
            adj += (-n if i0.mnemonic == "sub" else n)
            chain.append((cur, "%s ecx,0x%X" % (i0.mnemonic, n)))
            cur = int(ins[1].op_str, 16)
            continue
        break
    return cur, adj, chain

def ret_n(va, maxn=400):
    """first ret found scanning linearly from va (heuristic)."""
    for ins in dis(va, maxn, stop_at_ret=False):
        if ins.mnemonic == "ret":
            return ins.op_str or "0", ins.address
    return None, None

def vtable(va, maxslots=400):
    """read consecutive dwords that point into executable sections."""
    out = []
    for k in range(maxslots):
        p = u32(va + 4 * k)
        if not is_exec(p):
            break
        out.append(p)
    return out
