#!/usr/bin/env python3
"""Read-only linear disassembly of a VA range in SimCity 4.exe (ImageBase 0x400000).

Usage: python dis.py <startVA hex> <endVA hex>
The .text section is mapped 1:1 here (file offset = VA - 0x400000) per the
project's established convention, but we resolve it through the PE headers
anyway so a bad assumption cannot silently corrupt an address.
"""
import sys
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

_data = None
_secs = None


def load():
    global _data, _secs
    if _data is not None:
        return
    with open(EXE, "rb") as f:
        _data = f.read()
    e_lfanew = struct.unpack_from("<I", _data, 0x3C)[0]
    nsec = struct.unpack_from("<H", _data, e_lfanew + 6)[0]
    optsz = struct.unpack_from("<H", _data, e_lfanew + 20)[0]
    base = struct.unpack_from("<I", _data, e_lfanew + 24 + 28)[0]
    sect = e_lfanew + 24 + optsz
    _secs = []
    for i in range(nsec):
        o = sect + i * 40
        name = _data[o:o + 8].rstrip(b"\0").decode("latin1")
        vsz, va, rsz, ro = struct.unpack_from("<IIII", _data, o + 8)
        _secs.append((name, base + va, vsz, ro, rsz))


def va2off(va):
    load()
    for name, sva, vsz, ro, rsz in _secs:
        if sva <= va < sva + max(vsz, rsz):
            return ro + (va - sva)
    return None


def read(va, n):
    load()
    o = va2off(va)
    if o is None:
        raise ValueError("VA 0x%08x not mapped" % va)
    return _data[o:o + n]


def sections():
    load()
    return _secs


def disasm(start, end):
    code = read(start, end - start)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    for ins in md.disasm(code, start):
        yield ins


if __name__ == "__main__":
    a = int(sys.argv[1], 16)
    b = int(sys.argv[2], 16)
    for ins in disasm(a, b):
        print("0x%08x  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
