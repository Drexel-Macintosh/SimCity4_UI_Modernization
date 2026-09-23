# Independent offline PE reader + capstone helpers for the W-ToolTip verifier.
# Written from scratch (does not import the finder's pe.py).
import struct, sys
import capstone

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

class PE:
    def __init__(self, path=EXE):
        self.data = open(path, 'rb').read()
        d = self.data
        e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
        assert d[e_lfanew:e_lfanew+4] == b'PE\0\0'
        coff = e_lfanew + 4
        self.nsec = struct.unpack_from('<H', d, coff+2)[0]
        optsz = struct.unpack_from('<H', d, coff+16)[0]
        opt = coff + 20
        self.imagebase = struct.unpack_from('<I', d, opt+28)[0]
        sec = opt + optsz
        self.sections = []
        for i in range(self.nsec):
            o = sec + i*40
            name = d[o:o+8].rstrip(b'\0').decode('latin1')
            vsize, va, rawsize, rawptr = struct.unpack_from('<IIII', d, o+8)
            chars = struct.unpack_from('<I', d, o+36)[0]
            self.sections.append(dict(name=name, va=self.imagebase+va, vsize=vsize,
                                      rawsize=rawsize, rawptr=rawptr, chars=chars))
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.md.detail = True

    def sec_of(self, va):
        for s in self.sections:
            if s['va'] <= va < s['va'] + max(s['vsize'], s['rawsize']):
                return s
        return None

    def off(self, va):
        s = self.sec_of(va)
        if s is None:
            return None
        o = va - s['va']
        if o >= s['rawsize']:
            return None
        return s['rawptr'] + o

    def read(self, va, n):
        o = self.off(va)
        if o is None:
            return None
        return self.data[o:o+n]

    def u32(self, va):
        b = self.read(va, 4)
        return struct.unpack('<I', b)[0] if b and len(b) == 4 else None

    def is_text(self, va):
        s = self.sec_of(va)
        return s is not None and (s['chars'] & 0x20000000) != 0  # MEM_EXECUTE

    def dis(self, va, n=0x80, stop_ret=False, maxins=400):
        b = self.read(va, n)
        out = []
        for ins in self.md.disasm(b, va):
            out.append(ins)
            if stop_ret and ins.mnemonic in ('ret', 'retn'):
                break
            if len(out) >= maxins:
                break
        return out

    def dis_fn(self, va, maxbytes=0x2000, maxins=2000):
        """Linear sweep until a ret that is followed by padding (int3/nop) or next fn start heuristics."""
        b = self.read(va, maxbytes)
        out = []
        for ins in self.md.disasm(b, va):
            out.append(ins)
            if ins.mnemonic in ('ret',):
                nxt = self.read(ins.address + ins.size, 1)
                if nxt in (b'\xcc', b'\x90'):
                    break
            if len(out) >= maxins:
                break
        return out

    def fmt(self, ins):
        return "%08X  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)

    def pr(self, va, n=0x80, stop_ret=False, maxins=400):
        for i in self.dis(va, n, stop_ret, maxins):
            print(self.fmt(i))

    def scan_dword(self, value, exec_only=False):
        pat = struct.pack('<I', value)
        hits = []
        for s in self.sections:
            if exec_only and not (s['chars'] & 0x20000000):
                continue
            blob = self.data[s['rawptr']:s['rawptr']+s['rawsize']]
            i = blob.find(pat)
            while i >= 0:
                hits.append((s['va'] + i, s['name']))
                i = blob.find(pat, i+1)
        return hits

    def callers_rel32(self, target):
        """Find E8/E9 rel32 whose destination == target in executable sections."""
        hits = []
        for s in self.sections:
            if not (s['chars'] & 0x20000000):
                continue
            blob = self.data[s['rawptr']:s['rawptr']+s['rawsize']]
            base = s['va']
            n = len(blob)
            for i in range(n-5):
                op = blob[i]
                if op in (0xE8, 0xE9):
                    rel = struct.unpack_from('<i', blob, i+1)[0]
                    dst = (base + i + 5 + rel) & 0xFFFFFFFF
                    if dst == target:
                        hits.append((base+i, 'call' if op == 0xE8 else 'jmp'))
        return hits

if __name__ == '__main__':
    p = PE()
    print(hex(p.imagebase))
    for s in p.sections:
        print(s['name'], hex(s['va']), hex(s['vsize']), hex(s['rawsize']), hex(s['chars']))
