"""STROKE-WIDTH CONSISTENCY - the number for "some strokes 1px, some 2px".

The user's 2026-09-01 description of the 1.5x tier was "ragged / uneven edges,
some strokes 1px, some 2px, stair-steps of different sizes, nothing smeared" -
everywhere. That is the nearest signature at 3/2 (source columns get
multiplicity 2,1,2,1), and NONE of the existing instruments reads it directly:
`evenness.py` needs >=6 equal runs of length >=2 on one scanline (a tick
ladder), `metrics.soft_frac` reads blending, `edge_w` reads transition width.
A lone 1px bevel line that renders 2px on even rows and 1px on odd rows is
invisible to all three.

This one reads it. For every BOUNDED same-colour run in the 1x source (a run
whose two neighbours are a different colour and which does not touch the sheet
edge) of length L in 1..MAXL, along rows (horizontal extent) and along columns
(vertical extent), find the run the OUTPUT holds at the same place and record
its length. Then, per L:

    CV_L  = std / mean of the output lengths of all source runs of length L
    swc   = sum_L n_L * CV_L / sum_L n_L          (0 = every equal run equal)

The output run is located by the FACTOR MAP (`nearest`'s own, Upscale2x.cs
UpscaleNearest: src = floor(out / f)): the source run [s0,s1) maps to output
columns [ceil(s0*f), ceil(s1*f)), and the output run containing the CENTRE of
that span is measured. If the output pixel there is not the source run's exact
colour the candidate blended it - that run is counted in `blended` and excluded
from CV (a blending resampler is judged by `swc_ink`, below), never silently
included as a length-1 run.

    swc_ink  the same grouping, but integrated |luma - local background| over
             the mapped span - fair to a blender (ink_evenness.py's idea,
             extended to L=1 and to bounded runs of any repetition count).

POSITIVE CONTROL, by construction: at an integer factor a bounded run of length
L maps to exactly L*f output pixels of its own colour, so every CV_L must read
0.000 on `preview/` (2x) and `preview-3x/` (3x). If it does not, the instrument
is wrong, not the tier - fix it before believing any 1.5x number (law 88: a
model that condemns stock is a broken model).

PREDICTION the instrument must reproduce (the odd/even theorem, plan 2026-09-01):
at f=1.5 plain nearest gives 1px runs 1-or-2 (CV_1 high), 2px runs always 3
(CV_2 = 0), 3px runs 4-or-5, 4px always 6. A candidate that disagrees with that
table on a synthetic sheet is a bug in the candidate (theorem_check.py).

Usage as a module: `sheet_stats(src, out, factor)` -> dict.
"""
import numpy as np

MAXL = 4
LUMA = np.array([0.299, 0.587, 0.114])


def _pack(a):
    return (a[..., 0].astype(np.uint32) << 24 | a[..., 1].astype(np.uint32) << 16
            | a[..., 2].astype(np.uint32) << 8 | a[..., 3].astype(np.uint32))


def _runs2d(p):
    """Run decomposition of every row of a packed HxW array at once.

    Returns (row, start, length, colour) for every run. Rows are separated by
    a sentinel column so a run can never cross a row boundary."""
    h, w = p.shape
    # opaque white packs to 0xFFFFFFFF, so the sentinel must live above 32 bits
    sent = np.full((h, 1), np.uint64(1) << np.uint64(40), np.uint64)
    q = np.concatenate([p.astype(np.uint64), sent], axis=1).ravel()
    change = np.flatnonzero(q[1:] != q[:-1]) + 1
    starts = np.concatenate([[0], change])
    ends = np.concatenate([change, [q.size]])
    lengths = ends - starts
    rows = starts // (w + 1)
    cols = starts % (w + 1)
    keep = cols < w  # drop the sentinel runs
    return rows[keep], cols[keep], lengths[keep], q[starts[keep]]


def _bounded_runs(p, maxl=MAXL):
    """Bounded runs of length 1..maxl per row: (row, start, length, colour).
    Bounded = does not touch column 0 or column w-1 (both neighbours exist and
    differ by construction of a maximal run)."""
    h, w = p.shape
    r, c, L, col = _runs2d(p)
    ok = (L <= maxl) & (c > 0) & (c + L < w)
    return r[ok], c[ok], L[ok], col[ok]


def _out_row_for(y, f, oh):
    """The first output row whose factor-map source is y, clamped."""
    return np.minimum(np.ceil(y * f).astype(np.int64), oh - 1)


def _axis_stats(src_p, out_p, f, maxl=MAXL):
    """One axis (rows of the arrays given). Returns dict L -> list of output
    lengths (copy-exact), plus counts of blended runs and the ink table."""
    h, w = src_p.shape
    oh, ow = out_p.shape
    ry, rx, rL, rcol = _bounded_runs(src_p, maxl)
    if ry.size == 0:
        return {}, {}, 0
    # output run decomposition, addressable by (row, col)
    orow, ocol, oL, ocolour = _runs2d(out_p)
    # flat (row, col) start of every output run, sorted, for a searchsorted
    # lookup: the run holding output pixel i is the last start <= i
    flat_starts = orow * (ow + 1) + ocol
    kept_flat = flat_starts
    order = np.argsort(kept_flat)
    kept_flat = kept_flat[order]
    kL = oL[order]
    kcolour = ocolour[order]
    kcol = ocol[order]
    # for a flat output index i, the run is the last kept start <= i
    def lookup(flat_i):
        j = np.searchsorted(kept_flat, flat_i, side="right") - 1
        return kL[j], kcolour[j], kcol[j]

    oy = _out_row_for(ry, f, oh)
    centre = (rx.astype(np.float64) + rL / 2.0) * f  # centre of the mapped span
    ox = np.minimum(np.floor(centre).astype(np.int64), ow - 1)
    flat = oy * (ow + 1) + ox
    lens, cols, starts = lookup(flat)
    exact = cols == rcol
    # a copy candidate can still return the WRONG run if the centre pixel is a
    # neighbour's colour (an odd-width run entirely displaced): count as blended
    per_L = {}
    for L in range(1, maxl + 1):
        m = (rL == L) & exact
        per_L[L] = lens[m]
    blended = int((~exact).sum())
    return per_L, {}, blended


def _ink_stats(src, out, f, maxl=MAXL):
    """Integrated ink per bounded source run, grouped by L, both axes."""
    res = {}
    for axis in (0, 1):
        s = src if axis == 0 else np.transpose(src, (1, 0, 2))
        o = out if axis == 0 else np.transpose(out, (1, 0, 2))
        sp = _pack(s)
        lum = (o[..., :3].astype(np.float64) @ LUMA)
        h, w = sp.shape
        oh, ow = lum.shape
        ry, rx, rL, _ = _bounded_runs(sp, maxl)
        if ry.size == 0:
            continue
        oy = _out_row_for(ry, f, oh)
        x0 = np.ceil(rx * f).astype(np.int64)
        x1 = np.minimum(np.ceil((rx + rL) * f).astype(np.int64), ow)
        # local background = the output pixel just outside the span on the left
        # (the run is bounded, so it exists)
        bgx = np.maximum(x0 - 1, 0)
        bg = lum[oy, bgx]
        for i in range(ry.size):
            span = lum[oy[i], x0[i]:x1[i] + 1]  # +1: the AA half may spill one px
            ink = float(np.abs(span - bg[i]).sum())
            res.setdefault(int(rL[i]), []).append(ink)
    return res


def sheet_stats(src, out, factor, maxl=MAXL, ink=False):
    """src, out: HxWx4 uint8. Returns dict with per-L CV of output run lengths
    (both axes pooled), counts, blended count, and (optionally) ink CV."""
    sp, op = _pack(src), _pack(out)
    per_L = {L: [] for L in range(1, maxl + 1)}
    blended = 0
    for axis in (0, 1):
        s = sp if axis == 0 else sp.T
        o = op if axis == 0 else op.T
        pl, _, b = _axis_stats(np.ascontiguousarray(s), np.ascontiguousarray(o),
                               factor, maxl)
        blended += b
        for L, v in pl.items():
            per_L[L].append(v)
    out_d = {"blended": blended}
    ntot, acc = 0, 0.0
    for L in range(1, maxl + 1):
        v = np.concatenate(per_L[L]) if per_L[L] else np.zeros(0)
        n = int(v.size)
        out_d["n_%d" % L] = n
        if n >= 2 and v.mean() > 0:
            cv = float(v.std() / v.mean())
        else:
            cv = 0.0
        out_d["cv_%d" % L] = cv
        # distribution of output lengths for this L (what the eye sees)
        if n:
            vals, cnts = np.unique(v, return_counts=True)
            out_d["hist_%d" % L] = {int(a): int(b) for a, b in zip(vals, cnts)}
        ntot += n
        acc += n * cv
    out_d["n"] = ntot
    out_d["swc"] = (acc / ntot) if ntot else 0.0
    if ink:
        ik = _ink_stats(src, out, factor, maxl)
        nt, ac = 0, 0.0
        for L, v in ik.items():
            v = np.asarray(v)
            if v.size >= 2 and v.mean() > 0:
                cv = float(v.std() / v.mean())
                out_d["ink_cv_%d" % L] = cv
                nt += v.size
                ac += v.size * cv
        out_d["swc_ink"] = (ac / nt) if nt else 0.0
    return out_d


def pool(stats_list, maxl=MAXL):
    """Pool per-sheet stats into corpus numbers (n-weighted CV per L)."""
    out = {}
    ntot, acc = 0, 0.0
    for L in range(1, maxl + 1):
        n = sum(s.get("n_%d" % L, 0) for s in stats_list)
        cv = (sum(s.get("n_%d" % L, 0) * s.get("cv_%d" % L, 0.0) for s in stats_list)
              / n) if n else 0.0
        out["n_%d" % L] = n
        out["cv_%d" % L] = cv
        ntot += n
        acc += n * cv
    out["n"] = ntot
    out["swc"] = (acc / ntot) if ntot else 0.0
    out["blended"] = sum(s.get("blended", 0) for s in stats_list)
    ink_n = sum(1 for s in stats_list if "swc_ink" in s)
    if ink_n:
        out["swc_ink"] = sum(s["swc_ink"] for s in stats_list if "swc_ink" in s) / ink_n
    return out


def fmt(d, maxl=MAXL):
    parts = ["swc %.4f" % d.get("swc", 0.0)]
    for L in range(1, maxl + 1):
        parts.append("cv%d %.3f/%d" % (L, d.get("cv_%d" % L, 0.0), d.get("n_%d" % L, 0)))
    parts.append("blended %d" % d.get("blended", 0))
    if "swc_ink" in d:
        parts.append("ink %.4f" % d["swc_ink"])
    return "  ".join(parts)
