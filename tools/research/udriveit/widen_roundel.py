#!/usr/bin/env python3
r"""THE WIDENED PASS (step 5): drop the blue requirement entirely and rank every
marker-family sprite by how much it is a DISC / ROUNDEL, any colour.

Rationale: the Zot textures prove this family tints at runtime, so a colour test
can miss a disc that is blue only on screen.  Shape cannot be tinted away.

disc score = area / (pi * r95^2), where r95 is the 95th-percentile distance of a
visible pixel from the mask centroid.  A filled circle scores ~1.0; a square
~0.64; a thin or ragged blob much less.  Combined with bbox aspect ratio.

POSITIVE CONTROL FOR THE SHAPE DETECTOR: the four Zot_* sprites ARE roundels
(red prohibition circles, seen by eye in fsh-1e060400-0.png).  They MUST land
near the top of this ranking.  If they do not, the detector is broken and a
"no disc found" result below is a tool failure, not a fact.

Also answers, by lookup rather than by inference, whether the Tag1x1x3_* family
binds any model at all.

    python widen_roundel.py
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image                                            # noqa: E402
from index_all import index, T_S3D, G_S3D, T_EXEMPLAR, G_MARKER  # noqa: E402
from census_markers import read_entry, maybe_decompress, parse_exemplar  # noqa: E402
import render_family as RF                                       # noqa: E402

TSV = os.path.join(HERE, "family-pixels.tsv")
OUT = os.path.join(HERE, "family-roundel.tsv")
ZOTS = {"0FD10000", "107A0000", "1C430000", "1C440000"}


NBINS = 36


def disc_score(sp):
    """OUTLINE circularity: how constant is the silhouette's outer radius?

    ⛔ FIRST ATTEMPT WAS BROKEN AND ITS CONTROL CAUGHT IT.  Scoring
    area/(pi*r95^2) measures 'fills its own bounding box', so full-atlas SQUARE
    crops scored 0.93-0.97 and the four Zot roundels -- which are HOLLOW RINGS
    with a transparent middle -- ranked 1136-1382 of 1525.  A prohibition ring
    has small area and large radius, the exact worst case for that metric.

    This version bins the mask by angle around the centroid and takes the
    MAXIMUM radius per bin, i.e. the outer silhouette only.  Ring and filled
    disc both score alike; a square's radius swings by sqrt(2) between edge and
    corner and scores much lower.
    """
    # ⛔ SECOND BUG THE CONTROL CAUGHT: using alpha alone as "visible" counted
    # the atlas's OPAQUE BLACK padding as silhouette, so every crop became a
    # filled rectangle and three of the four Zot roundels were rejected outright
    # for having a square outline.  Near-black must be excluded here exactly as
    # render_family.score() already excludes it.
    W, H = sp.size
    a = list(sp.split()[3].getdata())
    val = list(sp.convert("HSV").split()[2].getdata())
    pts = [(k % W, k // W) for k in range(len(a))
           if a[k] > 100 and val[k] >= 13]
    if len(pts) < 60:
        return None
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    rmax = [0.0] * NBINS
    for x, y in pts:
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        b = int((math.atan2(dy, dx) + math.pi) / (2 * math.pi) * NBINS) % NBINS
        if r > rmax[b]:
            rmax[b] = r
    if min(rmax) <= 0:                    # a gap in the silhouette: not round
        return None
    mean = sum(rmax) / NBINS
    var = sum((r - mean) ** 2 for r in rmax) / NBINS
    circ = max(0.0, 1.0 - (math.sqrt(var) / mean))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    aspect = min(bw, bh) / max(bw, bh)
    return dict(disc=circ, aspect=aspect, area=len(pts), bw=bw, bh=bh)


def tag_family_model_check():
    """Does ANY Tag1x1x3_* exemplar bind a real S3D?  Lookup, not inference."""
    g = index()
    by_tgi = g["by_tgi"]
    s3d = set(i for (t, gg, i) in by_tgi if t == T_S3D and gg == G_S3D)
    print("=" * 78)
    print("Tag1x1x3_* MODEL BINDING  (the U-Drive-It vehicle marker family)")
    print("=" * 78)
    print("S3D {0x5AD0E817,0xBADB57F1,0x00000000} present in any archive: %s"
          % ("YES" if 0 in s3d else "NO"))
    print("S3D {...,0x00000400} (zoom-4 of a null base) present          : %s"
          % ("YES" if 0x400 in s3d else "NO"))
    print("  (positive control: {...,0x29F10400} present = %s)"
          % ("YES" if 0x29F10400 in s3d else "NO -> lookup is broken"))
    print()
    rows = []
    for (t, gg, i) in sorted(by_tgi):
        if (t, gg) != (T_EXEMPLAR, G_MARKER):
            continue
        path, off, sz = by_tgi[(t, gg, i)]
        payload, _c = maybe_decompress(read_entry(path, off, sz))
        try:
            _p, props, _o = parse_exemplar(payload)
        except Exception:
            continue
        nm = ""
        if 0x20 in props:
            v = props[0x20][1][0]
            nm = v.decode("latin-1", "replace") if isinstance(v, bytes) else str(v)
        if not nm.lower().startswith("tag1x1x3"):
            continue
        keys = []
        for pid in (0x27812820, 0x27812821, 0x27812822, 0x27812823,
                    0x27812824, 0x27812825):
            pv = props.get(pid)
            if pv and len(pv[1]) >= 3:
                keys.append("0x%08X={0x%08X,0x%08X,0x%08X}"
                            % (pid, pv[1][0], pv[1][1], pv[1][2]))
        tag = props.get(0xABB90E58)
        rows.append((i, nm, keys, tag[1][0] if tag else None,
                     props.get(0x8A416A99)))
    print("%d Tag1x1x3_* exemplars:" % len(rows))
    nonnull = 0
    for i, nm, keys, tag, rk in rows:
        null = all("0x00000000}" in k for k in keys) if keys else True
        nonnull += (not null)
        print("  I=0x%08X %-34s TagKind=%s  %s"
              % (i, nm[:34], ("0x%X" % tag) if tag is not None else "-",
                 "; ".join(keys) if keys else "NO resource-key property"))
    print()
    print("-> Tag1x1x3_* members binding a NON-NULL S3D instance: %d of %d"
          % (nonnull, len(rows)))
    return rows


def main():
    tag_family_model_check()

    g = index()
    by_ti = g["by_ti"]
    rows = list(csv.DictReader(open(TSV, encoding="utf-8"), delimiter="\t"))
    rows.sort(key=lambda r: r["tex"])
    out = []
    for k, r in enumerate(rows):
        if k % 250 == 0:
            print("  shape ...%d/%d" % (k, len(rows)))
        im = RF.atlas(int(r["tex"], 16), by_ti)
        if im is None:
            continue
        sp, _rect, _c = RF.crop_sprite(im, r)
        if sp.width * sp.height > 400 * 400:
            sp = sp.resize((200, 200), Image.LANCZOS)
        s = disc_score(sp)
        if s is None:
            continue
        rec = dict(r)
        rec.update(s)
        out.append(rec)

    out.sort(key=lambda r: -(r["disc"] * r["aspect"]))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("rank\tex_inst\tname\tmodel\ttex\tdisc\taspect\tarea\tbw\tbh"
                 "\tblue\twhite\tred\n")
        for n, r in enumerate(out):
            fh.write("%d\t%s\t%s\t%s\t%s\t%.3f\t%.3f\t%d\t%d\t%d\t%s\t%s\t%s\n"
                     % (n + 1, r["ex_inst"], r["name"], r["model"], r["tex"],
                        r["disc"], r["aspect"], r["area"], r["bw"], r["bh"],
                        r["blue"], r["white"], r["red"]))
    print()
    print("shape-scored sprites: %d  -> %s" % (len(out), OUT))
    print()
    print("SHAPE-DETECTOR POSITIVE CONTROL (the four Zot roundels):")
    for n, r in enumerate(out):
        if r["ex_inst"] in ZOTS:
            print("  rank %4d/%d  %-24s disc=%.3f aspect=%.3f"
                  % (n + 1, len(out), r["name"][:24], r["disc"], r["aspect"]))
    print()
    print("TOP 30 ROUNDELS (any colour):")
    for r in out[:30]:
        print("  %-42s I=%s F=%s disc=%.3f asp=%.3f %dx%d b=%s w=%s r=%s"
              % (r["name"][:42] or "(unnamed)", r["ex_inst"], r["tex"],
                 r["disc"], r["aspect"], r["bw"], r["bh"],
                 r["blue"], r["white"], r["red"]))
    return out


if __name__ == "__main__":
    main()
