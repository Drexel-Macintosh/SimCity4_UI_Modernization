#!/usr/bin/env python3
r"""iconhunt shape maths: connected components + "is it a filled disc with a
glyph in it" scoring.  No scipy on this machine, so components come from a
run-length union-find (exact 4-connectivity, not an approximation).

TWO SCORES, deliberately separate:
  score_blue  - a BLUE filled disc (hue 195-260, sat>=.30, val>=.15 so DARK
                navy survives) with a WHITE glyph occupying 5-40% of it.
  score_tint  - a WHITE/GREY filled roundel with a darker-or-cut-out glyph of
                5-40%.  The mission_selection family proves SC4 tints white
                textures at runtime, so the shipped texel may hold no blue.
"""
import numpy as np

MAX_RUNS = 80000


def label_runs(mask):
    """4-connected labelling. -> (lab int32 HxW, nlab) or (None, -1) if the
    mask is too fragmented to be an icon (guards a pathological texture)."""
    h, w = mask.shape
    pad = np.zeros((h, w + 2), np.int8)
    pad[:, 1:-1] = mask
    d = np.diff(pad, axis=1)
    st = np.argwhere(d == 1)
    en = np.argwhere(d == -1)
    R = len(st)
    if R == 0:
        return None, 0
    if R > MAX_RUNS:
        return None, -1
    ry = st[:, 0].astype(np.int32)
    rs = st[:, 1].astype(np.int32)
    re = en[:, 1].astype(np.int32)
    rowstart = np.searchsorted(ry, np.arange(h + 1)).astype(np.int32)

    parent = list(range(R))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    rs_l = rs.tolist()
    re_l = re.tolist()
    for y in range(h - 1):
        i = rowstart[y]
        iend = rowstart[y + 1]
        j = rowstart[y + 1]
        jend = rowstart[y + 2]
        while i < iend and j < jend:
            if re_l[i] <= rs_l[j]:
                i += 1
            elif re_l[j] <= rs_l[i]:
                j += 1
            else:
                union(i, j)
                if re_l[i] < re_l[j]:
                    i += 1
                else:
                    j += 1
    roots = np.array([find(k) for k in range(R)], np.int32)
    uniq, inv = np.unique(roots, return_inverse=True)
    lab = np.zeros((h, w), np.int32)
    ys = ry.tolist()
    ids = (inv + 1).tolist()
    for k in range(R):
        lab[ys[k], rs_l[k]:re_l[k]] = ids[k]
    return lab, len(uniq)


def _fill_holes(sub):
    """sub: bool bbox mask -> (filled, holes)."""
    inv = ~sub
    lab, n = label_runs(inv)
    if lab is None or n <= 0:
        return sub.copy(), np.zeros_like(sub)
    border = set(np.unique(np.concatenate([
        lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])).tolist())
    border.discard(0)
    holes = inv & ~np.isin(lab, list(border)) if border else inv.copy()
    return sub | holes, holes


def _gauss(x, mu, sig):
    return float(np.exp(-((x - mu) ** 2) / (2 * sig * sig)))


def components(mask, min_area=40, max_area=90000, max_comps=400):
    """Yield dicts of geometry for every plausible icon-sized blob."""
    lab, n = label_runs(mask)
    if lab is None:
        return [], (-1 if n == -1 else 0)
    ys, xs = np.nonzero(mask)
    l = lab[ys, xs]
    order = np.argsort(l, kind="stable")
    ls = l[order]
    xs = xs[order]
    ys = ys[order]
    bnd = np.searchsorted(ls, np.arange(1, n + 2))
    out = []
    for k in range(n):
        a, b = bnd[k], bnd[k + 1]
        area = b - a
        if area < min_area or area > max_area:
            continue
        cx0, cx1 = int(xs[a:b].min()), int(xs[a:b].max())
        cy0, cy1 = int(ys[a:b].min()), int(ys[a:b].max())
        out.append({"area": int(area), "bbox": (cx0, cy0, cx1, cy1),
                    "lab": k + 1})
        if len(out) >= max_comps:
            break
    return out, n


def disc_score(sub_filled):
    """Shape-only: how much does this filled blob look like a round disc?"""
    h, w = sub_filled.shape
    area = int(sub_filled.sum())
    if area < 30:
        return 0.0, {}
    ys, xs = np.nonzero(sub_filled)
    cy, cx = ys.mean(), xs.mean()
    r = np.sqrt((ys - cy) ** 2 + (xs - cx) ** 2)
    req = np.sqrt(area / np.pi)
    aspect = min(w, h) / max(w, h)
    compact = area / float(w * h)
    radial = float(r.mean() / req) if req else 9.0
    f_aspect = max(0.0, 1.0 - abs(1.0 - aspect) / 0.40)
    f_compact = _gauss(compact, 0.785, 0.13)
    f_radial = _gauss(radial, 0.667, 0.085)
    return (f_aspect * f_compact * f_radial,
            {"aspect": aspect, "compact": compact, "radial": radial,
             "req": float(req), "cx": float(cx), "cy": float(cy)})


def _glyph_band(f):
    """5-40% of the disc, soft outside."""
    if 0.05 <= f <= 0.40:
        return 1.0
    if f < 0.05:
        return max(0.0, f / 0.05) ** 2
    return max(0.0, 1.0 - (f - 0.40) / 0.25)


def analyse(img):
    """img: HxWx4 uint8 RGBA -> (blue_hits, tint_hits) lists of dicts."""
    h, w = img.shape[:2]
    if h * w < 36 or h * w > 4200000:
        return [], []
    rgb = img[:, :, :3].astype(np.float32) / 255.0
    al = img[:, :, 3]
    mx = rgb.max(2)
    mn = rgb.min(2)
    df = mx - mn
    sat = np.where(mx > 1e-6, df / np.maximum(mx, 1e-6), 0.0)
    val = mx
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    safe = np.maximum(df, 1e-6)
    hue = np.where(mx == r, ((g - b) / safe) % 6,
                   np.where(mx == g, (b - r) / safe + 2, (r - g) / safe + 4))
    hue = hue * 60.0
    vis = al > 128
    blue = vis & (hue >= 195) & (hue <= 262) & (sat >= 0.30) & (val >= 0.15)
    white = vis & (sat <= 0.30) & (val >= 0.68)
    light = vis & (sat <= 0.32) & (val >= 0.55)
    dark = vis & (val <= 0.48)

    blue_hits = []
    tint_hits = []

    # ---- PASS A: blue disc, white glyph ---------------------------------
    if blue.sum() >= 40:
        comps, _n = components(blue)
        for c in comps:
            x0, y0, x1, y1 = c["bbox"]
            sub = blue[y0:y1 + 1, x0:x1 + 1]
            filled, holes = _fill_holes(sub)
            sc, geo = disc_score(filled)
            if sc <= 0.02:
                continue
            farea = int(filled.sum())
            wsub = white[y0:y1 + 1, x0:x1 + 1]
            glyph = int((holes | (wsub & filled)).sum())
            gf = glyph / float(farea)
            bfrac = c["area"] / float(farea)
            score = sc * _glyph_band(gf) * min(1.0, max(0.0, (bfrac - 0.35) / 0.25))
            if farea < 60:
                score *= farea / 60.0
            if score <= 0.01:
                continue
            blue_hits.append({"score": float(score), "bbox": c["bbox"],
                              "area": farea, "glyph": gf, "bfrac": bfrac,
                              "shape": float(sc), **geo})

    # ---- PASS B: white/grey roundel, dark or cut-out glyph ---------------
    for tag, m in (("opaque", vis), ("light", light)):
        if m.sum() < 40 or m.sum() > 900000:
            continue
        comps, _n = components(m)
        for c in comps:
            x0, y0, x1, y1 = c["bbox"]
            sub = m[y0:y1 + 1, x0:x1 + 1]
            filled, holes = _fill_holes(sub)
            sc, geo = disc_score(filled)
            if sc <= 0.05:
                continue
            farea = int(filled.sum())
            lsub = light[y0:y1 + 1, x0:x1 + 1]
            dsub = dark[y0:y1 + 1, x0:x1 + 1]
            lfrac = float((lsub & filled).sum()) / farea
            glyph = int((holes | (dsub & filled)).sum())
            gf = glyph / float(farea)
            score = (sc * _glyph_band(gf)
                     * min(1.0, max(0.0, (lfrac - 0.30) / 0.30)))
            if farea < 60:
                score *= farea / 60.0
            if score <= 0.02:
                continue
            tint_hits.append({"score": float(score), "bbox": c["bbox"],
                              "area": farea, "glyph": gf, "lfrac": lfrac,
                              "mask": tag, "shape": float(sc), **geo})

    blue_hits.sort(key=lambda d: -d["score"])
    tint_hits.sort(key=lambda d: -d["score"])
    return blue_hits[:3], tint_hits[:3]
