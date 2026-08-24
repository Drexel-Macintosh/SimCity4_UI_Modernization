#!/usr/bin/env python3
r"""Zot ART end-to-end decode (scratch, read-only on game files).

(1) Full field decode of the four Zot S3D models {0x5AD0E817,0xBADB57F1,I}
    for I in the RKT bases AND their zoom-4 (+0x400) variants: VERT floats,
    INDX list, PRIM, MATS name + bound texture id.
(2) Resolve the FSH textures those models bind to full TGIs + pixel dims.
(3) (LTEXT handled outside - already resolved from ltext-all.tsv.)
(5) Census: every exemplar name in G=0xC977C536 containing 'zot' (case-ins),
    every S3D instance in G=0xBADB57F1 sharing the four top-16 bases, and a
    full decompressed-byte scan of EVERY S3D in the group for b'Zot'.

POSITIVE CONTROLS stated inline:
  - S3D decode: ConnectArrow 0x29F10000 must decode 4 verts / 6 idx
    [0,1,2,3,0,2] / MATS name '29F10000_ConnectArrow_Ui8x1x3_Z1S' tex
    0x1EE50000 (all proven by hand in row-15 sec.6).
  - Exemplar census: the 4 known Zot_* names MUST appear or the census is
    broken.
  - S3D 'Zot' byte scan: the 4x(zooms) zot models themselves MUST hit.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UDI = os.path.abspath(os.path.join(HERE, "..", "udriveit"))
sys.path.insert(0, UDI)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from census_markers import read_entry, maybe_decompress, parse_exemplar  # noqa: E402
from index_all import index, T_EXEMPLAR, G_MARKER, T_S3D, G_S3D, T_FSH   # noqa: E402

ZOTS = {
    0x0FD10000: "Zot_NoPower_0fd1",
    0x107A0000: "Zot_NoCar_107A",
    0x1C430000: "Zot_NoWater_1c43",
    0x1C440000: "Zot_NoWork_1c44",
}
CTRL_ARROW = 0x29F10000


def walk_sections(data):
    if data[:4] != b"3DMD":
        return
    off = 8
    while off + 8 <= len(data):
        tag = data[off:off + 4]
        if not tag.isalpha():
            break
        size = struct.unpack_from("<I", data, off + 4)[0]
        yield tag.decode("latin-1"), off, size
        if size < 8:
            break
        off += size


def decode_s3d(data, label):
    print("== %s : %d bytes decompressed" % (label, len(data)))
    if data[:4] != b"3DMD":
        print("   NOT 3DMD:", data[:8].hex())
        return None
    out = {}
    for tag, off, size in walk_sections(data):
        body = data[off + 8: off + size]
        if tag == "HEAD":
            ver = struct.unpack_from("<HH", data, off + 8)
            out["head_ver"] = ver
            print("   HEAD ver %d.%d" % ver)
        elif tag == "VERT":
            ngrp = struct.unpack_from("<I", body, 0)[0]
            p = 4
            groups = []
            for g in range(ngrp):
                a, nv = struct.unpack_from("<HH", body, p)
                fmt = body[p + 4: p + 8]
                p += 8
                verts = []
                for k in range(nv):
                    x, y, z, u, v = struct.unpack_from("<5f", body, p)
                    verts.append((x, y, z, u, v))
                    p += 20
                groups.append(verts)
                print("   VERT grp%d a=%d n=%d fmt=%s" % (g, a, nv, fmt.hex()))
                for k, (x, y, z, u, v) in enumerate(verts):
                    print("     v%d  X=%10.4f Y=%10.4f Z=%10.4f  U=%.6f V=%.6f"
                          % (k, x, y, z, u, v))
            out["verts"] = groups
        elif tag == "INDX":
            ngrp = struct.unpack_from("<I", body, 0)[0]
            p = 4
            groups = []
            for g in range(ngrp):
                a, b, ni = struct.unpack_from("<HHH", body, p)
                p += 6
                idx = list(struct.unpack_from("<%dH" % ni, body, p))
                p += 2 * ni
                groups.append(idx)
                print("   INDX grp%d a=%d b=%d n=%d idx=%s" % (g, a, b, ni, idx))
            out["indx"] = groups
        elif tag == "PRIM":
            vals = struct.unpack_from("<%dH" % (len(body) // 2), body, 0)
            print("   PRIM u16[] =", list(vals))
        elif tag == "MATS":
            # locate <len u8><name...><NUL> tail per mats_parse.py method
            end = len(body)
            k = end - 1
            while k > 0 and body[k] == 0:
                k -= 1
            t = k + 1
            j = None
            for L in range(2, 96):
                lenpos = t - L
                if lenpos < 1:
                    break
                if body[lenpos] == L and all(32 <= b < 127 for b in body[lenpos + 1:t]):
                    j = lenpos + 1
                    break
            name = body[j:t].decode("latin-1") if j else None
            tex = None
            if j:
                p = j - 1 - 4
                if p >= 4 and body[p:p + 4] == b"\x21\x00\x02\x00":
                    ver = out.get("head_ver", (1, 5))
                    back = 8 if ver == (1, 5) else 6
                    if p - back >= 0:
                        tex = struct.unpack_from("<I", body, p - back)[0]
            out["mats_name"], out["mats_tex"] = name, tex
            print("   MATS name=%r  tex=%s  rawhex=%s"
                  % (name, ("0x%08X" % tex) if tex is not None else None,
                     body[:min(40, len(body))].hex()))
        elif tag == "ANIM":
            # u16 nframes?, u16 framerate?, u32 mode?, 6 zero, u16 count,
            # u16 len-prefixed NUL-terminated name
            if len(body) >= 16:
                a, b = struct.unpack_from("<HH", body, 0)
                c = struct.unpack_from("<I", body, 4)[0]
                n = struct.unpack_from("<H", body, 14)[0]
                p = 16
                names = []
                for k in range(n):
                    if p + 2 > len(body):
                        break
                    L = struct.unpack_from("<H", body, p)[0]
                    p += 2
                    names.append(body[p:p + L].rstrip(b"\0").decode("latin-1"))
                    p += L
                print("   ANIM a=%d b=%d c=%d names=%s" % (a, b, c, names))
                out["anim_names"] = names
    return out


def fsh_dims(payload):
    """-> list of (code, w, h) for image entries in an SHPI FSH."""
    if payload[:4] != b"SHPI":
        return []
    nent = struct.unpack_from("<I", payload, 8)[0]
    out = []
    for e in range(min(nent, 64)):
        off = struct.unpack_from("<I", payload, 20 + 8 * e)[0]
        if off + 16 > len(payload):
            continue
        code = payload[off] & 0x7F
        w, h = struct.unpack_from("<2H", payload, off + 4)
        out.append((code, w, h))
    return out


def main():
    g = index()
    by_tgi, by_ti = g["by_tgi"], g["by_ti"]

    # ---------------- (control) ConnectArrow ----------------
    print("#### CONTROL: ConnectArrow 0x29F10000 base model")
    hit = by_tgi.get((T_S3D, G_S3D, CTRL_ARROW))
    payload, _ = maybe_decompress(read_entry(hit[0], hit[1], hit[2]))
    c = decode_s3d(payload, "ConnectArrow 0x29F10000")
    ok = (c and len(c["verts"][0]) == 4 and c["indx"][0] == [0, 1, 2, 3, 0, 2]
          and c["mats_name"] == "29F10000_ConnectArrow_Ui8x1x3_Z1S"
          and c["mats_tex"] == 0x1EE50000)
    print("CONTROL PASS" if ok else "*** CONTROL FAIL — everything below suspect")

    # ---------------- (1) four zots, base + zoom-4 ----------------
    tex_ids = set()
    for base, name in ZOTS.items():
        for inst in (base, base + 0x400):
            hit = by_tgi.get((T_S3D, G_S3D, inst))
            if not hit:
                print("== %s 0x%08X: NOT IN INDEX" % (name, inst))
                continue
            payload, comp = maybe_decompress(read_entry(hit[0], hit[1], hit[2]))
            r = decode_s3d(payload, "%s model 0x%08X (%s)"
                           % (name, inst, os.path.basename(hit[0])))
            if r and r.get("mats_tex") is not None:
                tex_ids.add(r["mats_tex"])
        print()

    # ---------------- (2) texture TGIs + dims ----------------
    print("#### TEXTURES (type 0x%08X)" % T_FSH)
    for tex in sorted(tex_ids):
        hits = by_ti.get((T_FSH, tex)) or []
        if not hits:
            print("tex 0x%08X: NOT FOUND as FSH type — checking all types" % tex)
            continue
        for (grp, path, off, sz) in hits:
            payload, comp = maybe_decompress(read_entry(path, off, sz))
            dims = fsh_dims(payload)
            print("tex {T=0x%08X,G=0x%08X,I=0x%08X} %s  entries=%s"
                  % (T_FSH, grp, tex, os.path.basename(path),
                     ["code=0x%02X %dx%d" % d for d in dims]))

    # ---------------- (5a) exemplar census for 'zot' ----------------
    print("\n#### EXEMPLAR CENSUS G=0x%08X names containing 'zot'" % G_MARKER)
    n_ex = 0
    zot_names = []
    for (t, grp, i), (path, off, sz) in by_tgi.items():
        if t != T_EXEMPLAR or grp != G_MARKER:
            continue
        n_ex += 1
        try:
            payload, _ = maybe_decompress(read_entry(path, off, sz))
            _parent, props, _order = parse_exemplar(payload)
        except Exception:
            continue
        nm = None
        ent = props.get(0x20)
        if ent:
            v = ent[1][0] if ent[1] else b""
            nm = v.decode("latin-1", "replace") if isinstance(v, bytes) else str(v)
        if nm and "zot" in str(nm).lower():
            zot_names.append((i, str(nm)))
    print("exemplars scanned in group: %d" % n_ex)
    for i, nm in sorted(zot_names):
        print("  I=0x%08X  %s" % (i, nm))
    ctrl = all(any(i == b for i, _ in zot_names) for b in ZOTS)
    print("census control (4 known zots present): %s"
          % ("PASS" if ctrl else "*** FAIL — name parse broken, list void"))

    # ---------------- (5b) S3D group siblings + byte scan ----------------
    print("\n#### S3D GROUP 0x%08X" % G_S3D)
    insts = sorted(i for (t, grp, i) in by_tgi if t == T_S3D and grp == G_S3D)
    print("total S3D instances in group: %d" % len(insts))
    for base in sorted(ZOTS) + [CTRL_ARROW]:
        sibs = [i for i in insts if (i >> 16) == (base >> 16)]
        print("  base 0x%04X****: %s" % (base >> 16,
              ", ".join("0x%08X" % s for s in sibs)))

    print("\n  byte-scan of ALL %d S3Ds in group for b'Zot' "
          "(decompressed — text scanners are blind to QFS)" % len(insts))
    zot_models = []
    scanned = failed = 0
    for i in insts:
        path, off, sz = by_tgi[(T_S3D, G_S3D, i)]
        try:
            payload, _ = maybe_decompress(read_entry(path, off, sz))
            scanned += 1
        except Exception:
            failed += 1
            continue
        if b"Zot" in payload or b"zot" in payload or b"ZOT" in payload:
            # pull the MATS/ANIM names for identification
            names = []
            p = 0
            while True:
                k = payload.find(b"Zot", p)
                k2 = payload.find(b"zot", p)
                k = min([x for x in (k, k2) if x >= 0], default=-1)
                if k < 0:
                    break
                s = k
                while s > 0 and 32 <= payload[s - 1] < 127:
                    s -= 1
                e = k
                while e < len(payload) and 32 <= payload[e] < 127:
                    e += 1
                names.append(payload[s:e].decode("latin-1"))
                p = e
            zot_models.append((i, sorted(set(names))))
    print("  scanned=%d decompress-failed=%d" % (scanned, failed))
    for i, names in zot_models:
        print("  S3D 0x%08X: %s" % (i, names))
    known = {b + z for b in ZOTS for z in
             (0x000, 0x100, 0x200, 0x300, 0x400)}
    extra = [x for x in zot_models if x[0] not in known]
    print("  models with 'Zot' beyond the 4 known bases+zooms: %d" % len(extra))


if __name__ == "__main__":
    main()
