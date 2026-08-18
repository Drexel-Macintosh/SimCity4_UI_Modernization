#!/usr/bin/env python3
r"""Which FSH textures does an S3D model bind?

Extracts {0x5AD0E817, 0xBADB57F1, <inst>} from the archives, QFS-decompresses,
walks the 3DMD section list, and reports the MATS section's texture instance
ids -- each CONFIRMED by looking it up in the archives' FSH (0x7AB50E44) index
rather than trusted from the parse.

POSITIVE CONTROL: pass --control to also run the ConnectArrow model
{...,0x29F10000}; it MUST yield at least one texture id that resolves to a real
FSH entry.  If the control yields nothing, a zero result elsewhere is a tool
failure, not a fact about the model.

    python s3d_textures.py 0FD10000 107A0000 1C430000 1C440000
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from census_markers import (dbpf_index, read_entry, maybe_decompress,   # noqa: E402
                            discover_dbpf)
from sc4paths import game_dir                                            # noqa: E402

T_S3D = 0x5AD0E817
G_S3D = 0xBADB57F1
T_FSH = 0x7AB50E44

_fsh_index = None


def fsh_index():
    global _fsh_index
    if _fsh_index is None:
        _fsh_index = {}
        for p in discover_dbpf(game_dir()):
            for (t, g, i, off, sz) in dbpf_index(p):
                if t == T_FSH:
                    _fsh_index.setdefault(i, []).append((g, os.path.basename(p)))
    return _fsh_index


def get_s3d(inst):
    for p in discover_dbpf(game_dir()):
        for (t, g, i, off, sz) in dbpf_index(p):
            if t == T_S3D and g == G_S3D and i == inst:
                payload, comp = maybe_decompress(read_entry(p, off, sz))
                return payload, p, comp
    return None, None, None


def walk_sections(data):
    """Yield (tag, offset, size) for each top-level 3DMD section."""
    if data[:4] != b"3DMD":
        return
    total = struct.unpack_from("<I", data, 4)[0]
    off = 8
    while off + 8 <= len(data):
        tag = data[off:off + 4]
        if not tag.isalpha():
            break
        size = struct.unpack_from("<I", data, off + 4)[0]
        # The size field COUNTS the 8-byte tag+size header (HEAD reads 0x0C for
        # a 4-byte payload; VERT at +20 in the ConnectArrow model proves it).
        yield tag.decode("latin-1"), off, size
        if size < 8:
            break
        off += size


def texture_ids(data):
    """Every dword inside the MATS section that resolves to a real FSH entry."""
    idx = fsh_index()
    found = []
    for tag, off, size in walk_sections(data):
        if tag != "MATS":
            continue
        blob = data[off + 8: off + size]
        for k in range(0, max(0, len(blob) - 4)):
            v = struct.unpack_from("<I", blob, k)[0]
            if v in idx and v not in [f[0] for f in found]:
                found.append((v, idx[v]))
    return found


def main(argv):
    want = [a for a in argv if not a.startswith("--")]
    if "--control" in argv:
        want.append("29F10000")
    for a in want:
        inst = int(a, 16)
        data, path, comp = get_s3d(inst)
        print("=" * 88)
        print("S3D {0x5AD0E817, 0xBADB57F1, 0x%08X}" % inst)
        if data is None:
            print("  NOT PRESENT in any game archive")
            continue
        print("  file: %s  (compressed=%s, %d bytes)"
              % (os.path.basename(path), comp, len(data)))
        secs = list(walk_sections(data))
        print("  sections: %s" % ", ".join("%s(%d)" % (t, s) for t, _o, s in secs))
        tex = texture_ids(data)
        if not tex:
            print("  NO texture id in MATS resolves to an FSH entry")
        for v, where in tex:
            print("  texture FSH instance 0x%08X -> %s"
                  % (v, ", ".join("G=0x%08X in %s" % (g, f) for g, f in where)))


if __name__ == "__main__":
    main(sys.argv[1:])
