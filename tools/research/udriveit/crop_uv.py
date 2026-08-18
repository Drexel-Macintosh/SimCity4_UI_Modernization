#!/usr/bin/env python3
r"""Crop the exact sprite an S3D uses out of its shared texture atlas.

The marker models bind 256x256 ATLASES shared by dozens of props, so opening
the atlas proves nothing about one marker.  This reads the model's VERT section
UVs and crops the atlas to that rect.

VERT layout, read off {..,0x29F10000} and cross-checked on 5 more models:
    "VERT" u32 sectionSize(incl header) u32 numGroups
    per group: u16 pad, u16 vertexCount, u32 vertexFormat(0x80004001),
               vertexCount x (float x, y, z, u, v)      -- 20 bytes each
Proof the stride is right: 12 + 4 + 4*20 == 100 == the ConnectArrow VERT size,
and every u,v it yields lands inside [0,1].

    python crop_uv.py 29F10000 0FD10000 107A0000 1C430000 1C440000
"""
import os
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from s3d_textures import get_s3d, walk_sections                # noqa: E402
from mats_parse import parse_mats                              # noqa: E402
import extract_fsh                                             # noqa: E402


def verts(data):
    for tag, off, size in walk_sections(data):
        if tag != "VERT":
            continue
        p = off + 8
        ngroups = struct.unpack_from("<I", data, p)[0]
        p += 4
        for _g in range(ngroups):
            _pad, count = struct.unpack_from("<HH", data, p)
            fmt = struct.unpack_from("<I", data, p + 4)[0]
            p += 8
            vs = []
            for _i in range(count):
                x, y, z, u, v = struct.unpack_from("<5f", data, p)
                vs.append((x, y, z, u, v))
                p += 20
            yield fmt, vs


def main(argv):
    for a in argv:
        inst = int(a, 16)
        data, path, comp = get_s3d(inst)
        print("=" * 80)
        print("S3D 0x%08X" % inst)
        if data is None:
            print("  NOT PRESENT")
            continue
        mats = parse_mats(data)
        if not mats:
            print("  no MATS")
            continue
        name, _nl, tex, ok = mats[0]
        print("  material : %s" % name)
        print("  texture  : 0x%08X (resolved=%s)" % (tex or 0, ok))
        allv = []
        for fmt, vs in verts(data):
            print("  vert grp : fmt=0x%08X count=%d" % (fmt, len(vs)))
            allv.extend(vs)
        if not allv:
            print("  no verts")
            continue
        us = [v[3] for v in allv]
        vsv = [v[4] for v in allv]
        xs = [v[0] for v in allv]
        ys = [v[1] for v in allv]
        zs = [v[2] for v in allv]
        print("  model bbox (x,y,z): (%.2f..%.2f, %.2f..%.2f, %.2f..%.2f)"
              % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
        print("  uv rect  : u %.4f..%.4f   v %.4f..%.4f"
              % (min(us), max(us), min(vsv), max(vsv)))
        if not ok:
            continue
        png = os.path.join(HERE, "fsh-%08x-0.png" % tex)
        if not os.path.exists(png):
            print("  atlas PNG missing: run  python extract_fsh.py %08x" % tex)
            continue
        im = Image.open(png).convert("RGBA")
        W, H = im.size
        l = int(round(min(us) * W))
        r = int(round(max(us) * W))
        # SC4 UV v runs top-down in these sheets; crop both ways and keep both.
        t = int(round(min(vsv) * H))
        b = int(round(max(vsv) * H))
        l, r = max(0, min(l, W - 1)), min(W, max(r, l + 1))
        t, b = max(0, min(t, H - 1)), min(H, max(b, t + 1))
        out = os.path.join(HERE, "sprite-%08x-%08x.png" % (inst, tex))
        crop = im.crop((l, t, r, b))
        scale = max(1, 160 // max(1, max(crop.size)))
        crop = crop.resize((crop.width * scale, crop.height * scale), Image.NEAREST)
        bg = Image.new("RGBA", crop.size, (40, 40, 48, 255))
        bg.alpha_composite(crop)
        bg.save(out)
        print("  CROP     : px (%d,%d)-(%d,%d)  ->  %s" % (l, t, r, b, os.path.basename(out)))


if __name__ == "__main__":
    main(sys.argv[1:])
