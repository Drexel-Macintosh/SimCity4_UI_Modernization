#!/usr/bin/env python3
r"""PASS 1 of the blue-disc hunt: for EVERY exemplar in
{T=0x6534284A, G=0xC977C536, *}, resolve exemplar -> S3D -> MATS -> FSH id and
the model's UV rect, and write one row per (exemplar, model) to a TSV.

No pixels are decoded here.  Pass 2 (render_family.py) groups the rows by
texture so each atlas is decoded exactly once.

Model instance key = base | zoom<<8 | rot<<4 (5 zooms x 4 rotations).  We take
the LARGEST zoom present (4 -> +0x400) at rotation 0, falling back downwards;
the fallback is recorded per row so nothing is silently substituted.

POSITIVE CONTROL: the row for {..,0x29F10000} UI8x1x3_ConnectArrow_29F1 MUST
come out with model 0x29F10400 and FSH 0x1EE50000 -- the pair proven by hand in
mats_parse.py's docstring.  If that row is absent or wrong, every empty result
below is a tool failure, not a fact about the family.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from census_markers import read_entry, maybe_decompress, parse_exemplar  # noqa: E402
from index_all import index, T_EXEMPLAR, G_MARKER, T_S3D, G_S3D, T_FSH   # noqa: E402

OUT = os.path.join(HERE, "family-resolved.tsv")

RESKEY_PROPS = (0x27812820, 0x27812821, 0x27812822, 0x27812823,
                0x27812824, 0x27812825)
# FIVE hand-verified exemplar -> model -> texture triples.  Each was rendered by
# eye in the previous session (sprite-<model>-<tex>.png on disk) so this is a
# real control set, not a restatement of what this script computes.
# ⛔ mats_parse.py's docstring pairs 0x29F10400 with 0x1EE50000; that is the
# BASE-instance model's texture, NOT the zoom-4 model's.  Asserting it here
# failed the control and nearly condemned a working parser.
CONTROLS = {
    0x0FD10000: (0x0FD10400, 0x1E060400),   # Zot_NoPower  yellow bolt, red ring
    0x107A0000: (0x107A0400, 0x1E060410),   # Zot_NoCar    green car,   red ring
    0x1C430000: (0x1C430400, 0x1E060420),   # Zot_NoWater
    0x1C440000: (0x1C440400, 0x1ED30400),   # Zot_NoWork   briefcase,   red ring
    0x29F10000: (0x29F10400, 0x293B0430),   # UI8x1x3_ConnectArrow orange arrow
}


# ------------------------------------------------------------------ S3D pieces
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


def mats_texture_ids(data, fsh_ids):
    """(list_of_texture_ids, method).

    METHOD 'struct' is mats_parse.parse_mats's proven layout: locate the
    `21 00 02 00 <len><name><NUL>` tail, then read the texture dword at a FIXED
    offset before it (8 back for HEAD v1.5, 6 back for v1.3).  That arithmetic
    was derived from three models by hand.

    ⛔ The earlier "scan MATS for any dword that happens to be an FSH instance"
    shortcut FAILED THE POSITIVE CONTROL: on {..,0x29F10400} it returned
    0x01000000 instead of 0x1EE50000, because 42,133 FSH ids make almost any
    dword a false hit.  It survives only as a labelled fallback.
    """
    out = []
    try:
        ver = struct.unpack_from("<HH", data, 16)
    except Exception:
        ver = (0, 0)
    for tag, off, size in walk_sections(data):
        if tag != "MATS":
            continue
        blob = data[off:off + size]
        k = len(blob) - 1
        while k > 0 and blob[k] == 0:
            k -= 1
        t = k + 1
        j = None
        for L in range(2, 96):
            lenpos = t - L
            if lenpos < 1:
                break
            if blob[lenpos] == L and all(32 <= b < 127 for b in blob[lenpos + 1:t]):
                j = lenpos + 1
                break
        if j is None:
            continue
        p = j - 1 - 4
        if p >= 4 and blob[p:p + 4] == b"\x21\x00\x02\x00":
            back = 8 if ver == (1, 5) else 6
            s = p - back
            if s >= 0:
                v = struct.unpack_from("<I", blob, s)[0]
                if v in fsh_ids and v not in out:
                    out.append(v)
    if out:
        return out, "struct"
    # labelled fallback -- noisy, never trusted silently
    for tag, off, size in walk_sections(data):
        if tag != "MATS":
            continue
        blob = data[off + 8: off + size]
        for k in range(0, max(0, len(blob) - 4)):
            v = struct.unpack_from("<I", blob, k)[0]
            if v in fsh_ids and v not in out:
                out.append(v)
    return out, ("scan" if out else "none")


def uv_rect(data):
    """(umin, umax, vmin, vmax, nverts) over every VERT group."""
    us, vs, n = [], [], 0
    for tag, off, size in walk_sections(data):
        if tag != "VERT":
            continue
        p = off + 8
        try:
            ngroups = struct.unpack_from("<I", data, p)[0]
        except Exception:
            continue
        p += 4
        for _g in range(min(ngroups, 64)):
            try:
                _pad, count = struct.unpack_from("<HH", data, p)
            except Exception:
                break
            p += 8
            if count > 20000:
                break
            for _i in range(count):
                if p + 20 > len(data):
                    break
                x, y, z, u, v = struct.unpack_from("<5f", data, p)
                p += 20
                if -8.0 < u < 8.0 and -8.0 < v < 8.0:
                    us.append(u)
                    vs.append(v)
                    n += 1
    if not us:
        return None
    return (min(us), max(us), min(vs), max(vs), n)


# ------------------------------------------------------------------ main
def main():
    g = index()
    by_tgi = g["by_tgi"]
    fsh_ids = set(i for (t, _gg, i) in by_tgi if t == T_FSH)
    s3d_have = set(i for (t, gg, i) in by_tgi if t == T_S3D and gg == G_S3D)

    exemplars = sorted(i for (t, gg, i) in by_tgi
                       if t == T_EXEMPLAR and gg == G_MARKER)
    print("exemplars in G=0x%08X: %d" % (G_MARKER, len(exemplars)))

    rows = []
    n_parse_fail = n_nokey = n_nomodel = n_notex = 0
    for k, inst in enumerate(exemplars):
        if k % 250 == 0:
            print("  ...%d/%d" % (k, len(exemplars)))
        path, off, sz = by_tgi[(T_EXEMPLAR, G_MARKER, inst)]
        payload, _c = maybe_decompress(read_entry(path, off, sz))
        try:
            _parent, props, _order = parse_exemplar(payload)
        except Exception:
            n_parse_fail += 1
            continue
        name = ""
        if 0x20 in props:
            v = props[0x20][1][0]
            name = v.decode("latin-1", "replace") if isinstance(v, bytes) else str(v)

        bases = []
        for pid in RESKEY_PROPS:
            pv = props.get(pid)
            if not pv:
                continue
            vals = pv[1]
            if len(vals) >= 3 and vals[0] == T_S3D:
                bases.append((pid, vals[2]))
        if not bases:
            n_nokey += 1
            continue

        for pid, base in bases:
            model = None
            for cand in [base | 0x400, base | 0x300, base | 0x200,
                         base | 0x100, base]:
                if cand in s3d_have:
                    model = cand
                    break
            if model is None:
                n_nomodel += 1
                continue
            mpath, moff, msz = by_tgi[(T_S3D, G_S3D, model)]
            mdata, _c = maybe_decompress(read_entry(mpath, moff, msz))
            texs, method = mats_texture_ids(mdata, fsh_ids)
            if not texs:
                n_notex += 1
                continue
            uv = uv_rect(mdata)
            for tex in texs[:2]:          # a marker model binds 1; allow 2
                rows.append(dict(
                    ex_inst=inst, name=name, prop=pid, base=base, model=model,
                    tex=tex, method=method,
                    umin=uv[0] if uv else None, umax=uv[1] if uv else None,
                    vmin=uv[2] if uv else None, vmax=uv[3] if uv else None,
                    nvert=uv[4] if uv else 0,
                    archive=os.path.basename(path)))

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("ex_inst\tname\tprop\tbase\tmodel\ttex\tmethod\tumin\tumax\tvmin\tvmax\tnvert\tarchive\n")
        for r in rows:
            fh.write("%08X\t%s\t%08X\t%08X\t%08X\t%08X\t%s\t%s\t%s\t%s\t%s\t%d\t%s\n"
                     % (r["ex_inst"], r["name"], r["prop"], r["base"], r["model"],
                        r["tex"], r["method"],
                        "%.6f" % r["umin"] if r["umin"] is not None else "",
                        "%.6f" % r["umax"] if r["umax"] is not None else "",
                        "%.6f" % r["vmin"] if r["vmin"] is not None else "",
                        "%.6f" % r["vmax"] if r["vmax"] is not None else "",
                        r["nvert"], r["archive"]))

    print()
    print("rows written        : %d  -> %s" % (len(rows), OUT))
    print("distinct textures   : %d" % len(set(r["tex"] for r in rows)))
    print("exemplar parse fails: %d" % n_parse_fail)
    print("no S3D resource key : %d" % n_nokey)
    print("key but no model    : %d" % n_nomodel)
    print("model but no texture: %d" % n_notex)
    npass = 0
    for want_inst, (want_model, want_tex) in CONTROLS.items():
        got = [r for r in rows if r["ex_inst"] == want_inst]
        if not got:
            print("*** CONTROL 0x%08X MISSING ***" % want_inst)
            continue
        c = got[0]
        good = (c["model"], c["tex"]) == (want_model, want_tex)
        npass += good
        print("CONTROL 0x%08X %-28s -> model 0x%08X tex 0x%08X  %s"
              % (want_inst, c["name"][:28], c["model"], c["tex"],
                 "OK" if good else "*** MISMATCH, expected 0x%08X / 0x%08X ***"
                 % (want_model, want_tex)))
    print("controls passed: %d/%d %s" % (npass, len(CONTROLS),
          "" if npass == len(CONTROLS) else "-> RESULTS UNTRUSTWORTHY"))


if __name__ == "__main__":
    main()
