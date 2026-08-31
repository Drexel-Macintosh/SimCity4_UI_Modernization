#!/usr/bin/env python3
r"""Shared DBPF reader for the row-15 probe rebuild.

Nothing here is a FINDING; it is only how to read the bytes.  Every archive in
the install root is DISCOVERED, never listed -- a hand-written list of "the
seven archives" already cost this project one shipped defect (see
tools\dbpf\find_tgi.py docstring: the install actually ships NINE .dat/.DAT
files, Intro.dat and Sound.dat included).

Read-only.  Opens the game install; never writes to it.
"""

import glob
import os
import struct

GAME = os.environ.get(
    "SC4_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe")

DIR_TYPE = 0xE86B1EEF          # the compression directory's TYPE id
T_EXEMPLAR = 0x6534284A
T_COHORT   = 0x05342861
T_LTEXT    = 0x2026960B
T_UI       = 0x00000000
T_S3D      = 0x5AD0E817
T_PNG      = 0x856DDBAC


def discover_archives(game_dir=GAME):
    """Every DBPF archive in the install root, discovered, case-insensitive."""
    seen = {}
    for pat in ("*.dat", "*.DAT", "*.Dat"):
        for p in glob.glob(os.path.join(game_dir, pat)):
            seen[os.path.basename(p).lower()] = p
    return [seen[k] for k in sorted(seen)]


def read_index(path):
    """(type, group, instance, offset, size) for every index entry."""
    with open(path, "rb") as f:
        hdr = f.read(96)
        if hdr[:4] != b"DBPF":
            return []
        count, idx_off, idx_size = struct.unpack_from("<III", hdr, 0x24)
        if not count:
            return []
        stride = idx_size // count
        f.seek(idx_off)
        blob = f.read(idx_size)
    out = []
    for k in range(count):
        out.append(struct.unpack_from("<IIIII", blob, k * stride))
    return out


def read_dir(path, index=None):
    """The archive's compression directory as {(t,g,i): uncompressed_size}.

    Returns ({}, None) when the archive carries no DIR record at all -- which
    is a different fact from "the DIR is empty", so the caller can tell them
    apart.  Returns (map, dir_tgi) otherwise.
    """
    if index is None:
        index = read_index(path)
    for (t, g, i, off, size) in index:
        if t == DIR_TYPE:
            with open(path, "rb") as f:
                f.seek(off)
                blob = f.read(size)
            m = {}
            for k in range(size // 16):
                et, eg, ei, esz = struct.unpack_from("<IIII", blob, k * 16)
                m[(et, eg, ei)] = esz
            # STRIDE IS 16, ASSERTED, NOT ASSUMED.  The sibling
            # decode_exemplar.py walks this table at stride 12 while reading
            # 16 bytes per record, which misaligns after the first entry and
            # can report a compressed record as "not listed".
            assert len(m) * 16 == size, (
                "DIR size %d is not a whole number of 16-byte records" % size)
            return m, (t, g, i)
    return {}, None


def has_qfs(raw):
    return (len(raw) >= 9 and raw[4] == 0x10 and raw[5] == 0xFB) or \
           (len(raw) >= 5 and raw[0] == 0x10 and raw[1] == 0xFB)


def qfs_decompress(src):
    if len(src) >= 9 and src[4] == 0x10 and src[5] == 0xFB:
        pos = 4
    elif len(src) >= 5 and src[0] == 0x10 and src[1] == 0xFB:
        pos = 0
    else:
        raise ValueError("no QFS 0x10FB signature")
    pos += 2
    out_len = (src[pos] << 16) | (src[pos + 1] << 8) | src[pos + 2]
    pos += 3
    dst = bytearray(out_len)
    out_pos = 0
    while pos < len(src) and out_pos < out_len:
        c0 = src[pos]; pos += 1
        if c0 < 0x80:
            c1 = src[pos]; pos += 1
            num_plain = c0 & 0x03
            num_copy = ((c0 & 0x1C) >> 2) + 3
            copy_off = ((c0 & 0x60) << 3) + c1 + 1
        elif c0 < 0xC0:
            c1 = src[pos]; pos += 1
            c2 = src[pos]; pos += 1
            num_plain = (c1 & 0xC0) >> 6
            num_copy = (c0 & 0x3F) + 4
            copy_off = ((c1 & 0x3F) << 8) + c2 + 1
        elif c0 < 0xE0:
            c1 = src[pos]; pos += 1
            c2 = src[pos]; pos += 1
            c3 = src[pos]; pos += 1
            num_plain = c0 & 0x03
            num_copy = ((c0 & 0x0C) << 6) + c3 + 5
            copy_off = ((c0 & 0x10) << 12) + (c1 << 8) + c2 + 1
        elif c0 < 0xFC:
            num_plain = ((c0 & 0x1F) + 1) << 2
            num_copy = 0
            copy_off = 0
        else:
            num_plain = c0 & 0x03
            dst[out_pos:out_pos + num_plain] = src[pos:pos + num_plain]
            pos += num_plain
            out_pos += num_plain
            break
        dst[out_pos:out_pos + num_plain] = src[pos:pos + num_plain]
        pos += num_plain
        out_pos += num_plain
        frm = out_pos - copy_off
        if num_copy > 0 and frm < 0:
            raise ValueError("copy offset before start")
        for _ in range(num_copy):
            dst[out_pos] = dst[frm]
            out_pos += 1
            frm += 1
    if out_pos != out_len:
        raise ValueError("decompressed %d != expected %d" % (out_pos, out_len))
    return bytes(dst)


class Archive(object):
    """One DBPF archive, index + DIR read once, payloads read on demand."""

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.index = read_index(path)
        self.dir, self.dir_tgi = read_dir(path, self.index)
        self._fh = None

    def open(self):
        if self._fh is None:
            self._fh = open(self.path, "rb")
        return self._fh

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def raw(self, off, size):
        f = self.open()
        f.seek(off)
        return f.read(size)

    def payload(self, entry):
        """Decompressed bytes for one index entry, plus whether it was QFS."""
        t, g, i, off, size = entry
        raw = self.raw(off, size)
        listed = (t, g, i) in self.dir
        if has_qfs(raw):
            return qfs_decompress(raw), True, listed
        return raw, False, listed

    def by_type(self, tid):
        return [e for e in self.index if e[0] == tid]

    def find(self, t=None, g=None, i=None):
        return [e for e in self.index
                if (t is None or e[0] == t)
                and (g is None or e[1] == g)
                and (i is None or e[2] == i)]


def ltext_text(buf):
    """Decode an LTEXT payload to str, or raise.

    SC4 LTEXT: u16 char count, u16 control (0x1000 = 'unicode'), then that many
    UTF-16LE code units.  The decoder ASSERTS the declared count against the
    buffer length rather than trusting either.
    """
    if len(buf) < 4:
        raise ValueError("LTEXT too short (%d bytes)" % len(buf))
    count, ctrl = struct.unpack_from("<HH", buf, 0)
    body = buf[4:]
    if ctrl != 0x1000:
        raise ValueError("unexpected LTEXT control word 0x%04X" % ctrl)
    if len(body) != count * 2:
        raise ValueError("LTEXT declares %d chars but carries %d body bytes"
                         % (count, len(body)))
    return body.decode("utf-16-le")


# --------------------------------------------------------------------------
# EXEMPLAR / COHORT binary decode (EQZB1### only; EQZT1### is the text form)
# --------------------------------------------------------------------------

_VT = {0x0100: ("Uint8", 1, "<B"), 0x0200: ("Uint16", 2, "<H"),
       0x0300: ("Uint32", 4, "<I"), 0x0700: ("Sint32", 4, "<i"),
       0x0800: ("Sint64", 8, "<q"), 0x0900: ("Float32", 4, "<f"),
       0x0B00: ("Bool", 1, "<B"), 0x0C00: ("String", 1, None)}


def decode_exemplar(buf):
    """{prop_id: (type_name, [values])} plus the parent-cohort TGI.

    Returns (parent_tgi, props) or raises.  Walk-exactness is ASSERTED: the
    property walk must land exactly on len(buf).
    """
    if buf[:8] not in (b"EQZB1###", b"CQZB1###"):
        raise ValueError("not a binary exemplar/cohort: %r" % buf[:8])
    pt, pg, pi, count = struct.unpack_from("<IIII", buf, 8)
    pos = 24
    props = {}
    for _ in range(count):
        pid, tc, kt = struct.unpack_from("<IHH", buf, pos)
        if kt == 0x0000:                 # single value, no count field
            n = 1
            vpos = pos + 9               # id4 + type2 + key2 + unused1
        elif kt == 0x0080:               # array, explicit count
            n = struct.unpack_from("<I", buf, pos + 9)[0]
            vpos = pos + 13              # ... + count4
        else:
            raise ValueError("unknown key type 0x%04X at %d" % (kt, pos))
        name, esz, fmt = _VT[tc]
        if tc == 0x0C00:
            vals = [buf[vpos:vpos + n].decode("latin-1")]
        else:
            vals = [struct.unpack_from(fmt, buf, vpos + k * esz)[0]
                    for k in range(n)]
        pos = vpos + n * esz
        props[pid] = (name, vals)
    if pos != len(buf):
        raise ValueError("walk ended at %d, record is %d bytes" % (pos, len(buf)))
    return (pt, pg, pi), props
