#!/usr/bin/env python3
r"""For every zoom/rotation variant of the 4 zot S3Ds: MATS texture id +
vertex count; then resolve every distinct texture's TGI + FSH dims.
Control: 0x0FD10000 must report tex 0x1EE50010 and 0x0FD10400 tex 0x1E060400
(both proven in zot_art_decode.out.txt)."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UDI = os.path.abspath(os.path.join(HERE, "..", "udriveit"))
sys.path.insert(0, UDI)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from census_markers import read_entry, maybe_decompress                # noqa: E402
from index_all import index, T_S3D, G_S3D, T_FSH                       # noqa: E402
from zot_art_decode import decode_s3d, fsh_dims                        # noqa: E402

ZOTS = [0x0FD10000, 0x107A0000, 0x1C430000, 0x1C440000]

import io, contextlib                                                   # noqa: E402

g = index()
by_tgi, by_ti = g["by_tgi"], g["by_ti"]
texset = {}
for base in ZOTS:
    row = []
    for zoom in range(5):
        for rot in range(4):
            inst = base + (zoom << 8) + (rot << 4)
            hit = by_tgi.get((T_S3D, G_S3D, inst))
            if not hit:
                row.append("z%dr%d:MISSING" % (zoom, rot))
                continue
            payload, _ = maybe_decompress(read_entry(*hit))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                r = decode_s3d(payload, "x")
            nv = len(r["verts"][0]) if r and r.get("verts") else -1
            row.append("z%dr%d:%08X(nv=%d)" % (zoom, rot, r["mats_tex"], nv))
            texset.setdefault(r["mats_tex"], []).append(inst)
    print("base 0x%08X:" % base)
    for k in range(0, 20, 4):
        print("   " + "  ".join(row[k:k + 4]))

print("\ndistinct textures bound by the 80 zot models:")
for tex in sorted(texset):
    hits = by_ti.get((T_FSH, tex)) or []
    for (grp, path, off, sz) in hits:
        payload, _ = maybe_decompress(read_entry(path, off, sz))
        dims = fsh_dims(payload)
        print("  0x%08X  {T=0x%08X,G=0x%08X} %s %s  <- %d models"
              % (tex, T_FSH, grp, os.path.basename(path),
                 ["0x%02X %dx%d" % d for d in dims], len(texset[tex])))
    if not hits:
        print("  0x%08X  *** no FSH with this instance ***" % tex)
