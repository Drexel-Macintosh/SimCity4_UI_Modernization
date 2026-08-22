#!/usr/bin/env python3
r"""Decode the MATS section of an SC4 S3D: material name + bound FSH texture id.

Layout derived from three known models (not guessed):
  {..,0x29F10000} ConnectArrow  HEAD ver 1.5  tex 0x1EE50000  name len 0x22
  {..,0x0FD10000} Zot_NoPower   HEAD ver 1.5  tex 0x1EE50010  name len 0x19
  {..,0x03060000} MarkerPost    HEAD ver 1.3  tex 0x03060000  name len 0x20
The name is a length-prefixed, NUL-terminated ASCII string at the tail; the
texture id is the dword 12 bytes (v1.5) / 11 bytes (v1.3) before the
`21 00 02 00 <len>` name preamble.  Rather than trust that arithmetic, this
parser LOCATES the `21 00 02 00 <len>` preamble by matching the trailing name,
then reads backwards -- and every id it reports is confirmed against the real
FSH index before being printed.

    python mats_parse.py 0FD10000 107A0000 1C430000 1C440000 29F10000
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from s3d_textures import get_s3d, walk_sections, fsh_index   # noqa: E402


def parse_mats(data):
    """-> list of (material_name, texture_iid_or_None, confirmed_bool)."""
    idx = fsh_index()
    out = []
    for tag, off, size in walk_sections(data):
        if tag != "MATS":
            continue
        blob = data[off:off + size]
        # tail: <namelen u8> <name bytes incl NUL>
        end = len(blob)
        # find the last NUL-terminated ASCII run
        k = end - 1
        while k > 0 and blob[k] == 0:
            k -= 1
        # blob[k] is the last non-NUL byte; the record is
        #   <len u8><name...><NUL>, len INCLUDING the NUL.
        # ⛔ Do NOT find the start by scanning back over printable bytes: the
        # length byte itself is often printable (0x22 '"', 0x20 ' '), which
        # swallowed it into the name and shifted every downstream offset by 1.
        # Solve for the length that is consistent with its own byte instead.
        t = k + 1                      # index of the NUL terminator
        j = None
        namelen = 0
        for L in range(2, 96):         # L counts the NUL
            lenpos = t - L             # where the length byte must sit
            if lenpos < 1:
                break
            if blob[lenpos] == L and all(32 <= b < 127 for b in blob[lenpos + 1:t]):
                j, namelen = lenpos + 1, L
                break
        if j is None:
            continue
        name = blob[j:t].decode("latin-1")
        # preamble `21 00 02 00` sits immediately before the length byte
        p = j - 1 - 4
        tex = None
        if p >= 4 and blob[p:p + 4] == b"\x21\x00\x02\x00":
            # FIXED offsets, read off three known models -- not a search:
            #   HEAD v1.5 -> dword at p-8   (ConnectArrow 0x1EE50000,
            #                                Zot_NoPower  0x1EE50010)
            #   HEAD v1.3 -> dword at p-6   (MarkerPost   0x03060000)
            ver = struct.unpack_from("<HH", data, 16)
            back = 8 if ver == (1, 5) else 6
            s = p - back
            if s >= 0:
                tex = struct.unpack_from("<I", blob, s)[0]
        out.append((name, namelen, tex, (tex in idx) if tex is not None else False))
    return out


def main(argv):
    idx = fsh_index()
    for a in argv:
        inst = int(a, 16)
        data, path, comp = get_s3d(inst)
        print("S3D 0x%08X" % inst, end="  ")
        if data is None:
            print("NOT PRESENT")
            continue
        ver = struct.unpack_from("<HH", data, 16)[0:2]
        rows = parse_mats(data)
        print("(HEAD v%d.%d, %s)" % (ver[0], ver[1], os.path.basename(path)))
        for name, namelen, tex, ok in rows:
            if tex is None or not ok:
                print("    material %-42r  tex dword 0x%s NOT in FSH index"
                      % (name, ('%08X' % tex) if tex is not None else '?'))
            else:
                where = ", ".join("G=0x%08X in %s" % (g, f) for g, f in idx[tex])
                print("    material %-42r  FSH 0x%08X  [%s]" % (name, tex, where))


if __name__ == "__main__":
    main(sys.argv[1:])
