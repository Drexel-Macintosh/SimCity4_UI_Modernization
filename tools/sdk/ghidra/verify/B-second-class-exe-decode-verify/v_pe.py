# Independent PE reader for the verifier (does NOT import the finder's pe.py).
import struct, os
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
            vsize, va, rawsz, rawptr = struct.unpack_from('<IIII', d, so+8)
            ch = struct.unpack_from('<I', d, so+36)[0]
            self.secs.append((name, self.imagebase+va, vsize, rawptr, rawsz, ch))
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
        if s is None: return None
        o = va - s[1]
        if o >= s[4]: return None
        return s[3] + o

    def is_code(self, va):
        s = self.sec_of(va)
        return s is not None and (s[5] & 0x20000000) != 0  # IMAGE_SCN_MEM_EXECUTE

    def u32(self, va):
        o = self.off(va)
        return struct.unpack_from('<I', self.data, o)[0]

    def bytes(self, va, n):
        o = self.off(va)
        return self.data[o:o+n]

    def dis(self, va, n=64, maxins=None):
        out = []
        for ins in self.md.disasm(self.bytes(va, n), va):
            out.append(ins)
            if maxins and len(out) >= maxins: break
        return out

    def dis_until_ret(self, va, maxbytes=0x400):
        out = []
        for ins in self.md.disasm(self.bytes(va, maxbytes), va):
            out.append(ins)
            if ins.mnemonic in ('ret', 'retn'): break
        return out

    def fmt(self, ins_list):
        return '\n'.join('  %08X  %-8s %s' % (i.address, i.mnemonic, i.op_str) for i in ins_list)

if __name__ == '__main__':
    p = PE()
    print('imagebase %08X size %d' % (p.imagebase, len(p.data)))
    for s in p.secs:
        print('%-8s va %08X vsz %08X raw %08X rawsz %08X ch %08X' % s)
