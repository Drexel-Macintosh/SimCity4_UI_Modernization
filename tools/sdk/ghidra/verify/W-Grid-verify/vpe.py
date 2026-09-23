# W-Grid-verify: independent read-only PE helper (does NOT reuse the finder's pe.py).
# Reads SimCity 4.exe offline; never writes to it.
import struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

class PE:
    def __init__(self, path=EXE):
        self.data = open(path, 'rb').read()
        d = self.data
        e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
        assert d[e_lfanew:e_lfanew+4] == b'PE\0\0'
        nsec = struct.unpack_from('<H', d, e_lfanew+6)[0]
        optsz = struct.unpack_from('<H', d, e_lfanew+20)[0]
        opt = e_lfanew + 24
        self.imagebase = struct.unpack_from('<I', d, opt+28)[0]
        self.secs = []
        so = opt + optsz
        for i in range(nsec):
            name = d[so:so+8].rstrip(b'\0').decode('latin1')
            vsize, vaddr, rsize, rptr = struct.unpack_from('<IIII', d, so+8)
            chars = struct.unpack_from('<I', d, so+36)[0]
            self.secs.append((name, self.imagebase+vaddr, vsize, rptr, rsize, chars))
            so += 40
        self.md = Cs(CS_ARCH_X86, CS_MODE_32)
        self.md.detail = False

    def sec_of(self, va):
        for s in self.secs:
            if s[1] <= va < s[1] + max(s[2], s[4]):
                return s
        return None

    def off(self, va):
        s = self.sec_of(va)
        if not s: return None
        o = va - s[1]
        if o >= s[4]: return None
        return s[3] + o

    def va_of_off(self, o):
        for s in self.secs:
            if s[3] <= o < s[3] + s[4]:
                return s[1] + (o - s[3])
        return None

    def read(self, va, n):
        o = self.off(va)
        return self.data[o:o+n]

    def u32(self, va):
        return struct.unpack('<I', self.read(va, 4))[0]

    def i32(self, va):
        return struct.unpack('<i', self.read(va, 4))[0]

    def is_code(self, va):
        s = self.sec_of(va)
        return bool(s) and (s[5] & 0x20000000) != 0  # IMAGE_SCN_MEM_EXECUTE

    def cstr(self, va, maxn=256):
        b = self.read(va, maxn)
        i = b.find(b'\0')
        return b[:i].decode('latin1') if i >= 0 else b.decode('latin1')

    def dis(self, va, n=64, stop_at_ret=True, maxbytes=0x4000):
        code = self.read(va, maxbytes)
        out = []
        for ins in self.md.disasm(code, va):
            out.append(ins)
            if stop_at_ret and ins.mnemonic in ('ret', 'retn'):
                break
            if len(out) >= n:
                break
        return out

    def dis_text(self, va, n=64, stop_at_ret=True):
        return '\n'.join('%08X: %-24s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str)
                         for i in self.dis(va, n, stop_at_ret))

    def text(self):
        for s in self.secs:
            if s[0] == '.text':
                return s
        raise KeyError('.text')

    def find_bytes(self, pat, sec_name=None):
        """all VAs where raw bytes pat occur (optionally within one section)"""
        res = []
        for s in self.secs:
            if sec_name and s[0] != sec_name: continue
            blob = self.data[s[3]:s[3]+s[4]]
            start = 0
            while True:
                i = blob.find(pat, start)
                if i < 0: break
                res.append(s[1] + i)
                start = i + 1
        return res

    def xrefs_imm32(self, value, sec_name='.text'):
        return self.find_bytes(struct.pack('<I', value), sec_name)

    def call_targets_to(self, target):
        """E8 rel32 call sites to target (in .text)"""
        s = self.text()
        blob = self.data[s[3]:s[3]+s[4]]
        res = []
        for m in re.finditer(b'\xE8', blob):
            i = m.start()
            if i + 5 > len(blob): break
            rel = struct.unpack_from('<i', blob, i+1)[0]
            va = s[1] + i
            if va + 5 + rel == target:
                res.append(va)
        return res

    def jmp_targets_to(self, target):
        s = self.text()
        blob = self.data[s[3]:s[3]+s[4]]
        res = []
        for m in re.finditer(b'\xE9', blob):
            i = m.start()
            if i + 5 > len(blob): break
            rel = struct.unpack_from('<i', blob, i+1)[0]
            va = s[1] + i
            if va + 5 + rel == target:
                res.append(va)
        return res

    def vtable(self, va, n):
        return [self.u32(va + 4*i) for i in range(n)]

    def vtable_walk(self, va, maxn=400):
        """entries while they point into executable sections"""
        out = []
        for i in range(maxn):
            v = self.u32(va + 4*i)
            if not self.is_code(v):
                break
            out.append(v)
        return out

def ret_n(pe, va, maxins=3000):
    """Linear sweep from va collecting ret imm values until first ret; also returns the instruction list.
    NOTE: linear, so a function that has an early ret returns that one (all rets in one fn share N under stdcall/thiscall)."""
    ins = pe.dis(va, maxins, stop_at_ret=True)
    last = ins[-1] if ins else None
    if last is not None and last.mnemonic in ('ret', 'retn'):
        n = int(last.op_str, 0) if last.op_str else 0
        return n, ins
    return None, ins

if __name__ == '__main__':
    pe = PE()
    print(hex(pe.imagebase))
    for s in pe.secs:
        print(s[0], hex(s[1]), hex(s[2]), hex(s[3]), hex(s[4]), hex(s[5]))
