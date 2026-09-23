"""Independent offline reader for SimCity 4.exe (1.1.641 Steam). READ ONLY.
Written by the W-FlatRect VERIFIER: deliberately does NOT import the finder's pe.py
(hand-parses the PE headers with struct instead of pefile, so a pefile quirk
cannot corroborate itself)."""
import struct, capstone

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
RAW = open(EXE, "rb").read()

e_lfanew = struct.unpack_from("<I", RAW, 0x3C)[0]
assert RAW[e_lfanew:e_lfanew + 4] == b"PE\0\0"
nsec = struct.unpack_from("<H", RAW, e_lfanew + 6)[0]
optsz = struct.unpack_from("<H", RAW, e_lfanew + 20)[0]
opt = e_lfanew + 24
BASE = struct.unpack_from("<I", RAW, opt + 28)[0]
SECS = []  # (name, va_lo, va_hi, rawptr, rawsize, vsize)
for i in range(nsec):
    o = opt + optsz + 40 * i
    name = RAW[o:o + 8].rstrip(b"\0").decode("latin1")
    vsize, vaddr, rsize, rptr = struct.unpack_from("<IIII", RAW, o + 8)
    SECS.append((name, BASE + vaddr, BASE + vaddr + max(vsize, rsize), rptr, rsize, vsize))


def sec(va):
    for s in SECS:
        if s[1] <= va < s[2]:
            return s
    return None


def secname(va):
    s = sec(va)
    return s[0] if s else None


def rd(va, n):
    s = sec(va)
    if s is None:
        raise ValueError(hex(va))
    off = va - s[1]
    out = bytearray()
    for k in range(n):
        if off + k < s[4]:
            out.append(RAW[s[3] + off + k])
        else:
            out.append(0)
    return bytes(out)


def u32(va):
    return struct.unpack("<I", rd(va, 4))[0]


def u8(va):
    return rd(va, 1)[0]


TEXT = [s for s in SECS if s[0] == ".text"][0]


def is_text(va):
    return TEXT[1] <= va < TEXT[2]


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def dis(va, n=40, stop_ret=True):
    out = []
    for ins in md.disasm(rd(va, 0x800), va):
        out.append(ins)
        if len(out) >= n:
            break
        if stop_ret and ins.mnemonic in ("ret", "retn"):
            break
    return out


def show(va, n=40, stop_ret=True):
    return "\n".join(f"  {i.address:08X}: {i.bytes.hex():<20} {i.mnemonic} {i.op_str}" for i in dis(va, n, stop_ret))


def disrange(lo, hi):
    """Linear sweep lo..hi."""
    out = []
    for ins in md.disasm(rd(lo, hi - lo + 16), lo):
        if ins.address >= hi:
            break
        out.append(ins)
    return out


def showrange(lo, hi):
    return "\n".join(f"  {i.address:08X}: {i.bytes.hex():<20} {i.mnemonic} {i.op_str}" for i in disrange(lo, hi))


def text_bytes():
    return rd(TEXT[1], TEXT[4])


def find_imm32(val, where=None):
    """Raw byte search of a 32-bit LE value in .text (or a given section)."""
    s = TEXT if where is None else [x for x in SECS if x[0] == where][0]
    blob = RAW[s[3]:s[3] + s[4]]
    pat = struct.pack("<I", val)
    hits = []
    i = blob.find(pat)
    while i >= 0:
        hits.append(s[1] + i)
        i = blob.find(pat, i + 1)
    return hits


def insn_containing(va, back_max=12):
    """Instruction that contains the 4 bytes at va, found by trying start
    offsets back_max..1 and keeping the one whose decode is consistent when
    decoding a window from further back (self-synchronising sweep)."""
    # sweep from 32 bytes back and take the instruction covering va
    for start_back in (48, 40, 32, 24, 16):
        st = va - start_back
        for ins in md.disasm(rd(st, start_back + 16), st):
            if ins.address <= va < ins.address + ins.size:
                if ins.address + ins.size >= va + 4:
                    return ins
                break
            if ins.address > va:
                break
    return None
