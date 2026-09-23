"""Minimal offline PE reader + capstone helpers for the W-Graph unit.
Reads the shipped SimCity 4.exe READ-ONLY."""
import struct, capstone, re, sys

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
data = open(EXE, 'rb').read()
e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
nsec = struct.unpack_from('<H', data, e_lfanew + 6)[0]
optsz = struct.unpack_from('<H', data, e_lfanew + 20)[0]
IMAGEBASE = struct.unpack_from('<I', data, e_lfanew + 24 + 28)[0]
secs = []
off = e_lfanew + 24 + optsz
for i in range(nsec):
    name = data[off:off + 8].rstrip(b'\0').decode()
    vsz, va, rsz, rptr = struct.unpack_from('<IIII', data, off + 8)
    secs.append((name, IMAGEBASE + va, vsz, rptr, rsz))
    off += 40

def sec_of(va):
    for s in secs:
        if s[1] <= va < s[1] + max(s[2], s[4]):
            return s
    return None

def fo(va):
    s = sec_of(va)
    if not s: return None
    d = va - s[1]
    if d >= s[4]: return None
    return s[3] + d

def rd(va, n):
    o = fo(va)
    return data[o:o + n] if o is not None else None

def u32(va):
    b = rd(va, 4)
    return struct.unpack('<I', b)[0] if b and len(b) == 4 else None

TEXT = [s for s in secs if s[0] == '.text'][0]
def is_text(va):
    return TEXT[1] <= va < TEXT[1] + TEXT[2]

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = False

def dis(va, n=0x100, stop_ret=False, maxins=10000):
    out = []
    code = rd(va, n)
    for ins in md.disasm(code, va):
        out.append(ins)
        if stop_ret and ins.mnemonic in ('ret', 'retn'):
            break
        if len(out) >= maxins: break
    return out

def pdis(va, n=0x100, stop_ret=False, file=sys.stdout):
    for ins in dis(va, n, stop_ret):
        print('  %08X  %-24s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str), file=file)

def find_bytes(pat, sec=None):
    res = []
    for s in secs:
        if sec and s[0] != sec: continue
        blob = data[s[3]:s[3] + s[4]]
        i = blob.find(pat)
        while i >= 0:
            res.append(s[1] + i)
            i = blob.find(pat, i + 1)
    return res

def vtable(va, maxn=400):
    out = []
    for i in range(maxn):
        p = u32(va + 4 * i)
        if p is None or not is_text(p): break
        out.append(p)
    return out
