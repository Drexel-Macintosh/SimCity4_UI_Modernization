#!/usr/bin/env python3
"""Shared read-only PE/disasm helpers for the #109 "who sizes off the Data Views
map" investigation. Imported by the other *_probe.py scripts. Writes nothing."""
import struct, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_IMM, X86_OP_REG

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

_md = Cs(CS_ARCH_X86, CS_MODE_32)
_md.detail = True


def load():
    data = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    off = pe + 24 + opt
    for i in range(nsec):
        n = data[off:off + 8].rstrip(b"\0").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
        secs.append((n, va, vsize, roff, rsize))
        off += 40
    return data, secs


def va2off(secs, va):
    rva = va - IMAGE_BASE
    for n, sva, vsize, roff, rsize in secs:
        if sva <= rva < sva + max(vsize, rsize):
            o = roff + (rva - sva)
            return o
    return None


def off2va(secs, off):
    for n, sva, vsize, roff, rsize in secs:
        if roff <= off < roff + rsize:
            return IMAGE_BASE + sva + (off - roff)
    return None


def text_ranges(secs):
    out = []
    for n, sva, vsize, roff, rsize in secs:
        if n.startswith(".text"):
            out.append((IMAGE_BASE + sva, roff, min(vsize, rsize) if vsize else rsize, rsize))
    return out


def disasm(data, secs, va, nbytes=0x400):
    o = va2off(secs, va)
    if o is None:
        return []
    return list(_md.disasm(data[o:o + nbytes], va))


def dword_at(data, secs, va):
    o = va2off(secs, va)
    if o is None or o + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, o)[0]


def find_dword_refs(data, secs, value, sections=None):
    """Every 4-byte-aligned-or-not location in the image whose dword == value.
    Returns list of (section_name, VA)."""
    out = []
    needle = struct.pack("<I", value)
    for n, sva, vsize, roff, rsize in secs:
        if sections and n not in sections:
            continue
        blob = data[roff:roff + rsize]
        i = blob.find(needle)
        while i != -1:
            out.append((n, IMAGE_BASE + sva + i))
            i = blob.find(needle, i + 1)
    return out


def callers_of(data, secs, target):
    hits = []
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff + rsize]
        i = 0
        while True:
            i = blob.find(b"\xE8", i)
            if i == -1 or i + 5 > len(blob):
                break
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            if base + i + 5 + rel == target:
                hits.append(base + i)
            i += 1
    # also E9 jmp (tail call)
    return hits


def jmp_callers_of(data, secs, target):
    hits = []
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff + rsize]
        i = 0
        while True:
            i = blob.find(b"\xE9", i)
            if i == -1 or i + 5 > len(blob):
                break
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            if base + i + 5 + rel == target:
                hits.append(base + i)
            i += 1
    return hits


_FN_STARTS = None


def function_starts(data, secs):
    """Every VA that is the destination of a `call rel32` in .text. That is the
    ground truth for 'this is a function entry' for non-virtual functions;
    virtuals additionally appear as dwords in .rdata vtables."""
    global _FN_STARTS
    if _FN_STARTS is not None:
        return _FN_STARTS
    starts = set()
    lo, hi = IMAGE_BASE, IMAGE_BASE + 0x800000
    for n, sva, vsize, roff, rsize in secs:
        if not n.startswith(".text"):
            continue
        base = IMAGE_BASE + sva
        blob = data[roff:roff + rsize]
        i = 0
        while True:
            i = blob.find(b"\xE8", i)
            if i == -1 or i + 5 > len(blob):
                break
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            t = base + i + 5 + rel
            if lo < t < hi:
                starts.add(t)
            i += 1
    # ALSO: every .rdata/.data dword that points into .text. Virtual functions
    # are never `call rel32` targets, so a call-target-only set silently merges
    # a virtual into whatever non-virtual precedes it -- that is exactly the
    # blind-null shape this project has been bitten by.
    tlo = thi = None
    for n, sva, vsize, roff, rsize in secs:
        if n.startswith(".text"):
            tlo = IMAGE_BASE + sva
            thi = IMAGE_BASE + sva + max(vsize, rsize)
    for n, sva, vsize, roff, rsize in secs:
        if n not in (".rdata", ".data"):
            continue
        blob = data[roff:roff + rsize]
        for off in range(0, len(blob) - 4, 4):
            d = struct.unpack_from("<I", blob, off)[0]
            if tlo <= d < thi:
                starts.add(d)
    _FN_STARTS = starts
    return starts


def enclosing_function(data, secs, va, starts=None):
    """Largest known function start <= va, within 0x3000 bytes."""
    if starts is None:
        starts = function_starts(data, secs)
    best = None
    for s in starts:
        if s <= va and (best is None or s > best):
            if va - s < 0x4000:
                best = s
    return best
